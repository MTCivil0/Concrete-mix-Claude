"""
app.py
Concrete Mix Design Copilot — main Streamlit application.
Run with: streamlit run app.py
"""

import streamlit as st
from dotenv import load_dotenv
from src.aci211 import calculate_mix, SHAPE_WATER_REDUCTION
from src.claude_client import run_analysis
from src.schemas import MixDesignInput
from src.reporting import generate_markdown_report

load_dotenv()

st.set_page_config(
    page_title="Concrete Mix Design Copilot",
    page_icon="🧱",
    layout="wide",
)

with st.sidebar:
    st.title("⚙️ Settings")
    demo_mode = st.toggle("Demo mode (no API cost)", value=True)
    st.caption(
        "Demo mode returns a realistic sample analysis. "
        "Turn off to use live Claude inference (requires API key in .env)."
    )
    st.divider()
    st.markdown("**About**")
    st.caption(
        "Calculations follow ACI 211.1 (PCA method). "
        "PCC is modeled as an inert micro-filler. "
        "Not a substitute for a licensed engineer."
    )

st.title("🧱 Concrete Mix Design Copilot")
st.caption(
    "ACI 211.1 proportioning + AI-assisted durability analysis. "
    "Fill in your project data and click **Run Analysis**."
)

with st.form("mix_design_form"):

    st.subheader("I. Exposure & Strength Requirements")
    col1, col2 = st.columns(2)

    with col1:
        fc_psi = st.number_input(
            "Required f'c (psi)", min_value=2000, max_value=12000,
            value=5000, step=500,
        )
        ft_class = st.selectbox(
            "Freeze-thaw exposure",
            ["F0 — protected", "F1 — limited moisture", "F2 — moisture exposed", "F3 — deicers"],
            index=1,
        )
        water_class = st.selectbox(
            "Water exposure",
            ["W0 — protected", "W1 — low permeability required"],
            index=0,
        )

    with col2:
        sulfate_class = st.selectbox(
            "Sulfate exposure",
            ["S0 — protected", "S1 — moderate", "S2 — severe", "S3 — very severe"],
            index=0,
        )
        chloride_class = st.selectbox(
            "Chloride exposure",
            ["C0 — protected", "C2 — deicers / seawater"],
            index=0,
        )
        air_entrained = st.checkbox("Air-entrained mix", value=True)

    st.subheader("II. Aggregate & Workability")
    col3, col4 = st.columns(2)

    with col3:
        agg_size = st.selectbox(
            "Nominal max aggregate size",
            ["3/8", "1/2", "3/4", "1", "1-1/2", "2"],
            index=2,
            help="Smallest of: 1/5 narrowest dimension, 3/4 rebar spacing, 1/3 slab depth"
        )
        slump = st.selectbox("Target slump range (inches)", ["1-2", "3-4", "6-7"], index=0)
        agg_shape = st.selectbox("Coarse aggregate shape", list(SHAPE_WATER_REDUCTION.keys()), index=2)

    with col4:
        fm_fa = st.number_input(
            "Fineness modulus of fine aggregate (FM)",
            min_value=2.3, max_value=3.1, value=2.77, step=0.01,
            help="From sieve analysis — your Excel shows FM = 2.77"
        )
        sg_ca = st.number_input("SG of coarse aggregate", 2.4, 3.0, 2.65, 0.01)
        sg_fa = st.number_input("SG of fine aggregate", 2.4, 3.0, 2.68, 0.01)
        rodded_density = st.number_input(
            "Rodded bulk density of CA (lbs/ft³)", 70.0, 120.0, 100.0, 1.0,
            help="ASTM C29 — from your lab data"
        )

    st.subheader("III. Supplementary Cementitious Materials (SCMs)")
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        flyash_pct = st.number_input("Fly ash (%)", 0, 40, 0, step=5)
    with col6:
        slag_pct = st.number_input("Slag (%)", 0, 50, 0, step=5)
    with col7:
        sf_pct = st.number_input("Silica fume (%)", 0, 15, 0, step=1)
    with col8:
        pcc_pct = st.number_input(
            "PCC (%)", 0, 20, 5, step=1,
            help="Precipitated Calcium Carbonate — inert micro-filler. Optimal: 3–8%."
        )

    total_scm = flyash_pct + slag_pct + sf_pct + pcc_pct
    if total_scm > 0:
        st.caption(f"Total SCM: {total_scm}%  →  Portland cement: {100 - total_scm}%")

    with st.expander("Advanced: SCM specific gravities (optional)"):
        sg_col1, sg_col2, sg_col3, sg_col4 = st.columns(4)
        with sg_col1:
            sg_flyash = st.number_input("SG fly ash", 2.0, 3.0, 2.65, 0.01)
        with sg_col2:
            sg_slag = st.number_input("SG slag", 2.0, 3.0, 2.85, 0.01)
        with sg_col3:
            sg_sf = st.number_input("SG silica fume", 2.0, 2.5, 2.20, 0.01)
        with sg_col4:
            sg_pcc = st.number_input("SG PCC", 2.0, 3.0, 2.71, 0.01,
                                      help="Western Sugar PCC ≈ 2.71")

    wcm_override_on = st.checkbox("Override w/cm (default: use ACI 211.1 table)")
    wcm_override = None
    if wcm_override_on:
        wcm_override = st.slider("Manual w/cm", 0.28, 0.70, 0.45, 0.01)

    st.subheader("IV. Field Notes & Project Context")
    field_notes = st.text_area(
        "Optional context for AI analysis",
        placeholder="e.g. Bridge deck, South Dakota climate, pump placement, hot weather...",
        height=100,
    )

    submitted = st.form_submit_button("🔬 Run Mix Design Analysis", use_container_width=True)


if submitted:
    codes = [
        ft_class.split(" ")[0],
        water_class.split(" ")[0],
        sulfate_class.split(" ")[0],
        chloride_class.split(" ")[0],
    ]

    if total_scm >= 100:
        st.error("Total SCM replacement cannot be 100% or more.")
        st.stop()

    inp = MixDesignInput(
        fc_psi=fc_psi,
        exposure_codes=codes,
        agg_size=agg_size,
        slump=slump,
        fm_fa=fm_fa,
        sg_ca=sg_ca,
        sg_fa=sg_fa,
        rodded_density_ca=rodded_density,
        agg_shape=agg_shape,
        flyash_pct=float(flyash_pct),
        slag_pct=float(slag_pct),
        sf_pct=float(sf_pct),
        pcc_pct=float(pcc_pct),
        sg_flyash=sg_flyash,
        sg_slag=sg_slag,
        sg_sf=sg_sf,
        sg_pcc=sg_pcc,
        air_entrained=air_entrained,
        wcm_override=wcm_override,
        field_notes=field_notes,
    )

    with st.spinner("Running ACI 211.1 calculations + AI analysis..."):
        aci = calculate_mix(
            fc_psi=inp.fc_psi,
            exposure_codes=inp.exposure_codes,
            agg_size=inp.agg_size,
            slump=inp.slump,
            fm_fa=inp.fm_fa,
            sg_ca=inp.sg_ca,
            sg_fa=inp.sg_fa,
            rodded_density_ca=inp.rodded_density_ca,
            agg_shape=inp.agg_shape,
            flyash_pct=inp.flyash_pct,
            slag_pct=inp.slag_pct,
            sf_pct=inp.sf_pct,
            pcc_pct=inp.pcc_pct,
            sg_flyash=inp.sg_flyash,
            sg_slag=inp.sg_slag,
            sg_sf=inp.sg_sf,
            sg_pcc=inp.sg_pcc,
            air_entrained=inp.air_entrained,
            wcm_override=inp.wcm_override,
        )
        result = run_analysis(inp, aci, demo_mode)

    st.divider()
    st.header("Mix Design Results")

    risk_colors = {"Low": "🟢", "Moderate": "🟡", "High": "🔴"}
    st.subheader(f"{risk_colors.get(result.risk_level, '🟡')} Risk Level: {result.risk_level}")
    st.info(result.ai_analysis)

    p = aci["proportions"]
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Design f'c", f"{aci['design_fc_psi']:,} psi")
    m2.metric("Selected w/cm", f"{aci['selected_wcm']:.2f}")
    m3.metric("Air content", f"{aci['air_pct']}%")
    m4.metric("Fresh density", f"{aci['density_pcf']} pcf")
    m5.metric("Total volume", f"{aci['volumes_ft3']['total']:.2f} ft³/CY")

    st.subheader("Proportions per Cubic Yard")
    rows = [("Water", f"{p['water_lbs']:.0f}", "—"),
            ("Portland cement", f"{p['cement_lbs']:.0f}", f"{100-flyash_pct-slag_pct-sf_pct-pcc_pct:.0f}% of CM")]
    if flyash_pct > 0:
        rows.append(("Fly ash", f"{p['flyash_lbs']:.0f}", f"{flyash_pct:.0f}% of CM"))
    if slag_pct > 0:
        rows.append(("Slag", f"{p['slag_lbs']:.0f}", f"{slag_pct:.0f}% of CM"))
    if sf_pct > 0:
        rows.append(("Silica fume", f"{p['sf_lbs']:.0f}", f"{sf_pct:.0f}% of CM"))
    if pcc_pct > 0:
        rows.append(("PCC (inert micro-filler)", f"{p['pcc_lbs']:.0f}", f"{pcc_pct:.0f}% of CM"))
    rows += [
        ("Coarse aggregate (SSD)", f"{p['ca_lbs']:.0f}", f"BV of CA = {aci['bv_ca']:.2f}"),
        ("Fine aggregate (SSD)", f"{p['fa_lbs']:.0f}", "Absolute volume method"),
        ("─── Total cementitious", f"{p['total_cm_lbs']:.0f}", ""),
    ]

    import pandas as pd
    st.dataframe(
        pd.DataFrame(rows, columns=["Material", "lbs/CY", "Notes"]),
        use_container_width=True, hide_index=True,
    )

    st.subheader("Durability Flags")
    for f in aci["flags"]:
        if f["status"] == "ok":
            st.success(f["flag"])
        elif f["status"] == "warning":
            st.warning(f["flag"])
        else:
            st.error(f["flag"])

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.subheader("SCM & PCC Notes")
        for note in result.scm_notes:
            st.markdown(f"- {note}")
    with col_b:
        st.subheader("ACI 211.1 Compliance")
        for note in result.aci_compliance:
            st.markdown(f"- {note}")
    with col_c:
        st.subheader("QC Tests")
        for test in result.qc_tests:
            st.markdown(f"- {test}")

    st.subheader("Recommendations")
    st.markdown(result.recommendations)

    st.divider()
    report_md = generate_markdown_report(result)
    st.download_button(
        label="📄 Download Mix Design Report (.md)",
        data=report_md,
        file_name="mix_design_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
