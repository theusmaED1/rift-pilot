"""Inspeciona um recording .jsonl para entender o schema."""
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(Path("recordings").glob("*.jsonl"))[-1]

with open(path, encoding="utf-8") as f:
    ticks = [json.loads(l) for l in f if l.strip()]

print(f"Recording: {path} — {len(ticks)} ticks\n")

# Unique event names
all_events = {}
for t in ticks:
    for ev in t["data"]["events"]["Events"]:
        name = ev["EventName"]
        if name not in all_events:
            all_events[name] = {k: v for k, v in ev.items() if k != "EventName"}

print("=== Eventos únicos ===")
for name, fields in all_events.items():
    print(f"  {name}: {fields}")

# Level and ability progression
print("\n=== Progressão de nível e habilidades ===")
prev_lvls = None
for t in ticks:
    ab = t["data"]["activePlayer"]["abilities"]
    lvls = {k: ab[k].get("abilityLevel", 0) for k in ["Q", "W", "E", "R"]}
    player_level = t["data"]["activePlayer"]["level"]
    if lvls != prev_lvls:
        print(f"  tick={t['tick']} player_level={player_level} abilities={lvls}")
        prev_lvls = lvls

# allPlayers snippet
print("\n=== allPlayers (tick 0, 1 jogador) ===")
p = ticks[0]["data"]["allPlayers"][0]
print(json.dumps({k: p[k] for k in ["championName", "level", "summonerName", "team", "scores"]}, indent=2, ensure_ascii=False))

# gameData sample
print("\n=== gameData (tick 0) ===")
print(json.dumps(ticks[0]["data"]["gameData"], indent=2))
