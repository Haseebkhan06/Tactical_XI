
import json
from urllib.request import urlopen

BASE = "https://raw.githubusercontent.com/hudl/open-data/master/data"

for season_id in (4, 41):
    url = f"{BASE}/matches/16/{season_id}.json"
    print(f"\n--- Season ID {season_id} ---")

    try:
        with urlopen(url, timeout=30) as response:
            matches = json.loads(response.read().decode("utf-8"))

        print("Total records:", len(matches))

        stages = {}
        for match in matches:
            stage = match.get("competition_stage")
            if isinstance(stage, dict):
                stage = stage.get("name")
            stage = str(stage or "UNKNOWN")
            stages[stage] = stages.get(stage, 0) + 1

        for stage, count in sorted(stages.items()):
            print(f"{stage}: {count}")

        if matches:
            print("\nExample record:")
            print(json.dumps(matches[0], indent=2)[:1800])

    except Exception as exc:
        print("Could not load:", exc)
