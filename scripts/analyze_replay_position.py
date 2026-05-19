#!/usr/bin/env python3
"""Analyze position field in replay data."""
import json
import sys
from pathlib import Path

replay_path = Path("recordings/game_20260515_203142.jsonl")

# Collect position data for Akali
positions = []
line_num = 0

print("Analyzing replay for Akali position...")
try:
    with open(replay_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_num += 1
            if line_num % 50 != 0:  # Sample every 50 lines
                continue

            try:
                record = json.loads(line)
                gt = record['data']['gameData']['gameTime']

                # Find Akali in allPlayers
                all_players = record['data']['allPlayers']
                for player in all_players:
                    if player.get('championName') == 'Akali' and not player.get('isBot', True):
                        position = player.get('position', 'NONE')
                        positions.append({
                            'tick': record.get('tick'),
                            'gt': round(gt, 1),
                            'position': position
                        })
                        break
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)

# Show the positions
print("\nAkali position throughout game (sampled every 50 lines):")
for p in positions:
    print(f"GT={p['gt']:7.1f}s, Tick={p['tick']:3d}, Position={p['position']}")

# Find when position becomes non-NONE
print("\n--- First non-NONE position ---")
found = False
for p in positions:
    if p['position'] != 'NONE':
        print(f"GT={p['gt']}s (Tick {p['tick']}), Position={p['position']}")
        found = True
        break

if not found:
    print("Position never becomes non-NONE (sampled every 50 lines)")

# Check exact values around GT=167
print("\n--- Exact position checks around GT=167 (2:47) ---")
line_num = 0
found_at_167 = False
try:
    with open(replay_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_num += 1
            try:
                record = json.loads(line)
                gt = record['data']['gameData']['gameTime']

                if 166 <= gt <= 168:
                    all_players = record['data']['allPlayers']
                    for player in all_players:
                        if player.get('championName') == 'Akali' and not player.get('isBot', True):
                            position = player.get('position', 'NONE')
                            print(f"GT={gt:.2f}s, Position={position}")
                            if not found_at_167:
                                found_at_167 = True
                            break
            except:
                pass
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)

if not found_at_167:
    print("No records found in the 166-168 GT range")
