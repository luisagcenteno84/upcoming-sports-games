# Upcoming Sports Games

FastAPI-based two-service app for tracking upcoming interesting sports games, including favorites, rivals, standings snapshots, venue and watch info in Phoenix, AZ time.

## Architecture

- `backend/`: FastAPI API with dashboard payload and Firestore test endpoint.
- `frontend/`: FastAPI UI rendering favorite teams and high-profile upcoming games.
- `cloudbuild.yaml`: Builds and deploys both services to Cloud Run.
- `scripts/bootstrap_gcp.ps1`: Enables APIs, IAM, Artifact Registry, Firestore.
- `scripts/create_trigger.ps1`: Creates Cloud Build GitHub trigger on `main`.
- `scripts/deploy_once.ps1`: Executes immediate deployment.

## Local run

```powershell
docker compose up --build
```

- Frontend: `http://localhost:8081`
- Backend: `http://localhost:8080`

## GCP setup

```powershell
.\scripts\bootstrap_gcp.ps1 -ProjectId "upcoming-sports-games" -Region "us-central1" -ArtifactRepo "app-images"
.\scripts\create_trigger.ps1 -ProjectId "upcoming-sports-games" -Region "us-central1" -GitHubOwner "luisagcenteno84" -RepoName "upcoming-sports-games" -TriggerName "upcoming-sports-games-main-deploy"
.\scripts\deploy_once.ps1 -ProjectId "upcoming-sports-games" -Region "us-central1"
```

## Endpoints

- Backend health: `/health`
- Backend smoke test: `/api/v1/test`
- Backend dashboard: `/api/v1/dashboard`
- Frontend health: `/health`
- Frontend backend-proxy test: `/api/v1/test`

## AI runbook

1. Ensure `gh auth status` and `gcloud auth list` are authenticated.
2. Push commits to `main` to trigger Cloud Build deploy.
3. If deploy fails, inspect build logs in Cloud Build, fix, and push again.
4. Validate frontend and backend health/test endpoints.
5. Keep service names fixed:
   - backend: `<app-slug>-backend`
   - frontend: `<app-slug>-frontend`
