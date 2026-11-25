
import json

from pyflow import Task, Workflow, run

from examples.demo_workflow import (
    read_csv,
    clean_data,
    aggregate_data,
    generate_json,
)


def test_csv_to_json_workflow(tmp_path):
    csv_file = tmp_path / "sales.csv"
    json_file = tmp_path / "report.json"

    csv_file.write_text(
        "category,amount\n"
        "Elektronika,1200\n"
        "Odziez,250\n"
        "Elektronika,800\n"
        "Sport,150\n",
        encoding="utf-8",
    )

    workflow = Workflow()

    workflow.add_task(Task(
        name="read_csv",
        function=read_csv,
        params={"file": str(csv_file)},
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
        params={"file": str(json_file)},
    ))

    result = run(workflow)

    assert result.succeeded is True
    assert result.outputs["generate_json"]["total_amount"] == 2400
    assert result.outputs["generate_json"]["valid_records"] == 4

    assert result.task_states["read_csv"].status.value == "SUCCEEDED"
    assert result.task_states["clean_data"].status.value == "SUCCEEDED"
    assert result.task_states["aggregate_data"].status.value == "SUCCEEDED"
    assert result.task_states["generate_json"].status.value == "SUCCEEDED"

    assert json_file.exists()

    saved_report = json.loads(json_file.read_text(encoding="utf-8"))

    assert saved_report["categories"] == {
        "Elektronika": 2000,
        "Odziez": 250,
        "Sport": 150,
    }
