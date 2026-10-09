
Write-Host "Pulling latest team changes..."

git pull --rebase origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "Pull failed. Fix Git issues before rebuilding."
    exit 1
}

Write-Host "Building Docker image..."

docker build -t handover-app .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed."
    exit 1
}

Write-Host "Update complete! Docker image is ready."


