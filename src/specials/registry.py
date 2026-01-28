from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Special:
    """Definicja zdolności specjalnej."""

    slug: str
    name: str
    aliases: list[str]
    description: str | None
    image: str | None
    execute: Callable[[object, object], bool | None]  # (hero, ctx) -> bool (False = nie zużyto akcji)


_SPECIALS: Dict[str, Special] = {}
_ALIASES: Dict[str, str] = {}


def _normalize(name: str) -> str:
    return name.strip().lower()


def register_special(
    slug: str,
    *,
    name: str | None = None,
    aliases: Optional[List[str]] = None,
    description: str | None = None,
    image: str | None = None,
):
    """Dekorator rejestrujący funkcję zdolności."""

    def decorator(func: Callable[[object, object], bool | None]) -> Callable[[object, object], bool | None]:
        key = _normalize(slug)
        if key in _SPECIALS:
            raise ValueError(f"Zdolność '{slug}' jest już zarejestrowana.")
        effective_name = name or slug
        alias_list = [key]
        for alias in aliases or []:
            norm = _normalize(alias)
            alias_list.append(norm)
        special = Special(
            slug=key,
            name=effective_name,
            aliases=alias_list,
            description=description,
            image=image,
            execute=func,
        )
        _SPECIALS[key] = special
        for alias in alias_list:
            _ALIASES[alias] = key
        return func

    return decorator


def get_special(name: str) -> Special:
    norm = _normalize(name)
    try:
        slug = _ALIASES[norm]
        return _SPECIALS[slug]
    except KeyError as exc:
        available = ", ".join(sorted(_SPECIALS))
        raise KeyError(f"Nieznana zdolność '{name}'. Dostępne: {available}") from exc


def list_specials() -> Dict[str, Special]:
    return dict(_SPECIALS)


def list_all_names() -> list[str]:
    """Zwraca wszystkie aliasy/slugi, które można wpisać."""
    return list(_ALIASES.keys())
