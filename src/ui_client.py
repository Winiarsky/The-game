import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

import requests

logger = logging.getLogger(__name__)


DEBUG_UNDO_COMMAND = "__debug_undo__"
SESSION_RESET_COMMAND = "__session_reset__"


class UndoRequested(BaseException):
    """Sygnał przerwania bieżącej akcji i cofnięcia do snapshotu debug."""

    def __init__(self, command: str = "undo"):
        self.command = str(command or "undo")
        super().__init__(self.command)


try:
    # Domyślny adres UI można ustawić w src/consts.py (PLAYER_UI_URL).
    from consts import PLAYER_UI_URL as DEFAULT_UI_URL
except Exception:  # pragma: no cover - consts może nie istnieć
    DEFAULT_UI_URL = None  # type: ignore


def _configured_url() -> Optional[str]:
    """Kolejność: zmienna środowiskowa -> consts -> None."""
    return (
        os.environ.get("PLAYER_UI_URL")
        or os.environ.get("PLAYER_UI_BASE_URL")
        or DEFAULT_UI_URL
    )


def _normalize_url(value: Optional[str]) -> Optional[str]:
    """Uzupełnij schemat/port, jeśli brak."""
    if not value:
        return None
    url = value.strip()
    if not url:
        return None
    if "://" not in url:
        url = f"http://{url}"
    parsed = urlsplit(url)
    if not parsed.hostname:
        return url
    port = parsed.port
    scheme = parsed.scheme or "http"
    netloc = parsed.hostname
    if parsed.username:
        netloc = f"{parsed.username}@{netloc}"
    if parsed.password:
        netloc = f"{parsed.username}:{parsed.password}@{parsed.hostname}"
    if port is None:
        # domyślny port UI
        netloc = f"{netloc}:5100"
    else:
        netloc = f"{netloc}:{port}"
    return urlunsplit((scheme, netloc, parsed.path or "", parsed.query, parsed.fragment))


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    for attr in ("object_id", "id", "name"):
        raw = getattr(value, attr, None)
        if raw is not None:
            return str(raw)
    return repr(value)


@dataclass
class UIClient:
    """Minimalny klient HTTP do komunikacji z aplikacją UI graczy."""

    base_url: Optional[str] = None
    poll_interval: float = 0.75
    request_timeout: float = 5.0
    max_wait: Optional[float] = None  # None = czekaj na UI bez limitu; można nadpisać env PLAYER_UI_MAX_WAIT
    enabled: bool = field(init=False)
    allow_cli_fallback: bool = field(init=False, default=False)
    session_id: Optional[str] = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.base_url is None:
            self.base_url = _configured_url()
        self.base_url = _normalize_url(self.base_url)
        self.enabled = bool(self.base_url)
        self.allow_cli_fallback = str(os.environ.get("ALLOW_CLI_FALLBACK", "0")).lower() in ("1", "true", "yes")
        if self.enabled and self.base_url and self.base_url.endswith("/"):
            self.base_url = self.base_url.rstrip("/")
        env_wait = os.environ.get("PLAYER_UI_MAX_WAIT")
        if env_wait is not None:
            try:
                value = float(env_wait)
                if value < 0:
                    self.max_wait = None
                else:
                    self.max_wait = value
            except ValueError:
                logger.warning("PLAYER_UI_MAX_WAIT musi być liczbą (sekundy); ignoruję wartość: %s", env_wait)
        self._ensure_session_id()

    # --- Public API ---

    def send_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Wyślij prosty event do UI (np. log, zmiana stanu)."""
        if not self.enabled:
            return False
        body = {"type": event_type, "payload": _json_safe(payload)}
        session_id = self._ensure_session_id()
        if session_id:
            body["session_id"] = session_id
        try:
            resp = requests.post(
                f"{self.base_url}/api/events",
                json=body,
                timeout=self.request_timeout,
            )
            if resp.status_code == 409:
                logger.warning("Sesja UI dla eventu %s jest nieaktualna; pomijam wysyłkę.", event_type)
                return False
            resp.raise_for_status()
            return True
        except Exception as exc:  # pragma: no cover - tylko logujemy
            logger.warning("Nie udało się wysłać eventu do UI: %s", exc)
            return False

    def prompt_roll(self, prompt: str, source: str | None = None, **extra) -> Optional[Any]:
        """Wyślij prompt na rzut; fallback CLI tylko w trybie debug."""
        return_meta = bool(extra.pop("return_meta", False))
        if self.enabled:
            prompt_id = self._create_prompt(prompt, source=source, **extra)
            if prompt_id is not None:
                ans = self._wait_for_answer(prompt_id, max_wait=self.max_wait)
                if return_meta:
                    return self._normalize_roll_answer(ans)
                parsed = self._coerce_roll_answer_int(ans)
                if parsed is not None:
                    return parsed
        if not self.enabled:
            logger.warning("UI jest wyłączone; prompt_roll bez odpowiedzi.")
        if not self.allow_cli_fallback:
            return None
        fallback = self._prompt_cli_int(prompt)
        if return_meta:
            if fallback is None:
                return None
            return {"roll": int(fallback), "raw_roll": int(fallback), "natural_mode": "none"}
        return fallback

    def prompt_choice(
        self,
        prompt: str,
        choices: list[str] | None = None,
        source: str | None = None,
        **extra,
    ) -> Optional[str]:
        """Wyślij prompt tekstowy z opcjonalną listą wyboru; fallback CLI tylko w debug."""
        if self.enabled:
            prompt_id = self._create_prompt(prompt, kind="choice", source=source, choices=choices, **extra)
            if prompt_id is not None:
                ans = self._wait_for_text_answer(prompt_id, max_wait=self.max_wait)
                if ans is not None:
                    return ans
        if not self.enabled:
            logger.warning("UI jest wyłączone; prompt_choice bez odpowiedzi.")
        if not self.allow_cli_fallback:
            return None
        return self._prompt_cli_choice(prompt, choices)

    def prompt_file_image(
        self,
        title: str = "Wybierz plik portretu",
        *,
        subtitle: str | None = None,
        prompt_long: str | None = None,
        source: str | None = None,
    ) -> Optional[Any]:
        """Prompt do wyboru pliku obrazu w UI (zwraca surową odpowiedź, np. dict z data_url)."""
        if self.enabled:
            prompt_id = self._create_prompt(
                title,
                kind="choice",
                source=source,
                layout="file_image",
                title=title,
                subtitle=subtitle,
                prompt_long=prompt_long,
            )
            if prompt_id is not None:
                return self._wait_for_answer(prompt_id, max_wait=self.max_wait)
        if not self.enabled:
            logger.warning("UI jest wyłączone; prompt_file_image bez odpowiedzi.")
        if not self.allow_cli_fallback:
            return None
        try:
            return input(f"{title} (podaj ścieżkę do pliku): ").strip() or None
        except Exception:
            return None

    def prompt_action_select(
        self,
        title: str = "Wybierz akcję",
        subtitle: str | None = None,
        source: str | None = None,
        image: str | None = None,
        action_desc: str | None = None,
    ) -> Optional[str]:
        """Specjalny prompt na wybór akcji z potwierdzeniem."""
        if self.enabled:
            prompt_id = self._create_prompt(
                title,
                kind="choice",
                source=source,
                layout="action_select",
                title=title,
                subtitle=subtitle,
                image=image,
                action_desc=action_desc,
            )
            if prompt_id is not None:
                ans = self._wait_for_text_answer(prompt_id, max_wait=self.max_wait)
                if ans is not None:
                    return ans
        if not self.enabled:
            logger.warning("UI jest wyłączone; prompt_action_select bez odpowiedzi.")
        if not self.allow_cli_fallback:
            return None
        try:
            return input(f"{title} (wpisz nazwę akcji): ").strip() or None
        except Exception:
            return None

    def prompt_info(
        self,
        title: str,
        *,
        prompt_long: str | None = None,
        source: str | None = None,
        image: str | None = None,
        **extra,
    ) -> Optional[str]:
        """Pokaż informację i poczekaj na potwierdzenie (Enter)."""
        if self.enabled:
            prompt_id = self._create_prompt(
                title,
                kind="info",
                source=source,
                layout="info",
                title=title,
                prompt_long=prompt_long,
                image=image,
                **extra,
            )
            if prompt_id is not None:
                return self._wait_for_text_answer(prompt_id, max_wait=self.max_wait)
        if not self.enabled:
            logger.warning("UI jest wyłączone; prompt_info bez potwierdzenia.")
        if not self.allow_cli_fallback:
            return None
        try:
            input(f"{title} (Enter aby kontynuować) ")
        except Exception:
            return None
        return "ok"

    # --- Helpers ---

    def _create_prompt(
        self,
        prompt: str,
        source: str | None = None,
        kind: str = "roll",
        choices: list[str] | None = None,
        **extra,
    ) -> Optional[str]:
        session_id = self._ensure_session_id()
        payload = {
            "prompt": prompt,
            "kind": kind,
            "source": source,
            "choices": choices or None,
            **extra,
        }
        if session_id:
            payload["session_id"] = session_id
        try:
            resp = requests.post(
                f"{self.base_url}/api/prompts",
                json=payload,
                timeout=self.request_timeout,
            )
            if resp.status_code == 409:
                logger.warning("Sesja UI dla promptu '%s' jest nieaktualna; nie tworzę promptu.", prompt)
                return None
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("id"))
        except Exception as exc:  # pragma: no cover - fallback na CLI
            logger.warning("Nie udało się utworzyć promptu w UI: %s", exc)
            return None

    # --- CLI fallbacks ---

    @staticmethod
    def _prompt_cli_int(prompt: str) -> Optional[int]:
        while True:
            try:
                raw = input(prompt).strip()
            except Exception:
                return None
            if not raw:
                continue
            try:
                return int(raw)
            except ValueError:
                continue

    @staticmethod
    def _prompt_cli_choice(prompt: str, choices: list[str] | None = None) -> Optional[str]:
        if choices:
            print(prompt)
            for idx, ch in enumerate(choices, start=1):
                print(f"{idx}. {ch}")
        try:
            raw = input(prompt + " ").strip()
        except Exception:
            return None
        return raw or None

    @staticmethod
    def _coerce_roll_answer_int(answer: Any) -> Optional[int]:
        if isinstance(answer, int):
            return int(answer)
        if isinstance(answer, float):
            return int(answer)
        if isinstance(answer, dict):
            for key in ("roll", "raw_roll", "value", "result"):
                if key not in answer:
                    continue
                try:
                    return int(answer.get(key))
                except (TypeError, ValueError):
                    continue
            return None
        try:
            return int(answer)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_roll_answer(answer: Any) -> dict[str, Any]:
        if isinstance(answer, dict):
            roll = UIClient._coerce_roll_answer_int(answer)
            raw_roll = UIClient._coerce_roll_answer_int(answer.get("raw_roll", roll))
            mode = answer.get("natural_mode", answer.get("natural", answer.get("nat", "none")))
            out: dict[str, Any] = {
                "roll": int(roll or 0),
                "raw_roll": int(raw_roll or 0),
                "natural_mode": str(mode or "none"),
            }
            for key in ("natural_shift", "modifier_delta", "computed_total"):
                if key not in answer:
                    continue
                try:
                    out[key] = int(answer.get(key) or 0)
                except (TypeError, ValueError):
                    pass
            if "roll_stack_values" in answer and isinstance(answer.get("roll_stack_values"), list):
                out["roll_stack_values"] = list(answer.get("roll_stack_values") or [])
            return out
        roll = UIClient._coerce_roll_answer_int(answer)
        return {"roll": int(roll or 0), "raw_roll": int(roll or 0), "natural_mode": "none"}

    @staticmethod
    def _debug_undo_response_for_source(answer: Any, payload: dict[str, Any]) -> str | None:
        """Dla kreatora postaci mapuj globalne cofnij na lokalny krok wstecz."""
        if str(answer).strip().lower() != DEBUG_UNDO_COMMAND:
            return None
        source = str(payload.get("source") or "").strip().lower()
        if source == "character_creation":
            return "/back"
        return None

    def _ensure_session_id(self) -> Optional[str]:
        if not self.enabled or not self.base_url:
            return None
        if self.session_id:
            return self.session_id
        try:
            resp = requests.get(
                f"{self.base_url}/api/session",
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            session = data.get("session") if isinstance(data, dict) else None
            if isinstance(session, dict):
                raw = session.get("id")
            else:
                raw = data.get("session_id") if isinstance(data, dict) else None
            session_id = str(raw or "").strip()
            if session_id:
                self.session_id = session_id
        except Exception as exc:
            logger.debug("Nie udało się ustalić sesji UI: %s", exc)
        return self.session_id

    def _wait_for_answer(self, prompt_id: str, *, max_wait: Optional[float] = None) -> Any:
        url = f"{self.base_url}/api/prompts/{prompt_id}"
        start = time.time()
        while True:
            try:
                resp = requests.get(url, timeout=self.request_timeout)
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") == "answered":
                    answer = data.get("answer")
                    if str(answer).strip().lower() == SESSION_RESET_COMMAND:
                        logger.info("Prompt %s zamknięty przez reset sesji UI.", prompt_id)
                        return None
                    mapped = self._debug_undo_response_for_source(answer, data if isinstance(data, dict) else {})
                    if mapped is not None:
                        return mapped
                    if str(answer).strip().lower() == DEBUG_UNDO_COMMAND:
                        raise UndoRequested("undo")
                    return answer
            except UndoRequested:
                raise
            except Exception as exc:  # pragma: no cover - fallback na CLI
                logger.warning("Błąd podczas oczekiwania na odpowiedź UI: %s", exc)
                return None
            if max_wait is not None and (time.time() - start) >= max_wait:
                logger.warning("UI nie odpowiedziało na prompt %s w %ss – wracam do CLI.", prompt_id, max_wait)
                return None
            time.sleep(self.poll_interval)

    def _wait_for_text_answer(self, prompt_id: str, *, max_wait: Optional[float] = None) -> Optional[str]:
        url = f"{self.base_url}/api/prompts/{prompt_id}"
        start = time.time()
        while True:
            try:
                resp = requests.get(url, timeout=self.request_timeout)
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") == "answered":
                    answer = data.get("answer")
                    if str(answer).strip().lower() == SESSION_RESET_COMMAND:
                        logger.info("Prompt %s zamknięty przez reset sesji UI.", prompt_id)
                        return None
                    mapped = self._debug_undo_response_for_source(answer, data if isinstance(data, dict) else {})
                    if mapped is not None:
                        return mapped
                    if str(answer).strip().lower() == DEBUG_UNDO_COMMAND:
                        raise UndoRequested("undo")
                    return str(answer) if answer is not None else None
            except UndoRequested:
                raise
            except Exception as exc:  # pragma: no cover
                logger.warning("Błąd podczas oczekiwania na odpowiedź UI: %s", exc)
                return None
            if max_wait is not None and (time.time() - start) >= max_wait:
                logger.warning("UI nie odpowiedziało na prompt %s w %ss – wracam do CLI.", prompt_id, max_wait)
                return None
            time.sleep(self.poll_interval)


_default_client: Optional[UIClient] = None


def get_ui_client() -> UIClient:
    """Zwróć singleton klienta UI (tworzy się tylko przy pierwszym wywołaniu)."""
    global _default_client
    if _default_client is None:
        _default_client = UIClient()
    return _default_client


def set_default_ui_client(client: UIClient) -> None:
    """Ustaw domyślnego klienta UI (np. gdy uruchamiasz UI z kodu)."""
    global _default_client
    _default_client = client
