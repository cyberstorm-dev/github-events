import os
from datetime import datetime, timedelta, timezone
from typing import List


class Config:
    """Configuration settings for the BigQuery to Pub/Sub job."""

    # BigQuery settings
    BQ_PROJECT_ID = os.getenv("BQ_PROJECT_ID", "githubarchive")
    BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "day")
    BQ_TABLE_PREFIX = os.getenv("BQ_TABLE_PREFIX", "")  # Empty for githubarchive.day.YYYYMMDD

    # Pub/Sub settings
    PUBSUB_PROJECT_ID = os.getenv("PUBSUB_PROJECT_ID")  # Required
    PUBSUB_TOPIC_ID = os.getenv("PUBSUB_TOPIC_ID")     # Required

    # GitHub event types to filter
    EVENT_TYPES = [
        "PullRequestEvent",
        "IssuesEvent",
        "ReleaseEvent",
        "PushEvent"
    ]

    # Processing settings
    HOURS_BEHIND = int(os.getenv("HOURS_BEHIND", "2"))  # Default: 2 hours behind current time
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))    # Pub/Sub batch size

    @classmethod
    def get_table_name(cls, target_date: datetime) -> str:
        """Generate the dayparted table name for a given date."""
        date_str = target_date.strftime("%Y%m%d")
        return f"{cls.BQ_PROJECT_ID}.{cls.BQ_DATASET_ID}.{cls.BQ_TABLE_PREFIX}{date_str}"

    @classmethod
    def get_min_timestamp(cls, current_time: datetime = None) -> datetime:
        """Calculate the minimum timestamp to query (HOURS_BEHIND ago)."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Round down to the hour and subtract HOURS_BEHIND
        rounded_time = current_time.replace(minute=0, second=0, microsecond=0)
        return rounded_time - timedelta(hours=cls.HOURS_BEHIND)

    @classmethod
    def get_max_timestamp(cls, min_timestamp: datetime) -> datetime:
        """Calculate the maximum timestamp (1 hour after min_timestamp)."""
        return min_timestamp + timedelta(hours=1)

    @classmethod
    def validate_config(cls):
        """Validate that required configuration is present."""
        if not cls.PUBSUB_PROJECT_ID:
            raise ValueError("PUBSUB_PROJECT_ID environment variable is required")
        if not cls.PUBSUB_TOPIC_ID:
            raise ValueError("PUBSUB_TOPIC_ID environment variable is required")