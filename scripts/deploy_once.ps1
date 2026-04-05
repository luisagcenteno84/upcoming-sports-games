param(
  [Parameter(Mandatory=$true)][string]$ProjectId,
  [string]$Region = "us-central1",
  [string]$ArtifactRepo = "app-images",
  [string]$FirestoreCollection = "items"
)

$ErrorActionPreference = "Stop"
$gcloud = "C:\Users\luisa\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

& $gcloud config set project $ProjectId | Out-Null

& $gcloud builds submit . `
  --config cloudbuild.yaml `
  --substitutions="_REGION=$Region,_AR_REPO=$ArtifactRepo,_BACKEND_SERVICE=$ProjectId-backend,_FRONTEND_SERVICE=$ProjectId-frontend,_FIRESTORE_COLLECTION=$FirestoreCollection"
