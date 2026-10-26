# -*- coding: utf-8 -*-
"""Tax, social insurance, commute and net-surplus model."""

import json
import re

import pandas as pd

SOCIAL_RATE = 0.105
FUND_RATE = 0.08
BASE_FLOOR = 4500
THRESHOLD = 5000
MEAL = 1500

METRO_CITIES = {
    "上海", "南京", "无锡", "徐州", "常州", "苏州", "南通",
    "杭州", "宁波", "温州", "绍兴", "金华", "台州",
}
METRO_FARE = 3.5 * 2 * 22
BUS_FARE = 2.0 * 2 * 22

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
    actual = {"上海": 2335, "杭州": 1484, "温州": 1188, "南京": 1073}

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

    df = rent.merge(salary, on="城市", how="left")
    eq_area = 25.8
    df["合租月租"] = df.apply(
        lambda r: actual.get(r["城市"], round(r["租金元每平米每月"] * eq_area)), axis=1
    )
    df["数据性质"] = df["城市"].map(lambda c: "实测" if c in actual else "模型推算")

    base = df["税前月薪"].clip(lower=BASE_FLOOR)
    df["社保"] = (base * SOCIAL_RATE).round(0)
    df["公积金"] = (base * FUND_RATE).round(0)
    df["应税所得"] = (df["税前月薪"] - df["社保"] - df["公积金"] - THRESHOLD).clip(lower=0)
    df["个税"] = df["应税所得"].apply(income_tax).round(0)
    df["现金到手"] = (df["税前月薪"] - df["社保"] - df["公积金"] - df["个税"]).round(0)
    df["通勤"] = df["城市"].map(lambda c: round(METRO_FARE if c in METRO_CITIES else BUS_FARE))
    df["餐饮"] = MEAL
    df["净结余_现金"] = (df["现金到手"] - df["合租月租"] - df["通勤"] - df["餐饮"]).round(0)
    df["净结余_含公积金"] = (df["净结余_现金"] + df["公积金"]).round(0)
    df["到手率"] = (df["现金到手"] / df["税前月薪"] * 100).round(1)

    df = df.sort_values("净结余_含公积金", ascending=False)
    cols = ["城市", "数据性质", "税前月薪", "社保", "公积金", "个税", "现金到手",
            "到手率", "合租月租", "通勤", "餐饮", "净结余_现金", "净结余_含公积金"]
    df[cols].to_csv(
        "ee-yzj-research/gh-tools/净结余_含税社保.csv", index=False, encoding="utf-8-sig"
    )
    pd.set_option("display.width", 230)
    print(df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
