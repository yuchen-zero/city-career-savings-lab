# -*- coding: utf-8 -*-
"""Build the full research report as DOCX."""

import json
import os

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))

FONT = "微软雅黑"
BLACK = RGBColor(0, 0, 0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
HEADER_FILL = "1F3864"
ALT_FILL = "F2F5FA"
BORDER = "D9D9D9"

TBLPR_ORDER = ["w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual",
               "w:tblStyleRowBandSize", "w:tblStyleColBandSize", "w:tblW", "w:jc",
               "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd", "w:tblLayout",
               "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription"]
TRPR_ORDER = ["w:cnfStyle", "w:divId", "w:gridBefore", "w:gridAfter", "w:wBefore",
              "w:wAfter", "w:cantSplit", "w:trHeight", "w:tblHeader", "w:tblCellSpacing",
              "w:jc", "w:hidden"]
TCPR_ORDER = ["w:cnfStyle", "w:tcW", "w:gridSpan", "w:hMerge", "w:vMerge", "w:tcBorders",
              "w:shd", "w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText",
              "w:vAlign", "w:hideMark"]


def reorder(element, order):
    index = {qn(n): i for i, n in enumerate(order)}
    for child in sorted(list(element), key=lambda c: index.get(c.tag, len(order))):
        element.append(child)


def style_run(run, size=10.5, bold=False, color=BLACK):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = FONT
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), FONT)
    return run


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)
    reorder(tcPr, TCPR_ORDER)


def add_table(doc, header, rows, widths, alt=True):
    table = doc.add_table(rows=1 + len(rows), cols=len(header))
    table.autofit = False
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for tag in ("w:top", "w:left", "w:bottom", "w:right", "w:insideH", "w:insideV"):
        el = OxmlElement(tag)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), BORDER)
        borders.append(el)
    tblPr.append(borders)
    mar = OxmlElement("w:tblCellMar")
    for tag, val in (("w:top", 90), ("w:start", 120), ("w:bottom", 90), ("w:end", 120)):
        el = OxmlElement(tag)
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    reorder(tblPr, TBLPR_ORDER)

    hrow = table.rows[0]
    trPr = hrow._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:cantSplit"))
    head = OxmlElement("w:tblHeader")
    trPr.append(head)
    reorder(trPr, TRPR_ORDER)
    for i, text in enumerate(header):
        cell = hrow.cells[i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        shade(cell, HEADER_FILL)
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_after = Pt(0)
        style_run(para.add_run(str(text)), size=9.5, bold=True, color=WHITE)

    for r, data_row in enumerate(rows):
        row_obj = table.rows[r + 1]
        row_trPr = row_obj._tr.get_or_add_trPr()
        row_trPr.append(OxmlElement("w:cantSplit"))
        reorder(row_trPr, TRPR_ORDER)
        cells = row_obj.cells
        for i, value in enumerate(data_row):
            cell = cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if alt and r % 2:
                shade(cell, ALT_FILL)
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT if i > 0 else WD_ALIGN_PARAGRAPH.LEFT
            style_run(para.add_run(str(value)), size=9.5)
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = width
    return table


def heading(doc, text, space_before=16):
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.keep_with_next = True
    style_run(p.add_run(text), size=13.5, bold=True)
    return p


def body(doc, text, size=10.5, space_after=7, bold=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.34
    style_run(p.add_run(text), size=size, bold=bold)
    return p


def build():
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.2

    for name, size in (("Title", 20), ("Heading 1", 13.5)):
        st = doc.styles[name]
        st.font.name = FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = BLACK
        rPr = st.element.get_or_add_rPr()
        rFonts = rPr.find(qn("w:rFonts")) or OxmlElement("w:rFonts")
        if rFonts.getparent() is None:
            rPr.insert(0, rFonts)
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rFonts.set(qn(attr), FONT)
        pPr = st.element.get_or_add_pPr()
        for b in pPr.findall(qn("w:pBdr")):
            pPr.remove(b)

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    sec.left_margin = sec.right_margin = Cm(2.0)
    sec.footer_distance = Cm(1.2)

    title = doc.add_paragraph(style="Title")
    title.paragraph_format.space_after = Pt(8)
    for b in title._p.get_or_add_pPr().findall(qn("w:pBdr")):
        title._p.get_or_add_pPr().remove(b)
    style_run(title.add_run("江浙沪电气与自动化应届生就业城市调研报告"), size=20, bold=True)

    body(doc,
         "本报告回答一个具体问题：电气工程及其自动化专业本科应届生，在江浙沪 25 座城市中，"
         "哪一座城市扣除房租、餐饮、通勤和税费之后，每月能剩下的钱最多。"
         "报告覆盖招聘薪资、官方统计数据、住房成本、日常开支和岗位工作条件五个方面，"
         "所有数据标注来源与证据等级，采集截止 2026 年 9 月 15 日。",
         size=10.5, space_after=4)
    body(doc, "数据规模：6197 条招聘岗位、141 条职位描述全文、25 城官方统计数据、"
              "25 城房租与 66 个区县房租、25 城餐饮与通勤成本。", size=10, space_after=14)

    heading(doc, "一、主要结论", space_before=8)
    body(doc, "第一条，上海的绝对净结余最高，但优势有限。上海应届生岗位月薪中位数 10,000 元，"
              "扣除五险一金、个税、合租、餐饮、通勤和水电气宽带后，每月净结余 4,601 元"
              "（含可提取的公积金）。苏州为 4,505 元，两者相差 96 元，仅占月薪的 1%。", space_after=6)
    body(doc, "第二条，苏州在两个维度上优于上海：房租占收入比为 10.8%，上海为 23.4%；"
              "岗位工作条件上，苏州电气岗位中标注「不需要出差」的数量多于上海。"
              "若按整租一居计算，苏州净结余反超上海。", space_after=6)
    body(doc, "第三条，同一城市内部不同区的差距大于城市之间的差距。"
              "上海浦东新区净结余 7,776 元，普陀区仅 1,021 元，相差 7.6 倍；"
              "南京雨花台区 5,147 元，玄武区 1,790 元。选对区比选对城市更重要。", space_after=6)
    body(doc, "第四条，岗位工作条件上存在结构性取舍。硬件、电源、电气设计、测试类岗位"
              "几乎不标注出差要求，但基本不提供住宿；设备工程师岗位 51% 标注需要出差，"
              "31% 提供住宿。想要「不出差」应优先选择硬件与电气设计方向。", space_after=6)
    body(doc, "第五条，也是决定性的：合租与整租会得到完全不同的城市排序。"
              "按合租计算，上海净结余 4,601 元居首；按整租一居计算，上海房租 4,776 元、"
              "房租占收入 47.8%，净结余降到 2,091 元并跌出前五名，苏州以 3,683 元升至第一。"
              "这个差异直接对应选择，需先确定租房方式再看排名。", space_after=12)

    heading(doc, "二、调研方法与数据来源")
    body(doc, "数据分三级标注。A 级为官方发布数据，含各市统计局、人社局、公积金中心与交通部门的公开文件；"
              "B 级为平台发布的商业数据，含招聘平台与房产数据平台；C 级为个体样本，本报告未使用。"
              "所有金额类指标在城市之间采用同一计算口径。", space_after=8)
    add_table(
        doc,
        ["数据模块", "来源", "覆盖范围", "等级"],
        [
            ["招聘薪资", "BOSS 直聘", "6197 条岗位，25 城", "B"],
            ["官方工资", "各市统计局工资统计公报", "11 城", "A"],
            ["居民收入与消费", "台州统计年鉴转载各市统计局", "25 城，2024 年", "A"],
            ["最新年度居民收入", "各市统计局统计公报", "14 城，2025 年", "A"],
            ["房租（城市级）", "中国房价行情网", "25 城，全国 323 城统一口径", "B"],
            ["房租（区县级）", "中国房价行情网", "12 城 66 个区县", "B"],
            ["合租价格", "中国房价行情网 合租排行", "上海、杭州、南京、温州 实测", "B"],
            ["餐饮成本", "统计年鉴食品烟酒分项", "13 城官方分项 + 12 城推算", "A/B"],
            ["工作条件标签", "BOSS 直聘结构化标签", "6197 条岗位", "B"],
            ["社保与个税", "各市人社局、公积金中心", "全省适用", "A"],
            ["通勤票价", "各市地铁与公交计价规则", "25 城", "A"],
        ],
        [Cm(3.6), Cm(6.4), Cm(5.4), Cm(1.6)],
    )

    heading(doc, "三、薪资水平")
    body(doc, "招聘市场数据来自 BOSS 直聘，筛选条件为「应届生」加「本科」，"
              "共 6197 条岗位。官方工资数据来自各市统计局的《单位就业人员年平均工资统计公报》。"
              "两组数据相互印证：杭州私营单位年平均工资 95,545 元，折合月薪 7,962 元，"
              "与招聘平台杭州应届生岗位薪资下限中位数 8,000 元高度一致。", space_after=8)
    add_table(
        doc,
        ["城市", "应届生月薪中位数", "私营单位年均工资", "非私营单位年均工资"],
        [
            ["上海", "10,000", "—", "—"],
            ["杭州", "8,000", "95,545", "168,604"],
            ["南京", "8,000", "—", "—"],
            ["苏州", "8,000", "—", "—"],
            ["常州", "7,000", "—", "—"],
            ["绍兴", "7,000", "—", "120,683"],
            ["宁波", "7,000", "—", "—"],
            ["无锡", "6,500", "82,880", "144,752"],
            ["镇江", "6,000", "—", "118,451"],
            ["盐城", "6,000", "72,757", "108,299"],
        ],
        [Cm(3.0), Cm(4.6), Cm(4.8), Cm(4.6)],
    )
    body(doc, "说明：招聘薪资为招聘广告标注的税前区间下限，官方工资为全行业平均，"
              "两者口径不同，不宜直接比较绝对值，仅用于交叉验证量级。", size=9, space_after=12)

    heading(doc, "四、居住成本")
    body(doc, "城市级房租来自中国房价行情网，为近三个月挂牌均价，单位元每平方米每月，"
              "全国 323 个城市采用统一口径。合租单间价格使用「等效面积法」估算："
              "以四个有实测合租价的城市反推换算系数，取中位数 25.8 平方米。"
              "该模型回测误差为：上海 +5.7%、杭州 -5.1%、南京 +9.3%，温州为异常值（-44.5%）需使用实测值。",
         space_after=8)
    add_table(
        doc,
        ["城市", "租金单价（元/㎡/月）", "全国排名", "合租单间（估算）", "整租一居（估算）"],
        [
            ["上海", "95.52", "2", "2,335（实测）", "4,776"],
            ["杭州", "54.47", "5", "1,484（实测）", "2,724"],
            ["南京", "45.36", "6", "1,073（实测）", "2,268"],
            ["宁波", "31.56", "15", "814", "1,578"],
            ["苏州", "31.39", "17", "810", "1,570"],
            ["无锡", "25.49", "29", "658", "1,274"],
            ["常州", "22.60", "47", "583", "1,130"],
            ["扬州", "21.20", "64", "547", "1,060"],
            ["徐州", "15.59", "172", "402", "780"],
            ["宿迁", "13.39", "265", "345", "670"],
        ],
        [Cm(2.6), Cm(4.4), Cm(2.4), Cm(4.0), Cm(3.6)],
    )
    body(doc, "区县级数据覆盖 12 个城市 66 个区县。以上海为例，黄浦区 153.21 元/㎡/月，"
              "宝山区 77.74，两者相差一倍；南京建邺区 56.51，高淳区 14.65，相差近三倍。"
              "城市平均租金无法反映这种内部差异。", space_after=12)

    heading(doc, "五、日常开支")
    body(doc, "餐饮成本以官方统计的「食品烟酒支出」为基线。台州统计年鉴的分项数据显示"
              "食品烟酒占人均消费支出 28.1%，据此推算各城市餐饮支出，再按单身青年"
              "在外饮食比例较高的特点上浮 25%。各城市差异显著：杭州 1,629 元，上海 1,605 元，"
              "而宿迁仅 694 元，最高与最低相差 935 元。", space_after=8)
    add_table(
        doc,
        ["项目", "计算方式", "典型数值"],
        [
            ["社保个人缴纳", "税前月薪 × 10.5%（养老 8% + 医疗 2% + 失业 0.5%）", "8,000 元月薪对应 840 元"],
            ["公积金个人缴纳", "税前月薪 × 8%（各市区间 5%–12%）", "8,000 元月薪对应 640 元"],
            ["个人所得税", "七级超额累进，起征点 5,000 元", "8,000 元月薪对应 46 元"],
            ["现金到手", "税前月薪 − 社保 − 公积金 − 个税", "8,000 元月薪对应 6,474 元，到手率 80.9%"],
            ["通勤", "地铁或公交单程票价 × 2 × 工作日", "上海 176 元，苏州 132 元，无地铁城市 88 元"],
        ],
        [Cm(3.2), Cm(8.8), Cm(5.0)],
    )
    body(doc, "需要注意，公积金是个人账户资金，可提取用于支付房租，"
              "因此报告同时给出「现金净结余」与「含公积金净结余」两个口径。", space_after=8)
    body(doc, "水电气与宽带按省级居民阶梯价格与单人月用量估算。居民用水、用气、用电执行政府定价，"
              "省内基本统一，因此城市之间差异很小。需要留意合租常为「合表」计价，"
              "上海合表电价为 0.637 元每度，高于一户一表第一档的 0.617 元；"
              "部分长租公寓使用商水商电，电价可达 1 元以上，会使实际支出明显高于本报告的估算。",
         space_after=8)
    add_table(
        doc,
        ["地区", "合租分摊（元/月）", "整租自付（元/月）", "单价构成"],
        [
            ["上海", "128", "197", "电 0.637 元/度（合表） 水 3.45 元/吨 气 3.00 元/立方"],
            ["江苏 13 市", "115", "177", "电 0.5283 元/度 水 3.00 元/吨 气 2.72 元/立方"],
            ["浙江 11 市", "118", "182", "电 0.538 元/度 水 3.00 元/吨 气 3.00 元/立方"],
        ],
        [Cm(2.2), Cm(2.8), Cm(2.8), Cm(8.8)],
    )
    body(doc, "用量假设：合租按人头分摊，月用电 90 度、用水 2.5 吨、用气 9 立方米、宽带分摊 35 元；"
              "整租全部自付，月用电 140 度、用水 3.5 吨、用气 12 立方米、宽带 60 元。",
         size=9, space_after=8)
    body(doc, "租房渠道还会带来额外支出，且三种渠道互斥：房东直租没有渠道费；"
              "通过中介租普通房源需一次性支付约 1 个月房租的中介费，本报告按 12 个月摊薄；"
              "品牌公寓按月收取约房租 10% 的服务费（自如公开报价区间 8% 至 12%）。"
              "中介费与房租挂钩，因此房租越贵的城市，渠道成本越高。", space_after=8)
    add_table(
        doc,
        ["城市", "房租", "中介费摊销（元/月）", "品牌公寓服务费（元/月）", "首月现金（押一付三加中介）"],
        [
            ["上海", "2,335", "195", "234", "10,118"],
            ["杭州", "1,484", "124", "148", "6,432"],
            ["南京", "1,073", "89", "107", "4,650"],
            ["苏州", "810", "67", "81", "3,509"],
            ["常州", "583", "49", "58", "2,527"],
            ["连云港", "441", "37", "44", "1,912"],
        ],
        [Cm(2.2), Cm(2.2), Cm(3.6), Cm(4.2), Cm(4.4)],
    )
    body(doc, "首月现金是刚毕业时最容易被低估的一项。押一付三意味着入住时要付 1 个月押金加 3 个月房租，"
              "若通过中介还需另付 1 个月房租作为中介费。上海一次性需要 10,118 元，是连云港的 5.3 倍。",
         space_after=12)

    heading(doc, "六、岗位工作条件")
    body(doc, "工作条件数据来自 BOSS 直聘的结构化标签字段，覆盖 6197 条岗位。"
              "在全部电气相关岗位中，「不需要出差」标签出现 392 次，「需要出差」481 次，"
              "「周末双休」92 次。标签的存在与否反映的是雇主是否主动披露，"
              "未标注不代表没有该条件。", space_after=8)
    add_table(
        doc,
        ["岗位族", "岗位数", "标注需要出差", "标注不需要出差", "说明"],
        [
            ["硬件类", "114", "0", "0", "非该岗位特征，通常不标注"],
            ["电气设计", "57", "0", "0", "同上"],
            ["测试类", "36", "0", "0", "同上"],
            ["电源类", "11", "0", "0", "同上"],
            ["设备工程师", "50", "27（54%）", "22（44%）", "核心工作条件，98% 有标注"],
        ],
        [Cm(2.6), Cm(1.8), Cm(3.0), Cm(3.4), Cm(6.2)],
    )
    body(doc, "进一步交叉筛选发现，「免房租」与「不需要出差」两个条件同时满足的岗位共 12 个，"
              "集中在设备工程师岗位族，企业多为制造业工厂，包括比亚迪、扬子江药业、"
              "龙腾光电、友达光电、蜂巢汽车集团等。", space_after=12)

    heading(doc, "七、净结余与城市排序")
    body(doc, "净结余按「含公积金」口径计算，即现金到手加上可提取的公积金，"
              "扣除房租、餐饮与通勤。月薪取招聘平台应届生档薪资下限的中位数。"
              "房租分两种口径分别计算：合租单间按等效面积 25.8 平方米换算"
              "（上海、杭州、南京、温州使用实测合租价），整租一居按建筑面积 50 平方米换算。",
         space_after=8)

    body(doc, "口径一：合租单间", size=10, space_after=5, bold=True)
    body(doc, "下表按房东直租计算，未含中介费或品牌公寓服务费。", size=9, space_after=4)
    rows = []
    for x in DATA["cities"]:
        rows.append([
            x["城市"], f"{int(x['税前月薪']):,}", f"{int(x['合租月租']):,}",
            f"{int(x['通勤']):,}", f"{int(x['餐饮']):,}",
            f"{int(x['净结余_含公积金'] - x['合租分摊']):,}",
            f"{int(x['净结余_含公积金'] - x['合租分摊'] - x['合租月租'] / 12):,}",
            f"{int((x['合租月租'] + x['合租月租'] / 12) * 4):,}",
        ])
    rows.sort(key=lambda r: -int(r[5].replace(",", "")))
    add_table(
        doc,
        ["城市", "税前月薪", "合租", "通勤", "餐饮", "净结余（直租）", "净结余（中介）", "首月现金"],
        rows[:10],
        [Cm(1.8), Cm(2.2), Cm(1.8), Cm(1.6), Cm(1.8), Cm(2.8), Cm(2.8), Cm(2.4)],
    )

    unit_of = {x["城市"]: x["租金元每平米每月"] for x in DATA["cities"]}
    util_of = {x["城市"]: x["整租自付"] for x in DATA["cities"]}
    share_of = {x["城市"]: x["合租分摊"] for x in DATA["cities"]}
    whole_rows = []
    for x in DATA["cities"]:
        unit = unit_of[x["城市"]]
        whole = unit * 50
        net = (x["净结余_含公积金"] - share_of[x["城市"]]
               - whole + x["合租月租"] - util_of[x["城市"]])
        whole_rows.append([
            x["城市"], f"{unit:.2f}", f"{int(whole):,}",
            f"{(whole / x['税前月薪'] * 100):.1f}%", f"{int(net):,}", int(net),
        ])
    whole_rows.sort(key=lambda r: -r[5])
    body(doc, "口径二：整租一居（建筑面积 50 平方米）", size=10, space_after=5, bold=True)
    add_table(
        doc,
        ["城市", "租金单价（元/㎡/月）", "整租一居月租", "房租占收入", "净结余（扣水电气后）"],
        [r[:5] for r in whole_rows[:10]],
        [Cm(2.4), Cm(4.2), Cm(3.4), Cm(2.8), Cm(3.8)],
    )
    body(doc, "两种口径的完整 25 城数据见随附 Excel 总表与可视化页面。",
         size=9, space_after=12)

    heading(doc, "八、区级对比与推荐")
    body(doc, "将区级房租与岗位所在区匹配后，得到区级净结余。以下为岗位数量不少于 3 个、"
              "且有区级房租数据的区。", space_after=8)
    add_table(
        doc,
        ["城市", "区", "电气岗位数", "月薪中位数", "合租", "净结余"],
        [
            ["上海", "浦东新区", "17", "15,000", "2,503", "7,776"],
            ["镇江", "京口区", "5", "10,000", "456", "6,345"],
            ["杭州", "滨江区", "14", "11,000", "1,666", "5,373"],
            ["南京", "雨花台区", "9", "10,000", "1,256", "5,147"],
            ["上海", "徐汇区", "6", "11,500", "3,162", "4,303"],
            ["南京", "栖霞区", "3", "8,000", "1,054", "3,741"],
            ["杭州", "余杭区", "8", "8,000", "1,232", "3,395"],
            ["绍兴", "越城区", "8", "7,000", "666", "3,370"],
            ["苏州", "吴中区", "11", "7,000", "881", "3,063"],
            ["上海", "普陀区", "3", "7,000", "2,826", "1,021"],
        ],
        [Cm(2.0), Cm(2.8), Cm(2.6), Cm(2.8), Cm(2.2), Cm(2.6)],
    )
    body(doc, "推荐排序基于三个条件：净结余水平、岗位工作条件是否符合「不需要出差」，"
              "以及可选岗位的数量。综合下来，上海浦东新区与杭州滨江区在净结余和岗位数量上"
              "表现最好；苏州在房租压力与工作条件上更均衡；镇江京口区净结余高但岗位数仅 5 个，"
              "且由英科医疗一家企业主导，统计上较脆弱。", space_after=12)

    heading(doc, "九、数据局限")
    body(doc, "第一，招聘薪资为税前广告值，实际到手受五险一金基数与比例影响，"
              "报告中的换算基于统一比例假设，各城市公积金实际缴存比例在 5% 至 12% 之间浮动。", space_after=6)
    body(doc, "第二，合租价格仅上海、杭州、南京、温州四城为实测值，其余 21 城为模型推算，"
              "回测显示偏差可达 ±10%，个别城市可能出现更大偏差。", space_after=6)
    body(doc, "第三，餐饮成本由官方「食品烟酒支出」推算，该口径覆盖全体居民，"
              "与单身青年在外饮食的实际支出一致性有限。", space_after=6)
    body(doc, "第四，区级房租仅覆盖 12 个城市 66 个区县，占电气岗位总数的 80%，"
              "其余城市的区级数据因数据源限流未能采集。", space_after=6)
    body(doc, "第五，工作条件标签由招聘方自行填写，未标注不等于不存在，"
              "出差、加班等条件仍需在面试环节确认。", space_after=6)
    body(doc, "第六，岗位数据为 2026 年 9 月快照，招聘岗位流动性高，"
              "建议在使用时重新核对岗位是否仍在招聘。", space_after=12)

    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(footer.add_run("江浙沪电气与自动化应届生就业城市调研报告 · 数据截止 2026-09-15"), size=8.5)

    props = doc.core_properties
    props.title = "江浙沪电气与自动化应届生就业城市调研报告"
    props.author = "Codex"
    return doc


if __name__ == "__main__":
    out = os.path.join(HERE, "outputs", "01a09ac1-e853-7671-a83f-cea3e7f16019")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "江浙沪电气应届生就业城市调研报告.docx")
    build().save(path)
    print("已生成", path)
