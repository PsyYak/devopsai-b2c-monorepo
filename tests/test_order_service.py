import importlib.util, pathlib

def load_app():
    p = pathlib.Path("services/order-service/app.py")
    spec = importlib.util.spec_from_file_location("order_app", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod.app

def test_healthz():
    app = load_app()
    client = app.test_client()
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["service"] == "order-service"

def test_browse_products():
    app = load_app()
    client = app.test_client()
    r = client.get("/products")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list) and len(data) >= 1
