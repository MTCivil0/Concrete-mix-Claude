"""
reporting.py — Professional PDF report | Teymouri Research Lab | SDSU
SDSU Colors: Blue #0033A0 | Yellow #FFB71B
"""
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from src.schemas import MixDesignResult

# ── SDSU Brand Colors ─────────────────────────────────────────────────────────
SDSU_BLUE       = colors.HexColor("#0033A0")
SDSU_BLUE_DARK  = colors.HexColor("#002080")
SDSU_BLUE_LIGHT = colors.HexColor("#E6EBF5")
SDSU_YELLOW     = colors.HexColor("#FFB71B")
SDSU_YELLOW_LT  = colors.HexColor("#FFF6DC")
GREEN_OK        = colors.HexColor("#1B5E20")
GREEN_OK_LT     = colors.HexColor("#E8F5E9")
AMBER           = colors.HexColor("#854F0B")
AMBER_LT        = colors.HexColor("#FFF8E1")
RED_ERR         = colors.HexColor("#B71C1C")
RED_ERR_LT      = colors.HexColor("#FFEBEE")
GRAY_DARK       = colors.HexColor("#212121")
GRAY_MID        = colors.HexColor("#616161")
GRAY_LIGHT      = colors.HexColor("#F5F5F5")
GRAY_LINE       = colors.HexColor("#BDBDBD")
WHITE           = colors.white

def PS(name, size, font="Helvetica", color=None, leading=None, **kw):
    return ParagraphStyle(name, fontSize=size, fontName=font,
                          textColor=color or GRAY_DARK,
                          leading=leading or size*1.4, **kw)

def _val(v): return v if v and v.strip() else "Not provided"


def _header_table(W):
    """Full-width SDSU header: blue left band + yellow accent line."""
    top = Table([[
        Paragraph("TEYMOURI RESEARCH LAB",
                  PS("trl", 10, "Helvetica-Bold", WHITE, leading=13)),
        Paragraph("Dept. of Construction &amp; Concrete Industry Management &nbsp;|&nbsp; "
                  "Jerome J. Lohr College of Engineering &nbsp;|&nbsp; South Dakota State University",
                  PS("trsub", 7.5, color=colors.HexColor("#B3C3E8"), leading=11)),
    ]], colWidths=[2.1*inch, 4.9*inch])
    top.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), SDSU_BLUE),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
        ("LINEAFTER",(0,0),(0,0),3,SDSU_YELLOW),
    ]))
    accent = Table([[""]], colWidths=[W])
    accent.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),SDSU_YELLOW),
        ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    return [top, accent]


def _section(title):
    t = Table([[Paragraph(title, PS("sh",9,"Helvetica-Bold",WHITE))]], colWidths=[7.0*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),SDSU_BLUE),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),10),
    ]))
    return t


def _kv_table(rows, widths):
    """Key-value table with alternating rows."""
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("TEXTCOLOR",(0,0),(-1,-1),GRAY_DARK),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHITE, GRAY_LIGHT]),
        ("GRID",(0,0),(-1,-1),0.5,GRAY_LINE),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    return t


def _data_table(rows, col_widths, header_span=None):
    """Standard data table with SDSU blue header."""
    t = Table(rows, colWidths=col_widths)
    styles = [
        ("BACKGROUND",(0,0),(-1,0),SDSU_BLUE),
        ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,GRAY_LIGHT]),
        ("GRID",(0,0),(-1,-1),0.5,GRAY_LINE),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("TEXTCOLOR",(0,1),(-1,-1),GRAY_DARK),
    ]
    t.setStyle(TableStyle(styles))
    return t


def generate_pdf_report(result: MixDesignResult) -> bytes:
    buf = BytesIO()
    W = 7.0 * inch
    inp = result.input_summary
    pi  = inp.project_info
    aci = result.aci_result
    p   = aci["proportions"]
    v   = aci["volumes_ft3"]
    total_scm = inp.flyash_pct + inp.slag_pct + inp.sf_pct + inp.pcc_pct
    is_review = bool(inp.uploaded_file_name)

    doc = SimpleDocTemplate(buf, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.6*inch, bottomMargin=0.6*inch,
        title="Concrete Mix Design Report — Teymouri Research Lab | SDSU")

    story = []

    # ── SDSU Header ───────────────────────────────────────────────────────────
    story += _header_table(W)
    story.append(Spacer(1,10))

    # ── Report title row ──────────────────────────────────────────────────────
    title_txt = "Mix Design Review Report" if is_review else "Concrete Mix Design Report"
    title_row = Table([[
        Paragraph(title_txt, PS("rt",18,"Helvetica-Bold",SDSU_BLUE,leading=22)),
        Table([[
            Paragraph("Date", PS("dl",7.5,color=GRAY_MID,leading=10)),
            Paragraph("Method",PS("ml",7.5,color=GRAY_MID,leading=10)),
        ],[
            Paragraph(date.today().strftime("%B %d, %Y"), PS("dv",8.5,"Helvetica-Bold",GRAY_DARK,leading=12)),
            Paragraph("ACI 211.1 (PCA)" if not is_review else "Document Review",
                      PS("mv",8.5,"Helvetica-Bold",GRAY_DARK,leading=12)),
        ]], colWidths=[1.5*inch,1.5*inch]),
    ]], colWidths=[4.0*inch,3.0*inch])
    title_row.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("ALIGN",(1,0),(1,0),"RIGHT"),
        ("LINEBELOW",(0,0),(-1,0),2,SDSU_YELLOW),
        ("BOTTOMPADDING",(0,0),(-1,0),8),
    ]))
    story += [title_row, Spacer(1,10)]

    # ── Demo notice ───────────────────────────────────────────────────────────
    demo_t = Table([[
        Paragraph("★  DEMO — Developed by Teymouri Research Lab at SDSU · For research and educational purposes only",
                  PS("dn",8,"Helvetica-Bold",SDSU_BLUE,leading=12))
    ]], colWidths=[W])
    demo_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),SDSU_YELLOW_LT),
        ("LINEBELOW",(0,0),(-1,-1),1.5,SDSU_YELLOW),
        ("LINEBEFORE",(0,0),(0,-1),4,SDSU_YELLOW),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),12),
    ]))
    story += [demo_t, Spacer(1,10)]

    # ── Project info ──────────────────────────────────────────────────────────
    story.append(_section("Project Information"))
    story.append(Spacer(1,2))
    proj_rows = [
        ["Project name", _val(pi.project_name), "Location", _val(pi.location)],
        ["Prepared by",  _val(pi.prepared_by),  "Organization", _val(pi.company)],
    ]
    if inp.uploaded_file_name:
        proj_rows.append(["Uploaded file", inp.uploaded_file_name, "", ""])
    story.append(_kv_table(proj_rows, [1.4*inch,2.2*inch,1.2*inch,2.2*inch]))
    story.append(Spacer(1,10))

    # ══════════════════════════════════════════════════════════════════════════
    # REVIEW MODE — show only review findings, skip mix design tables
    # ══════════════════════════════════════════════════════════════════════════
    if is_review and result.file_review_notes:
        story.append(_section("AI Mix Design Review Findings"))
        story.append(Spacer(1,4))

        # Parse the review text into paragraphs
        review_lines = result.file_review_notes.strip().split("\n")
        for line in review_lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1,4))
                continue
            # Detect markdown-style bold headers
            if line.startswith("**") and line.endswith("**"):
                story.append(Paragraph(line.replace("**",""),
                             PS("rh",10,"Helvetica-Bold",SDSU_BLUE,leading=14,spaceBefore=8)))
            elif line.startswith("- ") or line.startswith("* "):
                story.append(Paragraph("•  " + line[2:],
                             PS("rb",8.5,color=GRAY_DARK,leading=13,leftIndent=12)))
            elif line.startswith("#"):
                txt = line.lstrip("#").strip()
                story.append(Paragraph(txt, PS("rh2",10,"Helvetica-Bold",SDSU_BLUE,leading=14,spaceBefore=6)))
            else:
                story.append(Paragraph(line, PS("rp",8.5,color=GRAY_DARK,leading=13)))

        story.append(Spacer(1,12))

    # ══════════════════════════════════════════════════════════════════════════
    # DESIGN MODE — full mix design report
    # ══════════════════════════════════════════════════════════════════════════
    else:
        # ── Risk banner ───────────────────────────────────────────────────────
        risk_map = {
            "Low":      (GREEN_OK_LT, GREEN_OK, "▲ LOW RISK"),
            "Moderate": (AMBER_LT,    AMBER,    "▲ MODERATE RISK"),
            "High":     (RED_ERR_LT,  RED_ERR,  "▲ HIGH RISK"),
        }
        bg, fg, label = risk_map.get(result.risk_level, (AMBER_LT, AMBER, "▲ MODERATE RISK"))
        rb = Table([[
            Paragraph(label, PS("rl",10,"Helvetica-Bold",fg,leading=14)),
            Paragraph(result.ai_analysis or "",
                      PS("rs",8.5,color=fg,leading=13)),
        ]], colWidths=[1.4*inch,5.6*inch])
        rb.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),bg),
            ("LINEBEFORE",(0,0),(0,-1),4,fg),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),10),
            ("GRID",(0,0),(-1,-1),0.5,GRAY_LINE),
        ]))
        story += [rb, Spacer(1,10)]

        # ── Metric cards ──────────────────────────────────────────────────────
        labels = ["Design f'c","w/cm","Air content","Density","Volume/CY"]
        values = [f"{aci['design_fc_psi']:,} psi", f"{aci['selected_wcm']:.2f}",
                  f"{aci['air_pct']}%", f"{aci['density_pcf']} pcf",
                  f"{v['total']:.2f} ft\xb3"]
        mt = Table(
            [[Paragraph(l, PS("ml",7.5,color=GRAY_MID,leading=11)) for l in labels],
             [Paragraph(f"<b>{val}</b>", PS("mv",13,"Helvetica-Bold",SDSU_BLUE,leading=17)) for val in values]],
            colWidths=[W/5]*5)
        mt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),SDSU_BLUE_LIGHT),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LINEBELOW",(0,0),(-1,0),0.5,GRAY_LINE),
            ("LINEBEFORE",(1,0),(-1,-1),0.5,GRAY_LINE),
            ("LINEABOVE",(0,0),(-1,0),2,SDSU_YELLOW),
            ("LINEBELOW",(0,-1),(-1,-1),2,SDSU_YELLOW),
        ]))
        story += [mt, Spacer(1,10)]

        # ── Inputs + SCMs side by side ─────────────────────────────────────────
        story.append(_section("Mix Design Inputs"))
        story.append(Spacer(1,3))
        left = [["Parameter","Value"],
                ["Required f'c", f"{inp.fc_psi:,} psi"],
                ["Exposure classes", ", ".join(inp.exposure_codes)],
                ["Max aggregate size", f'{inp.agg_size}"'],
                ["Target slump", f'{inp.slump}"'],
                ["Fineness modulus (FA)", f"{inp.fm_fa:.2f}"],
                ["SG coarse / fine agg", f"{inp.sg_ca:.2f} / {inp.sg_fa:.2f}"],
                ["Rodded density (CA)", f"{inp.rodded_density_ca:.0f} lbs/ft\xb3"],
                ["Aggregate shape", inp.agg_shape],
                ["Air entrained", "Yes" if inp.air_entrained else "No"]]
        right= [["SCM","Replacement"],
                ["Portland cement", f"{100-total_scm:.0f}%"],
                ["Fly ash", f"{inp.flyash_pct:.0f}%"],
                ["Slag", f"{inp.slag_pct:.0f}%"],
                ["Silica fume", f"{inp.sf_pct:.0f}%"],
                ["PCC (micro-filler)", f"{inp.pcc_pct:.0f}%"],
                ["Total SCM", f"{total_scm:.0f}%"]]

        lt = _data_table(left,  [2.0*inch,1.55*inch])
        rt = _data_table(right, [1.5*inch,1.45*inch])
        two = Table([[lt, Spacer(0.2*inch,1), rt]], colWidths=[3.55*inch,0.2*inch,2.95*inch])
        two.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
        story += [two, Spacer(1,10)]

        # ── Material producers ─────────────────────────────────────────────────
        story.append(_section("Material Producers"))
        story.append(Spacer(1,3))
        prod_rows = [["Material","Producer / Source"],
                     ["Portland cement", _val(pi.cement_producer)],
                     ["Fly ash",     _val(pi.flyash_producer) if inp.flyash_pct>0 else "N/A"],
                     ["Slag",        _val(pi.slag_producer)   if inp.slag_pct>0   else "N/A"],
                     ["Silica fume", _val(pi.sf_producer)     if inp.sf_pct>0     else "N/A"],
                     ["PCC",         _val(pi.pcc_producer)    if inp.pcc_pct>0    else "N/A"]]
        story.append(_data_table(prod_rows, [2.0*inch,5.0*inch]))
        story.append(Spacer(1,10))

        # ── Proportions ────────────────────────────────────────────────────────
        story.append(_section("Mix Proportions per Cubic Yard"))
        story.append(Spacer(1,3))
        total_mass = sum([p[k] for k in ['water_lbs','cement_lbs','flyash_lbs','slag_lbs','sf_lbs','pcc_lbs','ca_lbs','fa_lbs']])
        pr = [["Material","lbs/CY","ft\xb3/CY","Notes"],
              ["Water",f"{p['water_lbs']:.0f}",f"{v['water']:.3f}",f"w/cm = {aci['selected_wcm']:.2f}"],
              ["Portland cement",f"{p['cement_lbs']:.0f}",f"{v['cement']:.3f}",f"{100-total_scm:.0f}% of CM"]]
        if inp.flyash_pct>0: pr.append(["Fly ash",f"{p['flyash_lbs']:.0f}",f"{v['flyash']:.3f}",f"{inp.flyash_pct:.0f}% replacement"])
        if inp.slag_pct>0:   pr.append(["Slag",f"{p['slag_lbs']:.0f}",f"{v['slag']:.3f}",f"{inp.slag_pct:.0f}% replacement"])
        if inp.sf_pct>0:     pr.append(["Silica fume",f"{p['sf_lbs']:.0f}",f"{v['sf']:.3f}",f"{inp.sf_pct:.0f}% replacement"])
        if inp.pcc_pct>0:    pr.append(["PCC (inert micro-filler)",f"{p['pcc_lbs']:.0f}",f"{v['pcc']:.3f}",f"{inp.pcc_pct:.0f}% — packing effect"])
        pr += [["Coarse aggregate (SSD)",f"{p['ca_lbs']:.0f}",f"{v['ca']:.3f}",f"BV of CA = {aci['bv_ca']:.2f}"],
               ["Fine aggregate (SSD)",f"{p['fa_lbs']:.0f}",f"{v['fa']:.3f}","Absolute volume method"],
               ["Air","—",f"{v['air']:.3f}",f"{aci['air_pct']}%"],
               ["TOTAL",f"{total_mass:.0f}",f"{v['total']:.3f}",""]]
        pt = _data_table(pr, [2.4*inch,0.9*inch,0.9*inch,2.8*inch])
        # Bold last row
        pt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),SDSU_BLUE),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
            ("BACKGROUND",(0,-1),(-1,-1),SDSU_BLUE_LIGHT),
            ("FONTSIZE",(0,0),(-1,-1),8.5),
            ("ROWBACKGROUNDS",(0,1),(-1,-2),[WHITE,GRAY_LIGHT]),
            ("GRID",(0,0),(-1,-1),0.5,GRAY_LINE),
            ("ALIGN",(1,0),(2,-1),"RIGHT"),
            ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("LEFTPADDING",(0,0),(-1,-1),8),
            ("TEXTCOLOR",(0,1),(-1,-2),GRAY_DARK),
        ]))
        story += [pt, Spacer(1,10)]

        # ── Durability flags ───────────────────────────────────────────────────
        story.append(_section("Durability Flags"))
        story.append(Spacer(1,3))
        flag_rows = [["Status","Flag"]]
        for f in aci["flags"]:
            flag_rows.append(["OK" if f["status"]=="ok" else ("WARN" if f["status"]=="warning" else "CRIT"), f["flag"]])
        ft = Table(flag_rows, colWidths=[0.75*inch,6.25*inch])
        fstyles = [
            ("BACKGROUND",(0,0),(-1,0),SDSU_BLUE),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),8.5),
            ("GRID",(0,0),(-1,-1),0.5,GRAY_LINE),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8),
        ]
        for i,f in enumerate(aci["flags"],start=1):
            bg_c = GREEN_OK_LT if f["status"]=="ok" else (AMBER_LT if f["status"]=="warning" else RED_ERR_LT)
            fg_c = GREEN_OK   if f["status"]=="ok" else (AMBER     if f["status"]=="warning" else RED_ERR)
            fstyles += [("BACKGROUND",(0,i),(-1,i),bg_c),
                        ("TEXTCOLOR",(0,i),(0,i),fg_c),("TEXTCOLOR",(1,i),(1,i),GRAY_DARK)]
        ft.setStyle(TableStyle(fstyles))
        story += [ft, Spacer(1,10)]

        # ── SCM notes / Compliance / QC ────────────────────────────────────────
        def list_tbl(title, items):
            rows = [[title]] + [[f"•  {i}"] for i in (items or ["None"])]
            t = Table(rows, colWidths=[W])
            t.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),SDSU_BLUE),("TEXTCOLOR",(0,0),(-1,0),WHITE),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1),8.5),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,GRAY_LIGHT]),
                ("GRID",(0,0),(-1,-1),0.5,GRAY_LINE),
                ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",(0,0),(-1,-1),10),
                ("TEXTCOLOR",(0,1),(-1,-1),GRAY_DARK),
            ]))
            return t

        for sec_title, items in [
            ("SCM & PCC Compatibility Notes", result.scm_notes),
            ("ACI 211.1 Compliance Notes",    result.aci_compliance),
            ("Recommended QC Tests",          result.qc_tests),
        ]:
            story.append(_section(sec_title))
            story.append(Spacer(1,3))
            story.append(list_tbl(sec_title, items))
            story.append(Spacer(1,8))

        # ── Recommendations ────────────────────────────────────────────────────
        if result.recommendations:
            story.append(_section("Recommendations"))
            story.append(Spacer(1,3))
            rt = Table([[result.recommendations]], colWidths=[W])
            rt.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,-1),SDSU_YELLOW_LT),
                ("LINEBEFORE",(0,0),(0,-1),4,SDSU_YELLOW),
                ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
                ("LEFTPADDING",(0,0),(-1,-1),12),("GRID",(0,0),(-1,-1),0.5,GRAY_LINE),
                ("FONTSIZE",(0,0),(-1,-1),8.5),("TEXTCOLOR",(0,0),(-1,-1),GRAY_DARK)]))
            story += [rt, Spacer(1,8)]

        if inp.field_notes:
            story.append(_section("Field Notes"))
            story.append(Spacer(1,3))
            story.append(Paragraph(inp.field_notes, PS("fn",8.5,color=GRAY_DARK,leading=13)))
            story.append(Spacer(1,8))

    # ── Footer ────────────────────────────────────────────────────────────────
    story += [
        Spacer(1,8),
        HRFlowable(width=W, thickness=2, color=SDSU_YELLOW),
        Spacer(1,4),
        Paragraph(
            "Teymouri Research Lab · Dept. of Construction &amp; Concrete Industry Management · "
            "Jerome J. Lohr College of Engineering · South Dakota State University (SDSU) · Brookings, SD. "
            "This tool provides AI-assisted preliminary mix design guidance based on ACI 211.1. "
            "Not a substitute for a licensed structural engineer or certified concrete technologist.",
            PS("ft",7,"Helvetica-Oblique",GRAY_MID,leading=10)),
    ]

    doc.build(story)
    return buf.getvalue()
