#!/usr/bin/env python3
"""
Process GitHub Archive events from Pub/Sub subscription.
This script pulls all available messages and processes them individually.
"""

import json
import logging
import os
import sys
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import PubsubMessage


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GitHubEventProcessor:
    """Process GitHub Archive events from Pub/Sub."""

    def __init__(self, project_id: str, subscription_id: str):
        self.project_id = project_id
        self.subscription_id = subscription_id
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(
            project_id, subscription_id
        )

    def process_single_message(self, message: PubsubMessage) -> bool:
        """
        Process a single GitHub event message.

        Args:
            message: The Pub/Sub message to process

        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Log raw message info for debugging
            logger.info(f"Message data type: {type(message.data)}, length: {len(message.data)}")

            # Try to decode the message data
            try:
                # First try direct UTF-8 decode
                raw_data = message.data.decode('utf-8')
                logger.info(f"Direct UTF-8 decode successful, length: {len(raw_data)}")
            except UnicodeDecodeError:
                # If that fails, the data might be binary - log the first few bytes
                logger.error(f"UTF-8 decode failed. First 50 bytes: {message.data[:50]}")
                return False

            # Parse JSON
            try:
                event_data = json.loads(raw_data)
                logger.info(f"JSON parse successful, type: {type(event_data)}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode failed: {e}. Raw data preview: {raw_data[:200]}")
                return False

            # Ensure event_data is a dictionary
            if not isinstance(event_data, dict):
                logger.error(f"Event data is not a dict, it's {type(event_data)}: {str(event_data)[:200]}")
                return False

            # Extract key information - add safety checks
            if not hasattr(event_data, 'get'):
                logger.error(f"event_data is not dict-like: {type(event_data)} = {str(event_data)[:200]}")
                return False

            event_type = event_data.get('type', 'unknown')
            event_id = event_data.get('id', 'unknown')
            created_at = event_data.get('created_at', 'unknown')

            # Safe repo name extraction
            repo_info = event_data.get('repo', {})
            if isinstance(repo_info, dict):
                repo_name = repo_info.get('name', 'unknown')
            else:
                repo_name = 'unknown'

            # Log event details
            logger.info(f"Processing {event_type} event {event_id} from {repo_name}")

            # Process based on event type
            if event_type == 'PullRequestEvent':
                self._process_pull_request(event_data)
            elif event_type == 'IssuesEvent':
                self._process_issue(event_data)
            elif event_type == 'ReleaseEvent':
                self._process_release(event_data)
            elif event_type == 'PushEvent':
                self._process_push(event_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")

            return True

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.error(f"Message attributes: {message.attributes if hasattr(message, 'attributes') else 'None'}")
            logger.error(f"Message data preview: {str(message.data)[:100] if hasattr(message, 'data') else 'No data'}")
            return False

    def _process_pull_request(self, event: Dict[str, Any]):
        """Process a Pull Request event."""
        payload = event.get('payload', {})

        # Handle case where payload is a JSON string
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse payload JSON string: {payload[:100]}...")
                return

        pr = payload.get('pull_request', {})
        action = payload.get('action', 'unknown')

        logger.info(f"PR {action}: #{pr.get('number')} - {pr.get('title', 'No title')}")

        # Add your PR processing logic here
        # Examples:
        # - Track PR metrics
        # - Send notifications
        # - Update databases
        # - Trigger CI/CD workflows

    def _process_issue(self, event: Dict[str, Any]):
        """Process an Issue event."""
        payload = event.get('payload', {})

        # Handle case where payload is a JSON string
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse payload JSON string: {payload[:100]}...")
                return

        issue = payload.get('issue', {})
        action = payload.get('action', 'unknown')

        logger.info(f"Issue {action}: #{issue.get('number')} - {issue.get('title', 'No title')}")

        # Add your issue processing logic here

    def _process_release(self, event: Dict[str, Any]):
        """Process a Release event."""
        payload = event.get('payload', {})

        # Handle case where payload is a JSON string
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse payload JSON string: {payload[:100]}...")
                return

        release = payload.get('release', {})
        action = payload.get('action', 'unknown')

        logger.info(f"Release {action}: {release.get('tag_name', 'No tag')} - {release.get('name', 'No name')}")

        # Add your release processing logic here

    def _process_push(self, event: Dict[str, Any]):
        """Process a Push event."""
        payload = event.get('payload', {})

        # Handle case where payload is a JSON string
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse payload JSON string: {payload[:100]}...")
                return

        commits = payload.get('commits', [])
        ref = payload.get('ref', 'unknown')

        logger.info(f"Push to {ref}: {len(commits)} commits")

        # Add your push processing logic here

    def pull_and_process_all(self, max_messages: int = 1000) -> int:
        """
        Pull and process all available messages from the subscription.

        Args:
            max_messages: Maximum number of messages to pull in one batch

        Returns:
            Total number of messages processed successfully
        """
        logger.info(f"Starting to pull messages from {self.subscription_path}")

        total_processed = 0
        total_failed = 0

        while True:
            # Pull messages synchronously
            try:
                response = self.subscriber.pull(
                    request={
                        "subscription": self.subscription_path,
                        "max_messages": max_messages,
                    }
                )

                if not response.received_messages:
                    logger.info("No more messages available")
                    break

                batch_size = len(response.received_messages)
                logger.info(f"Pulled {batch_size} messages")

                # Process messages with threading for better performance
                processed_count = 0
                failed_count = 0
                ack_ids = []

                with ThreadPoolExecutor(max_workers=10) as executor:
                    # Submit processing tasks
                    future_to_msg = {
                        executor.submit(self.process_single_message, msg.message): msg
                        for msg in response.received_messages
                    }

                    # Collect results
                    for future in as_completed(future_to_msg):
                        msg = future_to_msg[future]
                        try:
                            if future.result():
                                processed_count += 1
                                ack_ids.append(msg.ack_id)
                            else:
                                failed_count += 1
                                logger.warning(f"Failed to process message {msg.ack_id}")
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"Exception processing message {msg.ack_id}: {e}")

                # Acknowledge successfully processed messages
                if ack_ids:
                    try:
                        self.subscriber.acknowledge(
                            request={
                                "subscription": self.subscription_path,
                                "ack_ids": ack_ids,
                            }
                        )
                        logger.info(f"ACKed {len(ack_ids)} messages")
                    except Exception as e:
                        logger.error(f"Failed to ACK messages: {e}")

                total_processed += processed_count
                total_failed += failed_count

                logger.info(f"Batch complete: {processed_count} processed, {failed_count} failed")

                # If we got fewer messages than requested, we're done
                if batch_size < max_messages:
                    break

            except Exception as e:
                logger.error(f"Error pulling messages: {e}")
                break

        logger.info(f"Processing complete: {total_processed} total processed, {total_failed} total failed")

        # Return both counts so caller can decide success/failure
        return total_processed, total_failed


def main():
    """Main entry point."""
    project_id = os.getenv('PROJECT_ID')
    subscription_id = os.getenv('SUBSCRIPTION_ID')

    if not project_id or not subscription_id:
        logger.error("PROJECT_ID and SUBSCRIPTION_ID environment variables are required")
        sys.exit(1)

    processor = GitHubEventProcessor(project_id, subscription_id)

    try:
        processed_count, failed_count = processor.pull_and_process_all()

        # Output for GitHub Actions
        print(f"PROCESSED_COUNT={processed_count}")
        print(f"FAILED_COUNT={failed_count}")

        if failed_count > 0:
            failure_rate = failed_count / (processed_count + failed_count) * 100
            logger.error(f"❌ Job failed: {failed_count} messages failed to process ({failure_rate:.1f}% failure rate)")
            sys.exit(1)

        logger.info(f"✅ Successfully processed {processed_count} messages with no failures")

    except Exception as e:
        logger.error(f"❌ Processing failed with exception: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()