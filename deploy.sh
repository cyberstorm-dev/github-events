#!/bin/bash

# GitHub Archive to Pub/Sub ETL Job - Deployment Script
# This script deploys the Cloud Function and sets up the Cloud Scheduler job

set -e  # Exit on any error

# Configuration - UPDATE THESE VALUES
PROJECT_ID="${PROJECT_ID:-evm-attest}"
FUNCTION_NAME="${FUNCTION_NAME:-github-events-etl}"
REGION="${REGION:-us-central1}"
PUBSUB_TOPIC_ID="${PUBSUB_TOPIC_ID:-github-events}"
SCHEDULER_JOB_NAME="${SCHEDULER_JOB_NAME:-github-etl-hourly}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-github-etl-sa}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying GitHub Archive ETL Job${NC}"
echo "Project: $PROJECT_ID"
echo "Function: $FUNCTION_NAME"
echo "Region: $REGION"
echo "Pub/Sub Topic: $PUBSUB_TOPIC_ID"

# Extract topic name from full topic path if provided
if [[ "$PUBSUB_TOPIC_ID" == projects/*/topics/* ]]; then
    TOPIC_NAME=$(echo "$PUBSUB_TOPIC_ID" | sed 's|projects/.*/topics/||')
    echo -e "${YELLOW}📝 Extracted topic name: $TOPIC_NAME${NC}"
else
    TOPIC_NAME="$PUBSUB_TOPIC_ID"
fi

# Validate required environment variables
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Please set PROJECT_ID environment variable${NC}"
    echo "Example: export PROJECT_ID=evm-attest"
    exit 1
fi

if [ -z "$TOPIC_NAME" ]; then
    echo -e "${RED}❌ Please set PUBSUB_TOPIC_ID environment variable${NC}"
    exit 1
fi

# Set the project
echo -e "${YELLOW}📝 Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable bigquery.googleapis.com

# Create service account for the function
echo -e "${YELLOW}👤 Creating service account...${NC}"
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com --project=$PROJECT_ID 2>/dev/null; then
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
        --display-name="GitHub ETL Service Account" \
        --description="Service account for GitHub Archive ETL Cloud Function" \
        --project=$PROJECT_ID

    # Grant necessary permissions
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/bigquery.dataViewer"

    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/bigquery.jobUser"

    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/pubsub.publisher"

    echo -e "${GREEN}✅ Created service account with permissions${NC}"
else
    echo -e "${GREEN}✅ Service account already exists${NC}"
fi

# Create Pub/Sub topic if it doesn't exist
echo -e "${YELLOW}📡 Creating Pub/Sub topic...${NC}"
if ! gcloud pubsub topics describe $TOPIC_NAME --project=$PROJECT_ID 2>/dev/null; then
    gcloud pubsub topics create $TOPIC_NAME --project=$PROJECT_ID
    echo -e "${GREEN}✅ Created Pub/Sub topic: $TOPIC_NAME${NC}"
else
    echo -e "${GREEN}✅ Pub/Sub topic already exists: $TOPIC_NAME${NC}"
fi

# Deploy the Cloud Function
echo -e "${YELLOW}☁️  Deploying Cloud Function...${NC}"
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=github_events_etl \
    --trigger-http \
    --allow-unauthenticated \
    --service-account="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --set-env-vars="PUBSUB_PROJECT_ID=$PROJECT_ID,PUBSUB_TOPIC_ID=$TOPIC_NAME" \
    --memory=1Gi \
    --timeout=540s

# Get the function URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(serviceConfig.uri)")
echo -e "${GREEN}✅ Cloud Function deployed: $FUNCTION_URL${NC}"

# Create Cloud Scheduler job
echo -e "${YELLOW}⏰ Creating Cloud Scheduler job...${NC}"

# Delete existing job if it exists
if gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$REGION 2>/dev/null; then
    echo "Deleting existing scheduler job..."
    gcloud scheduler jobs delete $SCHEDULER_JOB_NAME --location=$REGION --quiet
fi

# Create new scheduler job (runs every hour)
gcloud scheduler jobs create http $SCHEDULER_JOB_NAME \
    --location=$REGION \
    --schedule="0 * * * *" \
    --uri=$FUNCTION_URL \
    --http-method=POST \
    --time-zone="UTC" \
    --description="Hourly GitHub Archive ETL job"

echo -e "${GREEN}✅ Cloud Scheduler job created: $SCHEDULER_JOB_NAME${NC}"

# Test the function
echo -e "${YELLOW}🧪 Testing the function...${NC}"
curl -X POST $FUNCTION_URL

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Monitor logs: gcloud functions logs read $FUNCTION_NAME --region=$REGION"
echo "2. Test scheduler: gcloud scheduler jobs run $SCHEDULER_JOB_NAME --location=$REGION"
echo "3. View Pub/Sub messages: gcloud pubsub subscriptions pull --auto-ack your-subscription"