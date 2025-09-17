import json
import logging
from datetime import datetime
from typing import Iterator, Dict, Any

from google.cloud import bigquery
from config import Config


class BigQueryClient:
    """Client for querying GitHub Archive data from BigQuery."""

    def __init__(self):
        self.client = bigquery.Client()
        self.logger = logging.getLogger(__name__)

    def query_github_events(
        self,
        min_timestamp: datetime,
        max_timestamp: datetime
    ) -> Iterator[Dict[str, Any]]:
        """
        Query GitHub events from the dayparted table within the time range.

        Args:
            min_timestamp: Start time for filtering events
            max_timestamp: End time for filtering events

        Yields:
            Dict representing each row from BigQuery
        """
        # Use the date from min_timestamp to determine which table to query
        table_name = Config.get_table_name(min_timestamp)

        # Format timestamps for BigQuery
        min_ts_str = min_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        max_ts_str = max_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Build the SQL query based on your example
        query = f"""
        SELECT * FROM `{table_name}`
        WHERE TRUE
        AND type IN ('PullRequestEvent', 'IssuesEvent', 'ReleaseEvent', 'PushEvent')
        AND created_at >= @min_timestamp
        AND created_at < @max_timestamp
        AND repo.name IN (SELECT repository FROM `evm-attest.cyberstorm.github_repositories`)
        ORDER BY created_at ASC
        """

        # Configure query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("min_timestamp", "TIMESTAMP", min_timestamp),
                bigquery.ScalarQueryParameter("max_timestamp", "TIMESTAMP", max_timestamp),
            ]
        )

        self.logger.info(
            f"Querying table {table_name} for events between {min_ts_str} and {max_ts_str}"
        )

        try:
            # Execute the query
            query_job = self.client.query(query, job_config=job_config)

            # Stream results to avoid loading all data into memory
            for row in query_job:
                # Convert BigQuery Row to dictionary
                row_dict = dict(row)

                # Convert datetime objects to ISO strings for JSON serialization
                for key, value in row_dict.items():
                    if isinstance(value, datetime):
                        row_dict[key] = value.isoformat()

                yield row_dict

        except Exception as e:
            self.logger.error(f"BigQuery query failed: {str(e)}")
            raise

    def get_row_count(self, min_timestamp: datetime, max_timestamp: datetime) -> int:
        """
        Get the count of rows that would be returned by the main query.
        Useful for logging and monitoring.
        """
        table_name = Config.get_table_name(min_timestamp)

        query = f"""
        SELECT COUNT(*) as row_count
        FROM `{table_name}`
        WHERE TRUE
        AND type IN ('PullRequestEvent', 'IssuesEvent', 'ReleaseEvent', 'PushEvent')
        AND created_at >= @min_timestamp
        AND created_at < @max_timestamp
        AND repo.name IN (SELECT repository FROM `evm-attest.cyberstorm.github_repositories`)
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("min_timestamp", "TIMESTAMP", min_timestamp),
                bigquery.ScalarQueryParameter("max_timestamp", "TIMESTAMP", max_timestamp),
            ]
        )

        try:
            query_job = self.client.query(query, job_config=job_config)
            result = list(query_job)[0]
            return result.row_count
        except Exception as e:
            self.logger.error(f"Row count query failed: {str(e)}")
            return 0