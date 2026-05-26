import csv
from pathlib import Path
from datetime import datetime

JOURNAL_PATH = Path(
    "trade_journal.csv"
)

def log_trade(payload):

    row = {
        "time":
        datetime.now()
        .isoformat(),

        "h4":
        payload.get(
            "h4_bias"
        ),

        "m15":
        payload.get(
            "m15_entry"
        ),

        "entry":
        payload.get(
            "entry"
        ),

        "sl":
        payload.get(
            "sl"
        ),

        "tp1":
        payload.get(
            "tp1"
        ),

        "tp2":
        payload.get(
            "tp2"
        ),

        "macro":
        payload.get(
            "macro"
        ),

        "liquidity": payload.get("liquidity"),
        "ai": payload.get("ai_bias"),
        "result": ""
    }

    file_exists = (
        JOURNAL_PATH
        .exists()
    )

    with open(
        JOURNAL_PATH,
        "a",
        newline="",
        encoding="utf8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=
            row.keys()
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            row
        )