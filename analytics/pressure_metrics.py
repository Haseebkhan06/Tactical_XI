
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime


DATA_PATH = Path("data/events/18245.json")
RECOVERY_WINDOW_SECONDS = 5


def timestamp_to_seconds(timestamp):
    """Convert a period-relative timestamp to seconds."""
    parsed = datetime.strptime(timestamp, "%H:%M:%S.%f")
    return (
        parsed.hour * 3600
        + parsed.minute * 60
        + parsed.second
        + parsed.microsecond / 1_000_000
    )


def get_match_clock_minutes(period, timestamp):
    """
    Convert period-relative timestamps into a continuous match clock.

    Period 1: 0 minutes onward.
    Period 2: starts at 45 minutes.
    Other periods: not handled by this two-half match clock.
    """
    if period not in (1, 2) or not timestamp:
        return None

    seconds = timestamp_to_seconds(timestamp)

    if period == 1:
        return round(seconds / 60, 2)

    return round(45 + seconds / 60, 2)


def get_name(event, field):
    return event.get(field, {}).get("name")


def analyze_pressing(events):
    events = sorted(events, key=lambda e: e.get("index", 0))

    # Count distinct recorded possessions for each possession owner.
    possessions = defaultdict(set)

    for event in events:
        owner = get_name(event, "possession_team")
        possession_id = event.get("possession")
        period = event.get("period")

        if owner and possession_id is not None and period is not None:
            possessions[owner].add((period, possession_id))

    # Count pressures applied against the opposing possession owner.
    defensive_pressures = []

    for i, event in enumerate(events):
        if get_name(event, "type") != "Pressure":
            continue

        pressing_team = get_name(event, "team")
        possession_owner = get_name(event, "possession_team")
        period = event.get("period")
        timestamp = event.get("timestamp")

        if not pressing_team or not possession_owner or not timestamp:
            continue

        if pressing_team == possession_owner:
            continue

        defensive_pressures.append({
            "event_index": i,
            "team": pressing_team,
            "opponent": possession_owner,
            "period": period,
            "timestamp": timestamp,
            "match_minute": get_match_clock_minutes(period, timestamp),
            "location": event.get("location"),
        })

    # Find a same-team Ball Recovery within five seconds after each pressure.
    # Never match a pressure to a recovery from a different period.
    successful_candidates = []

    for pressure in defensive_pressures:
        start_index = pressure["event_index"]
        start_time = timestamp_to_seconds(pressure["timestamp"])
        recovery_found = None

        for next_event in events[start_index + 1:]:
            if next_event.get("period") != pressure["period"]:
                break

            next_timestamp = next_event.get("timestamp")
            if not next_timestamp:
                continue

            elapsed = timestamp_to_seconds(next_timestamp) - start_time

            if elapsed > RECOVERY_WINDOW_SECONDS:
                break

            if elapsed < 0:
                continue

            if (
                get_name(next_event, "type") == "Ball Recovery"
                and get_name(next_event, "team") == pressure["team"]
            ):
                recovery_found = {
                    "team": pressure["team"],
                    "opponent": pressure["opponent"],
                    "period": pressure["period"],
                    "pressure_timestamp": pressure["timestamp"],
                    "pressure_match_minute": pressure["match_minute"],
                    "recovery_timestamp": next_timestamp,
                    "recovery_match_minute": get_match_clock_minutes(
                        next_event.get("period"),
                        next_timestamp
                    ),
                    "seconds_to_recovery": round(elapsed, 2),
                    "pressure_location": pressure["location"],
                    "recovery_location": next_event.get("location"),
                }
                break

        if recovery_found:
            successful_candidates.append(recovery_found)

    teams = sorted(set(possessions) | {
        pressure["team"] for pressure in defensive_pressures
    })

    summary = {}

    for team in teams:
        opponent_possessions = sum(
            len(ids)
            for owner, ids in possessions.items()
            if owner != team
        )

        pressures = [
            pressure for pressure in defensive_pressures
            if pressure["team"] == team
        ]

        recoveries = [
            recovery for recovery in successful_candidates
            if recovery["team"] == team
        ]

        summary[team] = {
            "opponent_possessions": opponent_possessions,
            "defensive_pressures": len(pressures),
            "pressures_per_100_opponent_possessions": round(
                len(pressures) / opponent_possessions * 100, 2
            ) if opponent_possessions else None,
            "pressures_followed_by_recovery_within_5s": len(recoveries),
            "candidate_recovery_rate_percent": round(
                len(recoveries) / len(pressures) * 100, 2
            ) if pressures else None,
        }

    return {
        "match": "Liverpool vs Real Madrid",
        "recovery_window_seconds": RECOVERY_WINDOW_SECONDS,
        "teams": summary,
        "candidate_sequences": successful_candidates,
        "method_note": (
            "A pressure followed by a same-team ball recovery within "
            "five seconds is a candidate sequence, not proof of causation. "
            "Possession counts are distinct recorded possession IDs. "
            "Match minutes are continuous for the two regular-time halves: "
            "period 1 starts at 0 minutes and period 2 starts at 45 minutes. "
            "Stoppage time may extend beyond 45 or 90 minutes."
        ),
    }


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Match data not found: {DATA_PATH.resolve()}"
        )

    with DATA_PATH.open("r", encoding="utf-8") as file:
        events = json.load(file)

    result = analyze_pressing(events)

    print(f"\n{result['match']}")
    print("=" * 50)

    for team, metrics in result["teams"].items():
        print(f"\n{team}")
        for metric, value in metrics.items():
            print(f"  {metric}: {value}")

    print(
        f"\nCandidate pressure-to-recovery sequences: "
        f"{len(result['candidate_sequences'])}"
    )

    print("\nCandidate sequence timeline:")
    for sequence in sorted(
        result["candidate_sequences"],
        key=lambda item: item["pressure_match_minute"]
    ):
        print(
            f"  {sequence['team']}: "
            f"{sequence['pressure_match_minute']:.2f}' pressure "
            f"-> {sequence['recovery_match_minute']:.2f}' recovery "
            f"({sequence['seconds_to_recovery']}s)"
        )


if __name__ == "__main__":
    main()
