# Deployment Guide

## GitHub Actions Setup

### 1. Create GitHub Repository
1. Create a new GitHub repository
2. Push this code to the `main` branch

### 2. Configure GitHub Secrets
Add the following secret in your GitHub repository settings (Settings → Secrets and variables → Actions):

**Secret Name**: `GCP_SA_KEY`
**Secret Value**: Copy the entire contents of `gcp-sa-key.json`

```bash
# To view the service account key:
cat gcp-sa-key.json
```

### 3. Deploy via GitHub Actions
1. Go to your repository on GitHub
2. Navigate to **Actions** tab
3. Find the "Deploy to GCP" workflow
4. Click **Run workflow**
5. Select environment (production/staging)
6. Click **Run workflow**

## Service Account Details

### CI/CD Service Account
- **Name**: `cicd-github-bq-pubsub@evm-attest.iam.gserviceaccount.com`
- **Roles**:
  - Cloud Functions Admin
  - Cloud Scheduler Admin
  - Pub/Sub Admin
  - Service Account Admin
  - Service Usage Admin

### Function Service Account (created by workflow)
- **Name**: `github-etl-sa@evm-attest.iam.gserviceaccount.com`
- **Roles**:
  - BigQuery Data Viewer
  - BigQuery Job User
  - Pub/Sub Publisher

## Manual Deployment (Alternative)
If you prefer to deploy manually:

```bash
export PROJECT_ID=evm-attest
export PUBSUB_TOPIC_ID=github-events
./deploy.sh
```

## Monitoring
- **Function logs**: `gcloud functions logs read github-events-etl --region=us-central1`
- **Test manually**: Trigger the GitHub Actions workflow
- **View scheduler**: `gcloud scheduler jobs list --location=us-central1`

## Security Notes
- The `gcp-sa-key.json` file is gitignored and should never be committed
- Delete the local key file after adding it to GitHub secrets
- Service accounts follow principle of least privilege