from threading import RLock
from uuid import UUID

from app.schemas import AnalysisResult, Experiment, ExperimentCreate, ExperimentStatus


class ExperimentRepository:
    """Thread-safe in-memory repository for the initial demonstrator.

    The interface deliberately isolates storage so SQLite or PostgreSQL can be
    introduced without changing the HTTP or analysis layers.
    """

    def __init__(self) -> None:
        self._experiments: dict[UUID, Experiment] = {}
        self._results: dict[UUID, AnalysisResult] = {}
        self._lock = RLock()

    def create(self, payload: ExperimentCreate) -> Experiment:
        experiment = Experiment(**payload.model_dump())
        with self._lock:
            self._experiments[experiment.id] = experiment
        return experiment

    def list(self) -> list[Experiment]:
        with self._lock:
            return sorted(
                self._experiments.values(),
                key=lambda experiment: experiment.created_at,
                reverse=True,
            )

    def get(self, experiment_id: UUID) -> Experiment | None:
        with self._lock:
            return self._experiments.get(experiment_id)

    def update_image_count(self, experiment_id: UUID, image_count: int) -> Experiment | None:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return None
            updated = experiment.model_copy(
                update={"image_count": image_count, "status": "ready" if image_count else "draft"}
            )
            self._experiments[experiment_id] = updated
            return updated

    def update_status(
        self, experiment_id: UUID, status: ExperimentStatus
    ) -> Experiment | None:
        with self._lock:
            experiment = self._experiments.get(experiment_id)
            if experiment is None:
                return None
            updated = experiment.model_copy(update={"status": status})
            self._experiments[experiment_id] = updated
            return updated

    def save_result(self, result: AnalysisResult) -> None:
        with self._lock:
            self._results[result.experiment_id] = result

    def get_result(self, experiment_id: UUID) -> AnalysisResult | None:
        with self._lock:
            return self._results.get(experiment_id)


repository = ExperimentRepository()

