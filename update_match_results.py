
import json
from pathlib import Path

CATALOG_PATH = Path("data/matches.json")

# Match IDs are from the existing Tactical_XI catalogue.
# Penalty scores are added only where the shootout result is known.
RESULTS = {
    "18235": {
        "winner": "Inter Milan",
        "result_type": "regular_time_or_extra_time",
        "result_note": "Inter Milan won 2-0.",
    },
    "3750200": {
        "winner": "AC Milan",
        "result_type": "regular_time_or_extra_time",
        "result_note": "AC Milan won 2-1.",
    },
    "2302764": {
        "winner": "Liverpool",
        "result_type": "penalties",
        "penalty_home_score": 2,
        "penalty_away_score": 3,
        "penalty_score": "2-3",
        "result_note": (
            "Liverpool won 3-2 on penalties after the match "
            "finished 3-3 after extra time."
        ),
    },
    "3750235": {
        "winner": "Ajax",
        "result_type": "regular_time_or_extra_time",
        "result_note": "Ajax won 2-0.",
    },
    "3869685": {
        "winner": "Argentina",
        "result_type": "penalties",
        "penalty_home_score": 4,
        "penalty_away_score": 2,
        "penalty_score": "4-2",
        "result_note": (
            "Argentina won 4-2 on penalties after the match "
            "finished 3-3 after extra time."
        ),
    },
    "3869684": {
        "winner": "Croatia",
        "result_type": "regular_time_or_extra_time",
        "result_note": "Croatia won 2-1.",
    },
    "3869552": {
        "winner": "France",
        "result_type": "regular_time_or_extra_time",
        "result_note": "France won 2-0.",
    },
    "3869519": {
        "winner": "Argentina",
        "result_type": "regular_time_or_extra_time",
        "result_note": "Argentina won 3-0.",
    },
    "3869486": {
        "winner": "Morocco",
        "result_type": "regular_time_or_extra_time",
        "result_note": "Morocco won 1-0.",
    },
    "3869354": {
        "winner": "France",
        "result_type": "regular_time_or_extra_time",
        "result_note": "France won 2-1.",
    },
}


def main():
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {CATALOG_PATH}. "
            "Run this script from the Tactical_XI project root."
        )

    with CATALOG_PATH.open("r", encoding="utf-8") as file:
        catalogue = json.load(file)

    # Support either a JSON list or an object containing a matches list.
    if isinstance(catalogue, list):
        matches = catalogue
    elif isinstance(catalogue, dict) and isinstance(
        catalogue.get("matches"), list
    ):
        matches = catalogue["matches"]
    else:
        raise ValueError(
            "Unexpected matches.json format. Expected a list of matches "
            "or an object with a 'matches' list."
        )

    updated = []
    unmatched = []

    for match in matches:
        match_id = str(match.get("match_id", match.get("id", "")))
        result = RESULTS.get(match_id)

        if result is None:
            unmatched.append(match_id or "(missing match ID)")
            continue

        # Preserve all existing catalogue fields and original scorelines.
        match.update(result)
        updated.append(match_id)

    # Validate that shootout metadata is internally consistent.
    for match in matches:
        if match.get("result_type") == "penalties":
            if (
                match.get("penalty_home_score") is None
                or match.get("penalty_away_score") is None
                or not match.get("winner")
            ):
                raise ValueError(
                    f"Incomplete penalty metadata for match "
                    f"{match.get('match_id', match.get('id'))}"
                )

    with CATALOG_PATH.open("w", encoding="utf-8") as file:
        json.dump(catalogue, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"Updated {len(updated)} matches in {CATALOG_PATH}")
    print("Original home_score and away_score fields were preserved.")

    if unmatched:
        print("Catalogue entries without a result update:")
        for match_id in unmatched:
            print(f"  - {match_id}")

    print("\nPenalty shootout metadata:")
    for match in matches:
        if match.get("result_type") == "penalties":
            print(
                f"  {match.get('home_team')} vs {match.get('away_team')}: "
                f"{match.get('home_score')}-{match.get('away_score')} "
                f"after extra time; penalties "
                f"{match.get('penalty_score')}; winner: "
                f"{match.get('winner')}"
            )


if __name__ == "__main__":
    main()
