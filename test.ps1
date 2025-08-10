$resp = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/process -ContentType 'application/json' -Body '{"url":"https://example.com","prompt":"List headings"}'
$tid = $resp.task_id
Write-Host "Task ID: $tid"
do {
  $s = Invoke-RestMethod -Uri ("http://localhost:8000/api/v1/status/{0}" -f $tid)
  $s | ConvertTo-Json -Depth 5
  if ($s.status -in @("PENDING","IN_PROGRESS")) { Start-Sleep -Seconds 3 }
} while ($s.status -in @("PENDING","IN_PROGRESS"))
Invoke-RestMethod -Uri ("http://localhost:8000/api/v1/result/{0}" -f $tid) | ConvertTo-Json -Depth 5