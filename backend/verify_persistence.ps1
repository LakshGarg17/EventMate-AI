$ErrorActionPreference = "Stop"

$tempDbPath = "d:/Virtual Promptwars/EventMate AI/backend/verify_persistence.db"
$tempDbUrl = "sqlite:///$tempDbPath"

if (Test-Path "d:\Virtual Promptwars\EventMate AI\backend\verify_persistence.db") {
    Remove-Item "d:\Virtual Promptwars\EventMate AI\backend\verify_persistence.db" -Force
}

$env:DATABASE_URL = $tempDbUrl

Write-Host "--- Persistence Check: Phase 1 (Create Data & Stop Backend) ---"
$proc1 = Start-Process -FilePath "d:\Virtual Promptwars\EventMate AI\backend\.venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" -WorkingDirectory "d:\Virtual Promptwars\EventMate AI\backend" -PassThru -NoNewWindow

$eventId = $null
$expenseId = $null
$taskId = $null

try {
    # Wait for startup
    $retries = 20
    while ($retries -gt 0) {
        try {
            $h = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
            if ($h.status -eq "ok") { break }
        } catch {
            Start-Sleep -Milliseconds 500
            $retries--
        }
    }

    # 1. Create Event
    $eventPayload = @{
        name = "Persistent Wedding Celebration"
        event_type = "Wedding"
        event_date = "2026-12-25"
        location = "Taj Palace"
        guest_count = 350
        total_budget = "500000.00"
        currency = "INR"
    } | ConvertTo-Json

    $event = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events" -Method Post -Body $eventPayload -ContentType "application/json"
    $eventId = $event.id
    Write-Host "Created Event: $($event.name) with ID: $eventId"

    # 2. Add Expense
    $expPayload = @{
        description = "Royal Floral Canopy"
        estimated_amount = "75000.00"
        actual_amount = "70000.00"
        payment_status = "Partial"
    } | ConvertTo-Json
    $exp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/$eventId/expenses" -Method Post -Body $expPayload -ContentType "application/json"
    $expenseId = $exp.id
    Write-Host "Created Expense: $($exp.description) ($($exp.estimated_amount)) with ID: $expenseId"

    # 3. Add Task
    $taskPayload = @{
        title = "Final Dress Fitting"
        category = "Attire"
        priority = "High"
        due_date = "2026-12-10"
        status = "In Progress"
    } | ConvertTo-Json
    $tsk = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/$eventId/tasks" -Method Post -Body $taskPayload -ContentType "application/json"
    $taskId = $tsk.id
    Write-Host "Created Task: $($tsk.title) with ID: $taskId"

} finally {
    Write-Host "Stopping Backend Server (Phase 1)..."
    Stop-Process -Id $proc1.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Host "`n--- Persistence Check: Phase 2 (Restart Backend with Same DB File) ---"
$proc2 = Start-Process -FilePath "d:\Virtual Promptwars\EventMate AI\backend\.venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" -WorkingDirectory "d:\Virtual Promptwars\EventMate AI\backend" -PassThru -NoNewWindow

try {
    # Wait for restart
    $retries = 20
    while ($retries -gt 0) {
        try {
            $h = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
            if ($h.status -eq "ok") { break }
        } catch {
            Start-Sleep -Milliseconds 500
            $retries--
        }
    }

    # Fetch event and verify data is still there
    $fetchedEvent = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/$eventId" -Method Get
    Write-Host "Verified Event Still Exists: $($fetchedEvent.name) ($($fetchedEvent.total_budget) $($fetchedEvent.currency))"

    if ($fetchedEvent.name -ne "Persistent Wedding Celebration") {
        throw "Event name mismatch after restart!"
    }
    if ($fetchedEvent.expenses.Count -ne 1 -or $fetchedEvent.expenses[0].id -ne $expenseId) {
        throw "Expense was lost after server restart!"
    }
    if ($fetchedEvent.tasks.Count -ne 1 -or $fetchedEvent.tasks[0].id -ne $taskId) {
        throw "Task was lost after server restart!"
    }

    Write-Host "Verified Expense Still Exists: $($fetchedEvent.expenses[0].description), Paid: $($fetchedEvent.expenses[0].actual_amount)"
    Write-Host "Verified Task Still Exists: $($fetchedEvent.tasks[0].title), Status: $($fetchedEvent.tasks[0].status)"

    Write-Host "`nPERSISTENCE VERIFICATION PASSED: SQLite data completely survived server restart!"
} finally {
    Write-Host "Cleaning up Phase 2..."
    Stop-Process -Id $proc2.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    if (Test-Path "d:\Virtual Promptwars\EventMate AI\backend\verify_persistence.db") {
        Remove-Item "d:\Virtual Promptwars\EventMate AI\backend\verify_persistence.db" -Force -ErrorAction SilentlyContinue
    }
}
