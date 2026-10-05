#!/usr/bin/env python3
"""Forensic trace for replay object 19263 STOP/reset behavior."""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from mgz.model import parse_match


TARGET = 19263
RECORD = Path("rec.aoe2record")


def action_summary(action):
    player = action.player
    return {
        "t": action.timestamp.total_seconds(),
        "type": action.type.name,
        "player": {
            "number": player.number if player else None,
            "name": player.name if player else None,
        },
        "object_ids": action.payload.get("object_ids", []),
        "target_id": action.payload.get("target_id"),
        "payload_keys": sorted(action.payload.keys()),
    }


def main() -> int:
    with RECORD.open("rb") as handle:
        match = parse_match(handle)

    actions = match.actions
    target_indices = [
        i
        for i, action in enumerate(actions)
        if TARGET in action.payload.get("object_ids", [])
        or action.payload.get("target_id") == TARGET
    ]
    stop_indices = [
        i
        for i, action in enumerate(actions)
        if action.type.name == "STOP" and TARGET in action.payload.get("object_ids", [])
    ]

    initial_object_matches = []
    for player in match.players:
        for obj in player.objects:
            if TARGET in (obj.object_id, obj.instance_id):
                initial_object_matches.append({
                    "player": {
                        "number": player.number,
                        "name": player.name,
                    },
                    "object_id": obj.object_id,
                    "instance_id": obj.instance_id,
                    "class_id": obj.class_id,
                    "name": obj.name,
                    "index": obj.index,
                    "position": {
                        "x": obj.position.x,
                        "y": obj.position.y,
                    },
                })

    target_events = [
        action
        for action in actions
        if TARGET in action.payload.get("object_ids", [])
        or action.payload.get("target_id") == TARGET
    ]
    action_counts = {}
    player_counts = {}
    for action in target_events:
        action_counts[action.type.name] = action_counts.get(action.type.name, 0) + 1
        if action.player:
            key = f"{action.player.number}:{action.player.name}"
            player_counts[key] = player_counts.get(key, 0) + 1

    all_stop_counts = {}
    all_stop_by_player = {}
    for action in actions:
        if action.type.name != "STOP":
            continue
        player = (
            f"{action.player.number}:{action.player.name}"
            if action.player else "unknown"
        )
        all_stop_by_player[player] = all_stop_by_player.get(player, 0) + 1
        for object_id in action.payload.get("object_ids", []):
            all_stop_counts[object_id] = all_stop_counts.get(object_id, 0) + 1

    def compact(action):
        return {
            "t": action.timestamp.total_seconds(),
            "type": action.type.name,
            "player": (
                f"{action.player.number}:{action.player.name}"
                if action.player else None
            ),
            "object_ids": action.payload.get("object_ids", []),
            "target_id": action.payload.get("target_id"),
            "position": (
                {
                    "x": action.position.x,
                    "y": action.position.y,
                }
                if action.position else None
            ),
        }

    report = {
        "header": {
            "save_version": match.save_version,
            "game_version": match.game_version,
            "build_version": match.build_version,
            "duration_seconds": match.duration.total_seconds(),
            "players": [
                {
                    "number": p.number,
                    "name": p.name,
                    "civilization": p.civilization,
                }
                for p in match.players
            ],
        },
        "target": TARGET,
        "initial_object_matches": initial_object_matches,
        "target_action_count": len(target_events),
        "target_action_types": dict(sorted(action_counts.items())),
        "target_action_players": dict(sorted(player_counts.items())),
        "target_first_events": [compact(action) for action in target_events[:20]],
        "target_last_events": [compact(action) for action in target_events[-20:]],
        "stop_count_for_target": len(stop_indices),
        "all_replay_stop_count": sum(all_stop_counts.values()),
        "all_replay_stop_by_player": dict(sorted(all_stop_by_player.items())),
        "all_replay_stop_top_objects": sorted(
            all_stop_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:20],
        "stops": [],
    }

    for index in stop_indices:
        action = actions[index]
        start = max(0, action.timestamp.total_seconds() - 15)
        end = action.timestamp.total_seconds() + 15
        context = [
            compact(candidate)
            for candidate in actions
            if start <= candidate.timestamp.total_seconds() <= end
            and (
                TARGET in candidate.payload.get("object_ids", [])
                or candidate.payload.get("target_id") == TARGET
                or (
                    action.player
                    and candidate.player
                    and candidate.player.number == action.player.number
                )
            )
        ]
        report["stops"].append({
            "index": index,
            "action": compact(action),
            "context": context,
        })

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
