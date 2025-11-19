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
Sometimes it won't work so run ```winget install jqlang.jq```
then, if it fails again, run 
```
Invoke-WebRequest -Uri http://localhost:5001/register `
  -Method Post `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"username":"yakir","password":"p@ss","name":"Yakir M.","email":"yakir@example.com"}'
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

---

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

---

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

---

## Environments: dev & stage

- Dev and stage image tags live under `gitops/image-tags/dev` and `gitops/image-tags/stage`.
- ArgoCD Applications:
  - Dev → `gitops/apps/*-app-dev.yaml` (namespace: `b2c-dev`)
  - Stage → `gitops/apps/*-app-stage.yaml` (namespace: `b2c-stage`)

### Promote to stage (manual)
Run the GitHub Action **Promote to stage** with input `tag` (e.g., the short SHA built by CI).
This opens a PR updating the stage values files; merge it and ArgoCD will roll out to `b2c-stage`.

---

## GitHub Actions Permissions

Your **Promote to stage** workflow uses the built-in `GITHUB_TOKEN` to open pull requests automatically.  
To allow this, you must enable a repository (or org-level) setting.

### 🧭 Enable “Allow GitHub Actions to create and approve pull requests”

1. Go to your repository page on GitHub.  
2. Click **Settings → Actions → General**.  
3. Scroll down to **Workflow permissions**.  
4. Check **“Allow GitHub Actions to create and approve pull requests.”**  
5. Click **Save**.

> If this option is disabled or greyed out, your organization’s admin must enable it at  
> **Organization Settings → Actions → General → Workflow permissions**  
> (or **Enterprise Settings** for enterprise-managed orgs).

---

## Running the Promotion Workflow

Once CI has pushed a new image, you can manually promote that tag to **stage**:

1. Go to **Actions** → **Promote to stage** in the GitHub web UI.  
2. Click **Run workflow** (top-right).  
3. Enter the short image tag or SHA from the CI build.  
4. Click **Run workflow**.

This creates a branch named `promote/<tag>` and automatically opens a Pull Request.  
After review and merge, ArgoCD detects the updated stage values and deploys to the `b2c-stage` namespace.

> 💡 You can also trigger the workflow from the CLI:
> ```bash
> gh workflow run "Promote to stage" -f tag=<short_sha>
> ```

---

## 🧰 Troubleshooting — “GitHub Actions is not permitted to create or approve pull requests”

If your workflow fails with this error:

```
GitHub Actions is not permitted to create or approve pull requests.
```

it means your repository or organization currently **disables PR creation via the default GITHUB_TOKEN**.

### ✅ Option 1 — Enable the permission in GitHub UI
1. Go to **Settings → Actions → General** in your repository.  
2. Under **Workflow permissions**, select **“Allow GitHub Actions to create and approve pull requests.”**  
3. Save changes.

If this option is greyed out:
- Ask your **org admin** to enable it at the organization level:  
  **Organization Settings → Actions → General → Workflow permissions.**

---

### 🔐 Option 2 — Use a Personal Access Token (bot)
If your org restricts that setting, you can use a **bot PAT** instead of `GITHUB_TOKEN`:

1. Create a GitHub user (e.g., `stage-bot`) with **Write** access to the repo.  
2. Generate a **Fine-grained Personal Access Token (PAT)** with:
   - Repository contents: Read/Write  
   - Pull requests: Read/Write  
3. Store it as a repo secret named `ACTIONS_BOT_PAT`.  
4. Update your workflow:

```yaml
- name: Create Pull Request (bot)
  uses: peter-evans/create-pull-request@v6
  with:
    token: ${{ secrets.ACTIONS_BOT_PAT }}
    branch: "promote/${{ github.event.inputs.tag }}"
    commit-message: "Promote to stage: ${{ github.event.inputs.tag }}"
    title: "Promote to stage: ${{ github.event.inputs.tag }}"
```

This lets the workflow create the branch and PR using your bot’s credentials, even if GitHub Actions itself isn’t permitted to.

---

### 🧩 Option 3 — Use a GitHub App Token
For enterprise setups, create a **GitHub App** with:
- `contents: read/write`
- `pull_requests: read/write`

Then generate an installation token in your workflow using:
```yaml
- uses: tibdex/github-app-token@v2
  id: app-token
  with:
    app_id: ${{ secrets.APP_ID }}
    private_key: ${{ secrets.APP_PRIVATE_KEY }}
    installation_id: ${{ secrets.APP_INSTALLATION_ID }}
```

And pass it to the `create-pull-request` step:
```yaml
token: ${{ steps.app-token.outputs.token }}
```

---

This ensures your **Promote to stage** workflow runs smoothly regardless of org policies and keeps your deployment flow secure and auditable.
