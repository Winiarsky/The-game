from __future__ import annotations

from dataclasses import dataclass, field

from board import consts
from GameObjects.interactions_mixin.base_interaction import InteractableMixin, Interaction
from GameObjects.items.inventory import add_item, item_label
from economy import format_cp_value
from party_stash import (
    add_party_cp,
    add_party_stash_items,
    item_details_markdown,
    item_summary,
    split_currency,
)
from prompt_text_catalog import render_prompt_text


@dataclass
class LootPile(InteractableMixin):
    name: str = "Loot"
    loot_items: list[object] = field(default_factory=list)
    allow_same_cell_interact: bool = True
    require_same_cell_interact: bool = False
    allow_hidden_interaction: bool = False
    blocks_movement: bool = False
    seek_color: list[int] = field(default_factory=lambda: list(consts.SEEK_LOOT_RGB))
    seek_color_name: str = "niebieskie"
    seek_label: str = "loot"

    def __post_init__(self) -> None:
        super().__post_init__()
        action_text = render_prompt_text("interaction.loot_pickup_action")
        self.register_action(
            Interaction(
                id="pickup_loot",
                label="Podnieś loot",
                description=str(
                    action_text.get("description")
                    or "Stań na polu lootu, użyj Interakcja i wybierz tę opcję, aby zabrać wszystkie przedmioty i monety."
                ),
                handler=self._pickup_handler,
                tags=["interaction", "manipulate", "loot"],
                end_interaction=True,
            )
        )

    def _breakdown(self, items: list[object] | None = None) -> tuple[list[str], int]:
        item_loot, coin_cp = split_currency(list(self.loot_items if items is None else items))
        return [item_label(item) for item in item_loot], coin_cp

    def _summary_from(self, items: list[object] | None = None, *, max_items: int = 4) -> str:
        item_loot, coin_cp = split_currency(list(self.loot_items if items is None else items))
        return item_summary(item_loot, coin_cp, max_items=max_items)

    def _details_from(self, items: list[object] | None = None) -> str:
        item_loot, coin_cp = split_currency(list(self.loot_items if items is None else items))
        return item_details_markdown(item_loot, coin_cp)

    def loot_summary(self) -> str:
        return self._summary_from()

    def loot_details_markdown(self) -> str:
        return self._details_from()

    def _pickup_description(self) -> str:
        text = render_prompt_text(
            "interaction.loot_pickup_action",
            loot_summary=self.loot_summary(),
        )
        return str(text.get("description") or f"Podnieś: {self.loot_summary()}.")

    def available_actions(self) -> list[Interaction]:
        actions = super().available_actions()
        for action in actions:
            if action.id == "pickup_loot":
                action.description = self._pickup_description()
        return actions

    def interaction_prompt_title(self, _actor=None, _game=None) -> str:
        return "Loot na polu"

    def interaction_prompt_summary(self, _actor=None, _game=None) -> str:
        position = self.position if self.position is not None else "?"
        return f"Pole {position}: {self.loot_summary()}."

    def interaction_prompt_body(self, _actor=None, _game=None) -> str:
        text = render_prompt_text(
            "interaction.loot_pickup_prompt",
            position_text=self.position if self.position is not None else "?",
            loot_summary=self.loot_summary(),
            loot_list=self.loot_details_markdown(),
        )
        return str(
            text.get("body_markdown")
            or f"Na tym polu leży loot:\n{self.loot_details_markdown()}"
        )

    def interaction_prompt_details(self, _actor=None, _game=None) -> str:
        text = render_prompt_text(
            "interaction.loot_pickup_prompt",
            position_text=self.position if self.position is not None else "?",
            loot_summary=self.loot_summary(),
            loot_list=self.loot_details_markdown(),
        )
        return str(text.get("details_markdown") or "")

    def can_interact(self, actor, game) -> bool:
        return bool(self.loot_items)

    def _pickup_handler(self, _interactable, actor, game, _payload) -> str:
        return self.collect(actor, game, allow_prompt=True)

    def collect(self, actor, game, *, allow_prompt: bool = True) -> str:
        if not self.loot_items:
            return "Brak przedmiotów do podniesienia."
        taken = list(self.loot_items)
        self.loot_items.clear()
        item_loot, coin_cp = split_currency(taken)
        hero_items, stash_items = self._choose_pickup_destinations(actor, game, item_loot, allow_prompt=allow_prompt)
        for item in hero_items:
            add_item(actor, item)
        add_party_stash_items(game, stash_items)
        add_party_cp(game, coin_cp)

        labels = item_summary(item_loot, coin_cp)
        self._announce_pickup(actor, game, taken, labels, hero_items=hero_items, stash_items=stash_items, coin_cp=coin_cp)
        if self.position is not None:
            try:
                game.board.remove_interactable(self, self.position)
            except Exception:
                pass
        return f"Podniesiono loot: {labels}."

    def _choose_pickup_destinations(
        self,
        actor,
        game,
        item_loot: list[object],
        *,
        allow_prompt: bool,
    ) -> tuple[list[object], list[object]]:
        remaining = list(item_loot or [])
        hero_items: list[object] = []
        player_prompt = getattr(game, "player_prompt", None)
        if not allow_prompt or player_prompt is None or not hasattr(player_prompt, "choice") or not remaining:
            return [], remaining

        actor_name = getattr(actor, "name", None) or "Bohater"
        while remaining:
            choices: list[str] = []
            choice_meta: list[dict[str, str]] = [
                {
                    "raw": "stash_all",
                    "label": "Zapisz resztę w Party Stash",
                    "desc": "Domyślnie cały niewybrany loot trafia do bezpiecznego magazynu drużyny.",
                    "key": "Enter",
                },
                {
                    "raw": "take_all",
                    "label": f"Weź wszystko do ekwipunku: {actor_name}",
                    "desc": "Wszystkie przedmioty z tej listy trafią bezpośrednio do aktywnego bohatera.",
                    "key": "*",
                },
            ]
            for idx, item in enumerate(remaining):
                label = item_label(item)
                choice_meta.append(
                    {
                        "raw": f"take:{idx}",
                        "label": f"Weź: {label}",
                        "desc": f"{label} trafi bezpośrednio do ekwipunku: {actor_name}. Resztę wybierzesz potem.",
                        "key": str(idx + 1),
                    }
                )
            choices = [entry["label"] for entry in choice_meta]
            body = (
                "**Loot zdobyty**\n"
                f"{item_details_markdown(remaining, 0)}\n\n"
                "**Domyślnie** niewybrane przedmioty trafią do **Party Stash**."
            )
            try:
                answer = player_prompt.choice(
                    "Loot zdobyty",
                    choices=choices,
                    source="loot_pickup",
                    subtitle=f"Możesz od razu wziąć coś dla {actor_name}; reszta trafi do Party Stash.",
                    body_markdown=body,
                    details_markdown=(
                        "Party Stash nie jest dostępny w trakcie walki. "
                        "Po walce otworzysz go przez akcję Ekwipunek."
                    ),
                    choice_meta=choice_meta,
                    scope_key="loot:pickup",
                    dedupe_key=f"loot_pickup_choice:{getattr(self, 'object_id', id(self))}:{len(remaining)}",
                    prompt_id="interaction.loot_pickup_assign",
                )
            except Exception:
                answer = None
            normalized = str(answer or "stash_all").strip().lower()
            if normalized in {"stash_all", "confirm", "ok", ""}:
                break
            if normalized == "take_all":
                hero_items.extend(remaining)
                remaining = []
                break
            if normalized.startswith("take:"):
                try:
                    idx = int(normalized.split(":", 1)[1])
                except Exception:
                    continue
                if 0 <= idx < len(remaining):
                    hero_items.append(remaining.pop(idx))
                continue
            break
        return hero_items, remaining

    def _announce_pickup(
        self,
        actor,
        game,
        taken: list[object],
        summary: str,
        *,
        hero_items: list[object],
        stash_items: list[object],
        coin_cp: int,
    ) -> None:
        player_prompt = getattr(game, "player_prompt", None)
        if player_prompt is None or not hasattr(player_prompt, "card"):
            return
        actor_name = getattr(actor, "name", None) or "Bohater"
        position_text = self.position if self.position is not None else "?"
        destination_rows: list[str] = []
        if hero_items:
            destination_rows.append(f"**Ekwipunek {actor_name}**")
            destination_rows.extend(f"- {item_label(item)}" for item in hero_items)
        if stash_items or coin_cp > 0:
            destination_rows.append("**Party Stash**")
            destination_rows.extend(f"- {item_label(item)}" for item in stash_items)
            if coin_cp > 0:
                destination_rows.append(f"- monety: {format_cp_value(coin_cp)}")
        destination_list = "\n".join(destination_rows) or item_details_markdown([], 0)
        text = render_prompt_text(
            "interaction.loot_pickup_result",
            actor_name=actor_name,
            position_text=position_text,
            loot_summary=summary,
            loot_list=self._details_from(taken),
            destination_list=destination_list,
        )
        try:
            player_prompt.card(
                kind="result",
                title=str(text.get("title") or "Loot podniesiony"),
                summary=str(text.get("summary") or f"{actor_name} podnosi loot."),
                body_markdown=str(
                    text.get("body_markdown")
                    or f"**{actor_name}** podnosi:\n{self._details_from(taken)}"
                ),
                details_markdown=str(text.get("details_markdown") or ""),
                priority="result",
                scope_key="hero_turn:resolution",
                dedupe_key=f"loot_pickup:{getattr(self, 'object_id', id(self))}",
                prompt_id="interaction.loot_pickup_result",
                ack_required=True,
                pause_policy="ack",
            )
        except Exception:
            return


__all__ = [
    "LootPile",
]
