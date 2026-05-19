"""Protótipo v8 do coach de build — IA dona da build de ponta a ponta.

Mudança chave vs v7 (decisão do usuário, 2026-05-15):

  1. NÃO existe mais split free-determinístico/IA dentro do tier pago. No
     tier pago a IA decide core (ordem) + botas + situacionais, sempre
     DENTRO dos pools que o OP.GG expõe. O STARTER é passthrough fixo do
     OP.GG, não decisão da IA: o starter canônico do campeão não tem
     opções reais; pedir "escolha" levava a starter incompleto (v8 teste
     omitiu a poção). (O tier free continua determinístico noutro lugar;
     este harness só exercita a camada IA.)

  2. ZERO tabela curada de ameaça. CHAMPION_PROFILES e ITEM_THREATS foram
     removidas: cobriam ~8% dos campeões/itens do jogo, então eram cegas na
     prática real e davam falsa sensação de estrutura. O modelo cravado
     (gpt-oss-120b) conhece campeão e item do próprio treino; ele raciocina
     ameaça sobre o dado REAL e completo que a Live API já dá (campeões
     inimigos + os itens que eles de fato compraram, nomes via Data Dragon).

Anti-fabricação (inalterado e por CÓDIGO, não confiado ao modelo): todo
item recomendado tem que estar no pool empírico do OP.GG E existir no Data
Dragon do patch. O raciocínio de ameaça NÃO precisa ser à prova de
alucinação — ele é só input pra uma escolha que já está engaiolada no pool.

Decisões da IA por partida:
  #1 — no warmup: build plan completo (starter, core ordenado, botas)
       escolhido dos pools do OP.GG, matchup-aware (só nomes de campeão
       inimigo; ninguém tem item ainda).
  #2 — por PROGRESSO de build (3/4/5 lendários fechados → 4º/5º/6º
       item), não por relógio; item do pool 4/5/6, dedup contra o
       inventário REAL (por ID, não por nome — independe do locale).

NOTA DE PRODUÇÃO: o build do OP.GG está hardcoded como stand-in (só Akali,
patch 16.10, IDs verificados contra Data Dragon). Em produção um
OpggBuildProvider substitui o DeeplolBuildProvider — caveat: OP.GG não tem
API JSON limpa como o deeplol; é o "ripple" a ser feito depois.

    $env:GROQ_API_KEY = "sua-key"
    python scripts/prototype_build_coach.py recordings/<replay>.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from rift_pilot.infrastructure.riot.data_dragon_client import DataDragonClient

PRICE_IN_PER_1M_USD = 0.59
PRICE_OUT_PER_1M_USD = 0.79
USD_TO_BRL = 5.30

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

LEGENDARY_TOTAL_THRESHOLD = 2200
WARMUP_GT = 75.0

# Gatilho do situacional = PROGRESSO DE BUILD, não relógio. O relógio
# (12/17min) era placeholder arbitrário: forçava recomendar o 4º/5º item
# pra quem tinha 1-2 itens. Agora dispara quando o jogador FECHA itens
# lendários: 3 lendários (core de 3 fechado) → recomenda o 4º; 4 → 5º;
# 5 → 6º. Determinístico e significativo (princípio cravado da arquitetura).
# Nuance: se o core do campeão tem 4 itens, o 1º disparo (3 lendários)
# pode pegar o jogador ainda comprando o 4º de core — o dedup por
# inventário evita recomendar o que ele já tem; o que falta de core o
# situacional não cobre (gap conhecido, aceitável no prototype).
SITUATIONAL_AFTER_LEGENDARY: tuple[int, ...] = (3, 4, 5)

# ── Stand-in da fonte OP.GG (patch 16.10) ───────────────────────────────────
# IDs VERIFICADOS contra Data Dragon (não chutados). Só Akali por ora — é o
# campeão do replay de teste. Em produção isto vem do OpggBuildProvider, que
# expõe os MESMOS pools que a página de build do OP.GG mostra (starter, botas,
# core com alternativas, 4º/5º/6º). Mantive só IDs já verificados na v7 — não
# inventei opções novas: o stand-in é deliberadamente conservador.
OPGG_BUILDS: dict[str, dict[str, Any]] = {
    "Akali": {
        "starter_options": [
            {"ids": [1056, 2003], "winrate": 53.74, "games": 18232},  # Anel de Doran, Poção
            {"ids": [1054, 2003], "winrate": 43.13, "games": 14633},  # Escudo de Doran, Poção
        ],
        "boots_pool_ids":       [3020, 3111],               # Feiticeiro, Mercúrio
        "core_pool_ids":        [3146, 4645, 3157, 3089],   # Pistola, Chama Sombria, Zhonya, Rabadon
        "situational_pool_ids": [3089, 3157, 3135],         # Rabadon, Zhonya, Cajado do Vazio
    },
}


@dataclass
class Baseline:
    campeao: str
    rota: str
    starter_options: list[dict[str, Any]]  # [{"items": [...], "winrate": float, "games": int}, ...]
    boots_pool: list[str]
    boots_pool_ids: list[int]  # alinhado 1:1 com boots_pool
    core_pool: list[str]
    core_pool_ids: list[int]  # alinhado 1:1 com core_pool
    situational_pool: list[str]
    situational_pool_ids: list[int]  # alinhado 1:1 com situational_pool
    fonte: str = "OP.GG (stand-in, patch 16.10)"


@dataclass
class BuildPlan:
    """Decisão #1: build inteira escolhida pela IA dentro dos pools."""

    starter: list[str] = field(default_factory=list)
    core_order: list[str] = field(default_factory=list)
    boots: str = ""
    boots_razao: str = ""         # ex.: "tenacidade contra CC pesado do Galio"
    razao: str = ""
    # Mensagens naturais geradas pela IA (com tone e mode aplicados)
    starter_message: str = ""     # mensagem completa sobre starter
    core_message: str = ""        # mensagem completa sobre core
    boots_message: str = ""       # mensagem completa sobre boots
    # Explicações (mode="explanatory" only)
    explanation: dict[str, str] = field(default_factory=dict)  # {starter, core, boots}
    valido: bool = False           # tudo dentro dos pools? (checado por código)
    fora_do_pool: list[str] = field(default_factory=list)
    raw: str = ""
    error: str = ""
    tok_in: int = 0
    tok_out: int = 0


@dataclass
class SituationalDecision:
    momento_gt: float
    item_recomendado: str
    valido: bool
    gatilho: str = ""          # ex.: "3 lendários → 4º item"
    razao: str = ""
    raw: str = ""
    error: str = ""
    tok_in: int = 0
    tok_out: int = 0


def _mmss(s: float) -> str:
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


def _resolve(ids: list[int], names: dict[int, str]) -> list[str]:
    return [names[i] for i in ids if i in names]


def _resolve_aligned(
    ids: list[int], names: dict[int, str]
) -> tuple[list[str], list[int]]:
    """Como _resolve, mas devolve nomes e IDs alinhados 1:1 (só os resolvidos)."""
    pairs = [(names[i], i) for i in ids if i in names]
    return [n for n, _ in pairs], [i for _, i in pairs]


def _build_baseline(champion: str, role: str,
                    names: dict[int, str]) -> Baseline | None:
    raw = OPGG_BUILDS.get(champion)
    if raw is None:
        return None
    boots_names, boots_ids = _resolve_aligned(raw["boots_pool_ids"], names)
    core_names, core_ids = _resolve_aligned(raw["core_pool_ids"], names)
    situational_names, situational_ids = _resolve_aligned(raw["situational_pool_ids"], names)

    starter_options = [
        {
            "items": _resolve(opt["ids"], names),
            "winrate": opt["winrate"],
            "games": opt["games"],
        }
        for opt in raw["starter_options"]
        if _resolve(opt["ids"], names)  # só opções com IDs válidos
    ]
    return Baseline(
        campeao=champion, rota=role,
        starter_options=starter_options,
        boots_pool=boots_names,
        boots_pool_ids=boots_ids,
        core_pool=core_names,
        core_pool_ids=core_ids,
        situational_pool=situational_names,
        situational_pool_ids=situational_ids,
    )


def _my_team(payload: dict[str, Any]) -> tuple[str, Any, list[dict[str, Any]]]:
    active = payload.get("activePlayer", {}) or {}
    players = payload.get("allPlayers", []) or []
    me_name = active.get("riotId") or active.get("summonerName", "")
    team = next(
        (p.get("team") for p in players
         if (p.get("riotId") or p.get("summonerName", "")) == me_name),
        None,
    )
    return me_name, team, players


def _enemy_champions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Warmup: só campeões inimigos (ninguém tem item ainda). Dado cru, 100%."""
    _, team, players = _my_team(payload)
    return [
        {"champ": p.get("championName", "?"), "lvl": p.get("level", 0)}
        for p in players
        if team is not None and p.get("team") not in (None, team)
    ]


def _lane_enemy(payload: dict[str, Any], my_team: str | None,
                my_rota: str) -> dict[str, Any] | None:
    """Retorna o jogador inimigo de mesma posição (lane), ou None."""
    if not my_team or not my_rota:
        return None
    for p in payload.get("allPlayers", []) or []:
        if (p.get("team") != my_team and p.get("position") == my_rota):
            return p
    return None


def _enemy_threats(payload: dict[str, Any], legendary_ids: frozenset[int],
                   names: dict[int, str]) -> list[dict[str, Any]]:
    """Situacional: campeão inimigo + os itens lendários que ele DE FATO tem.

    Sem tag/classificação curada — só o nome real do item (resolvido por ID
    via Data Dragon, estável ao locale). O 120B raciocina a ameaça sobre
    isso. O recorte "lendário" usa preço do Data Dragon (empírico, não
    curado) só pra manter o payload pequeno.
    """
    _, team, players = _my_team(payload)
    out: list[dict[str, Any]] = []
    for p in players:
        if team is None or p.get("team") in (None, team):
            continue
        itens: list[str] = []
        for it in (p.get("items", []) or []):
            iid = int(it.get("itemID", 0))
            if it.get("slot", 99) > 5 or it.get("consumable", False):
                continue
            if iid not in legendary_ids:
                continue
            itens.append(names.get(iid, it.get("displayName", str(iid))))
        if itens:
            out.append({"champ": p.get("championName", "?"), "itens": itens})
    return out


def _player_state(payload: dict[str, Any]) -> dict[str, Any]:
    _, _, players = _my_team(payload)
    active = payload.get("activePlayer", {}) or {}
    me_name = active.get("riotId") or active.get("summonerName", "")
    me = next(
        (p for p in players
         if (p.get("riotId") or p.get("summonerName", "")) == me_name),
        {},
    )
    scores = me.get("scores", {}) or {}
    owned = [
        it for it in (me.get("items", []) or [])
        if it.get("slot", 99) <= 5 and not it.get("consumable", False)
    ]
    return {
        "champ": me.get("championName", "?"),
        "rota": me.get("position", ""),
        "lvl": me.get("level", 0),
        "ouro": round(active.get("currentGold", 0)),
        "kda": f"{scores.get('kills',0)}/"
               f"{scores.get('deaths',0)}/{scores.get('assists',0)}",
        "cs": scores.get("creepScore", 0),
        "itens": [it.get("displayName", "?") for it in owned],
        # IDs estáveis (independem do locale do cliente) — base do dedup.
        "_itens_ids": [int(it.get("itemID", 0)) for it in owned],
    }


def _get_starter_prompt(tone: str = "neutral", mode: str = "simple") -> str:
    """Retorna o prompt SYSTEM para decisão de STARTER apenas (lane enemy).

    tone: "funny", "neutral", ou "serious"
    mode: "simple" ou "explanatory"
    """
    tone_instr = {
        "funny": "Use tom descontraído e engraçado. Faça piadas sobre o matchup.",
        "neutral": "Use tom profissional e direto.",
        "serious": "Use tom sério e técnico.",
    }.get(tone, "Use tom profissional.")

    if mode == "explanatory":
        msg_instr = (
            "Mensagem explicando em detalhes por que esse starter foi escolhido "
            "(considerando o matchup, sustain vs dano, tipo de ameaça, etc)."
        )
        explanation_instr = '\nInclua também campo "explanation": "resumo curto do raciocínio".'
    else:
        msg_instr = (
            "Mensagem curta e natural listando os itens com uma razão bem simples (1 frase). "
            "Ex: 'Escudo de Doran e Poção pra sustain contra poke.'"
        )
        explanation_instr = ""

    return (
        f"Você é um especialista em itemização de League of Legends. {tone_instr}\n"
        f"Decida qual STARTER é melhor para este matchup de lane.{explanation_instr}\n"
        "\n"
        "O jogador tem 2 opções de starter (dados reais do OP.GG com winrate e games). "
        "Sua decisão considera APENAS o inimigo de lane, ninguém mais.\n"
        "\n"
        "REGRAS:\n"
        "1. Escolha UM dos starter_options.\n"
        "2. Use winrate/games como referência estatística.\n"
        "3. Raciocine sobre o matchup específico:\n"
        "   - vs ranged/poke? Prefira sustain (Escudo de Doran).\n"
        "   - vs melee/all-in? Considere dano (Anel de Doran).\n"
        "   - vs mage AP burst? Escudo de Doran bloqueia dano mágico melhor.\n"
        "4. Copie EXATAMENTE os nomes dos itens da opção escolhida.\n"
        "5. NÃO invente itens fora das opções.\n"
        "\n"
        f"FORMATO: JSON puro\n"
        '{"starter": [...], "starter_message": "<mensagem, com tom ' + tone + '>"' +
        (', "explanation": "..."' if mode == "explanatory" else "") +
        '}'
    )


def _get_core_boots_prompt(tone: str = "neutral", mode: str = "simple") -> str:
    """Retorna o prompt SYSTEM para decisão de CORE + BOTAS (comp inimiga completa).

    tone: "funny", "neutral", ou "serious"
    mode: "simple" ou "explanatory"
    """
    tone_instr = {
        "funny": "Use tom descontraído e engraçado. Faça piadas sobre o jogo/comp.",
        "neutral": "Use tom profissional e direto.",
        "serious": "Use tom sério e técnico.",
    }.get(tone, "Use tom profissional.")

    if mode == "explanatory":
        core_msg_instr = (
            "Mensagem explicando a estratégia de build: qual é o power spike, qual ameaça "
            "cada item responde, como ele escala."
        )
        boots_msg_instr = (
            "Mensagem explicando por que essas botas foram escolhidas (qual dano evita, "
            "qual recurso do inimigo bloqueia, etc)."
        )
        explanation_instr = f"""\n\nMODO EXPLANATORY:
{core_msg_instr}
{boots_msg_instr}
Inclua também objeto 'explanation' com resumos curtos {{core, boots}}."""
    else:
        explanation_instr = (
            "\n\nMODO SIMPLES:\n"
            "- core_message: APENAS a ordem dos itens de forma natural, sem explicar cada um. "
            "Ex: 'Core: Pistola, Chama Sombria, Zhonya, Rabadon.'\n"
            "- boots_message: APENAS o nome das botas e uma razão simples (1 frase)."
        )

    return (
        f"Você é um especialista em itemização de League of Legends. {tone_instr}\n"
        f"Decida CORE (ordem) + BOTAS considerando a composição inimiga completa.{explanation_instr}\n"
        "\n"
        "O jogador tem os POOLS de itens que o OP.GG lista para esse campeão. "
        "Você já sabe qual starter foi escolhido. Agora decida core (ordem) e botas.\n"
        "\n"
        "REGRAS CORE:\n"
        "1. core_em_ordem é a ordem de compra PROVADA do OP.GG (estatística real). "
        "É o DEFAULT e deve ser MANTIDO EXATAMENTE na maioria dos casos.\n"
        "2. Só desvie se ganho defensivo/ofensivo for CLARO vs comp inimiga completa.\n"
        "3. Desvio máximo: mover UM item. core_order = default ou default + 1 ajuste.\n"
        "4. Para qualquer desvio, cite QUAL item inimigo/ameaça específica você responde.\n"
        "\n"
        "REGRAS BOTAS:\n"
        "1. Escolha UMA de boots_pool.\n"
        "2. Cite resistência mágica/tenacidade APENAS se houver de fato ameaça AP/CC.\n"
        "3. Se comp é 80% AD, armadura faz sentido.\n"
        "4. Use nomes EXATOS, verbatim.\n"
        "\n"
        "FORMATO: JSON puro\n"
        '{"core_order": [...], "boots": "<nome exato>", '
        '"core_message": "<mensagem, tom ' + tone + '>", '
        '"boots_message": "<mensagem, tom ' + tone + '>"' +
        (', "explanation": {core: "...", boots: "..."}' if mode == "explanatory" else "") +
        '}'
    )

SYSTEM_SITUATIONAL = (
    "Você é um especialista em itemização. O jogador já completou o core. "
    "Decida qual item do POOL SITUACIONAL (dado real do OP.GG pra esse "
    "campeão) ele compra AGORA.\n"
    "\n"
    "REGRAS:\n"
    "1. Escolha UM item de pool_situacionais que melhor responde à maior "
    "ameaça inimiga atual. Raciocine sobre os campeões inimigos e os itens "
    "que eles realmente compraram (inimigos_e_itens) — sem categorias "
    "prontas, use seu conhecimento do jogo.\n"
    "2. NÃO recomende item em recomendacoes_anteriores — escolha outro do "
    "pool. Se todos já foram, escolha o melhor remanescente.\n"
    "3. Considere o estado do jogador (itens, KDA, ouro).\n"
    "4. Use o nome EXATO do item, verbatim do pool.\n"
    "\n"
    "FORMATO: JSON puro:\n"
    '{"item": "<nome exato do pool>", "razao": "frase curta citando '
    'inimigo/item específico"}'
)


def _call_groq_json(
    client: httpx.Client, model: str, key: str,
    system: str, user_payload: dict[str, Any],
) -> tuple[dict[str, Any], int, int, str]:
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",
             "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        # Teto, não custo: cobra-se token real. O prompt do build plan faz o
        # modelo de raciocínio gastar mais antes de fechar o JSON; 400
        # estourava (HTTP 400 json_validate_failed). 900 dá folga.
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
    }
    if "gpt-oss" in model.lower():
        body["reasoning_effort"] = "low"
    else:
        body["temperature"] = 0.2
    for attempt in range(3):
        resp = client.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"},
                           json=body, timeout=40.0)
        if resp.status_code == 429 and attempt < 2:
            time.sleep(20 * (attempt + 1))
            continue
        if resp.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {resp.status_code} :: {resp.text}",
                request=resp.request, response=resp)
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        ti = int(usage.get("prompt_tokens", 0))
        to = int(usage.get("completion_tokens", 0))
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}
        return parsed, ti, to, raw
    raise RuntimeError("429 persistente")


def _decide_build_plan(client, model, key, baseline: Baseline,
                       enemies: list[dict[str, Any]],
                       tone: str = "neutral",
                       mode: str = "simple") -> BuildPlan:
    """Decida starter, core e botas em 2 chamadas separadas à IA.

    Call #1: Starter (lane_enemy apenas)
    Call #2: Core + Botas (comp inimiga completa)
    """
    # Detectar lane_enemy
    lane_enemy = None
    if enemies:
        lane_enemy = enemies[0]  # Simplificado: assume 1º é o lane

    # ── CALL #1: STARTER (lane_enemy only) ──────────────────────────────
    starter = []
    starter_message = ""
    starter_explanation = ""
    ti_starter, to_starter = 0, 0
    raw_s = ""

    if lane_enemy:
        payload_starter = {
            "champion": baseline.campeao,
            "role": baseline.rota,
            "lane_enemy": lane_enemy,
            "starter_opcoes": baseline.starter_options,
        }
        system_starter = _get_starter_prompt(tone=tone, mode=mode)
        try:
            parsed_s, ti_starter, to_starter, raw_s = _call_groq_json(
                client, model, key, system_starter, payload_starter)
            ia_starter = parsed_s.get("starter") or []
            valid_starter_sets = [frozenset(opt["items"]) for opt in baseline.starter_options]
            if frozenset(ia_starter) in valid_starter_sets:
                starter = ia_starter
            else:
                starter = baseline.starter_options[0]["items"]
            starter_message = str(parsed_s.get("starter_message", ""))
            starter_explanation = str(parsed_s.get("explanation", ""))
        except Exception as e:  # noqa: BLE001
            return BuildPlan(error=f"Starter call failed: {repr(e)}")

    # ── CALL #2: CORE + BOTAS (full comp) ───────────────────────────────
    core_order = []
    boots = ""
    core_message = ""
    boots_message = ""
    explanation_dict = {}
    ti_core, to_core = 0, 0
    raw_c = ""

    payload_core = {
        "champion": baseline.campeao,
        "role": baseline.rota,
        "core_em_ordem": baseline.core_pool,
        "boots_pool": baseline.boots_pool,
        "campeoes_inimigos": enemies,
    }
    system_core = _get_core_boots_prompt(tone=tone, mode=mode)
    try:
        parsed_c, ti_core, to_core, raw_c = _call_groq_json(
            client, model, key, system_core, payload_core)
        core_order = [str(x) for x in (parsed_c.get("core_order") or [])]
        boots = str(parsed_c.get("boots", ""))
        core_message = str(parsed_c.get("core_message", ""))
        boots_message = str(parsed_c.get("boots_message", ""))
        explanation_dict = parsed_c.get("explanation", {}) if isinstance(
            parsed_c.get("explanation"), dict) else {}
    except Exception as e:  # noqa: BLE001
        return BuildPlan(error=f"Core/boots call failed: {repr(e)}")

    # ── Anti-fabricação (POR CÓDIGO): validar ───────────────────────────
    cp, bp = set(baseline.core_pool), set(baseline.boots_pool)
    fora = [c for c in core_order if c not in cp]
    if boots and boots not in bp:
        fora.append(boots)

    # Consolidar explanation
    explanation = {
        "starter": starter_explanation,
        **(explanation_dict or {})
    }

    return BuildPlan(
        starter=starter, core_order=core_order, boots=boots,
        boots_razao="",
        razao="",
        starter_message=starter_message,
        core_message=core_message,
        boots_message=boots_message,
        explanation=explanation,
        valido=not fora, fora_do_pool=fora,
        raw=f"[Starter]\n{raw_s}\n\n[Core/Boots]\n{raw_c}",
        tok_in=ti_starter + ti_core,
        tok_out=to_starter + to_core,
    )


def _decide_situational(client, model, key, state, enemies,
                        pool: list[str], pool_ids: list[int],
                        game_time: float,
                        previous: list[str]) -> SituationalDecision:
    # Dedup contra o inventário REAL: itens que já viraram posse do jogador
    # (Zhonya está no core E no pool da Akali) não podem ser "recomendados"
    # de novo. Comparação por ID (não por nome) — IDs independem do locale
    # do cliente; displayName não.
    owned_ids = set(state.get("_itens_ids", []))
    pool = [n for n, i in zip(pool, pool_ids) if i not in owned_ids]
    if not pool:
        # Pool esgotado: todo situacional já está no inventário. Calar é a
        # resposta correta — e não queima tokens à toa.
        return SituationalDecision(
            momento_gt=game_time, item_recomendado="—", valido=True,
            razao="pool situacional esgotado — todos já no inventário",
        )
    payload = {
        "estado_jogador": {k: v for k, v in state.items()
                           if not k.startswith("_")},
        "inimigos_e_itens": enemies,
        "pool_situacionais": pool,
        "recomendacoes_anteriores": previous,
    }
    try:
        parsed, ti, to, raw = _call_groq_json(client, model, key,
                                               SYSTEM_SITUATIONAL, payload)
    except Exception as e:  # noqa: BLE001
        return SituationalDecision(momento_gt=game_time, item_recomendado="",
                                    valido=False, error=repr(e))
    item = str(parsed.get("item", "")).strip()
    valido = any(p.lower() == item.lower() or p.lower() in item.lower()
                 for p in pool)
    return SituationalDecision(
        momento_gt=game_time, item_recomendado=item, valido=valido,
        razao=str(parsed.get("razao", "")), raw=raw, tok_in=ti, tok_out=to,
    )


def _detect_champion_and_role(replay: Path) -> tuple[str, str]:
    with replay.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line).get("data", {})
            active = payload.get("activePlayer", {}) or {}
            me_name = active.get("riotId") or active.get("summonerName", "")
            for p in payload.get("allPlayers", []) or []:
                if (p.get("riotId") or p.get("summonerName", "")) == me_name:
                    if p.get("championName") and p.get("position"):
                        return p["championName"], p["position"]
    raise RuntimeError("Não foi possível detectar campeão/rota.")


def _run(client, replay: Path, model: str, key: str, baseline: Baseline,
         legendary_ids: frozenset[int],
         names: dict[int, str]) -> tuple[BuildPlan, list[SituationalDecision]]:
    plan: BuildPlan | None = None
    sits: list[SituationalDecision] = []
    pend = list(SITUATIONAL_AFTER_LEGENDARY)  # limiares de nº de lendários
    with replay.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line).get("data", {})
            gt = float(payload.get("gameData", {}).get("gameTime", 0))

            if plan is None and gt >= WARMUP_GT:
                enemies = _enemy_champions(payload)
                print(f"  [{_mmss(gt)}] BUILD PLAN — inimigos: "
                      f"{', '.join(e['champ'] for e in enemies) or '?'}",
                      flush=True)
                plan = _decide_build_plan(client, model, key, baseline, enemies)

            if plan is not None and pend:
                state = _player_state(payload)
                legcount = sum(1 for i in state["_itens_ids"]
                               if i in legendary_ids)
                while pend and legcount >= pend[0]:
                    th = pend.pop(0)
                    gatilho = f"{th} lendários → {th + 1}º item"
                    enemies_it = _enemy_threats(payload, legendary_ids, names)
                    prev = [s.item_recomendado for s in sits
                            if s.valido and s.item_recomendado]
                    print(f"  [{_mmss(gt)}] SITUACIONAL ({gatilho}) — "
                          f"{state['champ']} {state['kda']} "
                          f"ouro={state['ouro']}, "
                          f"inimigos c/ itens={len(enemies_it)}, já={prev}",
                          flush=True)
                    d = _decide_situational(
                        client, model, key, state, enemies_it,
                        baseline.situational_pool,
                        baseline.situational_pool_ids, gt, prev)
                    d.gatilho = gatilho
                    sits.append(d)

            if plan is not None and not pend:
                break
    if plan is None:
        plan = BuildPlan(error="warmup não atingido")
    return plan, sits


def _report(replay: Path, model: str, baseline: Baseline,
            plan: BuildPlan, sits: list[SituationalDecision]) -> Path:
    safe = re.sub(r'[/\\:*?"<>|]', "_", model)
    out = replay.with_name(f"prototype_v8_{safe}_{replay.stem}.md")
    tin = plan.tok_in + sum(s.tok_in for s in sits)
    tout = plan.tok_out + sum(s.tok_out for s in sits)
    cost = tin / 1e6 * PRICE_IN_PER_1M_USD + tout / 1e6 * PRICE_OUT_PER_1M_USD

    L = [f"# Protótipo v8 — `{replay.name}` ({model})\n"]
    L.append("> **IA decide core (ordem) + botas; starter é fixo do OP.GG.** "
             "Fonte de pools = OP.GG (stand-in patch 16.10, IDs verificados). "
             "Zero curadoria de ameaça — modelo raciocina sobre dado real.\n")
    starter_opts = " | ".join(
        f"{', '.join(opt['items'])} ({opt['winrate']:.1f}%)"
        for opt in baseline.starter_options
    )
    L.append(f"> **{baseline.campeao} {baseline.rota}** · "
             f"starter_options: {starter_opts} · "
             f"boots_pool: {', '.join(baseline.boots_pool)} · "
             f"core_pool: {', '.join(baseline.core_pool)}\n")
    L.append(f"> **Pool situacional OP.GG (4/5/6):** "
             f"{', '.join(baseline.situational_pool)}\n")

    L.append("\n## Decisão #1 — Build plan (warmup)\n")
    if plan.error:
        L.append(f"- ⚠️ **ERRO:** {plan.error}")
    else:
        flag = "OK" if plan.valido else f"FORA DO POOL: {plan.fora_do_pool}"
        desvio = ("= default OP.GG" if plan.core_order == baseline.core_pool
                  else f"DESVIOU do default ({' → '.join(baseline.core_pool)})")
        L.append(f"- **Starter:** {', '.join(plan.starter) or '—'} "
                 f"*(fixo do OP.GG, não é decisão da IA)*")
        L.append(f"- **Core (ordem):** {' → '.join(plan.core_order) or '—'} "
                 f"*({desvio})*")
        L.append(f"- **Botas:** {plan.boots or '—'}")
        L.append(f"- **Anti-fabricação:** {flag}")
        L.append(f"- **Razão:** {plan.razao or '—'}")
    L.append(f"- Tokens: in {plan.tok_in} · out {plan.tok_out}")

    L.append("\n## Decisões #2 — Situacionais (gatilho = progresso de build)\n")
    if not sits:
        L.append("> Nenhum situacional disparado: o jogador não fechou "
                 "lendários suficientes (gatilho por progresso, não relógio). "
                 "Comportamento correto — não há 4º/5º/6º a recomendar sem "
                 "core completo. (Replays de Practice Tool curtos não fecham "
                 "core; validar a camada situacional exige replay de jogo "
                 "real.)\n")
    L.append("| Gatilho | @gt | Item | Válido (no pool)? | Razão | Tokens |")
    L.append("|---|---|---|:---:|---|---|")
    for s in sits:
        err = f"⚠️ {s.error}" if s.error else ""
        L.append(f"| {s.gatilho or '?'} | {_mmss(s.momento_gt)} | "
                 f"{s.item_recomendado or '—'} {err}| "
                 f"{'OK' if s.valido else 'FORA DO POOL'} | "
                 f"{s.razao.replace('|','\\|') or '—'} | "
                 f"in={s.tok_in}/out={s.tok_out} |")

    L.append("\n## Resumo\n")
    L.append(f"- Chamadas IA: **{1 + len(sits)}**")
    L.append(f"- Tokens: in **{tin}** · out **{tout}** (total {tin + tout})")
    L.append(f"- Custo: **US$ {cost:.4f}** ≈ **R$ {cost * USD_TO_BRL:.3f}** "
             f"*(Groq grátis = R$0)*")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("replay", type=Path)
    ap.add_argument("--model", default="openai/gpt-oss-120b")
    args = ap.parse_args()

    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print('ERRO: $env:GROQ_API_KEY = "sua-key"', file=sys.stderr)
        return 1
    if not args.replay.exists():
        print(f"ERRO: replay não existe: {args.replay}", file=sys.stderr)
        return 1

    print(f"=== {args.replay.name} (v8: IA dona da build, zero curadoria) ===",
          flush=True)
    dd = DataDragonClient()
    names = dd.get_item_names()
    legendary_ids = frozenset(i for i, g in dd.get_item_prices().items()
                              if g >= LEGENDARY_TOTAL_THRESHOLD)

    champ, role = _detect_champion_and_role(args.replay)
    print(f"  Jogador: {champ} ({role})", flush=True)
    baseline = _build_baseline(champ, role, names)
    if baseline is None:
        print(f"ERRO: sem build OP.GG (stand-in) para {champ}. "
              f"Disponível: {list(OPGG_BUILDS)}", file=sys.stderr)
        return 1
    print(f"  core_pool: {baseline.core_pool}", flush=True)
    print(f"  pool 4/5/6: {baseline.situational_pool}", flush=True)
    print(f"  boots_pool: {baseline.boots_pool}", flush=True)

    with httpx.Client() as client:
        plan, sits = _run(client, args.replay, args.model, key,
                          baseline, legendary_ids, names)
    report = _report(args.replay, args.model, baseline, plan, sits)
    print(f"-> relatório: {report}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
