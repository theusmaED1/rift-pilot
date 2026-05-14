"""Estruturas que representam a build recomendada para o campeão."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderResult:
    """Build retornada por um provedor externo (ex.: deeplol.gg).

    Itens vêm como pares `(item_id, nome_localizado)` para que a camada de
    aplicação possa relacionar IDs (preços, inventário) e nomes (TTS).
    `skill_sequence` é a sequência exata por nível: 1=Q, 2=W, 3=E, 4=R.
    """

    starter_items: list[tuple[int, str]] = field(default_factory=list)
    core_items: list[tuple[int, str]] = field(default_factory=list)
    boots: tuple[int, str] | None = None
    runes_primary: str = ""
    runes_secondary: str = ""
    skill_sequence: list[int] = field(default_factory=list)
    source: str = ""


@dataclass(frozen=True)
class RecommendedBuild:
    """Build pronta para consumo pela GUI e pelos detectores."""

    champion: str
    position: str
    starter_items: list[str] = field(default_factory=list)
    core_items: list[str] = field(default_factory=list)
    boots: str = ""
    runes_primary: str = ""
    runes_secondary: str = ""
    skill_priority: list[str] = field(default_factory=list)
    skill_sequence: list[int] = field(default_factory=list)
    source: str = ""
    starter_item_ids: list[int] = field(default_factory=list)
    core_item_ids: list[int] = field(default_factory=list)
    boots_id: int = 0
    quest_item_id: int = 0
    quest_item_name: str = ""
    quest_intermediate_id: int = 0

    @property
    def is_complete(self) -> bool:
        return bool(self.core_items or self.boots or self.starter_items)

    def items_in_purchase_order(self) -> list[tuple[int, str]]:
        """Itens na ordem que devem ser comprados: starters → core."""
        ordered = [
            (iid, name)
            for iid, name in zip(self.starter_item_ids, self.starter_items)
            if iid
        ]
        ordered += [
            (iid, name)
            for iid, name in zip(self.core_item_ids, self.core_items)
            if iid
        ]
        return ordered
