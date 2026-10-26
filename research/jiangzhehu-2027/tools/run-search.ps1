$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$outDir = Join-Path $root 'data'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'

function Clean-Html([string]$html) {
    if (-not $html) { return '' }
    $t = $html -replace '(?s)<script.*?</script>', ' '
    $t = $t -replace '(?s)<style.*?</style>', ' '
    $t = $t -replace '(?s)<!--.*?-->', ' '
    $t = $t -replace '<[^>]+>', ' '
    $t = [System.Net.WebUtility]::HtmlDecode($t)
    $t = $t -replace '[ \t\u00a0]+', ' '
    $t = $t -replace '(\r?\n\s*){2,}', "`n"
    return $t.Trim()
}

function Get-Page([string]$url, [int]$timeout = 20) {
    $raw = curl.exe -sS -m $timeout -L -A $UA -H 'Accept-Language: zh-CN,zh;q=0.9' $url 2>&1
    return ($raw -join "`n")
}

function Search-Web([string]$query, [string]$tag) {
    $enc = [uri]::EscapeDataString($query)
    $text = ''
    $src = ''
    foreach ($cand in @(
        @{ n = 'bing';   u = "https://cn.bing.com/search?q=$enc&setlang=zh-CN&mkt=zh-CN&count=20" },
        @{ n = 'sogou';  u = "https://www.sogou.com/web?query=$enc" },
        @{ n = 'toutiao'; u = "https://so.toutiao.com/search?keyword=$enc" }
    )) {
        $html = Get-Page $cand.u
        $t = Clean-Html $html
        if ($t.Length -gt 800) { $text = $t; $src = $cand.n; break }
        Start-Sleep -Milliseconds 400
    }
    if (-not $text) { $text = 'NO_RESULT'; $src = 'none' }
    if ($text.Length -gt 9000) { $text = $text.Substring(0, 9000) + "`n...[TRUNCATED len=$($text.Length)]" }
    $file = Join-Path $outDir "$tag.txt"
    "### QUERY: $query`n### SOURCE: $src`n### LEN: $($text.Length)`n$text" | Out-File -FilePath $file -Encoding UTF8
    Write-Output "$tag | $src | $($text.Length)"
    Start-Sleep -Milliseconds 700
}

$queries = [ordered]@{
    'salary-01-shanghai'        = '上海 电气工程及其自动化 应届生 起薪 薪资 2026'
    'salary-02-suzhou'          = '苏州 电气工程师 应届生 薪资 2026'
    'salary-03-nanjing'         = '南京 电气工程师 应届生 薪资 2026'
    'salary-04-wuxi'            = '无锡 电气工程师 应届生 薪资 2026'
    'salary-05-changzhou'       = '常州 电气工程师 薪资 应届生 2026'
    'salary-06-nantong'         = '南通 电气工程师 薪资 应届生 2026'
    'salary-07-xuzhou'          = '徐州 电气工程师 薪资 待遇 2026'
    'salary-08-yangzhou-zhenjiang' = '扬州 镇江 电气工程师 工资 待遇 2026'
    'salary-09-taizhou-yancheng'   = '泰州 盐城 电气工程师 工资 待遇'
    'salary-10-subei-small'        = '淮安 连云港 宿迁 电气工程师 工资 待遇'
    'salary-11-hangzhou'        = '杭州 电气工程师 应届生 薪资 2026'
    'salary-12-ningbo'          = '宁波 电气工程师 应届生 薪资 2026'
    'salary-13-wenzhou'         = '温州 电气工程师 应届生 薪资 2026'
    'salary-14-jiaxing'         = '嘉兴 电气工程师 薪资 应届生 2026'
    'salary-15-shaoxing'        = '绍兴 电气工程师 薪资 待遇 2026'
    'salary-16-jinhua'          = '金华 电气工程师 薪资 待遇 2026'
    'salary-17-taizhou-zj'      = '台州 电气工程师 薪资 待遇 2026'
    'salary-18-huzhou'          = '湖州 电气工程师 薪资 待遇 2026'
    'salary-19-zhoushan-quzhou-lishui' = '舟山 衢州 丽水 电气工程师 工资 待遇'
    'salary-20-jobui-ee'        = '职友集 电气工程及其自动化 本科 应届生 工资 多少'
    'salary-21-jobui-nanjing'   = '职友集 南京 电气工程师 工资 待遇'
    'salary-22-jobui-suzhou'    = '职友集 苏州 电气工程师 工资 待遇'
    'salary-23-jobui-hangzhou'  = '职友集 杭州 电气工程师 工资 待遇'
    'salary-24-sgcc-js-zj'      = '国家电网 江苏 浙江 上海 电力公司 待遇 应届生 年薪 转正'
    'salary-25-automation-firms' = '汇川技术 台达 阳光电源 应届生 电气 薪资 offer'
    'salary-26-mycos'           = '麦可思 2026 中国大学生就业报告 本科 平均月收入'
    'salary-27-province-avg'    = '江苏 浙江 上海 应届生 平均起薪 2026 高校毕业生'
    'salary-28-total-package'   = '应届生 总包 年包 税前 税后 到手 五险一金 公积金 计算'
    'rent-01-shanghai'      = '上海 平均租金 2026 元 每平米 合租 单间 一居室'
    'rent-02-nanjing'       = '南京 平均租金 2026 合租 单间 一居室 多少钱'
    'rent-03-suzhou'        = '苏州 平均租金 2026 合租 单间 一居室'
    'rent-04-hangzhou'      = '杭州 平均租金 2026 合租 单间 一居室'
    'rent-05-ningbo'        = '宁波 平均租金 2026 合租 单间'
    'rent-06-wuxi-changzhou'= '无锡 常州 平均租金 2026 单间 合租'
    'rent-07-wenzhou-jiaxing' = '温州 嘉兴 平均租金 2026 单间'
    'rent-08-shaoxing-jinhua-taizhou-huzhou' = '绍兴 金华 台州 湖州 租金 平均 单间'
    'rent-09-nantong-yangzhou-xuzhou' = '南通 扬州 徐州 平均租金 单间 2026'
    'rent-10-subei-zhexi'   = '盐城 淮安 连云港 宿迁 衢州 丽水 舟山 租金 平均'
    'rent-11-city-rank'     = '中国房价行情网 2026 城市租金排行 每平米 月租'
    'rent-12-rent-income'   = '长三角 租金收入比 2026 贝壳研究院 租房报告'
    'food-01-takeout-avg'   = '外卖 客单价 平均 一单多少钱 2026'
    'food-02-meituan'       = '美团 外卖 平均订单价格 报告 2025 2026'
    'food-03-shanghai'      = '上海 外卖 人均 一顿饭 多少钱 2026'
    'food-04-hangzhou-nanjing' = '杭州 南京 外卖 人均消费 一顿饭 多少钱'
    'food-05-city-compare'  = '各城市 餐饮 人均消费 对比 2026 一二三线'
    'food-06-monthly-food'  = '一二线城市 每月 吃饭 开销 多少钱 2026'
    'misc-01-js-talent'     = '江苏 高校毕业生 租房补贴 生活补贴 政策 2026'
    'misc-02-zj-talent'     = '浙江 高校毕业生 生活补贴 租房补贴 落户 2026'
    'misc-03-sh-hukou'      = '上海 应届生 落户 政策 2026 评分 双一流'
    'misc-04-ee-employers'  = '江浙沪 电气自动化 龙头企业 分布 新能源 光伏 储能 招聘'
}

foreach ($k in $queries.Keys) { Search-Web $queries[$k] $k }

Write-Output 'SEARCH PHASE COMPLETE'
