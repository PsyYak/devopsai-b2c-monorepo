from flask import Flask, request, jsonify
from itsdangerous import URLSafeSerializer
import hashlib

app = Flask(__name__)
SECRET = "dev-secret"  # overridden by env in Docker/compose
import os
SECRET = os.getenv("SECRET_KEY", SECRET)
signer = URLSafeSerializer(SECRET, salt="user-auth")

# naive in-memory stores (demo only)
USERS = {}   # username -> dict
NEXT_ID = 1

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def make_token(username: str) -> str:
    return signer.dumps({"u": username})

def parse_token(token: str):
    try:
        data = signer.loads(token)
        return data.get("u")
    except Exception:
        return None

@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "user-service"})

@app.post("/register")
def register():
    global NEXT_ID
    payload = request.get_json(force=True, silent=True) or {}
    username = payload.get("username","").strip()
    password = payload.get("password","")
    name = payload.get("name","").strip()
    email = payload.get("email","").strip()

    if not username or not password:
        return jsonify({"error":"username and password required"}), 400
    if username in USERS:
        return jsonify({"error":"username already exists"}), 409

    user = {
        "id": str(NEXT_ID),
        "username": username,
        "name": name,
        "email": email,
        "password_hash": hash_pw(password)
    }
    USERS[username] = user
    NEXT_ID += 1
    public = {k:v for k,v in user.items() if k != "password_hash"}
    return jsonify(public), 201

@app.post("/login")
def login():
    payload = request.get_json(force=True, silent=True) or {}
    username = payload.get("username","").strip()
    password = payload.get("password","")
    user = USERS.get(username)
    if not user or user["password_hash"] != hash_pw(password):
        return jsonify({"error":"invalid credentials"}), 401
    token = make_token(username)
    return jsonify({"token": token})

@app.get("/profile")
def profile():
    auth = request.headers.get("authorization","")
    if not auth.lower().startswith("bearer "):
        return jsonify({"error":"missing bearer token"}), 401
    token = auth.split(" ",1)[1].strip()
    username = parse_token(token)
    if not username or username not in USERS:
        return jsonify({"error":"invalid token"}), 401
    user = USERS[username]
    public = {k:v for k,v in user.items() if k != "password_hash"}
    return jsonify(public)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
