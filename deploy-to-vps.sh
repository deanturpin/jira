#!/bin/bash
# Deploy Jira Planning Tools to VPS

set -e

VPS_HOST="sornhub"
VPS_USER="sorn"
DEPLOY_DIR="/var/www/jira-reports"

echo "🚀 Deploying Jira Planning Tools to VPS..."

# Check if we can connect to VPS
if ! ssh -q "$VPS_HOST" exit; then
    echo "❌ Cannot connect to VPS via ssh $VPS_HOST"
    echo "Make sure your SSH config is set up correctly"
    exit 1
fi

echo "✓ Connected to VPS"

# Create directory if it doesn't exist
echo "📁 Setting up directories..."
ssh "$VPS_HOST" "sudo mkdir -p $DEPLOY_DIR && sudo chown $VPS_USER:$VPS_USER $DEPLOY_DIR"

# Check if repo exists, clone or pull
echo "📦 Updating code..."
ssh "$VPS_HOST" "
    if [ -d $DEPLOY_DIR/.git ]; then
        cd $DEPLOY_DIR && git pull
    else
        git clone https://github.com/deanturpin/jira.git $DEPLOY_DIR
    fi
"

# Install/update dependencies
echo "📚 Installing dependencies..."
ssh "$VPS_HOST" "
    cd $DEPLOY_DIR
    if [ ! -d venv ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -q -r requirements.txt
"

echo "✓ Code deployed successfully"

# Restart service if it exists
if ssh "$VPS_HOST" "sudo systemctl is-active --quiet jira-reports.service 2>/dev/null"; then
    echo "🔄 Restarting service..."
    ssh "$VPS_HOST" "sudo systemctl restart jira-reports.service"
    echo "✓ Service restarted"
else
    echo "ℹ️  Service not yet configured. Follow VPS_DEPLOYMENT.md to set up systemd service."
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "  1. Configure environment: /root/.jira-env on VPS"
echo "  2. Set up systemd service (see VPS_DEPLOYMENT.md)"
echo "  3. Test: ssh $VPS_HOST 'sudo systemctl start jira-reports.service'"
