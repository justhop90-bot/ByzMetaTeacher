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
        "target_action_count": len(target_indices),
        "stop_count": len(stop_indices),
        "stops": [],
    }

    for index in stop_indices:
        action = actions[index]
        start = max(0, action.timestamp.total_seconds() - 15)
        end = action.timestamp.total_seconds() + 15
        context = [
            action_summary(candidate)
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
            "action": action_summary(action),
            "context": context,
        })

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
