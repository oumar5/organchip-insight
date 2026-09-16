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
