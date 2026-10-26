#!/usr/bin/env python3
"""Build the traceable Lingang research dataset and scenario calculations."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median


PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "data"
OUTPUT = PROJECT / "output"
COLLECTED = "2026-10-26"
CITY = "上海"
DISTRICT = "浦东新区"
AREA = "临港新片区（重点滴水湖/南汇新城核心区）"


def write_csv(name: str, rows: list[dict], columns: list[str]) -> None:
    with (DATA / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


EVIDENCE = [
    {
        "module": "payroll",
        "key": "evi_social_base",
        "source_name": "上海市人力资源和社会保障局：2026年度社保缴费基数",
        "source_type": "government",
        "url": "https://rsj.sh.gov.cn/tgsgg_17341/20260818/t0035_1443203.html",
        "published_at": "2026-08-18",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "上海；2026-07-01起；月缴费基数下限7546元、上限37731元",
        "raw_file": "sources/raw/official/social_base_2026.html",
        "notes": "2025年度全口径城镇单位就业人员平均工资12577元/月。",
    },
    {
        "module": "payroll",
        "key": "evi_social_rates",
        "source_name": "上海市人力资源和社会保障局：员工个人社保缴费比例",
        "source_type": "government",
        "url": "https://rsj.sh.gov.cn/tmsztc_17502/20240416/t0035_1423583.html",
        "published_at": "2024-04-16",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "上海；个人养老8%、医疗2%、失业0.5%，合计10.5%",
        "raw_file": "sources/raw/official/social_employee_20240416.html",
        "notes": "模型按目标月固定税前工资与2026基数上下限取缴费基数。",
    },
    {
        "module": "payroll",
        "key": "evi_fund_2026",
        "source_name": "上海市公积金管理中心：2026年度缴存基数与比例",
        "source_type": "government",
        "url": "https://www.shzfgjj.cn/html/twzl/228488.html",
        "published_at": "2026-08-19",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "上海；2026-07至2027-06；单位和个人主公积金各5%-7%",
        "raw_file": "sources/raw/official/housingfund_notice_2026.html",
        "notes": "主情景7%，5%用于敏感性；补充公积金未计入主情景。",
    },
    {
        "module": "tax",
        "key": "evi_tax_rent",
        "source_name": "国家税务总局上海市税务局：住房租金专项附加扣除",
        "source_type": "government",
        "url": "https://shanghai.chinatax.gov.cn/zcfw/rdwd/202603/t479656.html",
        "published_at": "2026-03-10",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "上海符合条件住房租金专项附加扣除1500元/月",
        "raw_file": "sources/raw/official/tax_rent_faq_2026.html",
        "notes": "要求本人及配偶在主要工作城市无自有住房并实际发生租金；模型假定合格。",
    },
    {
        "module": "tax",
        "key": "evi_tax_rates",
        "source_name": "中国居民综合所得年度税率表",
        "source_type": "government",
        "url": "https://www.chinatax.gov.cn/chinatax/n810341/n810755/c5132044/content.html",
        "published_at": "2018-12-27",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "居民综合所得；年基本减除费用60000元及七级超额累进税率",
        "raw_file": "sources/raw/official/tax_rate_table.html",
        "notes": "年度税额=应纳税所得额×税率-速算扣除数；本报告按年度综合所得近似。",
    },
    {
        "module": "living",
        "key": "evi_price_guide",
        "source_name": "2026年上海市市民价格信息指南（上观新闻转载页及扫描页）",
        "source_type": "official_republished_scan",
        "url": "https://www.shobserver.cn/sgh/detail?id=1695525",
        "published_at": "2026-01-14",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "上海居民水、电、燃气和公共交通价格",
        "raw_file": "sources/raw/official/price_guide_2026_shobserver/page_01.jpg",
        "notes": "价格规则A级；抓取的是官方内容媒体转载扫描页。",
    },
    {
        "module": "official_salary",
        "key": "evi_stats_2025",
        "source_name": "上海市统计局：2025年居民人均可支配收入和消费支出",
        "source_type": "government",
        "url": "https://tjj.sh.gov.cn/ydsj71/20260120/39ae4cd58421478d897b739d83f39c10.html",
        "published_at": "2026-01-20",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "上海2025年全体居民和城镇常住居民人均口径",
        "raw_file": "sources/raw/official/stats_income_expense_2025.html",
        "notes": "只作外部背景，不能替代电气本科应届生招聘工资或单身青年生活成本。",
    },
    {
        "module": "rent",
        "key": "evi_anjuke_rent",
        "source_name": "安居客临港新城租房价格页",
        "source_type": "marketplace_asking_rent",
        "url": "https://m.anjuke.com/sh/rent/",
        "published_at": "2026-10-26",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "临港新城；页面显示一室今日均价2200元/月及少量示例房源",
        "raw_file": "sources/raw/anjuke_mobile_lingang_rent_20261026.html",
        "notes": "挂牌/平台展示价，不是成交价；样本量、面积和发布日期不透明，只作观察。",
    },
    {
        "module": "rent",
        "key": "evi_ke_listing",
        "source_name": "贝壳租房挂牌：绿地东岸涟城",
        "source_type": "marketplace_listing",
        "url": "https://m.ke.com/chuzu/sh/zufang/SH1661736411599994880.html",
        "published_at": "2025-09-01",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "临港；2室1厅84㎡；2300元/月",
        "raw_file": "",
        "notes": "单条历史挂牌，不代表当前可租或成交价。",
    },
    {
        "module": "rent",
        "key": "evi_fang_listing",
        "source_name": "房天下挂牌：宜浩佳园",
        "source_type": "marketplace_listing",
        "url": "https://zu.fang.com/sh/chuzu/8_1016019970_1.htm",
        "published_at": "2025-07-10",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "临港；1室2厅77㎡；2000元/月",
        "raw_file": "",
        "notes": "单条历史挂牌；户型面积较特殊，不能直接视为标准一居。",
    },
    {
        "module": "rent",
        "key": "evi_58_share_listing",
        "source_name": "58同城合租挂牌：保利蔚蓝林语",
        "source_type": "marketplace_listing",
        "url": "https://sh.58.com/hezu/4088587099561999x.shtml",
        "published_at": "2025-06-03",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "临港；合租单间、独立卫浴；1100元/月",
        "raw_file": "sources/raw/58_lingang_20261026.html",
        "notes": "单条历史挂牌；水电、服务费和实际室友人数未完整核实。",
    },
    {
        "module": "rent",
        "key": "evi_talent_apartment",
        "source_name": "临港新片区国际人才港：主城区人才公寓",
        "source_type": "government",
        "url": "https://www.lingang.gov.cn/html/website/lg/rc/hotspot/redianxinwen/p1781237685213462530.html",
        "published_at": "2024-04-12",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "主城区人才公寓；一居31.27-53.25㎡约1000-1800元/月",
        "raw_file": "sources/raw/official/lingang_talent_apartment.html",
        "notes": "租金标准A级；需单位清单、户籍/居住证积分、本科、无房等条件，个人适用需审核。",
    },
    {
        "module": "policy",
        "key": "evi_youth_housing",
        "source_name": "临港新片区国际人才港：新就业青年安居支持政策",
        "source_type": "government",
        "url": "https://www.lingang.gov.cn/html/website/lg/rc/hotspot/redianxinwen/2096770314522361858.html",
        "published_at": "2026-08-29",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "高水平大学毕业生；第一年补贴房租60%、最高1500元/月，第二年退坡",
        "raw_file": "sources/raw/official/lingang_youth_housing_2026.html",
        "notes": "不进入普通本科主情景；仅双一流或世界前500等高水平大学条件情景。",
    },
    {
        "module": "jobs",
        "key": "evi_smic_supply",
        "source_name": "智联招聘校园页：中芯国际临港2027岗位",
        "source_type": "recruitment_platform",
        "url": "https://www.zhaopin.com/zhaopin/77d11caf785b4ee185513c53ec47b291/",
        "published_at": "2026-09-14",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "中芯国际设备、封装设备、自动化算法、封装生产运筹等2027岗位",
        "raw_file": "sources/raw/official/smic_2027_campus_search.html",
        "notes": "岗位存在性和学历/面议状态可核验；页面地址只显示上海，标题注明临港。",
    },
    {
        "module": "jobs",
        "key": "evi_smic_packaging",
        "source_name": "智联招聘：中芯国际封装生产运筹工程师-临港（2027届）",
        "source_type": "recruitment_listing",
        "url": "https://m.zhaopin.com/jobs/CC000439650J40870065707.htm",
        "published_at": "2026",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "临港；本科/硕士；电气、自动化等可投；30人；面议；轮班",
        "raw_file": "sources/raw/official/smic_packaging_2027.html",
        "notes": "明确轮班/洁净室，不符合双休硬条件；不得用于薪资中位数。",
    },
    {
        "module": "jobs",
        "key": "evi_gta_2027",
        "source_name": "上海积塔半导体：2027届校园招聘",
        "source_type": "company_career",
        "url": "https://www.gtasemi.com.cn/careers/campus-recruitment_2",
        "published_at": "2026",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "scope": "设备工程师；本科；机械、自动化、电气工程相关专业；上海自贸区厂区；未列薪资",
        "raw_file": "sources/raw/official/gta_2027_campus_official_page2.html",
        "notes": "云水路600号位于泥城镇，属临港新片区更广范围，未证明位于滴水湖核心区；主表不并入核心区供给。",
    },
    {
        "module": "jobs",
        "key": "evi_aiwill_2027",
        "source_name": "应届生求职网转载前程无忧：艾为设备工程师-临港-2027届",
        "source_type": "campus_job_repost",
        "url": "https://m.yingjiesheng.com/job-008-033-479.html",
        "published_at": "2026-08-20",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "本科及以上；电子工程相关；临港；设备维修、调试与测试平台异常处理；未列薪资",
        "raw_file": "sources/raw/official/aiwill_equipment_2027_yingjiesheng_mobile.html",
        "notes": "未写双休、出差和住宿；电气工程专业能否投递需HR确认。",
    },
    {
        "module": "jobs",
        "key": "evi_yanfeng_2027",
        "source_name": "应届生求职网转载前程无忧：延锋彼欧2027工程设备",
        "source_type": "campus_job_repost",
        "url": "https://m.yingjiesheng.com/job-008-084-813.html",
        "published_at": "2026-09-18",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "临港公司；2027本科及以上；机械、电气自动化等优先；设备安装与改造",
        "raw_file": "sources/raw/official/yanfeng_equipment_2027_yingjiesheng.html",
        "notes": "未列薪资；未明确双休、出差和住宿。",
    },
    {
        "module": "jobs",
        "key": "evi_amec_campus",
        "source_name": "南开大学就业网：中微公司2027登峰计划",
        "source_type": "university_career",
        "url": "https://career.nankai.edu.cn/correcruit/content/id/116861.html",
        "published_at": "2026-08-20",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "2027本科/硕/博，400人；设备研发、公共工程研发、售后服务等；地点含上海",
        "raw_file": "sources/raw/official/amec_2027_nankai.html",
        "notes": "页面层级显示20000元以上，但不是岗位级薪资，不能当作本科应届起薪。",
    },
    {
        "module": "jobs",
        "key": "evi_market_signals",
        "source_name": "智联招聘临港相关岗位原始搜索页",
        "source_type": "recruitment_platform",
        "url": "https://sou.zhaopin.com/?jl=538&kw=临港%20电气",
        "published_at": "2026-10-26",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "40个关键词、1页/词；129张卡片、86个去重职位；仅作市场信号",
        "raw_file": "sources/raw/zhaopin_candidates/normalized_jobs.csv",
        "notes": "含经验岗、外地岗、非目标岗；搜索返回数不等于有效应届样本。",
    },
    {
        "module": "living",
        "key": "evi_food_basket",
        "source_name": "临港快餐平台页与透明餐饮篮子假设",
        "source_type": "marketplace_plus_model",
        "url": "https://sh.58.com/lingangxinc/kuaican/list_25/",
        "published_at": "2026-10-26",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "外卖单餐全包价格约22-44元；月度餐饮三档为1380/2100/2800元模型篮子",
        "raw_file": "sources/raw/search_snippets_food_lingang_2026-10-26.csv",
        "notes": "未取得连续30天可复核菜单；优惠券不假定长期可用，餐饮是模型估算。",
    },
    {
        "module": "living",
        "key": "evi_internet_model",
        "source_name": "上海宽带与家庭网络费用假设",
        "source_type": "model_assumption",
        "url": "https://www.189.cn/sh/",
        "published_at": "2026",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "宽带/移动网络100元/月；合租按每人50元",
        "raw_file": "",
        "notes": "未捕获同周期套餐合同价；仅作保守模型参数，签约前应复核。",
    },
    {
        "module": "rent",
        "key": "evi_agency_fee",
        "source_name": "上海租房中介费与押付公开信息汇总",
        "source_type": "search_result_secondary",
        "url": "https://www.so.com/s?q=上海+租房+中介费+35%25",
        "published_at": "2026-10-26",
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "scope": "模型采用租客承担0.35个月中介费作为协商/常见情景；直租为0",
        "raw_file": "sources/raw/search_snippets_agency_fee_2026-10-26.csv",
        "notes": "中介费并非统一费率；必须按具体合同核验，房东承担时应为0。",
    },
    {
        "module": "jobs",
        "key": "evi_boss_attempt",
        "source_name": "BOSS直聘专用浏览器烟测失败记录",
        "source_type": "collection_limit",
        "url": "https://www.zhipin.com/",
        "published_at": "2026-10-26",
        "collected_at": COLLECTED,
        "evidence_level": "D",
        "scope": "专用浏览器最终显示登录页，未取得可用登录态",
        "raw_file": "sources/raw/boss_smoke/search_page.html",
        "notes": "未绕过登录或验证码，也未导出Cookie、账号或密码。",
    },
]


def job_row(
    job_id: str,
    source: str,
    url: str,
    title: str,
    company: str,
    family: str,
    salary_text: str,
    salary_min: float | None,
    salary_max: float | None,
    months: int | None,
    education: str,
    experience: str,
    weekend: str,
    trip: str,
    accommodation: str,
    include: str,
    exclusion: str,
    notes: str,
    district: str = DISTRICT,
) -> dict:
    return {
        "job_id": job_id,
        "source": source,
        "source_url": url,
        "collected_at": COLLECTED,
        "evidence_level": "C",
        "search_keyword": "临港 2027 电气 自动化 设备",
        "search_page": "1",
        "city": CITY,
        "district": district,
        "company": company,
        "company_id": "",
        "job_title": title,
        "job_family": family,
        "monthly_min": salary_min if salary_min is not None else "",
        "monthly_max": salary_max if salary_max is not None else "",
        "salary_text": salary_text,
        "annual_months": months if months is not None else "",
        "education": education,
        "experience": experience,
        "salary_type": "negotiable" if salary_min is None else "monthly",
        "weekend": weekend,
        "trip_requirement": trip,
        "accommodation": accommodation,
        "include_in_analysis": include,
        "exclusion_reason": exclusion,
        "notes": notes,
    }


JOBS = [
    job_row("zhaopin_CC000439650J40870063007", "智联招聘校招", "https://xiaoyuan.zhaopin.com/job/CC000439650J40870063007", "设备工程师-临港（2027届校招）(J13300)", "中芯国际集成电路制造(上海)有限公司", "设备工程", "面议", None, None, None, "本科", "应届/经验不限", "unknown", "unknown", "unknown", "yes", "", "设备安装调试、预防保养和故障排查；薪资、双休、出差均未公开。"),
    job_row("zhaopin_CC000439650J40870063207", "智联招聘校招", "https://xiaoyuan.zhaopin.com/job/CC000439650J40870063207", "封装设备工程师-临港（2027届校招）(J13308)", "中芯国际集成电路制造(上海)有限公司", "封装设备", "面议", None, None, None, "本科", "应届/经验不限", "unknown", "unknown", "unknown", "yes", "", "设备点检、参数校准、故障分析；面向传感器信号和气液路系统；关键条件未公开。"),
    job_row("zhaopin_CC000439650J40881561407", "智联招聘校招", "https://xiaoyuan.zhaopin.com/job/CC000439650J40881561407", "自动化算法工程师-临港（2027届校招）(J13774)", "中芯国际集成电路制造(上海)有限公司", "自动化算法", "面议", None, None, None, "本科", "应届/经验不限", "unknown", "unknown", "unknown", "yes", "", "制造系统、实时派货规则和数据优化；自动化相邻岗位，非传统电气设计。"),
    job_row("zhaopin_CC000439650J40870065707", "智联招聘", "https://m.zhaopin.com/jobs/CC000439650J40870065707.htm", "封装生产运筹工程师-临港（2027届校招）", "中芯国际集成电路制造(上海)有限公司", "生产运筹", "面议", None, None, None, "本科/硕士", "应届", "rotating", "unknown", "unknown", "yes", "", "电气、自动化等可投；明确白班/夜班/轮班和洁净室；不符合双休硬条件。"),
    job_row("yingjiesheng_J11192", "应届生求职网转载51job", "https://m.yingjiesheng.com/job-008-033-479.html", "设备工程师-临港-2027届(J11192)", "上海艾为电子技术股份有限公司", "设备工程", "未列薪资", None, None, None, "本科及以上", "2027应届", "unknown", "unknown", "unknown", "yes", "", "2027本科，电子工程相关；设备维修改机、测试平台异常处理与硬件改造；是否接受电气工程需确认。"),
    job_row("yingjiesheng_yanfeng_2027", "应届生求职网转载51job", "https://m.yingjiesheng.com/job-008-084-813.html", "2027届应届生-临港公司-工程设备方向", "延锋彼欧汽车外饰系统有限公司", "工程设备", "未列薪资", None, None, None, "本科及以上", "2027应届", "unknown", "unknown", "unknown", "yes", "", "机械、电气自动化等优先；涉及设备安装、改造、TPM与现场问题处理；用户可接受现场调试/工程实施。"),
    job_row("gta_2027_equipment", "积塔半导体官网", "https://www.gtasemi.com.cn/careers/campus-recruitment_2", "设备工程师（2027届）", "上海积塔半导体有限公司", "设备工程", "未列薪资", None, None, None, "本科及以上", "2027应届", "unknown", "unknown", "unknown", "no", "厂址位于泥城镇，未证明属于滴水湖核心区", "机械、自动化、电气工程相关；上海自贸区厂区（云水路600号）；纳入更广临港片区观察，不纳入核心区供给。"),
    job_row("zhaopin_CC000439650J40872309907", "智联招聘", "https://www.zhaopin.com/jobdetail/CC000439650J40872309907.htm", "设备工程师-临港（2027届校招）-DIFF", "中芯国际集成电路制造(上海)有限公司", "设备工程", "1-2万·16薪", 10000, 20000, 16, "硕士", "应届/经验不限", "unknown", "unknown", "unknown", "no", "学历要求硕士，不是本科主样本", "仅作同企业2027设备岗薪资锚点；本科不得套用。"),
    job_row("zhaopin_sjtu_mechatronics", "智联招聘", "https://www.zhaopin.com/jobdetail/CC445534830J00183849304.htm", "机电一体化工程师（临港）", "上海交大临港智能制造创新科技有限公司", "机电/自动化", "1-1.2万", 10000, 12000, 12, "本科", "1-3年", "unknown", "unknown", "unknown", "no", "非2027应届，有1-3年经验要求", "南汇新城海洋一路333号；机器人调试；提供免费班车（页面信号，班车路线需确认）。"),
    job_row("zhaopin_smic_metrology", "智联招聘", "https://www.zhaopin.com/jobdetail/CC000439650J40328271707.htm", "量测设备工程师-临港", "中芯国际集成电路制造(上海)有限公司", "设备工程", "1-1.5万·15薪", 10000, 15000, 15, "本科", "1-3年", "unknown", "unknown", "unknown", "no", "有1-3年经验要求，不是应届样本", "接受夜班/无尘室；仅作经验岗市场信号。"),
    job_row("zhaopin_smic_metrology_12in", "智联招聘", "https://www.zhaopin.com/jobdetail/CC000439650J40328271707.htm", "量测设备工程师-临港12寸", "中芯国际集成电路制造(上海)有限公司", "设备工程", "1.3-1.8万·15薪", 13000, 18000, 15, "本科", "1-3年", "unknown", "unknown", "unknown", "no", "有1-3年经验要求，不是应届样本", "经验岗信号；岗位页面工作条件需面试确认。"),
    job_row("zhaopin_shengmei_equipment", "智联招聘", "https://www.zhaopin.com/jobdetail/CC838172970J40826794512.htm", "研发线设备工程师", "盛美半导体设备（上海）股份有限公司", "设备工程", "1.1-1.8万·14薪", 11000, 18000, 14, "本科", "3-5年", "unknown", "unknown", "unknown", "no", "有3-5年经验要求，不是应届样本", "临港总部；经验岗信号，不能作为2027本科起薪。"),
    job_row("zhaopin_CCL1394680540J40958598908", "智联招聘", "https://www.zhaopin.com/jobdetail/CCL1394680540J40958598908.htm", "电气工程师（量产支持） (MJ000057)", "乐孜芯创半导体设备(上海)有限公司", "电气/自动化", "8000-15000元·17薪", 8000, 15000, 17, "本科", "1-3年", "unknown", "unknown", "unknown", "no", "有1-3年经验要求，不是应届样本", "临港飞渡路；2027-04后常驻临港；经验岗信号。"),
    job_row("zhaopin_CCL1345579240J40722949811", "智联招聘", "https://www.zhaopin.com/jobdetail/CCL1345579240J40722949811.htm", "售后工程师-上海临港", "常熟柏山科技有限公司", "现场/售后工程", "6000-9000元·13薪", 6000, 9000, 13, "大专及以上", "经验不限", "double", "unknown", "provided", "no", "未明确限定2027应届，且岗位描述含值班/快速到场要求", "页面标签为周末双休、包住；同时有2小时到场响应与值班要求，仅作工作条件案例。"),
]


RENTS = [
    {"city": CITY, "district": "临港新城", "rent_mode": "whole", "area_sqm": "", "monthly_rent": 2200, "listing_count": "", "deposit_months": "", "advance_rent_months": "", "agency_fee_months": "", "service_fee_monthly": "", "service_fee_upfront": "", "station_distance_km": "", "source_name": "安居客临港新城租金页", "source_url": "https://m.anjuke.com/sh/rent/", "published_at": "2026-10-26", "collected_at": COLLECTED, "evidence_level": "C", "notes": "页面“一室今日租金均价”，样本量、面积和成交属性不透明；只作市场观察，不作为成交均价。"},
    {"city": CITY, "district": "临港新城", "rent_mode": "whole", "area_sqm": "", "monthly_rent": 2400, "listing_count": 1, "deposit_months": "", "advance_rent_months": "", "agency_fee_months": "", "service_fee_monthly": "", "service_fee_upfront": "", "station_distance_km": "", "source_name": "安居客：滴水湖馨苑创馨派", "source_url": "https://m.anjuke.com/sh/rent/", "published_at": "2026-10-26", "collected_at": COLLECTED, "evidence_level": "C", "notes": "1室1厅精装修示例挂牌；页面未提供稳定明细链接和可比面积，押付与服务费未核实。"},
    {"city": CITY, "district": "临港新城", "rent_mode": "whole", "area_sqm": "", "monthly_rent": 1300, "listing_count": 1, "deposit_months": "", "advance_rent_months": "", "agency_fee_months": "", "service_fee_monthly": "", "service_fee_upfront": "", "station_distance_km": "", "source_name": "安居客：绿地东岸涟城（南区公寓住宅）", "source_url": "https://m.anjuke.com/sh/rent/", "published_at": "2026-10-26", "collected_at": COLLECTED, "evidence_level": "C", "notes": "页面显示1室2厅1300元/月的低价示例；可能为公寓或特殊房源，面积未在页面上稳定呈现，不当作典型一居。"},
    {"city": CITY, "district": "临港", "rent_mode": "share", "area_sqm": "", "monthly_rent": 1100, "listing_count": 1, "deposit_months": "", "advance_rent_months": "", "agency_fee_months": "", "service_fee_monthly": "", "service_fee_upfront": "", "station_distance_km": "", "source_name": "58同城：保利蔚蓝林语合租单间", "source_url": "https://sh.58.com/hezu/4088587099561999x.shtml", "published_at": "2025-06-03", "collected_at": COLLECTED, "evidence_level": "C", "notes": "独立卫浴单间；历史挂牌，面积、水电和服务费未完整核实。"},
    {"city": CITY, "district": "临港新城", "rent_mode": "share", "area_sqm": "", "monthly_rent": 1500, "listing_count": 1, "deposit_months": "", "advance_rent_months": "", "agency_fee_months": "", "service_fee_monthly": "", "service_fee_upfront": "", "station_distance_km": "", "source_name": "临港合租市场观察区间上沿", "source_url": "https://m.anjuke.com/sh/rent/", "published_at": "2026-10-26", "collected_at": COLLECTED, "evidence_level": "C", "notes": "由少量平台与搜索样本形成的观察上沿，面积和样本量不透明；不是统计中位数。"},
    {"city": CITY, "district": "临港", "rent_mode": "whole", "area_sqm": 77, "monthly_rent": 2000, "listing_count": 1, "deposit_months": "", "advance_rent_months": "", "agency_fee_months": "", "service_fee_monthly": "", "service_fee_upfront": "", "station_distance_km": "", "source_name": "房天下：宜浩佳园", "source_url": "https://zu.fang.com/sh/chuzu/8_1016019970_1.htm", "published_at": "2025-07-10", "collected_at": COLLECTED, "evidence_level": "C", "notes": "1室2厅77㎡；历史挂牌，户型面积不典型。"},
    {"city": CITY, "district": "临港", "rent_mode": "whole", "area_sqm": 84, "monthly_rent": 2300, "listing_count": 1, "deposit_months": "", "advance_rent_months": "", "agency_fee_months": "", "service_fee_monthly": "", "service_fee_upfront": "", "station_distance_km": "", "source_name": "贝壳：绿地东岸涟城", "source_url": "https://m.ke.com/chuzu/sh/zufang/SH1661736411599994880.html", "published_at": "2025-09-01", "collected_at": COLLECTED, "evidence_level": "C", "notes": "2室1厅84㎡；适合合租或情侣，不是单人一居。"},
    {"city": CITY, "district": "临港主城区", "rent_mode": "other", "area_sqm": 31.27, "monthly_rent": 1000, "listing_count": 1, "deposit_months": "", "advance_rent_months": "", "agency_fee_months": 0, "service_fee_monthly": "", "service_fee_upfront": "", "station_distance_km": 6.5, "source_name": "临港人才公寓：宸寓·星苑", "source_url": "https://www.lingang.gov.cn/html/website/lg/rc/hotspot/redianxinwen/p1781237685213462530.html", "published_at": "2024-04-12", "collected_at": COLLECTED, "evidence_level": "A", "notes": "官方人才公寓一居室低端租金；rent_mode=other用于标识条件性人才住房，需符合资格，距滴水湖站约6.5公里。"},
    {"city": CITY, "district": "临港主城区", "rent_mode": "other", "area_sqm": 53.25, "monthly_rent": 1800, "listing_count": 1, "deposit_months": "", "advance_rent_months": "", "agency_fee_months": 0, "service_fee_monthly": "", "service_fee_upfront": "", "station_distance_km": 6.5, "source_name": "临港人才公寓：宸寓·星苑", "source_url": "https://www.lingang.gov.cn/html/website/lg/rc/hotspot/redianxinwen/p1781237685213462530.html", "published_at": "2024-04-12", "collected_at": COLLECTED, "evidence_level": "A", "notes": "官方人才公寓一居室高端租金；rent_mode=other用于标识条件性人才住房，资格与空房需另核。"},
]


LIVING = [
    {"city": CITY, "district": "临港", "food_monthly": 1500, "commute_monthly": 160, "water_monthly": 16.2, "electricity_monthly": 61.7, "gas_monthly": 18, "internet_monthly": 50, "other_fixed_monthly": 300, "source_url": "https://www.shobserver.cn/sgh/detail?id=1695525", "published_at": "2026-01-14", "collected_at": COLLECTED, "evidence_level": "C", "notes": "合租个人分摊；餐饮低档1500元=8+18+20元/日×30，不含优惠券；水4m³、电100kWh/2人、气6m³/2人、网50元/人。"},
    {"city": CITY, "district": "临港", "food_monthly": 2100, "commute_monthly": 160, "water_monthly": 16.2, "electricity_monthly": 61.7, "gas_monthly": 18, "internet_monthly": 50, "other_fixed_monthly": 300, "source_url": "https://www.shobserver.cn/sgh/detail?id=1695525", "published_at": "2026-01-14", "collected_at": COLLECTED, "evidence_level": "C", "notes": "主情景；餐饮2100元=70元/日×30；其他固定300元含手机、清洁和个人用品，未含旅行/医疗。"},
    {"city": CITY, "district": "临港", "food_monthly": 2800, "commute_monthly": 160, "water_monthly": 16.2, "electricity_monthly": 61.7, "gas_monthly": 18, "internet_monthly": 50, "other_fixed_monthly": 300, "source_url": "https://sh.58.com/lingangxinc/kuaican/list_25/", "published_at": "2026-10-26", "collected_at": COLLECTED, "evidence_level": "C", "notes": "外卖高频情景；约93元/日×30，按单餐商品20-35元加配送/包装2-9元组合，不假定长期优惠券。"},
    {"city": CITY, "district": "临港", "food_monthly": 1500, "commute_monthly": 160, "water_monthly": 16.2, "electricity_monthly": 74.04, "gas_monthly": 18, "internet_monthly": 100, "other_fixed_monthly": 300, "source_url": "https://www.shobserver.cn/sgh/detail?id=1695525", "published_at": "2026-01-14", "collected_at": COLLECTED, "evidence_level": "C", "notes": "整租个人承担；水4m³、电120kWh、气6m³、网100元；餐饮低档1500元。"},
    {"city": CITY, "district": "临港", "food_monthly": 2100, "commute_monthly": 160, "water_monthly": 16.2, "electricity_monthly": 74.04, "gas_monthly": 18, "internet_monthly": 100, "other_fixed_monthly": 300, "source_url": "https://www.shobserver.cn/sgh/detail?id=1695525", "published_at": "2026-01-14", "collected_at": COLLECTED, "evidence_level": "C", "notes": "整租主情景；餐饮2100元；其他固定300元；未含旅游、医疗和家电一次性支出。"},
    {"city": CITY, "district": "临港", "food_monthly": 2800, "commute_monthly": 160, "water_monthly": 16.2, "electricity_monthly": 74.04, "gas_monthly": 18, "internet_monthly": 100, "other_fixed_monthly": 300, "source_url": "https://sh.58.com/lingangxinc/kuaican/list_25/", "published_at": "2026-10-26", "collected_at": COLLECTED, "evidence_level": "C", "notes": "整租外卖高频情景；水电气按官方单价和透明用量计算，餐饮为模型篮子。"},
]


PAYROLL = [
    {
        "city": CITY,
        "year": 2026,
        "employee_social_rate": 0.105,
        "employee_fund_rate": 0.07,
        "social_security_monthly": "",
        "housing_fund_monthly": "",
        "special_deduction_monthly": 1500,
        "tax_model": "china_annualized",
        "source_url": "https://rsj.sh.gov.cn/tgsgg_17341/20260818/t0035_1443203.html",
        "published_at": "2026-08-18",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "notes": "社保基数取max(7546,月固定税前)；公积金基数取max(2740,月固定税前)；主公积金7%。",
    },
    {
        "city": CITY,
        "year": 2026,
        "employee_social_rate": 0.105,
        "employee_fund_rate": 0.05,
        "social_security_monthly": "",
        "housing_fund_monthly": "",
        "special_deduction_monthly": 1500,
        "tax_model": "china_annualized",
        "source_url": "https://www.shzfgjj.cn/html/twzl/228488.html",
        "published_at": "2026-08-19",
        "collected_at": COLLECTED,
        "evidence_level": "A",
        "notes": "公积金5%敏感性，用于企业选择下限的情形；补充公积金未计。",
    },
]


OFFICIAL_SALARY = [
    {"city": CITY, "district": "全市", "metric": "全口径城镇单位就业人员平均工资", "year": 2025, "period": "月", "value": 12577, "unit": "元/月", "sample_n": "", "source_name": "上海市人社局", "source_url": "https://rsj.sh.gov.cn/tgsgg_17341/20260818/t0035_1443203.html", "published_at": "2026-08-18", "collected_at": COLLECTED, "evidence_level": "A", "notes": "用于社保口径的官方全口径平均工资，不是2027电气本科应届招聘中位数。"},
    {"city": CITY, "district": "全市", "metric": "居民人均可支配收入", "year": 2025, "period": "年", "value": 91987, "unit": "元/年", "sample_n": "", "source_name": "上海市统计局", "source_url": "https://tjj.sh.gov.cn/ydsj71/20260120/39ae4cd58421478d897b739d83f39c10.html", "published_at": "2026-01-20", "collected_at": COLLECTED, "evidence_level": "A", "notes": "全体居民口径，不能当作目标岗位工资。"},
    {"city": CITY, "district": "全市", "metric": "居民人均消费支出", "year": 2025, "period": "年", "value": 54765, "unit": "元/年", "sample_n": "", "source_name": "上海市统计局", "source_url": "https://tjj.sh.gov.cn/ydsj71/20260120/39ae4cd58421478d897b739d83f39c10.html", "published_at": "2026-01-20", "collected_at": COLLECTED, "evidence_level": "A", "notes": "全体居民平均口径，含家庭消费结构，不直接替代单身青年预算。"},
    {"city": CITY, "district": "全市", "metric": "城镇常住居民人均消费支出", "year": 2025, "period": "年", "value": 57076, "unit": "元/年", "sample_n": "", "source_name": "上海市统计局", "source_url": "https://tjj.sh.gov.cn/ydsj71/20260120/39ae4cd58421478d897b739d83f39c10.html", "published_at": "2026-01-20", "collected_at": COLLECTED, "evidence_level": "A", "notes": "城镇常住居民平均口径，只作外部交叉校验。"},
]


def annual_tax(taxable: float) -> float:
    bands = (
        (36000, 0.03, 0),
        (144000, 0.10, 2520),
        (300000, 0.20, 16920),
        (420000, 0.25, 31920),
        (660000, 0.30, 52920),
        (960000, 0.35, 85920),
        (math.inf, 0.45, 181920),
    )
    taxable = max(0.0, taxable)
    for ceiling, rate, quick in bands:
        if taxable <= ceiling:
            return max(0.0, taxable * rate - quick)
    return 0.0


def payroll(gross: float, months: int, fund_rate: float = 0.07) -> dict:
    social_base = min(37731, max(7546, gross))
    fund_base = min(37731, max(2740, gross))
    social = social_base * 0.105
    fund = fund_base * fund_rate
    annual_gross = gross * months
    annual_social = social * 12
    annual_fund = fund * 12
    taxable = max(0.0, annual_gross - annual_social - annual_fund - 60000 - 1500 * 12)
    tax = annual_tax(taxable)
    monthly_cash = (annual_gross - annual_social - annual_fund - tax) / 12
    return {
        "social_base": social_base,
        "fund_base": fund_base,
        "social": social,
        "fund": fund,
        "annual_gross": annual_gross,
        "annual_social": annual_social,
        "annual_fund": annual_fund,
        "taxable": taxable,
        "tax": tax,
        "monthly_cash": monthly_cash,
    }


HOUSING_SCENARIOS = {
    "合租-直租": {
        "rent": 1200,
        "deposit": 1,
        "advance": 1,
        "agency": 0,
        "service": 0,
        "service_upfront": 0,
        "utilities": 145.9,
        "commute": 160,
        "rent_n": 2,
        "rent_level": "C",
        "rent_key": "evi_58_share_listing",
        "notes": "合租市场观察区间1100-1500取中值1200；1人分摊水电气网，直租无中介费。",
    },
    "合租-中介押一付三": {
        "rent": 1300,
        "deposit": 1,
        "advance": 3,
        "agency": 0.35,
        "service": 0,
        "service_upfront": 0,
        "utilities": 145.9,
        "commute": 160,
        "rent_n": 2,
        "rent_level": "C",
        "rent_key": "evi_agency_fee",
        "notes": "合租上沿1300；押一付三并按0.35个月中介费做敏感性，签约前须核实。",
    },
    "整租-直租": {
        "rent": 2200,
        "deposit": 1,
        "advance": 1,
        "agency": 0,
        "service": 0,
        "service_upfront": 0,
        "utilities": 208.24,
        "commute": 160,
        "rent_n": 6,
        "rent_level": "C",
        "rent_key": "evi_anjuke_rent",
        "notes": "整租一室取安居客今日均价2200；不是成交均价，直接租赁无中介费。",
    },
    "整租-中介押一付三": {
        "rent": 2200,
        "deposit": 1,
        "advance": 3,
        "agency": 0.35,
        "service": 0,
        "service_upfront": 0,
        "utilities": 208.24,
        "commute": 160,
        "rent_n": 6,
        "rent_level": "C",
        "rent_key": "evi_agency_fee",
        "notes": "整租2200；押一付三并按0.35个月中介费做敏感性，不含品牌公寓服务费。",
    },
    "人才公寓-条件情景": {
        "rent": 1500,
        "deposit": 1,
        "advance": 1,
        "agency": 0,
        "service": 0,
        "service_upfront": 0,
        "utilities": 208.24,
        "commute": 180,
        "rent_n": 1,
        "rent_level": "A",
        "rent_key": "evi_talent_apartment",
        "notes": "官方项目一居1000-1800取中值1500；押付按1+1压力测试，资格、空房和实际合同需审核。",
    },
}


def category_food(food: int, utilities: float, commute: int) -> dict:
    return {
        "food": food,
        "water": 16.2,
        "electricity": 61.7 if utilities < 200 else 74.04,
        "gas": 18,
        "internet": 50 if utilities < 200 else 100,
        "commute": commute,
        "other": 300,
    }


def build_model_rows() -> list[dict]:
    rows: list[dict] = []
    salaries = [8000, 10000, 12000, 15000]
    for gross in salaries:
        for housing_name, scenario in HOUSING_SCENARIOS.items():
            pay = payroll(gross, 12)
            rows.append(model_row(gross, 12, housing_name, scenario, pay))
    for months in [13, 16]:
        for housing_name, scenario in HOUSING_SCENARIOS.items():
            pay = payroll(10000, months)
            rows.append(model_row(10000, months, housing_name, scenario, pay))
    return rows


def model_row(gross: int, months: int, housing_name: str, scenario: dict, pay: dict) -> dict:
    suffix = "" if months == 12 else f"-{months}薪"
    return {
        "city": CITY,
        "district": DISTRICT,
        "job_family": "电气/自动化/设备工程",
        "scenario": f"{gross}元-{housing_name}{suffix}",
        "monthly_gross": gross,
        "annual_months": months,
        "social_security_monthly": round(pay["social"], 2),
        "housing_fund_monthly": round(pay["fund"], 2),
        "special_deduction_monthly": 1500,
        "monthly_cash_override": round(pay["monthly_cash"], 2),
        "rent_monthly": scenario["rent"],
        "deposit_months": scenario["deposit"],
        "advance_rent_months": scenario["advance"],
        "agency_fee_months": scenario["agency"],
        "service_fee_monthly": scenario["service"],
        "service_fee_upfront": scenario["service_upfront"],
        "water_monthly": 16.2,
        "electricity_monthly": 61.7 if scenario["utilities"] < 200 else 74.04,
        "gas_monthly": 18,
        "internet_monthly": 50 if scenario["utilities"] < 200 else 100,
        "food_monthly": 2100,
        "commute_monthly": scenario["commute"],
        "other_fixed_monthly": 300,
        "other_upfront": 0,
        "employer_housing": "no",
        "salary_sample_n": 0,
        "rent_sample_n": scenario["rent_n"],
        "employer_count": 3,
        "max_employer_share": round(4 / 6, 3),
        "salary_evidence_level": "C",
        "rent_evidence_level": scenario["rent_level"],
        "cost_evidence_level": "C",
        "source_keys": "|".join([
            "evi_social_base", "evi_social_rates", "evi_fund_2026", "evi_tax_rent",
            "evi_tax_rates", "evi_price_guide", scenario["rent_key"], "evi_food_basket",
            "evi_internet_model", "evi_smic_supply", "evi_smic_packaging",
            "evi_aiwill_2027", "evi_yanfeng_2027",
        ]),
        "notes": scenario["notes"] + " 薪资为压力测试输入，不是观测到的2027应届中位数。",
    }


EVIDENCE_COLUMNS = ["module", "key", "source_name", "source_type", "url", "published_at", "collected_at", "evidence_level", "scope", "raw_file", "notes"]
JOB_COLUMNS = ["job_id", "source", "source_url", "collected_at", "evidence_level", "search_keyword", "search_page", "city", "district", "company", "company_id", "job_title", "job_family", "monthly_min", "monthly_max", "salary_text", "annual_months", "education", "experience", "salary_type", "weekend", "trip_requirement", "accommodation", "include_in_analysis", "exclusion_reason", "notes"]
RENT_COLUMNS = ["city", "district", "rent_mode", "area_sqm", "monthly_rent", "listing_count", "deposit_months", "advance_rent_months", "agency_fee_months", "service_fee_monthly", "service_fee_upfront", "station_distance_km", "source_name", "source_url", "published_at", "collected_at", "evidence_level", "notes"]
LIVING_COLUMNS = ["city", "district", "food_monthly", "commute_monthly", "water_monthly", "electricity_monthly", "gas_monthly", "internet_monthly", "other_fixed_monthly", "source_url", "published_at", "collected_at", "evidence_level", "notes"]
PAYROLL_COLUMNS = ["city", "year", "employee_social_rate", "employee_fund_rate", "social_security_monthly", "housing_fund_monthly", "special_deduction_monthly", "tax_model", "source_url", "published_at", "collected_at", "evidence_level", "notes"]
OFFICIAL_COLUMNS = ["city", "district", "metric", "year", "period", "value", "unit", "sample_n", "source_name", "source_url", "published_at", "collected_at", "evidence_level", "notes"]
MODEL_COLUMNS = ["city", "district", "job_family", "scenario", "monthly_gross", "annual_months", "social_security_monthly", "housing_fund_monthly", "special_deduction_monthly", "monthly_cash_override", "rent_monthly", "deposit_months", "advance_rent_months", "agency_fee_months", "service_fee_monthly", "service_fee_upfront", "water_monthly", "electricity_monthly", "gas_monthly", "internet_monthly", "food_monthly", "commute_monthly", "other_fixed_monthly", "other_upfront", "employer_housing", "salary_sample_n", "rent_sample_n", "employer_count", "max_employer_share", "salary_evidence_level", "rent_evidence_level", "cost_evidence_level", "source_keys", "notes"]


def calculate_scenario(row: dict) -> dict:
    rent = float(row["rent_monthly"])
    agency_amortized = rent * float(row["agency_fee_months"]) / 12
    utilities = sum(float(row[key]) for key in ["water_monthly", "electricity_monthly", "gas_monthly", "internet_monthly"])
    recurring = rent + agency_amortized + float(row["service_fee_monthly"]) + utilities + float(row["food_monthly"]) + float(row["commute_monthly"]) + float(row["other_fixed_monthly"])
    net_cash = float(row["monthly_cash_override"]) - recurring
    upfront_rent = rent * (float(row["deposit_months"]) + float(row["advance_rent_months"]) + float(row["agency_fee_months"])) + float(row["service_fee_upfront"])
    living_first_month = utilities + float(row["service_fee_monthly"]) + float(row["food_monthly"]) + float(row["commute_monthly"]) + float(row["other_fixed_monthly"])
    return {
        **row,
        "agency_amortized": agency_amortized,
        "utilities": utilities,
        "recurring": recurring,
        "net_cash": net_cash,
        "net_with_fund": net_cash + float(row["housing_fund_monthly"]),
        "upfront_rent": upfront_rent,
        "living_first_month": living_first_month,
        "first_month_min": upfront_rent + living_first_month,
        "first_month_with_2000_buffer": upfront_rent + living_first_month + 2000,
        "rent_burden_pct": rent / float(row["monthly_gross"]),
    }


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv("jobs.csv", JOBS, JOB_COLUMNS)
    write_csv("rent.csv", RENTS, RENT_COLUMNS)
    write_csv("living_costs.csv", LIVING, LIVING_COLUMNS)
    write_csv("payroll_assumptions.csv", PAYROLL, PAYROLL_COLUMNS)
    write_csv("official_salary.csv", OFFICIAL_SALARY, OFFICIAL_COLUMNS)
    write_csv("evidence.csv", EVIDENCE, EVIDENCE_COLUMNS)
    model = build_model_rows()
    write_csv("city_model.csv", model, MODEL_COLUMNS)

    recalculated = [calculate_scenario(row) for row in model]
    salary_rows = [row for row in JOBS if row["include_in_analysis"] == "yes" and row["monthly_min"] != ""]
    direct_jobs = [row for row in JOBS if "2027" in row["job_title"] and row["include_in_analysis"] == "yes"]
    explicit_salary = [row for row in direct_jobs if row["monthly_min"] != ""]
    double_weekend_explicit = [row for row in direct_jobs if row["weekend"] == "double"]
    no_trip_explicit = [row for row in direct_jobs if row["trip_requirement"] == "none"]
    hard_qualified = [
        row for row in direct_jobs
        if row["monthly_min"] != "" and row["weekend"] == "double" and row["trip_requirement"] == "none"
    ]
    # The report table includes every excluded record with a disclosed salary
    # range, including the master's-degree sensitivity anchor. Keep headline
    # statistics on the exact same population so count/range/median cannot drift.
    comparable_market = [
        row for row in JOBS if row["include_in_analysis"] == "no" and row["monthly_min"] != ""
    ]
    market_equiv = []
    for row in comparable_market:
        mid = (float(row["monthly_min"]) + float(row["monthly_max"])) / 2
        months = int(row["annual_months"]) if row["annual_months"] else 12
        market_equiv.append(mid * months / 12)

    payload = {
        "meta": {
            "title": "2027届电气工程及其自动化本科应届生临港城市调研",
            "area_requested": "上海市浦东新区临港心片区",
            "area_operational": AREA,
            "data_cutoff": COLLECTED,
            "data_version": "2027EE-LG-20261026-v1",
            "graduate_year": 2027,
            "major": "电气工程及其自动化",
            "currency": "CNY",
            "note": "临港心片区按临港新片区、重点滴水湖/南汇新城核心区解释；泥城、书院等更广范围单列。",
        },
        "headline": {
            "direct_2027_job_n": len(direct_jobs),
            "direct_2027_employer_n": len({row["company"] for row in direct_jobs}),
            "explicit_salary_n": len(explicit_salary),
            "double_weekend_explicit_n": len(double_weekend_explicit),
            "no_trip_explicit_n": len(no_trip_explicit),
            "hard_qualified_n": len(hard_qualified),
            "market_anchor_n": len(comparable_market),
            "market_annualized_mid_min": round(min(market_equiv), 2) if market_equiv else None,
            "market_annualized_mid_median": round(median(market_equiv), 2) if market_equiv else None,
            "market_annualized_mid_max": round(max(market_equiv), 2) if market_equiv else None,
        },
        "jobs": JOBS,
        "rents": RENTS,
        "living": LIVING,
        "official_salary": OFFICIAL_SALARY,
        "evidence": EVIDENCE,
        "scenarios": recalculated,
        "payroll_examples": {str(gross): payroll(gross, 12) for gross in [8000, 10000, 12000, 15000]},
        "assumptions": {
            "salary_inputs_not_observations": [8000, 10000, 12000, 15000],
            "main_fund_rate": 0.07,
            "sensitivity_fund_rate": 0.05,
            "social_rate": 0.105,
            "social_base_min": 7546,
            "social_base_max": 37731,
            "fund_base_min": 2740,
            "fund_base_max": 37731,
            "special_deduction": 1500,
            "food_baskets": {
                "食堂/自炊/低价混合": 1500,
                "堂食与外卖混合": 2100,
                "外卖高频": 2800,
            },
            "delivery_single_meal_all_in_range": [22, 44],
            "emergency_buffer": 2000,
            "lease_months": 12,
        },
    }
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
    (DATA / "analysis_payload.json").write_text(payload_text, encoding="utf-8", newline="\n")
    manifest = {
        "data_version": payload["meta"]["data_version"],
        "data_cutoff": COLLECTED,
        "payload_file": "data/analysis_payload.json",
        "payload_sha256": hashlib.sha256(payload_text.encode("utf-8")).hexdigest(),
        "generated_at": "2026-10-26T22:00:00+08:00",
    }
    (DATA / "build_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "jobs": len(JOBS),
        "direct_2027_core": len(direct_jobs),
        "explicit_salary_2027_core": len(explicit_salary),
        "double_weekend_explicit": len(double_weekend_explicit),
        "no_trip_explicit": len(no_trip_explicit),
        "hard_qualified": len(hard_qualified),
        "model_scenarios": len(model),
        "market_anchor_n": len(comparable_market),
        "market_annualized_mid": payload["headline"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
