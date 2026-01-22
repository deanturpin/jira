"""Jira API client for extracting planning data."""

import requests
from typing import Any
import os


class JiraClient:
    """Client for interacting with Jira REST API."""

    def __init__(self, url: str, email: str, api_token: str):
        self.url = url.rstrip('/')
        self.auth = (email, api_token)
        self.headers = {'Accept': 'application/json'}

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make GET request to Jira API."""
        response = requests.get(
            f'{self.url}/rest/agile/1.0{endpoint}',
            auth=self.auth,
            headers=self.headers,
            params=params or {}
        )
        response.raise_for_status()
        return response.json()

    def get_board_sprints(self, board_id: int, max_results: int = 50) -> list[dict[str, Any]]:
        """Get all sprints for a board, including completed ones."""
        sprints = []
        start_at = 0

        while True:
            data = self._get(
                f'/board/{board_id}/sprint',
                params={'startAt': start_at, 'maxResults': max_results}
            )
            sprints.extend(data.get('values', []))

            if data.get('isLast', True):
                break
            start_at += max_results

        return sprints

    def get_sprint_issues(self, sprint_id: int) -> list[dict[str, Any]]:
        """Get all issues in a sprint with story points."""
        issues = []
        start_at = 0
        max_results = 50

        while True:
            data = self._get(
                f'/sprint/{sprint_id}/issue',
                params={
                    'startAt': start_at,
                    'maxResults': max_results,
                    'fields': 'summary,status,customfield_10016,issuetype,created,resolutiondate'
                }
            )
            issues.extend(data.get('issues', []))

            if start_at + max_results >= data.get('total', 0):
                break
            start_at += max_results

        return issues

    def get_epics(self, board_id: int) -> list[dict[str, Any]]:
        """Get all epics for a board."""
        epics = []
        start_at = 0
        max_results = 50

        while True:
            data = self._get(
                f'/board/{board_id}/epic',
                params={'startAt': start_at, 'maxResults': max_results}
            )
            epics.extend(data.get('values', []))

            if data.get('isLast', True):
                break
            start_at += max_results

        return epics

    def get_epic_issues(self, epic_id: int) -> list[dict[str, Any]]:
        """Get all issues in an epic."""
        issues = []
        start_at = 0
        max_results = 50

        while True:
            data = self._get(
                f'/epic/{epic_id}/issue',
                params={
                    'startAt': start_at,
                    'maxResults': max_results,
                    'fields': 'summary,status,customfield_10016,issuetype'
                }
            )
            issues.extend(data.get('issues', []))

            if start_at + max_results >= data.get('total', 0):
                break
            start_at += max_results

        return issues

    def get_story_points(self, issue: dict[str, Any]) -> float:
        """Extract story points from an issue (customfield_10016 is typical for story points)."""
        fields = issue.get('fields', {})
        story_points = fields.get('customfield_10016')
        return float(story_points) if story_points else 0.0

    def is_issue_completed(self, issue: dict[str, Any]) -> bool:
        """Check if an issue is completed based on status."""
        status = issue.get('fields', {}).get('status', {}).get('name', '').lower()
        return status in ['done', 'closed', 'resolved']
