#!/usr/bin/env python3
"""
EventMate AI Live Smoke Test Script
Exercises core API workflows against a live running server.
Always cleans up test resources in a finally block.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class SmokeTestRunner:
    def __init__(self, base_url: str, with_ai: bool = False):
        self.base_url = base_url.rstrip("/")
        self.with_ai = with_ai
        self.created_event_id: Optional[str] = None
        self.failed = False

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
    ) -> Tuple[int, Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
                json_data = json.loads(body) if body.strip() else {}
                if status != expected_status:
                    raise AssertionError(f"Expected status {expected_status}, got {status}: {body[:200]}")
                return status, json_data
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8")
            if err.code == expected_status:
                try:
                    return err.code, json.loads(body) if body.strip() else {}
                except Exception:
                    return err.code, {}
            raise AssertionError(f"HTTP {err.code} on {method} {path}: {body[:200]}") from err
        except urllib.error.URLError as err:
            raise RuntimeError(f"Connection failure to {url}: {err.reason}") from err

    def run(self) -> bool:
        print("=" * 60)
        print(f"Starting EventMate AI Smoke Test -> Base URL: {self.base_url}")
        print("=" * 60)

        try:
            # 1. Health checks
            self._test_health()

            # 2. Event creation & CRUD
            self._test_event_lifecycle()

            # 3. Optional AI test
            if self.with_ai:
                self._test_ai_endpoints()

            print("\n" + "=" * 60)
            print("ALL SMOKE TESTS COMPLETED SUCCESSFULLY! (Exit Code 0)")
            print("=" * 60)
            return True

        except Exception as exc:
            self.failed = True
            print(f"\n[FAIL] Smoke test encountered an error: {exc}", file=sys.stderr)
            return False

        finally:
            self._cleanup()

    def _test_health(self):
        print("\n[1/3] Testing Health & Readiness endpoints...")
        status, data = self._request("GET", "/api/health", expected_status=200)
        print(f"  [OK] GET /api/health -> status={data.get('status')} ai_configured={data.get('ai_configured')} model={data.get('model')}")

        status, data = self._request("GET", "/api/health/ready", expected_status=200)
        print(f"  [OK] GET /api/health/ready -> status={data.get('status')} database={data.get('database')}")

    def _test_event_lifecycle(self):
        print("\n[2/3] Testing Core Event, Expense, Task & Vendor Lifecycle...")
        test_uuid = str(uuid.uuid4())[:8]
        event_name = f"SMOKE TEST {test_uuid}"

        # A. Create Event
        create_payload = {
            "name": event_name,
            "event_type": "Birthday",
            "event_date": "2026-11-25",
            "location": "Smoke Test Venue",
            "guest_count": 50,
            "total_budget": "50000.00",
            "currency": "INR",
        }
        _, ev_data = self._request("POST", "/api/events", payload=create_payload, expected_status=201)
        self.created_event_id = ev_data["id"]
        print(f"  [OK] POST /api/events -> created event id={self.created_event_id} name='{event_name}'")

        # B. Add Expense
        exp_payload = {
            "description": "Birthday Cake & Confections",
            "estimated_amount": "5000.00",
            "actual_amount": "4800.00",
            "payment_status": "Paid",
        }
        _, exp_data = self._request("POST", f"/api/events/{self.created_event_id}/expenses", payload=exp_payload, expected_status=201)
        print(f"  [OK] POST /api/events/{self.created_event_id}/expenses -> created expense id={exp_data['id']}")

        # C. Add Task
        task_payload = {
            "title": "Confirm Cake Delivery Timing",
            "category": "Catering",
            "priority": "High",
            "due_date": "2026-11-24",
        }
        _, task_data = self._request("POST", f"/api/events/{self.created_event_id}/tasks", payload=task_payload, expected_status=201)
        print(f"  [OK] POST /api/events/{self.created_event_id}/tasks -> created task id={task_data['id']}")

        # D. Add Vendor
        vendor_payload = {
            "name": "Pastry Delights Bakery",
            "category": "Catering",
            "quoted_amount": "4800.00",
            "status": "Selected",
        }
        _, vend_data = self._request("POST", f"/api/events/{self.created_event_id}/vendors", payload=vendor_payload, expected_status=201)
        print(f"  [OK] POST /api/events/{self.created_event_id}/vendors -> created vendor id={vend_data['id']}")

        # E. Verify Event Details and Summaries
        _, detail = self._request("GET", f"/api/events/{self.created_event_id}", expected_status=200)
        b_sum = detail.get("budget_summary", {})
        t_sum = detail.get("task_summary", {})
        assert b_sum.get("total_actual") == "4800.00", f"Expected total_actual 4800.00, got {b_sum.get('total_actual')}"
        assert t_sum.get("total") == 1, f"Expected total tasks 1, got {t_sum.get('total')}"
        print(f"  [OK] GET /api/events/{self.created_event_id} -> verified budget_summary and task_summary")

        # F. Verify Vendor Comparison
        _, comp = self._request("GET", f"/api/events/{self.created_event_id}/vendors/comparison", expected_status=200)
        assert comp.get("selected_total") == "4800.00", f"Expected selected_total 4800.00, got {comp.get('selected_total')}"
        print(f"  [OK] GET /api/events/{self.created_event_id}/vendors/comparison -> verified selected_total='4800.00'")

    def _test_ai_endpoints(self):
        print("\n[3/3] Testing AI / Demo Generation Endpoints (--with-ai enabled)...")

        # Plan generation
        _, plan = self._request(
            "POST",
            "/api/events/generate",
            payload={
                "event_name": "Smoke AI Celebration",
                "event_type": "Birthday",
                "event_date": "2026-11-30",
                "location": "Goa Beach",
                "guest_count": 40,
                "total_budget": 100000,
                "currency": "INR",
            },
            expected_status=200,
        )
        overview_snippet = (plan.get("overview") or "")[:120]
        print(f"  [OK] POST /api/events/generate -> source={plan.get('source')} overview='{overview_snippet}...'")

        # Theme recommendation
        _, themes = self._request(
            "POST",
            "/api/themes/recommend",
            payload={
                "event_type": "Birthday",
                "location": "Goa",
                "guest_count": 40,
                "total_budget": "100000.00",
                "currency": "INR",
            },
            expected_status=200,
        )
        theme_names = [t.get("name") for t in themes.get("themes", [])][:3]
        print(f"  [OK] POST /api/themes/recommend -> source={themes.get('source')} themes={theme_names}")

        # Invitation generation
        _, inv = self._request(
            "POST",
            "/api/invitations/generate",
            payload={
                "event_type": "Birthday",
                "host_name": "Smoke Tester",
                "event_date": "2026-11-30",
                "event_time": "19:00",
                "location": "Goa Beach",
                "language": "English",
                "tone": "Fun",
            },
            expected_status=200,
        )
        inv_snippet = (inv.get("invitation_text") or "")[:120].replace("\n", " ")
        print(f"  [OK] POST /api/invitations/generate -> source={inv.get('source')} text='{inv_snippet}...'")

    def _cleanup(self):
        if self.created_event_id:
            print(f"\n[CLEANUP] Deleting temporary smoke test event id={self.created_event_id}...")
            try:
                self._request("DELETE", f"/api/events/{self.created_event_id}", expected_status=204)
                print("  [OK] Cleanup complete. Temporary event deleted.")
            except Exception as exc:
                print(f"  [WARN] Cleanup error (event {self.created_event_id}): {exc}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="EventMate AI Live Smoke Test")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of running server (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--with-ai",
        action="store_true",
        help="Include AI generation endpoints (using configured key or demo fallback)",
    )
    args = parser.parse_args()

    runner = SmokeTestRunner(base_url=args.base_url, with_ai=args.with_ai)
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
