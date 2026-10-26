# 数据契约

本文件定义跨地区项目的最小字段、证据等级、清洗口径和计算含义。字段名保持英文，报告标题和说明可用当地语言。缺少的数值留空，不使用 `0`、`待定`、`N/A` 混作同一个含义；原因写入 `notes` 或证据台账。

## 证据等级

| 等级 | 适用证据 | 典型用途 |
|---|---|---|
| A | 政府统计、统计公报、税务/社保/公积金规则、公开方法可核验的官方指数 | 作为制度口径和外部分母 |
| B | 带原始页面和采集日期的大样本招聘/租房平台数据、行业协会或方法透明的市场数据 | 岗位、挂牌价和平台行情主数据 |
| C | 小于 30 条岗位或小于 10 条租房的样本、单一企业主导、模型估算、多个 B 级来源的派生值 | 辅助判断、敏感性分析 |
| D | 单条个人晒薪、社交媒体转述、公司宣传、无法回溯的聚合转载 | 只作线索，不支撑结论 |

证据等级描述的是“该数字对本问题的可信度”，不是来源名气。一个 B 级大平台的少量搜索结果仍可能只有 C 级；一次官方统计中的不同指标也不能自动互相替代。

## 项目结构

`init` 生成以下结构：

```text
project/
  config.json
  data/
    jobs.csv
    city_model.csv
    rent.csv
    living_costs.csv
    payroll_assumptions.csv
    official_salary.csv
    evidence.csv
  sources/raw/
  output/
```

`sources/raw/` 保存原始 JSON、HTML、CSV、截图或 PDF；文件名包含模块、城市、查询词和日期。不要把登录 Cookie、密码、手机号或个人聊天记录保存进项目。

## `jobs.csv`

每条记录是一个可分析职位，不得把搜索结果数当作岗位数。

| 字段 | 含义与要求 |
|---|---|
| `job_id` | 平台职位 ID 或稳定哈希；同一职位只保留一条 |
| `source` | 平台/企业官网名称 |
| `source_url` | 原始职位链接 |
| `collected_at` | 采集日期，建议 `YYYY-MM-DD` |
| `evidence_level` | 该条职位及薪资字段的证据等级 `A/B/C/D` |
| `search_keyword`、`search_page` | 用于评估覆盖和重复，不只保留结果 |
| `city`、`district` | 标准化城市和区县；不能用“附近”代替 |
| `company`、`company_id` | 企业名；能取得统一 ID 时填写 |
| `job_title`、`job_family` | 原标题，以及预先定义的目标岗位族 |
| `monthly_min`、`monthly_max` | 统一到税前月薪的数值；固定薪资两者相等 |
| `salary_text` | 原始薪资文字，保留“年薪/日薪/面议/13 薪”等证据 |
| `annual_months` | 年发月数；未知留空，分析时明确按 12 还是排除 |
| `education`、`experience` | 原始要求及标准化值 |
| `salary_type` | `monthly`、`annualized`、`hourly`、`negotiable` 之一 |
| `weekend` | `double`、`single`、`rotating`、`unknown` |
| `trip_requirement` | `none`、`occasional`、`frequent`、`required`、`unknown` |
| `accommodation` | `provided`、`subsidy`、`none`、`unknown` |
| `include_in_analysis` | `yes` 或 `no`；不删除排除记录，便于审计 |
| `exclusion_reason` | 被排除的具体原因 |
| `notes` | 关键口径和歧义 |

清洗规则：

1. 先按用户地区、届别、学历、岗位族和排除项过滤，再统计薪资。
2. 合并同一 `job_id`；不同平台转载若无法确认是同一职位，保留但记录 `duplicate_group`（可加入备注）。
3. “8-20K”这类宽区间不能只取最高值；汇总用区间中点，同时报告区间宽度、四分位和样本数。
4. “面议”不进入薪资中位数，但保留在岗位供给和条件统计中。
5. 薪资为税前广告值。无法证明实际到手值时，不得写成“真实工资”或“员工中位数”。
6. 岗位标签 `none` 只表示招聘页明确写了不需要出差；`unknown` 不等于 `none`。
7. 学历、经验、行业、公司规模等筛选条件必须和薪资结果一起报告。

## `rent.csv`

| 字段 | 含义与要求 |
|---|---|
| `city`、`district` | 城市及区县；能到街道/商圈时额外记录，但不要伪造 |
| `rent_mode` | `share`（合租单间）、`whole`（整租一套）、`brand`（品牌公寓）等 |
| `area_sqm` | 整租按套内/建筑面积，合租按可比较房间口径记录 |
| `monthly_rent` | 实际挂牌或成交月租；不得把押金混入月租 |
| `listing_count` | 形成该数值的有效挂牌数或样本数 |
| `deposit_months`、`advance_rent_months` | 押金月数、签约时预付的总月数；`押一付三` 对应 `1` 和 `3` |
| `agency_fee_months` | 租客承担的中介费月数；房东承担时为 `0` 并在备注说明 |
| `service_fee_monthly`、`service_fee_upfront` | 月度服务费、一次性服务费，分开记录 |
| `station_distance_km` | 与通勤假设相关的距离/步行时间，可留空 |
| `source_name`、`source_url` | 原始挂牌页或平台口径页面 |
| `published_at`、`collected_at` | 发布日和采集日 |
| `evidence_level`、`notes` | 证据等级、面积/装修/楼层/板块范围等 |

合租和整租必须分成不同情景。城市均价可以用于初筛，但不能替代区县和目标户型；模型估算要与实测样本分栏，不能合并成“实测”。

## `living_costs.csv`

至少保留：

`city,district,food_monthly,commute_monthly,water_monthly,electricity_monthly,gas_monthly,internet_monthly,other_fixed_monthly,source_url,published_at,collected_at,evidence_level,notes`

餐饮优先使用同口径的月度篮子或官方支出推算；若用官方全体居民食品烟酒支出推算单身青年，需说明覆盖差异并向独立餐饮样本校准。水电气网按当地阶梯价格、季节用量和整租/合租分摊假设计算，不能只写“水电约 100 元”而不留依据。

## `payroll_assumptions.csv`

至少保留：

`city,year,employee_social_rate,employee_fund_rate,social_security_monthly,housing_fund_monthly,special_deduction_monthly,tax_model,source_url,published_at,collected_at,evidence_level,notes`

优先填写当地当年员工个人缴费比例、缴费基数和公积金比例。比例必须保留小数形式（例如 10.5% 写 `0.105`），月扣款和比例同时存在时优先使用明确的月扣款。目标城市的规则不同，不得直接套用其他城市或上一年的比例。

## `official_salary.csv`

至少保留：

`city,district,metric,year,period,value,unit,sample_n,source_name,source_url,published_at,collected_at,evidence_level,notes`

官方工资/收入是外部分母，不等于目标岗位的真实起薪。必须写清是城镇非私营单位、私营单位、全行业、特定职业、全体居民收入还是招聘市场指标。遇到发布期和统计期不同，分别记录。

## `city_model.csv`

一行代表一个分析情景，例如“上海-浦东-电气设计-合租-直租”。字段：

```text
city,district,job_family,scenario,
monthly_gross,annual_months,
social_security_monthly,housing_fund_monthly,special_deduction_monthly,
monthly_cash_override,
rent_monthly,deposit_months,advance_rent_months,agency_fee_months,
service_fee_monthly,service_fee_upfront,
water_monthly,electricity_monthly,gas_monthly,internet_monthly,
food_monthly,commute_monthly,other_fixed_monthly,other_upfront,
employer_housing,salary_sample_n,rent_sample_n,employer_count,max_employer_share,
salary_evidence_level,rent_evidence_level,cost_evidence_level,source_keys,notes
```

`monthly_cash_override` 是扣除个税和员工社保/公积金后的现金（不含公积金账户），可直接用于本地精确工资单；设置后不再用税率公式重算现金。`annual_months` 表示一年发放月数，计算月均收入时会年化再除以 12。

`advance_rent_months` 是签约时预付的总月数，不是“首月之后再加几个月”。例如押一付三：押金 `1`、预付租金 `3`，首月现金中的房租部分为 4 个月租金。中介费一次性支出为 `agency_fee_months × rent_monthly`，再按月租期摊销到月度结余；若实际为房东全额承担，填 `0`。

## `evidence.csv`

至少保留：

`module,key,source_name,source_type,url,published_at,collected_at,evidence_level,scope,raw_file,notes`

`key` 与 `city`、`district`、`job_family` 或数据文件名对应。报告中的所有关键来源都应能在此台账找到；派生指标在 `notes` 写公式或计算脚本版本。

## 核心计算

### 中国居民综合所得个税

在 `tax_model=china_annualized` 且没有 `monthly_cash_override` 时：

```text
annual_taxable = max(0,
  monthly_gross × annual_months
  - social_security_monthly × annual_months
  - housing_fund_monthly × annual_months
  - 60,000
  - special_deduction_monthly × 12)

annual_tax = 按年度综合所得税率表计算
monthly_cash_avg = (年税前收入 - 社保 - 公积金 - 年度个税) / 12
```

脚本使用 2026 年中国大陆居民综合所得年度税率表作为可替换的计算器，不替代目标城市的工资单、专项附加扣除或非居民/外籍人员规则。若规则或年度不同，填 `monthly_cash_override` 或在本地修订 `calculate_row`，并在报告中声明。

### 月度与首月

```text
utilities_monthly = water + electricity + gas + internet
agency_amortized = rent × agency_fee_months / lease_months
recurring_monthly = rent + service_fee_monthly + utilities_monthly
                    + food + commute + other_fixed
                    + agency_amortized
net_cash_monthly = monthly_cash_avg - recurring_monthly
net_with_fund_monthly = net_cash_monthly + housing_fund_monthly
upfront_cash = rent × (deposit_months + advance_rent_months + agency_fee_months)
               + service_fee_upfront + other_upfront
```

`lease_months` 默认 12，只在 `calculate --lease-months` 或配置中改变。公司提供住宿时，租金和租房渠道费按 0 处理，但餐饮、通勤、水电网等仍按实际假设计入，除非另有记录。

## 结果解释

- `salary_p25/median/p75` 是广告薪资中点（年发月数年化）的分位数，不是劳动合同到手工资。
- `employer_concentration` 是单一企业职位数占该组职位数的比例；超过 0.5 时只能视为企业样本。
- `rent_burden_pct = rent / monthly_gross`，不得用“房租 / 税后收入”与别人的同名字段直接比较。
- 排名差异小于数据误差、样本不足或证据只有 C/D 时，写“无法区分”，不要强行制造第一。
- 负净结余、首月现金超过可承担能力、必须合租才能为正等结果都要明确展示，不能用平均值掩盖。
