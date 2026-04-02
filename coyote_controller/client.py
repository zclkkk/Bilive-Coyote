from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


class CoyoteAPIError(RuntimeError):
    """Raised when the Coyote API returns an error."""


@dataclass
class CoyoteClient:
    base_url: str = "http://127.0.0.1:8920"
    client_id: Optional[str] = None
    token: Optional[str] = None
    timeout: float = 10.0

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self.session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = self.session.request(
            method=method,
            url=url,
            headers=self._headers(),
            json=json_body,
            timeout=self.timeout,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise CoyoteAPIError(f"HTTP {response.status_code} for {url}: {response.text}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise CoyoteAPIError(f"Invalid JSON from {url}: {response.text}") from exc

        if isinstance(data, dict) and data.get("status") == 0:
            code = data.get("code", "UNKNOWN")
            message = data.get("message", "")
            raise CoyoteAPIError(f"API error {code}: {message}")

        return data

    def _require_client_id(self, client_id: Optional[str] = None) -> str:
        cid = client_id or self.client_id
        if cid:
            return cid
        raise ValueError("client_id is required. Set client_id in config.json.")

    def get_server_info(self) -> Dict[str, Any]:
        return self._request("GET", "/api/server_info")

    def get_game_api_info(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v2/game")

    def get_game_info(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        cid = self._require_client_id(client_id)
        return self._request("GET", f"/api/v2/game/{cid}")

    def get_strength_config(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        cid = self._require_client_id(client_id)
        return self._request("GET", f"/api/v2/game/{cid}/strength")

    def change_strength(
        self,
        *,
        target: str,
        action: str,
        value: float,
        client_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cid = self._require_client_id(client_id)
        target_map = {
            "base": "strength",
            "random": "randomStrength",
        }
        action_map = {
            "add": "add",
            "sub": "sub",
            "set": "set",
        }

        try:
            payload_key = target_map[target]
            action_key = action_map[action]
        except KeyError as exc:
            raise ValueError("target must be 'base' or 'random', and action must be 'add', 'sub', or 'set'.") from exc

        payload: Dict[str, Any] = {
            payload_key: {
                action_key: value,
            }
        }
        return self._request("POST", f"/api/v2/game/{cid}/strength", json_body=payload)

    def fire(
        self,
        *,
        strength: int,
        time_ms: Optional[int] = None,
        override: bool = False,
        pulse_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cid = self._require_client_id(client_id)
        payload: Dict[str, Any] = {"strength": strength, "override": override}
        if time_ms is not None:
            payload["time"] = time_ms
        if pulse_id:
            payload["pulseId"] = pulse_id
        return self._request("POST", f"/api/v2/game/{cid}/action/fire", json_body=payload)
