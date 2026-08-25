#!/bin/bash
# FastAPI Cloud Deployment Script

set -e

echo "🚀 Starting FastAPI Cloud Deployment..."

# Check if required environment variables are set
check_env_vars() {
    local required_vars=("DATABASE_URL" "JWT_SECRET" "GROQ_API_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "❌ Error: Required environment variable $var is not set"
            exit 1
        fi
    done
    echo "✓ All required environment variables are set"
}

# Install FastAPI Cloud CLI if not already installed
install_cli() {
    if ! command -v fastapi-cloud &> /dev/null; then
        echo "Installing FastAPI Cloud CLI..."
        pip install fastapi-cloud
    else
        echo "✓ FastAPI Cloud CLI is already installed"
    fi
}

# Build and deploy
deploy() {
    echo "Building Docker image..."
    docker build -t flyrank-widget-backend:latest .
    
    echo "Deploying to FastAPI Cloud..."
    fastapi-cloud deploy \
        --config fastapi-cloud.json \
        --env-file .env.cloud \
        --name flyrank-widget-backend \
        --tag latest
}

# Run all steps
echo "Step 1: Checking environment variables..."
check_env_vars

echo "Step 2: Installing FastAPI Cloud CLI..."
install_cli

echo "Step 3: Building and deploying..."
deploy

echo "✅ Deployment complete!"
echo "Your application is being deployed to FastAPI Cloud..."
echo "Check the deployment status at: https://cloud.fastapi.com/deployments"
