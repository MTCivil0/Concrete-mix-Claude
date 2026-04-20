"""
aci211.py
All ACI 211.1 lookup tables and mix design calculations.
Extracted from RSCA_mix_design.xlsx (PCA method).
"""

# ── Exposure class limits (ACI 318 Table 19.3) ───────────────────────────────
# Returns (max_wcm, min_fc_psi). None = no limit from this class.
EXPOSURE_LIMITS = {
    "F0": (None, None),
    "F1": (0.55, 3500),
    "F2": (0.45, 4500),
    "F3": (0.40, 5000),
    "W0": (None, None),
    "W1": (0.50, 4000),
    "S0": (None, None),
    "S1": (0.50, 4000),
    "S2": (0.45, 4500),
    "S3": (0.40, 5000),
    "C0": (None, None),
    "C2": (0.40, 5000),
}

# ── Suggested w/cm from target f'c (ACI 211.1 Table 6.3.4) ──────────────────
# {f'c_psi: (non_air_wcm, air_wcm)}
WCM_FROM_FC = {
    7000: (0.33, None),
    6000: (0.41, 0.32),
    5000: (0.48, 0.40),
    4000: (0.57, 0.48),
    3000: (0.68, 0.59),
    2000: (0.82, 0.74),
}

# ── Air content % (ACI 211.1 Table 6.3.3) ────────────────────────────────────
# {agg_size_in: {exposure: air_%}}
AIR_CONTENT = {
    "3/8": {"F0": 4.5, "F1": 6.0, "F2": 7.5, "F3": 7.5},
    "1/2": {"F0": 4.0, "F1": 5.5, "F2": 7.0, "F3": 7.0},
    "3/4": {"F0": 3.5, "F1": 5.0, "F2": 6.0, "F3": 6.0},
    "1":   {"F0": 3.0, "F1": 4.5, "F2": 6.0, "F3": 6.0},
    "1-1/2": {"F0": 2.5, "F1": 4.5, "F2": 5.5, "F3": 5.5},
    "2":   {"F0": 2.0, "F1": 3.5, "F2": 5.0, "F3": 5.0},
}

# ── Mixing water (lbs/CY) — ACI 211.1 Table 6.3.3 ────────────────────────────
# {agg_size_in: {slump_range: (non_air_lbs, air_lbs)}}
WATER_CONTENT = {
    "3/8": {"1-2": (350, 305), "3-4": (385, 340), "6-7": (410, 365)},
    "1/2": {"1-2": (335, 295), "3-4": (365, 325), "6-7": (385, 345)},
    "3/4": {"1-2": (315, 280), "3-4": (340, 305), "6-7": (360, 325)},
    "1":   {"1-2": (300, 270), "3-4": (325, 295), "6-7": (340, 310)},
    "1-1/2": {"1-2": (275, 250), "3-4": (300, 275), "6-7": (315, 290)},
    "2":   {"1-2": (260, 240), "3-4": (285, 265), "6-7": (300, 280)},
}

# ── Bulk volume of CA (ACI 211.1 Table 6.3.6) ────────────────────────────────
# {FM: {agg_size_in: bulk_volume_fraction}}
BULK_VOLUME_CA = {
    2.40: {"3/8": 0.50, "1/2": 0.59, "3/4": 0.66, "1": 0.71, "1-1/2": 0.75, "2": 0.78},
    2.50: {"3/8": 0.49, "1/2": 0.58, "3/4": 0.65, "1": 0.70, "1-1/2": 0.74, "2": 0.77},
    2.60: {"3/8": 0.48, "1/2": 0.57, "3/4": 0.64, "1": 0.69, "1-1/2": 0.73, "2": 0.76},
    2.70: {"3/8": 0.47, "1/2": 0.56, "3/4": 0.63, "1": 0.68, "1-1/2": 0.72, "2": 0.75},
    2.80: {"3/8": 0.46, "1/2": 0.55, "3/4": 0.62, "1": 0.67, "1-1/2": 0.71, "2": 0.74},
    2.90: {"3/8": 0.45, "1/2": 0.54, "3/4": 0.61, "1": 0.66, "1-1/2": 0.70, "2": 0.73},
    3.00: {"3/8": 0.44, "1/2": 0.53, "3/4": 0.60, "1": 0.65, "1-1/2": 0.69, "2": 0.72},
}

# ── Minimum cementitious content (lbs/CY) — ACI 211.1 ────────────────────────
MIN_CEMENT = {
    "3/8": 610,
    "1/2": 590,
    "3/4": 540,
    "1":   520,
    "1-1/2": 470,
    "2":   440,
}

# ── Aggregate shape water reduction (lbs/CY) ─────────────────────────────────
SHAPE_WATER_REDUCTION = {
    "Angular aggregate": 0,
    "Subangular aggregate": -20,
    "Gravel with crushed faces": -35,
    "Rounded river gravel": -45,
}

# ── Specific gravities (defaults, user can override) ─────────────────────────
DEFAULT_SG = {
    "cement": 3.15,
    "fly_ash": 2.65,
    "slag": 2.85,
    "silica_fume": 2.20,
    "pcc": 2.71,       # Precipitated Calcium Carbonate
    "water": 1.00,
}

CY_TO_FT3 = 27.0   # 1 cubic yard = 27 cubic feet


# ─────────────────────────────────────────────────────────────────────────────
# Lookup helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_governing_limits(exposure_codes: list[str]) -> tuple[float, int]:
    """
    Given a list of exposure codes (e.g. ['F2', 'W1']),
    return the most restrictive (lowest max_wcm, highest min_fc).
    """
    max_wcm = 1.0
    min_fc = 0
    for code in exposure_codes:
        wcm, fc = EXPOSURE_LIMITS.get(code, (None, None))
        if wcm is not None:
            max_wcm = min(max_wcm, wcm)
        if fc is not None:
            min_fc = max(min_fc, fc)
    if max_wcm == 1.0:
        max_wcm = None
    return max_wcm, min_fc


def get_wcm_from_fc(fc_psi: int, air_entrained: bool) -> float:
    """Interpolate w/cm from target f'c using ACI 211.1 Table 6.3.4."""
    strengths = sorted(WCM_FROM_FC.keys(), reverse=True)
    col = 1 if air_entrained else 0

    for i, s in enumerate(strengths):
        if fc_psi >= s:
            wcm = WCM_FROM_FC[s][col]
            if wcm is None:
                # Extrapolate from next lower
                wcm = WCM_FROM_FC[strengths[i + 1]][col]
            return wcm

    # fc below 2000 — use 0.82 / 0.74
    return WCM_FROM_FC[2000][col]


def get_air_content(agg_size: str, freeze_thaw_class: str) -> float:
    """Return recommended air content % for given agg size and F-class."""
    return AIR_CONTENT.get(agg_size, {}).get(freeze_thaw_class, 3.5)


def get_water_content(agg_size: str, slump: str, air_entrained: bool) -> float:
    """Return initial mixing water in lbs/CY."""
    row = WATER_CONTENT.get(agg_size, WATER_CONTENT["3/4"])
    values = row.get(slump, row["3-4"])
    return float(values[1] if air_entrained else values[0])


def interpolate_bulk_volume_ca(fm: float, agg_size: str) -> float:
    """Interpolate bulk volume of CA from ACI 211.1 Table 6.3.6."""
    fms = sorted(BULK_VOLUME_CA.keys())
    if fm <= fms[0]:
        return BULK_VOLUME_CA[fms[0]][agg_size]
    if fm >= fms[-1]:
        return BULK_VOLUME_CA[fms[-1]][agg_size]
    for i in range(len(fms) - 1):
        if fms[i] <= fm <= fms[i + 1]:
            lo, hi = fms[i], fms[i + 1]
            t = (fm - lo) / (hi - lo)
            v_lo = BULK_VOLUME_CA[lo].get(agg_size, 0.63)
            v_hi = BULK_VOLUME_CA[hi].get(agg_size, 0.63)
            return v_lo + t * (v_hi - v_lo)
    return 0.63


# ─────────────────────────────────────────────────────────────────────────────
# Main calculation engine
# ─────────────────────────────────────────────────────────────────────────────

def calculate_mix(
    fc_psi: int,
    exposure_codes: list[str],
    agg_size: str,
    slump: str,
    fm_fa: float,
    sg_ca: float,
    sg_fa: float,
    rodded_density_ca: float,   # lbs/ft³
    agg_shape: str,
    flyash_pct: float,
    slag_pct: float,
    sf_pct: float,
    pcc_pct: float,
    sg_flyash: float = 2.65,
    sg_slag: float = 2.85,
    sg_sf: float = 2.20,
    sg_pcc: float = 2.71,
    air_entrained: bool = True,
    wcm_override: float | None = None,
) -> dict:
    """
    Full ACI 211.1 mix design calculation.
    Returns a dict with all proportions and flags.
    """

    # ── Step 1: Governing exposure limits ────────────────────────────────────
    freeze_thaw_codes = [c for c in exposure_codes if c.startswith("F")]
    ft_class = freeze_thaw_codes[0] if freeze_thaw_codes else "F0"

    max_wcm_durability, min_fc_durability = get_governing_limits(exposure_codes)

    design_fc = max(fc_psi, min_fc_durability)

    # ── Step 2: w/cm ─────────────────────────────────────────────────────────
    wcm_from_strength = get_wcm_from_fc(design_fc, air_entrained)
    if wcm_override:
        selected_wcm = wcm_override
    elif max_wcm_durability:
        selected_wcm = min(wcm_from_strength, max_wcm_durability)
    else:
        selected_wcm = wcm_from_strength

    # ── Step 3: Air content ───────────────────────────────────────────────────
    air_pct = get_air_content(agg_size, ft_class) if air_entrained else 1.5
    air_fraction = air_pct / 100.0

    # ── Step 4: Mixing water ──────────────────────────────────────────────────
    water_lbs = get_water_content(agg_size, slump, air_entrained)
    shape_reduction = SHAPE_WATER_REDUCTION.get(agg_shape, 0)
    water_lbs += shape_reduction

    # ── Step 5: Cementitious content ──────────────────────────────────────────
    total_cm = water_lbs / selected_wcm
    min_cm = MIN_CEMENT.get(agg_size, 470)
    total_cm = max(total_cm, min_cm)

    # Breakdown by SCM type (pcc is inert filler, still displaces cement by mass)
    total_scm_pct = flyash_pct + slag_pct + sf_pct + pcc_pct
    cement_pct = 100.0 - total_scm_pct
    cement_lbs = total_cm * cement_pct / 100.0
    flyash_lbs = total_cm * flyash_pct / 100.0
    slag_lbs   = total_cm * slag_pct / 100.0
    sf_lbs     = total_cm * sf_pct / 100.0
    pcc_lbs    = total_cm * pcc_pct / 100.0

    # ── Step 6: Coarse aggregate ──────────────────────────────────────────────
    bv_ca = interpolate_bulk_volume_ca(fm_fa, agg_size)
    ca_ft3 = bv_ca * CY_TO_FT3                      # ft³/CY
    ca_lbs = ca_ft3 * rodded_density_ca              # lbs/CY (OD)
    ca_sg = sg_ca

    # ── Step 7: Fine aggregate by absolute volume ─────────────────────────────
    water_ft3  = water_lbs / (1.0 * 62.4)
    cement_ft3 = cement_lbs / (3.15 * 62.4)
    flyash_ft3 = flyash_lbs / (sg_flyash * 62.4)
    slag_ft3   = slag_lbs   / (sg_slag * 62.4)
    sf_ft3     = sf_lbs     / (sg_sf * 62.4)
    pcc_ft3    = pcc_lbs    / (sg_pcc * 62.4)
    ca_vol_ft3 = ca_lbs     / (ca_sg * 62.4)
    air_ft3    = air_fraction * CY_TO_FT3

    fa_ft3 = CY_TO_FT3 - (water_ft3 + cement_ft3 + flyash_ft3 + slag_ft3
                           + sf_ft3 + pcc_ft3 + ca_vol_ft3 + air_ft3)
    fa_lbs = fa_ft3 * sg_fa * 62.4

    # ── Step 8: Density and volume check ─────────────────────────────────────
    total_mass = water_lbs + cement_lbs + flyash_lbs + slag_lbs + sf_lbs + pcc_lbs + ca_lbs + fa_lbs
    density_pcf = total_mass / CY_TO_FT3

    total_vol = (water_ft3 + cement_ft3 + flyash_ft3 + slag_ft3 + sf_ft3
                 + pcc_ft3 + ca_vol_ft3 + fa_ft3 + air_ft3)

    # ── Step 9: Checks and flags ──────────────────────────────────────────────
    flags = []

    # w/cm durability check
    if max_wcm_durability and selected_wcm > max_wcm_durability + 0.001:
        flags.append({
            "flag": f"w/cm {selected_wcm:.2f} exceeds durability limit {max_wcm_durability:.2f}",
            "status": "critical"
        })
    else:
        flags.append({
            "flag": f"w/cm {selected_wcm:.2f} — meets durability requirements",
            "status": "ok"
        })

    # Minimum cement
    if total_cm < min_cm - 1:
        flags.append({
            "flag": f"Cementitious content {total_cm:.0f} lbs/CY below ACI minimum {min_cm}",
            "status": "critical"
        })
    else:
        flags.append({
            "flag": f"Cementitious content {total_cm:.0f} lbs/CY meets ACI 211.1 minimum",
            "status": "ok"
        })

    # PCC-specific guidance
    if pcc_pct > 0:
        if 3.0 <= pcc_pct <= 8.0:
            flags.append({
                "flag": f"PCC at {pcc_pct:.0f}% — optimal micro-filler range (3–8%); expect packing strength gain",
                "status": "ok"
            })
        elif pcc_pct > 8.0:
            flags.append({
                "flag": f"PCC at {pcc_pct:.0f}% — above optimal range; monitor workability and strength",
                "status": "warning"
            })

    # Total SCM %
    if total_scm_pct > 60:
        flags.append({
            "flag": f"Total SCM replacement {total_scm_pct:.0f}% is high — verify early strength and curing",
            "status": "warning"
        })

    # Air entrainment for F2/F3
    if ft_class in ("F2", "F3") and not air_entrained:
        flags.append({
            "flag": "Air entrainment strongly recommended for F2/F3 exposure",
            "status": "critical"
        })

    # Volume check
    if abs(total_vol - CY_TO_FT3) > 0.5:
        flags.append({
            "flag": f"Total volume {total_vol:.2f} ft³ deviates from 27 ft³ — verify SG inputs",
            "status": "warning"
        })

    return {
        "design_fc_psi": design_fc,
        "selected_wcm": round(selected_wcm, 3),
        "max_wcm_durability": max_wcm_durability,
        "air_pct": round(air_pct, 1),
        "proportions": {
            "water_lbs":    round(water_lbs, 1),
            "cement_lbs":   round(cement_lbs, 1),
            "flyash_lbs":   round(flyash_lbs, 1),
            "slag_lbs":     round(slag_lbs, 1),
            "sf_lbs":       round(sf_lbs, 1),
            "pcc_lbs":      round(pcc_lbs, 1),
            "ca_lbs":       round(ca_lbs, 1),
            "fa_lbs":       round(fa_lbs, 1),
            "total_cm_lbs": round(total_cm, 1),
        },
        "volumes_ft3": {
            "water":  round(water_ft3, 3),
            "cement": round(cement_ft3, 3),
            "flyash": round(flyash_ft3, 3),
            "slag":   round(slag_ft3, 3),
            "sf":     round(sf_ft3, 3),
            "pcc":    round(pcc_ft3, 3),
            "ca":     round(ca_vol_ft3, 3),
            "fa":     round(fa_ft3, 3),
            "air":    round(air_ft3, 3),
            "total":  round(total_vol, 3),
        },
        "density_pcf": round(density_pcf, 1),
        "flags": flags,
        "bv_ca": round(bv_ca, 3),
    }
