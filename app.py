"""
app.py — Normal Concrete Mix Design Sheet for Students and Learners
Teymouri Research Lab | South Dakota State University
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import anthropic
import base64
import os
import io
from datetime import datetime
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from src.aci211 import calculate_mix, SHAPE_WATER_REDUCTION
from src.claude_client import run_analysis
from src.schemas import MixDesignInput, MixDesignResult, ProjectInfo
from src.reporting import generate_pdf_report

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Concrete Mix Design Sheet | Teymouri Research Lab",
    page_icon="🧱",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS  — light, warm, minimal black
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Page background slightly warm */
.stApp { background-color: #F8F9FC; }

/* All default text — navy not black */
html, body, [class*="css"] { color: #2A3A5C; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #F0F4FB;
    border-right: 1px solid #E0E7F5;
}

/* Section header labels */
.sec-label {
    display: flex; align-items: center; gap: 8px;
    margin: 18px 0 10px;
}
.sec-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #FFB71B; flex-shrink: 0;
}
.sec-text {
    font-size: 12px; font-weight: 600; color: #5C6E91;
    letter-spacing: 0.05em; text-transform: uppercase;
}

/* Mode card grid */
.mode-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 10px; margin-bottom: 24px;
}
.mcard {
    background: #FAFBFF; border: 1px solid #E0E7F5;
    border-radius: 10px; padding: 14px 16px; cursor: pointer;
}
.mcard.active { border: 2px solid #0033A0; background: #EEF2FB; }
.mcard-icon { font-size: 20px; margin-bottom: 6px; }
.mcard-title { font-size: 13px; font-weight: 600; color: #1A2B5F; margin-bottom: 3px; }
.mcard.active .mcard-title { color: #0033A0; }
.mcard-desc { font-size: 11px; color: #8A9BB5; line-height: 1.5; }
.badge {
    font-size: 10px; background: #FFB71B; color: #7A5200;
    padding: 2px 7px; border-radius: 99px; font-weight: 600;
    margin-left: 6px; vertical-align: middle;
}

/* Gamma card */
.gamma-card {
    background: #F5F3FF; border: 1px solid #D4CCFF;
    border-radius: 10px; padding: 13px 16px;
    display: flex; align-items: center; gap: 14px; margin-top: 12px;
}
.gamma-logo {
    width: 36px; height: 36px; background: #6C47FF;
    border-radius: 8px; display: flex; align-items: center;
    justify-content: center; color: white; font-weight: 700;
    font-size: 16px; flex-shrink: 0;
}
.gamma-title { font-size: 13px; font-weight: 600; color: #3B2DB5; margin-bottom: 2px; }
.gamma-sub { font-size: 11px; color: #7A6FBB; }

/* SDSU Q&A header */
.qa-header {
    background: #0033A0; color: white;
    padding: 12px 18px; border-radius: 8px 8px 0 0;
    font-weight: 600; font-size: 15px;
}
.qa-gold { height: 3px; background: #FFB71B; border-radius: 0 0 4px 4px; margin-bottom: 14px; }
.qa-qlabel {
    background: #EEF2FB; border-left: 4px solid #0033A0;
    padding: 7px 14px; border-radius: 0 6px 6px 0;
    color: #0033A0; font-weight: 600; font-size: 13px; margin-bottom: 10px;
}

/* Inputs and selects — warmer */
input, select, textarea {
    color: #2A3A5C !important;
    background: #FAFBFF !important;
    border-color: #D8E2F0 !important;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: #EEF2FB;
    border: 1px solid #D8E2F0;
    border-radius: 8px; padding: 12px;
}
div[data-testid="stMetricLabel"] { color: #5C6E91 !important; font-size: 12px !important; }
div[data-testid="stMetricValue"] { color: #0033A0 !important; }

/* Suggestion buttons in Q&A */
div[data-testid="column"] button {
    border-left: 3px solid #0033A0 !important;
    font-size: 12px !important;
    color: #2A3A5C !important;
    background: #FAFBFF !important;
}
div[data-testid="column"] button:hover {
    border-left: 3px solid #FFB71B !important;
    background: #EEF2FB !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**Teymouri Research Lab**")
    st.caption("Dept. of Construction & Concrete Industry Management\nJerome J. Lohr College of Engineering\nSouth Dakota State University")
    st.divider()
    demo_mode = st.toggle("Demo mode (no API cost)", value=True)
    st.caption("Turn off + add API key to `.env` for live Claude inference.")
    st.divider()

    st.markdown("**💾 Saved mix designs**")
    if "saved_mixes" not in st.session_state:
        st.session_state.saved_mixes = {}
    if st.session_state.saved_mixes:
        for name in list(st.session_state.saved_mixes.keys()):
            cl, cr = st.columns([3,1])
            with cl:
                if st.button(f"📂 {name}", key=f"load_{name}", use_container_width=True):
                    st.session_state.load_mix = name
                    st.rerun()
            with cr:
                if st.button("✕", key=f"del_{name}"):
                    del st.session_state.saved_mixes[name]
                    st.rerun()
    else:
        st.caption("No saved mixes yet.")

    st.divider()
    st.markdown("**📊 Comparison**")
    if "comparison_mixes" not in st.session_state:
        st.session_state.comparison_mixes = []
    n = len(st.session_state.comparison_mixes)
    st.caption(f"{n} mix{'es' if n!=1 else ''} in comparison table")
    if n > 0 and st.button("🗑️ Clear comparison", use_container_width=True):
        st.session_state.comparison_mixes = []
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#0033A0;padding:11px 18px;border-radius:8px 8px 0 0;
     display:flex;align-items:center;justify-content:space-between;">
  <div>
    <span style="color:white;font-size:14px;font-weight:600;">Teymouri Research Lab</span><br>
    <span style="color:#B3C3E8;font-size:11px;">South Dakota State University · Jerome J. Lohr College of Engineering</span>
  </div>
  <span style="color:#B3C3E8;font-size:11px;background:rgba(255,255,255,0.12);
        padding:3px 10px;border-radius:99px;">ACI 211.1</span>
</div>
<div style="height:3px;background:#FFB71B;border-radius:0 0 4px 4px;margin-bottom:20px;"></div>
""", unsafe_allow_html=True)

st.markdown("<h1 style='font-size:22px;font-weight:600;color:#1A2B5F;margin-bottom:4px;'>"
            "Normal Concrete Mix Design Sheet</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size:13px;color:#8A9BB5;margin-bottom:18px;'>"
            "For students and learners &nbsp;·&nbsp; Teymouri Research Lab &nbsp;·&nbsp; SDSU</p>",
            unsafe_allow_html=True)
st.markdown("<hr style='border:none;border-top:1px solid #E0E7F5;margin-bottom:20px;'>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODE CARDS
# ─────────────────────────────────────────────────────────────────────────────
if "mode" not in st.session_state:
    st.session_state.mode = None

st.markdown("""
<div class="mode-grid">
  <div class="mcard" id="mc-qa">
    <div class="mcard-icon">💬</div>
    <div class="mcard-title">Ask a question <span class="badge">Start here</span></div>
    <div class="mcard-desc">ASTM standards, test methods, SCMs, UHPC, SCC, and more</div>
  </div>
  <div class="mcard" id="mc-design">
    <div class="mcard-icon">🔬</div>
    <div class="mcard-title">Design a new mix</div>
    <div class="mcard-desc">ACI 211.1 proportioning with AI durability check</div>
  </div>
  <div class="mcard" id="mc-review">
    <div class="mcard-icon">📄</div>
    <div class="mcard-title">Review a mix design</div>
    <div class="mcard-desc">Upload PDF or photo for AI review</div>
  </div>
  <div class="mcard" id="mc-compare">
    <div class="mcard-icon">📊</div>
    <div class="mcard-title">Compare mixes</div>
    <div class="mcard-desc">Side-by-side table and Excel export</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Buttons that actually work for mode selection
b1, b2, b3, b4 = st.columns(4)
with b1:
    if st.button("💬 Ask a question", use_container_width=True, key="btn_qa"):
        st.session_state.mode = "qa"
        st.rerun()
with b2:
    if st.button("🔬 Design a mix", use_container_width=True, key="btn_design"):
        st.session_state.mode = "design"
        st.rerun()
with b3:
    if st.button("📄 Review a mix", use_container_width=True, key="btn_review"):
        st.session_state.mode = "review"
        st.rerun()
with b4:
    if st.button("📊 Compare mixes", use_container_width=True, key="btn_compare"):
        st.session_state.mode = "compare"
        st.rerun()

if st.session_state.mode is None:
    st.stop()

mode = st.session_state.mode
st.markdown("<hr style='border:none;border-top:1px solid #E0E7F5;margin:8px 0 20px;'>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Excel export
# ─────────────────────────────────────────────────────────────────────────────
def make_excel(mixes):
    wb = Workbook()
    ws = wb.active
    ws.title = "Mix Comparison"
    hdr_font  = Font(name="Arial", bold=True, color="FFFFFF", size=10)
    hdr_fill  = PatternFill("solid", fgColor="0033A0")
    gray_fill = PatternFill("solid", fgColor="F5F7FB")
    bold_font = Font(name="Arial", bold=True, size=10)
    reg_font  = Font(name="Arial", size=10)
    center    = Alignment(horizontal="center", vertical="center")
    left      = Alignment(horizontal="left", vertical="center")
    thin      = Side(style="thin", color="D0D8EC")
    border    = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells(f"A1:{get_column_letter(len(mixes)+1)}1")
    ws["A1"] = "Teymouri Research Lab — Concrete Mix Design Comparison"
    ws["A1"].font = Font(name="Arial", bold=True, size=13, color="1A2B5F")
    ws["A1"].alignment = center
    ws.row_dimensions[1].height = 22

    ws.merge_cells(f"A2:{get_column_letter(len(mixes)+1)}2")
    ws["A2"] = f"Generated: {datetime.now().strftime('%B %d, %Y')} | ACI 211.1 (PCA Method) | SDSU"
    ws["A2"].font = Font(name="Arial", size=9, color="8A9BB5", italic=True)
    ws["A2"].alignment = center

    ws["A4"] = "Parameter"
    ws["A4"].font = hdr_font; ws["A4"].fill = hdr_fill
    ws["A4"].alignment = left; ws["A4"].border = border
    ws.column_dimensions["A"].width = 30

    for i,(label,aci,inp) in enumerate(mixes):
        col = get_column_letter(i+2)
        ws[f"{col}4"] = label
        ws[f"{col}4"].font = hdr_font; ws[f"{col}4"].fill = hdr_fill
        ws[f"{col}4"].alignment = center; ws[f"{col}4"].border = border
        ws.column_dimensions[col].width = 18

    def section(title, rows, r):
        ws.merge_cells(f"A{r}:{get_column_letter(len(mixes)+1)}{r}")
        ws[f"A{r}"] = title
        ws[f"A{r}"].font = Font(name="Arial", bold=True, size=10, color="FFFFFF")
        ws[f"A{r}"].fill = PatternFill("solid", fgColor="0033A0")
        ws[f"A{r}"].alignment = left; ws[f"A{r}"].border = border
        ws.row_dimensions[r].height = 18
        r += 1
        for j,(param,vals) in enumerate(rows):
            fill = gray_fill if j%2==0 else PatternFill("solid", fgColor="FFFFFF")
            ws[f"A{r}"] = param
            ws[f"A{r}"].font = bold_font; ws[f"A{r}"].fill = fill
            ws[f"A{r}"].border = border; ws[f"A{r}"].alignment = left
            for k,val in enumerate(vals):
                col = get_column_letter(k+2)
                ws[f"{col}{r}"] = val
                ws[f"{col}{r}"].font = reg_font; ws[f"{col}{r}"].fill = fill
                ws[f"{col}{r}"].border = border; ws[f"{col}{r}"].alignment = center
            r += 1
        return r

    inp_rows = [
        ("Required f'c (psi)",       [f"{m[2].fc_psi:,}" for m in mixes]),
        ("Exposure codes",            [", ".join(m[2].exposure_codes) for m in mixes]),
        ("Max agg size (in)",         [m[2].agg_size for m in mixes]),
        ("w/cm",                      [str(m[1]["selected_wcm"]) for m in mixes]),
        ("Air content (%)",           [str(m[1]["air_pct"]) for m in mixes]),
        ("Fly ash (%)",               [str(m[2].flyash_pct) for m in mixes]),
        ("Slag (%)",                  [str(m[2].slag_pct) for m in mixes]),
        ("Silica fume (%)",           [str(m[2].sf_pct) for m in mixes]),
        ("PCC (%)",                   [str(m[2].pcc_pct) for m in mixes]),
    ]
    res_rows = [
        ("Water (lbs/CY)",            [str(m[1]["proportions"]["water_lbs"]) for m in mixes]),
        ("Portland cement (lbs/CY)",  [str(m[1]["proportions"]["cement_lbs"]) for m in mixes]),
        ("Fly ash (lbs/CY)",          [str(m[1]["proportions"]["flyash_lbs"]) for m in mixes]),
        ("Slag (lbs/CY)",             [str(m[1]["proportions"]["slag_lbs"]) for m in mixes]),
        ("PCC (lbs/CY)",              [str(m[1]["proportions"]["pcc_lbs"]) for m in mixes]),
        ("Coarse agg (lbs/CY)",       [str(m[1]["proportions"]["ca_lbs"]) for m in mixes]),
        ("Fine agg (lbs/CY)",         [str(m[1]["proportions"]["fa_lbs"]) for m in mixes]),
        ("Total CM (lbs/CY)",         [str(m[1]["proportions"]["total_cm_lbs"]) for m in mixes]),
        ("Fresh density (pcf)",       [str(m[1]["density_pcf"]) for m in mixes]),
    ]
    r = section("INPUTS", inp_rows, 6)
    r = section("ACI 211.1 RESULTS", res_rows, r+1)
    r += 1
    ws.merge_cells(f"A{r}:{get_column_letter(len(mixes)+1)}{r}")
    ws[f"A{r}"] = "Teymouri Research Lab · SDSU · ACI 211.1 · Not a substitute for a licensed engineer"
    ws[f"A{r}"].font = Font(name="Arial", size=8, color="8A9BB5", italic=True)
    ws[f"A{r}"].alignment = center
    out = io.BytesIO(); wb.save(out); return out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# MODE: Q&A
# ─────────────────────────────────────────────────────────────────────────────
if mode == "qa":
    st.markdown("""
    <div class="qa-header">💬 &nbsp; Concrete Q&A — Ask anything</div>
    <div class="qa-gold"></div>
    """, unsafe_allow_html=True)
    st.caption("Ask about ASTM/ACI test standards, concrete properties, mix design theory, SCMs, UHPC, SCC, durability, and more.")

    st.markdown('<div class="qa-qlabel">Quick questions to get started</div>', unsafe_allow_html=True)
    qc1, qc2, qc3 = st.columns(3)
    suggestions = [
        ("What are SCMs in concrete?", qc1),
        ("What is ASTM C143 — slump test?", qc2),
        ("What is ASTM C39 — compressive strength?", qc3),
        ("What is ASTM C1202 — RCPT test?", qc1),
        ("What are SCC tests and standards?", qc2),
        ("What is UHPC and how is it tested?", qc3),
        ("How is crack detection done?", qc1),
        ("What is the Vebe test for pavement?", qc2),
        ("What is fly ash Class C vs Class F?", qc3),
        ("What is the ITZ in concrete?", qc1),
        ("How does carbonation affect concrete?", qc2),
        ("What is ASTM C231 — air content?", qc3),
    ]
    for question, col in suggestions:
        with col:
            if st.button(question, use_container_width=True, key=f"q_{question[:25]}"):
                st.session_state.chat_input_prefill = question

    st.divider()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    SYSTEM = """You are a concrete materials engineering tutor at the Teymouri Research Lab, SDSU.
Help students understand concrete science clearly and rigorously.
For ASTM/ACI standards: give designation, purpose, equipment, numbered procedure, acceptance criteria, Google search terms.
For graduate topics (ITZ, carbonation, ASR, pozzolanic reaction): give mechanistic in-depth explanations.
PCC research (Teymouri Lab): Precipitated CaCO3 from Western Sugar Cooperative — inert micro-filler, 3-8% optimal, +5-9% strength gain from particle packing, no pozzolanic activity, SG≈2.71.
Always cite standard numbers. Be encouraging and clear."""

    DEMOS = {
        "scm": """**Supplementary Cementitious Materials (SCMs)**

Materials that partially replace Portland cement. They react with cement hydration products to form additional C-S-H binding gel.

| SCM | Standard | Reactivity | Typical % | Key benefit |
|---|---|---|---|---|
| Fly ash Class F | ASTM C618 | Pozzolanic | 15–25% | Durability, cost |
| Fly ash Class C | ASTM C618 | Pozzolanic + cementitious | 20–35% | Faster than F |
| Slag cement | ASTM C989 | Latent hydraulic | 25–50% | Low permeability |
| Silica fume | ASTM C1240 | High pozzolanic | 5–10% | Very high strength |
| **PCC** (Teymouri Lab) | — | **Inert filler** | 3–8% | Particle packing |

**Pozzolanic reaction:**
SiO₂ (SCM) + Ca(OH)₂ (cement hydration) + H₂O → **C-S-H** (additional binding gel)

Benefits: lower CO₂, better long-term durability, reduced heat of hydration.

🔍 Search: `supplementary cementitious materials SCM concrete ACI guide`""",

        "c143": """**ASTM C143 — Slump Test**

**Purpose:** Measures workability (consistency) of fresh concrete.
**Equipment:** Abrams cone (4″ top, 8″ base, 12″ height), tamping rod (5/8″ × 24″), base plate, ruler.

**Procedure:**
1. Dampen cone and base plate; stand on foot pieces
2. Sample per ASTM C172 — begin within 5 minutes
3. Fill in **3 equal layers**; rod each **25 times**
4. Strike off top; lift cone straight up in **5 ± 2 seconds**
5. Measure drop to nearest **1/4″**; complete within 2.5 minutes

**Target slumps (ACI 211.1):**
| Element | Slump |
|---|---|
| Footings / walls | 1–3″ |
| Beams / columns | 1–4″ |
| Pavements / slabs | 1–3″ |
| Pumped concrete | 4–6″ |

🔍 Search: `ASTM C143 slump test procedure concrete`""",

        "c39": """**ASTM C39 — Compressive Strength of Concrete Cylinders**

**Purpose:** Measures f'c — primary quality control and acceptance test.
**Equipment:** Compression machine (calibrated per ASTM E4), 4×8″ cylinders, neoprene pads (ASTM C1231).

**Procedure:**
1. Make specimens per ASTM C192; fill in 2 layers, rod 25× each
2. Cure in molds at 60–80°F for 24 ± 8 hours
3. Strip; moist cure at 73 ± 3°F until test age
4. Cap ends flat within 0.002″
5. Load at **35 ± 7 psi/second** continuously
6. **f'c = Load ÷ Area**; note fracture pattern

**Test ages:** 7 days (early check) · **28 days** (acceptance)
**ACI 318:** Average of 2 cylinders ≥ f'c; no single cylinder < f'c − 500 psi

🔍 Search: `ASTM C39 compressive strength concrete cylinder procedure`""",

        "c231": """**ASTM C231 — Air Content (Pressure Method)**

**Purpose:** Measures total air content (%) using Boyle's Law. For normal-weight aggregate only.

**Procedure:**
1. Fill meter bowl in 3 layers, rod 25×, tap sides 10–15 times
2. Clamp cover; inject water through petcocks; close petcocks
3. Pump to initial pressure; open main valve; read gauge
4. Subtract **aggregate correction factor** (Annex A2)

**Required air — 3/4″ aggregate (ACI 318):**
| Exposure | Air % |
|---|---|
| F1 moderate freeze-thaw | 5.0% |
| F2 severe freeze-thaw | 6.0% |
| F3 deicers | 6.0% |

Note: Use ASTM C173 (volumetric) for lightweight aggregate.

🔍 Search: `ASTM C231 air content pressure meter concrete`""",

        "rcpt": """**ASTM C1202 — Rapid Chloride Permeability Test (RCPT)**

**Purpose:** Measures electrical conductance as indicator of chloride resistance. Key durability test for bridge decks, marine structures.

**Procedure:**
1. Cut 2″ disc from 4×8″ cylinder (mid-height, wet saw)
2. Vacuum saturate 18 hours (Annex A)
3. Mount between cells: **3% NaCl** one side, **0.3N NaOH** other
4. Apply **60V DC for 6 hours**; log current every 30 min
5. Total charge (coulombs) = area under current-time curve

**Classification:**
| Coulombs | Rating |
|---|---|
| > 4,000 | High permeability |
| 2,000–4,000 | Moderate |
| 1,000–2,000 | Low |
| 100–1,000 | Very low |
| < 100 | Negligible |

Test at **56 days** for SCM mixes — earlier underestimates durability.

🔍 Search: `ASTM C1202 RCPT rapid chloride permeability test`""",

        "scc": """**Self-Consolidating Concrete (SCC) — Key Tests**

Flows under own weight with no vibration. Standard slump is insufficient — use these 4 tests:

**1. ASTM C1611 — Slump Flow + T50**
- Spread target: 18–32″ | T50 (time to 20″): 2–7 sec
- VSI: 0–1 stable, 2–3 unstable

**2. ASTM C1621 — J-Ring (passing ability)**
- Difference from free slump ≤ 2″ = good passing ability

**3. ASTM C1610 — Column Segregation**
- Segregation index ≤ 10% = acceptable

**4. ASTM C1712 — Penetration (site check)**

Typical SCC mix: w/cm 0.32–0.42 · paste volume 34–40% · HRWRA required

🔍 Search: `ASTM C1611 slump flow SCC self consolidating concrete`""",

        "uhpc": """**Ultra-High Performance Concrete (UHPC)**

f'c ≥ 14,500 psi (100 MPa), no coarse aggregate, steel fibers (2% vol.).

**Typical mix (per CY):**
| Material | Amount |
|---|---|
| Cement | 700–900 lb |
| Silica fume | 200–250 lb (25–30%) |
| Quartz sand | 900–1100 lb |
| Steel fibers | ~260 lb |
| w/cm | 0.14–0.22 |

**Key tests:**
| Test | Standard | UHPC value |
|---|---|---|
| Compressive | ASTM C39 | 14,500–29,000 psi |
| Flexural | **ASTM C1609** | 2,000–4,000 psi |
| Chloride | ASTM C1202 | < 100 coulombs |

Curing: steam at **194°F for 48 hours**.

🔍 Search: `FHWA HRT-14-084 UHPC state of the art report PDF`""",

        "crack": """**Crack Detection in Concrete — NDT Methods**

**Visual inspection first:** Crack comparator gauge → ACI 224R limits (> 0.013″ = concern)

**NDT Methods:**

| Method | Standard | What it detects |
|---|---|---|
| Ultrasonic Pulse Velocity | ASTM C597 | Velocity loss from cracks; > 14,000 ft/s = sound |
| Impact-Echo | ASTM C1383 | Delamination, voids in slabs |
| Ground Penetrating Radar | ASTM D6432 | Cracks, rebar, voids — fast scan |
| Acoustic Emission | ASTM E1316 | Active crack propagation monitoring |

**Crack width guide (ACI 224R):**
| Width | Action |
|---|---|
| < 0.006″ | Monitor |
| 0.006–0.013″ | Acceptable outdoors |
| > 0.013″ | Investigate cause |
| > 0.020″ | Structural concern |

🔍 Search: `ACI 224R crack control concrete NDT methods`""",

        "vebe": """**Vebe Test — ASTM C1170 (Stiff / RCC Pavement Concrete)**

Used when slump = 0″ and meaningless. Measures workability of roller-compacted concrete.

**Equipment:** Vibrating table (50 Hz), Abrams cone, cylindrical container, Plexiglass disc, stopwatch.

**Procedure:**
1. Fill cone in cylindrical container (3 layers, 25 rods each)
2. Remove cone; place Plexiglass disc on top
3. Start vibrator + stopwatch simultaneously
4. Stop when disc underside fully covered with mortar
5. Record time to nearest **0.5 second**

**Vebe time classification:**
| Time | Class | Use |
|---|---|---|
| 3–5 s | V0 | Wet RCC |
| **6–12 s** | **V1** | **Standard RCC pavement** |
| 12–20 s | V2 | Dry RCC / lean base |
| > 20 s | V3–V4 | Very stiff / dry-cast |

🔍 Search: `ASTM C1170 Vebe test roller compacted concrete pavement`""",

        "flyash": """**Fly Ash — Class C vs Class F (ASTM C618)**

| Property | Class F | Class C |
|---|---|---|
| Coal source | Anthracite/bituminous | Sub-bituminous/lignite |
| SiO₂+Al₂O₃+Fe₂O₃ | > 70% | > 50% |
| CaO content | Low (< 10%) | High (15–35%) |
| Reactivity | Pozzolanic only | Pozzolanic + cementitious |
| Self-cementing | No | **Yes** |
| Strength gain | Slower, long-term | Faster |
| Common in SD | Less | **Yes — very common** |

**Pozzolanic reaction:** SiO₂ + Ca(OH)₂ → C-S-H (slow, benefits at 28–90 days)

Typical replacement: F = 15–25% · C = 20–35%

🔍 Search: `ASTM C618 fly ash Class C Class F concrete difference`""",

        "itz": """**Interfacial Transition Zone (ITZ)**

The ~20–50 μm zone of cement paste around aggregate particles. **Weakest zone in concrete.**

**Why it exists:** Water films form around aggregates during mixing (wall effect) → higher local w/c, more porous microstructure, larger Ca(OH)₂ crystals.

**Microstructure zones:**
- 0–5 μm: Ca(OH)₂ duplex film
- 5–20 μm: ettringite + Ca(OH)₂ rich
- 20–50 μm: transition to bulk paste

**Effect on properties:**
- Strength: cracks initiate at ITZ under load
- Permeability: preferential pathway for chloride and water
- Durability: weakest link for freeze-thaw, sulfate, ASR

**How SCMs improve ITZ:**
- Silica fume fills ITZ voids → dramatically improves bond
- Fly ash / slag react with Ca(OH)₂ → densify ITZ

🔍 Search: `interfacial transition zone ITZ concrete microstructure SEM`""",

        "carbonation": """**Carbonation of Concrete**

**Reaction:** CO₂ + Ca(OH)₂ → CaCO₃ + H₂O

**Why it matters:** pH drops from 12.5–13.5 → 8–9 → passive film on rebar destroyed → corrosion starts.

**Carbonation depth model:** d = K × √t
(d = depth mm, K = rate coefficient, t = years)

**Factors increasing carbonation rate:**
- Higher w/cm → more permeable
- High SCM content → less Ca(OH)₂ reserve
- Poor curing → porous surface zone

**Testing:** Cut or core section → spray **phenolphthalein**
- Pink/magenta = uncarbonated (pH > 9)
- Colorless = carbonated (pH < 9)

**Protection:** w/cm ≤ 0.45, adequate cover (ACI 318 Table 20.6.1), proper curing.

🔍 Search: `concrete carbonation mechanism phenolphthalein test rebar corrosion`""",
    }

    def get_response(q):
        q = q.lower()
        if "scm" in q or "supplementary" in q or "cementitious material" in q: return DEMOS["scm"]
        if "c1202" in q or "rcpt" in q or "rapid chloride" in q: return DEMOS["rcpt"]
        if "scc" in q or "self-consolidat" in q or "j-ring" in q or "slump flow" in q: return DEMOS["scc"]
        if "uhpc" in q or "ultra-high" in q or "ultra high" in q: return DEMOS["uhpc"]
        if "crack" in q and ("detect" in q or "test" in q or "done" in q or "method" in q): return DEMOS["crack"]
        if "vebe" in q or ("pavement" in q and ("rcc" in q or "roller" in q)): return DEMOS["vebe"]
        if "c143" in q or ("slump" in q and "flow" not in q and "vebe" not in q): return DEMOS["c143"]
        if "c39" in q or "compressive" in q: return DEMOS["c39"]
        if "c231" in q or "air content" in q: return DEMOS["c231"]
        if "fly ash" in q or "class c" in q or "class f" in q: return DEMOS["flyash"]
        if "itz" in q or "interfacial" in q or "transition zone" in q: return DEMOS["itz"]
        if "carbonat" in q: return DEMOS["carbonation"]
        return ("**This question isn't pre-loaded in demo mode.**\n\n"
                "Turn off Demo Mode and add your API key to get a full AI answer.\n\n"
                "Pre-loaded topics: SCMs · Slump (C143) · Compressive strength (C39) · "
                "Air content (C231) · RCPT (C1202) · SCC · UHPC · Crack detection · "
                "Vebe test · Fly ash C vs F · ITZ · Carbonation")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prefill    = st.session_state.pop("chat_input_prefill", "")
    user_input = st.chat_input("Ask anything about concrete...", key="chat_in")
    active     = prefill or user_input

    if active:
        st.session_state.chat_history.append({"role":"user","content":active})
        with st.chat_message("user"):
            st.markdown(active)
        with st.chat_message("assistant"):
            with st.spinner("Looking that up..."):
                if demo_mode:
                    response = get_response(active)
                else:
                    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY",""))
                    msgs   = [{"role":m["role"],"content":m["content"]} for m in st.session_state.chat_history]
                    resp   = client.messages.create(model="claude-opus-4-5", max_tokens=1500, system=SYSTEM, messages=msgs)
                    response = resp.content[0].text
            st.markdown(response)
            st.session_state.chat_history.append({"role":"assistant","content":response})

    if st.session_state.get("chat_history"):
        st.markdown("<hr style='border:none;border-top:1px solid #E0E7F5;margin:12px 0;'>", unsafe_allow_html=True)
        cc, _ = st.columns([1,4])
        with cc:
            if st.button("🗑️ Clear chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MODE: DESIGN
# ─────────────────────────────────────────────────────────────────────────────
elif mode == "design":
    load_defaults = {}
    if "load_mix" in st.session_state:
        name = st.session_state.pop("load_mix")
        if name in st.session_state.saved_mixes:
            load_defaults = st.session_state.saved_mixes[name]
            st.success(f"Loaded: **{name}**")

    def D(key, fallback): return load_defaults.get(key, fallback)

    with st.expander("📋 Project information (optional)"):
        pi1, pi2 = st.columns(2)
        with pi1:
            proj_name   = st.text_input("Project name",  value=D("proj_name",""),  placeholder="e.g. US-14 Bridge Deck")
            location    = st.text_input("Location",       value=D("location",""),   placeholder="e.g. Brookings, SD")
        with pi2:
            prepared_by = st.text_input("Prepared by",   value=D("prepared_by",""),placeholder="e.g. Dr. Mohammad Teymouri, PE")
            company     = st.text_input("Organization",  value=D("company",""),    placeholder="e.g. SDSU Teymouri Research Lab")

    with st.expander("🏭 Material producers (optional)"):
        mp1, mp2 = st.columns(2)
        with mp1:
            cement_prod = st.text_input("Cement producer", value=D("cement_prod",""), placeholder="e.g. Ash Grove, Type I/II")
            flyash_prod = st.text_input("Fly ash",          value=D("flyash_prod",""), placeholder="e.g. Basin Electric, Class F")
            slag_prod   = st.text_input("Slag",             value=D("slag_prod",""),   placeholder="e.g. Lafarge, Grade 100")
        with mp2:
            sf_prod     = st.text_input("Silica fume",      value=D("sf_prod",""),     placeholder="e.g. Elkem, densified")
            pcc_prod    = st.text_input("PCC producer",     value=D("pcc_prod",""),    placeholder="e.g. Western Sugar Cooperative")

    with st.form("mix_form"):
        st.markdown('<div class="sec-label"><div class="sec-dot"></div><span class="sec-text">Exposure & strength</span></div>', unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            fc_psi        = st.number_input("Required f'c (psi)", 2000, 12000, D("fc_psi",5000), 500)
            ft_class      = st.selectbox("Freeze-thaw", ["F0 — protected","F1 — limited moisture","F2 — moisture exposed","F3 — deicers"], index=D("ft_idx",1))
            water_class   = st.selectbox("Water exposure", ["W0 — protected","W1 — low permeability required"], index=D("w_idx",0))
        with c2:
            sulfate_class = st.selectbox("Sulfate", ["S0 — protected","S1 — moderate","S2 — severe","S3 — very severe"], index=D("s_idx",0))
            chloride_class= st.selectbox("Chloride", ["C0 — protected","C2 — deicers / seawater"], index=D("c_idx",0))
            air_entrained = st.checkbox("Air-entrained mix", value=D("air_entrained",True))

        st.markdown('<div class="sec-label"><div class="sec-dot"></div><span class="sec-text">Aggregate & workability</span></div>', unsafe_allow_html=True)
        c3,c4 = st.columns(2)
        with c3:
            agg_size      = st.selectbox("Max agg size", ["3/8","1/2","3/4","1","1-1/2","2"], index=D("agg_idx",2))
            slump         = st.selectbox("Target slump (in)", ["1-2","3-4","6-7"], index=D("slump_idx",0))
            agg_shape     = st.selectbox("Aggregate shape", list(SHAPE_WATER_REDUCTION.keys()), index=D("shape_idx",2))
        with c4:
            fm_fa         = st.number_input("Fineness modulus (FA)", 2.3, 3.1, D("fm_fa",2.77), 0.01)
            sg_ca         = st.number_input("SG coarse aggregate",   2.4, 3.0, D("sg_ca",2.65), 0.01)
            sg_fa         = st.number_input("SG fine aggregate",     2.4, 3.0, D("sg_fa",2.68), 0.01)
            rodded_density= st.number_input("Rodded density CA (lbs/ft³)", 70.0, 120.0, D("rodded",100.0), 1.0)

        st.markdown('<div class="sec-label"><div class="sec-dot"></div><span class="sec-text">SCMs</span></div>', unsafe_allow_html=True)
        cs1,cs2,cs3,cs4 = st.columns(4)
        with cs1: flyash_pct = st.number_input("Fly ash (%)", 0, 40, D("flyash_pct",0), 5)
        with cs2: slag_pct   = st.number_input("Slag (%)",    0, 50, D("slag_pct",0),   5)
        with cs3: sf_pct     = st.number_input("Silica fume (%)", 0, 15, D("sf_pct",0), 1)
        with cs4: pcc_pct    = st.number_input("PCC (%)",     0, 20, D("pcc_pct",5),    1, help="Optimal: 3–8%")

        total_scm = flyash_pct + slag_pct + sf_pct + pcc_pct
        if total_scm > 0:
            st.caption(f"Total SCM: {total_scm}%  →  Portland cement: {100-total_scm}%")

        with st.expander("Advanced: SCM specific gravities"):
            sg1,sg2,sg3,sg4 = st.columns(4)
            with sg1: sg_flyash = st.number_input("SG fly ash",    2.0, 3.0, D("sg_flyash",2.65), 0.01)
            with sg2: sg_slag   = st.number_input("SG slag",       2.0, 3.0, D("sg_slag",2.85),   0.01)
            with sg3: sg_sf     = st.number_input("SG silica fume",2.0, 2.5, D("sg_sf",2.20),     0.01)
            with sg4: sg_pcc    = st.number_input("SG PCC",        2.0, 3.0, D("sg_pcc",2.71),    0.01)

        wcm_on = st.checkbox("Override w/cm manually")
        wcm_override = st.slider("w/cm", 0.28, 0.70, D("wcm_ov",0.45), 0.01) if wcm_on else None

        st.markdown('<div class="sec-label"><div class="sec-dot"></div><span class="sec-text">Notes</span></div>', unsafe_allow_html=True)
        mix_label   = st.text_input("Mix label (for comparison)", value=D("mix_label",""), placeholder="e.g. Mix A — 5% PCC")
        field_notes = st.text_area("Field notes / context", value=D("field_notes",""), placeholder="e.g. Bridge deck, F2 exposure, pump placement...", height=70)

        submitted = st.form_submit_button("Run mix design analysis", use_container_width=True)

    # Parametric slider
    st.markdown('<div class="sec-label"><div class="sec-dot"></div><span class="sec-text">Parametric sensitivity — PCC %</span></div>', unsafe_allow_html=True)
    st.caption("Move to instantly see how PCC replacement affects proportions.")
    param_pcc = st.slider("PCC replacement (%)", 0, 20, int(pcc_pct), 1, key="param_pcc")
    if param_pcc != pcc_pct:
        codes_p = [ft_class.split(" ")[0], water_class.split(" ")[0], sulfate_class.split(" ")[0], chloride_class.split(" ")[0]]
        aci_p = calculate_mix(fc_psi=fc_psi, exposure_codes=codes_p, agg_size=agg_size,
            slump=slump, fm_fa=fm_fa, sg_ca=sg_ca, sg_fa=sg_fa,
            rodded_density_ca=rodded_density, agg_shape=agg_shape,
            flyash_pct=float(flyash_pct), slag_pct=float(slag_pct), sf_pct=float(sf_pct),
            pcc_pct=float(param_pcc), air_entrained=air_entrained)
        pp = aci_p["proportions"]
        pm1,pm2,pm3,pm4 = st.columns(4)
        pm1.metric("Water", f"{pp['water_lbs']:.0f} lbs/CY")
        pm2.metric("Cement", f"{pp['cement_lbs']:.0f} lbs/CY")
        pm3.metric("PCC", f"{pp['pcc_lbs']:.0f} lbs/CY", delta=f"@ {param_pcc}%")
        pm4.metric("w/cm", f"{aci_p['selected_wcm']:.2f}")

    if submitted:
        if total_scm >= 100:
            st.error("Total SCM cannot be 100% or more.")
            st.stop()

        codes = [ft_class.split(" ")[0], water_class.split(" ")[0], sulfate_class.split(" ")[0], chloride_class.split(" ")[0]]
        pi = ProjectInfo(project_name=proj_name, location=location, prepared_by=prepared_by, company=company,
                         cement_producer=cement_prod, flyash_producer=flyash_prod,
                         slag_producer=slag_prod, sf_producer=sf_prod, pcc_producer=pcc_prod)
        inp = MixDesignInput(fc_psi=fc_psi, exposure_codes=codes, agg_size=agg_size,
            slump=slump, fm_fa=fm_fa, sg_ca=sg_ca, sg_fa=sg_fa,
            rodded_density_ca=rodded_density, agg_shape=agg_shape,
            flyash_pct=float(flyash_pct), slag_pct=float(slag_pct), sf_pct=float(sf_pct),
            pcc_pct=float(pcc_pct), sg_flyash=sg_flyash, sg_slag=sg_slag, sg_sf=sg_sf, sg_pcc=sg_pcc,
            air_entrained=air_entrained, wcm_override=wcm_override, field_notes=field_notes, project_info=pi)

        with st.spinner("Calculating..."):
            aci = calculate_mix(fc_psi=inp.fc_psi, exposure_codes=inp.exposure_codes, agg_size=inp.agg_size,
                slump=inp.slump, fm_fa=inp.fm_fa, sg_ca=inp.sg_ca, sg_fa=inp.sg_fa,
                rodded_density_ca=inp.rodded_density_ca, agg_shape=inp.agg_shape,
                flyash_pct=inp.flyash_pct, slag_pct=inp.slag_pct, sf_pct=inp.sf_pct,
                pcc_pct=inp.pcc_pct, sg_flyash=inp.sg_flyash, sg_slag=inp.sg_slag,
                sg_sf=inp.sg_sf, sg_pcc=inp.sg_pcc, air_entrained=inp.air_entrained, wcm_override=inp.wcm_override)
            result = run_analysis(inp, aci, demo_mode)

        st.markdown("<hr style='border:none;border-top:1px solid #E0E7F5;margin:16px 0;'>", unsafe_allow_html=True)
        risk_icons = {"Low":"🟢","Moderate":"🟡","High":"🔴"}
        st.subheader(f"{risk_icons.get(result.risk_level,'🟡')} Risk: {result.risk_level}")
        st.info(result.ai_analysis)

        p = aci["proportions"]
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Design f'c",  f"{aci['design_fc_psi']:,} psi")
        c2.metric("w/cm",        f"{aci['selected_wcm']:.2f}")
        c3.metric("Air content", f"{aci['air_pct']}%")
        c4.metric("Density",     f"{aci['density_pcf']} pcf")
        c5.metric("Volume/CY",   f"{aci['volumes_ft3']['total']:.2f} ft³")

        rows = [("Water",f"{p['water_lbs']:.0f}","—"),
                ("Portland cement",f"{p['cement_lbs']:.0f}",f"{100-total_scm:.0f}% of CM")]
        if flyash_pct>0: rows.append(("Fly ash",f"{p['flyash_lbs']:.0f}",f"{flyash_pct:.0f}%"))
        if slag_pct>0:   rows.append(("Slag",f"{p['slag_lbs']:.0f}",f"{slag_pct:.0f}%"))
        if sf_pct>0:     rows.append(("Silica fume",f"{p['sf_lbs']:.0f}",f"{sf_pct:.0f}%"))
        if pcc_pct>0:    rows.append(("PCC (micro-filler)",f"{p['pcc_lbs']:.0f}",f"{pcc_pct:.0f}%"))
        rows += [("Coarse aggregate (SSD)",f"{p['ca_lbs']:.0f}",f"BV={aci['bv_ca']:.2f}"),
                 ("Fine aggregate (SSD)",f"{p['fa_lbs']:.0f}","abs. volume"),
                 ("Total cementitious",f"{p['total_cm_lbs']:.0f}","")]
        st.dataframe(pd.DataFrame(rows,columns=["Material","lbs/CY","Notes"]), use_container_width=True, hide_index=True)

        for f in aci["flags"]:
            if f["status"]=="ok":       st.success(f["flag"])
            elif f["status"]=="warning": st.warning(f["flag"])
            else:                        st.error(f["flag"])

        ca,cb,cc2 = st.columns(3)
        with ca:
            st.markdown("**SCM & PCC notes**")
            for n in result.scm_notes: st.markdown(f"- {n}")
        with cb:
            st.markdown("**ACI 211.1 compliance**")
            for n in result.aci_compliance: st.markdown(f"- {n}")
        with cc2:
            st.markdown("**QC tests**")
            for t in result.qc_tests: st.markdown(f"- {t}")

        if result.recommendations:
            st.markdown("**Recommendations**")
            st.markdown(result.recommendations)

        # Actions
        st.markdown("<hr style='border:none;border-top:1px solid #E0E7F5;margin:16px 0;'>", unsafe_allow_html=True)
        a1,a2,a3,a4 = st.columns(4)
        with a1:
            save_name = st.text_input("Save as:", placeholder="e.g. Mix A")
        with a2:
            st.write(""); st.write("")
            if st.button("💾 Save", use_container_width=True):
                if save_name:
                    st.session_state.saved_mixes[save_name] = {
                        "fc_psi":fc_psi,"ft_idx":["F0 — protected","F1 — limited moisture","F2 — moisture exposed","F3 — deicers"].index(ft_class),
                        "w_idx":["W0 — protected","W1 — low permeability required"].index(water_class),
                        "s_idx":["S0 — protected","S1 — moderate","S2 — severe","S3 — very severe"].index(sulfate_class),
                        "c_idx":["C0 — protected","C2 — deicers / seawater"].index(chloride_class),
                        "air_entrained":air_entrained,"agg_idx":["3/8","1/2","3/4","1","1-1/2","2"].index(agg_size),
                        "slump_idx":["1-2","3-4","6-7"].index(slump),"shape_idx":list(SHAPE_WATER_REDUCTION.keys()).index(agg_shape),
                        "fm_fa":fm_fa,"sg_ca":sg_ca,"sg_fa":sg_fa,"rodded":rodded_density,
                        "flyash_pct":flyash_pct,"slag_pct":slag_pct,"sf_pct":sf_pct,"pcc_pct":pcc_pct,
                        "sg_flyash":sg_flyash,"sg_slag":sg_slag,"sg_sf":sg_sf,"sg_pcc":sg_pcc,
                        "wcm_ov":wcm_override or 0.45,"mix_label":mix_label or save_name,
                        "field_notes":field_notes,"proj_name":proj_name,"location":location,
                        "prepared_by":prepared_by,"company":company,
                        "cement_prod":cement_prod,"flyash_prod":flyash_prod,
                        "slag_prod":slag_prod,"sf_prod":sf_prod,"pcc_prod":pcc_prod,
                    }
                    st.success(f"Saved as **{save_name}**"); st.rerun()
                else:
                    st.warning("Enter a name first.")
        with a3:
            st.write(""); st.write("")
            if st.button("📊 Add to compare", use_container_width=True):
                label = mix_label or f"Mix {len(st.session_state.comparison_mixes)+1}"
                st.session_state.comparison_mixes.append((label, aci, inp))
                st.success(f"Added **{label}**")
        with a4:
            pdf_bytes = generate_pdf_report(result)
            st.write(""); st.write("")
            st.download_button("📄 PDF report", pdf_bytes,
                f"mix_{proj_name.replace(' ','_') or 'design'}.pdf","application/pdf", use_container_width=True)

        # Gamma card
        st.markdown("""
        <div class="gamma-card">
          <div class="gamma-logo">γ</div>
          <div style="flex:1;">
            <div class="gamma-title">Generate slides or concept map with Gamma</div>
            <div class="gamma-sub">Turn your mix design results into a presentation or visual map for class or your thesis</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Connect Gamma in the sidebar to enable this feature.")


# ─────────────────────────────────────────────────────────────────────────────
# MODE: COMPARE
# ─────────────────────────────────────────────────────────────────────────────
elif mode == "compare":
    st.subheader("📊 Mix design comparison")
    mixes = st.session_state.get("comparison_mixes",[])
    if not mixes:
        st.info("No mixes yet. Go to **Design a mix**, run an analysis, then click **Add to compare**.")
        st.stop()

    params = ["Required f'c (psi)","Exposure codes","Max agg size","Slump (in)",
              "w/cm","Air content (%)","Density (pcf)","Volume (ft³/CY)",
              "Water (lbs/CY)","Portland cement (lbs/CY)","Fly ash (lbs/CY)",
              "Slag (lbs/CY)","Silica fume (lbs/CY)","PCC (lbs/CY)",
              "Coarse agg (lbs/CY)","Fine agg (lbs/CY)","Total CM (lbs/CY)"]
    data = {"Parameter": params}
    for label,aci,inp in mixes:
        p = aci["proportions"]
        data[label] = [f"{inp.fc_psi:,}",", ".join(inp.exposure_codes),f'{inp.agg_size}"',f'{inp.slump}"',
                       str(aci["selected_wcm"]),f"{aci['air_pct']}%",str(aci["density_pcf"]),
                       str(aci["volumes_ft3"]["total"]),str(p["water_lbs"]),str(p["cement_lbs"]),
                       str(p["flyash_lbs"]),str(p["slag_lbs"]),str(p["sf_lbs"]),str(p["pcc_lbs"]),
                       str(p["ca_lbs"]),str(p["fa_lbs"]),str(p["total_cm_lbs"])]

    st.dataframe(pd.DataFrame(data).set_index("Parameter"), use_container_width=True)

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button("📥 Download Excel",make_excel(mixes),
            "mix_comparison.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
    with dl2:
        st.download_button("📥 Download CSV",
            pd.DataFrame(data).set_index("Parameter").to_csv().encode(),
            "mix_comparison.csv","text/csv", use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# MODE: REVIEW
# ─────────────────────────────────────────────────────────────────────────────
elif mode == "review":
    st.subheader("📄 Review an existing mix design")
    st.caption("Upload a PDF report, mix design sheet, or photo. Claude will extract values and check ACI compliance.")

    with st.expander("📋 Project information (optional)"):
        ri1,ri2 = st.columns(2)
        with ri1:
            proj_name   = st.text_input("Project name", placeholder="e.g. RC4")
            location    = st.text_input("Location", placeholder="e.g. Brookings, SD")
        with ri2:
            prepared_by = st.text_input("Prepared by")
            company     = st.text_input("Organization")

    uploaded = st.file_uploader("Upload mix design file",
                                type=["pdf","png","jpg","jpeg","webp"])
    review_notes = st.text_area("Additional context (optional)",
                                placeholder="e.g. Bridge deck, F2 exposure — check w/cm compliance.",
                                height=70)

    if uploaded and st.button("Review Mix Design", use_container_width=True, type="primary"):
        with st.spinner("Analyzing..."):
            file_bytes = uploaded.read()
            file_b64   = base64.b64encode(file_bytes).decode()
            is_pdf     = uploaded.type == "application/pdf"

            if demo_mode:
                review_text = ("**Demo mode** — Turn off Demo Mode and add your API key to get Claude "
                               "to read and review the actual values in your document.\n\n"
                               "In live mode Claude extracts: w/cm, cement/SCM content, water, "
                               "aggregate properties, admixtures, target strength, and performs "
                               "full ACI 318 compliance checks.")
            else:
                PROMPT = f"""You are a concrete materials engineer. Read this mix design document carefully.

## Mix Design Summary
Extract all key values: w/cm, cement, SCM types and %, water, aggregates, admixtures, density, target strength, mix ID, date.

## ACI 318 Compliance Check
PASS / WARN / FAIL for each: w/cm vs exposure class, min cementitious content, air content.

## Observed Materials
List all materials with quantities from the document.

## Durability Flags
List concerns based on what you see.

## Recommended QC Tests
List appropriate ASTM tests for this mix.

## Summary & Recommendations
2–3 sentences of practical guidance.

Context: {review_notes or 'None'}
Be specific — use actual numbers from the document."""

                client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY",""))
                content_msg = [
                    {"type":"document","source":{"type":"base64","media_type":"application/pdf","data":file_b64}}
                    if is_pdf else
                    {"type":"image","source":{"type":"base64","media_type":uploaded.type,"data":file_b64}},
                    {"type":"text","text":PROMPT}
                ]
                msg = client.messages.create(model="claude-opus-4-5", max_tokens=2000,
                                             messages=[{"role":"user","content":content_msg}])
                review_text = msg.content[0].text

        st.markdown(review_text)

        pi = ProjectInfo(project_name=proj_name, location=location, prepared_by=prepared_by, company=company)
        dummy_inp = MixDesignInput(fc_psi=0, exposure_codes=["—"], agg_size="—", slump="—",
            fm_fa=0, sg_ca=0, sg_fa=0, rodded_density_ca=0, agg_shape="—",
            field_notes=review_notes, project_info=pi, uploaded_file_name=uploaded.name)
        dummy_aci = {
            "design_fc_psi":0,"selected_wcm":0,"air_pct":0,"density_pcf":0,"bv_ca":0,
            "proportions":{k:0 for k in ["water_lbs","cement_lbs","flyash_lbs","slag_lbs","sf_lbs","pcc_lbs","ca_lbs","fa_lbs","total_cm_lbs"]},
            "volumes_ft3":{k:0 for k in ["water","cement","flyash","slag","sf","pcc","ca","fa","air","total"]},
            "flags":[{"flag":"See review findings above.","status":"ok"}],
        }
        rev_result = MixDesignResult(input_summary=dummy_inp, aci_result=dummy_aci,
            risk_level="Review", ai_analysis="Document reviewed.",
            recommendations=review_text, file_review_notes=review_text)
        pdf_bytes = generate_pdf_report(rev_result)
        st.divider()
        st.download_button("📄 Download Review Report (PDF)", pdf_bytes,
                           f"review_{uploaded.name}.pdf","application/pdf", use_container_width=True)
