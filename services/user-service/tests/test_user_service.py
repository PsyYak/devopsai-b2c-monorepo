import importlib.util, pathlib

def load_app():
    p = pathlib.Path("/user-service/app.py")
    spec = importlib.util.spec_from_file_location("user_app", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod.app

def test_healthz():
    app = load_app()
    client = app.test_client()
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["service"] == "user-service"

def test_register_login_profile():
    app = load_app()
    client = app.test_client()
    # register
    res = client.post("/register", json={
        "username":"alice","password":"p@ss","name":"Alice","email":"alice@example.com"
    })
    assert res.status_code in (200,201)
    # login
    tok = client.post("/login", json={"username":"alice","password":"p@ss"}).get_json()["token"]
    # profile
    prof = client.get("/profile", headers={"authorization": f"Bearer {tok}"})
    assert prof.status_code == 200
    assert prof.get_json()["username"] == "alice"
