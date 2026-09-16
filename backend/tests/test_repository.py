from app.repository import ExperimentRepository
from app.schemas import ExperimentCreate


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
