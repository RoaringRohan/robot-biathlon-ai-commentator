$ErrorActionPreference = "Stop"
# Set DROPLET_IP in your environment before running, e.g.
#   $env:DROPLET_IP = "203.0.113.10"
$DROPLET_IP = $env:DROPLET_IP
if (-not $DROPLET_IP) { throw "DROPLET_IP is not set. Export it before deploying." }
$REMOTE_USER = "root"

Write-Host "Deploying to $DROPLET_IP..."

# Copy Files
scp -r . "$REMOTE_USER@${DROPLET_IP}:~/Model-Training"

# Copy Env
scp ../Web-App/.env.local "$REMOTE_USER@${DROPLET_IP}:~/Model-Training/.env"

Write-Host "Done. Run these commands on the server:"
Write-Host "ssh $REMOTE_USER@$DROPLET_IP"
Write-Host "cd Model-Training"
Write-Host "python3 -m venv venv"
Write-Host "source venv/bin/activate"
Write-Host "pip install -r requirements.txt"
Write-Host "python train_pipeline.py"
