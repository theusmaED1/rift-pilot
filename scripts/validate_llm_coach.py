"""Harness descartável de validação: o Gemini Flash (tier grátis) dá dica boa?

NÃO faz parte do produto. Único objetivo: responder ao portão de decisão —
um modelo barato, alimentado com o estado que a API pública expõe, produz
dica tática acionável o suficiente pra sustentar um produto pago?

Uso:

    $env:GEMINI_API_KEY = "sua-key"
    python scripts/validate_llm_coach.py

Gera `recordings/validation_<replay>.md` (pasta já ignorada pelo git) com,
por amostra: tempo de jogo, resumo do estado, dica do LLM e uma coluna de
nota em branco pra avaliação cega. No fim: contagens, tokens reais medidos
e custo estimado por partida.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

# --- Preços (VERIFIQUE antes de citar como verdade) -------------------------
# Gemini 2.5 Flash, tabela paga aproximada (USD por 1M tokens). O tier grátis
# custa 0; estes valores existem só pra responder "quanto custaria SE pago".
PRICE_INPUT_PER_1M_USD = 0.30
PRICE_OUTPUT_PER_1M_USD = 2.50
USD_TO_BRL = 5.30

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

SYSTEM_INSTRUCTION = (
    "Você é um coach de voz de League of Legends que fala durante a partida. "
    "Recebe o estado atual do jogo em JSON. Responda com UMA única frase curta, "
    "imperativa, em português do Brasil, com a ação mais útil para o jogador "
    "AGORA. Sem markdown, sem saudação, sem explicação. Se neste instante não "
    "houver nada realmente acionável, responda exatamente com um único traço: —"
)


class _QuotaExhausted(Exception):
    """Cota diária do tier grátis acabou — esperar não resolve hoje."""


@dataclass
class Sample:
    game_time: float
    state_summary: str
    tip: str
    prompt_tokens: int
    output_tokens: int
    error: str = ""


def _mmss(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _build_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Extrai do payload cru o contexto compacto que o coach veria.

    Direto do payload (e não via GameState) de propósito: o que o modelo
    enxerga É a IP em teste — quero controle total do recorte.
    """
    active = payload.get("activePlayer", {}) or {}
    game_data = payload.get("gameData", {}) or {}
    all_players = payload.get("allPlayers", []) or []
    game_time = float(game_data.get("gameTime", 0.0))

    active_name = active.get("riotId") or active.get("summonerName", "")

    def brief(p: dict[str, Any]) -> dict[str, Any]:
        sc = p.get("scores", {}) or {}
        return {
            "champ": p.get("championName", "?"),
            "lvl": p.get("level", 0),
            "kda": f"{sc.get('kills',0)}/{sc.get('deaths',0)}/{sc.get('assists',0)}",
        }

    my_team = next(
        (p.get("team") for p in all_players
         if (p.get("riotId") or p.get("summonerName", "")) == active_name),
        None,
    )
    me: dict[str, Any] = {}
    allies: list[dict[str, Any]] = []
    enemies: list[dict[str, Any]] = []
    for p in all_players:
        pid = p.get("riotId") or p.get("summonerName", "")
        if pid == active_name:
            me = {
                **brief(p),
                "cs": (p.get("scores", {}) or {}).get("creepScore", 0),
                "lane": p.get("position", ""),
                "dead": p.get("isDead", False),
                "gold": round(active.get("currentGold", 0)),
            }
        elif my_team is not None and p.get("team") == my_team:
            allies.append(brief(p))
        else:
            enemies.append(brief(p))

    events = payload.get("events", {}).get("Events", []) or []
    recent = [
        {"t": _mmss(ev.get("EventTime", 0)), "ev": ev.get("EventName", "")}
        for ev in events
        if game_time - ev.get("EventTime", 0) <= 90
    ]

    return {
        "tempo": _mmss(game_time),
        "eu": me,
        "aliados": allies,
        "inimigos": enemies,
        "eventos_recentes": recent,
    }


def _summarize(ctx: dict[str, Any]) -> str:
    me = ctx.get("eu", {})
    ev = ", ".join(e["ev"] for e in ctx.get("eventos_recentes", [])) or "—"
    return (
        f"{me.get('champ','?')} {me.get('lane','')} "
        f"lvl{me.get('lvl','?')} {me.get('gold','?')}g "
        f"KDA {me.get('kda','?')} | {len(ctx.get('inimigos',[]))} inimigos | "
        f"eventos: {ev}"
    )


def _call_gemini(
    client: httpx.Client, model: str, api_key: str, context: dict[str, Any]
) -> tuple[str, int, int]:
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": json.dumps(context, ensure_ascii=False)}
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 256,
            # Flash 2.5 é modelo de thinking: sem isto, o raciocínio interno
            # consome o orçamento e a resposta visível vem vazia/truncada.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    url = GEMINI_URL.format(model=model)
    backoffs = [0, 25, 50]  # 1ª tentativa imediata; depois espera o reset/min.
    for attempt, wait in enumerate(backoffs):
        if wait:
            time.sleep(wait)
        resp = client.post(
            url, params={"key": api_key}, json=body, timeout=30.0
        )
        if resp.status_code == 429:
            # Cota DIÁRIA esgotada não volta esperando segundos — falha já,
            # sem queimar 75s de backoff por amostra.
            if "perday" in resp.text.lower().replace(" ", ""):
                raise _QuotaExhausted(resp.text[:300])
            if attempt < len(backoffs) - 1:
                continue
        resp.raise_for_status()
        break

    data = resp.json()
    cand = (data.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts")
    if parts:
        text = parts[0].get("text", "").strip()
    else:
        text = f"(sem texto; finishReason={cand.get('finishReason', '?')})"
    usage = data.get("usageMetadata", {})
    return (
        text,
        int(usage.get("promptTokenCount", 0)),
        int(usage.get("candidatesTokenCount", 0)),
    )


def _process_replay(
    client: httpx.Client,
    replay: Path,
    model: str,
    api_key: str,
    interval: float,
    gap_seconds: float,
) -> list[Sample]:
    samples: list[Sample] = []
    next_threshold = 0.0
    with replay.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line).get("data", {})
            game_time = float(
                payload.get("gameData", {}).get("gameTime", 0.0)
            )
            if game_time < next_threshold:
                continue
            next_threshold = game_time + interval
            ctx = _build_context(payload)
            summary = _summarize(ctx)
            print(f"  [{_mmss(game_time)}] {summary[:70]}...", flush=True)
            try:
                tip, pin, pout = _call_gemini(client, model, api_key, ctx)
                samples.append(Sample(game_time, summary, tip, pin, pout))
            except _QuotaExhausted as exc:
                print(
                    "\n[ABORTANDO] Cota diária grátis esgotada — não adianta "
                    "continuar hoje. Salvando o parcial.\n"
                    f"  detalhe: {exc}",
                    file=sys.stderr,
                )
                # Registra no relatório por que parou — senão o .md mente,
                # parecendo uma rodada limpa que só "acabou".
                samples.append(
                    Sample(game_time, summary, "", 0, 0,
                           error="ABORTADO: cota diária grátis esgotada — "
                                 "rodada incompleta, NÃO representa o jogo todo")
                )
                break
            except KeyboardInterrupt:
                print(
                    "\n[INTERROMPIDO] Salvando o parcial coletado até aqui.",
                    file=sys.stderr,
                )
                break
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:200]
                samples.append(
                    Sample(game_time, summary, "", 0, 0,
                           error=f"HTTP {exc.response.status_code}: {detail}")
                )
            except Exception as exc:  # noqa: BLE001 - harness descartável
                samples.append(
                    Sample(game_time, summary, "", 0, 0, error=repr(exc))
                )
            try:
                time.sleep(gap_seconds)
            except KeyboardInterrupt:
                print(
                    "\n[INTERROMPIDO] Salvando o parcial coletado até aqui.",
                    file=sys.stderr,
                )
                break
    return samples


def _write_report(replay: Path, model: str, samples: list[Sample]) -> Path:
    out = replay.with_name(f"validation_{replay.stem}.md")
    total_in = sum(s.prompt_tokens for s in samples)
    total_out = sum(s.output_tokens for s in samples)
    errors = sum(1 for s in samples if s.error)
    silent = sum(1 for s in samples if s.tip.strip() == "—")
    spoken = len(samples) - silent - errors

    cost_usd = (
        total_in / 1_000_000 * PRICE_INPUT_PER_1M_USD
        + total_out / 1_000_000 * PRICE_OUTPUT_PER_1M_USD
    )
    # Extrapola pra uma partida média de 30 min nesta mesma cadência.
    span = max((s.game_time for s in samples), default=1.0) or 1.0
    scale = (30 * 60) / span if span else 1.0

    lines: list[str] = []
    lines.append(f"# Validação LLM — `{replay.name}` ({model})\n")
    lines.append(
        "> **Como avaliar:** preencha a coluna **Nota** sem olhar o tempo: "
        "`1` = inútil/errada/alucinação · `2` = ok · `3` = boa e acionável. "
        "Marque `X` na coluna **Aluc.** se a dica contradiz o estado.\n"
    )
    lines.append(
        "> **Portão de decisão:** ≥70% com nota 3 · ≤5% alucinação · "
        "≤15% nota 1. Abaixo disso, o thesis do produto não se sustenta.\n"
    )
    lines.append(
        "> ⚠️ Estes replays são Practice Tool (sem inimigos reais) — o teto "
        "de qualidade aqui é subestimado. Mecânica e custo, porém, são reais.\n"
    )
    lines.append("\n## Amostras\n")
    lines.append("| Tempo | Estado | Dica do LLM | Nota | Aluc. |")
    lines.append("|---|---|---|:---:|:---:|")
    for s in samples:
        tip = s.error and f"⚠️ {s.error}" or s.tip.replace("|", "\\|").replace("\n", " ")
        state = s.state_summary.replace("|", "\\|")
        lines.append(f"| {_mmss(s.game_time)} | {state} | {tip} |  |  |")

    lines.append("\n## Resumo\n")
    lines.append(f"- Amostras: **{len(samples)}** "
                 f"(falou: {spoken} · silêncio `—`: {silent} · erros: {errors})")
    lines.append(f"- Tokens reais: entrada **{total_in}** · saída **{total_out}**")
    lines.append(
        f"- Custo desta partida (~{_mmss(span)} de jogo): "
        f"**US$ {cost_usd:.4f}** ≈ **R$ {cost_usd * USD_TO_BRL:.3f}** "
        "*(tier grátis = R$0; valor só pra projeção)*"
    )
    lines.append(
        f"- Projeção partida de 30 min, mesma cadência: "
        f"**US$ {cost_usd * scale:.4f}** ≈ **R$ {cost_usd * scale * USD_TO_BRL:.3f}**"
    )
    lines.append(
        f"- Preços usados (VERIFIQUE): in US${PRICE_INPUT_PER_1M_USD}/1M · "
        f"out US${PRICE_OUTPUT_PER_1M_USD}/1M · câmbio R${USD_TO_BRL}"
    )

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "replays", nargs="*", type=Path,
        help="Arquivos .jsonl (padrão: todos em recordings/)",
    )
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument(
        "--interval", type=float, default=30.0,
        help="Segundos de tempo de JOGO entre amostras (padrão 30)",
    )
    parser.add_argument(
        "--gap", type=float, default=7.0,
        help="Pausa real entre chamadas, p/ respeitar rate limit (padrão 7s)",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "ERRO: defina a key antes de rodar:\n"
            '  $env:GEMINI_API_KEY = "sua-key"',
            file=sys.stderr,
        )
        return 1

    replays = args.replays or sorted(
        (Path(__file__).resolve().parents[1] / "recordings").glob("game_*.jsonl")
    )
    if not replays:
        print("ERRO: nenhum replay .jsonl encontrado em recordings/.",
              file=sys.stderr)
        return 1

    with httpx.Client() as client:
        for replay in replays:
            if not replay.exists():
                print(f"pulando (não existe): {replay}", file=sys.stderr)
                continue
            print(f"\n=== {replay.name} ===", flush=True)
            samples = _process_replay(
                client, replay, args.model, api_key,
                args.interval, args.gap,
            )
            report = _write_report(replay, args.model, samples)
            print(f"-> relatório: {report}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
