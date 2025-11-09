# B2C Flask Monorepo — user-service & order-service (Demo)

A single repository with two self-contained Flask microservices:

- **user-service** — registration, login (issues a simple signed token), and profile
- **order-service** — product browsing and order placement (validates the token)

Each service has its own `Dockerfile` and `requirements.txt`.  
A GitHub Actions workflow detects changes per service and builds & **pushes** only the changed image to **GHCR**.

> ⚠️ Demo-only auth using a signed token (itsdangerous). Do **not** use in production.

---

## Quick start (local)

```bash
docker compose up --build
# user-service  → http://localhost:5001/healthz
# order-service → http://localhost:5002/healthz
```

### Sample flow

1) **Register** a user
```bash
curl -s http://localhost:5001/register -H "content-type: application/json" -d '{
  "username":"alice","password":"p@ss","name":"Alice A.","email":"alice@example.com"
}' | jq .
```

2) **Login** to get token
```bash
TOKEN=$(curl -s http://localhost:5001/login -H "content-type: application/json" -d '{
  "username":"alice","password":"p@ss"
}' | jq -r .token)
echo $TOKEN
```

3) **Profile** (user-service, requires token)
```bash
curl -s http://localhost:5001/profile -H "authorization: Bearer $TOKEN" | jq .
```

4) **Browse products** (order-service, public)
```bash
curl -s http://localhost:5002/products | jq .
```

5) **Place an order** (order-service, requires token)
```bash
curl -s http://localhost:5002/orders   -H "authorization: Bearer $TOKEN"   -H "content-type: application/json"   -d '{"items":[{"product_id":"p1","qty":2},{"product_id":"p3","qty":1}]}' | jq .
```

---

## API Summary

### user-service (port 5001)
- `GET /healthz` → `{ "status": "ok", "service": "user-service" }`
- `POST /register` body:
  ```json
  {"username":"alice","password":"p@ss","name":"Alice","email":"alice@example.com"}
  ```
  response:
  ```json
  {"id":"1","username":"alice","name":"Alice","email":"alice@example.com"}
  ```
- `POST /login` body:
  ```json
  {"username":"alice","password":"p@ss"}
  ```
  response:
  ```json
  {"token":"<signed_token>"}
  ```
- `GET /profile` header `Authorization: Bearer <token>` → profile JSON

### order-service (port 5002)
- `GET /healthz` → `{ "status": "ok", "service": "order-service" }`
- `GET /products` → list of products
- `POST /orders` header `Authorization: Bearer <token>`
  body:
  ```json
  {"items":[{"product_id":"p1","qty":2},{"product_id":"p3","qty":1}]}
  ```
  response:
  ```json
  {"order_id":"o-1","user":"alice","items":[...],"total":123.45}
  ```

---

## GitHub Actions — selective build & push to GHCR
- Workflow: `.github/workflows/ci.yml`
- Builds and pushes only changed services:
  - `ghcr.io/<owner>/user-service:<sha>` and `latest`
  - `ghcr.io/<owner>/order-service:<sha>` and `latest`

> Requires no extra secrets for GHCR: uses the built-in `GITHUB_TOKEN`.  
> Ensure repository has **Packages: write** permission (set in workflow).

---

## Repo layout
```
.
├─ services/
│  ├─ user-service/
│  │  ├─ app.py
│  │  ├─ requirements.txt
│  │  └─ Dockerfile
│  └─ order-service/
│     ├─ app.py
│     ├─ requirements.txt
│     └─ Dockerfile
├─ docker-compose.yml
└─ .github/workflows/ci.yml
```

---

## Tests (pytest)

Install locally and run:

```bash
python -m venv .venv && . .venv/bin/activate  # or Scripts\activate on Windows
pip install -r services/user-service/requirements.txt -r services/order-service/requirements.txt pytest
pytest -q
```

The tests load each Flask app directly and check core endpoints.

## Helm charts

Two simple Helm charts are included:

```
helm/
  user-service/
    Chart.yaml
    values.yaml
    templates/deployment.yaml
    templates/service.yaml
  order-service/
    Chart.yaml
    values.yaml
    templates/deployment.yaml
    templates/service.yaml
```

Set `image.repository` and `image.tag` in values or via ArgoCD.

## ArgoCD (demo app-of-apps)

Folder: `gitops/`

```
gitops/
  apps/
    app-of-apps.yaml
    user-service-app.yaml
    order-service-app.yaml
  image-tags/
    user-service-values.yaml   # sets image.tag for user-service
    order-service-values.yaml  # sets image.tag for order-service
```

- The Applications reference the Helm charts in this same repo and include a **values file** per service to drive the image tag.  
- Update `repoURL` fields to point at your Git repository.
- Change the tag files under `gitops/image-tags/*.yaml` to rollout new versions (GitOps-friendly).

Apply (assuming ArgoCD installed and repo accessible):

```bash
# create namespace for workloads
kubectl create ns b2c-demo

# bootstrap the app-of-apps in argocd namespace
kubectl -n argocd apply -f gitops/apps/app-of-apps.yaml
```


## Environments: dev & stage

- Dev and stage image tags live under `gitops/image-tags/dev` and `gitops/image-tags/stage`.
- ArgoCD Applications:
  - Dev → `gitops/apps/*-app-dev.yaml` (namespace: `b2c-dev`)
  - Stage → `gitops/apps/*-app-stage.yaml` (namespace: `b2c-stage`)

### Promote to stage (manual)
Run the GitHub Action **Promote to stage** with input `tag` (e.g., the short SHA built by CI).
This opens a PR updating the stage values files; merge it and ArgoCD will roll out to `b2c-stage`.
