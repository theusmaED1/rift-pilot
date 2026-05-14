"""Inferência de role/lane combinando posição reportada e summoner spells."""
from __future__ import annotations

_JUNGLE = "JUNGLE"
_UNKNOWN_POSITION_ALIASES = {"", "NONE"}


def resolve_position_for_build_lookup(reported_position: str, has_smite: bool) -> str:
    """Devolve a posição que deve ser usada para buscar a build recomendada.

    Quem tem Golpear equipado é selva, sobrepondo a posição reportada. Se a
    Live API disse JUNGLE mas o jogador não tem Golpear, devolve string vazia
    para que o provedor escolha uma lane não-selva.
    """
    normalized = (reported_position or "").upper()
    if has_smite:
        return _JUNGLE
    if normalized == _JUNGLE:
        return ""
    if normalized in _UNKNOWN_POSITION_ALIASES:
        return ""
    return normalized
