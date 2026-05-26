import csv
from pathlib import Path

JOURNAL_PATH = Path(
    "trade_journal.csv"
)

def update_trade_result(
    current_price
):

    if not JOURNAL_PATH.exists():
        return

    rows = []

    with open(
        JOURNAL_PATH,
        "r",
        encoding="utf8"
    ) as f:

        reader = csv.DictReader(
            f
        )

        for row in reader:

            if row.get(
                "result"
            ):
                rows.append(
                    row
                )
                continue

            entry = float(
                row["entry"]
                .replace(
                    ",",
                    ""
                )
            )

            sl = float(
                row["sl"]
                .replace(
                    ",",
                    ""
                )
            )

            tp1 = float(
                row["tp1"]
                .replace(
                    ",",
                    ""
                )
            )

            tp2 = float(
                row["tp2"]
                .replace(
                    ",",
                    ""
                )
            )

            result = ""

            if current_price <= tp2:
                result = "TP2"

            elif current_price <= tp1:
                result = "TP1"

            elif current_price >= sl:
                result = "SL"

            row[
                "result"
            ] = result

            rows.append(
                row
            )

    with open(
        JOURNAL_PATH,
        "w",
        newline="",
        encoding="utf8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=
            rows[0].keys()
        )

        writer.writeheader()

        writer.writerows(
            rows
        )