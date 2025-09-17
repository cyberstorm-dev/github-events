import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any

import functions_framework
from flask import Request

from config import Config
from bq_client import BigQueryClient
from pubsub_client import PubSubClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



@functions_framework.http
def github_events_etl(request: Request) -> Dict[str, Any]:
    """
    Cloud Function entry point for GitHub Archive ETL job.

    This function:
    1. Calculates the time window for querying (2 hours behind current time)
    2. Queries GitHub Archive BigQuery table for specific event types
    3. Publishes the results to a Pub/Sub topic

    Args:
        request: HTTP request object (unused, but required for Cloud Functions)

    Returns:
        Dict with job execution results
    """
    start_time = datetime.now(timezone.utc)
    logger.info(f"Starting GitHub events ETL job at {start_time}")

    try:
        # Validate configuration
        Config.validate_config()

        # Calculate time window
        current_time = datetime.now(timezone.utc)
        min_timestamp = Config.get_min_timestamp(current_time)
        max_timestamp = Config.get_max_timestamp(min_timestamp)

        logger.info(f"Querying events from {min_timestamp} to {max_timestamp}")

        # Initialize clients
        bq_client = BigQueryClient()
        pubsub_client = PubSubClient()

        # Get row count first for logging
        row_count = bq_client.get_row_count(min_timestamp, max_timestamp)
        logger.info(f"Expected {row_count} events to process")

        if row_count == 0:
            logger.info("No events found in time window")
            return {
                "status": "success",
                "message": "No events found in time window",
                "events_processed": 0,
                "events_published": 0,
                "execution_time_seconds": (datetime.now(timezone.utc) - start_time).total_seconds()
            }

        # Query BigQuery and collect events
        events = []
        for event in bq_client.query_github_events(min_timestamp, max_timestamp):
            events.append(event)

            # Process in chunks to avoid memory issues (though with <5MB this shouldn't be a problem)
            if len(events) >= 1000:
                published_count = pubsub_client.publish_events(events)
                logger.info(f"Published batch of {published_count} events")
                events = []  # Clear the batch

        # Publish remaining events
        published_count = 0
        if events:
            published_count = pubsub_client.publish_events(events)

        # Calculate final metrics
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()

        result = {
            "status": "success",
            "message": f"Successfully processed GitHub events",
            "events_processed": row_count,
            "events_published": published_count,
            "execution_time_seconds": execution_time,
            "time_window": {
                "start": min_timestamp.isoformat(),
                "end": max_timestamp.isoformat()
            }
        }

        logger.info(f"Job completed successfully: {result}")
        return result

    except Exception as e:
        error_msg = f"GitHub events ETL job failed: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")

        return {
            "status": "error",
            "message": error_msg,
            "events_processed": 0,
            "events_published": 0,
            "execution_time_seconds": (datetime.now(timezone.utc) - start_time).total_seconds()
        }


def main():
    """Local development entry point."""
    # This allows you to test the function locally
    from flask import Flask, request as flask_request

    app = Flask(__name__)

    @app.route('/', methods=['POST', 'GET'])
    def local_test():
        return github_events_etl(flask_request)

    logger.info("Starting local development server on http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)


if __name__ == '__main__':
    main()