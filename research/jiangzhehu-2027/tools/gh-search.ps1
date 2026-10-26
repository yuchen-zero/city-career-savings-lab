$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$outDir = Join-Path $root 'data'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$queries = @(
    '薪资 爬虫',
    '工资 数据分析',
    'salary china data',
    '应届生 就业 数据',
    '房租 数据',
    '链家 爬虫 租房',
    'cost of living china',
    '招聘 数据 分析 boss直聘',
    '外卖 数据 爬虫',
    'jobui',
    '城市 房租 爬虫',
    '电气工程 就业'
)

$all = @()
foreach ($q in $queries) {
    $enc = [uri]::EscapeDataString($q)
    $json = gh api "search/repositories?q=$enc&sort=stars&order=desc&per_page=6" 2>&1
    $text = ($json -join "`n")
    if ($text -notmatch '^\s*\{') {
        Write-Output "FAIL | $q | $text"
        continue
    }
    $obj = $text | ConvertFrom-Json
    Write-Output "=== $q | total=$($obj.total_count)"
    foreach ($it in $obj.items) {
        $desc = ($it.description -replace '\s+', ' ')
        Write-Output ("  {0} | stars={1} | updated={2} | {3}" -f $it.full_name, $it.stargazers_count, ($it.updated_at -replace 'T.*', ''), $desc)
        $all += [pscustomobject]@{ query = $q; repo = $it.full_name; stars = $it.stargazers_count; lang = $it.language; updated = $it.updated_at; desc = $desc; url = $it.html_url }
    }
    Start-Sleep -Milliseconds 800
}

$all | ConvertTo-Json -Depth 4 | Out-File -FilePath (Join-Path $outDir 'github-repos.json') -Encoding UTF8
Write-Output 'GITHUB SEARCH COMPLETE'
