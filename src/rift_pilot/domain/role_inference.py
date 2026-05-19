"""Inferência de role/lane combinando posição reportada e summoner spells."""
from __future__ import annotations

_JUNGLE = "JUNGLE"
_UNKNOWN_POSITION_ALIASES = {"", "NONE"}
_ALL_POSITIONS = {"TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"}


def resolve_position_for_build_lookup(
    reported_position: str,
    has_smite: bool,
    team_positions: dict[str, str] | None = None,
) -> str:
    """Devolve a posição que deve ser usada para buscar a build recomendada.

    Quem tem Golpear equipado é selva, sobrepondo a posição reportada. Se a
    Live API disse JUNGLE mas o jogador não tem Golpear, devolve string vazia
    para que o provedor escolha uma lane não-selva.

    Se a posição reportada é NONE/vazia e há dados de outras posições do time,
    tenta inferir por exclusão: qual posição falta no time atual?
    """
    normalized = (reported_position or "").upper()
    if has_smite:
        return _JUNGLE
    if normalized == _JUNGLE:
        return ""

    # Inferência por exclusão: se NONE/vazio e temos dados de aliados
    if normalized in _UNKNOWN_POSITION_ALIASES:
        if team_positions:
            occupied = set(team_positions.values()) - _UNKNOWN_POSITION_ALIASES
            missing = _ALL_POSITIONS - occupied
            if len(missing) == 1:
                return missing.pop()
        return ""

    return normalized
