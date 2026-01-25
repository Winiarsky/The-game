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
    enabled: bool = field(init=False)

    def __post_init__(self) -> None:
        if self.base_url is None:
            self.base_url = _configured_url()
        self.base_url = _normalize_url(self.base_url)
        self.enabled = bool(self.base_url)
        if self.enabled and self.base_url and self.base_url.endswith("/"):
            self.base_url = self.base_url.rstrip("/")

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

    def prompt_roll(self, prompt: str, source: str | None = None) -> Optional[int]:
        """Wyślij prompt na rzut i poczekaj na odpowiedź z UI."""
        if not self.enabled:
            return None
        prompt_id = self._create_prompt(prompt, source=source)
        if prompt_id is None:
            return None
        return self._wait_for_answer(prompt_id)

    def prompt_choice(
        self, prompt: str, choices: list[str] | None = None, source: str | None = None
    ) -> Optional[str]:
        """Wyślij prompt tekstowy z opcjonalną listą wyboru, zwróć odpowiedź."""
        if not self.enabled:
            return None
        prompt_id = self._create_prompt(prompt, kind="choice", source=source, choices=choices)
        if prompt_id is None:
            return None
        return self._wait_for_text_answer(prompt_id)

    # --- Helpers ---

    def _create_prompt(
        self,
        prompt: str,
        source: str | None = None,
        kind: str = "roll",
        choices: list[str] | None = None,
    ) -> Optional[str]:
        try:
            resp = requests.post(
                f"{self.base_url}/api/prompts",
                json={
                    "prompt": prompt,
                    "kind": kind,
                    "source": source,
                    "choices": choices or None,
                },
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("id"))
        except Exception as exc:  # pragma: no cover - fallback na CLI
            logger.warning("Nie udało się utworzyć promptu w UI: %s", exc)
            return None

    def _wait_for_answer(self, prompt_id: str) -> Optional[int]:
        url = f"{self.base_url}/api/prompts/{prompt_id}"
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
            time.sleep(self.poll_interval)

    def _wait_for_text_answer(self, prompt_id: str) -> Optional[str]:
        url = f"{self.base_url}/api/prompts/{prompt_id}"
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
            time.sleep(self.poll_interval)


_default_client: Optional[UIClient] = None


def get_ui_client() -> UIClient:
    """Zwróć singleton klienta UI (tworzy się tylko przy pierwszym wywołaniu)."""
    global _default_client
    if _default_client is None:
        _default_client = UIClient()
    return _default_client
