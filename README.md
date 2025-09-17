# GitHub Archive to Pub/Sub ETL Job

A Python 3.11 Cloud Function that queries GitHub Archive data from BigQuery and publishes events to Google Cloud Pub/Sub.

## Overview

This job runs hourly and:
1. Queries the dayparted `githubarchive.day.YYYYMMDD` table
2. Filters for specific GitHub event types (PullRequestEvent, IssuesEvent, ReleaseEvent, PushEvent)
3. Gets events from 2 hours ago (configurable buffer time)
4. Publishes all matching events to a Pub/Sub topic

## Configuration

Set these environment variables before deployment:

```bash
export PROJECT_ID="your-gcp-project"
export PUBSUB_TOPIC_ID="github-events"
```

Optional configuration (with defaults):
- `HOURS_BEHIND=2` - How many hours behind current time to query
- `BATCH_SIZE=100` - Pub/Sub batch publishing size
- `BQ_PROJECT_ID=githubarchive` - BigQuery project (usually githubarchive)
- `BQ_DATASET_ID=day` - BigQuery dataset

## Local Development

1. Install dependencies:
```bash
pip install -e .
```

2. Set environment variables:
```bash
export PUBSUB_PROJECT_ID="your-project"
export PUBSUB_TOPIC_ID="github-events"
```

3. Run locally:
```bash
python main.py
```

The function will be available at `http://localhost:8080`

## Deployment

1. Update configuration in `deploy.sh`
2. Run the deployment script:
```bash
./deploy.sh
```

This will:
- Enable required GCP APIs
- Create the Pub/Sub topic
- Deploy the Cloud Function
- Create an hourly Cloud Scheduler job

## Monitoring

- **Function logs**: `gcloud functions logs read github-events-etl --region=us-central1`
- **Test manually**: `curl -X POST <FUNCTION_URL>`
- **Trigger scheduler**: `gcloud scheduler jobs run github-etl-hourly --location=us-central1`

## Architecture

```
Cloud Scheduler (hourly) → Cloud Function → BigQuery → Pub/Sub Topic
```

The function queries GitHub Archive tables like `githubarchive.day.20250917` for events from the previous hour (with a 2-hour buffer to ensure data processing completion).

## Cost Estimation

For typical usage (hourly runs, small result sets):
- **Cloud Functions**: ~$1.20/month
- **BigQuery**: Minimal (queries public dataset)
- **Pub/Sub**: ~$0.40/month for 1M messages
- **Cloud Scheduler**: Free (≤3 jobs)

**Total**: ~$2/month