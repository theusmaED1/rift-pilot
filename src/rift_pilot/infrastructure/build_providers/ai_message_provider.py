"""Gera mensagens curtas via IA (gpt-oss-20b) para substituir templates fixos.

Usado por NextItemDetector (lembrete/affordable) e FarmDetector (low/behind).
Cada call é independente, ~400 tokens. Fallback para template em caso de falha.
"""
from __future__ import annotations

import logging
from typing import Any

from rift_pilot.infrastructure.groq.router import AllModelsExhausted, GroqRouter
from rift_pilot.settings.messages import TTSMessages

logger = logging.getLogger(__name__)


def _tone_instr(tone: str) -> str:
    return {
        "funny": "Tom descontraído, pode fazer piadas curtas. Mensagem objetiva.",
        "neutral": "Tom profissional, direto e amigável.",
        "serious": "Tom sério, técnico e focado.",
    }.get(tone, "Tom profissional e direto.")


def _short_message_prompt(tone: str) -> str:
    return (
        f"Você é um coach de League of Legends em pt-BR. {_tone_instr(tone)}\n\n"
        "Gere UMA mensagem curta (máx 15 palavras) em português brasileiro para o "
        "jogador ouvir via TTS.\n\n"
        "REGRAS DURAS:\n"
        "1. Use a palavra 'farm' — NUNCA 'CS', 'creep score' ou 'minions mortos'.\n"
        "2. Use APENAS os nomes/números do payload. NÃO invente atributos de "
        "itens (não diga o que um item faz — você pode errar). Apenas cite o "
        "nome do item se ele estiver no payload.\n"
        "3. Não traduza nomes próprios de itens/campeões.\n"
        "4. Varie a forma de falar entre chamadas — não repita a mesma frase.\n\n"
        'FORMATO: JSON {"message": "<texto curto pt-BR>"}'
    )


class AiMessageProvider:
    """Gera mensagens via IA para lembretes de item e feedback de farm.

    Em qualquer falha (Groq, JSON inválido, modelos esgotados), cai para o
    template fixo correspondente — coach continua falando, só perde variação.
    """

    def __init__(self, groq_router: GroqRouter, tone: str = "neutral") -> None:
        self._router = groq_router
        self._tone = tone

    # ── NextItemDetector ─────────────────────────────────────────────────────

    def reminder(
        self,
        item_name: str,
        can_afford: bool,
        missing_boots: str | None,
        following_name: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "tipo": "lembrete_proximo_item",
            "item_atual": item_name,
            "pode_comprar": can_afford,
            "botas_pendente": missing_boots,
            "proximo_item": following_name,
        }
        return self._call_or_fallback(
            payload,
            fallback=lambda: TTSMessages.next_item_reminder(
                item_name, can_afford, missing_boots, following_name
            ),
        )

    def affordable(self, item_name: str, following_name: str | None = None) -> str:
        payload: dict[str, Any] = {
            "tipo": "ouro_suficiente",
            "item_pronto": item_name,
            "proximo_item": following_name,
        }
        return self._call_or_fallback(
            payload,
            fallback=lambda: TTSMessages.gold_reached_for_item(item_name, following_name),
        )

    def boots_reminder(self, boots_name: str) -> str:
        payload: dict[str, Any] = {
            "tipo": "lembrete_de_bota",
            "bota_recomendada": boots_name,
            "instrucao": "Lembre o jogador de comprar botas. Não detalhe atributos.",
        }
        return self._call_or_fallback(
            payload,
            fallback=lambda: TTSMessages.boots_reminder(boots_name),
        )

    # Farm migrou para banco determinístico (TTSMessages._FARM_MESSAGES).
    # Métodos farm_* removidos: IA gerava alucinações ("corte o Cutelo
    # Negro", "Farm alto" contradizendo farm baixo). Ver FarmDetector.

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _call_or_fallback(self, payload: dict[str, Any], fallback) -> str:
        logger.info(
            f"[AiMessageProvider] Gerando mensagem via IA — tipo={payload.get('tipo')!r}"
        )
        try:
            # gpt-oss-20b é modelo de reasoning: gasta tokens "pensando" antes
            # do JSON. max_tokens baixo (ex: 120) causa json_validate_failed
            # (400) quando o reasoning consome o orçamento. 512 dá folga.
            parsed, model, ti, to = self._router.call(
                task_type="reminder",
                system=_short_message_prompt(self._tone),
                user_payload=payload,
                max_tokens=512,
            )
            message = str(parsed.get("message", "")).strip()
            if message:
                logger.info(
                    f"[AiMessageProvider] OK ({model}, ti={ti}, to={to}): {message[:80]}"
                )
                return message
            logger.warning(
                f"[AiMessageProvider] Resposta sem 'message' — fallback. Payload tipo: {payload.get('tipo')}"
            )
        except AllModelsExhausted as e:
            logger.warning(f"[AiMessageProvider] Modelos esgotados, fallback: {e}")
        except Exception as e:
            logger.warning(f"[AiMessageProvider] Falha na call, fallback: {e}")
        return fallback()
