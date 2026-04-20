"""
schemas.py — Data classes for inputs and outputs.
"""
from dataclasses import dataclass, field


@dataclass
class ProjectInfo:
    project_name: str = ""
    location: str = ""
    prepared_by: str = ""
    company: str = ""
    cement_producer: str = ""
    flyash_producer: str = ""
    slag_producer: str = ""
    sf_producer: str = ""
    pcc_producer: str = ""


@dataclass
class MixDesignInput:
    fc_psi: int
    exposure_codes: list[str]
    agg_size: str
    slump: str
    fm_fa: float
    sg_ca: float
    sg_fa: float
    rodded_density_ca: float
    agg_shape: str
    flyash_pct: float = 0.0
    slag_pct: float = 0.0
    sf_pct: float = 0.0
    pcc_pct: float = 0.0
    sg_flyash: float = 2.65
    sg_slag: float = 2.85
    sg_sf: float = 2.20
    sg_pcc: float = 2.71
    air_entrained: bool = True
    wcm_override: float | None = None
    field_notes: str = ""
    project_info: ProjectInfo = field(default_factory=ProjectInfo)
    uploaded_file_name: str = ""


@dataclass
class MixDesignResult:
    input_summary: MixDesignInput
    aci_result: dict
    ai_analysis: str = ""
    risk_level: str = "Moderate"
    scm_notes: list[str] = field(default_factory=list)
    aci_compliance: list[str] = field(default_factory=list)
    qc_tests: list[str] = field(default_factory=list)
    recommendations: str = ""
    file_review_notes: str = ""
