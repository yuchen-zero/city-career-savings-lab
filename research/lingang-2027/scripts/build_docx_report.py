#!/usr/bin/env python3
"""Build the final Word report from the versioned research payload."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
ASSETS = OUTPUT / "_report_assets"
REPORT = OUTPUT / "2027届_电气工程及其自动化_临港_城市净结余报告_2026-10-26.docx"

PAYLOAD = json.loads((DATA / "analysis_payload.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((DATA / "build_manifest.json").read_text(encoding="utf-8"))

FONT = "等线"
FONT_BOLD = "等线"
BLACK = "000000"
NAVY = "17365D"
TEAL = "1F6C75"
GOLD = "A87821"
WHITE = "FFFFFF"
PALE = "EAF1F7"
PALE2 = "F5F8FA"
GRAY = "D9D9D9"
DARK_GRAY = "4C4C4C"


def money(value: float | int | None) -> str:
    if value is None:
        return "未取得"
    return f"{value:,.0f} 元"


def money1(value: float | int | None) -> str:
    if value is None:
        return "未取得"
    return f"{value:,.1f} 元"


def pct(value: float | int | None) -> str:
    if value is None:
        return "未取得"
    return f"{value * 100:.1f}%"


def shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top: int = 90, start: int = 110, bottom: int = 90, end: int = 110) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color: str = GRAY, size: int = 4) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), str(size))
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), color)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def style_run(run, size: float = 10.5, bold: bool = False, color: str = BLACK, italic: bool = False) -> None:
    run.font.name = FONT_BOLD if bold else FONT
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT_BOLD if bold else FONT)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def add_hyperlink(paragraph, url: str, text: str, size: float = 8.5) -> None:
    part = paragraph.part
    rel_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    new_run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1F4E78")
    r_pr.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_pr.append(underline)
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:eastAsia"), FONT)
    r_pr.append(fonts)
    size_el = OxmlElement("w:sz")
    size_el.set(qn("w:val"), str(int(size * 2)))
    r_pr.append(size_el)
    new_run.append(r_pr)
    text_el = OxmlElement("w:t")
    text_el.text = text
    new_run.append(text_el)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def add_page_number(paragraph) -> None:
    run = paragraph.add_run("第 ")
    style_run(run, 8.5, color=DARK_GRAY)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, placeholder, end])
    run2 = paragraph.add_run(" 页")
    style_run(run2, 8.5, color=DARK_GRAY)


def set_keep_with_next(paragraph, enabled: bool = True) -> None:
    paragraph.paragraph_format.keep_with_next = enabled


def body(doc: Document, text: str, bold_lead: str | None = None, space_after: float = 5) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.25
    if bold_lead and text.startswith(bold_lead):
        first = p.add_run(bold_lead)
        style_run(first, 10.5, bold=True)
        rest = p.add_run(text[len(bold_lead):])
        style_run(rest, 10.5)
    else:
        r = p.add_run(text)
        style_run(r, 10.5)


def bullet(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.12)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    style_run(r, 10.2)


def label(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    style_run(r, 9, bold=True, color=DARK_GRAY)
    set_keep_with_next(p)


def add_table(
    doc: Document,
    headers: Sequence[str],
    rows: Iterable[Sequence[object]],
    widths: Sequence[float] | None = None,
    font_size: float = 8.3,
    header_fill: str = NAVY,
    alignments: Sequence[str] | None = None,
) -> None:
    rows = list(rows)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    header = table.rows[0]
    set_repeat_table_header(header)
    prevent_row_split(header)
    for idx, text in enumerate(headers):
        cell = header.cells[idx]
        shade(cell, header_fill)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(str(text))
        style_run(r, font_size, bold=True, color=WHITE)
        if widths:
            cell.width = Inches(widths[idx])
    for row_index, values in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        for idx, value in enumerate(values):
            cell = row.cells[idx]
            if row_index % 2 == 1:
                shade(cell, PALE2)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            if alignments and idx < len(alignments):
                p.alignment = {
                    "left": WD_ALIGN_PARAGRAPH.LEFT,
                    "center": WD_ALIGN_PARAGRAPH.CENTER,
                    "right": WD_ALIGN_PARAGRAPH.RIGHT,
                }[alignments[idx]]
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(str(value))
            style_run(r, font_size)
            if widths:
                cell.width = Inches(widths[idx])
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    section.header_distance = Inches(0.35)
    section.footer_distance = Inches(0.35)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.25

    for name, size in (("Title", 28), ("Subtitle", 13), ("Heading 1", 18), ("Heading 2", 13.5), ("Heading 3", 11.5)):
        style = styles[name]
        style.font.name = FONT_BOLD
        style._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BOLD)
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(10 if name.startswith("Heading") else 0)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True

    title_style = styles["Title"]
    title_p_pr = title_style.element.get_or_add_pPr()
    for border in list(title_p_pr.findall(qn("w:pBdr"))):
        title_p_pr.remove(border)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = header.add_run("2027届电气工程及其自动化本科应届生临港调研")
    style_run(r, 8, color=DARK_GRAY)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_page_number(footer)
    add_page_number_text = footer.add_run(f"  |  {PAYLOAD['meta']['data_version']}")
    style_run(add_page_number_text, 8, color=DARK_GRAY)


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    style_run(r, 18 if level == 1 else 13.5 if level == 2 else 11.5, bold=True)


def make_charts() -> tuple[Path, Path]:
    ASSETS.mkdir(parents=True, exist_ok=True)
    regular = Path("C:/Windows/Fonts/msyh.ttc")
    bold = Path("C:/Windows/Fonts/msyhbd.ttc")
    f_title = ImageFont.truetype(str(bold), 44)
    f_sub = ImageFont.truetype(str(regular), 23)
    f_text = ImageFont.truetype(str(regular), 22)
    f_small = ImageFont.truetype(str(regular), 18)

    salary_path = ASSETS / "salary_net_cash.png"
    img = Image.new("RGB", (1800, 920), "#" + WHITE)
    draw = ImageDraw.Draw(img)
    draw.text((90, 45), "压力测试薪资下的月现金净结余", font=f_title, fill="#111111")
    draw.text((90, 105), "合租直租与整租直租，12薪；薪资为模型输入，不是2027届观测工资", font=f_sub, fill="#555555")
    x0, y0, x1, y1 = 150, 185, 1725, 790
    max_value = 9000
    for tick in range(0, max_value + 1, 1500):
        y = y1 - (tick / max_value) * (y1 - y0)
        draw.line((x0, y, x1, y), fill="#D9E0E5", width=2)
        draw.text((50, y - 13), f"{tick:,.0f}", font=f_small, fill="#555555")
    salaries = [8000, 10000, 12000, 15000]
    share = {}
    whole = {}
    for row in PAYLOAD["scenarios"]:
        if row["annual_months"] == 12:
            if row["scenario"].endswith("合租-直租"):
                share[row["monthly_gross"]] = row["net_cash"]
            if row["scenario"].endswith("整租-直租"):
                whole[row["monthly_gross"]] = row["net_cash"]
    group_width = (x1 - x0) / len(salaries)
    bar_width = 105
    colors = [NAVY, GOLD]
    for i, salary in enumerate(salaries):
        center = x0 + group_width * (i + 0.5)
        for j, values in enumerate((share, whole)):
            value = values[salary]
            height = value / max_value * (y1 - y0)
            left = center - bar_width - 7 if j == 0 else center + 7
            right = left + bar_width
            draw.rounded_rectangle((left, y1 - height, right, y1), radius=7, fill="#" + colors[j])
            label = f"{value:,.0f}"
            box = draw.textbbox((0, 0), label, font=f_small)
            draw.text((left + (bar_width - (box[2] - box[0])) / 2, y1 - height - 30), label, font=f_small, fill="#111111")
        draw.text((center - 58, y1 + 24), f"{salary/1000:.0f}k", font=f_text, fill="#222222")
    draw.rectangle((x0, y1, x1, y1), fill="#333333", width=2)
    draw.rounded_rectangle((1270, 130, 1305, 155), radius=4, fill="#" + NAVY)
    draw.text((1315, 125), "合租直租", font=f_small, fill="#222222")
    draw.rounded_rectangle((1460, 130, 1495, 155), radius=4, fill="#" + GOLD)
    draw.text((1505, 125), "整租直租", font=f_small, fill="#222222")
    draw.text((150, 850), "单位：元/月；未计个人公积金。含公积金净结余另在总表列出。", font=f_small, fill="#555555")
    img.save(salary_path, quality=95)

    cost_path = ASSETS / "cost_composition_10k.png"
    img = Image.new("RGB", (1800, 880), "#" + WHITE)
    draw = ImageDraw.Draw(img)
    draw.text((90, 45), "10,000元压力薪资下的月度现金去向", font=f_title, fill="#111111")
    draw.text((90, 105), "房租、水电燃气网、餐饮、通勤、其他固定支出与剩余现金", font=f_sub, fill="#555555")
    selected = {
        "合租直租": next(r for r in PAYLOAD["scenarios"] if r["scenario"] == "10000元-合租-直租"),
        "整租直租": next(r for r in PAYLOAD["scenarios"] if r["scenario"] == "10000元-整租-直租"),
    }
    categories = [
        ("房租", "rent_monthly", "#17365D"),
        ("水电燃气网", "utilities", "#4B7F9C"),
        ("餐饮", "food_monthly", "#6F9C87"),
        ("通勤", "commute_monthly", "#C6A15B"),
        ("其他固定", "other_fixed_monthly", "#A46B6B"),
        ("净结余", "net_cash", "#DCE6EC"),
    ]
    x0, x1 = 290, 1715
    total = 8200
    for idx, (label_text, row) in enumerate(selected.items()):
        y = 245 + idx * 245
        draw.text((90, y + 38), label_text, font=f_text, fill="#111111")
        x = x0
        for cat, key, color in categories:
            value = row[key]
            width = value / total * (x1 - x0)
            draw.rectangle((x, y, x + width, y + 78), fill=color)
            if width > 95:
                text = f"{value:,.0f}"
                bbox = draw.textbbox((0, 0), text, font=f_small)
                draw.text((x + (width - (bbox[2] - bbox[0])) / 2, y + 26), text, font=f_small, fill="#111111" if color == "#DCE6EC" else "#" + WHITE)
            x += width
        draw.line((x0, y + 91, x1, y + 91), fill="#D9D9D9", width=2)
    legend_x = 180
    for cat, _, color in categories:
        draw.rounded_rectangle((legend_x, 725, legend_x + 28, 753), radius=4, fill=color)
        draw.text((legend_x + 38, 721), cat, font=f_small, fill="#222222")
        legend_x += 235
    draw.text((90, 810), "单位：元/月；采用主情景餐饮2,100元、通勤160元、其他固定300元。", font=f_small, fill="#555555")
    img.save(cost_path, quality=95)
    return salary_path, cost_path


def build_report() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    chart_salary, chart_cost = make_charts()
    doc = Document()
    configure_document(doc)

    scenarios = {row["scenario"]: row for row in PAYLOAD["scenarios"]}
    direct_jobs = [job for job in PAYLOAD["jobs"] if "2027" in job["job_title"] and job["include_in_analysis"] == "yes"]
    market_anchors = [job for job in PAYLOAD["jobs"] if job["include_in_analysis"] == "no" and job["monthly_min"] != ""]
    share_10 = scenarios["10000元-合租-直租"]
    whole_10 = scenarios["10000元-整租-直租"]
    agency_share_10 = scenarios["10000元-合租-中介押一付三"]
    agency_whole_10 = scenarios["10000元-整租-中介押一付三"]
    talent_10 = scenarios["10000元-人才公寓-条件情景"]

    cover_kicker = doc.add_paragraph()
    cover_kicker.paragraph_format.space_before = Inches(0.65)
    cover_kicker.paragraph_format.space_after = Pt(18)
    r = cover_kicker.add_run("应届生城市研究 | 官方规则优先 | 证据分级")
    style_run(r, 9, color=DARK_GRAY)

    title = doc.add_paragraph(style="Title")
    title.paragraph_format.space_after = Pt(14)
    r = title.add_run("2027届电气工程及其自动化本科应届生临港就业与现金测算报告")
    style_run(r, 28, bold=True)

    subtitle = doc.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(26)
    r = subtitle.add_run("上海市浦东新区临港新片区核心区 | 数据截止 2026-10-26")
    style_run(r, 13, color=DARK_GRAY)

    cover_table = doc.add_table(rows=4, cols=2)
    cover_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cover_table.autofit = False
    cover_rows = [
        ("研究对象", "2027届，电气工程及其自动化，本科应届生"),
        ("空间口径", "临港新片区，重点滴水湖与南汇新城核心区"),
        ("薪资口径", "招聘广告税前固定月薪；未观测到本科2027目标岗薪资"),
        ("数据版本", f"{PAYLOAD['meta']['data_version']}  |  SHA-256 {MANIFEST['payload_sha256'][:12]}"),
    ]
    for i, (k, v) in enumerate(cover_rows):
        for idx, value in enumerate((k, v)):
            cell = cover_table.cell(i, idx)
            cell.width = Inches(1.35 if idx == 0 else 4.7)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell, top=110, bottom=110)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            rr = p.add_run(value)
            style_run(rr, 9.5, bold=(idx == 0), color=BLACK if idx == 0 else DARK_GRAY)
            if idx == 0:
                shade(cell, PALE)

    cover_note = doc.add_paragraph()
    cover_note.paragraph_format.space_before = Inches(1.25)
    cover_note.paragraph_format.space_after = Pt(0)
    r = cover_note.add_run("核心判断  ")
    style_run(r, 9, bold=True, color=DARK_GRAY)
    r = cover_note.add_run("目前没有足够的透明样本支持“2027届临港电气本科薪资中位数”。报告以可核验岗位供给、官方税费规则和明确标注的薪资压力测试回答现金与生活成本问题。")
    style_run(r, 9, color=DARK_GRAY)
    doc.add_page_break()

    add_heading(doc, "一 结论摘要", 1)
    body(doc, "本报告支持选域和预算判断，但不支持看似精确的应届生工资中位数。核心区共核验到6条2027届本科相邻岗位，来自3家企业；中芯国际占4条、66.7%。6条均未公开薪资，也没有一条同时明确双休和不出差。")
    body(doc, "按先前口径，双休与不出差作为硬条件单列；现场调试和工程实施可接受。若双休或不出差必须由招聘页面直接证明，当前合格样本为0条。若这些条件允许在面试或offer阶段核实，岗位供给仍可作为持续投递池，但不能据此宣称已经满足条件。")
    body(doc, "现金测算采用8,000、10,000、12,000和15,000元税前固定月薪，属于压力测试而非观测值。主情景按2026年上海社保基数、10.5%个人社保、7%个人公积金、6万元年度基本减除和1,500元住房租金专项扣除计算。")

    label(doc, "表 1  核心样本与硬条件计数")
    add_table(
        doc,
        ["指标", "结果", "直接含义"],
        [
            ("2027本科相邻岗位", f"{len(direct_jobs)} 条 / {PAYLOAD['headline']['direct_2027_employer_n']} 家企业", "样本小于30条，仅作观察，不能做强排名"),
            ("公开薪资岗位", f"{PAYLOAD['headline']['explicit_salary_n']} 条", "无法计算2027目标岗广告薪资中位数或四分位"),
            ("明确双休", f"{PAYLOAD['headline']['double_weekend_explicit_n']} 条", "未标注不等于无双休，但也不能当作满足硬条件"),
            ("明确不出差", f"{PAYLOAD['headline']['no_trip_explicit_n']} 条", "未标注不等于必须出差，同样需要面试核验"),
            ("薪资+双休+不出差同时明确", f"{PAYLOAD['headline']['hard_qualified_n']} 条", "当前无法宣称任何岗位已通过硬筛选"),
            ("最大企业占比", pct(4 / len(direct_jobs)), "中芯国际4条，企业集中度高"),
        ],
        widths=[1.9, 1.4, 3.4],
        font_size=8.5,
        alignments=["left", "center", "left"],
    )

    label(doc, "表 2  2027届固定月税前薪资压力测试")
    salary_rows = []
    for gross in (8000, 10000, 12000, 15000):
        s = scenarios[f"{gross}元-合租-直租"]
        w = scenarios[f"{gross}元-整租-直租"]
        salary_rows.append((money(gross), money1(s["monthly_cash_override"]), money1(s["net_cash"]), money1(w["net_cash"]), pct(s["rent_burden_pct"]), pct(w["rent_burden_pct"])))
    add_table(
        doc,
        ["税前月薪", "月均到手现金", "合租直租净结余", "整租直租净结余", "合租房租/税前", "整租房租/税前"],
        salary_rows,
        widths=[1.15, 1.35, 1.35, 1.35, 0.85, 0.85],
        font_size=8.3,
        alignments=["right", "right", "right", "right", "center", "center"],
    )
    body(doc, "Word、Excel和交互页统一采用10,000元、12薪、合租中介押一付三、月租1,300元的现金压力测试作为默认情景。扣税社保和公积金后月均现金收入为8,197.5元；月度纯现金净结余为4,153.7元，含个人公积金为4,853.7元；首月最低现金8,360.9元，加2,000元应急缓冲后建议储备10,360.9元。房租占税前工资13.0%。")
    bullet(doc, "成本优先的可执行线：若改为合租直租、月租约1,200元，10,000元税前收入的月纯现金结余约4,291.6元；首月最低现金约5,105.9元，建议储备7,105.9元。")
    bullet(doc, "风险边界：独立整租直租2,200元时，月纯现金结余降至3,229.3元；不能仅凭月度净结余判断，还要同时预留押付和签约渠道费。")
    bullet(doc, "硬条件线：在没有书面offer或招聘页面明确确认前，不把任何当前岗位视为“双休且不出差”的合格岗位。")

    add_heading(doc, "二 研究范围与用户约束", 1)
    body(doc, "决策问题是：2027届电气工程及其自动化本科应届生在临港核心区，面对尚未公开的目标岗薪资，需要怎样的税前工资、租房方式和现金储备，才能获得可持续的月净结余和首月承受能力？")
    body(doc, "“临港心片区”不是公开的标准行政名称。本报告按“临港新片区，重点滴水湖与南汇新城核心区”操作。泥城、书院等更广范围单独标注；积塔半导体云水路厂区因位于泥城镇且无法证明属于滴水湖核心区，只作为范围外观察，不进入6条核心岗位计数。")
    body(doc, "本报告把双休、出差、住宿、现场调试和工程实施分开记录。页面写“未知”时保留为未知：不能推断为双休，也不能推断为必须出差。薪资只把广告中的固定月薪或可识别月区间用于市场观察；“面议”和未列薪资留空。")

    add_heading(doc, "三 数据质量与计算口径", 1)
    body(doc, "证据分级按数字对本问题的可信度，而不是按网站名气。官方社保、税务和公用事业价格规则为A级；有原始页面和采集日期的大样本招聘或租房平台可到B级；少于30条岗位、少于10条租房、单一企业主导或模型估算为C级；单条个人晒薪和无法回溯的转述仅作D级线索。")
    label(doc, "表 3  本报告证据使用规则")
    add_table(
        doc,
        ["等级", "本报告中的用途", "本轮实际覆盖"],
        [
            ("A", "制度价格、税费社保、官方住房项目规则", "社保、公积金、个税、水电气、交通票价、人才公寓条件"),
            ("B", "足够大的平台招聘或租房样本", "未取得可直接进入主模型的B级大样本"),
            ("C", "小样本岗位、挂牌价、市场观察、模型估算", "6条核心岗位、单条或少量历史租赁挂牌、生活成本篮子"),
            ("D", "失败采集记录或无法回溯的线索", "BOSS登录态失效记录；不用于任何薪资或成本主值"),
        ],
        widths=[0.55, 2.65, 3.55],
        font_size=8.5,
        alignments=["center", "left", "left"],
    )
    body(doc, "月税后现金按年度综合所得近似：年度税前收入减去全年个人社保、全年个人公积金、60,000元基本减除和18,000元住房租金专项扣除，再套用居民综合所得七级超额累进税率，最后除以12。社保缴费基数按固定税前月薪并受2026年上下限约束；13薪或16薪只增加年度税前收入，社保和公积金仍按12个月固定月薪计缴。")
    body(doc, "月度现金净结余等于月均到手现金，减房租、中介费按12个月摊销、月度服务费、水电气网、餐饮、通勤和其他固定支出。含公积金净结余再加回个人公积金月缴额。首月最低现金等于押金、预付租金、租客承担中介费和一次性服务费，再加首月水电燃气网、月度服务费、餐饮、通勤和其他固定支出。")

    add_heading(doc, "四 岗位供给、薪资与工作条件", 1)
    body(doc, "核心样本只有6条。四家中芯国际岗位覆盖设备、封装设备和自动化算法；另外两条分别来自艾为和延锋彼欧。艾为页面写“电子工程相关”，延锋写“机械、电气自动化等优先”，因此两条都需要在投递或面试时确认电气工程及其自动化专业的正式可投性。")
    label(doc, "表 4  2027届本科相邻岗位与工作条件")
    job_rows = [
        ("中芯国际", "设备工程师", "本科 / 应届", "安装调试、保养、故障排查；双休、出差、住宿未写", "面议"),
        ("中芯国际", "封装设备工程师", "本科 / 应届", "点检、参数校准、故障分析；关键条件未写", "面议"),
        ("中芯国际", "自动化算法工程师", "本科 / 应届", "制造系统、实时派货和数据优化；出差未写", "面议"),
        ("中芯国际", "封装生产运筹工程师", "本科或硕士 / 应届", "明确白班、夜班和轮班，洁净室；不符合双休", "面议"),
        ("艾为电子", "设备工程师", "本科及以上 / 2027", "设备改机、测试异常和硬件改造；专业可投性需确认", "未列"),
        ("延锋彼欧", "工程设备方向", "本科及以上 / 2027", "设备安装、改造、TPM和现场问题处理；出差未写", "未列"),
    ]
    add_table(
        doc,
        ["企业", "岗位", "学历 / 届别", "页面可证工作条件", "薪资"],
        job_rows,
        widths=[1.0, 1.45, 1.15, 3.1, 0.55],
        font_size=8.0,
        alignments=["left", "left", "left", "left", "center"],
    )
    body(doc, "这6条记录全部为C级小样本。没有一条公开可计算的月薪，也没有一条同时明确双休和不出差。生产运筹岗位明确存在轮班，因此即使薪资后续公开，也不能进入双休硬筛选。其余岗位的未知项必须在HR初筛和部门面试中逐条确认。")

    label(doc, "表 5  排除的相邻岗位市场锚点（仅作外部观察）")
    anchor_rows = []
    for job in market_anchors:
        months = int(job["annual_months"]) if job["annual_months"] else 12
        midpoint = (float(job["monthly_min"]) + float(job["monthly_max"])) / 2
        anchor_rows.append((job["job_title"].replace("（临港）", ""), job["salary_text"], f"{midpoint * months / 12:,.0f} 元", job["exclusion_reason"]))
    add_table(
        doc,
        ["岗位", "广告薪资", "年化区间中点", "为何不能当2027本科应届工资"],
        anchor_rows,
        widths=[1.75, 1.05, 1.0, 3.1],
        font_size=7.5,
        alignments=["left", "center", "right", "left"],
    )
    headline = PAYLOAD["headline"]
    body(
        doc,
        f"这{headline['market_anchor_n']}条排除样本的年化区间中点为"
        f"{headline['market_annualized_mid_min']:,.0f}至{headline['market_annualized_mid_max']:,.0f}元/月，"
        f"中位数为{headline['market_annualized_mid_median']:,.1f}元/月，"
        "但其中包含1至3年、3至5年经验岗、硕士岗和条件不同的售后岗。"
        "该中位数只描述这批被排除记录，不能作为2027届本科应届生工资。",
    )

    doc.add_page_break()
    add_heading(doc, "五 官方工资与制度校准", 1)
    body(doc, "上海目前可取得的官方工资类数据是全口径就业人员平均工资和居民收入统计，不是电气工程及其自动化本科应届生招聘工资价位。官方数字用于校验统计口径和制度参数，不能自动替代目标岗位广告值。")
    label(doc, "表 6  官方统计与制度口径")
    add_table(
        doc,
        ["指标", "数值", "统计期 / 用途", "等级"],
        [
            ("上海全口径单位就业人员平均工资", "12,577 元/月", "2025口径，用于2026社保；不是应届薪资", "A"),
            ("全体居民人均可支配收入", "91,987 元/年", "2025年；不是岗位工资", "A"),
            ("全体居民人均消费支出", "54,765 元/年", "2025年；不是单身青年预算", "A"),
            ("城镇常住居民人均消费支出", "57,076 元/年", "2025年；外部背景", "A"),
            ("社保缴费基数", "7,546至37,731 元/月", "2026-07起，个人社保10.5%", "A"),
            ("公积金缴存基数与比例", "2,740至37,731 元/月；5%至7%", "2026年度；主情景7%，敏感性5%", "A"),
            ("基本减除与住房租金扣除", "60,000元/年；1,500元/月", "符合主要工作城市无房、实际租房条件", "A"),
        ],
        widths=[2.05, 1.55, 2.55, 0.45],
        font_size=8.2,
        alignments=["left", "center", "left", "center"],
    )
    body(doc, "官方统计的使用边界很重要。91,987元的年可支配收入覆盖全体居民和不同家庭结构；12,577元是社保口径全口径平均工资。把任一数字直接写成“临港电气本科起薪”都会混淆统计对象、学历、经验和地区层级。", bold_lead="官方统计的使用边界很重要。")


    add_heading(doc, "六 房租、押付与首月现金", 1)
    body(doc, "临港核心区的租房数据明显弱于官方制度数据。当前可复核的整租平台展示价为一室约2,200元/月，但页面没有公开样本量、可比面积和成交属性；具体房源示例集中在2,000至2,300元/月，且发布于2025年。合租单间有1,100元的具体历史挂牌，同时以1,100至1,500元作为观察区间。所有市场价均应标为挂牌或页面展示价，不是成交价。")
    label(doc, "表 7  房租观察与证据边界")
    add_table(
        doc,
        ["类型 / 项目", "月租", "面积或口径", "日期", "等级与用途"],
        [
            ("临港新城整租平台展示", "2,200 元", "一室；样本量不透明", "2026-10-26", "C；主模型整租锚点"),
            ("绿地东岸涟城整租", "2,300 元", "84㎡，2室1厅", "2025-09-01", "C；历史具体挂牌"),
            ("宜浩佳园整租", "2,000 元", "77㎡，1室2厅", "2025-07-10", "C；历史具体挂牌，户型不典型"),
            ("保利蔚蓝林语合租", "1,100 元", "单间、独立卫浴；面积未核实", "2025-06-03", "C；历史具体挂牌"),
            ("临港合租观察区间", "1,100至1,500 元", "单间；样本量不透明", "2026-10-26", "C；主模型取1,200至1,300"),
            ("安居客特殊低价示例", "1,300 元", "1室2厅；面积和稳定性未核", "2026-10-26", "C；不进入典型整租主值"),
            ("官方人才公寓一居", "1,000至1,800 元", "31.27至53.25㎡", "2024-04-12", "A租金、条件性资格；压力值1,500"),
        ],
        widths=[1.65, 1.15, 1.55, 0.85, 1.45],
        font_size=7.7,
        alignments=["left", "right", "left", "center", "left"],
    )
    body(doc, "临港主城区人才公寓的一居室租金为官方项目价，但需要单位清单、上海户籍或居住证积分达标、本科及以上、本人及家庭无房等条件，并受项目清单和空房约束。报告仅把1,500元作为条件情景；如果没有资格或没有房源，不能把人才公寓成本当成默认选项。青年住房补贴只适用于公告所列高水平大学等条件，不进入普通本科主情景。")

    label(doc, "表 8  10,000元压力薪资下的住房方案与首月资金")
    housing_names = ["合租-直租", "合租-中介押一付三", "整租-直租", "整租-中介押一付三", "人才公寓-条件情景"]
    housing_rows = []
    for name in housing_names:
        row = scenarios[f"10000元-{name}"]
        terms = f"{int(row['deposit_months'])}押 / {int(row['advance_rent_months'])}付"
        if row["agency_fee_months"]:
            terms += f" / 中介{row['agency_fee_months']:.2f}月"
        housing_rows.append((name.replace("中介押一付三", "中介").replace("-条件情景", ""), money(row["rent_monthly"]), terms, money1(row["monthly_cash_override"]), money1(row["first_month_min"]), money1(row["first_month_with_2000_buffer"])))
    add_table(
        doc,
        ["住房方案", "月租", "押付与渠道费", "月均到手现金", "首月最低现金", "建议储备"],
        housing_rows,
        widths=[1.55, 0.9, 1.55, 1.15, 1.15, 1.0],
        font_size=7.9,
        alignments=["left", "right", "center", "right", "right", "right"],
    )
    body(doc, "押一付一合租直租的最低首月现金为5,105.9元，建议储备7,105.9元；押一付三且中介费0.35月时，最低首月现金升至8,360.9元，建议储备10,360.9元。整租直租分别为7,168.2元和9,168.2元；整租中介押一付三分别为12,338.2元和14,338.2元。差额主要来自押金、预付租金和中介费，而不是月租金本身。")
    body(doc, "首月现金还可能被搬家、床品、厨具、开卡、押金以外的平台服务费和首月采购抬高。报告只把2,000元作为应急缓冲，不是对所有个人都足够的保证。若家庭承担押付，月度现金流不变，但入职门槛会显著下降。")

    add_heading(doc, "七 生活成本与通勤", 1)
    body(doc, "居住成本之外，餐饮是最大且最容易产生虚假精确的项目。本报告不把偶尔出现的满减价当作长期价格，而用三档月度餐饮篮子做敏感性：1,500元用于食堂、自炊和低价混合；2,100元用于堂食与外卖混合；2,800元用于外卖高频。外卖单餐全包观察约为22至44元，但没有取得连续30天、可复核的完整菜单，因此月度数字标为C级模型。")
    label(doc, "表 9  生活成本主情景与敏感性")
    add_table(
        doc,
        ["项目", "主情景", "敏感性或计算说明", "等级"],
        [
            ("餐饮", "2,100 元/月", "低档1,500；外卖高频2,800；按30天篮子", "C"),
            ("水费", "16.2 元/月", "4.05元/m³ × 4m³，合租按个人分摊", "A单价/C用量"),
            ("电费", "61.7 或 74.0 元/月", "0.617元/kWh × 100或120kWh", "A单价/C用量"),
            ("燃气", "18.0 元/月", "3.00元/m³ × 6m³，按个人分摊", "A单价/C用量"),
            ("网络", "50 或 100 元/月", "合租50元/人；整租100元/户", "C模型"),
            ("通勤", "160 元/月", "公交2元×4次/日×20天；人才公寓情景180元", "C路线假设"),
            ("其他固定", "300 元/月", "手机、清洁、个人用品；不含旅行、医疗、大件", "C模型"),
        ],
        widths=[1.1, 1.2, 3.75, 0.8],
        font_size=8.3,
        alignments=["left", "right", "left", "center"],
    )
    body(doc, "水、电、燃气单价来自2026年上海市民价格信息指南扫描页。公共交通常规公交单一票制2元，地铁按里程计价；本报告不把公交和地铁同时计入一个月，而用4次公交/日作为较保守上限。实际通勤应以具体公司厂址、班车路线和租房小区复核。")

    add_heading(doc, "八 月净结余与敏感性", 1)
    body(doc, "薪资压力测试显示，合租与整租之间的月度现金差约为860至1,060元，取决于薪级和公积金口径。两者不是数百元以内无法区分，而是在本模型中对单身租房者持续有实质影响。该判断在房租超过2,400元或公司提供住宿时会改变。")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(chart_salary), width=Inches(6.6))
    p.paragraph_format.space_after = Pt(2)
    label(doc, "图 1  8k至15k压力薪资下的月现金净结余（元/月）")

    label(doc, "表 10  月税后现金与含公积金结余")
    sensitivity_rows = []
    for gross in (8000, 10000, 12000, 15000):
        s = scenarios[f"{gross}元-合租-直租"]
        w = scenarios[f"{gross}元-整租-直租"]
        sensitivity_rows.append((money(gross), money1(s["monthly_cash_override"]), money1(s["net_cash"]), money1(s["net_with_fund"]), money1(w["net_cash"]), money1(w["net_with_fund"])))
    add_table(
        doc,
        ["税前月薪", "月均到手现金", "合租净结余", "合租含公积金", "整租净结余", "整租含公积金"],
        sensitivity_rows,
        widths=[1.05, 1.2, 1.15, 1.25, 1.15, 1.25],
        font_size=8.1,
        alignments=["right", "right", "right", "right", "right", "right"],
    )

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(chart_cost), width=Inches(5.8))
    p.paragraph_format.space_after = Pt(2)
    label(doc, "图 2  10,000元压力薪资下的月度现金构成（元/月）")

    label(doc, "表 11  10,000元、12薪的餐饮和年发月数敏感性")
    add_table(
        doc,
        ["情景", "合租直租纯现金结余", "整租直租纯现金结余", "解释"],
        [
            ("餐饮1,500元", money1(share_10["net_cash"] + 600), money1(whole_10["net_cash"] + 600), "食堂、自炊和低价混合"),
            ("餐饮2,100元", money1(share_10["net_cash"]), money1(whole_10["net_cash"]), "主情景"),
            ("餐饮2,800元", money1(share_10["net_cash"] - 700), money1(whole_10["net_cash"] - 700), "外卖高频"),
            ("12薪", money1(share_10["net_cash"]), money1(whole_10["net_cash"]), "月均到手8,197.5元"),
            ("13薪", money1(scenarios["10000元-合租-直租-13薪"]["net_cash"]), money1(scenarios["10000元-整租-直租-13薪"]["net_cash"]), "月均到手9,005.8元"),
            ("16薪", money1(scenarios["10000元-合租-直租-16薪"]["net_cash"]), money1(scenarios["10000元-整租-直租-16薪"]["net_cash"]), "月均到手11,285.0元"),
        ],
        widths=[1.2, 1.65, 1.65, 2.35],
        font_size=8.1,
        alignments=["left", "right", "right", "left"],
    )
    body(doc, "公积金5%与7%的敏感性应同时看现金和积累。10,000元税前时，个人公积金从700元降到500元，会提高月现金，但计税和到手变化的综合效应只有约百元级；在本模型下，7%情景的含公积金净结余仍略高。实际企业是否缴补充公积金、是否按固定工资或全薪缴存，必须以工资单和书面offer为准。")

    add_heading(doc, "九 决策建议与核验清单", 1)
    body(doc, "如果以控制首月现金和月固定成本为先，合租直租是最稳妥的模型基准：10,000元税前时，月纯现金净结余约4,292元，首月最低现金约5,106元。押一付三且中介费0.35月会把首月门槛提高到8,361元，因此签约条款的影响可能大于每月多100元房租的影响。")
    body(doc, "如果要求独立整租，建议把10,000元作为最低压力测试线而不是工资预测。该情景月纯现金结余约3,229元，首月最低现金约7,168元；若实际薪资只有8,000元，整租直租净结余约1,629元，任何一次搬家、医疗或大额支出都可能耗尽缓冲。")
    body(doc, "岗位选择上，当前6条核心样本可继续投递和面试，但没有任何一条能通过“明确薪资、双休、不出差”三项硬筛。最关键的下一步不是等待网站标签自动出现，而是在初筛阶段获得可追溯的书面确认；口头说“基本不出差”不能写成不出差。")
    label(doc, "表 12  面试与签约核验清单")
    add_table(
        doc,
        ["核验项", "必须问清并留痕的内容"],
        [
            ("固定与浮动薪资", "税前固定月薪、绩效比例、13/16薪是否保证、发放条件"),
            ("社保公积金", "缴费基数是否为全薪、公积金比例、是否补充公积金"),
            ("工作制度", "标准工时或轮班、每月夜班数、周末值班频率"),
            ("双休", "是否固定周六日休息；轮班制下如何计算双休"),
            ("出差与驻场", "年度出差次数、单次时长、现场调试、紧急到场和值班要求"),
            ("宿舍与补贴", "是否包住、宿舍条件与扣费；住房补贴的资格和发放方式"),
            ("试用期", "工资比例、社保是否正常缴、转正条件"),
            ("通勤", "具体工作地址、班车线路、首末班时间、极端天气方案"),
            ("租房合同", "押付、中介费、月度服务费、一次性服务费、维修责任"),
            ("水电燃气网", "民用或商用价格、是否包含在租金、抄表和分摊方式"),
            ("搬迁与家具", "床品、厨具、网络安装、保洁、家电大修由谁承担"),
            ("人才公寓与补贴", "资格、单位清单、空房、租期、续租和退租规则"),
        ],
        widths=[1.55, 5.0],
        font_size=8.1,
        alignments=["left", "left"],
    )

    add_heading(doc, "十 限制、风险与结论变化条件", 1)
    bullet(doc, "BOSS直聘专用浏览器最终显示登录页，本轮未能取得可用的授权会话；未绕过验证码、未保存Cookie或账号信息。覆盖缺口会降低对整租和岗位条件的交叉验证。")
    bullet(doc, "2027核心岗位只有6条、3家企业，且4条来自同一企业；这是观察样本，不是市场总体。薪资为0条公开值，不能计算中位数、四分位或确定性排名。")
    bullet(doc, "房租平台均价是页面展示，不是成交价；具体房源多为2025年历史挂牌。当前实际可租房、议价、面积、维修和真实费用需要重新核验。")
    bullet(doc, "餐饮、网络、水电用量、通勤和其他固定支出是透明模型，不是个人账单。个人是否能拿人才公寓、青年补贴、公司宿舍或家庭支持，会显著改变首月现金。")
    bullet(doc, "“临港心片区”已按滴湖水湖南汇新城核心区操作，不能把泥城、书院等更广范围的公司自动当作同一边界。具体公司厂址应在地图和班车路线上复核。")
    body(doc, "以下任一条件出现，主要结论应重算：获得2027届本科目标岗的书面固定月薪或13/16薪；岗位明确双休或出差制度与原假设不同；公司提供免费宿舍或稳定住房补贴；实际合租低于1,000元或整租高于2,500元；通勤需要跨区或打车；餐饮和固定支出明显超过2,100元和300元。")

    doc.add_page_break()
    add_heading(doc, "附录一 主要来源与证据", 1)
    evidence_by_key = {row["key"]: row for row in PAYLOAD["evidence"]}
    source_keys = [
        "evi_social_base", "evi_social_rates", "evi_fund_2026", "evi_tax_rent", "evi_tax_rates",
        "evi_price_guide", "evi_stats_2025", "evi_talent_apartment", "evi_anjuke_rent",
        "evi_58_share_listing", "evi_smic_supply", "evi_aiwill_2027", "evi_yanfeng_2027",
    ]
    label(doc, "表 13  关键来源台账摘要")
    source_rows = []
    for key in source_keys:
        item = evidence_by_key.get(key)
        if item:
            source_rows.append((item["source_name"], item["published_at"], item["evidence_level"], item["scope"]))
    add_table(
        doc,
        ["来源", "发布日", "级别", "用于本报告的范围"],
        source_rows,
        widths=[2.45, 0.8, 0.45, 2.9],
        font_size=7.2,
        alignments=["left", "center", "center", "left"],
    )
    body(doc, "下列链接为来源入口。链接可打开不代表平台当前页面仍保持原内容；本报告以数据截止日和本地原始文件为准。")
    for key in source_keys:
        item = evidence_by_key.get(key)
        if not item:
            continue
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.05
        r = p.add_run(f"{item['source_name']}  ")
        style_run(r, 8.2, color=DARK_GRAY)
        add_hyperlink(p, item["url"], item["url"], size=7.3)

    add_heading(doc, "附录二 数据版本与复算入口", 1)
    body(doc, f"数据版本为{PAYLOAD['meta']['data_version']}，截止日为{PAYLOAD['meta']['data_cutoff']}。用作建模的标准化数据保存在项目data目录，交互页使用同一份analysis_payload.json，Excel总表使用同一套税率、基数与住房参数。")
    add_table(
        doc,
        ["文件", "作用", "校验值"],
        [
            ("data/analysis_payload.json", "岗位、房租、生活成本、官方数据与30个测算情景", f"SHA-256 {MANIFEST['payload_sha256']}"),
            ("data/jobs.csv", "14条岗位明细，含6条核心2027样本与8条排除/观察样本", "由同一构建脚本生成"),
            ("data/rent.csv", "9条房租与官方人才公寓观察", "小样本警告保留"),
            ("data/city_model.csv", "30个可复算情景，使用精确月度到手现金覆盖", "租赁期12个月"),
        ],
        widths=[1.35, 3.8, 1.45],
        font_size=7.9,
        alignments=["left", "left", "left"],
    )
    body(doc, "报告没有把模型输入写成观测值，也没有把未知条件写成否定条件。若需要将本流程复用到其他城市，应重新确认当地税费、社保公积金、岗位关键词、押付规则、租金和餐饮篮子。")

    doc.save(REPORT)
    print(REPORT)


if __name__ == "__main__":
    build_report()
