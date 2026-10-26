# -*- coding: utf-8 -*-
"""Final net-surplus model with per-city rent, food, commute and payroll tax."""

import json
import re

import pandas as pd

SOCIAL_RATE = 0.105      # 养老 8% + 医疗 2% + 失业 0.5%
FUND_RATE = 0.08         # 公积金个人缴存，各市区间 5%-12%，取中位
BASE_FLOOR = 4900        # 社保缴费基数下限（各市 4500-5500，取中位）
THRESHOLD = 5000

# 地铁单程票价按 10 公里典型通勤估算，依据各市公开计价规则
COMMUTE_FARE = {
    "上海": 4.0, "杭州": 4.0,
    "南京": 3.0, "苏州": 3.0, "宁波": 3.0, "无锡": 3.0, "常州": 3.0,
    "徐州": 3.0, "南通": 3.0, "温州": 3.0, "绍兴": 3.0, "金华": 3.0, "台州": 3.0,
}
BUS_FARE = 2.0
WORK_DAYS = 22

BRACKETS = [(3000, 0.03, 0), (12000, 0.10, 210), (25000, 0.20, 1410),
            (35000, 0.25, 2660), (55000, 0.30, 4410), (80000, 0.35, 7160)]


def income_tax(taxable):
    if taxable <= 0:
        return 0.0
    for ceiling, rate, deduction in BRACKETS:
        if taxable <= ceiling:
            return taxable * rate - deduction
    return taxable * 0.45 - 15160


def main():
    rent = pd.read_csv("ee-yzj-research/gh-tools/city_rent_2026.csv", encoding="utf-8-sig")
    food = pd.read_csv(
        "ee-yzj-research/gh-tools/餐饮成本推算.csv", encoding="utf-8-sig"
    )[["城市", "单身青年月"]]
    measured_rent = {"上海": 2335, "杭州": 1484, "温州": 1188, "南京": 1073}

    jobs = json.load(open("ee-yzj-research/gh-tools/fullrun/combined_jobs.json", encoding="utf-8"))
    pattern = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)K")
    lows = []
    for job in jobs:
        if job.get("source_experience") != "102":
            continue
        match = pattern.search(job.get("salary") or "")
        if match:
            lows.append({"城市": job.get("source_city"), "lo": float(match.group(1))})
    salary = pd.DataFrame(lows).groupby("城市")["lo"].median().reset_index()
    salary.columns = ["城市", "月薪K"]
    salary["税前月薪"] = (salary["月薪K"] * 1000).round(0)

    df = rent.merge(salary, on="城市", how="left").merge(food, on="城市", how="left")
    df["合租月租"] = df.apply(
        lambda r: measured_rent.get(r["城市"], round(r["租金元每平米每月"] * 25.8)), axis=1
    )
    df["房租性质"] = df["城市"].map(lambda c: "实测" if c in measured_rent else "模型推算")
    df["通勤单程"] = df["城市"].map(lambda c: COMMUTE_FARE.get(c, BUS_FARE))
    df["通勤"] = (df["通勤单程"] * 2 * WORK_DAYS).round(0)
    df["通勤方式"] = df["城市"].map(lambda c: "地铁" if c in COMMUTE_FARE else "公交")

    base = df["税前月薪"].clip(lower=BASE_FLOOR)
    df["社保"] = (base * SOCIAL_RATE).round(0)
    df["公积金"] = (base * FUND_RATE).round(0)
    df["应税所得"] = (df["税前月薪"] - df["社保"] - df["公积金"] - THRESHOLD).clip(lower=0)
    df["个税"] = df["应税所得"].apply(income_tax).round(0)
    df["现金到手"] = (df["税前月薪"] - df["社保"] - df["公积金"] - df["个税"]).round(0)
    df["餐饮"] = df["单身青年月"]
    df["净结余_现金"] = (df["现金到手"] - df["合租月租"] - df["通勤"] - df["餐饮"]).round(0)
    df["净结余_含公积金"] = (df["净结余_现金"] + df["公积金"]).round(0)
    df["支出合计"] = (df["合租月租"] + df["通勤"] + df["餐饮"]).round(0)

    df = df.sort_values("净结余_含公积金", ascending=False)
    cols = ["城市", "房租性质", "税前月薪", "社保", "公积金", "个税", "现金到手",
            "合租月租", "通勤方式", "通勤", "餐饮", "支出合计",
            "净结余_现金", "净结余_含公积金"]
    df[cols].to_csv("ee-yzj-research/gh-tools/净结余_最终版.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 240)
    print(df[cols].to_string(index=False))
    print()
    print("社保个人 %.1f%%，公积金 %.1f%%，基数下限 %d 元，个税起征点 %d 元"
          % (SOCIAL_RATE * 100, FUND_RATE * 100, BASE_FLOOR, THRESHOLD))
    print("通勤按 10 公里典型通勤、每月 %d 个工作日往返计" % WORK_DAYS)


if __name__ == "__main__":
    main()
