from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import random
import struct
import time
import zlib
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, Iterable, List

import requests

from .gift_actions import GiftActionService, GiftEvent, GiftRule


class BilibiliLiveError(RuntimeError):
    """Raised when Bilibili Open Live integration fails."""


@dataclass
class BilibiliLiveConfig:
    code: str
    app_id: int
    access_key_id: str
    access_key_secret: str
    host: str
    gift_actions: List[GiftRule]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BilibiliLiveConfig":
        if not isinstance(data, dict):
            raise BilibiliLiveError("Missing 'bilibili' config section.")

        missing: List[str] = []
        for field in ["code", "access_key_id", "access_key_secret"]:
            if not str(data.get(field, "")).strip():
                missing.append(field)
        if "app_id" not in data:
            missing.append("app_id")
        if missing:
            raise BilibiliLiveError(f"Missing bilibili config fields: {', '.join(missing)}")

        raw_rules = data.get("gift_actions")
        if not isinstance(raw_rules, list) or not raw_rules:
            raise BilibiliLiveError("bilibili.gift_actions must be a non-empty list.")

        return cls(
            code=str(data["code"]),
            app_id=int(data["app_id"]),
            access_key_id=str(data["access_key_id"]),
            access_key_secret=str(data["access_key_secret"]),
            host=str(data.get("host", "https://live-open.biliapi.com")).rstrip("/"),
            gift_actions=[GiftRule.from_dict(item) for item in raw_rules],
        )


class BilibiliLiveBridge:
    def __init__(self, config: BilibiliLiveConfig, gift_service: GiftActionService, timeout: float = 10.0) -> None:
        self.config = config
        self.gift_service = gift_service
        self.game_id = ""
        self.http = requests.Session()
        self.timeout = timeout

    def run(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        websocket = None
        heartbeat_task = None
        app_heartbeat_task = None
        try:
            websocket = await self._connect()
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket))
            app_heartbeat_task = asyncio.create_task(self._app_heartbeat_loop())
            await self._recv_loop(websocket)
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
            if app_heartbeat_task:
                app_heartbeat_task.cancel()
            if websocket:
                await websocket.close()
            if self.game_id:
                self._end_app()

    def _sign_headers(self, payload: str) -> Dict[str, str]:
        md5 = hashlib.md5()
        md5.update(payload.encode("utf-8"))

        timestamp = str(int(time.time()))
        nonce = str(random.randint(1, 100000) + time.time())
        headers = {
            "x-bili-timestamp": timestamp,
            "x-bili-signature-method": "HMAC-SHA256",
            "x-bili-signature-nonce": nonce,
            "x-bili-accesskeyid": self.config.access_key_id,
            "x-bili-signature-version": "1.0",
            "x-bili-content-md5": md5.hexdigest(),
        }

        canonical = "\n".join(f"{key}:{headers[key]}" for key in sorted(headers))
        signature = hmac.new(
            self.config.access_key_secret.encode("utf-8"),
            canonical.encode("utf-8"),
            digestmod=sha256,
        ).hexdigest()

        headers["Authorization"] = signature
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        return headers

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        response = self.http.post(
            f"{self.config.host}{path}",
            headers=self._sign_headers(body),
            data=body.encode("utf-8"),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise BilibiliLiveError(f"Bilibili API error {data.get('code')}: {data.get('message', '')}")
        return data

    def _start_app(self) -> Dict[str, Any]:
        data = self._post("/v2/app/start", {"code": self.config.code, "app_id": self.config.app_id})
        self.game_id = str(data["data"]["game_info"]["game_id"])
        return data["data"]

    def _app_heartbeat(self) -> None:
        if not self.game_id:
            raise BilibiliLiveError("Cannot heartbeat before app start.")
        self._post("/v2/app/heartbeat", {"game_id": self.game_id})

    def _end_app(self) -> None:
        self._post("/v2/app/end", {"game_id": self.game_id, "app_id": self.config.app_id})

    async def _connect(self):
        try:
            import websockets
        except ModuleNotFoundError as exc:
            raise BilibiliLiveError(
                "Missing dependency 'websockets'. Run: pip install -r requirements.txt"
            ) from exc

        data = self._start_app()
        ws_url = data["websocket_info"]["wss_link"][0]
        auth_body = data["websocket_info"]["auth_body"]
        websocket = await websockets.connect(ws_url)
        await self._auth(websocket, auth_body)
        print("[bilibili] connected")
        return websocket

    async def _auth(self, websocket, auth_body: str) -> None:
        await websocket.send(self._pack_packet(auth_body.encode("utf-8"), op=7))
        response = await websocket.recv()
        for packet in self._iter_packets(response):
            if packet["op"] != 8:
                continue
            try:
                body = json.loads(packet["body"].decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BilibiliLiveError("Invalid auth response from websocket.") from exc
            if body.get("code") != 0:
                raise BilibiliLiveError(f"Bilibili websocket auth failed: {body}")
            return
        raise BilibiliLiveError("Missing auth response from websocket.")

    async def _heartbeat_loop(self, websocket) -> None:
        while True:
            await asyncio.sleep(20)
            await websocket.send(self._pack_packet(b"", op=2))

    async def _app_heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(20)
            self._app_heartbeat()

    async def _recv_loop(self, websocket) -> None:
        while True:
            raw = await websocket.recv()
            for message in self._decode_messages(raw):
                self._handle_message(message)

    def _handle_message(self, message: Dict[str, Any]) -> None:
        if message.get("cmd") != "LIVE_OPEN_PLATFORM_SEND_GIFT":
            return

        data = message.get("data", {})
        try:
            gift_id = int(data["gift_id"])
            gift_num = int(data.get("gift_num", 1))
        except (KeyError, TypeError, ValueError):
            print(f"[bilibili] skip malformed gift message: {message}")
            return

        gift_name = str(data.get("gift_name", gift_id))
        event = GiftEvent(
            gift_id=gift_id,
            gift_name=gift_name,
            gift_num=gift_num,
            raw=message,
        )
        self.gift_service.handle_gift(event)

    @staticmethod
    def _pack_packet(body: bytes, op: int) -> bytes:
        header_len = 16
        packet_len = header_len + len(body)
        return struct.pack(">IHHII", packet_len, header_len, 1, op, 1) + body

    @staticmethod
    def _iter_packets(buffer: bytes) -> Iterable[Dict[str, Any]]:
        offset = 0
        while offset + 16 <= len(buffer):
            packet_len, header_len, ver, op, seq = struct.unpack(">IHHII", buffer[offset : offset + 16])
            if packet_len <= 0:
                break
            body_start = offset + header_len
            body_end = offset + packet_len
            yield {
                "packet_len": packet_len,
                "header_len": header_len,
                "ver": ver,
                "op": op,
                "seq": seq,
                "body": buffer[body_start:body_end],
            }
            offset += packet_len

    def _decode_messages(self, buffer: bytes) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        for packet in self._iter_packets(buffer):
            ver = packet["ver"]
            op = packet["op"]
            body = packet["body"]

            if op in {3, 8}:
                continue
            if ver in {0, 1}:
                if not body:
                    continue
                try:
                    messages.append(json.loads(body.decode("utf-8")))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    print("[bilibili] skip undecodable packet")
            elif ver == 2:
                messages.extend(self._decode_messages(zlib.decompress(body)))
            else:
                print(f"[bilibili] unsupported packet version: {ver}")
        return messages
