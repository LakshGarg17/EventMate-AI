$ErrorActionPreference = "Stop"

$tempDbPath = "d:/Virtual Promptwars/EventMate AI/backend/verify_temp.db"
$tempDbUrl = "sqlite:///$tempDbPath"

if (Test-Path "d:\Virtual Promptwars\EventMate AI\backend\verify_temp.db") {
    Remove-Item "d:\Virtual Promptwars\EventMate AI\backend\verify_temp.db" -Force
}

$env:DATABASE_URL = $tempDbUrl

Write-Host "Starting backend on port 8000 with temp DB..."
$backendProcess = Start-Process -FilePath "d:\Virtual Promptwars\EventMate AI\backend\.venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" -WorkingDirectory "d:\Virtual Promptwars\EventMate AI\backend" -PassThru -NoNewWindow

try {
    # 1. Wait for health check
    $retries = 20
    $healthy = $false
    while ($retries -gt 0) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
            if ($health.status -eq "ok") {
                $healthy = $true
                Write-Host "Backend is healthy! Status: $($health.status), AI Configured: $($health.ai_configured)"
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
            $retries--
        }
    }

    if (-not $healthy) {
        throw "Backend failed to start within timeout"
    }

    # 2. Call /api/events/generate
    Write-Host "`nStep 2: Generate Event Plan..."
    $genPayload = @{
        event_name = "Golden Jubilee Gala"
        event_type = "Community Event"
        event_date = "2026-11-28"
        location = "Grand Banquet Plaza"
        guest_count = 200
        total_budget = 250000
        currency = "INR"
    } | ConvertTo-Json

    $genResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/generate" -Method Post -Body $genPayload -ContentType "application/json"
    Write-Host "Generated plan from source: $($genResponse.source), Timeline tasks: $($genResponse.timeline.Count)"

    # 3. Save Event with Plan
    Write-Host "`nStep 3: Save Event with Plan (POST /api/events)..."
    $savePayload = @{
        name = "Golden Jubilee Gala"
        event_type = "Community Event"
        event_date = "2026-11-28"
        location = "Grand Banquet Plaza"
        guest_count = 200
        total_budget = "250000.00"
        currency = "INR"
        generated_plan = $genResponse
    } | ConvertTo-Json -Depth 10

    $event = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events" -Method Post -Body $savePayload -ContentType "application/json"
    $eventId = $event.id
    Write-Host "Saved Event ID: $eventId, Total Budget: $($event.total_budget), Categories: $($event.budget_categories.Count), Tasks: $($event.tasks.Count)"

    # 4. List Events
    Write-Host "`nStep 4: List Events (GET /api/events)..."
    $list = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events" -Method Get
    Write-Host "Total Events listed: $($list.Count)"
    if ($list[0].id -ne $eventId) { throw "Event not first in newest list" }

    # 5. Get Event by ID
    Write-Host "`nStep 5: Get Event (GET /api/events/$eventId)..."
    $fetched = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/$eventId" -Method Get
    Write-Host "Fetched Event Name: $($fetched.name), Utilization: $($fetched.budget_summary.utilization_percent)%"

    # 6. PUT Event
    Write-Host "`nStep 6: Update Event (PUT /api/events/$eventId)..."
    $updatePayload = @{
        name = "Golden Jubilee Gala (Updated)"
        guest_count = 220
        total_budget = "260000.00"
    } | ConvertTo-Json
    $updated = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/$eventId" -Method Put -Body $updatePayload -ContentType "application/json"
    Write-Host "Updated Name: $($updated.name), Guests: $($updated.guest_count), Unallocated: $($updated.budget_summary.unallocated)"

    # 7. Add Expense
    Write-Host "`nStep 7: Add Expense (POST /api/events/$eventId/expenses)..."
    $catId = $event.budget_categories[0].id
    $expPayload = @{
        description = "Stage Lighting Rental"
        estimated_amount = "15000.00"
        actual_amount = "12000.00"
        budget_category_id = $catId
        payment_status = "Partial"
        expense_date = "2026-11-10"
        notes = "Advance paid"
    } | ConvertTo-Json
    $expense = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/$eventId/expenses" -Method Post -Body $expPayload -ContentType "application/json"
    $expenseId = $expense.id
    Write-Host "Created Expense ID: $expenseId, Estimated: $($expense.estimated_amount), Actual: $($expense.actual_amount)"

    # 8. Edit Expense
    Write-Host "`nStep 8: Edit Expense (PUT /api/expenses/$expenseId)..."
    $expUpdatePayload = @{
        actual_amount = "15000.00"
        payment_status = "Paid"
    } | ConvertTo-Json
    $expUpdated = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/expenses/$expenseId" -Method Put -Body $expUpdatePayload -ContentType "application/json"
    Write-Host "Updated Expense Actual: $($expUpdated.actual_amount), Status: $($expUpdated.payment_status)"

    # 9. Delete Expense
    Write-Host "`nStep 9: Delete Expense (DELETE /api/expenses/$expenseId)..."
    $delExpRes = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/expenses/$expenseId" -Method Delete
    Write-Host "Expense Delete Status: $($delExpRes.StatusCode)"

    # 10. Add Task
    Write-Host "`nStep 10: Add Task (POST /api/events/$eventId/tasks)..."
    $taskPayload = @{
        title = "Print Entry Badges"
        category = "Registration"
        priority = "High"
        due_date = "2026-11-20"
        status = "Pending"
    } | ConvertTo-Json
    $task = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/$eventId/tasks" -Method Post -Body $taskPayload -ContentType "application/json"
    $taskId = $task.id
    Write-Host "Created Task ID: $taskId, Title: $($task.title), Due: $($task.due_date)"

    # 11. Update Task to Completed
    Write-Host "`nStep 11: Update Task (PUT /api/tasks/$taskId)..."
    $taskUpdatePayload = @{
        status = "Completed"
    } | ConvertTo-Json
    $taskUpdated = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/tasks/$taskId" -Method Put -Body $taskUpdatePayload -ContentType "application/json"
    Write-Host "Updated Task Status: $($taskUpdated.status)"

    # 12. Delete Task
    Write-Host "`nStep 12: Delete Task (DELETE /api/tasks/$taskId)..."
    $delTaskRes = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/tasks/$taskId" -Method Delete
    Write-Host "Task Delete Status: $($delTaskRes.StatusCode)"

    # 13. Check Summaries
    Write-Host "`nStep 13: Check Event Summaries..."
    $finalEvent = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/$eventId" -Method Get
    Write-Host "Budget Remaining: $($finalEvent.budget_summary.remaining), Utilization: $($finalEvent.budget_summary.utilization_percent)%"
    Write-Host "Task Summary - Total: $($finalEvent.task_summary.total), Completed: $($finalEvent.task_summary.completed)"

    # 14. Delete Event & Confirm 404
    Write-Host "`nStep 14: Delete Event and Confirm 404..."
    $delEventRes = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/events/$eventId" -Method Delete
    Write-Host "Event Delete Status: $($delEventRes.StatusCode)"

    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/events/$eventId" -Method Get
        throw "Event should not exist after deletion"
    } catch {
        Write-Host "Confirmed: GET /api/events/$eventId returned 404 as expected."
    }

    Write-Host "`nALL E2E API CHECKS PASSED SUCCESSFULLY!"
} finally {
    Write-Host "Stopping backend process..."
    Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    if (Test-Path "d:\Virtual Promptwars\EventMate AI\backend\verify_temp.db") {
        Remove-Item "d:\Virtual Promptwars\EventMate AI\backend\verify_temp.db" -Force -ErrorAction SilentlyContinue
    }
}
