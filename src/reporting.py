"""
reporting.py
Generates a plain-text / Markdown mix design report for download.
"""

from datetime import date
from src.schemas import MixDesignResult


def generate_markdown_report(result: MixDesignResult) -> str:
    inp = result.input_summary
    aci = result.aci_result
    p   = aci["proportions"]

    lines = [
        "# Concrete Mix Design Report",
        f"**Date:** {date.today().strftime('%B %d, %Y')}",
        "",
        "---",
        "",
        "## Project Inputs",
        f"- Required f'c: **{inp.fc_psi:,} psi**",
        f"- Exposure classes: {', '.join(inp.exposure_codes)}",
        f"- Max aggregate size: {inp.agg_size}\"",
        f"- Target slump: {inp.slump}\"",
        f"- Fineness modulus (FA): {inp.fm_fa}",
        f"- Aggregate shape: {inp.agg_shape}",
        f"- Air entrained: {'Yes' if inp.air_entrained else 'No'}",
        "",
        "## SCM Replacements",
        f"- Portland cement: {100 - inp.flyash_pct - inp.slag_pct - inp.sf_pct - inp.pcc_pct:.0f}%",
        f"- Fly ash: {inp.flyash_pct:.0f}%",
        f"- Slag: {inp.slag_pct:.0f}%",
        f"- Silica fume: {inp.sf_pct:.0f}%",
        f"- PCC (inert micro-filler): {inp.pcc_pct:.0f}%",
        "",
        "---",
        "",
        "## ACI 211.1 Mix Proportions (per cubic yard)",
        "",
        "| Material | lbs/CY |",
        "|---|---|",
        f"| Water | {p['water_lbs']:.0f} |",
        f"| Portland cement | {p['cement_lbs']:.0f} |",
    ]

    if inp.flyash_pct > 0:
        lines.append(f"| Fly ash | {p['flyash_lbs']:.0f} |")
    if inp.slag_pct > 0:
        lines.append(f"| Slag | {p['slag_lbs']:.0f} |")
    if inp.sf_pct > 0:
        lines.append(f"| Silica fume | {p['sf_lbs']:.0f} |")
    if inp.pcc_pct > 0:
        lines.append(f"| PCC (micro-filler) | {p['pcc_lbs']:.0f} |")

    lines += [
        f"| Coarse aggregate (SSD) | {p['ca_lbs']:.0f} |",
        f"| Fine aggregate (SSD) | {p['fa_lbs']:.0f} |",
        f"| **Total cementitious** | **{p['total_cm_lbs']:.0f}** |",
        "",
        f"**Selected w/cm:** {aci['selected_wcm']}  ",
        f"**Air content:** {aci['air_pct']}%  ",
        f"**Fresh density:** {aci['density_pcf']} pcf  ",
        f"**Total volume:** {aci['volumes_ft3']['total']:.2f} ft³/CY  ",
        "",
        "---",
        "",
        f"## Risk Level: {result.risk_level}",
        f"{result.ai_analysis}",
        "",
        "## Durability Flags",
    ]

    for f in aci["flags"]:
        icon = "✅" if f["status"] == "ok" else ("⚠️" if f["status"] == "warning" else "🚫")
        lines.append(f"- {icon} {f['flag']}")

    lines += [
        "",
        "## SCM & PCC Compatibility Notes",
    ]
    for note in result.scm_notes:
        lines.append(f"- {note}")

    lines += [
        "",
        "## ACI 211.1 Compliance",
    ]
    for note in result.aci_compliance:
        lines.append(f"- {note}")

    lines += [
        "",
        "## Recommended QC Tests",
    ]
    for test in result.qc_tests:
        lines.append(f"- {test}")

    lines += [
        "",
        "## Recommendations",
        result.recommendations,
        "",
        "---",
        "*This report provides AI-assisted preliminary mix design guidance based on ACI 211.1.*",
        "*It is not a substitute for a licensed structural engineer or certified concrete technologist.*",
    ]

    if inp.field_notes:
        lines += ["", "## Field Notes", inp.field_notes]

    return "\n".join(lines)
