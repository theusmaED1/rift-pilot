"""AI-powered build decisions using Groq and gpt-oss-120b.

A IA recebe pools de itens do OP.GG e a comp inimiga, então:
1. Decide starter considerando o lane_enemy
2. Decide core + botas considerando a comp completa
3. Gera mensagens naturais (variam a cada execução, não são template)
4. Retorna RecommendedBuild com ai_messages preenchido
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from rift_pilot.domain.entities.recommended_build import ProviderResult
from rift_pilot.domain.ports.data_dragon_repository import DataDragonRepository
from rift_pilot.domain.ports.build_provider import BuildProvider

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = "openai/gpt-oss-120b"


def _get_starter_prompt(tone: str = "neutral", mode: str = "simple") -> str:
    """System prompt para decisão de STARTER (lane_enemy only)."""
    tone_instr = {
        "funny": "Use tom descontraído e engraçado. Faça piadas sobre o matchup.",
        "neutral": "Use tom profissional e direto.",
        "serious": "Use tom sério, técnico e focado.",
    }.get(tone, "Use tom profissional.")

    if mode == "explanatory":
        msg_instr = (
            "Mensagem explicando em detalhes por que esse starter foi escolhido "
            "(considerando o matchup, sustain vs dano, tipo de ameaça, etc)."
        )
        explanation_instr = '\nInclua também "explanation": "resumo curto".'
    else:
        msg_instr = (
            "Mensagem curta e natural listando os itens com razão simples (1 frase). "
            "Ex: 'Escudo de Doran e Poção pra sustain contra poke.'"
        )
        explanation_instr = ""

    return (
        f"Você é um especialista em itemização de League of Legends. {tone_instr}\n"
        f"Decida qual STARTER é melhor para este matchup de lane.{explanation_instr}\n"
        "\n"
        "O jogador tem 2 opções de starter (dados reais do OP.GG). "
        "Sua decisão considera APENAS o inimigo de lane.\n"
        "\n"
        "REGRAS:\n"
        "1. Escolha UM dos starter_options.\n"
        "2. Use winrate/games como referência.\n"
        "3. Raciocine sobre o matchup:\n"
        "   - vs ranged/poke? Prefira sustain (Escudo de Doran).\n"
        "   - vs melee/all-in? Considere dano (Anel de Doran).\n"
        "   - vs mage AP? Escudo bloqueia melhor.\n"
        "4. Use nomes EXATOS dos itens.\n"
        "5. NÃO invente itens.\n"
        "\n"
        "FORMATO: JSON puro\n"
        '{"starter": [...], "starter_message": "<mensagem, tom ' + tone + '>"' +
        (', "explanation": "..."' if mode == "explanatory" else "") +
        '}'
    )


def _get_core_boots_prompt(tone: str = "neutral", mode: str = "simple") -> str:
    """System prompt para decisão de CORE + BOTAS (comp completa)."""
    tone_instr = {
        "funny": "Use tom descontraído e engraçado. Faça piadas.",
        "neutral": "Use tom profissional e direto.",
        "serious": "Use tom sério, técnico e focado.",
    }.get(tone, "Use tom profissional.")

    if mode == "explanatory":
        explanation_instr = (
            "\n\nMODO EXPLANATORY:\n"
            "- Mensagens com detalhes de estratégia\n"
            "- Inclua 'explanation' com resumos"
        )
    else:
        explanation_instr = (
            "\n\nMODO SIMPLES:\n"
            "- core_message: apenas ordem, sem detalhe\n"
            "- boots_message: nome + razão em 1 frase"
        )

    return (
        f"Você é um especialista em itemização de League of Legends. {tone_instr}\n"
        f"Decida CORE (ordem) + BOTAS considerando a comp inimiga completa.{explanation_instr}\n"
        "\n"
        "O jogador tem POOLS de itens (OP.GG) e você já sabe o starter.\n"
        "\n"
        "REGRAS CORE:\n"
        "1. core_em_ordem é o default (OP.GG estatística real).\n"
        "2. Só desvie se ganho defensivo/ofensivo for CLARO.\n"
        "3. Máximo: mover UM item. Cite qual ameaça responde.\n"
        "\n"
        "REGRAS BOTAS:\n"
        "1. Escolha UMA de boots_pool.\n"
        "2. Cite resistência mágica/tenacidade APENAS se ameaça AP/CC real.\n"
        "3. Use nomes EXATOS.\n"
        "\n"
        "FORMATO: JSON puro\n"
        '{"core_order": [...], "boots": "<nome exato>", '
        '"core_message": "<mensagem>", "boots_message": "<mensagem>"' +
        (', "explanation": {core: "...", boots: "..."}' if mode == "explanatory" else "") +
        '}'
    )


def _call_groq_json(
    key: str,
    system: str,
    user_payload: dict[str, Any],
) -> tuple[dict[str, Any], int, int]:
    """Call Groq API and return (parsed_json, tokens_in, tokens_out)."""
    body = {
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "reasoning_effort": "low",
    }

    for attempt in range(3):
        resp = httpx.post(
            _GROQ_URL,
            headers={"Authorization": f"Bearer {key}"},
            json=body,
            timeout=40.0,
        )
        if resp.status_code == 429 and attempt < 2:
            time.sleep(20 * (attempt + 1))
            continue
        resp.raise_for_status()

        data = resp.json()
        raw = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        ti = int(usage.get("prompt_tokens", 0))
        to = int(usage.get("completion_tokens", 0))
        parsed = json.loads(raw)
        return parsed, ti, to

    raise RuntimeError("429 persistente após 3 tentativas")


class AiBuildProvider:
    """IA provider — Groq decide starter, core, botas com mensagens naturais.

    Recebe pools do OP.GG e inimigos, e gera decisões + mensagens variadas.
    """

    def __init__(
        self,
        base_provider: BuildProvider,
        data_dragon: DataDragonRepository,
        api_key: str = "",
        tone: str = "neutral",
        mode: str = "simple",
    ):
        """
        Args:
            base_provider: OpggBuildProvider (fonte de pools)
            data_dragon: Para resolução de IDs
            api_key: Chave Groq (fallback: env var GROQ_API_KEY)
            tone: "funny", "neutral", "serious"
            mode: "simple", "explanatory"
        """
        self._base_provider = base_provider
        self._data_dragon = data_dragon
        self._api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self._tone = tone
        self._mode = mode
        self._lane_enemy: dict[str, Any] | None = None
        self._full_comp: list[dict[str, Any]] = []

    def set_enemies(
        self,
        lane_enemy: dict[str, Any] | None,
        full_comp: list[dict[str, Any]],
    ) -> None:
        """Chamado pela CoachSession antes de fetch() com dados de inimigos."""
        self._lane_enemy = lane_enemy
        self._full_comp = full_comp

    def fetch(self, champion_id: int, position: str) -> ProviderResult | None:
        """Fetch pools do OP.GG e decide via Groq."""
        if not self._api_key:
            return self._base_provider.fetch(champion_id, position)

        baseline = self._base_provider.fetch(champion_id, position)
        if baseline is None:
            return None

        try:
            return self._decide_with_groq(baseline, champion_id)
        except Exception:
            return baseline

    def _decide_with_groq(
        self, baseline: ProviderResult, champion_id: int
    ) -> ProviderResult:
        """Executa 2 calls Groq: starter + core/boots."""
        champion_name = self._data_dragon.get_champion_name(champion_id) or "?"

        # Extrair nomes dos pools
        starter_names = [name for _, name in baseline.starter_items]
        core_names = [name for _, name in baseline.core_items]
        boots_name = baseline.boots[1] if baseline.boots else ""

        ai_messages: dict[str, str] = {}

        # ── CALL #1: STARTER ──
        # Se lane_enemy não está disponível, usa um genérico "desconhecido"
        lane_enemy_name = (
            self._lane_enemy.get("championName", "?")
            if self._lane_enemy
            else "inimigo desconhecido"
        )
        payload_starter = {
            "champion": champion_name,
            "lane_enemy": lane_enemy_name,
            "starter_opcoes": [
                {"items": starter_names, "winrate": 50.0, "games": 1000}
            ],
        }
        system_starter = _get_starter_prompt(tone=self._tone, mode=self._mode)
        try:
            parsed_s, _, _ = _call_groq_json(self._api_key, system_starter, payload_starter)
            ai_messages["starter"] = str(parsed_s.get("starter_message", ""))
        except Exception as e:
            import logging
            logging.warning(f"[AiBuildProvider] Erro ao gerar starter message: {e}")

        # ── CALL #2: CORE + BOTAS (full comp) ──
        payload_core = {
            "champion": champion_name,
            "core_em_ordem": core_names,
            "boots_pool": [boots_name] if boots_name else [],
            "campeoes_inimigos": self._full_comp,
        }
        system_core = _get_core_boots_prompt(tone=self._tone, mode=self._mode)
        try:
            parsed_c, _, _ = _call_groq_json(self._api_key, system_core, payload_core)
            ai_messages["core"] = str(parsed_c.get("core_message", ""))
            ai_messages["boots"] = str(parsed_c.get("boots_message", ""))
        except Exception:
            pass

        # ── Retornar baseline com ai_messages preenchido ──
        if ai_messages:
            return ProviderResult(
                starter_items=baseline.starter_items,
                core_items=baseline.core_items,
                boots=baseline.boots,
                runes_primary=baseline.runes_primary,
                runes_secondary=baseline.runes_secondary,
                skill_sequence=baseline.skill_sequence,
                source="ai (" + baseline.source + ")",
                ai_messages=ai_messages,
            )
        return baseline
