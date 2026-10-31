from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import select

from app.db.models import ChangeProposal, Event, Vendor


@pytest.fixture
def vendor_event(temp_db):
    SessionLocal = temp_db["SessionLocal"]
    with SessionLocal() as db:
        event = Event(
            name="Ananya Graduation",
            event_type="Birthday",
            event_date=date(2026, 11, 20),
            location="Bengaluru",
            guest_count=60,
            total_budget=20000000,  # 200,000.00 INR
            currency="INR",
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id
    return event_id


def test_vendor_crud_lifecycle(client, vendor_event):
    # 1. Create vendor
    create_payload = {
        "name": "Spice Route Caterers",
        "category": "Catering",
        "contact_info": "contact@spiceroute.com",
        "quoted_amount": "45000.00",
        "notes": "Includes 3 live counters",
        "status": "Considering",
    }
    create_res = client.post(f"/api/events/{vendor_event}/vendors", json=create_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    vendor_id = created["id"]
    assert created["name"] == "Spice Route Caterers"
    assert created["quoted_amount"] == "45000.00"
    assert created["status"] == "Considering"

    # 2. List vendors
    list_res = client.get(f"/api/events/{vendor_event}/vendors")
    assert list_res.status_code == 200
    vendors = list_res.json()
    assert len(vendors) == 1
    assert vendors[0]["id"] == vendor_id

    # 3. Update vendor
    update_payload = {
        "quoted_amount": "42000.00",
        "status": "Shortlisted",
        "notes": "Negotiated 3,000 discount",
    }
    update_res = client.put(f"/api/vendors/{vendor_id}", json=update_payload)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["quoted_amount"] == "42000.00"
    assert updated["status"] == "Shortlisted"
    assert updated["notes"] == "Negotiated 3,000 discount"

    # 4. Delete vendor
    del_res = client.delete(f"/api/vendors/{vendor_id}")
    assert del_res.status_code == 204

    # Confirm deleted
    assert client.get(f"/api/vendors/{vendor_id}").status_code == 404 or client.delete(f"/api/vendors/{vendor_id}").status_code == 404
    assert len(client.get(f"/api/events/{vendor_event}/vendors").json()) == 0


def test_vendor_filters_and_validation(client, vendor_event):
    # Create two vendors in different categories & statuses
    client.post(
        f"/api/events/{vendor_event}/vendors",
        json={"name": "Lens Magic", "category": "Photography", "status": "Selected", "quoted_amount": "30000"},
    )
    client.post(
        f"/api/events/{vendor_event}/vendors",
        json={"name": "Floral Fantasy", "category": "Decoration", "status": "Contacted", "quoted_amount": "20000"},
    )

    # Valid category filter
    res_cat = client.get(f"/api/events/{vendor_event}/vendors?category=Photography")
    assert res_cat.status_code == 200
    assert len(res_cat.json()) == 1
    assert res_cat.json()[0]["name"] == "Lens Magic"

    # Invalid category filter -> 422
    assert client.get(f"/api/events/{vendor_event}/vendors?category=Nonexistent").status_code == 422

    # Valid status filter
    res_stat = client.get(f"/api/events/{vendor_event}/vendors?status=Contacted")
    assert res_stat.status_code == 200
    assert len(res_stat.json()) == 1
    assert res_stat.json()[0]["name"] == "Floral Fantasy"

    # Invalid status filter -> 422
    assert client.get(f"/api/events/{vendor_event}/vendors?status=InvalidStatus").status_code == 422

    # Negative quote -> 422
    neg_res = client.post(
        f"/api/events/{vendor_event}/vendors",
        json={"name": "Bad Quote", "category": "Venue", "quoted_amount": "-500"},
    )
    assert neg_res.status_code == 422

    # Too many decimals -> 422
    dec_res = client.post(
        f"/api/events/{vendor_event}/vendors",
        json={"name": "Bad Decimals", "category": "Venue", "quoted_amount": "500.1234"},
    )
    assert dec_res.status_code == 422


def test_vendor_comparison_logic(client, vendor_event):
    # Add vendors to Catering:
    # V1: 50,000 (Considering)
    # V2: 40,000 (Shortlisted) -> Lowest valid
    # V3: 40,000 (Selected) -> Lowest valid tie & Selected
    # V4: 30,000 (Rejected) -> Lowest amount but Rejected, MUST BE IGNORED!
    # V5: null quote (Selected) -> Missing quote
    client.post(f"/api/events/{vendor_event}/vendors", json={"name": "Cat V1", "category": "Catering", "status": "Considering", "quoted_amount": "50000.00"})
    client.post(f"/api/events/{vendor_event}/vendors", json={"name": "Cat V2", "category": "Catering", "status": "Shortlisted", "quoted_amount": "40000.00"})
    client.post(f"/api/events/{vendor_event}/vendors", json={"name": "Cat V3", "category": "Catering", "status": "Selected", "quoted_amount": "40000.00"})
    client.post(f"/api/events/{vendor_event}/vendors", json={"name": "Cat V4", "category": "Catering", "status": "Rejected", "quoted_amount": "30000.00"})
    client.post(f"/api/events/{vendor_event}/vendors", json={"name": "Cat V5", "category": "Catering", "status": "Selected", "quoted_amount": None})

    res = client.get(f"/api/events/{vendor_event}/vendors/comparison")
    assert res.status_code == 200
    comp = res.json()
    assert comp["event_total_budget"] == "200000.00"

    # Selected total: Cat V3 (40,000) + Cat V5 (null -> 0) = 40,000.00
    assert comp["selected_total"] == "40000.00"
    assert "Cat V5" in comp["missing_quotes"]

    cater_comp = next(c for c in comp["categories"] if c["category"] == "Catering")
    # Lowest quote among non-rejected is 40,000.00 (Cat V4 at 30k was ignored!)
    assert cater_comp["lowest_quote"] == "40000.00"
    assert len(cater_comp["lowest_vendor_ids"]) == 2  # V2 and V3 tied!

    # Multiple selected flag
    assert cater_comp["multiple_selected"] is True
    assert set(cater_comp["selected_vendors"]) == {"Cat V3", "Cat V5"}

    # Difference from lowest check
    v1_item = next(v for v in cater_comp["vendors"] if v["name"] == "Cat V1")
    assert v1_item["difference_from_lowest"] == "10000.00"  # 50k - 40k = 10k

    v3_item = next(v for v in cater_comp["vendors"] if v["name"] == "Cat V3")
    assert v3_item["difference_from_lowest"] == "0.00"  # tied lowest!
    assert v3_item["is_lowest"] is True
    assert v3_item["is_selected"] is True

    v5_item = next(v for v in cater_comp["vendors"] if v["name"] == "Cat V5")
    assert v5_item["difference_from_lowest"] is None
    assert v5_item["quoted_amount"] is None


def test_vendor_event_isolation_and_cascade_delete(client, vendor_event, temp_db):
    SessionLocal = temp_db["SessionLocal"]
    # Create second event
    with SessionLocal() as db:
        ev2 = Event(name="Event B", event_type="Birthday", event_date=date(2026, 12, 1), location="Pune", guest_count=30, total_budget=5000000, currency="INR")
        db.add(ev2)
        db.commit()
        db.refresh(ev2)
        ev2_id = ev2.id

    # Add vendor to event A and vendor to event B
    client.post(f"/api/events/{vendor_event}/vendors", json={"name": "Vendor A", "category": "Venue"})
    client.post(f"/api/events/{ev2_id}/vendors", json={"name": "Vendor B", "category": "Venue"})

    # Check isolation
    list_a = client.get(f"/api/events/{vendor_event}/vendors").json()
    list_b = client.get(f"/api/events/{ev2_id}/vendors").json()
    assert len(list_a) == 1 and list_a[0]["name"] == "Vendor A"
    assert len(list_b) == 1 and list_b[0]["name"] == "Vendor B"

    # Delete event A -> vendor A must be cascade deleted, vendor B preserved!
    del_res = client.delete(f"/api/events/{vendor_event}")
    assert del_res.status_code == 204

    with SessionLocal() as db:
        v_a = db.scalars(select(Vendor).where(Vendor.name == "Vendor A")).first()
        v_b = db.scalars(select(Vendor).where(Vendor.name == "Vendor B")).first()
        assert v_a is None
        assert v_b is not None

