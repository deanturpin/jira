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
                    'fields': 'summary,status,customfield_10016,customfield_10026,customfield_10031,issuetype,created,resolutiondate'
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

    def get_epic_issues(self, epic_key: str) -> list[dict[str, Any]]:
        """Get all issues in an epic using JQL search."""
        issues = []
        start_at = 0
        max_results = 50

        while True:
            response = requests.get(
                f'{self.url}/rest/api/3/search',
                auth=self.auth,
                headers=self.headers,
                params={
                    'jql': f'parent = {epic_key}',
                    'startAt': start_at,
                    'maxResults': max_results,
                    'fields': 'summary,status,customfield_10016,issuetype'
                }
            )
            response.raise_for_status()
            data = response.json()

            issues.extend(data.get('issues', []))

            if start_at + max_results >= data.get('total', 0):
                break
            start_at += max_results

        return issues

    def get_story_points(self, issue: dict[str, Any]) -> float:
        """Extract story points from an issue.

        Checks multiple common story point fields:
        - customfield_10016: Story Points (CIT project)
        - customfield_10026: Story point estimate
        - customfield_10031: Story Points (IVEMCS project)
        Uses whichever field is populated.
        """
        fields = issue.get('fields', {})

        # Try common story point fields in order
        for field_id in ['customfield_10016', 'customfield_10026', 'customfield_10031']:
            story_points = fields.get(field_id)
            if story_points:
                return float(story_points)

        return 0.0

    def is_issue_completed(self, issue: dict[str, Any]) -> bool:
        """Check if an issue is completed based on status."""
        status = issue.get('fields', {}).get('status', {}).get('name', '').lower()
        return status in ['done', 'closed', 'resolved']
