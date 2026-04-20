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

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("##### Teymouri Research Lab · South Dakota State University")
st.title("🧱 Concrete Mix Design Copilot")
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

                if is_pdf:
                    content = [
                        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": file_b64}},
                        {"type": "text", "text": f"Review this concrete mix design document. Check ACI 211.1 and ACI 318 compliance, identify any durability concerns, flag w/cm against exposure requirements, and list recommended QC tests. Additional context: {review_notes or 'None'}"}
                    ]
                else:
                    content = [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": file_b64}},
                        {"type": "text", "text": f"Review this concrete mix design document/image. Check ACI 211.1 and ACI 318 compliance, identify any durability concerns, flag w/cm against exposure requirements, and list recommended QC tests. Additional context: {review_notes or 'None'}"}
                    ]

                msg = client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=1500,
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
    st.subheader("💬 Concrete Q&A — Ask anything about concrete")
    st.caption(
        "Ask about concrete properties, mix design theory, ASTM/ACI standards, "
        "test methods, durability, admixtures, SCMs, or anything related to concrete materials. "
        "This assistant is tuned for construction engineering students."
    )

    # Suggested questions as clickable buttons
    st.markdown("**Quick questions to get started:**")
    q_col1, q_col2, q_col3 = st.columns(3)
    suggestions = [
        ("What is the ASTM standard for compressive strength testing?", q_col1),
        ("What does w/cm ratio mean and why does it matter?", q_col2),
        ("What is the difference between fly ash Class C and Class F?", q_col3),
        ("How does air entrainment protect concrete from freeze-thaw?", q_col1),
        ("What is the slump test and what ASTM standard governs it?", q_col2),
        ("What is Precipitated Calcium Carbonate (PCC) as a cement replacement?", q_col3),
    ]
    for question, col in suggestions:
        with col:
            if st.button(question, use_container_width=True):
                st.session_state.chat_input_prefill = question

    st.divider()

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # System prompt — concrete engineering tutor
    CONCRETE_SYSTEM = """You are a concrete materials engineering assistant and tutor at the Teymouri Research Lab, 
South Dakota State University (SDSU). You help construction engineering students understand:

- Concrete mix design theory (ACI 211.1, PCA method)
- Concrete material properties: strength, durability, workability, permeability
- ASTM and ACI standards for concrete testing (always cite the exact standard number)
- Test methods: slump (C143), air content (C231), unit weight (C138), compressive strength (C39), 
  chloride permeability (C1202), shrinkage (C157), freeze-thaw (C666), and others
- Supplementary cementitious materials: fly ash (C618), slag (C989), silica fume (C1240), 
  and PCC (Precipitated Calcium Carbonate) as an inert micro-filler
- Admixtures: water reducers, air entrainers, accelerators, retarders (ASTM C494)
- Exposure classes (ACI 318 Table 19.3): freeze-thaw F0-F3, sulfate S0-S3, water W0-W1, chloride C0-C2
- Concrete durability: freeze-thaw resistance, sulfate attack, alkali-silica reaction, carbonation
- Curing methods and their effect on strength development
- Fresh and hardened concrete properties

When citing standards, always give the full designation (e.g., ASTM C39, ACI 211.1, ACI 318-19).
Keep answers clear and educational. Use examples when helpful. 
If a student asks about PCC, explain it as an inert micro-filler (not a reactive binder) that improves 
particle packing and can provide 5-9% compressive strength gain at 3-8% replacement — this is active 
research at the Teymouri Research Lab using PCC from Western Sugar Cooperative.
Always be encouraging and supportive of students."""

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle prefilled question from suggestion buttons
    prefill = st.session_state.pop("chat_input_prefill", "")

    # Chat input
    user_input = st.chat_input("Ask a concrete question...", key="concrete_chat")

    # Use prefilled question if button was clicked
    active_input = prefill or user_input

    if active_input:
        # Show user message
        st.session_state.chat_history.append({"role": "user", "content": active_input})
        with st.chat_message("user"):
            st.markdown(active_input)

        # Get Claude response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if demo_mode:
                    # Smart demo responses based on keywords
                    q = active_input.lower()
                    if "astm" in q or "standard" in q or "test" in q:
                        response = (
                            "**Key ASTM Standards for Concrete Testing:**\n\n"
                            "- **ASTM C39** — Compressive strength of cylindrical specimens (most common test)\n"
                            "- **ASTM C143** — Slump of hydraulic cement concrete (workability)\n"
                            "- **ASTM C231** — Air content by pressure method (air-entrained concrete)\n"
                            "- **ASTM C138** — Unit weight (density) and yield\n"
                            "- **ASTM C1202** — Rapid chloride permeability (RCPT) — durability\n"
                            "- **ASTM C666** — Freeze-thaw resistance (300 cycles)\n"
                            "- **ASTM C157** — Length change / drying shrinkage\n"
                            "- **ASTM C618** — Fly ash and natural pozzolans specification\n"
                            "- **ASTM C989** — Slag cement specification\n"
                            "- **ASTM C494** — Chemical admixtures (Types A–G)\n\n"
                            "Which standard would you like to learn more about?"
                        )
                    elif "w/cm" in q or "water" in q and "cement" in q:
                        response = (
                            "**Water-to-Cementitious Material Ratio (w/cm)**\n\n"
                            "The w/cm ratio is the single most important parameter in concrete mix design. "
                            "It equals the mass of water divided by the mass of all cementitious materials "
                            "(cement + fly ash + slag + silica fume + PCC).\n\n"
                            "**Why it matters:**\n"
                            "- Lower w/cm → higher strength, lower permeability, better durability\n"
                            "- Higher w/cm → easier to place, but weaker and more permeable\n\n"
                            "**ACI 318 durability limits:**\n"
                            "- F2 (moderate freeze-thaw): max w/cm = 0.45\n"
                            "- F3 (severe, deicers): max w/cm = 0.40\n"
                            "- C2 (chloride exposure): max w/cm = 0.40\n\n"
                            "A good rule of thumb: every 0.05 increase in w/cm reduces 28-day strength by ~10%."
                        )
                    elif "pcc" in q or "calcium carbonate" in q or "western sugar" in q:
                        response = (
                            "**Precipitated Calcium Carbonate (PCC) as a Cement Replacement**\n\n"
                            "PCC is an inert micro-filler — unlike fly ash or slag, it does **not** react "
                            "chemically with cement hydration products. It works through **physical** mechanisms:\n\n"
                            "**Particle packing effect:** PCC particles fill voids between cement grains, "
                            "reducing porosity and improving the microstructure.\n\n"
                            "**Research at Teymouri Research Lab (SDSU):**\n"
                            "- Optimal replacement: **3–8%** by mass of cementitious content\n"
                            "- At 5% PCC: expect **+5–9% compressive strength gain** from packing\n"
                            "- PCC source: Western Sugar Cooperative byproduct (Brookings, SD)\n"
                            "- Does not contribute to early heat of hydration\n"
                            "- No pozzolanic reaction — SG ≈ 2.71\n\n"
                            "This is an active research area — results help reduce Portland cement demand sustainably."
                        )
                    elif "fly ash" in q or "class c" in q or "class f" in q:
                        response = (
                            "**Fly Ash in Concrete — Class C vs Class F (ASTM C618)**\n\n"
                            "**Class F fly ash** (from burning anthracite/bituminous coal):\n"
                            "- SiO₂ + Al₂O₃ + Fe₂O₃ > 70%\n"
                            "- Pozzolanic only — reacts with Ca(OH)₂ from cement hydration\n"
                            "- Slower strength gain, better long-term durability\n"
                            "- Typical replacement: 15–25%\n\n"
                            "**Class C fly ash** (from burning sub-bituminous/lignite coal):\n"
                            "- SiO₂ + Al₂O₃ + Fe₂O₃ > 50%, high CaO content\n"
                            "- Both pozzolanic AND cementitious (self-cementing)\n"
                            "- Faster strength gain than Class F\n"
                            "- More common in the Midwest (including South Dakota)\n\n"
                            "Both reduce heat of hydration, improve workability, and enhance sulfate resistance."
                        )
                    elif "slump" in q:
                        response = (
                            "**Slump Test — ASTM C143**\n\n"
                            "The slump test measures the **workability** (consistency) of fresh concrete.\n\n"
                            "**Procedure:**\n"
                            "1. Fill an Abrams cone (12\" tall) in 3 layers, rod each 25 times\n"
                            "2. Lift the cone straight up in 5±2 seconds\n"
                            "3. Measure the drop from the original height to the top of the concrete\n\n"
                            "**Typical target slumps (ACI 211.1):**\n"
                            "- Footings, walls: 1–3\"\n"
                            "- Beams, columns: 1–4\"\n"
                            "- Pavements, slabs: 1–3\"\n"
                            "- Pumped concrete: 4–6\"\n\n"
                            "**Important:** Test within 5 minutes of sampling, per ASTM C172."
                        )
                    elif "air" in q and ("entrain" in q or "freeze" in q):
                        response = (
                            "**Air Entrainment and Freeze-Thaw Protection**\n\n"
                            "Air entrainment intentionally introduces tiny, uniformly distributed air bubbles "
                            "(0.1–1 mm diameter) into concrete using an air-entraining admixture (ASTM C260).\n\n"
                            "**How it protects against freeze-thaw (ACI 318 Table 19.3.3):**\n"
                            "Water expands ~9% when it freezes. Entrained air bubbles act as **pressure relief "
                            "valves** — water under freezing pressure flows into nearby air voids instead of "
                            "cracking the paste.\n\n"
                            "**Required air content (for 3/4\" max aggregate):**\n"
                            "- F1 exposure: 5.0%\n"
                            "- F2 exposure: 6.0%\n"
                            "- F3 exposure (deicers): 6.0%\n\n"
                            "**Key concept — spacing factor:** Air voids must be within 0.008\" (0.2 mm) "
                            "of any point in the paste (ASTM C457 — air void analysis).\n\n"
                            "Test with ASTM C231 (pressure method) for normal-weight concrete."
                        )
                    else:
                        response = (
                            "**DEMO MODE** — In live mode, Claude would answer your specific question in detail.\n\n"
                            "Try one of the suggested questions above, or turn off Demo Mode and add your "
                            "API key to get full AI-powered answers on any concrete topic including:\n"
                            "- Specific ASTM/ACI standard lookups\n"
                            "- Concrete property calculations\n"
                            "- Mix design theory explanations\n"
                            "- Admixture selection guidance\n"
                            "- Durability and exposure class questions"
                        )
                else:
                    api_key = os.getenv("ANTHROPIC_API_KEY", "")
                    client  = anthropic.Anthropic(api_key=api_key)

                    # Build messages from history
                    messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_history
                    ]

                    resp = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=1000,
                        system=CONCRETE_SYSTEM,
                        messages=messages,
                    )
                    response = resp.content[0].text

            st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

    # Clear chat button
    if st.session_state.get("chat_history"):
        st.divider()
        col_clear, col_space = st.columns([1, 4])
        with col_clear:
            if st.button("🗑️ Clear chat history", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
