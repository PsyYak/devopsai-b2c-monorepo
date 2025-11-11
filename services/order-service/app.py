from flask import Flask, request, jsonify
from itsdangerous import URLSafeSerializer
from decimal import Decimal, ROUND_HALF_UP
import os

app = Flask(__name__)
SECRET = os.getenv("SECRET_KEY","dev-secret")
signer = URLSafeSerializer(SECRET, salt="user-auth")
ENVIRONMENT = os.getenv("APP_ENV", "unknown")  # set via Helm values per env


# toy catalog and orders (demo)
PRODUCTS = {
    "p1": {"id":"p1","name":"Wireless Mouse","price": 19.99},
    "p2": {"id":"p2","name":"Mechanical Keyboard","price": 59.49},
    "p3": {"id":"p3","name":"USB-C Hub","price": 24.90},
}
ORDERS = []
ORDER_SEQ = 1

def parse_token(token: str):
    try:
        data = signer.loads(token)
        return data.get("u")
    except Exception:
        return None

def money(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "order-service", "env": ENVIRONMENT})

@app.get("/env")
def env():
    return jsonify({"env": ENVIRONMENT})

@app.get("/products")
def products():
    return jsonify(list(PRODUCTS.values()))

@app.post("/create_order")
def create_order():
    global ORDER_SEQ
    auth = request.headers.get("authorization","")
    if not auth.lower().startswith("bearer "):
        return jsonify({"error":"missing bearer token"}), 401
    token = auth.split(" ",1)[1].strip()
    username = parse_token(token)
    if not username:
        return jsonify({"error":"invalid token"}), 401

    payload = request.get_json(force=True, silent=True) or {}
    items = payload.get("items",[])
    if not items:
        return jsonify({"error":"items required"}), 400

    line_items = []
    total = 0.0
    for it in items:
        pid = it.get("product_id")
        qty = int(it.get("qty",1))
        prod = PRODUCTS.get(pid)
        if not prod or qty <= 0:
            return jsonify({"error": f"invalid item {it}"}), 400
        line_total = money(prod["price"] * qty)
        total = money(total + line_total)
        line_items.append({
            "product_id": pid,
            "name": prod["name"],
            "unit_price": money(prod["price"]),
            "qty": qty,
            "line_total": line_total
        })

    oid = f"o-{ORDER_SEQ}"
    ORDER_SEQ += 1
    order = {"order_id": oid, "user": username, "items": line_items, "total": total}
    ORDERS.append(order)
    return jsonify(order), 201

@app.get("/orders/<order_id>")
def get_order(order_id):
    auth = request.headers.get("authorization","")
    if not auth.lower().startswith("bearer "):
        return jsonify({"error":"missing bearer token"}), 401
    token = auth.split(" ",1)[1].strip()
    username = parse_token(token)
    if not username:
        return jsonify({"error":"invalid token"}), 401

    for o in ORDERS:
        if o["order_id"] == order_id and o["user"] == username:
            return jsonify(o)
    return jsonify({"error":"not found"}), 404

@app.get("/orders")
def list_orders():
    auth = request.headers.get("authorization","")
    if not auth.lower().startswith("bearer "):
        return jsonify({"error":"missing bearer token"}), 401
    token = auth.split(" ",1)[1].strip()
    username = parse_token(token)
    if not username:
        return jsonify({"error":"invalid token"}), 401

    # return only this user’s orders
    user_orders = [o for o in ORDERS if o["user"] == username]
    return jsonify(user_orders)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
