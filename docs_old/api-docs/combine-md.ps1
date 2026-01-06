# combine-md.ps1
# Combines all .md files in the current directory into README.md,
# ordered by Date Modified (oldest -> newest).

$ErrorActionPreference = "Stop"

$outFile = Join-Path -Path (Get-Location) -ChildPath "README.md"

# Get .md files, excluding README.md itself
$files = Get-ChildItem -File -Filter "*.md" |
  Where-Object { $_.Name -ne "README.md" } |
  Sort-Object LastWriteTime  # oldest -> newest

# Build output in memory (preserves file content exactly)
$sb = New-Object System.Text.StringBuilder

$null = $sb.AppendLine("# Combined Markdown")
$null = $sb.AppendLine()
$null = $sb.AppendLine("> Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$null = $sb.AppendLine()

foreach ($f in $files) {
  $null = $sb.AppendLine("## $($f.Name)")
  $null = $sb.AppendLine()
  $null = $sb.AppendLine("*(Modified: $($f.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')))*")
  $null = $sb.AppendLine()

  # Read file raw so we don't alter line endings within the content more than necessary
  $content = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8
  $null = $sb.AppendLine($content.TrimEnd())  # avoid runaway extra blank lines
  $null = $sb.AppendLine()
  $null = $sb.AppendLine("---")
  $null = $sb.AppendLine()
}

# Write as UTF-8 (no BOM) so Markdown renders nicely on GitHub
[System.IO.File]::WriteAllText($outFile, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))

Write-Host "Wrote $outFile from $($files.Count) files (oldest -> newest)."
