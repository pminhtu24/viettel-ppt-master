param(
    [Parameter(Mandatory = $true)]
    [string]$PptxPath
)

$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $PptxPath).Path
$smokePath = Join-Path ([IO.Path]::GetTempPath()) (([IO.Path]::GetRandomFileName()) + '.pptx')
Copy-Item -LiteralPath $source -Destination $smokePath

$powerPoint = $null
$presentation = $null
try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $presentation = $powerPoint.Presentations.Open($smokePath, $false, $false, $false)

    $fontRows = @{}
    for ($index = 1; $index -le $presentation.Fonts.Count; $index++) {
        $font = $presentation.Fonts.Item($index)
        $fontRows[$font.Name] = $font.Embedded
    }
    $magistral = @($fontRows.Keys | Where-Object { $_ -match '^FS Magistral (Book|Medium|Bold)$' })
    if ($magistral.Count -eq 0) {
        throw 'PowerPoint did not expose any embedded FS Magistral static face.'
    }
    foreach ($name in $magistral) {
        if (-not $fontRows[$name]) {
            throw "PowerPoint reports that $name is not embedded."
        }
    }

    $probeFace = $magistral[0]
    $probe = $presentation.Slides.Item(1).Shapes.AddTextbox(1, 0, 0, 10, 10)
    $probe.Name = 'CodexFontSmokeProbe'
    $probe.TextFrame.TextRange.Text = 'font-smoke'
    $probe.TextFrame.TextRange.Font.Name = $probeFace
    $presentation.Save()
    $presentation.Close()
    [Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null
    $presentation = $null

    $presentation = $powerPoint.Presentations.Open($smokePath, $false, $false, $false)
    $reopened = @()
    for ($index = 1; $index -le $presentation.Fonts.Count; $index++) {
        $reopened += $presentation.Fonts.Item($index).Name
    }
    foreach ($name in $magistral) {
        if ($name -notin $reopened) {
            throw "$name disappeared after PowerPoint save/reopen."
        }
    }
    $reopenedProbe = $presentation.Slides.Item(1).Shapes.Item('CodexFontSmokeProbe')
    if ($reopenedProbe.TextFrame.TextRange.Font.Name -ne $probeFace) {
        throw "PowerPoint substituted $probeFace after editing and save/reopen."
    }

    Write-Host "PASS: PowerPoint opened, edited, saved, and reopened embedded FS Magistral faces: $($magistral -join ', ')"
}
finally {
    if ($presentation) {
        $presentation.Close()
        [Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) | Out-Null
    }
    if ($powerPoint) {
        $powerPoint.Quit()
        [Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint) | Out-Null
    }
    Remove-Item -LiteralPath $smokePath -Force -ErrorAction SilentlyContinue
}
