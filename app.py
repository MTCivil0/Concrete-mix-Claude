"""
app.py — Concrete Mix Design Copilot
Teymouri Research Lab | South Dakota State University
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import anthropic
import base64
import os
from dotenv import load_dotenv
from src.aci211 import calculate_mix, SHAPE_WATER_REDUCTION
from src.claude_client import run_analysis
from src.schemas import MixDesignInput, MixDesignResult, ProjectInfo
from src.reporting import generate_pdf_report

load_dotenv()

st.set_page_config(
    page_title="Concrete Mix Design Copilot | Teymouri Research Lab",
    page_icon="🧱",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**Teymouri Research Lab**")
    st.caption("Dept. of Construction & Concrete Industry Management\nJerome J. Lohr College of Engineering\nSouth Dakota State University")
    st.divider()
    demo_mode = st.toggle("Demo mode (no API cost)", value=True)
    st.caption("Demo mode returns a realistic sample analysis. Turn off to use live Claude inference (requires API key in .env).")
    st.divider()
    st.markdown("**About this tool**")
    st.caption("ACI 211.1 (PCA Method) proportioning with AI-assisted durability analysis. Not a substitute for a licensed engineer.")

# ── Global SDSU CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
/* SDSU Blue header strip */
.sdsu-header {
    background: #0033A0;
    color: white;
    padding: 10px 18px;
    border-radius: 8px 8px 0 0;
    font-weight: 700;
    font-size: 15px;
}
.sdsu-gold-bar {
    height: 4px;
    background: #FFB71B;
    border-radius: 0 0 4px 4px;
    margin-bottom: 14px;
}
/* Style all Streamlit buttons in chat area with SDSU feel */
div[data-testid="column"] button {
    border-left: 3px solid #0033A0 !important;
    font-size: 12px !important;
}
div[data-testid="column"] button:hover {
    border-left: 3px solid #FFB71B !important;
    background: #E6EBF5 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sdsu-header">🧱 &nbsp; Teymouri Research Lab · South Dakota State University</div>
<div class="sdsu-gold-bar"></div>
""", unsafe_allow_html=True)
st.title("Concrete Mix Design Copilot")
st.caption("ACI 211.1 proportioning + AI-assisted durability analysis and QC guidance")
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# MODE SELECTION
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("What would you like to do?")
mode = st.radio(
    "Select a mode:",
    ["🔬 Design a new mix (ACI 211.1)",
     "📄 Review an existing mix design (upload PDF or image)",
     "💬 Ask a concrete question (student Q&A)"],
    horizontal=True,
)
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT INFORMATION (shared by both modes)
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📋 Project information (optional — will appear in report)", expanded=True):
    pi_col1, pi_col2 = st.columns(2)
    with pi_col1:
        proj_name    = st.text_input("Project name", placeholder="e.g. US-14 Bridge Deck Replacement")
        location     = st.text_input("Location", placeholder="e.g. Brookings, SD")
    with pi_col2:
        prepared_by  = st.text_input("Prepared by", placeholder="e.g. Dr. Mohammad Teymouri, PE")
        company      = st.text_input("Company / Institution", placeholder="e.g. SDSU Teymouri Research Lab")

with st.expander("🏭 Material producers (optional — will appear in report)"):
    mp_col1, mp_col2 = st.columns(2)
    with mp_col1:
        cement_prod = st.text_input("Cement producer", placeholder="e.g. Ash Grove Cement, Type I/II")
        flyash_prod = st.text_input("Fly ash producer / class", placeholder="e.g. Basin Electric, Class F")
        slag_prod   = st.text_input("Slag producer / grade", placeholder="e.g. Lafarge, Grade 100")
    with mp_col2:
        sf_prod     = st.text_input("Silica fume producer", placeholder="e.g. Elkem, densified")
        pcc_prod    = st.text_input("PCC producer", placeholder="e.g. Western Sugar Cooperative, Brookings SD")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# MODE A: REVIEW UPLOADED FILE
# ─────────────────────────────────────────────────────────────────────────────
if "Review" in mode:
    st.subheader("📄 Upload your mix design document")
    st.caption("Upload a PDF report, mix design sheet, or photo of a mix ticket. Claude will review it and generate a structured report.")

    uploaded = st.file_uploader(
        "Upload mix design file",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        help="Max 10MB. Supports PDF documents and images (photo of mix ticket, lab report, etc.)"
    )

    review_notes = st.text_area(
        "Additional context (optional)",
        placeholder="e.g. This is a proposed mix for a bridge deck in F2 exposure. We need to check ACI 318 compliance and w/cm.",
        height=80,
    )

    if uploaded and st.button("🔍 Review Mix Design", use_container_width=True, type="primary"):
        with st.spinner("Analyzing your mix design document..."):
            file_bytes = uploaded.read()
            file_b64   = base64.b64encode(file_bytes).decode()
            is_pdf     = uploaded.type == "application/pdf"
            media_type = uploaded.type

            if demo_mode:
                review_text = (
                    "DEMO ANALYSIS — In live mode, Claude would read the full document. "
                    "Sample findings: w/cm ratio appears to be 0.45, which meets F2 exposure requirements. "
                    "Cementitious content is approximately 560 lbs/CY — above ACI 211.1 minimum for 3/4\" aggregate. "
                    "Air content target of 6% is appropriate for moderate freeze-thaw. "
                    "Recommended QC: ASTM C143, C231, C39 at 7 and 28 days. "
                    "No critical compliance issues identified in this demo."
                )
            else:
                api_key = os.getenv("ANTHROPIC_API_KEY", "")
                client  = anthropic.Anthropic(api_key=api_key)

                REVIEW_PROMPT = f"""You are a concrete materials engineer reviewing a mix design sheet.
Carefully read all values in this document/image and provide a structured review with these exact sections:

## Mix Design Summary
Extract and list all key values you can read: w/cm ratio, cement content, SCM types and %, water content, aggregate info, admixtures, density, target strength, casting date, mix ID.

## ACI 211.1 & ACI 318 Compliance Check
For each item, state PASS / WARN / FAIL:
- w/cm ratio vs exposure class requirements
- Minimum cementitious content
- Air content (if shown)
- Any other compliance items visible

## Observed Materials
List all materials with their quantities as shown in the document.

## Durability Flags
List any concerns about durability based on what you see.

## Recommended QC Tests
List appropriate ASTM tests for this mix.

## Summary & Recommendations
2-3 sentences of practical guidance.

Additional context from user: {review_notes or 'None provided'}

Be specific — extract actual numbers from the document, do not use placeholder values."""

                if is_pdf:
                    content = [
                        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": file_b64}},
                        {"type": "text", "text": REVIEW_PROMPT}
                    ]
                else:
                    content = [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": file_b64}},
                        {"type": "text", "text": REVIEW_PROMPT}
                    ]

                msg = client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": content}],
                )
                review_text = msg.content[0].text

        st.subheader("Review findings")
        st.info(review_text)

        # Build a minimal result for the PDF
        pi = ProjectInfo(project_name=proj_name, location=location,
                         prepared_by=prepared_by, company=company,
                         cement_producer=cement_prod, flyash_producer=flyash_prod,
                         slag_producer=slag_prod, sf_producer=sf_prod, pcc_producer=pcc_prod)
        dummy_inp = MixDesignInput(
            fc_psi=0, exposure_codes=["—"], agg_size="—", slump="—",
            fm_fa=0, sg_ca=0, sg_fa=0, rodded_density_ca=0, agg_shape="—",
            field_notes=review_notes, project_info=pi,
            uploaded_file_name=uploaded.name,
        )
        dummy_aci = {
            "design_fc_psi": 0, "selected_wcm": 0, "air_pct": 0,
            "density_pcf": 0, "bv_ca": 0,
            "proportions": {k: 0 for k in ["water_lbs","cement_lbs","flyash_lbs","slag_lbs","sf_lbs","pcc_lbs","ca_lbs","fa_lbs","total_cm_lbs"]},
            "volumes_ft3":  {k: 0 for k in ["water","cement","flyash","slag","sf","pcc","ca","fa","air","total"]},
            "flags": [{"flag": "See AI review findings above.", "status": "ok"}],
        }
        review_result = MixDesignResult(
            input_summary=dummy_inp, aci_result=dummy_aci,
            risk_level="See review", ai_analysis="Document review — see findings above.",
            recommendations=review_text, file_review_notes=review_text,
        )
        pdf_bytes = generate_pdf_report(review_result)
        st.divider()
        st.download_button(
            label="📄 Download Review Report (PDF)",
            data=pdf_bytes,
            file_name=f"mix_design_review_{uploaded.name}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# MODE B: DESIGN A NEW MIX
# ─────────────────────────────────────────────────────────────────────────────
else:
    with st.form("mix_design_form"):

        st.subheader("I. Exposure & strength requirements")
        col1, col2 = st.columns(2)
        with col1:
            fc_psi = st.number_input("Required f'c (psi)", 2000, 12000, 5000, 500)
            ft_class     = st.selectbox("Freeze-thaw exposure",
                ["F0 — protected", "F1 — limited moisture", "F2 — moisture exposed", "F3 — deicers"], index=1)
            water_class  = st.selectbox("Water exposure",
                ["W0 — protected", "W1 — low permeability required"], index=0)
        with col2:
            sulfate_class  = st.selectbox("Sulfate exposure",
                ["S0 — protected", "S1 — moderate", "S2 — severe", "S3 — very severe"], index=0)
            chloride_class = st.selectbox("Chloride exposure",
                ["C0 — protected", "C2 — deicers / seawater"], index=0)
            air_entrained  = st.checkbox("Air-entrained mix", value=True)

        st.subheader("II. Aggregate & workability")
        col3, col4 = st.columns(2)
        with col3:
            agg_size = st.selectbox("Nominal max aggregate size",
                ["3/8", "1/2", "3/4", "1", "1-1/2", "2"], index=2,
                help="Smallest of: 1/5 narrowest dimension, 3/4 rebar spacing, 1/3 slab depth")
            slump    = st.selectbox("Target slump range (inches)", ["1-2", "3-4", "6-7"], index=0)
            agg_shape = st.selectbox("Coarse aggregate shape", list(SHAPE_WATER_REDUCTION.keys()), index=2)
        with col4:
            fm_fa        = st.number_input("Fineness modulus of FA", 2.3, 3.1, 2.77, 0.01,
                                            help="From sieve analysis — your RSCA Excel shows FM = 2.77")
            sg_ca        = st.number_input("SG coarse aggregate", 2.4, 3.0, 2.65, 0.01)
            sg_fa        = st.number_input("SG fine aggregate", 2.4, 3.0, 2.68, 0.01)
            rodded_density = st.number_input("Rodded bulk density of CA (lbs/ft³)", 70.0, 120.0, 100.0, 1.0,
                                              help="ASTM C29 — from your lab data")

        st.subheader("III. Supplementary cementitious materials (SCMs)")
        c5, c6, c7, c8 = st.columns(4)
        with c5: flyash_pct = st.number_input("Fly ash (%)", 0, 40, 0, 5)
        with c6: slag_pct   = st.number_input("Slag (%)", 0, 50, 0, 5)
        with c7: sf_pct     = st.number_input("Silica fume (%)", 0, 15, 0, 1)
        with c8: pcc_pct    = st.number_input("PCC (%)", 0, 20, 5, 1,
                                               help="Precipitated Calcium Carbonate — inert micro-filler. Optimal: 3–8%.")

        total_scm = flyash_pct + slag_pct + sf_pct + pcc_pct
        if total_scm > 0:
            st.caption(f"Total SCM: {total_scm}%  →  Portland cement: {100 - total_scm}%")

        with st.expander("Advanced: SCM specific gravities (optional)"):
            sg1, sg2, sg3, sg4 = st.columns(4)
            with sg1: sg_flyash = st.number_input("SG fly ash", 2.0, 3.0, 2.65, 0.01)
            with sg2: sg_slag   = st.number_input("SG slag", 2.0, 3.0, 2.85, 0.01)
            with sg3: sg_sf     = st.number_input("SG silica fume", 2.0, 2.5, 2.20, 0.01)
            with sg4: sg_pcc    = st.number_input("SG PCC", 2.0, 3.0, 2.71, 0.01, help="Western Sugar PCC ≈ 2.71")

        wcm_override_on = st.checkbox("Override w/cm (default: use ACI 211.1 table)")
        wcm_override = None
        if wcm_override_on:
            wcm_override = st.slider("Manual w/cm", 0.28, 0.70, 0.45, 0.01)

        st.subheader("IV. Field notes & project context")
        field_notes = st.text_area("Optional context for AI analysis",
            placeholder="e.g. Bridge deck, South Dakota climate, pump placement, cold weather expected...",
            height=90)

        submitted = st.form_submit_button("🔬 Run Mix Design Analysis", use_container_width=True)

    if submitted:
        codes = [ft_class.split(" ")[0], water_class.split(" ")[0],
                 sulfate_class.split(" ")[0], chloride_class.split(" ")[0]]
        if total_scm >= 100:
            st.error("Total SCM replacement cannot be 100% or more.")
            st.stop()

        pi = ProjectInfo(
            project_name=proj_name, location=location,
            prepared_by=prepared_by, company=company,
            cement_producer=cement_prod, flyash_producer=flyash_prod,
            slag_producer=slag_prod, sf_producer=sf_prod, pcc_producer=pcc_prod,
        )
        inp = MixDesignInput(
            fc_psi=fc_psi, exposure_codes=codes, agg_size=agg_size,
            slump=slump, fm_fa=fm_fa, sg_ca=sg_ca, sg_fa=sg_fa,
            rodded_density_ca=rodded_density, agg_shape=agg_shape,
            flyash_pct=float(flyash_pct), slag_pct=float(slag_pct),
            sf_pct=float(sf_pct), pcc_pct=float(pcc_pct),
            sg_flyash=sg_flyash, sg_slag=sg_slag, sg_sf=sg_sf, sg_pcc=sg_pcc,
            air_entrained=air_entrained, wcm_override=wcm_override,
            field_notes=field_notes, project_info=pi,
        )

        with st.spinner("Running ACI 211.1 calculations + AI analysis..."):
            aci = calculate_mix(
                fc_psi=inp.fc_psi, exposure_codes=inp.exposure_codes,
                agg_size=inp.agg_size, slump=inp.slump, fm_fa=inp.fm_fa,
                sg_ca=inp.sg_ca, sg_fa=inp.sg_fa,
                rodded_density_ca=inp.rodded_density_ca, agg_shape=inp.agg_shape,
                flyash_pct=inp.flyash_pct, slag_pct=inp.slag_pct,
                sf_pct=inp.sf_pct, pcc_pct=inp.pcc_pct,
                sg_flyash=inp.sg_flyash, sg_slag=inp.sg_slag,
                sg_sf=inp.sg_sf, sg_pcc=inp.sg_pcc,
                air_entrained=inp.air_entrained, wcm_override=inp.wcm_override,
            )
            result = run_analysis(inp, aci, demo_mode)

        st.divider()
        st.header("Mix design results")

        # Project info summary
        if proj_name or location or prepared_by:
            info_parts = []
            if proj_name:    info_parts.append(f"**Project:** {proj_name}")
            if location:     info_parts.append(f"**Location:** {location}")
            if prepared_by:  info_parts.append(f"**Prepared by:** {prepared_by}")
            if company:      info_parts.append(f"**Organization:** {company}")
            st.caption(" · ".join(info_parts))

        risk_colors = {"Low": "🟢", "Moderate": "🟡", "High": "🔴"}
        st.subheader(f"{risk_colors.get(result.risk_level, '🟡')} Risk level: {result.risk_level}")
        st.info(result.ai_analysis)

        p = aci["proportions"]
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Design f'c",    f"{aci['design_fc_psi']:,} psi")
        m2.metric("Selected w/cm", f"{aci['selected_wcm']:.2f}")
        m3.metric("Air content",   f"{aci['air_pct']}%")
        m4.metric("Fresh density", f"{aci['density_pcf']} pcf")
        m5.metric("Total volume",  f"{aci['volumes_ft3']['total']:.2f} ft³/CY")

        st.subheader("Proportions per cubic yard")
        rows = [("Water", f"{p['water_lbs']:.0f}", "—"),
                ("Portland cement", f"{p['cement_lbs']:.0f}", f"{100-total_scm:.0f}% of CM")]
        if flyash_pct > 0: rows.append(("Fly ash", f"{p['flyash_lbs']:.0f}", f"{flyash_pct:.0f}% of CM"))
        if slag_pct > 0:   rows.append(("Slag", f"{p['slag_lbs']:.0f}", f"{slag_pct:.0f}% of CM"))
        if sf_pct > 0:     rows.append(("Silica fume", f"{p['sf_lbs']:.0f}", f"{sf_pct:.0f}% of CM"))
        if pcc_pct > 0:    rows.append(("PCC (inert micro-filler)", f"{p['pcc_lbs']:.0f}", f"{pcc_pct:.0f}% of CM"))
        rows += [("Coarse aggregate (SSD)", f"{p['ca_lbs']:.0f}", f"BV of CA = {aci['bv_ca']:.2f}"),
                 ("Fine aggregate (SSD)", f"{p['fa_lbs']:.0f}", "Absolute volume method"),
                 ("Total cementitious", f"{p['total_cm_lbs']:.0f}", "")]
        st.dataframe(pd.DataFrame(rows, columns=["Material", "lbs/CY", "Notes"]),
                     use_container_width=True, hide_index=True)

        st.subheader("Durability flags")
        for f in aci["flags"]:
            if f["status"] == "ok":      st.success(f["flag"])
            elif f["status"] == "warning": st.warning(f["flag"])
            else:                          st.error(f["flag"])

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.subheader("SCM & PCC notes")
            for note in result.scm_notes: st.markdown(f"- {note}")
        with col_b:
            st.subheader("ACI 211.1 compliance")
            for note in result.aci_compliance: st.markdown(f"- {note}")
        with col_c:
            st.subheader("QC tests")
            for test in result.qc_tests: st.markdown(f"- {test}")

        st.subheader("Recommendations")
        st.markdown(result.recommendations)

        st.divider()
        pdf_bytes = generate_pdf_report(result)
        st.download_button(
            label="📄 Download Mix Design Report (PDF)",
            data=pdf_bytes,
            file_name=f"mix_design_{proj_name.replace(' ','_') or 'report'}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# MODE C: STUDENT CONCRETE Q&A CHATBOX
# ─────────────────────────────────────────────────────────────────────────────
if "Q&A" in mode:
    st.markdown("""
    <div style="background:#0033A0; padding:14px 18px 10px 18px; border-radius:8px; margin-bottom:4px;">
        <span style="color:#FFB71B; font-size:18px; font-weight:700;">💬 Concrete Q&A</span><br>
        <span style="color:#B3C3E8; font-size:13px;">Ask about concrete properties, ASTM/ACI test standards, mix design theory, durability, admixtures, or SCMs — tuned for construction engineering students at SDSU.</span>
    </div>
    <div style="height:4px; background:#FFB71B; border-radius:0 0 4px 4px; margin-bottom:12px;"></div>
    """, unsafe_allow_html=True)

    # ── Suggested questions ───────────────────────────────────────────────────
    st.markdown("""<div style="background:#E6EBF5; border-left:4px solid #0033A0; padding:7px 14px; border-radius:0 6px 6px 0; margin-bottom:8px;"><span style="color:#0033A0; font-weight:600; font-size:14px;">Quick questions to get started</span></div>""", unsafe_allow_html=True)
    q_col1, q_col2, q_col3 = st.columns(3)
    suggestions = [
        ("What is ASTM C143 — slump test?", q_col1),
        ("What is ASTM C39 — compressive strength test?", q_col2),
        ("What is ASTM C231 — air content test?", q_col3),
        ("What is ASTM C1202 — RCPT test?", q_col1),
        ("What are SCC tests and standards?", q_col2),
        ("What is UHPC and how is it tested?", q_col3),
        ("How is crack detection done in concrete?", q_col1),
        ("What is the Vebe test for pavement concrete?", q_col2),
        ("What is fly ash Class C vs Class F?", q_col3),
    ]
    for question, col in suggestions:
        with col:
            if st.button(question, use_container_width=True):
                st.session_state.chat_input_prefill = question

    st.divider()

    # ── Chat history init ─────────────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ── System prompt ─────────────────────────────────────────────────────────
    CONCRETE_SYSTEM = """You are a concrete materials engineering assistant and tutor at the Teymouri Research Lab, 
South Dakota State University (SDSU). You help construction engineering students.

When a student asks about a specific ASTM or ACI standard or test method, ALWAYS structure your answer as:

1. **Standard:** Full designation (e.g., ASTM C143-20)
2. **Purpose:** One sentence on what it measures
3. **Equipment:** List the required equipment
4. **Step-by-step procedure:** Numbered steps, concise and clear
5. **Key acceptance criteria / limits**
6. **Official link:** https://www.astm.org/Standards/[standard].htm — note it requires ASTM membership, but the free preview is available
7. **Related standards:** 2-3 related standards

For non-standard questions, give clear educational answers with examples.

Key standards to know:
- ASTM C143 — Slump test (workability)
- ASTM C39 — Compressive strength of cylinders  
- ASTM C231 — Air content (pressure method)
- ASTM C138 — Unit weight and yield
- ASTM C1202 — Rapid chloride permeability (RCPT)
- ASTM C666 — Freeze-thaw resistance
- ASTM C157 — Drying shrinkage
- ASTM C618 — Fly ash specification
- ASTM C989 — Slag specification
- ASTM C1240 — Silica fume specification
- ASTM C494 — Chemical admixtures
- ASTM C172 — Sampling fresh concrete
- ASTM C192 — Making and curing test specimens
- ASTM C138 — Density, yield, air content (gravimetric)
- ACI 211.1 — Mix design (PCA method)
- ACI 318 — Building code (exposure classes Table 19.3)

PCC research context: Precipitated Calcium Carbonate from Western Sugar Cooperative is studied 
at Teymouri Research Lab as an inert micro-filler (3-8% optimal, +5-9% strength from packing).

Always be encouraging and specific. Never give a generic list when a specific standard was asked."""

    # ── Demo responses — one per standard, focused and complete ──────────────
    DEMO_RESPONSES = {
        "c143": """**ASTM C143 — Standard Test Method for Slump of Hydraulic-Cement Concrete**

**Purpose:** Measures the workability (consistency) of fresh concrete before placement.

**Equipment required:**
- Abrams slump cone: 4\" top diameter, 8\" base diameter, 12\" height
- Tamping rod: 5/8\" diameter, 24\" long, bullet-tipped
- Rigid, non-absorbent base plate
- Measuring tape or ruler (to nearest 1/4\")
- Stopwatch

**Step-by-step procedure:**
1. Dampen the cone and base plate — place cone on base, stand on foot pieces
2. Sample fresh concrete per **ASTM C172** within 5 minutes of sampling
3. Fill cone in **3 equal layers** (~4\" each)
4. Rod each layer **25 times** uniformly over the cross-section; rod the bottom layer throughout, for upper layers penetrate 1\" into the previous layer
5. Strike off the top flush with the cone opening
6. Remove the cone by lifting **straight up in 5 ± 2 seconds** — no twisting
7. Place the cone beside the slumped concrete
8. Measure the difference between the top of the cone and the displaced center of the concrete
9. Record to the nearest **1/4 inch (5 mm)**
10. Complete entire test within **2.5 minutes** of sampling

**Acceptance criteria (ACI 211.1 typical targets):**
| Construction type | Typical slump |
|---|---|
| Footings & substructure walls | 1–3\" |
| Beams & reinforced walls | 1–4\" |
| Building columns | 1–4\" |
| Pavements & slabs | 1–3\" |
| Mass concrete | 1–2\" |
| Pumped concrete | 4–6\" |

**Key rule:** If the concrete shears or falls apart (shear slump), the test is not valid — resample and retest.

**Find it online — search Google for:**
- 🔍 `ASTM C143 slump test PDF free`
- 🔍 `concrete slump test procedure step by step`
- 🔍 `ASTM C143 standard scope astm.org`
- 🔍 `slump test concrete workability ACI`

**Related standards:**
- **ASTM C172** — Sampling fresh concrete (required before C143)
- **ASTM C138** — Unit weight and yield
- **ASTM C231** — Air content""",

        "c39": """**ASTM C39 — Standard Test Method for Compressive Strength of Cylindrical Concrete Specimens**

**Purpose:** Measures the compressive strength (f'c) of hardened concrete — the most fundamental concrete test.

**Equipment required:**
- Compression testing machine (calibrated per ASTM E4)
- Standard cylinders: 4×8\" or 6×12\" (diameter × height ratio must be 2:1)
- Capping compound or neoprene pads (ASTM C1231) for end preparation
- Curing tank or moist room (73±3°F)

**Step-by-step procedure:**
1. Make specimens per **ASTM C192** — fill cylinder molds in 2 layers (4×8\") or 3 layers (6×12\"), rod each 25 times
2. Cure in molds at 60–80°F for **24±8 hours**
3. Strip molds and transport to lab; cure in water or moist room at **73±3°F (23±1.7°C)**
4. Test at specified age — typically **7 days** (verify early strength) and **28 days** (acceptance)
5. Cap or grind cylinder ends so they are flat within 0.002\"
6. Center specimen in testing machine
7. Apply load continuously at **35 ± 7 psi/second** (no jolts or shocks)
8. Record maximum load at failure
9. Calculate: **f'c = Load (lbs) ÷ Area (in²)**
10. Note the fracture type (Type 1–6 per C39 Figure 3)

**Acceptance (ACI 318):**
- Average of two cylinders must ≥ specified f'c
- No individual cylinder < f'c − 500 psi (if f'c ≤ 5000 psi)

**Find it online — search Google for:**
- 🔍 
- 🔍 
- 🔍 
- 🔍 

**Related standards:**
- **ASTM C192** — Making and curing specimens in the lab
- **ASTM C31** — Making and curing specimens in the field
- **ASTM C1231** — Neoprene pad capping systems""",

        "c231": """**ASTM C231 — Standard Test Method for Air Content of Freshly Mixed Concrete by the Pressure Method**

**Purpose:** Measures the total air content (%) of fresh concrete using Boyle's Law — most common method for normal-weight aggregate concrete.

**Equipment required:**
- Type A or Type B pressure meter (air meter)
- Tamping rod, vibrator, or both
- Strike-off bar
- Rubber mallet

**Step-by-step procedure:**
1. Sample fresh concrete per **ASTM C172**
2. Dampen the base of the air meter
3. Fill the bowl in **3 equal layers**, rod each **25 times** + tap sides 10–15 times with mallet; or vibrate per standard
4. Strike off the top flush
5. Clean the flange and clamp the cover assembly tightly
6. Close air valves; inject water through petcocks to remove air from space above concrete
7. Close petcocks; pump air to initial pressure (pre-charge)
8. Tap sides of bowl; open main valve and read the gauge after pointer stabilizes
9. Record air content to the nearest **0.1%**
10. **Aggregate correction factor:** Subtract the aggregate correction factor (determined separately per Annex A2)

**Typical target air content (ACI 318, 3/4\" max aggregate):**
| Exposure | Required air % |
|---|---|
| F1 — moderate freeze-thaw | 5.0% |
| F2 — severe freeze-thaw | 6.0% |
| F3 — deicers | 6.0% |

**Important:** ASTM C231 is for **normal-weight** aggregate only. Use **ASTM C173** (volumetric method) for lightweight aggregate or slag aggregate.

**Find it online — search Google for:**
- 🔍 
- 🔍 
- 🔍 
- 🔍 

**Related standards:**
- **ASTM C173** — Air content by volumetric method (lightweight aggregate)
- **ASTM C138** — Unit weight (can also estimate air gravimetrically)
- **ASTM C457** — Microscopical determination of air-void parameters (hardened concrete)""",

        "wcm": """**Water-to-Cementitious Material Ratio (w/cm)**

**Definition:**
> w/cm = Mass of water ÷ Mass of all cementitious materials

Cementitious materials include: Portland cement + fly ash + slag + silica fume + PCC (if reactive)
Note: PCC (Precipitated Calcium Carbonate) is an **inert filler** — it is typically excluded from w/cm denominator.

**Why it's the most important parameter in mix design:**
- Controls **capillary porosity** in the hardened cement paste
- Lower w/cm → denser microstructure → higher strength + lower permeability
- Every 0.05 increase in w/cm ≈ 10% reduction in 28-day strength

**ACI 318-19 maximum w/cm by exposure class:**
| Exposure | Max w/cm | Min f'c |
|---|---|---|
| F1 (moderate freeze-thaw) | 0.55 | 3,500 psi |
| F2 (severe freeze-thaw) | 0.45 | 4,500 psi |
| F3 (deicers) | 0.40 | 5,000 psi |
| W1 (watertight) | 0.50 | 4,000 psi |
| S2 (severe sulfate) | 0.45 | 4,500 psi |
| C2 (chlorides/deicers) | 0.40 | 5,000 psi |

**ACI 211.1 guidance (Table 6.3.4):**
| Target f'c (psi) | Non-air-entrained w/cm | Air-entrained w/cm |
|---|---|---|
| 5,000 | 0.48 | 0.40 |
| 4,000 | 0.57 | 0.48 |
| 3,000 | 0.68 | 0.59 |

**Key formula check in this tool:**
w/cm = Water (lbs/CY) ÷ Total cementitious (lbs/CY)

**Reference:** ACI 211.1, ACI 318-19 Table 19.3.3.1""",

        "fly ash": """**Fly Ash in Concrete — ASTM C618**

**What is fly ash?** A fine powder byproduct from burning coal in power plants. Captured by electrostatic precipitators. Used as a partial cement replacement in concrete.

**Class F vs Class C — Key differences:**

| Property | Class F | Class C |
|---|---|---|
| Coal source | Anthracite / bituminous | Sub-bituminous / lignite |
| SiO₂+Al₂O₃+Fe₂O₃ | > 70% | > 50% |
| CaO content | Low (< 10%) | High (15–35%) |
| Reactivity | Pozzolanic only | Pozzolanic + cementitious |
| Self-cementing | No | Yes |
| Strength gain | Slower (long-term gain) | Faster |
| Heat of hydration | Lower | Moderate |
| Sulfate resistance | Better | Good |
| Midwest availability | Less common | **Very common in SD** |

**Typical replacement levels:**
- Class F: 15–25% by mass of cementitious
- Class C: 20–35% by mass of cementitious

**Benefits of fly ash:**
- Reduces heat of hydration (good for mass concrete)
- Improves workability and pumpability
- Enhances long-term durability
- Reduces cost compared to Portland cement
- Reduces CO₂ footprint

**ASTM C618 key requirements:**
- Fineness: ≤ 34% retained on No. 325 sieve
- Strength activity index: ≥ 75% at 28 days
- Soundness: autoclave expansion ≤ 0.8%

**Official standard:** [ASTM C618](https://www.astm.org/c0618-22.html)

**Related:** ASTM C989 (slag), ASTM C1240 (silica fume), ACI 232.2R (fly ash in concrete)""",


        "rcpt": """**ASTM C1202 — Rapid Chloride Permeability Test (RCPT)**

**Purpose:** Measures the electrical conductance of concrete to assess its resistance to chloride ion penetration — key durability indicator for bridge decks, marine structures, and any concrete exposed to deicers or seawater.

**Equipment required:**
- Two copper electrode cells with rubber gaskets
- DC power supply (60 V)
- Ammeter (data logger preferred)
- Vacuum pump and desiccator
- Water-saturated specimens (4" dia × 2" thick discs)

**Step-by-step procedure:**
1. Cut a 2" thick disc from a 4×8" cylinder (at mid-height) using a wet saw
2. Condition the disc: vacuum saturate in water for 18 hours per Annex A
3. Mount disc between two cells: one filled with 3% NaCl, one with 0.3N NaOH
4. Apply **60 V DC** across the specimen for **6 hours**
5. Record current every 30 minutes using data logger
6. Calculate total charge passed (coulombs) = area under current-time curve

**Acceptance criteria (ASTM C1202 Table 1):**
| Charge passed (Coulombs) | Chloride permeability |
|---|---|
| > 4,000 | High |
| 2,000 – 4,000 | Moderate |
| 1,000 – 2,000 | Low |
| 100 – 1,000 | Very low |
| < 100 | Negligible |

**ACI 318 / AASHTO target:** ≤ 2,000 coulombs for bridge decks; ≤ 1,000 for severe exposure.
**Test age:** Typically at **28 or 56 days** (56 days preferred for SCM mixes — slag/fly ash need time to react).

**Important:** RCPT measures electrical conductance, not chloride directly — high SCM content can lower readings independently of actual permeability. Confirm with **ASTM C1556** (bulk diffusion) for SCM-rich mixes.

**Find it online — search Google for:**
- 🔍 
- 🔍 
- 🔍 
- 🔍 

**Related standards:**
- **ASTM C1556** — Bulk diffusion test (more accurate for SCM mixes)
- **AASHTO T 277** — Equivalent to ASTM C1202
- **ASTM C642** — Absorption and voids in hardened concrete""",

        "scc": """**Self-Consolidating Concrete (SCC) — Key Tests and Standards**

**What is SCC?** Concrete that flows under its own weight, fills formwork completely, and passes through reinforcement without vibration. Requires specific fresh property tests — slump alone is insufficient.

**The 4 essential SCC fresh property tests:**

**1. ASTM C1611 — Slump Flow and T50**
- Pour concrete into inverted slump cone on flat plate; lift cone; measure spread diameter
- **Target:** 18–32" (450–810 mm) spread
- **T50:** Time to reach 20" diameter — measures viscosity
- **Target T50:** 2–7 seconds (longer = more viscous = more stable)
- Also assess **VSI (Visual Stability Index):** 0 = stable, 1 = stable, 2 = unstable, 3 = highly unstable

**2. ASTM C1621 — J-Ring Test (passing ability)**
- Same as slump flow but with a ring of vertical rebar around the cone
- Measure spread WITH the ring; compare to free slump flow
- **Acceptable difference:** ≤ 2" (50 mm) → good passing ability
- Larger difference = blockage risk in congested reinforcement

**3. ASTM C1610 — Column Segregation Test**
- Fill a 26" tall PVC column in one lift; let stand 15 minutes; section into 4 parts
- Compare aggregate content top vs bottom
- **Segregation index:** ≤ 10% acceptable; > 15% = segregation concern

**4. ASTM C1712 — Rapid Assessment of SCC (Penetration Test)**
- Simple site test: measure depth a standard cylinder penetrates fresh SCC
- Quick field check for stability and viscosity

**Typical SCC mix characteristics:**
- w/cm: 0.32–0.42
- High paste volume: 34–40%
- VMA (viscosity-modifying admixture) often used
- HRWRA (high-range water reducer, ASTM C494 Type F or G) required

**ACI reference:** ACI 237R-07 — Self-Consolidating Concrete

**Official standards:**
**Find it online — search Google for:**
- 🔍 
- 🔍 
- 🔍 
- 🔍 
- 🔍 """,

        "uhpc": """**Ultra-High-Performance Concrete (UHPC) — Properties and Testing**

**What is UHPC?**
Concrete with compressive strength ≥ **14,500 psi (100 MPa)**, exceptional durability, and high tensile strength from steel fiber reinforcement. No coarse aggregate — uses quartz sand, silica fume, HRWRA, and steel fibers.

**Typical UHPC mix composition:**
| Material | Typical content |
|---|---|
| Portland cement (Type I/II or III) | 700–900 lb/CY |
| Silica fume | 200–250 lb/CY (25–30%) |
| Quartz flour (< 300 μm) | 200–400 lb/CY |
| Quartz sand (150–600 μm) | 900–1100 lb/CY |
| Steel fibers (2% by volume) | 260 lb/CY |
| HRWRA | 30–50 lb/CY |
| w/cm | 0.14–0.22 |

**Key UHPC test standards:**

| Test | Standard | UHPC typical value |
|---|---|---|
| Compressive strength | ASTM C39 | 14,500–29,000 psi |
| Flexural strength | ASTM C1609 | 2,000–4,000 psi |
| Splitting tensile | ASTM C496 | 1,000–2,500 psi |
| Flow (fresh) | ASTM C1437 | > 8" spread |
| Chloride permeability | ASTM C1202 | < 100 coulombs (negligible) |
| Absorption | ASTM C642 | < 2% |

**ASTM C1609 — Flexural Performance of Fiber-Reinforced Concrete:**
- Uses 6×6×20" beam on 18" span
- Measures load vs mid-point deflection curve
- Captures post-crack toughness — critical for UHPC

**Find it online — search Google for:**
- 🔍 
- 🔍 
- 🔍 
- 🔍 
- 🔍 

**Curing:** UHPC typically requires **steam curing at 194°F (90°C) for 48 hours** to achieve full strength.

**Related:** ASTM C1437 (flow of hydraulic cement mortar), ASTM C1609 (fiber-reinforced concrete)""",

        "crack": """**Crack Detection in Concrete — Methods and Standards**

**Why it matters:** Cracks are the primary pathway for chloride, water, and sulfate ingress — directly affecting durability and service life.

**Visual inspection (first step — always):**
- Crack width measured with a **crack comparator gauge** (optical)
- Map crack patterns: map, pattern/shrinkage, structural flexural, corrosion-induced
- **ACI 224R** — Control of Cracking in Concrete Structures (key reference)
- Acceptable crack width limits (ACI 318): 0.013" (0.33 mm) for exterior exposure

**Non-destructive testing (NDT) methods:**

**1. Ultrasonic Pulse Velocity (UPV) — ASTM C597**
- Transmit ultrasonic pulse through concrete; measure travel time
- Lower velocity = higher porosity / cracking
- Crack depth estimated by indirect transmission method
- Typical sound concrete: > 14,000 ft/s (4,300 m/s)

**2. Impact-Echo — ASTM C1383**
- Strike surface with small hammer; measure reflected stress wave frequency
- Detects delamination, voids, and internal cracks
- Best for slabs and walls — non-invasive

**3. Ground Penetrating Radar (GPR) — ASTM D6432**
- Electromagnetic pulse maps internal features including cracks, rebar, voids
- Fast scanning method for bridge decks and pavements

**4. Acoustic Emission (AE) — ASTM E1316**
- Passive sensors detect stress waves from active crack propagation
- Used for real-time monitoring of structural elements

**5. Dye penetrant / fluorescent crack mapping**
- Apply dye or epoxy; UV light reveals crack network
- Used in lab specimens and cores

**Crack width classification (ACI 224R):**
| Width | Classification |
|---|---|
| < 0.006" (0.15 mm) | Hairline — monitor |
| 0.006–0.013" | Fine — acceptable outdoors |
| > 0.013" | Wide — investigate cause |
| > 0.020" | Severe — structural concern |

**Related standards:**
**Find it online — search Google for:**
- 🔍 
- 🔍 
- 🔍 
- 🔍 
- 🔍 """,

        "vebe": """**Vebe Test — ASTM C1170 (Stiff / Roller-Compacted Concrete)**

**Purpose:** Measures the consistency (workability) of **very stiff concrete** — used for roller-compacted concrete (RCC) pavements, no-slump mixes, and dry-cast concrete where the slump test gives 0" and is therefore meaningless.

**Why not slump for pavement concrete?**
Pavement and RCC mixes are intentionally stiff (0" slump) for stability under compaction. Slump cannot differentiate between these mixes — Vebe time fills this gap.

**Equipment required:**
- Vibrating table (frequency: 50 Hz, amplitude: 0.35 mm)
- Slump cone (standard Abrams cone)
- Plexiglass disc rider (to detect completion)
- Stopwatch
- Container (cylindrical, 9.5" dia × 8" height)

**Step-by-step procedure (ASTM C1170):**
1. Place slump cone centered inside the cylindrical container on the vibrating table
2. Fill cone in 3 layers, rod each 25 times (same as slump test)
3. Strike off top and remove slump cone
4. Place transparent Plexiglass disc on top of the concrete
5. Start vibrator and stopwatch simultaneously
6. Stop when the concrete has fully compacted and the disc is uniformly covered on its entire underside with mortar (no more air bubbles escaping)
7. Record time to nearest **0.5 second** = **Vebe time**

**Interpretation:**
| Vebe time (seconds) | Workability class | Typical use |
|---|---|---|
| 3–5 s | V0 — very workable | Wet RCC |
| 6–12 s | V1 — workable | Standard RCC pavement |
| 12–20 s | V2 — stiff | Dry RCC, lean concrete base |
| 20–30 s | V3 — very stiff | No-fines, stiff pavement |
| > 30 s | V4 — extremely stiff | Prestressed dry-cast |

**RCC pavement target:** Typically **6–12 seconds** (V1 class) for optimal compaction with vibratory roller.

**Related test — ASTM C1228:** Modified Vebe for no-slump concrete.

**Find it online — search Google for:**
- 🔍 
- 🔍 
- 🔍 
- 🔍 

**Related standards:**
- **ACI 325.10R** — Guide for Construction of Roller-Compacted Concrete Pavements
- **ASTM C1435** — Molding roller-compacted concrete in cylinder molds
- **ASTM C1040** — Density of unhardened and hardened concrete by nuclear methods""",
        "pcc": """**Precipitated Calcium Carbonate (PCC) as a Cement Replacement**

**What is PCC?**
Precipitated Calcium Carbonate (CaCO₃) is a manufactured, ultra-fine limestone powder produced by a controlled chemical precipitation process. At SDSU, our source is a **byproduct from Western Sugar Cooperative** in Brookings, SD.

**Key distinction — inert micro-filler (NOT a reactive binder):**
Unlike fly ash, slag, or silica fume, PCC does **not** react chemically with cement hydration products. It has **no pozzolanic activity**.

**How it works — particle packing effect:**
PCC particles (< 10 μm) fill the interstitial voids between larger cement grains, improving the packing density of the cementitious system. This reduces capillary porosity without chemical reaction.

**Research findings — Teymouri Research Lab (SDSU):**
| PCC replacement | Expected effect |
|---|---|
| 3–5% | Optimal packing — +5 to +9% compressive strength gain |
| 5–8% | Good range — monitor workability |
| > 8% | Diminishing returns — may reduce strength |
| > 15% | Likely strength reduction |

**Properties of Western Sugar PCC:**
- Specific gravity: ~2.71
- Particle size: < 10 μm (finer than cement)
- Color: Bright white
- No pozzolanic reactivity
- Does not contribute to heat of hydration
- Chemically inert in concrete environment

**Mix design note:** In this tool, PCC% is applied as a mass replacement of the cementitious content. Since PCC is inert, the effective w/cm uses only the reactive cementitious materials.

**Related research area:** Sustainable concrete — reducing Portland cement demand using industrial byproducts.

**ACI guidance:** ACI 211.1 does not explicitly address inert fillers — engineering judgment required.

**Related:** ASTM C1797 (limestone filler), EN 197-1 (Portland-limestone cement, European standard)"""
    }

    def get_demo_response(question: str) -> str:
        q = question.lower()
        # Specific standard checks FIRST — most specific wins
        if "c1202" in q or "rcpt" in q or "rapid chloride" in q or "chloride perm" in q:
            return DEMO_RESPONSES["rcpt"]
        elif "scc" in q or "self-consolidat" in q or "self consolidat" in q or "j-ring" in q or "slump flow" in q:
            return DEMO_RESPONSES["scc"]
        elif "uhpc" in q or "ultra-high" in q or "ultra high" in q:
            return DEMO_RESPONSES["uhpc"]
        elif "crack" in q and ("detect" in q or "test" in q or "measur" in q or "done" in q):
            return DEMO_RESPONSES["crack"]
        elif "vebe" in q or ("pavement" in q and ("stiff" in q or "rcc" in q or "roller" in q or "test" in q)):
            return DEMO_RESPONSES["vebe"]
        elif "c143" in q or ("slump" in q and "vebe" not in q and "flow" not in q):
            return DEMO_RESPONSES["c143"]
        elif "c39" in q or "compressive" in q:
            return DEMO_RESPONSES["c39"]
        elif "c231" in q or "air content" in q or "air meter" in q:
            return DEMO_RESPONSES["c231"]
        elif "w/cm" in q or ("water" in q and "cement" in q and "ratio" in q):
            return DEMO_RESPONSES["wcm"]
        elif "pcc" in q or "calcium carbonate" in q or "western sugar" in q:
            return DEMO_RESPONSES["pcc"]
        elif "fly ash" in q or "class c" in q or "class f" in q:
            return DEMO_RESPONSES["fly ash"]
        else:
            return (
                "**Demo mode — specific answer not pre-loaded for this question.**\n\n"
                "In **live mode** (toggle off Demo Mode + add API key), Claude will give you a full answer with:\n"
                "- The exact ASTM/ACI standard number and edition\n"
                "- Step-by-step test procedure\n"
                "- Equipment list\n"
                "- Acceptance criteria\n"
                "- Official ASTM link\n"
                "- Related standards\n\n"
                "**Try one of these pre-loaded demo questions:**\n"
                "- *What is ASTM C143 — slump test?*\n"
                "- *What is ASTM C39 — compressive strength test?*\n"
                "- *What is ASTM C231 — air content test?*\n"
                "- *What does w/cm ratio mean?*\n"
                "- *What is fly ash Class C vs Class F?*\n"
                "- *What is PCC as a cement replacement?*"
            )

    # ── Display chat history ───────────────────────────────────────────────────
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Handle prefill from buttons ───────────────────────────────────────────
    prefill = st.session_state.pop("chat_input_prefill", "")
    user_input = st.chat_input("Ask a concrete question — e.g. 'What is ASTM C143?'", key="concrete_chat")
    active_input = prefill or user_input

    if active_input:
        st.session_state.chat_history.append({"role": "user", "content": active_input})
        with st.chat_message("user"):
            st.markdown(active_input)

        with st.chat_message("assistant"):
            with st.spinner("Looking that up..."):
                if demo_mode:
                    response = get_demo_response(active_input)
                else:
                    api_key = os.getenv("ANTHROPIC_API_KEY", "")
                    client  = anthropic.Anthropic(api_key=api_key)
                    messages = [{"role": m["role"], "content": m["content"]}
                                for m in st.session_state.chat_history]
                    resp = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=1500,
                        system=CONCRETE_SYSTEM,
                        messages=messages,
                    )
                    response = resp.content[0].text

            st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

    # ── Clear chat ────────────────────────────────────────────────────────────
    if st.session_state.get("chat_history"):
        st.markdown("<div style=height:3px;background:linear-gradient(to right,#0033A0,#FFB71B);border-radius:2px;margin:12px 0;></div>", unsafe_allow_html=True)
        col_clear, _ = st.columns([1, 4])
        with col_clear:
            if st.button("🗑️ Clear chat history", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
