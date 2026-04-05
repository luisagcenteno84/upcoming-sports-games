param(
  [Parameter(Mandatory=$true)][string]$ProjectId,
  [Parameter(Mandatory=$true)][string]$Region,
  [Parameter(Mandatory=$true)][string]$GitHubOwner,
  [Parameter(Mandatory=$true)][string]$RepoName,
  [Parameter(Mandatory=$true)][string]$TriggerName,
  [string]$ArtifactRepo = "app-images",
  [string]$FirestoreCollection = "items"
)

$ErrorActionPreference = "Stop"
$gcloud = "C:\Users\luisa\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

& $gcloud config set project $ProjectId | Out-Null

$exists = & $gcloud builds triggers list --format="value(name)" --filter="name=$TriggerName"
if ($exists -eq $TriggerName) {
  Write-Output "Trigger already exists: $TriggerName"
  exit 0
}

& $gcloud builds triggers create github `
  --name=$TriggerName `
  --repo-owner=$GitHubOwner `
  --repo-name=$RepoName `
  --branch-pattern="^main$" `
  --build-config="cloudbuild.yaml" `
  --substitutions="_REGION=$Region,_AR_REPO=$ArtifactRepo,_BACKEND_SERVICE=$ProjectId-backend,_FRONTEND_SERVICE=$ProjectId-frontend,_FIRESTORE_COLLECTION=$FirestoreCollection"

Write-Output "Trigger created: $TriggerName"
