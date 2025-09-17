import json
import logging
from typing import Dict, Any, List
from concurrent.futures import as_completed

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import PublisherClient
from google.cloud.pubsub_v1.publisher.futures import Future

from config import Config


class PubSubClient:
    """Client for publishing messages to Google Cloud Pub/Sub."""

    def __init__(self):
        self.client = PublisherClient()
        self.topic_path = self.client.topic_path(
            Config.PUBSUB_PROJECT_ID,
            Config.PUBSUB_TOPIC_ID
        )
        self.logger = logging.getLogger(__name__)

    def publish_events(self, events: List[Dict[str, Any]]) -> int:
        """
        Publish GitHub events to Pub/Sub in batches.

        Args:
            events: List of event dictionaries to publish

        Returns:
            Number of successfully published messages
        """
        if not events:
            self.logger.info("No events to publish")
            return 0

        self.logger.info(f"Publishing {len(events)} events to {self.topic_path}")

        # Batch the events
        batches = self._create_batches(events, Config.BATCH_SIZE)
        published_count = 0
        futures = []

        try:
            # Publish all batches
            for batch in batches:
                for event in batch:
                    # Convert event to JSON string
                    message_data = json.dumps(event, ensure_ascii=False).encode('utf-8')

                    # Add attributes for filtering/routing
                    attributes = {
                        'event_type': event.get('type', 'unknown'),
                        'created_at': event.get('created_at', ''),
                        'source': 'github_archive'
                    }

                    # Publish message (non-blocking)
                    future = self.client.publish(
                        self.topic_path,
                        message_data,
                        **attributes
                    )
                    futures.append(future)

            # Wait for all publishes to complete
            for future in as_completed(futures):
                try:
                    message_id = future.result(timeout=30)
                    published_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to publish message: {str(e)}")

            self.logger.info(f"Successfully published {published_count}/{len(events)} messages")
            return published_count

        except Exception as e:
            self.logger.error(f"Batch publish failed: {str(e)}")
            raise

    def _create_batches(self, items: List[Any], batch_size: int) -> List[List[Any]]:
        """Split a list into batches of specified size."""
        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i:i + batch_size])
        return batches

    def publish_single_event(self, event: Dict[str, Any]) -> str:
        """
        Publish a single event to Pub/Sub.

        Args:
            event: Event dictionary to publish

        Returns:
            Message ID of published message
        """
        try:
            # Convert event to JSON string
            message_data = json.dumps(event, ensure_ascii=False).encode('utf-8')

            # Add attributes
            attributes = {
                'event_type': event.get('type', 'unknown'),
                'created_at': event.get('created_at', ''),
                'source': 'github_archive'
            }

            # Publish message
            future = self.client.publish(
                self.topic_path,
                message_data,
                **attributes
            )

            message_id = future.result(timeout=30)
            self.logger.debug(f"Published message {message_id}")
            return message_id

        except Exception as e:
            self.logger.error(f"Failed to publish single message: {str(e)}")
            raise