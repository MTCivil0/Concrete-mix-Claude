"""
schemas.py
Simple dataclasses for inputs and outputs.
No external libraries needed — just Python built-ins.
"""
from dataclasses import dataclass, field


@dataclass
class MixDesignInput:
    fc_psi: int                          # Required compressive strength
    exposure_codes: list[str]            # e.g. ['F2', 'W1']
    agg_size: str                        # '3/4', '1/2', etc.
    slump: str                           # '1-2', '3-4', '6-7'
    fm_fa: float                         # Fineness modulus of fine aggregate
    sg_ca: float                         # Specific gravity, coarse aggregate
    sg_fa: float                         # Specific gravity, fine aggregate
    rodded_density_ca: float             # Oven-dry rodded bulk density, lbs/ft³
    agg_shape: str                       # Shape category
    flyash_pct: float = 0.0
    slag_pct: float = 0.0
    sf_pct: float = 0.0
    pcc_pct: float = 0.0                 # Precipitated Calcium Carbonate
    sg_flyash: float = 2.65
    sg_slag: float = 2.85
    sg_sf: float = 2.20
    sg_pcc: float = 2.71
    air_entrained: bool = True
    wcm_override: float | None = None
    field_notes: str = ""


@dataclass
class MixDesignResult:
    input_summary: MixDesignInput
    aci_result: dict                     # Raw output from aci211.calculate_mix()
    ai_analysis: str = ""               # Claude's narrative analysis
    risk_level: str = "Moderate"
    scm_notes: list[str] = field(default_factory=list)
    aci_compliance: list[str] = field(default_factory=list)
    qc_tests: list[str] = field(default_factory=list)
    recommendations: str = ""
