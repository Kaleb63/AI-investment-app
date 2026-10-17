from pydantic import BaseModel, ConfigDict, Field


class EvidenceSelection(BaseModel):
    """AI may select verified facts, but cannot supply prose or financial values."""

    model_config = ConfigDict(extra="forbid", strict=True, revalidate_instances="always")

    evidence_ids: list[str] = Field(min_length=1, max_length=12)
