#!/bin/bash

# Script to help set up GitHub repository secrets
# This script displays the service account key that needs to be added to GitHub

echo "==================================="
echo "GitHub Repository Secret Setup"
echo "==================================="
echo ""
echo "1. Go to your GitHub repository"
echo "2. Navigate to Settings → Secrets and variables → Actions"
echo "3. Click 'New repository secret'"
echo "4. Use the following details:"
echo ""
echo "Secret Name: GCP_SA_KEY"
echo "Secret Value (copy the JSON below):"
echo ""
echo "---BEGIN SERVICE ACCOUNT KEY---"
cat gcp-sa-key.json
echo ""
echo "---END SERVICE ACCOUNT KEY---"
echo ""
echo "5. Click 'Add secret'"
echo ""
echo "After adding the secret to GitHub, you can safely delete the local key file:"
echo "rm gcp-sa-key.json"
echo ""
echo "Then you can deploy via GitHub Actions:"
echo "- Go to Actions tab in your repo"
echo "- Find 'Deploy to GCP' workflow"
echo "- Click 'Run workflow'"