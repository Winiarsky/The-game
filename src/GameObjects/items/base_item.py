from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


def _new_instance_id() -> str:
    return f"item-{uuid4().hex[:10]}"


@dataclass
class BaseItem:
    item_id: str
    name: str
    category: str
    description: str = ""
    traits: tuple[str, ...] = ()
    price_cp: int = 0
    bulk: str | int | float = "-"
    instance_id: str = field(default_factory=_new_instance_id)

    @staticmethod
    def _bulk_label(value: str | int | float | None) -> str:
        raw = str(value if value is not None else "-").strip()
        if not raw:
            return "-"
        if raw.lower() == "l":
            return "L"
        return raw

    @staticmethod
    def _price_label(price_cp: int) -> str:
        value = max(0, int(price_cp or 0))
        if value == 0:
            return "0 cp"
        pp = value // 1000
        value %= 1000
        gp = value // 100
        value %= 100
        sp = value // 10
        cp = value % 10
        parts: list[str] = []
        if pp:
            parts.append(f"{pp} pp")
        if gp:
            parts.append(f"{gp} gp")
        if sp:
            parts.append(f"{sp} sp")
        if cp:
            parts.append(f"{cp} cp")
        return ", ".join(parts) if parts else "0 cp"

    def ui_description(self) -> str:
        traits = ", ".join(self.traits) if self.traits else "brak"
        economy_lines = [
            f"- Cena: {self._price_label(self.price_cp)}",
            f"- Bulk: {self._bulk_label(self.bulk)}",
        ]
        ammo_line = ""
        ammo_count = getattr(self, "ammo_count", None)
        try:
            if ammo_count is not None:
                ammo_line = f"\n- Amunicja w stacku: {max(0, int(ammo_count))}"
        except Exception:
            ammo_line = ""
        if self.description:
            return f"{self.description}\n" + "\n".join(economy_lines) + f"\n- Traits: {traits}{ammo_line}"
        return "\n".join(economy_lines) + f"\n- Traits: {traits}{ammo_line}"


__all__ = [
    "BaseItem",
]
