from pydantic import BaseModel


class FeatureContribution(BaseModel):
    feature: str
    label: str
    unit: str
    value: float
    baseline: float
    z_score: float
    direction: str
    contribution: float
    ratio: float | None = None


class ExplainResponse(BaseModel):
    event_id: str
    attack_type: str
    risk_level: str
    anomaly_score: float
    is_anomaly: bool
    contributors: list[FeatureContribution]