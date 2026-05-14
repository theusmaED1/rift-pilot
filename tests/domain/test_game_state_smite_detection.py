"""Testes da detecção de Punir/Smite em `GameState.from_live_api`."""

from lol_coach.domain.entities.game_state import GameState


def _payload(spell_one_raw: str, spell_two_raw: str = "") -> dict:
    return {
        "gameData": {"gameTime": 0.0},
        "events": {"Events": []},
        "activePlayer": {
            "level": 1,
            "currentGold": 500,
            "abilities": {
                "Q": {"abilityLevel": 0},
                "W": {"abilityLevel": 0},
                "E": {"abilityLevel": 0},
                "R": {"abilityLevel": 0},
            },
            "summonerName": "Tester#BR1",
        },
        "allPlayers": [
            {
                "summonerName": "Tester#BR1",
                "championName": "Ambessa",
                "position": "TOP",
                "items": [],
                "summonerSpells": {
                    "summonerSpellOne": {"rawDisplayName": spell_one_raw},
                    "summonerSpellTwo": {"rawDisplayName": spell_two_raw},
                },
            }
        ],
    }


def test_detects_smite_in_first_slot():
    state = GameState.from_live_api(
        _payload("GeneratedTip_SummonerSpell_SummonerSmite_DisplayName")
    )
    assert state.has_smite is True


def test_detects_smite_in_second_slot():
    state = GameState.from_live_api(
        _payload(
            "GeneratedTip_SummonerSpell_SummonerFlash_DisplayName",
            "GeneratedTip_SummonerSpell_SummonerSmite_DisplayName",
        )
    )
    assert state.has_smite is True


def test_returns_false_when_no_smite_present():
    state = GameState.from_live_api(
        _payload(
            "GeneratedTip_SummonerSpell_SummonerFlash_DisplayName",
            "GeneratedTip_SummonerSpell_SummonerHaste_DisplayName",
        )
    )
    assert state.has_smite is False


def test_falls_back_to_localized_display_name():
    payload = _payload("")
    payload["allPlayers"][0]["summonerSpells"]["summonerSpellOne"] = {
        "rawDisplayName": "",
        "displayName": "Golpear",
    }
    state = GameState.from_live_api(payload)
    assert state.has_smite is True
