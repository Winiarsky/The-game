from __future__ import annotations

from typing import Any

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from skills import Skill


_VOICEOVER_BASE = "audio/voiceover/"


class BoundSmugglerNPC(BaseNPC):
    """Związany przemytnik z dialogiem benchmarkowym dla Bandit Cave."""

    def __init__(
        self,
        *,
        name: str = 'Marek "Lina" Voss',
        npc_id: str = "marek_bound_smuggler",
        cache_map_id: str = "treasure_room",
        cache_id: str = "upper_smuggler_cache",
        diplomacy_dc: int = 16,
        intimidation_dc: int = 15,
        deception_dc: int = 17,
        insight_dc: int = 15,
        stop_escape_dc: int = 16,
        **kwargs: Any,
    ) -> None:
        self.npc_id = str(npc_id or "marek_bound_smuggler").strip()
        self.cache_map_id = str(cache_map_id or "treasure_room").strip()
        self.cache_id = str(cache_id or "upper_smuggler_cache").strip()
        self.diplomacy_dc = int(diplomacy_dc or 16)
        self.intimidation_dc = int(intimidation_dc or 15)
        self.deception_dc = int(deception_dc or 17)
        self.insight_dc = int(insight_dc or 15)
        self.stop_escape_dc = int(stop_escape_dc or 16)
        super().__init__(
            name=name,
            enable_talk=False,
            enable_trade=False,
            enable_pickpocket=False,
            enable_diplomacy=False,
            blocks_movement=False,
            allow_same_cell_interact=True,
            require_same_cell_interact=False,
            **kwargs,
        )
        self.bound = True
        self.cooperative = False
        self.cache_revealed = False
        self.lie_detected = False
        self.escape_attempted = False
        self.escape_stopped = False
        self.actions.clear()
        self.register_default_actions()

    def can_interact(self, actor, game) -> bool:
        state = getattr(game, "state", None)
        return getattr(state.__class__, "__name__", "") != "Combat"

    def interaction_prompt_title(self, _actor=None, _game=None) -> str:
        return f"Rozmowa: {self.name}"

    def interaction_prompt_summary(self, _actor=None, _game=None) -> str:
        if self.bound:
            return "Związany jeniec przy pomoście."
        if self.cooperative:
            return "Uwolniony przemytnik pilnuje rąk z daleka od cum."
        return "Uwolniony przemytnik nerwowo zerka na łódź."

    def interaction_prompt_body(self, _actor=None, _game=None) -> str:
        if self.bound:
            return (
                "Przy pomoście siedzi związany człowiek w mokrym płaszczu. "
                "Ma rozciętą wargę, ale patrzy zbyt przytomnie jak na bezradną ofiarę.\n\n"
                '"Rozwiążcie mnie, a powiem wam, gdzie trzymają prawdziwy łup."'
            )
        return (
            "Marek rozciera nadgarstki. Próbuje brzmieć wdzięcznie, ale ciągle sprawdza, "
            "czy ktoś pilnuje łodzi."
        )

    def interaction_prompt_audio(self, _actor=None, _game=None) -> str:
        if self.bound:
            return f"{_VOICEOVER_BASE}npc_marek_bound_intro_001.mp3"
        if self.escape_attempted and not self.escape_stopped and not self.cooperative:
            return f"{_VOICEOVER_BASE}npc_marek_loose_at_boat_001.mp3"
        return f"{_VOICEOVER_BASE}npc_marek_untied_cooperative_001.mp3"

    def interaction_result_audio(self, action_id: str | None, message: str | None = None) -> str | None:
        action = str(action_id or "").strip()
        text = str(message or "").strip().lower()
        mapping = {
            "ask_identity": "npc_marek_identity_001.mp3",
        }
        if action in mapping:
            return f"{_VOICEOVER_BASE}{mapping[action]}"
        if action == "ask_cache":
            filename = (
                "npc_marek_reveals_cache_001.mp3"
                if self.cache_revealed or "powtarza" in text
                else "npc_marek_cache_bargain_001.mp3"
            )
            return f"{_VOICEOVER_BASE}{filename}"
        if action in {"diplomacy_cache", "intimidate_cache", "deceive_cache"}:
            if "zdradza skrytkę" in text or "skrytka będzie jawna" in text:
                return f"{_VOICEOVER_BASE}npc_marek_reveals_cache_001.mp3"
            if action == "diplomacy_cache":
                return f"{_VOICEOVER_BASE}npc_marek_diplomacy_fail_001.mp3"
            if action == "intimidate_cache":
                return f"{_VOICEOVER_BASE}npc_marek_intimidation_fail_001.mp3"
            return f"{_VOICEOVER_BASE}npc_marek_deception_fail_001.mp3"
        if action == "read_motive":
            filename = (
                "npc_marek_motive_read_001.mp3"
                if "nie jest ofiarą" in text
                else ""
            )
            if not filename:
                return None
            return f"{_VOICEOVER_BASE}{filename}"
        if action == "untie":
            if "już odwiązany" in text:
                return None
            if "trzyma ręce widocznie" in text:
                return f"{_VOICEOVER_BASE}npc_marek_untied_cooperative_001.mp3"
            if "groźba zatrzymuje" in text:
                return f"{_VOICEOVER_BASE}npc_marek_escape_stopped_intimidation_001.mp3"
            if "zmyłka działa" in text:
                return f"{_VOICEOVER_BASE}npc_marek_escape_stopped_deception_001.mp3"
            if "wyrywa się" in text:
                return f"{_VOICEOVER_BASE}npc_marek_escape_attempt_001.mp3"
        return None

    def register_default_actions(self) -> None:
        for interaction in (
            Interaction(
                id="ask_identity",
                label="Kim jesteś?",
                description="Wypytaj Marka o rolę w dokach.",
                handler=type(self).action_ask_identity,
                end_interaction=False,
            ),
            Interaction(
                id="ask_cache",
                label="Co wiesz o skrytce?",
                description="Zapytaj o ukryty łup na górze.",
                handler=type(self).action_ask_cache,
                end_interaction=False,
            ),
            Interaction(
                id="diplomacy_cache",
                label="Przekonaj go",
                description=f"Diplomacy DC {self.diplomacy_dc}: obietnica uczciwego traktowania.",
                handler=type(self).action_diplomacy_cache,
                end_interaction=False,
                tags=["diplomacy", "social"],
            ),
            Interaction(
                id="intimidate_cache",
                label="Zastrasz go",
                description=f"Intimidation DC {self.intimidation_dc}: wymuś informacje.",
                handler=type(self).action_intimidate_cache,
                end_interaction=False,
                tags=["intimidation", "social"],
            ),
            Interaction(
                id="deceive_cache",
                label="Udawaj przemytnika",
                description=f"Deception DC {self.deception_dc}: podaj się za odbiorcę kontrabandy.",
                handler=type(self).action_deceive_cache,
                end_interaction=False,
                tags=["deception", "social"],
            ),
            Interaction(
                id="read_motive",
                label="Złap go na kłamstwie",
                description=f"Society DC {self.insight_dc}: oceń, czy Marek gra na czas.",
                handler=type(self).action_read_motive,
                end_interaction=False,
                tags=["society", "social"],
            ),
            Interaction(
                id="untie",
                label="Odwiąż go",
                description="Uwolnij Marka. Jeśli mu nie ufasz, może spróbować numeru z łodzią.",
                handler=type(self).action_untie,
                end_interaction=False,
            ),
            Interaction(
                id="leave",
                label="Zakończ",
                description="Zakończ rozmowę.",
                handler=lambda *_args, **_kwargs: "Kończysz rozmowę z Markiem.",
            ),
        ):
            self.register_action(interaction)

    def _session(self, game):
        return getattr(game, "scenario_session", None)

    def _set_flag(self, game, flag: str, value: Any = True) -> None:
        session = self._session(game)
        if session is not None:
            try:
                session.global_flags[str(flag)] = value
                return
            except Exception:
                pass
        try:
            flags = getattr(game, "scenario_flags", {})
            flags[str(flag)] = value
            setattr(game, "scenario_flags", flags)
        except Exception:
            pass

    def _check(self, *, actor, game, skill_id: str, dc: int, tags: list[str]):
        return resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=dc,
            actor=actor,
            target=self,
            tags=tags,
            game=game,
            apply_modifiers=True,
        )

    @staticmethod
    def _passed(outcome: object) -> bool:
        return str(outcome or "").strip() in {"success", "critical_success"}

    def _reveal_cache(self, game, *, reason: str) -> str:
        if self.cache_revealed:
            return "Marek już wskazał położenie skrytki."
        self.cache_revealed = True
        self.cooperative = True
        self._set_flag(game, "upper_cache_revealed", True)
        self._set_flag(game, "upper_cache_revealed_by_marek", True)
        session = self._session(game)
        if session is not None:
            revealer = getattr(session, "reveal_object", None)
            if callable(revealer):
                revealer(
                    self.cache_map_id,
                    self.cache_id,
                    state_updates={
                        "hidden": False,
                        "revealed": True,
                        "trap_armed": False,
                        "revealed_by_marek": True,
                        "revealed_by_seek": False,
                    },
                    message=(
                        "Marek wskazuje skrytkę w górnym skarbcu. "
                        "Mechanizm pułapki da się ominąć, jeśli otworzysz panel od strony zawiasu."
                    ),
                )
        return (
            f"{reason} Marek zdradza skrytkę w skarbcu na górze. "
            "Gdy wejdziesz do skarbca, skrytka będzie jawna i możliwa do normalnej interakcji."
        )

    def action_ask_identity(self, _actor, _game, _payload=None) -> str:
        return (
            '"Marek Voss. Pilot. Oni mówią na mnie Lina, bo znam każdy węzeł i każdą mieliznę." '
            "Nie brzmi jak przypadkowy więzień. Bardziej jak ktoś, kto wybrał złą stronę interesu."
        )

    def action_ask_cache(self, _actor, _game, _payload=None) -> str:
        if self.cache_revealed:
            return "Marek powtarza: skrytka jest w górnym skarbcu, przy kontrabandowych księgach."
        return (
            '"Najpierw liny. Potem sekret." Marek uśmiecha się krzywo. '
            "Wygląda, jakby próbował sprzedać wam informację dwa razy."
        )

    def action_diplomacy_cache(self, actor, game, _payload=None) -> str:
        result = self._check(
            actor=actor,
            game=game,
            skill_id=Skill.DIPLOMACY.value,
            dc=self.diplomacy_dc,
            tags=[Skill.DIPLOMACY.value, "social", "make_an_impression"],
        )
        if self._passed(getattr(result, "outcome", None)):
            return self._reveal_cache(game, reason=f"Udana perswazja ({result.outcome}).")
        return f"Marek nie kupuje obietnic. Wynik: {getattr(result, 'outcome', 'failure')}."

    def action_intimidate_cache(self, actor, game, _payload=None) -> str:
        result = self._check(
            actor=actor,
            game=game,
            skill_id=Skill.INTIMIDATION.value,
            dc=self.intimidation_dc,
            tags=[Skill.INTIMIDATION.value, "social", "coerce"],
        )
        if self._passed(getattr(result, "outcome", None)):
            self.cooperative = str(getattr(result, "outcome", "")) == "critical_success"
            return self._reveal_cache(game, reason=f"Zastraszenie działa ({result.outcome}).")
        return f"Marek zaciska szczękę i patrzy na łódź. Wynik: {getattr(result, 'outcome', 'failure')}."

    def action_deceive_cache(self, actor, game, _payload=None) -> str:
        result = self._check(
            actor=actor,
            game=game,
            skill_id=Skill.DECEPTION.value,
            dc=self.deception_dc,
            tags=[Skill.DECEPTION.value, "social", "impersonate", "smuggler"],
        )
        if self._passed(getattr(result, "outcome", None)):
            return self._reveal_cache(game, reason=f"Blef przechodzi ({result.outcome}).")
        self.escape_attempted = True
        return (
            f"Marek rozpoznaje blef ({getattr(result, 'outcome', 'failure')}) i zaczyna grać na czas. "
            "Jeśli go teraz odwiążesz, spróbuje dostać się do łodzi."
        )

    def action_read_motive(self, actor, game, _payload=None) -> str:
        result = self._check(
            actor=actor,
            game=game,
            skill_id=Skill.SOCIETY.value,
            dc=self.insight_dc,
            tags=[Skill.SOCIETY.value, "social", "sense_motive", "smuggler"],
        )
        if self._passed(getattr(result, "outcome", None)):
            self.lie_detected = True
            return (
                f"Rozgryzasz go ({result.outcome}). Marek nie jest ofiarą, tylko pilotem przemytników. "
                "Po odwiązaniu może spróbować odbić łódź, jeśli nie macie nad nim kontroli."
            )
        return f"Nie łapiesz pełnego obrazu. Wynik: {getattr(result, 'outcome', 'failure')}."

    def action_untie(self, actor, game, _payload=None) -> str:
        if not self.bound:
            return "Marek jest już odwiązany."
        self.bound = False
        self._set_flag(game, "dock_prisoner_freed", True)
        if self.cooperative or self.cache_revealed or self.lie_detected:
            self._set_flag(game, "dock_prisoner_cooperative", bool(self.cooperative or self.cache_revealed))
            return "Odwiązujesz Marka. Trzyma ręce widocznie i nie zbliża się do cum."

        self.escape_attempted = True
        self._set_flag(game, "dock_prisoner_escape_attempt", True)
        ui = getattr(game, "ui", None)
        answer = None
        if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_choice"):
            answer = ui.prompt_choice(
                "Marek rzuca się do łodzi",
                choices=["intimidation", "deception", "let_go"],
                source="bound_smuggler",
                prompt_long=(
                    "Gdy tylko liny spadają, Marek szarpie się w stronę cumy. "
                    "Możesz spróbować zatrzymać go głosem albo puścić."
                ),
                choice_meta=[
                    {
                        "raw": "intimidation",
                        "label": "Zatrzymaj groźbą",
                        "desc": f"Intimidation DC {self.stop_escape_dc}.",
                        "key": "1",
                    },
                    {
                        "raw": "deception",
                        "label": "Zmyłka",
                        "desc": f"Deception DC {self.stop_escape_dc}.",
                        "key": "2",
                    },
                    {"raw": "let_go", "label": "Puść go", "desc": "Pozwól mu dobiec do łodzi.", "key": "3"},
                ],
            )
        choice = str(answer or "let_go").strip().lower()
        if choice in {"intimidation", "zatrzymaj groźbą", "zatrzymaj grozba"}:
            result = self._check(
                actor=actor,
                game=game,
                skill_id=Skill.INTIMIDATION.value,
                dc=self.stop_escape_dc,
                tags=[Skill.INTIMIDATION.value, "social", "stop_escape"],
            )
            if self._passed(getattr(result, "outcome", None)):
                self.escape_stopped = True
                self._set_flag(game, "dock_prisoner_escape_stopped", True)
                return f"Groźba zatrzymuje Marka ({result.outcome}). Odsuwa się od łodzi."
        if choice in {"deception", "zmyłka", "zmylka"}:
            result = self._check(
                actor=actor,
                game=game,
                skill_id=Skill.DECEPTION.value,
                dc=self.stop_escape_dc,
                tags=[Skill.DECEPTION.value, "social", "stop_escape"],
            )
            if self._passed(getattr(result, "outcome", None)):
                self.escape_stopped = True
                self._set_flag(game, "dock_prisoner_escape_stopped", True)
                return f"Zmyłka działa ({result.outcome}). Marek traci tempo i zostaje przy pomoście."
        self._set_flag(game, "dock_prisoner_loose", True)
        return "Marek wyrywa się w stronę łodzi. Nie odpływa jeszcze, ale statek przestaje być bezpiecznie zabezpieczony."


META = GameObjectMeta(
    object_id="bound_smuggler_npc",
    label='Związany przemytnik',
    color="#7c5c45",
    category="NPC",
    placement="cell",
    description="Związany pilot przemytników z dialogiem i testami społecznymi.",
    logic_cls=BoundSmugglerNPC,
    default_config={
        "name": 'Marek "Lina" Voss',
        "npc_id": "marek_bound_smuggler",
        "cache_map_id": "treasure_room",
        "cache_id": "upper_smuggler_cache",
        "diplomacy_dc": 16,
        "intimidation_dc": 15,
        "deception_dc": 17,
        "insight_dc": 15,
        "stop_escape_dc": 16,
    },
)
