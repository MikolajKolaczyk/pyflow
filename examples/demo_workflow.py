
import csv
import json
from pathlib import Path
from typing import Any

from pyflow import Task, Workflow, run


BASE_DIR = Path(__file__).parent
CSV_FILE = BASE_DIR / "data" / "sales.csv"
JSON_FILE = BASE_DIR / "report.json"
TEXT_REPORT_FILE = BASE_DIR / "execution_report.txt"


def read_csv(inputs: dict[str, Any], params: dict[str, Any]) -> list[dict]:
    """Odczytuje dane z pliku CSV."""
    with open(params["file"], "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def clean_data(inputs: dict[str, Any], params: dict[str, Any]) -> dict:
    """Czyści i waliduje rekordy."""
    records = inputs["read_csv"]
    valid_records = []
    rejected_records = 0

    for record in records:
        category = record["category"].strip()

        try:
            amount = int(record["amount"])
        except (ValueError, TypeError):
            rejected_records += 1
            continue

        if not category or amount <= 0:
            rejected_records += 1
            continue

        valid_records.append({
            "category": category,
            "amount": amount,
        })

    return {
        "records": valid_records,
        "rejected_records": rejected_records,
    }


def aggregate_data(inputs: dict[str, Any], params: dict[str, Any]) -> dict:
    """Agreguje sprzedaż według kategorii."""
    cleaned = inputs["clean_data"]
    totals = {}

    for record in cleaned["records"]:
        category = record["category"]
        amount = record["amount"]
        totals[category] = totals.get(category, 0) + amount

    return {
        "totals": dict(sorted(totals.items())),
        "valid_records": len(cleaned["records"]),
        "rejected_records": cleaned["rejected_records"],
        "total_amount": sum(totals.values()),
    }


def generate_json(inputs: dict[str, Any], params: dict[str, Any]) -> dict:
    """Generuje raport JSON."""
    data = inputs["aggregate_data"]

    report = {
        "title": "Raport sprzedaży",
        "categories": data["totals"],
        "valid_records": data["valid_records"],
        "rejected_records": data["rejected_records"],
        "total_amount": data["total_amount"],
    }

    with open(params["file"], "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=4)

    return report


def main() -> None:
    workflow = Workflow()

    workflow.add_task(Task(
        name="read_csv",
        function=read_csv,
        params={"file": str(CSV_FILE)},
    ))

    workflow.add_task(Task(
        name="clean_data",
        function=clean_data,
        dependencies=frozenset({"read_csv"}),
        params={},
    ))

    workflow.add_task(Task(
        name="aggregate_data",
        function=aggregate_data,
        dependencies=frozenset({"clean_data"}),
        params={},
    ))

    workflow.add_task(Task(
        name="generate_json",
        function=generate_json,
        dependencies=frozenset({"aggregate_data"}),
        params={"file": str(JSON_FILE)},
    ))

    result = run(workflow)

    report_lines = [
        "RAPORT WYKONANIA WORKFLOW",
        "=" * 35,
        "",
    ]

    for task_name, state in result.task_states.items():
        report_lines.append(
            f"{task_name}: {state.status.value} | "
            f"Czas: {state.duration:.6f} s"
        )

    report_lines.extend([
        "",
        f"Czas całego przebiegu: {result.duration:.6f} s",
        f"Sukces: {result.succeeded}",
    ])

    TEXT_REPORT_FILE.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print("Workflow zakończony!")
    print(json.dumps(
        result.outputs["generate_json"],
        indent=4,
        ensure_ascii=False,
    ))
    print(f"Raport JSON: {JSON_FILE}")
    print(f"Raport tekstowy: {TEXT_REPORT_FILE}")


if __name__ == "__main__":
    main()
