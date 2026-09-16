from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

ExperimentStatus = Literal["draft", "ready", "analyzing", "complete", "failed"]


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1_000)
    control_label: str = Field(default="Control", min_length=1, max_length=80)
    treatment_label: str = Field(default="Treatment", min_length=1, max_length=80)


class Experiment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    control_label: str = "Control"
    treatment_label: str = "Treatment"
    status: ExperimentStatus = "draft"
    image_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UploadSummary(BaseModel):
    experiment_id: UUID
    accepted_files: list[str]
    rejected_files: list[str]
    total_images: int


class AnalysisEngine(BaseModel):
    id: str
    name: str
    kind: Literal["zero-training", "pretrained", "trained"]
    status: Literal["available", "planned", "license-review"]
    description: str
    training_required: bool
    limitations: list[str]


class AnalysisArtifact(BaseModel):
    filename: str
    kind: Literal["segmentation-overlay"]
    media_type: str = "image/png"
    url: str


class ImageAnalysis(BaseModel):
    filename: str
    object_count: int
    foreground_fraction: float
    mean_object_area: float
    median_object_area: float
    mean_equivalent_diameter: float
    threshold: float
    foreground_polarity: Literal["bright", "dark"]
    overlay_url: str


class AnalysisResult(BaseModel):
    experiment_id: UUID
    analysis_version: str
    engine: AnalysisEngine
    image_count: int
    metrics: dict[str, float]
    image_results: list[ImageAnalysis]
    artifacts: list[AnalysisArtifact]
    warnings: list[str]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
