"""Testes do `FarmDetector` determinístico (sem IA).

Cobre: emissão de evento com TTL + tag, anti-repetição por janela
deslizante, e robustez do banco para todos os tons/modos.
"""
from __future__ import annotations

import pytest

from rift_pilot.domain.detectors.farm_detector import (
    RECENT_WINDOW,
    FarmDetector,
)
from rift_pilot.domain.entities.abilities import Abilities
from rift_pilot.domain.entities.game_state import GameState
from rift_pilot.domain.entities.state_diff import StateDiff
from rift_pilot.settings.constants import EventTags
from rift_pilot.settings.messages import TTSMessages

_TONES = ("neutral", "funny", "serious", "tryhard", "sarcastic")
_MODES = ("simple", "explanatory")
_CATEGORIES = (
    "farm_low",
    "farm_good",
    "farm_behind",
    "farm_ahead",
    "farm_highest",
)


def _state(gt: float, creep_score: int, position: str = "MIDDLE") -> GameState:
    return GameState(
        game_time_seconds=gt,
        player_level=3,
        abilities=Abilities(q=1, w=0, e=0, r=0),
        current_gold=500.0,
        events=[],
        champion_name="Akali",
        position=position,
        creep_score=creep_score,
    )


def test_message_provider_removido_da_assinatura():
    """FarmDetector não deve mais aceitar message_provider (IA removida)."""
    import inspect

    params = inspect.signature(FarmDetector.__init__).parameters
    assert "message_provider" not in params
    assert "mode" in params


def test_farm_low_emite_evento_deterministico():
    detector = FarmDetector(tone="tryhard", mode="explanatory")
    # Pula o gate de início de farm (chegada de wave em MIDDLE = 52s).
    detector._farm_start_gt = 52.0

    # gt=120s, sem farm: feedback A (farm abaixo do ideal) elegível.
    diff = StateDiff(
        previous=_state(gt=119.0, creep_score=0),
        current=_state(gt=120.0, creep_score=0),
    )
    events = detector.detect(diff)

    assert len(events) == 1
    ev = events[0]
    assert ev.tag == EventTags.FARM
    assert ev.expires_at is not None  # TTL setado
    assert isinstance(ev.message, str) and ev.message
    # Mensagem deve vir do banco determinístico tryhard/explanatory.
    bank = TTSMessages._FARM_MESSAGES["tryhard"]["explanatory"]
    all_low = bank["farm_low"]
    assert ev.message in all_low


def test_anti_repeat_janela_deslizante():
    """Nenhuma frase repete dentro de uma janela de RECENT_WINDOW escolhas."""
    detector = FarmDetector(tone="neutral", mode="simple")
    seen: list[str] = []
    for _ in range(40):
        msg, _prio = detector._farm_low(my_farm=0, ideal_now=10)
        seen.append(msg)

    for i in range(len(seen)):
        window = seen[max(0, i - RECENT_WINDOW):i]
        assert seen[i] not in window, (
            f"Frase repetida dentro da janela em i={i}: {seen[i]!r}"
        )


def test_farm_behind_formata_placeholders():
    detector = FarmDetector(tone="serious", mode="simple")
    msg, _prio = detector._farm_behind(diff_cs=15, enemy_name="Nasus")
    assert "{diff}" not in msg and "{enemy}" not in msg
    assert "15" in msg
    assert "Nasus" in msg


@pytest.mark.parametrize("tone", _TONES)
@pytest.mark.parametrize("mode", _MODES)
@pytest.mark.parametrize("category", _CATEGORIES)
def test_banco_cobre_todas_combinacoes(tone: str, mode: str, category: str):
    """Toda combinação tom×modo×categoria tem >=8 variantes não vazias."""
    template, formatted = TTSMessages._farm_pick(
        category, tone, mode, recent=(), diff=10, enemy="X"
    )
    assert isinstance(template, str) and template
    assert isinstance(formatted, str) and formatted
    variants = TTSMessages._FARM_MESSAGES[tone][mode][category]
    assert len(variants) >= 8, (
        f"{tone}/{mode}/{category} tem só {len(variants)} variantes"
    )


def test_farm_pick_fallback_tom_invalido():
    """Tom inexistente cai para neutral sem estourar."""
    template, formatted = TTSMessages._farm_pick(
        "farm_low", "inexistente", "simple", recent=()
    )
    assert formatted in TTSMessages._FARM_MESSAGES["neutral"]["simple"]["farm_low"]
