# Render a DOCX to page PNGs on Windows.
# Word COM exports the PDF, Poppler rasterises each page.
param(
    [Parameter(Mandatory = $true)][string]$DocxPath,
    [Parameter(Mandatory = $true)][string]$OutputDir,
    [int]$Dpi = 110
)

$ErrorActionPreference = 'Stop'

$docx = (Resolve-Path -LiteralPath $DocxPath).Path
if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
}
$outDir = (Resolve-Path -LiteralPath $OutputDir).Path
$stem = [System.IO.Path]::GetFileNameWithoutExtension($docx)
$pdf = Join-Path $outDir ("$stem.pdf")

$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($docx, $false, $true)
    $doc.ExportAsFixedFormat($pdf, 17)
    $doc.Close(0)
    $doc = $null
}
finally {
    if ($word) {
        $word.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

if (-not (Test-Path -LiteralPath $pdf)) {
    throw "PDF export failed: $pdf"
}

Get-ChildItem -LiteralPath $outDir -Filter 'page-*.png' -ErrorAction SilentlyContinue |
    Remove-Item -Force

& pdftoppm -png -r $Dpi $pdf (Join-Path $outDir 'page')

$pages = Get-ChildItem -LiteralPath $outDir -Filter 'page-*.png' | Sort-Object Name
Write-Output ("pdf: {0} ({1} bytes)" -f $pdf, (Get-Item -LiteralPath $pdf).Length)
foreach ($page in $pages) {
    Write-Output ("{0}  {1} bytes" -f $page.Name, $page.Length)
}
