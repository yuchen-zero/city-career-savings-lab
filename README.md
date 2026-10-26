# city-career-savings-lab

这是一个公开研究快照，包含可复用的 `city-career-savings-lab` Codex Skill，以及 2027 届电气工程及其自动化本科应届生的江浙沪城市调研和上海临港深化研究产物。技能从岗位、生活成本和税费出发，回答“去哪个城市工作、一个月能攒下多少钱”。

## 仓库内容

```text
skill/city-career-savings-lab/
  可复用的城市职业、每月净结余与单岗位核验 Skill

research/jiangzhehu-2027/
  江浙沪 25 城市比较数据、正式报告、问卷与采集/构建脚本

research/lingang-2027/
  上海浦东临港新片区核心区深化研究、标准化数据与正式交付物
```

## 正式交付物

### 江浙沪 25 城市

- `research/jiangzhehu-2027/outputs/江浙沪电气应届生就业城市调研报告.docx`
- `research/jiangzhehu-2027/outputs/江浙沪电气应届生调研数据总表.xlsx`
- `research/jiangzhehu-2027/outputs/江浙沪电气应届生净结余测算.html`

### 上海临港深化版

- `research/lingang-2027/outputs/2027届_电气工程及其自动化_临港_城市净结余报告_2026-10-26.docx`
- `research/lingang-2027/outputs/2027届_电气工程及其自动化_临港_数据总表_2026-10-26.xlsx`
- `research/lingang-2027/outputs/2027届_电气工程及其自动化_临港_参数化测算_2026-10-26.html`

## 数据使用边界

- 招聘薪资是招聘广告值，不是员工实际工资或户口所在地工资中位数。
- 房租多为挂牌或页面展示价，不等同于成交价。
- 餐饮、通勤、水电气网等字段分为官方单价、平台观察和透明模型假设，不能混写为实测账单。
- 未知的双休、出差、住宿和专业资格不会被推断为“满足”或“不满足”。
- 江浙沪宽口径数据中的部分城市成本为模型推算；原始表内的“房租性质”等字段保留该区别。
- 临港研究的截止日为 2026-10-26；核心区只取得 6 条 2027 届本科相邻岗位、3 家企业，公开薪资为 0 条，因此 8,000 至 15,000 元只是现金压力测试。

## 证据与复现

`data/`、`evidence/` 和 `outputs/` 保留标准化数据、分析结果、来源 URL 与证据等级。构建脚本保留在各自的 `tools/` 或 `scripts/` 目录；运行依赖未随仓库提交，需要按脚本导入重新安装。

为控制仓库体积并避免保存会话态内容，以下文件未提交：

- BOSS、智联、租房平台等页面的完整原始 HTML 快照；
- 浏览器 Cookie、账号密码、验证码和登录态文件；
- `.venv`、`node_modules`、Python/Node 缓存；
- `*.inspect.ndjson`、PDF/PNG 渲染中间件和临时 QA 文件；
- 从 GitHub 克隆的第三方采集器源码。研究只保留本项目自己的脚本、归一化数据和来源信息。

第三方网站内容、招聘广告和图片仍受各自权利与平台条款约束。本仓库是研究归档，不代表对第三方内容再许可。

## Skill 用法

在支持 Skills 的 Codex 环境中，将 `skill/city-career-savings-lab` 放回个人的 skills 目录，或直接阅读其中的 `SKILL.md`。技能支持两种模式：

1. 城市/区县批量的岗位、工资、房租、生活成本和净结余调研；
2. 按企业、岗位名、岗位链接或岗位编号核验一个具体岗位。

单岗位模式的详细流程见 `skill/city-career-savings-lab/references/job-lookup.md`。

技能还提供一个自包含 HTML 决策页模板和生成命令，断网也能打开与切换敏感参数：

```text
python scripts/research_workbench.py dashboard --project <项目目录> --title "<报告标题>" --output <项目目录>/output/<报告标题>.html
```

## 许可证与使用范围

- 原创源代码、脚本、Skill 说明、文档和 HTML 模板采用 [MIT License](./LICENSE)。
- 对 Yuchen-zero 拥有可保护权利的原创数据选择、结构、注释和派生汇总表，采用 [CC BY 4.0](./DATA_LICENSE.md)。
- 招聘广告、招聘平台内容、租房房源、政府原始文件、第三方仓库内容和商标等不在这两项授权范围内，继续适用原来源条款。详见 [NOTICE](./NOTICE)。

转载或再使用数据时，请保留来源链接、数据截止日、许可证说明和所做的修改。第三方内容的授权状态必须逐项回到原始来源核对。
