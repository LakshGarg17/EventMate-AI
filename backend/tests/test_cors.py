from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_cors_preflight_allows_put_and_delete():
    headers_put = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "content-type",
    }
    res_put = client.options("/api/events/test-id", headers=headers_put)
    assert res_put.status_code == 200
    assert res_put.headers.get("access-control-allow-origin") == "http://localhost:5173"
    allowed_methods = res_put.headers.get("access-control-allow-methods", "")
    assert "PUT" in allowed_methods

    headers_del = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "DELETE",
        "Access-Control-Request-Headers": "content-type",
    }
    res_del = client.options("/api/events/test-id", headers=headers_del)
    assert res_del.status_code == 200
    assert res_del.headers.get("access-control-allow-origin") == "http://localhost:5173"
    allowed_methods_del = res_del.headers.get("access-control-allow-methods", "")
    assert "DELETE" in allowed_methods_del
