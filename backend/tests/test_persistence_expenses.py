import pytest


def test_expense_crud_and_cross_event_rejection(client):
    # Create Event A with a category
    plan_a = {
        "budget": {"items": [{"category": "Catering", "amount": 50000}]}
    }
    event_a = client.post("/api/events", json={
        "name": "Event A",
        "event_type": "Wedding",
        "event_date": "2026-11-20",
        "location": "Chicago",
        "guest_count": 50,
        "total_budget": "500.00",
        "currency": "USD",
        "generated_plan": plan_a
    }).json()

    # Create Event B
    event_b = client.post("/api/events", json={
        "name": "Event B",
        "event_type": "Birthday",
        "event_date": "2026-11-22",
        "location": "Miami",
        "guest_count": 20,
        "total_budget": "200.00",
        "currency": "USD"
    }).json()

    cat_a_id = event_a["budget_categories"][0]["id"]

    # 1. Attempt to create expense in Event B referencing Category from Event A -> 422
    cross_res = client.post(f"/api/events/{event_b['id']}/expenses", json={
        "description": "Cross Category Exp",
        "estimated_amount": "50.00",
        "budget_category_id": cat_a_id
    })
    assert cross_res.status_code == 422
    assert "budget_category_id must belong to the same event" in cross_res.json()["detail"]

    # 2. Create valid expense in Event A
    exp_res = client.post(f"/api/events/{event_a['id']}/expenses", json={
        "description": "Appetizers Deposit",
        "estimated_amount": "150.00",
        "actual_amount": "100.00",
        "budget_category_id": cat_a_id,
        "payment_status": "Partial",
        "expense_date": "2026-11-01",
        "notes": "50 outstanding"
    })
    assert exp_res.status_code == 201
    exp_data = exp_res.json()
    expense_id = exp_data["id"]
    assert exp_data["estimated_amount"] == "150.00"
    assert exp_data["actual_amount"] == "100.00"
    assert exp_data["payment_status"] == "Partial"

    # 3. List expenses
    list_res = client.get(f"/api/events/{event_a['id']}/expenses")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 4. Reject event_id modification on PUT
    bad_put = client.put(f"/api/expenses/{expense_id}", json={
        "event_id": event_b["id"]
    })
    assert bad_put.status_code == 422

    # 5. Cross-event category update rejected
    cross_put = client.put(f"/api/expenses/{expense_id}", json={
        "budget_category_id": "nonexistent-or-other-cat"
    })
    assert cross_put.status_code == 422

    # 6. Valid update
    up_res = client.put(f"/api/expenses/{expense_id}", json={
        "actual_amount": "150.00",
        "payment_status": "Paid"
    })
    assert up_res.status_code == 200
    assert up_res.json()["actual_amount"] == "150.00"
    assert up_res.json()["payment_status"] == "Paid"

    # 7. Check generated_plan unchanged
    refetched_event = client.get(f"/api/events/{event_a['id']}").json()
    assert refetched_event["generated_plan"] == plan_a

    # 8. Delete expense
    del_res = client.delete(f"/api/expenses/{expense_id}")
    assert del_res.status_code == 204

    # 9. 404 on nonexistent expense
    assert client.put(f"/api/expenses/{expense_id}", json={"description": "x"}).status_code == 404
    assert client.delete(f"/api/expenses/{expense_id}").status_code == 404
    assert client.delete("/api/expenses/invalid-expense-id-999").status_code == 404
