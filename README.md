# GitHub Archive Data Pipeline

A two-process data pipeline that extracts GitHub Archive events and processes them independently for high availability.

## Architecture

The system consists of two independent processes with separate schedulers to avoid single points of failure:

### Process 1: Data Extraction (BQ → Pub/Sub)
**Cloud Scheduler** → **Cloud Function** → **BigQuery** → **Pub/Sub Topic**

- Runs hourly at `:00` (1:00, 2:00, 3:00...)
- Queries GitHub Archive dayparted tables (`githubarchive.day.YYYYMMDD`)
- Filters for: PullRequestEvent, IssuesEvent, ReleaseEvent, PushEvent
- Publishes events to Pub/Sub topic with 2-hour processing buffer

### Process 2: Event Processing (Pub/Sub → Processing)
**GitHub Actions Cron** → **Python Processor** → **Pub/Sub Subscription**

- Runs hourly at `:15` (1:15, 2:15, 3:15...) - 15 minute offset
- Pulls all available messages from subscription
- Processes events by type with individual ACKing
- Threaded processing for performance

## Key Features

- **Independent Processes**: Each has its own scheduler and failure domain
- **No Single Point of Failure**: Process failures are isolated
- **Robust Message Handling**: Individual ACKing, proper error handling
- **Scalable Processing**: Threaded Python processor handles all available messages
- **Cost Effective**: ~$2/month for typical usage

## Quick Start

1. **Deploy Process 1 (Data Extraction)**:
   ```bash
   # Set GitHub repository secret: GCP_SA_KEY
   # Run "Deploy to GCP" GitHub Action
   ```

2. **Process 2 runs automatically** via GitHub Actions cron

## Configuration

### Environment Variables (Process 1)
- `PROJECT_ID=evm-attest` - GCP project
- `PUBSUB_TOPIC_ID=github-events` - Pub/Sub topic name
- `HOURS_BEHIND=2` - Query offset (default: 2 hours)
- `BATCH_SIZE=100` - Pub/Sub batch size

### GitHub Secrets Required
- `GCP_SA_KEY` - Service account JSON key for deployment and processing

## Deployment

### Initial Setup
1. Add the `GCP_SA_KEY` secret to your GitHub repository
2. Run the "Deploy to GCP" GitHub Action workflow
3. Process 2 will start automatically on the next `:15` interval

### Manual Deployment
```bash
export PROJECT_ID=evm-attest
export PUBSUB_TOPIC_ID=github-events
./deploy.sh
```

## Processing Logic

The Python processor (`process_messages.py`) handles events by type:

- **PullRequestEvent**: PR creation, updates, merges
- **IssuesEvent**: Issue creation, closing, comments
- **ReleaseEvent**: New releases, tags
- **PushEvent**: Code commits

Extend the `_process_*` methods to add custom processing logic.

## Monitoring

### Process 1 (Cloud Function)
```bash
gcloud functions logs read github-events-etl --region=us-central1
gcloud scheduler jobs run github-etl-hourly --location=us-central1
```

### Process 2 (GitHub Actions)
- View workflow runs in GitHub Actions tab
- Check logs for message processing details

### Pub/Sub Monitoring
```bash
# Check topic and subscription status
gcloud pubsub topics describe github-events
gcloud pubsub subscriptions describe github-events-processor
```

## Failure Scenarios

- **Process 1 fails**: Messages stop flowing, Process 2 processes remaining backlog
- **Process 2 fails**: Messages accumulate in Pub/Sub, will be processed when recovered
- **Both fail**: No data loss, messages retained in Pub/Sub (7-day retention)

## Cost Breakdown

- **Cloud Functions**: ~$1.20/month (hourly execution)
- **Cloud Scheduler**: Free (≤3 jobs)
- **Pub/Sub**: ~$0.40/month (1M messages)
- **BigQuery**: Minimal (queries public dataset)
- **GitHub Actions**: Free (public repo)

**Total**: ~$2/month