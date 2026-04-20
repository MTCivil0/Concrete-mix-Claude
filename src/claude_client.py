"""
claude_client.py
Sends the calculated ACI 211.1 mix design to Claude for
expert-level narrative analysis, SCM notes, and QC guidance.
"""

import os
import json
import anthropic
from src.schemas import MixDesignInput, MixDesignResult


DEMO_RESULT = {
    "risk_level": "Low",
    "risk_summary": "Mix meets durability requirements for F2 exposure; w/cm and air content are within ACI 318 limits.",
    "scm_notes": [
        "PCC at 5% functions as an inert micro-filler — no reactive contribution to hydration.",
        "Particle packing effect from PCC is expected to yield a 5–9% compressive strength gain vs. plain Portland cement mix.",
        "Fly ash at 20% will extend set time by ~1–2 hours; plan finishing accordingly.",
        "Total SCM replacement at 25% is within acceptable range for structural concrete.",
    ],
    "aci_compliance": [
        "w/cm 0.45 satisfies F2 exposure limit of 0.45 (ACI 318 Table 19.3.3.1).",
        "Air content 6.0% meets ACI 318 F2 requirement for 3/4\" max aggregate.",
        "Cementitious content exceeds ACI 211.1 minimum of 540 lbs/CY for 3/4\" aggregate.",
        "Bulk volume of CA = 0.63 based on FM = 2.77 (ACI 211.1 Table 6.3.6).",
    ],
    "qc_tests": [
        "ASTM C143 — Slump test at truck discharge and point of placement",
        "ASTM C231 — Air content (pressure method) for every 50 CY",
        "ASTM C138 — Fresh unit weight and yield check",
        "ASTM C39 — Compressive strength at 7 and 28 days (min 2 cylinders per set)",
        "ASTM C1202 — Rapid chloride permeability test at 28 days if W1/C2 exposure",
        "ASTM C157 — Length change (shrinkage) if PCC content > 5%",
    ],
    "recommendations": (
        "Use Type I/II cement with 20% Class F fly ash and 5% PCC for best balance of "
        "durability and economy. Ensure proper curing for at least 7 days given the SCM "
        "content. Verify slump at point of placement, not at truck, for pumped concrete."
    ),
}


def _build_prompt(inp: MixDesignInput, aci: dict) -> str:
    p = aci["proportions"]
    v = aci["volumes_ft3"]
    flags_text = "\n".join(f"  [{f['status'].upper()}] {f['flag']}" for f in aci["flags"])

    return f"""You are a senior concrete materials engineer. A concrete mix design has been
calculated using ACI 211.1. Review the inputs, calculated proportions, and flags,
then return a JSON object ONLY — no markdown, no backticks, no preamble.

INPUTS:
- Required f'c: {inp.fc_psi} psi
- Exposure codes: {', '.join(inp.exposure_codes)}
- Max aggregate size: {inp.agg_size}"
- Target slump: {inp.slump}" 
- Fineness modulus FA: {inp.fm_fa}
- Aggregate shape: {inp.agg_shape}
- Air entrained: {inp.air_entrained}
- SCMs: Fly ash {inp.flyash_pct}%, Slag {inp.slag_pct}%, Silica fume {inp.sf_pct}%, PCC {inp.pcc_pct}%
- Field notes: {inp.field_notes or 'None'}

ACI 211.1 CALCULATED PROPORTIONS (per CY):
- Water: {p['water_lbs']} lbs
- Portland cement: {p['cement_lbs']} lbs
- Fly ash: {p['flyash_lbs']} lbs
- Slag: {p['slag_lbs']} lbs
- Silica fume: {p['sf_lbs']} lbs
- PCC (inert micro-filler): {p['pcc_lbs']} lbs
- Coarse aggregate: {p['ca_lbs']} lbs
- Fine aggregate: {p['fa_lbs']} lbs
- Total cementitious: {p['total_cm_lbs']} lbs
- Selected w/cm: {aci['selected_wcm']}
- Air content: {aci['air_pct']}%
- Density: {aci['density_pcf']} pcf
- Total volume: {v['total']} ft³

ACI FLAGS:
{flags_text}

IMPORTANT — PCC behavior: Precipitated Calcium Carbonate is an inert micro-filler,
NOT a reactive binder. At 3–8% it improves particle packing and can yield 5–9%
compressive strength gain. It does not contribute to hydration or pozzolanic reaction.

Return this exact JSON:
{{
  "risk_level": "Low" or "Moderate" or "High",
  "risk_summary": "One sentence overall assessment",
  "scm_notes": ["note1", "note2", "note3"],
  "aci_compliance": ["note1", "note2", "note3"],
  "qc_tests": ["ASTM test 1", "ASTM test 2", "ASTM test 3", "ASTM test 4"],
  "recommendations": "2-3 sentence practical summary"
}}"""


def run_analysis(inp: MixDesignInput, aci_result: dict, demo_mode: bool) -> MixDesignResult:
    """
    Run Claude analysis on the calculated mix design.
    In demo mode, returns a realistic sample result.
    """
    result = MixDesignResult(input_summary=inp, aci_result=aci_result)

    if demo_mode:
        r = DEMO_RESULT
    else:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env file.")

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": _build_prompt(inp, aci_result)}],
        )
        raw = message.content[0].text
        raw = raw.replace("```json", "").replace("```", "").strip()
        r = json.loads(raw)

    result.risk_level      = r.get("risk_level", "Moderate")
    result.ai_analysis     = r.get("risk_summary", "")
    result.scm_notes       = r.get("scm_notes", [])
    result.aci_compliance  = r.get("aci_compliance", [])
    result.qc_tests        = r.get("qc_tests", [])
    result.recommendations = r.get("recommendations", "")

    return result
