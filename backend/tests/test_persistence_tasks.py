from datetime import date, timedelta
import pytest


def test_task_crud_lifecycle_and_flags(client, freeze_today):
    frozen_now = date(2026, 11, 1)
    freeze_today(frozen_now)

    event = client.post("/api/events", json={
        "name": "Task Lifecycle Fest",
        "event_type": "Community Event",
        "event_date": "2026-11-20",
        "location": "Park",
        "guest_count": 50,
        "total_budget": "5000.00",
        "currency": "INR",
        "generated_plan": {"source": "demo"}
    }).json()
    event_id = event["id"]

    # 1. Zero tasks progress is 0.0
    ev_detail = client.get(f"/api/events/{event_id}").json()
    assert ev_detail["task_summary"]["total"] == 0
    assert ev_detail["task_summary"]["progress_percent"] == 0.0

    # 2. Reject invalid priority
    bad_prio = client.post(f"/api/events/{event_id}/tasks", json={
        "title": "Bad Prio",
        "category": "Setup",
        "priority": "Urgent",  # Invalid
        "due_date": "2026-11-05"
    })
    assert bad_prio.status_code == 422

    # 3. Reject invalid status
    bad_status = client.post(f"/api/events/{event_id}/tasks", json={
        "title": "Bad Status",
        "category": "Setup",
        "status": "Doing",  # Invalid
        "due_date": "2026-11-05"
    })
    assert bad_status.status_code == 422

    # 4. Create Overdue task: due before frozen today (2026-10-25 < 2026-11-01)
    t_overdue = client.post(f"/api/events/{event_id}/tasks", json={
        "title": "Overdue Permit",
        "category": "Permits",
        "priority": "High",
        "due_date": "2026-10-25",
        "status": "Pending"
    }).json()
    assert t_overdue["is_overdue"] is True
    assert t_overdue["is_upcoming"] is False
    assert t_overdue["after_event_date"] is False

    # 5. Create Upcoming task: due within 7 days (2026-11-05 is 4 days from 2026-11-01)
    t_upcoming = client.post(f"/api/events/{event_id}/tasks", json={
        "title": "Order Tents",
        "category": "Logistics",
        "priority": "Medium",
        "due_date": "2026-11-05",
        "status": "Pending"
    }).json()
    assert t_upcoming["is_overdue"] is False
    assert t_upcoming["is_upcoming"] is True

    # 6. Create Task due after event date (2026-11-25 > 2026-11-20)
    t_post_event = client.post(f"/api/events/{event_id}/tasks", json={
        "title": "Return Rental Gear",
        "category": "Logistics",
        "priority": "Low",
        "due_date": "2026-11-25",
        "status": "Pending"
    }).json()
    assert t_post_event["after_event_date"] is True

    # 7. Filter tasks by status
    pending_list = client.get(f"/api/events/{event_id}/tasks?status=Pending").json()
    assert len(pending_list) == 3

    # Reject invalid status filter query
    bad_filter = client.get(f"/api/events/{event_id}/tasks?status=Archived")
    assert bad_filter.status_code == 422

    # 8. Update task status to Completed
    task_id = t_upcoming["id"]
    up_res = client.put(f"/api/tasks/{task_id}", json={
        "status": "Completed"
    })
    assert up_res.status_code == 200
    updated_task = up_res.json()
    assert updated_task["id"] == task_id  # same id, updates in place
    assert updated_task["status"] == "Completed"
    # Completed tasks are neither overdue nor upcoming
    assert updated_task["is_overdue"] is False
    assert updated_task["is_upcoming"] is False

    # 9. Verify task summary calculation
    ev_detail_updated = client.get(f"/api/events/{event_id}").json()
    t_sum = ev_detail_updated["task_summary"]
    assert t_sum["total"] == 3
    assert t_sum["completed"] == 1
    assert t_sum["overdue"] == 1
    assert t_sum["progress_percent"] == 33.3

    # 10. Reject event_id modification on PUT
    bad_put = client.put(f"/api/tasks/{task_id}", json={"event_id": "other-id"})
    assert bad_put.status_code == 422

    # 11. Delete task
    del_res = client.delete(f"/api/tasks/{task_id}")
    assert del_res.status_code == 204

    # 12. 404 for missing task
    assert client.put(f"/api/tasks/{task_id}", json={"title": "x"}).status_code == 404
    assert client.delete(f"/api/tasks/{task_id}").status_code == 404
    assert client.delete("/api/tasks/invalid-task-id-999").status_code == 404
