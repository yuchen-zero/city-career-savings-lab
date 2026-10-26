#!/usr/bin/env python3
"""Reproducible workbench for graduate city research.

Dependencies: Python 3.10+ standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


EVIDENCE_LEVELS = ("A", "B", "C", "D")
EVIDENCE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "UNKNOWN": 4}
WEEKEND_VALUES = {"double", "single", "rotating", "unknown"}
TRIP_VALUES = {"none", "occasional", "frequent", "required", "unknown"}
ACCOMMODATION_VALUES = {"provided", "subsidy", "none", "unknown"}

JOB_COLUMNS = [
    "job_id", "source", "source_url", "collected_at", "evidence_level",
    "search_keyword", "search_page", "city", "district", "company",
    "company_id", "job_title", "job_family", "monthly_min", "monthly_max",
    "salary_text", "annual_months", "education", "experience", "salary_type",
    "weekend", "trip_requirement", "accommodation", "include_in_analysis",
    "exclusion_reason", "notes",
]

RENT_COLUMNS = [
    "city", "district", "rent_mode", "area_sqm", "monthly_rent",
    "listing_count", "deposit_months", "advance_rent_months",
    "agency_fee_months", "service_fee_monthly", "service_fee_upfront",
    "station_distance_km", "source_name", "source_url", "published_at",
    "collected_at", "evidence_level", "notes",
]

LIVING_COLUMNS = [
    "city", "district", "food_monthly", "commute_monthly", "water_monthly",
    "electricity_monthly", "gas_monthly", "internet_monthly",
    "other_fixed_monthly", "source_url", "published_at", "collected_at",
    "evidence_level", "notes",
]

PAYROLL_COLUMNS = [
    "city", "year", "employee_social_rate", "employee_fund_rate",
    "social_security_monthly", "housing_fund_monthly",
    "special_deduction_monthly", "tax_model", "source_url", "published_at",
    "collected_at", "evidence_level", "notes",
]

OFFICIAL_COLUMNS = [
    "city", "district", "metric", "year", "period", "value", "unit",
    "sample_n", "source_name", "source_url", "published_at", "collected_at",
    "evidence_level", "notes",
]

EVIDENCE_COLUMNS = [
    "module", "key", "source_name", "source_type", "url", "published_at",
    "collected_at", "evidence_level", "scope", "raw_file", "notes",
]

MODEL_COLUMNS = [
    "city", "district", "job_family", "scenario", "monthly_gross",
    "annual_months", "social_security_monthly", "housing_fund_monthly",
    "special_deduction_monthly", "monthly_cash_override", "rent_monthly",
    "deposit_months", "advance_rent_months", "agency_fee_months",
    "service_fee_monthly", "service_fee_upfront", "water_monthly",
    "electricity_monthly", "gas_monthly", "internet_monthly", "food_monthly",
    "commute_monthly", "other_fixed_monthly", "other_upfront",
    "employer_housing", "salary_sample_n", "rent_sample_n", "employer_count",
    "max_employer_share", "salary_evidence_level", "rent_evidence_level",
    "cost_evidence_level", "source_keys", "notes",
]

TEMPLATES = {
    "jobs.csv": JOB_COLUMNS,
    "rent.csv": RENT_COLUMNS,
    "living_costs.csv": LIVING_COLUMNS,
    "payroll_assumptions.csv": PAYROLL_COLUMNS,
    "official_salary.csv": OFFICIAL_COLUMNS,
    "evidence.csv": EVIDENCE_COLUMNS,
    "city_model.csv": MODEL_COLUMNS,
}

DEMO_MODEL_ROW = {
    "city": "示例市",
    "district": "示例区",
    "job_family": "研发设计",
    "scenario": "整租-中介",
    "monthly_gross": "8000",
    "annual_months": "12",
    "social_security_monthly": "650",
    "housing_fund_monthly": "560",
    "special_deduction_monthly": "0",
    "monthly_cash_override": "",
    "rent_monthly": "2200",
    "deposit_months": "1",
    "advance_rent_months": "3",
    "agency_fee_months": "1",
    "service_fee_monthly": "0",
    "service_fee_upfront": "0",
    "water_monthly": "20",
    "electricity_monthly": "100",
    "gas_monthly": "25",
    "internet_monthly": "50",
    "food_monthly": "1200",
    "commute_monthly": "150",
    "other_fixed_monthly": "300",
    "other_upfront": "500",
    "employer_housing": "no",
    "salary_sample_n": "40",
    "rent_sample_n": "20",
    "employer_count": "8",
    "max_employer_share": "0.20",
    "salary_evidence_level": "B",
    "rent_evidence_level": "B",
    "cost_evidence_level": "C",
    "source_keys": "demo-only",
    "notes": "仅用于验证脚本，不可作为实证结论",
}


def csv_read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle).fieldnames or [])


def csv_write(path: Path, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    text = str(value).strip().replace(",", "")
    if text.lower() in {"", "-", "na", "n/a", "null", "none", "nan"}:
        return default
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"not numeric: {value!r}") from exc


def require_float(row: dict[str, str], key: str) -> float:
    value = as_float(row.get(key))
    if value is None:
        raise ValueError(f"missing required number: {key}")
    return value


def nonnegative(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = as_float(row.get(key), default)
    if value is None:
        return default
    if value < 0:
        raise ValueError(f"negative value: {key}")
    return value


def parse_date(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    text = text.replace("/", "-")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        datetime.fromisoformat(text[:10])
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10]))
    except ValueError:
        return False


def split_cities(raw: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,，]", raw or "") if part.strip()]


def issue(level: str, dataset: str, message: str, row: int | None = None,
          field: str | None = None, value: Any = None) -> dict[str, Any]:
    return {
        "level": level,
        "dataset": dataset,
        "row": row,
        "field": field,
        "value": value,
        "message": message,
    }


def init_project(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise SystemExit(f"refusing to overwrite non-empty project: {output}")
    for name in ("data", "sources/raw", "output"):
        (output / name).mkdir(parents=True, exist_ok=True)

    config = {
        "schema_version": 1,
        "region": args.region,
        "major": args.major,
        "graduate_year": args.graduate_year,
        "cities": split_cities(args.cities),
        "data_cutoff": date.today().isoformat(),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tax_model": "china_annualized",
        "default_lease_months": 12,
        "evidence_levels": list(EVIDENCE_LEVELS),
        "notes": "Replace assumptions with local official rules; keep a source key for every headline number.",
    }
    (output / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    for filename, columns in TEMPLATES.items():
        rows: list[dict[str, Any]] = []
        if args.demo and filename == "city_model.csv":
            rows = [DEMO_MODEL_ROW]
        csv_write(output / "data" / filename, columns, rows)

    brief = f"""# {args.region} {args.major} 应届生城市调研

- 目标届别：{args.graduate_year}
- 数据截止日：{config['data_cutoff']}
- 目标城市/区县：{', '.join(config['cities']) or '待补充'}

## 开工前确认

1. 明确排除的行业、企业、岗位和城市。
2. 双休、出差、现场调试、工程实施、住宿是否是硬约束。
3. 整租/合租、人数、首月押付上限和家庭支持。
4. 薪资是否需要税前/税后、是否有年发月数和绩效。
5. 交付格式、地区层级和数据截止日。

## 执行顺序

1. 官方工资、税费社保和生活成本规则。
2. 目标岗位采集、去重和工作条件结构化。
3. 城市/区县整租、合租、押付和渠道费。
4. 建立 `city_model.csv` 情景并运行 `validate`、`jobs-summary`、`calculate`。
5. 生成 Word、Excel、HTML，并完成限制和敏感性分析。

本文件只包含项目参数与方法提示；正式报告必须引用 `data/` 和 `evidence.csv` 的可复核记录。
"""
    (output / "research_brief.md").write_text(brief, encoding="utf-8")
    print(f"initialized: {output}")
    print(f"next: python {Path(__file__).name} validate --project {output}")
    if args.demo:
        print("demo row included; it is synthetic and must not be cited as evidence")
    return 0


def validate_evidence(issues: list[dict[str, Any]], dataset: str, row_number: int,
                      row: dict[str, str], field: str = "evidence_level") -> None:
    level = (row.get(field) or "").strip().upper()
    if not level:
        issues.append(issue("warning", dataset, "missing evidence level", row_number, field))
    elif level not in EVIDENCE_LEVELS:
        issues.append(issue("error", dataset, "invalid evidence level", row_number, field, level))


def validate_url(issues: list[dict[str, Any]], dataset: str, row_number: int,
                 row: dict[str, str], field: str = "source_url") -> None:
    url = (row.get(field) or "").strip()
    if not url:
        issues.append(issue("warning", dataset, "missing source URL", row_number, field))
    elif not re.match(r"^https?://", url, flags=re.I):
        issues.append(issue("error", dataset, "source URL must start with http(s)", row_number, field, url))


def validate_date_field(issues: list[dict[str, Any]], dataset: str, row_number: int,
                        row: dict[str, str], field: str, required: bool = True) -> None:
    value = (row.get(field) or "").strip()
    if not value and not required:
        return
    if not parse_date(value):
        issues.append(issue("warning", dataset, f"missing or invalid {field}", row_number, field, value))


def validate_project(project: Path, strict: bool = False,
                     report_path: Path | None = None) -> tuple[int, dict[str, Any]]:
    data_dir = project / "data"
    config_path = project / "config.json"
    config: dict[str, Any] = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"config.json is invalid JSON: {exc}", file=sys.stderr)
            return 2, {"status": "error", "issues": []}
    else:
        print(f"warning: missing {config_path}", file=sys.stderr)

    lease_months = int(config.get("default_lease_months", 12) or 12)
    cutoff = str(config.get("data_cutoff", ""))
    issues: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}

    for filename, expected_columns in TEMPLATES.items():
        path = data_dir / filename
        if not path.exists():
            issues.append(issue("warning", filename, "file is missing"))
            summaries[filename] = {"rows": 0, "status": "missing"}
            continue
        try:
            rows = csv_read(path)
        except UnicodeDecodeError:
            issues.append(issue("error", filename, "file is not UTF-8/UTF-8-BOM"))
            summaries[filename] = {"rows": 0, "status": "unreadable"}
            continue
        header = csv_header(path)
        missing_columns = [column for column in expected_columns if column not in header]
        if missing_columns:
            issues.append(issue(
                "error", filename, "missing columns", field=",".join(missing_columns)
            ))
        summaries[filename] = {"rows": len(rows), "status": "present"}

        if filename == "jobs.csv":
            seen_ids: set[str] = set()
            fingerprints: Counter[tuple[str, ...]] = Counter()
            included_by_group: Counter[tuple[str, str, str]] = Counter()
            for row_number, row in enumerate(rows, start=2):
                included = (row.get("include_in_analysis") or "").strip().lower()
                if included not in {"yes", "no"}:
                    issues.append(issue(
                        "error", filename, "include_in_analysis must be yes/no",
                        row_number, "include_in_analysis", included,
                    ))
                    included = "yes"
                if included == "no":
                    continue
                for required in ("city", "job_title", "job_family", "company"):
                    if not (row.get(required) or "").strip():
                        issues.append(issue("error", filename, f"missing {required}", row_number, required))
                job_id = (row.get("job_id") or "").strip()
                if job_id:
                    if job_id in seen_ids:
                        issues.append(issue("error", filename, "duplicate job_id", row_number, "job_id", job_id))
                    seen_ids.add(job_id)
                else:
                    issues.append(issue("warning", filename, "missing stable job_id", row_number, "job_id"))
                fingerprint = tuple((row.get(key) or "").strip() for key in (
                    "source", "city", "district", "company", "job_title",
                    "monthly_min", "monthly_max", "annual_months",
                ))
                fingerprints[fingerprint] += 1
                city = (row.get("city") or "").strip() or "UNKNOWN"
                district = (row.get("district") or "").strip() or "UNKNOWN"
                family = (row.get("job_family") or "").strip() or "UNKNOWN"
                included_by_group[(city, district, family)] += 1

                minimum = as_float(row.get("monthly_min"))
                maximum = as_float(row.get("monthly_max"))
                if minimum is not None and minimum <= 0:
                    issues.append(issue("error", filename, "monthly_min must be positive", row_number, "monthly_min"))
                if maximum is not None and maximum <= 0:
                    issues.append(issue("error", filename, "monthly_max must be positive", row_number, "monthly_max"))
                if minimum is not None and maximum is not None and maximum < minimum:
                    issues.append(issue("error", filename, "monthly_max is below monthly_min", row_number))
                if minimum is not None and maximum is not None and minimum > 0 and maximum / minimum > 3:
                    issues.append(issue("warning", filename, "salary range is wider than 3x", row_number))
                if maximum is not None and (maximum < 1000 or maximum > 100000):
                    issues.append(issue("warning", filename, "salary is a potential unit/outlier issue", row_number, "monthly_max", maximum))
                months = as_float(row.get("annual_months"))
                if months is not None and not (1 <= months <= 24):
                    issues.append(issue("error", filename, "annual_months outside 1..24", row_number, "annual_months", months))
                salary_type = (row.get("salary_type") or "").strip().lower()
                if salary_type and salary_type not in {"monthly", "annualized", "hourly", "negotiable"}:
                    issues.append(issue("warning", filename, "unrecognized salary_type", row_number, "salary_type", salary_type))
                if (row.get("weekend") or "").strip().lower() not in WEEKEND_VALUES:
                    issues.append(issue("error", filename, "invalid weekend value", row_number, "weekend"))
                if (row.get("trip_requirement") or "").strip().lower() not in TRIP_VALUES:
                    issues.append(issue("error", filename, "invalid trip_requirement", row_number, "trip_requirement"))
                accommodation = (row.get("accommodation") or "").strip().lower()
                if accommodation not in ACCOMMODATION_VALUES:
                    issues.append(issue("error", filename, "invalid accommodation value", row_number, "accommodation"))
                validate_evidence(issues, filename, row_number, row)
                validate_url(issues, filename, row_number, row)
                validate_date_field(issues, filename, row_number, row, "collected_at")

            for fingerprint, count in fingerprints.items():
                if count > 1:
                    issues.append(issue(
                        "warning", filename, "possible duplicate job fingerprint",
                        value={"fingerprint": fingerprint, "count": count},
                    ))
            for group, count in included_by_group.items():
                if count < 10:
                    issues.append(issue(
                        "warning", filename, "small job sample; do not use for a strong ranking",
                        value={"city": group[0], "district": group[1], "job_family": group[2], "n": count},
                    ))

        elif filename == "rent.csv":
            for row_number, row in enumerate(rows, start=2):
                if not (row.get("city") or "").strip():
                    issues.append(issue("error", filename, "missing city", row_number, "city"))
                mode = (row.get("rent_mode") or "").strip().lower()
                if mode not in {"share", "whole", "brand", "other"}:
                    issues.append(issue("error", filename, "invalid rent_mode", row_number, "rent_mode", mode))
                for key in ("area_sqm", "monthly_rent", "listing_count", "deposit_months",
                            "advance_rent_months", "agency_fee_months", "service_fee_monthly",
                            "service_fee_upfront", "station_distance_km"):
                    try:
                        value = as_float(row.get(key))
                        if value is not None and value < 0:
                            issues.append(issue("error", filename, "negative value", row_number, key, value))
                    except ValueError:
                        issues.append(issue("error", filename, "not numeric", row_number, key, row.get(key)))
                rent = as_float(row.get("monthly_rent"))
                if rent is None or rent <= 0:
                    issues.append(issue("error", filename, "monthly_rent must be positive", row_number, "monthly_rent"))
                elif rent > 50000:
                    issues.append(issue("warning", filename, "monthly rent is a potential outlier", row_number, "monthly_rent", rent))
                listings = as_float(row.get("listing_count"))
                if listings is not None and listings < 10:
                    issues.append(issue("warning", filename, "small rent sample", row_number, "listing_count", listings))
                if mode == "whole" and as_float(row.get("area_sqm")) is None:
                    issues.append(issue("warning", filename, "whole-rent sample lacks area_sqm", row_number, "area_sqm"))
                validate_evidence(issues, filename, row_number, row)
                validate_url(issues, filename, row_number, row)
                validate_date_field(issues, filename, row_number, row, "published_at", required=False)
                validate_date_field(issues, filename, row_number, row, "collected_at")

        elif filename == "living_costs.csv":
            numeric_keys = ("food_monthly", "commute_monthly", "water_monthly",
                            "electricity_monthly", "gas_monthly", "internet_monthly",
                            "other_fixed_monthly")
            for row_number, row in enumerate(rows, start=2):
                if not (row.get("city") or "").strip():
                    issues.append(issue("error", filename, "missing city", row_number, "city"))
                for key in numeric_keys:
                    try:
                        value = as_float(row.get(key))
                        if value is not None and value < 0:
                            issues.append(issue("error", filename, "negative value", row_number, key, value))
                    except ValueError:
                        issues.append(issue("error", filename, "not numeric", row_number, key, row.get(key)))
                validate_evidence(issues, filename, row_number, row)
                validate_url(issues, filename, row_number, row)
                validate_date_field(issues, filename, row_number, row, "published_at", required=False)
                validate_date_field(issues, filename, row_number, row, "collected_at")

        elif filename == "payroll_assumptions.csv":
            for row_number, row in enumerate(rows, start=2):
                for key in ("employee_social_rate", "employee_fund_rate"):
                    try:
                        value = as_float(row.get(key))
                        if value is not None and not (0 <= value <= 1):
                            issues.append(issue("error", filename, "rate must be a decimal between 0 and 1", row_number, key, value))
                    except ValueError:
                        issues.append(issue("error", filename, "not numeric", row_number, key, row.get(key)))
                for key in ("social_security_monthly", "housing_fund_monthly", "special_deduction_monthly"):
                    try:
                        value = as_float(row.get(key))
                        if value is not None and value < 0:
                            issues.append(issue("error", filename, "negative value", row_number, key, value))
                    except ValueError:
                        issues.append(issue("error", filename, "not numeric", row_number, key, row.get(key)))
                validate_evidence(issues, filename, row_number, row)
                validate_url(issues, filename, row_number, row)
                validate_date_field(issues, filename, row_number, row, "published_at", required=False)
                validate_date_field(issues, filename, row_number, row, "collected_at")

        elif filename == "official_salary.csv":
            for row_number, row in enumerate(rows, start=2):
                if not (row.get("city") or "").strip() or not (row.get("metric") or "").strip():
                    issues.append(issue("error", filename, "missing city or metric", row_number))
                try:
                    as_float(row.get("value"))
                except ValueError:
                    issues.append(issue("error", filename, "official value is not numeric", row_number, "value", row.get("value")))
                validate_evidence(issues, filename, row_number, row)
                validate_url(issues, filename, row_number, row)
                validate_date_field(issues, filename, row_number, row, "published_at", required=False)
                validate_date_field(issues, filename, row_number, row, "collected_at")

        elif filename == "evidence.csv":
            for row_number, row in enumerate(rows, start=2):
                if not (row.get("module") or "").strip() or not (row.get("key") or "").strip():
                    issues.append(issue("error", filename, "missing module or key", row_number))
                validate_evidence(issues, filename, row_number, row)
                validate_url(issues, filename, row_number, row, field="url")
                validate_date_field(issues, filename, row_number, row, "collected_at")
                raw_file = (row.get("raw_file") or "").strip()
                if raw_file and not (project / raw_file).exists():
                    issues.append(issue("warning", filename, "raw_file does not exist", row_number, "raw_file", raw_file))

        elif filename == "city_model.csv":
            for row_number, row in enumerate(rows, start=2):
                if not (row.get("city") or "").strip():
                    issues.append(issue("error", filename, "missing city", row_number, "city"))
                employer_housing = (row.get("employer_housing") or "no").strip().lower()
                if employer_housing not in {"yes", "no", "unknown"}:
                    issues.append(issue("error", filename, "invalid employer_housing", row_number, "employer_housing"))
                share = as_float(row.get("max_employer_share"))
                if share is not None and not (0 <= share <= 1):
                    issues.append(issue("error", filename, "max_employer_share must be between 0 and 1", row_number, "max_employer_share", share))
                for key in ("salary_evidence_level", "rent_evidence_level", "cost_evidence_level"):
                    validate_evidence(issues, filename, row_number, row, field=key)
                if not (row.get("monthly_cash_override") or "").strip():
                    social_text = (row.get("social_security_monthly") or "").strip()
                    fund_text = (row.get("housing_fund_monthly") or "").strip()
                    if not social_text or not fund_text:
                        issues.append(issue(
                            "warning", filename, "tax formula will use 0 for a blank payroll deduction",
                            row_number, "social_security_monthly/housing_fund_monthly",
                        ))
                try:
                    calc = calculate_row(row, lease_months, cutoff)
                except ValueError as exc:
                    issues.append(issue("error", filename, f"cannot calculate row: {exc}", row_number))
                    continue
                if calc["monthly_net_cash"] < 0:
                    issues.append(issue("warning", filename, "negative monthly cash net", row_number, "monthly_net_cash"))
                if calc["rent_burden_pct"] > 0.35:
                    issues.append(issue("warning", filename, "rent exceeds 35% of gross salary", row_number, "rent_burden_pct", calc["rent_burden_pct"]))
                for flag in str(calc["quality_flags"]).split(";"):
                    if flag:
                        issues.append(issue("warning", filename, f"quality flag: {flag}", row_number))

    error_count = sum(1 for item in issues if item["level"] == "error")
    warning_count = sum(1 for item in issues if item["level"] == "warning")
    status = "error" if error_count else ("warning" if warning_count else "ok")
    result = {
        "project": str(project),
        "status": status,
        "error_count": error_count,
        "warning_count": warning_count,
        "files": summaries,
        "issues": issues,
    }
    if report_path:
        report_path = report_path.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"report: {report_path}")
    print(f"validation: {status}; errors={error_count}; warnings={warning_count}")
    for item in issues[:50]:
        location = f" row={item['row']}" if item.get("row") else ""
        field = f" field={item['field']}" if item.get("field") else ""
        print(f"[{item['level']}] {item['dataset']}{location}{field}: {item['message']}")
    if len(issues) > 50:
        print(f"... {len(issues) - 50} more issues; use --report for the full list")
    exit_code = 2 if error_count or (strict and warning_count) else 0
    return exit_code, result


def china_annual_tax(taxable_income: float) -> float:
    """2026 mainland China resident comprehensive-income annual tax table."""
    taxable = max(0.0, taxable_income)
    brackets = (
        (36000, 0.03, 0),
        (144000, 0.10, 2520),
        (300000, 0.20, 16920),
        (420000, 0.25, 31920),
        (660000, 0.30, 52920),
        (960000, 0.35, 85920),
        (math.inf, 0.45, 181920),
    )
    for ceiling, rate, quick_deduction in brackets:
        if taxable <= ceiling:
            return max(0.0, taxable * rate - quick_deduction)
    return 0.0


def worst_evidence(*levels: str) -> str:
    cleaned = [(level or "UNKNOWN").strip().upper() for level in levels]
    if not cleaned:
        return "UNKNOWN"
    valid = [level if level in EVIDENCE_RANK else "UNKNOWN" for level in cleaned]
    return max(valid, key=lambda level: EVIDENCE_RANK[level])


def calculate_row(row: dict[str, Any], lease_months: int = 12,
                   data_cutoff: str = "") -> dict[str, Any]:
    if lease_months <= 0:
        raise ValueError("lease_months must be positive")

    gross = require_float(row, "monthly_gross")
    if gross <= 0:
        raise ValueError("monthly_gross must be positive")
    annual_months = as_float(row.get("annual_months"), 12.0)
    if annual_months is None or not (1 <= annual_months <= 24):
        raise ValueError("annual_months must be between 1 and 24")

    override = as_float(row.get("monthly_cash_override"))
    if override is not None and override < 0:
        raise ValueError("monthly_cash_override must be non-negative")
    social = nonnegative(row, "social_security_monthly")
    fund = nonnegative(row, "housing_fund_monthly")
    special_deduction = nonnegative(row, "special_deduction_monthly")
    annual_gross = gross * annual_months
    if override is not None:
        monthly_cash_avg = override
        annual_tax: float | None = None
        payroll_method = "monthly_cash_override"
    else:
        annual_taxable = max(
            0.0,
            annual_gross
            - social * annual_months
            - fund * annual_months
            - 60000.0
            - special_deduction * 12.0,
        )
        annual_tax = china_annual_tax(annual_taxable)
        annual_cash = annual_gross - social * annual_months - fund * annual_months - annual_tax
        monthly_cash_avg = annual_cash / 12.0
        payroll_method = "china_annualized"

    employer_housing = (str(row.get("employer_housing") or "no")).strip().lower()
    if employer_housing not in {"yes", "no", "unknown"}:
        raise ValueError("employer_housing must be yes/no/unknown")
    governed_housing = employer_housing == "yes"

    if governed_housing:
        rent = 0.0
        deposit_months = 0.0
        advance_months = 0.0
        agency_months = 0.0
        service_fee_monthly = 0.0
        service_fee_upfront = 0.0
    else:
        rent = nonnegative(row, "rent_monthly")
        deposit_months = nonnegative(row, "deposit_months")
        advance_months = nonnegative(row, "advance_rent_months")
        agency_months = nonnegative(row, "agency_fee_months")
        service_fee_monthly = nonnegative(row, "service_fee_monthly")
        service_fee_upfront = nonnegative(row, "service_fee_upfront")

    water = nonnegative(row, "water_monthly")
    electricity = nonnegative(row, "electricity_monthly")
    gas = nonnegative(row, "gas_monthly")
    internet = nonnegative(row, "internet_monthly")
    food = nonnegative(row, "food_monthly")
    commute = nonnegative(row, "commute_monthly")
    other_fixed = nonnegative(row, "other_fixed_monthly")
    other_upfront = nonnegative(row, "other_upfront")

    utilities = water + electricity + gas + internet
    agency_amortized = rent * agency_months / lease_months
    recurring = (
        rent + service_fee_monthly + utilities + food + commute + other_fixed + agency_amortized
    )
    net_cash = monthly_cash_avg - recurring
    net_with_fund = net_cash + fund
    upfront = (
        rent * (deposit_months + advance_months + agency_months)
        + service_fee_upfront
        + other_upfront
    )
    rent_burden = rent / gross

    salary_n = as_float(row.get("salary_sample_n"))
    rent_n = as_float(row.get("rent_sample_n"))
    employer_count = as_float(row.get("employer_count"))
    max_share = as_float(row.get("max_employer_share"))
    overall_evidence = worst_evidence(
        row.get("salary_evidence_level", ""),
        row.get("rent_evidence_level", ""),
        row.get("cost_evidence_level", ""),
    )
    flags: list[str] = []
    if salary_n is not None and salary_n < 10:
        flags.append("salary_n_lt_10")
    elif salary_n is not None and salary_n < 30:
        flags.append("salary_n_lt_30")
    if rent_n is not None and rent_n < 10:
        flags.append("rent_n_lt_10")
    elif rent_n is not None and rent_n < 20:
        flags.append("rent_n_lt_20")
    if employer_count is not None and employer_count < 3:
        flags.append("fewer_than_3_employers")
    if max_share is not None and max_share > 0.5:
        flags.append("single_employer_dominates")
    if overall_evidence in {"C", "D", "UNKNOWN"}:
        flags.append(f"evidence_{overall_evidence.lower()}")
    if rent_burden > 0.35:
        flags.append("rent_burden_gt_35pct")
    if net_cash < 0:
        flags.append("negative_net_cash")
    if payroll_method == "china_annualized" and social == 0 and fund == 0:
        flags.append("payroll_deductions_zero")
    if not any((water, electricity, gas, internet)):
        flags.append("utilities_zero_or_missing")

    return {
        "city": str(row.get("city") or "").strip(),
        "district": str(row.get("district") or "").strip(),
        "job_family": str(row.get("job_family") or "").strip(),
        "scenario": str(row.get("scenario") or "").strip(),
        "data_cutoff": data_cutoff,
        "monthly_gross": round(gross, 2),
        "annual_months": round(annual_months, 2),
        "annual_gross": round(annual_gross, 2),
        "employee_social_monthly": round(social, 2),
        "employee_fund_monthly": round(fund, 2),
        "annual_tax": None if annual_tax is None else round(annual_tax, 2),
        "avg_monthly_cash": round(monthly_cash_avg, 2),
        "rent_monthly": round(rent, 2),
        "agency_amortized_monthly": round(agency_amortized, 2),
        "service_fee_monthly": round(service_fee_monthly, 2),
        "utilities_monthly": round(utilities, 2),
        "food_monthly": round(food, 2),
        "commute_monthly": round(commute, 2),
        "other_fixed_monthly": round(other_fixed, 2),
        "monthly_recurring_cost": round(recurring, 2),
        "monthly_net_cash": round(net_cash, 2),
        "monthly_net_with_fund": round(net_with_fund, 2),
        "rent_burden_pct": round(rent_burden, 4),
        "upfront_cash": round(upfront, 2),
        "employer_housing": employer_housing,
        "payroll_method": payroll_method,
        "salary_sample_n": salary_n,
        "rent_sample_n": rent_n,
        "employer_count": employer_count,
        "max_employer_share": max_share,
        "overall_evidence_level": overall_evidence,
        "quality_flags": ";".join(flags),
        "source_keys": str(row.get("source_keys") or "").strip(),
        "notes": str(row.get("notes") or "").strip(),
    }


OUTPUT_MODEL_COLUMNS = [
    "rank_by_scenario", "city", "district", "job_family", "scenario", "data_cutoff",
    "monthly_gross", "annual_months", "annual_gross", "employee_social_monthly",
    "employee_fund_monthly", "annual_tax", "avg_monthly_cash", "rent_monthly",
    "agency_amortized_monthly", "service_fee_monthly", "utilities_monthly",
    "food_monthly", "commute_monthly", "other_fixed_monthly",
    "monthly_recurring_cost", "monthly_net_cash", "monthly_net_with_fund",
    "rent_burden_pct", "upfront_cash", "employer_housing", "payroll_method",
    "salary_sample_n", "rent_sample_n", "employer_count", "max_employer_share",
    "overall_evidence_level", "quality_flags", "source_keys", "notes",
]


def calculate_project(project: Path, input_path: Path | None = None,
                      output_path: Path | None = None,
                      lease_months: int | None = None) -> int:
    config_path = project / "config.json"
    config: dict[str, Any] = {}
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    model_path = input_path or (project / "data" / "city_model.csv")
    output = output_path or (project / "output" / "city_net_savings.csv")
    if not model_path.exists():
        raise SystemExit(f"model file not found: {model_path}")
    rows = csv_read(model_path)
    effective_lease = lease_months or int(config.get("default_lease_months", 12) or 12)
    cutoff = str(config.get("data_cutoff", ""))

    results: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        try:
            result = calculate_row(row, effective_lease, cutoff)
        except ValueError as exc:
            raise SystemExit(f"row {row_number}: {exc}") from exc
        result["_input_order"] = row_number
        results.append(result)

    by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        scenario_key = result["scenario"] or f"{result['job_family']}|default"
        by_scenario[scenario_key].append(result)
    for group in by_scenario.values():
        group.sort(key=lambda item: item["monthly_net_cash"], reverse=True)
        previous_value: float | None = None
        previous_rank = 0
        for index, item in enumerate(group, start=1):
            value = item["monthly_net_cash"]
            if previous_value is not None and value == previous_value:
                item["rank_by_scenario"] = previous_rank
            else:
                item["rank_by_scenario"] = index
                previous_rank = index
                previous_value = value

    results.sort(key=lambda item: item["_input_order"])
    csv_write(output, OUTPUT_MODEL_COLUMNS, results)
    print(f"wrote: {output} rows={len(results)} lease_months={effective_lease}")
    return 0


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def summarize_jobs(project: Path, input_path: Path | None = None,
                   output_path: Path | None = None) -> int:
    jobs_path = input_path or (project / "data" / "jobs.csv")
    output = output_path or (project / "output" / "jobs_summary.csv")
    if not jobs_path.exists():
        raise SystemExit(f"jobs file not found: {jobs_path}")
    rows = csv_read(jobs_path)
    groups: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(lambda: {
        "jobs": 0,
        "salaries": [],
        "annual_months": [],
        "companies": Counter(),
        "double_weekend": 0,
        "trip_none": 0,
        "trip_occasional": 0,
        "trip_frequent_or_required": 0,
        "trip_unknown": 0,
        "accommodation_provided": 0,
        "negotiable": 0,
        "salary_missing": 0,
    })

    for row in rows:
        included = (row.get("include_in_analysis") or "").strip().lower()
        if included == "no":
            continue
        city = (row.get("city") or "").strip() or "UNKNOWN"
        district = (row.get("district") or "").strip() or "全市/未细分"
        family = (row.get("job_family") or "").strip() or "UNKNOWN"
        group = groups[(city, district, family)]
        group["jobs"] += 1
        company = (row.get("company") or "").strip() or "UNKNOWN"
        group["companies"][company] += 1

        if (row.get("weekend") or "").strip().lower() == "double":
            group["double_weekend"] += 1
        trip = (row.get("trip_requirement") or "").strip().lower()
        if trip == "none":
            group["trip_none"] += 1
        elif trip == "occasional":
            group["trip_occasional"] += 1
        elif trip in {"frequent", "required"}:
            group["trip_frequent_or_required"] += 1
        else:
            group["trip_unknown"] += 1
        if (row.get("accommodation") or "").strip().lower() == "provided":
            group["accommodation_provided"] += 1

        if (row.get("salary_type") or "").strip().lower() == "negotiable":
            group["negotiable"] += 1
            continue
        minimum = as_float(row.get("monthly_min"))
        maximum = as_float(row.get("monthly_max"))
        candidates = [value for value in (minimum, maximum) if value is not None and value > 0]
        if not candidates:
            group["salary_missing"] += 1
            continue
        midpoint = statistics.mean(candidates)
        months = as_float(row.get("annual_months"), 12.0) or 12.0
        if not (1 <= months <= 24):
            months = 12.0
        group["salaries"].append(midpoint * months / 12.0)
        group["annual_months"].append(months)

    output_rows: list[dict[str, Any]] = []
    for (city, district, family), group in sorted(groups.items()):
        salaries: list[float] = group["salaries"]
        companies: Counter[str] = group["companies"]
        total_jobs = group["jobs"]
        max_company_n = max(companies.values()) if companies else 0
        output_rows.append({
            "city": city,
            "district": district,
            "job_family": family,
            "job_count": total_jobs,
            "company_count": len(companies),
            "max_employer_share": round(max_company_n / total_jobs, 4) if total_jobs else 0,
            "salary_n": len(salaries),
            "salary_coverage_pct": round(len(salaries) / total_jobs, 4) if total_jobs else 0,
            "salary_p25_monthly": round(percentile(salaries, 0.25), 2) if salaries else "",
            "salary_median_monthly": round(percentile(salaries, 0.50), 2) if salaries else "",
            "salary_p75_monthly": round(percentile(salaries, 0.75), 2) if salaries else "",
            "median_annual_months": round(statistics.median(group["annual_months"]), 2) if group["annual_months"] else "",
            "double_weekend_n": group["double_weekend"],
            "double_weekend_share": round(group["double_weekend"] / total_jobs, 4) if total_jobs else 0,
            "trip_none_n": group["trip_none"],
            "trip_none_share": round(group["trip_none"] / total_jobs, 4) if total_jobs else 0,
            "trip_occasional_n": group["trip_occasional"],
            "trip_frequent_or_required_n": group["trip_frequent_or_required"],
            "trip_unknown_n": group["trip_unknown"],
            "accommodation_provided_n": group["accommodation_provided"],
            "negotiable_salary_n": group["negotiable"],
            "salary_missing_n": group["salary_missing"],
        })

    columns = [
        "city", "district", "job_family", "job_count", "company_count",
        "max_employer_share", "salary_n", "salary_coverage_pct",
        "salary_p25_monthly", "salary_median_monthly", "salary_p75_monthly",
        "median_annual_months", "double_weekend_n", "double_weekend_share",
        "trip_none_n", "trip_none_share", "trip_occasional_n",
        "trip_frequent_or_required_n", "trip_unknown_n",
        "accommodation_provided_n", "negotiable_salary_n", "salary_missing_n",
    ]
    csv_write(output, columns, output_rows)
    print(f"wrote: {output} groups={len(output_rows)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create, validate, summarize, and calculate graduate city research data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a traceable research project")
    init_parser.add_argument("--output", required=True, help="new project directory")
    init_parser.add_argument("--region", required=True, help="target region")
    init_parser.add_argument("--major", required=True, help="graduate major or job field")
    init_parser.add_argument("--graduate-year", required=True, type=int)
    init_parser.add_argument("--cities", default="", help="comma-separated cities or districts")
    init_parser.add_argument("--demo", action="store_true", help="add a clearly synthetic city_model row")

    validate_parser = subparsers.add_parser("validate", help="validate schemas, dates, duplicates, and quality flags")
    validate_parser.add_argument("--project", required=True)
    validate_parser.add_argument("--strict", action="store_true", help="return nonzero when warnings exist")
    validate_parser.add_argument("--report", help="optional JSON report path")

    jobs_parser = subparsers.add_parser("jobs-summary", help="aggregate normalized job records")
    jobs_parser.add_argument("--project", required=True)
    jobs_parser.add_argument("--input", help="default: <project>/data/jobs.csv")
    jobs_parser.add_argument("--output", help="default: <project>/output/jobs_summary.csv")

    calc_parser = subparsers.add_parser("calculate", help="calculate net cash and upfront cash")
    calc_parser.add_argument("--project", required=True)
    calc_parser.add_argument("--input", help="default: <project>/data/city_model.csv")
    calc_parser.add_argument("--output", help="default: <project>/output/city_net_savings.csv")
    calc_parser.add_argument("--lease-months", type=int, help="agency-fee amortization period")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return init_project(args)
    project = Path(args.project).expanduser().resolve()
    if args.command == "validate":
        report = Path(args.report).expanduser().resolve() if args.report else None
        exit_code, _ = validate_project(project, strict=args.strict, report_path=report)
        return exit_code
    if args.command == "jobs-summary":
        input_path = Path(args.input).expanduser().resolve() if args.input else None
        output_path = Path(args.output).expanduser().resolve() if args.output else None
        return summarize_jobs(project, input_path, output_path)
    if args.command == "calculate":
        input_path = Path(args.input).expanduser().resolve() if args.input else None
        output_path = Path(args.output).expanduser().resolve() if args.output else None
        return calculate_project(project, input_path, output_path, args.lease_months)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
