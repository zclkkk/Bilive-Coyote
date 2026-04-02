from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable

from coyote_controller.api import CoyoteAPI


class GiftActionError(RuntimeError):
    """Raised when gift action configuration is invalid."""


@dataclass
class GiftEvent:
    gift_id: int
    gift_name: str
    gift_num: int
    raw: Dict[str, Any]


@dataclass
class GiftRule:
    gift_id: int
    target: str
    action: str
    value: float
    multiply_by_gift_num: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GiftRule":
        try:
            return cls(
                gift_id=int(data["gift_id"]),
                target=str(data["target"]),
                action=str(data["action"]),
                value=float(data["value"]),
                multiply_by_gift_num=bool(data.get("multiply_by_gift_num", True)),
            )
        except KeyError as exc:
            raise GiftActionError(f"Missing bilibili.gift_actions field: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise GiftActionError(f"Invalid bilibili.gift_actions entry: {data}") from exc

    def resolve_amount(self, gift_num: int) -> float:
        return self.value * gift_num if self.multiply_by_gift_num else self.value


class GiftActionService:
    def __init__(self, api: CoyoteAPI, rules: Iterable[GiftRule]) -> None:
        self.api = api
        self.rules = list(rules)

    def handle_gift(self, event: GiftEvent) -> bool:
        matched = False
        for rule in self.rules:
            if rule.gift_id != event.gift_id:
                continue
            matched = True
            amount = rule.resolve_amount(event.gift_num)
            result = self.api.change_strength(target=rule.target, action=rule.action, value=amount)
            print(
                f"[gift] {event.gift_name} x{event.gift_num} -> {rule.target}.{rule.action} {amount} | "
                f"{result.get('message', result.get('code', 'OK'))}"
            )
        if not matched:
            print(f"[gift] {event.gift_name} x{event.gift_num} ignored")
        return matched
