r"""Runner AO VIVO só-IA — testa a camada de IA de build numa partida real, com TTS.

NÃO é o produto e NÃO toca os detectores determinísticos do app. Faz só uma
coisa: pollar a Live Client Data API real, rodar a MESMA lógica de IA já
validada offline no prototype (build plan + situacional) e FALAR a decisão
pela TTS do app. Objetivo: ouvir, in-game, se a IA faz o papel dela.

Reusa as funções de `scripts/prototype_build_coach.py` por import — a lógica
da IA tem UMA fonte de verdade (a validada), este arquivo é só o "vivo".

PRINCÍPIO DE CUSTO: a IA decide UMA vez (o plano ordenado) e só volta a ser
chamada quando há decisão NOVA (situacional, quando o core acaba). Andar
pelo plano — reforçar o item atual, detectar que completou, anunciar o
próximo — é 100% determinístico, ZERO token. Chamar IA pra repetir o que
ela já decidiu seria desperdício.

Cadência de fala:
- Itens iniciais: 1x, determinístico, no instante em que o campeão é
  detectado (você na fonte) — ZERO IA, ZERO espera.
- Plano: 1x, logo após o starter, assim que a comp inimiga existe (sem
  esperar warmup — a comp é conhecida desde o loadscreen).
- Item atual: reforço periódico (a cada REINFORCE_GT s de jogo) E quando
  você junta ouro pro custo RESTANTE dele (custo total menos os
  componentes da receita que você já tem — cai conforme você compra).
- Ao completar o item: anuncia o próximo NA HORA.
- Situacional: IA decide quando o core acaba e abre marco de lendário.

Como não roda mais nada junto, a chamada Groq pode ser síncrona.

Limites honestos:
- Stand-in só tem Akali. Outro campeão = avisa por voz e sai.
- Botas NÃO entram na ordem de traversal (o OP.GG não diz em que slot
  exato vão); são ditas uma vez no plano. Evita fabricar timing.
- Situacional nunca foi validado offline; aqui é o 1º exercício real.

    $env:GROQ_API_KEY = "sua-key"
    .venv\Scripts\python.exe scripts/live_ai_coach.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prototype_build_coach as proto  # noqa: E402  (lógica de IA validada)

from rift_pilot.domain.ports.game_data_source import (  # noqa: E402
    GameDataSourceUnavailable,
    GameLoading,
)
from rift_pilot.infrastructure.riot.data_dragon_client import (  # noqa: E402
    DataDragonClient,
)
from rift_pilot.infrastructure.riot.live_client_data_api import (  # noqa: E402
    LiveClientDataApi,
)
from rift_pilot.infrastructure.tts.edge_tts_speaker import (  # noqa: E402
    EdgeTtsSpeaker,
)

MODEL = "openai/gpt-oss-120b"
TONE = "funny"    # "funny", "neutral", ou "serious"
MODE = "simple"   # "simple" ou "explanatory"
POLL_SECONDS = 2.0  # detecção mais rápida de mudanças (compras de itens)
REINFORCE_GT = 120.0  # reforça o item atual a cada 120s de tempo de JOGO
MAX_FAILURES_AFTER_CONNECTED = 5  # falhas seguidas pós-conexão = fim de jogo
FARM_CHECK_INTERVAL = 60.0  # feedback de farm a cada 60s de jogo
FARM_ENEMY_THRESHOLD = 10  # avisa se estiver 10+ CS atrás do inimigo de lane

# Wave arrival times (quando minions chegam na lane)
FARM_WAVE_ARRIVAL = {
    "MIDDLE": 52.0,   # mid wave chega aos 52s
    "TOP": 62.0,      # top wave chega aos 62s
    "BOTTOM": 62.0,   # bot wave chega aos 62s
    "JUNGLE": 55.0,   # camps surgem aos 55s
}

# Farm rate ideais por posição (CS/min)
FARM_RATE_IDEAL = {
    "MIDDLE": 8.0,    # 8-10 CS/min
    "TOP": 8.0,       # 8-10 CS/min
    "BOTTOM": 8.0,    # 8-10 CS/min (for ADC; support is excluded)
    "JUNGLE": 8.0,    # 8 CS/min (diferente das rotas)
}

# Mensagens customizadas por tone
MESSAGES_BY_TONE = {
    "funny": {
        "farm_low": "Bora acordar! Farm tá fraco demais pra esse momento do jogo. Mete a foice nos minions!",
        "farm_behind": "Ops! Você tá {diff} minions atrás daquele {enemy} chato. Bora recuperar no farm!",
        "item_afford": "Ó! Você juntou ouro pro {item}. Compra logo que a hora é essa!",
        "item_reminder": "Ei! Ainda tá esperando o {item}? Concentra no farm e na build!",
    },
    "neutral": {
        "farm_low": "Farm abaixo do esperado nesse ponto do jogo. Continue focando nos minions.",
        "farm_behind": "Você está {diff} minions atrás de {enemy}. Prioridade: recuperar no farm.",
        "item_afford": "Você tem ouro suficiente para {item}. Proceda com a compra.",
        "item_reminder": "Seu alvo atual é {item}.",
    },
    "serious": {
        "farm_low": "Farm crítico. Todos os recursos devem ir para minions neste momento.",
        "farm_behind": "Déficit crítico: {diff} minions atrás de {enemy}. Prioridade absoluta: farm.",
        "item_afford": "Recurso disponível. Adquira {item} imediatamente.",
        "item_reminder": "Objetivo: {item}.",
    },
}


# ── Custo restante consciente de receita ────────────────────────────────────
def _invested(target: int, owned: frozenset[int],
              prices: dict[int, int], sources: dict[int, list[int]],
              memo: dict[int, int], _guard: int = 0) -> int:
    """Ouro já investido num item-alvo, dado o inventário (recursivo).

    Se o próprio alvo está no inventário → valor cheio. Senão, soma o que
    está investido em cada componente da receita (que por sua vez pode ter
    componentes seus no inventário). Capa na soma no preço total do alvo —
    o "custo de combinação" só é pago ao concluir, então não conta como
    investido até lá.
    """
    if target in owned:
        return prices.get(target, 0)
    if target in memo:
        return memo[target]
    if _guard > 12:  # receitas de LoL são rasas; trava paranoia anti-ciclo
        return 0
    s = 0
    for comp in sources.get(target, []):
        s += _invested(comp, owned, prices, sources, memo, _guard + 1)
    s = min(s, prices.get(target, 0))
    memo[target] = s
    return s


def _remaining_cost(target: int, owned: frozenset[int],
                    prices: dict[int, int],
                    sources: dict[int, list[int]]) -> int:
    return max(0, prices.get(target, 0)
               - _invested(target, owned, prices, sources, {}))


# ── Helpers de payload / fala ───────────────────────────────────────────────
def _detect_champ_role(payload: dict[str, Any]) -> tuple[str, str] | None:
    active = payload.get("activePlayer", {}) or {}
    me = active.get("riotId") or active.get("summonerName", "")
    for p in payload.get("allPlayers", []) or []:
        if (p.get("riotId") or p.get("summonerName", "")) == me:
            champ, pos = p.get("championName"), p.get("position")
            if champ and pos:
                return champ, pos
    return None


def _get_message(key: str, tone: str, **kwargs) -> str:
    """Retorna mensagem customizada por tone, com variáveis substituídas."""
    msgs = MESSAGES_BY_TONE.get(tone, MESSAGES_BY_TONE["neutral"])
    template = msgs.get(key, "")
    return template.format(**kwargs) if template else ""


def _say(speaker: EdgeTtsSpeaker, text: str, events: list[str] | None = None) -> None:
    print(f"  🔊 {text}", flush=True)
    if events is not None:
        events.append(text)
    try:
        speaker.speak(text)
    except Exception as exc:  # noqa: BLE001 - TTS não derruba o teste
        print(f"  [TTS falhou: {exc!r}]", file=sys.stderr, flush=True)


def main() -> int:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print('ERRO: $env:GROQ_API_KEY = "sua-key"', file=sys.stderr)
        return 1

    print("=== Runner AO VIVO só-IA (sem detectores determinísticos) ===",
          flush=True)

    # Preparar gravação de partida
    record_path = Path("recordings") / f"live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    record_file = None
    tick_num = 0

    dd = DataDragonClient()
    names = dd.get_item_names()
    prices = dd.get_item_prices()
    sources = dd.get_item_sources()
    # Mapeamento reverso confiável: nome → ID. Inverte names corretamente.
    # Se houver duplicatas de nomes, usa o primeiro encontrado (raramente acontece).
    name_to_id: dict[str, int] = {nm: iid for iid, nm in names.items()}
    legendary_ids = frozenset(
        i for i, g in prices.items() if g >= proto.LEGENDARY_TOTAL_THRESHOLD
    )
    speaker = EdgeTtsSpeaker()

    baseline: proto.Baseline | None = None
    plan: proto.BuildPlan | None = None
    # sequência de (nome, id) a percorrer: core ordenado + situacionais (append).
    sequence: list[tuple[str, int]] = []
    sequence_by_name: dict[str, int] = {}  # para rápida lookup por nome
    sit_pend = list(proto.SITUATIONAL_AFTER_LEGENDARY)
    sits: list[proto.SituationalDecision] = []

    current_target: str | None = None
    last_reinforce_gt = 0.0
    affordable_announced_for: str | None = None
    last_farm_check_epoch = -1  # epoch anterior checado (para farm geral)
    last_farm_threshold_announcement = 0.0  # último GT em que avisou de threshold

    connected = False
    failures = 0
    loading_announced = False
    detected_rota: str | None = None  # memória da posição uma vez detectada

    print("Aguardando partida... (Ctrl+C pra parar)", flush=True)
    with LiveClientDataApi() as api, httpx.Client() as groq:
        while True:
            tick_events: list[str] = []  # eventos deste tick
            try:
                payload = api.get_all_data()
            except GameLoading:
                failures = 0
                if not loading_announced:
                    loading_announced = True
                    print("  tela de carregamento (404) — aguardando...",
                          flush=True)
                time.sleep(POLL_SECONDS)
                continue
            except GameDataSourceUnavailable:
                failures += 1
                if connected and failures >= MAX_FAILURES_AFTER_CONNECTED:
                    print("Partida encerrada (API inacessível). Fim.",
                          flush=True)
                    break
                time.sleep(POLL_SECONDS)
                continue
            except KeyboardInterrupt:
                print("\nInterrompido.", flush=True)
                break

            failures = 0
            if not connected:
                connected = True
                record_file = record_path.open("w", encoding="utf-8")
                print(f"Conectado à partida. Gravando em {record_path}", flush=True)

            gt = float(payload.get("gameData", {}).get("gameTime", 0.0))

            if baseline is None:
                cr = _detect_champ_role(payload)
                if cr is None:
                    time.sleep(POLL_SECONDS)
                    continue
                champ, role = cr
                baseline = proto._build_baseline(champ, role, names)
                if baseline is None:
                    _say(speaker,
                         f"Campeão {champ} não está no stand-in; "
                         "este teste só suporta Akali por enquanto.",
                         tick_events)
                    print(f"Sem build stand-in para {champ}. Saindo.",
                          flush=True)
                    return 0
                print(f"Jogador: {champ} ({role})", flush=True)

                # ── Tenta inferir posição imediatamente se não vier do API ──
                state = proto._player_state(payload)
                if not state.get("rota") or state.get("rota") == "NONE":
                    active = payload.get("activePlayer", {}) or {}
                    my_name = active.get("riotId") or active.get("summonerName", "")
                    my_team = next(
                        (p.get("team") for p in (payload.get("allPlayers", []) or [])
                         if (p.get("riotId") or p.get("summonerName", "")) == my_name),
                        None,
                    )
                    if my_team:
                        filled_positions = set(
                            p.get("position") for p in (payload.get("allPlayers", []) or [])
                            if p.get("team") == my_team and p.get("position") != "NONE"
                        )
                        all_positions = {"TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"}
                        missing = all_positions - filled_positions
                        if len(missing) == 1:
                            detected_rota = missing.pop()
                            print(f"  [Posição inferida imediatamente: {detected_rota}]",
                                  flush=True)

            # ── IA #1: plano — assim que a comp inimiga existe (sem warmup) ──
            # A comp adversária é conhecida desde o loadscreen; não há razão
            # pra esperar 1:15. Dispara no 1º poll com inimigos populados —
            # logo após o starter, antes de você sair da base.
            if plan is None:
                enemies = proto._enemy_champions(payload)
                if not enemies:
                    time.sleep(POLL_SECONDS)
                    continue
                print(f"  [{proto._mmss(gt)}] decidindo build plan — "
                      f"inimigos: "
                      f"{', '.join(e['champ'] for e in enemies) or '?'}",
                      flush=True)
                plan = proto._decide_build_plan(
                    groq, MODEL, key, baseline, enemies,
                    tone=TONE, mode=MODE)
                if plan.error:
                    _say(speaker,
                         "Não consegui montar a build agora; a IA falhou.",
                         tick_events)
                else:
                    # Starter primeiro — imediato, antes de sair da base
                    if plan.starter and plan.starter_message:
                        _say(speaker, plan.starter_message, tick_events)
                        time.sleep(0.5)  # Pequena pausa pra garantir que foi ouvido

                    # Depois o plano de build completo
                    # Monta sequência usando IDs do baseline (garantidos corretos)
                    sequence = []
                    sequence_by_name = {}
                    for nm in plan.core_order:
                        # Procura o índice do nome em core_pool
                        if nm in baseline.core_pool:
                            idx = baseline.core_pool.index(nm)
                            iid = baseline.core_pool_ids[idx]
                            sequence.append((nm, iid))
                            sequence_by_name[nm] = iid
                        else:
                            # Fallback se nome não está exatamente em core_pool
                            iid = name_to_id.get(nm, -1)
                            sequence.append((nm, iid))
                            sequence_by_name[nm] = iid

                    # Usa mensagens geradas pela IA (com tone e mode)
                    if plan.core_message:
                        _say(speaker, plan.core_message, tick_events)
                    if plan.boots_message:
                        _say(speaker, plan.boots_message, tick_events)

            if plan is None or plan.error:
                time.sleep(POLL_SECONDS)
                continue

            state = proto._player_state(payload)
            owned = frozenset(state["_itens_ids"])
            legcount = sum(1 for i in owned if i in legendary_ids)

            # ── IA #2..N: situacional (core acabou + marco de lendário) ─────
            core_done = all(iid in owned
                            for nm, iid in sequence) if sequence \
                else True
            if core_done and sit_pend:
                while sit_pend and legcount >= sit_pend[0]:
                    th = sit_pend.pop(0)
                    gatilho = f"{th} lendários → {th + 1}º item"
                    enemies_it = proto._enemy_threats(
                        payload, legendary_ids, names)
                    prev = [s.item_recomendado for s in sits
                            if s.valido and s.item_recomendado]
                    print(f"  [{proto._mmss(gt)}] situacional ({gatilho})",
                          flush=True)
                    d = proto._decide_situational(
                        groq, MODEL, key, state, enemies_it,
                        baseline.situational_pool,
                        baseline.situational_pool_ids, gt, prev)
                    d.gatilho = gatilho
                    sits.append(d)
                    if (not d.error
                            and d.item_recomendado not in ("", "—")):
                        # Procura no pool situacional do baseline
                        if d.item_recomendado in baseline.situational_pool:
                            idx = baseline.situational_pool.index(d.item_recomendado)
                            iid = baseline.situational_pool_ids[idx]
                        else:
                            # Fallback se não está no baseline
                            iid = name_to_id.get(d.item_recomendado, -1)
                        sequence.append((d.item_recomendado, iid))
                        sequence_by_name[d.item_recomendado] = iid
                        tick_events.append(f"Situacional: {d.item_recomendado}")

            # ── Motor determinístico: alvo atual, reforço, próximo ──────────
            # Procura o primeiro item da sequência que você NÃO tem
            new_target = None
            for nm, iid in sequence:
                if iid not in owned:
                    new_target = nm
                    break

            # DEBUG: log do estado de detecção
            if sequence:
                print(f"  [DEBUG] GT={proto._mmss(gt)} | owned={sorted(owned)} | "
                      f"sequence={[(nm, iid) for nm, iid in sequence[:3]]} | "
                      f"new_target={new_target}", flush=True)

            if new_target != current_target:
                print(f"  [MUDANÇA] current={current_target} → new={new_target} | "
                      f"owned={sorted(owned)}", flush=True)
                if (current_target is not None and new_target is not None
                        and sequence_by_name.get(current_target, -1) in owned):
                    # completou o alvo anterior → próximo IMEDIATO
                    _say(speaker,
                         f"{current_target} feito. Próximo: {new_target}.",
                         tick_events)
                elif new_target is not None and current_target is None:
                    _say(speaker, f"Comece subindo {new_target}.", tick_events)
                elif new_target is not None:
                    _say(speaker, f"Agora suba {new_target}.", tick_events)
                current_target = new_target
                last_reinforce_gt = gt
                affordable_announced_for = None

            if current_target is not None:
                # Usa o ID do mapeamento da sequência, que é confiável
                tid = sequence_by_name.get(current_target, -1)
                gold = round(
                    (payload.get("activePlayer", {}) or {})
                    .get("currentGold", 0))
                rem = _remaining_cost(tid, owned, prices, sources)

                # reforço por PODER COMPRAR (1x por alvo, ao ficar afford.)
                if (rem > 0 and gold >= rem
                        and affordable_announced_for != current_target):
                    affordable_announced_for = current_target
                    last_reinforce_gt = gt
                    msg = _get_message("item_afford", TONE, item=current_target)
                    _say(speaker, msg, tick_events)
                # reforço PERIÓDICO do item atual
                elif gt - last_reinforce_gt >= REINFORCE_GT:
                    last_reinforce_gt = gt
                    msg = _get_message("item_reminder", TONE, item=current_target)
                    _say(speaker, msg, tick_events)

            # ── Memoriza posição assim que aparecer (para Practice Tool) ────
            current_rota = state["rota"]
            if current_rota and current_rota != "NONE":
                if detected_rota is None:
                    detected_rota = current_rota
                    print(f"  [Posição detectada: {detected_rota}]", flush=True)
                elif detected_rota != current_rota:
                    # Position changed (shouldn't happen mid-game, but log it)
                    print(f"  [AVISO] Posição mudou: {detected_rota} → {current_rota}",
                          flush=True)
                    detected_rota = current_rota

            # ── Farm feedback — por rota com timings específicos ──
            # Regras:
            # - UTILITY (support): sem farm feedback
            # - Outras rotas: 60s após wave arrival, a cada 30s, com thresholds por rota
            my_rota = detected_rota or current_rota
            if my_rota and my_rota != "NONE" and my_rota != "UTILITY":
                wave_arrival = FARM_WAVE_ARRIVAL.get(my_rota, 90.0)
                farm_start_gt = wave_arrival + 60.0  # primeiro check 60s após wave

                if gt >= farm_start_gt:
                    my_cs = state["cs"]
                    gt_min = gt / 60.0
                    cs_per_min = my_cs / gt_min if gt_min > 0 else 0
                    farm_rate_ideal = FARM_RATE_IDEAL.get(my_rota, 8.0)

                    # Detecta inimigo de lane uma vez
                    enemy = None
                    if my_rota in ("MIDDLE", "TOP", "BOTTOM"):
                        active = payload.get("activePlayer", {}) or {}
                        my_name = active.get("riotId") or active.get("summonerName", "")
                        my_team = next(
                            (p.get("team") for p in (payload.get("allPlayers", []) or [])
                             if (p.get("riotId") or p.get("summonerName", "")) == my_name),
                            None,
                        )
                        enemy = proto._lane_enemy(payload, my_team, my_rota)

                    # ── THRESHOLD: Checado a cada tick, avisado 1x por minuto ──
                    if enemy and gt - last_farm_threshold_announcement >= 60.0:
                        enemy_cs = (enemy.get("scores", {}) or {}).get("creepScore", 0)
                        diff = enemy_cs - my_cs
                        if diff >= FARM_ENEMY_THRESHOLD:
                            msg = _get_message("farm_behind", TONE,
                                              diff=diff,
                                              enemy=enemy.get("championName", "o inimigo"))
                            _say(speaker, msg, tick_events)
                            last_farm_threshold_announcement = gt

                    # ── FARM GERAL: A cada 60s (epochs) ──
                    current_epoch = int((gt - farm_start_gt) / FARM_CHECK_INTERVAL)
                    if current_epoch > last_farm_check_epoch:
                        last_farm_check_epoch = current_epoch
                        print(f"  [FARM CHECK] GT={proto._mmss(gt)} | rota={my_rota} | "
                              f"CS={my_cs} | cs/min={cs_per_min:.1f} | ideal={farm_rate_ideal}",
                              flush=True)

                        # Só avisa farm geral se NÃO alertou sobre threshold agora
                        threshold_alerted = (
                            enemy and gt - last_farm_threshold_announcement < 5.0
                        )
                        if not threshold_alerted and cs_per_min < farm_rate_ideal:
                            target_cs = int(farm_rate_ideal * gt_min)
                            msg = _get_message("farm_low", TONE,
                                              cs=my_cs,
                                              minutes=int(gt_min),
                                              target=target_cs)
                            _say(speaker, msg, tick_events)

            # ── Gravar tick ─────────────────────────────────────────────────
            if record_file is not None:
                record_file.write(json.dumps({
                    "tick": tick_num,
                    "ts": time.time(),
                    "gt": gt,
                    "data": payload,
                    "coach_events": tick_events,
                }, ensure_ascii=False) + "\n")
                record_file.flush()
                tick_num += 1

            try:
                time.sleep(POLL_SECONDS)
            except KeyboardInterrupt:
                print("\nInterrompido.", flush=True)
                break

        # Fechar o arquivo de gravação
        if record_file is not None:
            record_file.close()
            print(f"Gravação salva em {record_path}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
