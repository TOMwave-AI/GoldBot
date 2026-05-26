import csv
from pathlib import Path
from datetime import datetime

JOURNAL_PATH = Path(
    "trade_journal.csv"
)

TIMEOUT_MINUTES = 240


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

            risk = abs(
                entry - sl
            )

            reward_tp1 = abs(
                entry - tp1
            )

            reward_tp2 = abs(
                entry - tp2
            )

            row[
                "r_tp1"
            ] = round(
                reward_tp1 /
                risk,
                2
            )

            row[
                "r_tp2"
            ] = round(
                reward_tp2 /
                risk,
                2
            )
            r2 = row[
                "r_tp2"
            ]

            if r2 >= 4:
                row["grade"] = "GOD"

            elif r2 >= 3:
                row["grade"] = "S"

            elif r2 >= 2:
                row["grade"] = "A"

            elif r2 >= 1.5:
                row["grade"] = "B"

            else:
                row["grade"] = "REJECT"

            is_sell = (
                tp1 < entry
            )

            if is_sell:

                if current_price <= tp2:
                    result = "TP2"

                elif current_price <= tp1:
                    result = "TP1"

                elif current_price >= sl:
                    result = "SL"

            else:

                if current_price >= tp2:
                    result = "TP2"

                elif current_price >= tp1:
                    result = "TP1"

                elif current_price <= sl:
                    result = "SL"

            row[
                "result"
            ] = result

            rows.append(
                row
            )

    if not rows:
        return

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