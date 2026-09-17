from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

ExperimentStatus = Literal["draft", "ready", "analyzing", "complete", "failed"]


class ExperimentMetadata(BaseModel):
    chip_id: str = Field(default="", max_length=120)
    well_id: str = Field(default="", max_length=80)
    cell_line: str = Field(default="", max_length=120)
    culture_day: int | None = Field(default=None, ge=0, le=3_650)
    microns_per_pixel: float | None = Field(default=None, gt=0.0, le=1_000.0)
    calibration_source: str = Field(default="", max_length=240)

    @model_validator(mode="after")
    def calibration_is_traceable(self) -> "ExperimentMetadata":
        self.chip_id = self.chip_id.strip()
        self.well_id = self.well_id.strip()
        self.cell_line = self.cell_line.strip()
        self.calibration_source = self.calibration_source.strip()
        if self.microns_per_pixel is not None and not self.calibration_source:
            raise ValueError(
                "La source de calibration est obligatoire lorsqu’une échelle est renseignée."
            )
        if self.microns_per_pixel is None and self.calibration_source:
            raise ValueError(
                "Une échelle en µm/pixel est obligatoire avec une source de calibration."
            )
        return self


class ExperimentCreate(ExperimentMetadata):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1_000)
    control_label: str = Field(default="Control", min_length=1, max_length=80)
    treatment_label: str = Field(default="Treatment", min_length=1, max_length=80)


class Experiment(ExperimentMetadata):
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
    duplicate_files: list[str] = Field(default_factory=list)
    rejection_reasons: dict[str, str] = Field(default_factory=dict)


class ImageRecord(BaseModel):
    """One stored image of an experiment, with a browser-displayable preview."""

    filename: str
    display_name: str
    size_bytes: int
    preview_url: str
    source_format: str
    source_mode: str
    source_bit_depth: int
    width: int
    height: int


class AnalysisEngine(BaseModel):
    id: str
    name: str
    task: Literal["segmentation", "quality-classification"] = "segmentation"
    kind: Literal["zero-training", "pretrained", "trained"]
    status: Literal["available", "experimental", "planned", "license-review"]
    runnable: bool = True
    unavailable_reason: str | None = None
    description: str
    training_required: bool
    limitations: list[str]


class AnalysisArtifact(BaseModel):
    filename: str
    kind: Literal["segmentation-overlay"]
    media_type: str = "image/png"
    url: str


class ImageAnalysis(BaseModel):
    analysis_type: Literal["segmentation"] = "segmentation"
    filename: str
    object_count: int
    foreground_fraction: float
    mean_object_area: float
    median_object_area: float
    mean_equivalent_diameter: float
    threshold: float
    foreground_polarity: Literal["bright", "dark"]
    overlay_url: str


class QualityImageAnalysis(BaseModel):
    analysis_type: Literal["quality-classification"] = "quality-classification"
    filename: str
    source_acquisition_mode: Literal["L", "RGB", "outside-training-domain"]
    probability_good_raw: float | None = Field(default=None, ge=0.0, le=1.0)
    review_required: Literal[True] = True
    interpretation: Literal["review-required", "outside-training-domain"]


class AnalysisResult(BaseModel):
    experiment_id: UUID
    analysis_version: str
    task: Literal["segmentation", "quality-classification"] = "segmentation"
    engine: AnalysisEngine
    image_count: int
    metrics: dict[str, float]
    image_results: list[ImageAnalysis | QualityImageAnalysis]
    artifacts: list[AnalysisArtifact]
    warnings: list[str]
    provenance: dict[str, str] = Field(default_factory=dict)
    experiment_metadata: ExperimentMetadata = Field(default_factory=ExperimentMetadata)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
