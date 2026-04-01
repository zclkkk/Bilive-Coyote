from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .client import DGLabClient


@dataclass
class CoyoteAPI:
    client: DGLabClient

    def get_server_info(self) -> Dict[str, Any]:
        return self.client.get_server_info()

    def get_game_api_info(self) -> Dict[str, Any]:
        return self.client.get_game_api_info()

    def get_game_info(self) -> Dict[str, Any]:
        return self.client.get_game_info()

    def get_strength_info(self) -> Dict[str, Any]:
        return self.client.get_strength_config()

    def change_strength(self, *, target: str, action: str, value: float) -> Dict[str, Any]:
        return self.client.change_strength(target=target, action=action, value=value)

    def fire(
        self,
        *,
        strength: int,
        time_ms: Optional[int] = None,
        override: bool = False,
        pulse_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.client.fire(
            strength=strength,
            time_ms=time_ms,
            override=override,
            pulse_id=pulse_id,
        )
