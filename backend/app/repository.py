import json
import sqlite3
from pathlib import Path
from threading import RLock
from uuid import UUID

from app.config import get_settings
from app.schemas import AnalysisResult, Experiment, ExperimentCreate, ExperimentStatus


class ExperimentRepository:
    """Persistent repository backed by the Python standard-library SQLite driver."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    control_label TEXT NOT NULL,
                    treatment_label TEXT NOT NULL,
                    status TEXT NOT NULL,
                    image_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS analysis_results (
                    experiment_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(experiment_id) REFERENCES experiments(id)
                );
                """
            )

    @staticmethod
    def _row_to_experiment(row: sqlite3.Row) -> Experiment:
        return Experiment.model_validate(dict(row))

    def create(self, payload: ExperimentCreate) -> Experiment:
        experiment = Experiment(**payload.model_dump())
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO experiments (
                    id, name, description, control_label, treatment_label,
                    status, image_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(experiment.id),
                    experiment.name,
                    experiment.description,
                    experiment.control_label,
                    experiment.treatment_label,
                    experiment.status,
                    experiment.image_count,
                    experiment.created_at.isoformat(),
                ),
            )
        return experiment

    def list(self) -> list[Experiment]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM experiments ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_experiment(row) for row in rows]

    def get(self, experiment_id: UUID) -> Experiment | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM experiments WHERE id = ?", (str(experiment_id),)
            ).fetchone()
        return self._row_to_experiment(row) if row else None

    def update_image_count(self, experiment_id: UUID, image_count: int) -> Experiment | None:
        next_status = "ready" if image_count else "draft"
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE experiments SET image_count = ?, status = ? WHERE id = ?",
                (image_count, next_status, str(experiment_id)),
            )
        return self.get(experiment_id)

    def update_status(
        self, experiment_id: UUID, status: ExperimentStatus
    ) -> Experiment | None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE experiments SET status = ? WHERE id = ?",
                (status, str(experiment_id)),
            )
        return self.get(experiment_id)

    def save_result(self, result: AnalysisResult) -> None:
        payload = json.dumps(result.model_dump(mode="json"))
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_results (experiment_id, payload)
                VALUES (?, ?)
                ON CONFLICT(experiment_id) DO UPDATE SET payload = excluded.payload
                """,
                (str(result.experiment_id), payload),
            )

    def get_result(self, experiment_id: UUID) -> AnalysisResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM analysis_results WHERE experiment_id = ?",
                (str(experiment_id),),
            ).fetchone()
        return AnalysisResult.model_validate_json(row["payload"]) if row else None


repository = ExperimentRepository(get_settings().database_path)
