
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Load match data
file_path = Path("data/events/18245.json")

with file_path.open("r", encoding="utf-8") as file:
    events = json.load(file)

print(f"Total events loaded: {len(events)}")

# Convert StatsBomb timestamps to seconds
def timestamp_to_seconds(timestamp):
    parsed = datetime.strptime(timestamp, "%H:%M:%S.%f")
    return (
        parsed.hour * 3600
        + parsed.minute * 60
        + parsed.second
        + parsed.microsecond / 1_000_000
    )

# Group events by period and possession ID
possessions = defaultdict(list)

for event in events:
    possession_id = event.get("possession")
    period = event.get("period")
    owner = event.get("possession_team", {}).get("name")

    if possession_id is None or period is None or owner is None:
        continue

    possessions[(period, possession_id)].append(event)

# Calculate approximate recorded event span
summary = []

for (period, possession_id), possession_events in possessions.items():
    possession_events.sort(key=lambda e: e.get("index", 0))

    # Exclude match setup events from the timing calculation
    playable_events = [
        e for e in possession_events
        if e.get("type", {}).get("name") not in ("Starting XI", "Half Start")
        and e.get("timestamp") is not None
    ]

    if not playable_events:
        continue

    owner = playable_events[0].get("possession_team", {}).get("name")
    start_time = playable_events[0]["timestamp"]
    end_time = playable_events[-1]["timestamp"]

    duration = (
        timestamp_to_seconds(end_time)
        - timestamp_to_seconds(start_time)
    )

    summary.append({
        "period": period,
        "id": possession_id,
        "owner": owner,
        "start": start_time,
        "end": end_time,
        "duration": duration,
        "events": len(playable_events),
    })

# Show first 10 possession summaries
print("\n--- FIRST 10 POSSESSION SUMMARIES ---")

for p in summary[:10]:
    print(
        f"Period {p['period']} | ID {p['id']} | {p['owner']} | "
        f"{p['start']} to {p['end']} | "
        f"Recorded span: {p['duration']:.1f}s | "
        f"Events: {p['events']}"
    )

# Compare average recorded event spans by team
print("\n--- AVERAGE RECORDED EVENT SPAN BY TEAM ---")

team_durations = defaultdict(list)

for p in summary:
    if p["duration"] >= 0:
        team_durations[p["owner"]].append(p["duration"])

for team, durations in team_durations.items():
    print(
        f"{team}: {sum(durations) / len(durations):.1f}s average "
        f"across {len(durations)} possessions"
    )
