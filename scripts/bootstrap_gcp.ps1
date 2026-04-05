param(
  [Parameter(Mandatory=$true)][string]$ProjectId,
  [string]$Region = "us-central1",
  [string]$ArtifactRepo = "app-images",
  [string]$FirestoreLocation = "nam5"
)

$ErrorActionPreference = "Stop"

$gcloud = "C:\Users\luisa\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

& $gcloud config set project $ProjectId | Out-Null

& $gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  firestore.googleapis.com `
  iam.googleapis.com | Out-Null

$repoExists = & $gcloud artifacts repositories list --location=$Region --format="value(name)" | Select-String -Pattern "/$ArtifactRepo$"
if (-not $repoExists) {
  & $gcloud artifacts repositories create $ArtifactRepo --repository-format=docker --location=$Region --description="Docker images for app"
}

$dbs = & $gcloud firestore databases list --format="value(name)"
if (-not $dbs) {
  & $gcloud firestore databases create --database="(default)" --location=$FirestoreLocation --type=firestore-native
}

$projectNumber = & $gcloud projects describe $ProjectId --format="value(projectNumber)"
$cloudBuildSa = "$projectNumber@cloudbuild.gserviceaccount.com"

& $gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cloudBuildSa" --role="roles/run.admin" | Out-Null
& $gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cloudBuildSa" --role="roles/iam.serviceAccountUser" | Out-Null
& $gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cloudBuildSa" --role="roles/artifactregistry.writer" | Out-Null
& $gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$cloudBuildSa" --role="roles/datastore.user" | Out-Null

Write-Output "Bootstrap complete for $ProjectId"
