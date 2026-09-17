import sqlite3

from app.repository import ExperimentRepository
from app.schemas import AnalysisResult, ExperimentCreate, ExperimentMetadata


def test_experiment_persists_across_repository_instances(tmp_path) -> None:
    database_path = tmp_path / "test.sqlite3"
    first_repository = ExperimentRepository(database_path)
    created = first_repository.create(ExperimentCreate(name="Persistent experiment"))

    reloaded_repository = ExperimentRepository(database_path)
    reloaded = reloaded_repository.get(created.id)

    assert reloaded is not None
    assert reloaded.name == "Persistent experiment"


def test_restart_marks_interrupted_analysis_failed(tmp_path):
    repository = ExperimentRepository(tmp_path / "restart.sqlite3")
    experiment = repository.create(ExperimentCreate(name="Interrupted analysis"))
    repository.update_image_count(experiment.id, 1)
    assert repository.start_analysis(experiment.id)
    assert not repository.start_analysis(experiment.id)
    reloaded = ExperimentRepository(repository.database_path)
    reloaded.recover_interrupted_analyses()
    assert reloaded.get(experiment.id).status == "failed"
    assert reloaded.get(experiment.id).image_count == 1
    assert reloaded.start_analysis(experiment.id)


def test_repository_migrates_existing_experiment_table(tmp_path) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE experiments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                control_label TEXT NOT NULL,
                treatment_label TEXT NOT NULL,
                status TEXT NOT NULL,
                image_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    repository = ExperimentRepository(database_path)
    created = repository.create(
        ExperimentCreate(
            name="Migrated experiment",
            chip_id="chip-7",
            microns_per_pixel=0.65,
            calibration_source="Microscope export",
        )
    )

    assert repository.get(created.id).chip_id == "chip-7"
    assert repository.get(created.id).microns_per_pixel == 0.65


def test_metadata_update_invalidates_previous_result(tmp_path) -> None:
    repository = ExperimentRepository(tmp_path / "metadata.sqlite3")
    experiment = repository.create(ExperimentCreate(name="Calibrated experiment"))
    repository.update_image_count(experiment.id, 1)
    repository.save_result(
        AnalysisResult(
            experiment_id=experiment.id,
            analysis_version="fixture-v1",
            engine={
                "id": "fixture",
                "name": "Fixture",
                "kind": "zero-training",
                "status": "available",
                "description": "Fixture",
                "training_required": False,
                "limitations": ["Fixture only"],
            },
            image_count=0,
            metrics={},
            image_results=[],
            artifacts=[],
            warnings=[],
        )
    )
    repository.update_status(experiment.id, "complete")

    updated = repository.update_metadata(
        experiment.id,
        ExperimentMetadata(
            chip_id="chip-42",
            well_id="A03",
            cell_line="iPSC-01",
            culture_day=18,
            microns_per_pixel=0.65,
            calibration_source="Objective metadata",
        ),
    )

    assert updated is not None
    assert updated.status == "ready"
    assert updated.chip_id == "chip-42"
    assert repository.get_result(experiment.id) is None
