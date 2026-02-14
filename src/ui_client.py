import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

import requests

logger = logging.getLogger(__name__)


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


@dataclass
class UIClient:
    """Minimalny klient HTTP do komunikacji z aplikacją UI graczy."""

    base_url: Optional[str] = None
    poll_interval: float = 0.75
    request_timeout: float = 5.0
    max_wait: Optional[float] = None  # None = czekaj na UI bez limitu; można nadpisać env PLAYER_UI_MAX_WAIT
    enabled: bool = field(init=False)

    def __post_init__(self) -> None:
        if self.base_url is None:
            self.base_url = _configured_url()
        self.base_url = _normalize_url(self.base_url)
        self.enabled = bool(self.base_url)
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

    # --- Public API ---

    def send_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        """Wyślij prosty event do UI (np. log, zmiana stanu)."""
        if not self.enabled:
            return False
        try:
            resp = requests.post(
                f"{self.base_url}/api/events",
                json={"type": event_type, "payload": payload},
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:  # pragma: no cover - tylko logujemy
            logger.warning("Nie udało się wysłać eventu do UI: %s", exc)
            return False

    def prompt_roll(self, prompt: str, source: str | None = None, **extra) -> Optional[int]:
        """Wyślij prompt na rzut; jeśli UI wyłączone lub błąd – fallback na CLI."""
        if self.enabled:
            prompt_id = self._create_prompt(prompt, source=source, **extra)
            if prompt_id is not None:
                ans = self._wait_for_answer(prompt_id, max_wait=self.max_wait)
                if isinstance(ans, int):
                    return ans
        # fallback CLI
        return self._prompt_cli_int(prompt)

    def prompt_choice(
        self,
        prompt: str,
        choices: list[str] | None = None,
        source: str | None = None,
        **extra,
    ) -> Optional[str]:
        """Wyślij prompt tekstowy z opcjonalną listą wyboru; fallback na CLI."""
        if self.enabled:
            prompt_id = self._create_prompt(prompt, kind="choice", source=source, choices=choices, **extra)
            if prompt_id is not None:
                ans = self._wait_for_text_answer(prompt_id, max_wait=self.max_wait)
                if ans is not None:
                    return ans
        return self._prompt_cli_choice(prompt, choices)

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
        # fallback na prosty input
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
            )
            if prompt_id is not None:
                return self._wait_for_text_answer(prompt_id, max_wait=self.max_wait)
        # fallback CLI
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
        try:
            resp = requests.post(
                f"{self.base_url}/api/prompts",
                json={
                    "prompt": prompt,
                    "kind": kind,
                    "source": source,
                    "choices": choices or None,
                    **extra,
                },
                timeout=self.request_timeout,
            )
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

    def _wait_for_answer(self, prompt_id: str, *, max_wait: Optional[float] = None) -> Optional[int]:
        url = f"{self.base_url}/api/prompts/{prompt_id}"
        start = time.time()
        while True:
            try:
                resp = requests.get(url, timeout=self.request_timeout)
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") == "answered":
                    answer = data.get("answer")
                    try:
                        return int(answer)
                    except (TypeError, ValueError):
                        logger.warning("Odpowiedź UI nie jest liczbą całkowitą: %s", answer)
                        return None
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
                    return str(answer) if answer is not None else None
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
