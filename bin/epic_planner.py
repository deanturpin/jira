"""Epic timeline projection based on team capacity and story points."""

from datetime import datetime
from typing import Any


class EpicPlanner:
    """Plans epic completion timelines based on velocity and capacity."""

    def __init__(self, jira_client, velocity_calculator):
        self.client = jira_client
        self.velocity_calc = velocity_calculator

    def get_epic_data(self, board_id: int) -> list[dict[str, Any]]:
        """Get all epics with their story point totals."""
        epics = self.client.get_epics(board_id)
        epic_data = []

        for epic in epics:
            # Skip done epics
            if epic.get('done', False):
                continue

            issues = self.client.get_epic_issues(epic['key'])

            total_points = 0.0
            completed_points = 0.0
            remaining_points = 0.0

            for issue in issues:
                points = self.client.get_story_points(issue)
                total_points += points

                if self.client.is_issue_completed(issue):
                    completed_points += points
                else:
                    remaining_points += points

            epic_data.append({
                'id': epic.get('id'),
                'key': epic.get('key'),
                'name': epic.get('name', 'Unnamed Epic'),
                'total_points': total_points,
                'completed_points': completed_points,
                'remaining_points': remaining_points,
                'completion_percentage': (completed_points / total_points * 100) if total_points > 0 else 0.0
            })

        # Sort by remaining points (descending) to prioritise larger epics
        epic_data.sort(key=lambda e: e['remaining_points'], reverse=True)
        return epic_data

    def calculate_epic_timeline(
        self,
        epics: list[dict[str, Any]],
        sprint_projections: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Calculate when each epic will complete based on sprint capacity."""
        timeline = []
        available_capacity = []

        # Create a list of available capacity per sprint
        for projection in sprint_projections:
            available_capacity.append({
                'sprint_number': projection['sprint_number'],
                'start_date': projection['start_date'],
                'end_date': projection['end_date'],
                'capacity': projection['projected_capacity'],
                'remaining_capacity': projection['projected_capacity'],
                'assigned_epics': []
            })

        # Allocate epics to sprints based on remaining points
        for epic in epics:
            if epic['remaining_points'] == 0:
                continue

            remaining_work = epic['remaining_points']
            epic_sprints = []
            start_sprint = None
            end_sprint = None

            for sprint in available_capacity:
                if remaining_work <= 0:
                    break

                # Allocate work to this sprint
                allocated = min(remaining_work, sprint['remaining_capacity'])
                if allocated > 0:
                    remaining_work -= allocated
                    sprint['remaining_capacity'] -= allocated
                    sprint['assigned_epics'].append({
                        'epic_key': epic['key'],
                        'epic_name': epic['name'],
                        'points_allocated': allocated
                    })
                    epic_sprints.append(sprint['sprint_number'])

                    if start_sprint is None:
                        start_sprint = sprint
                    end_sprint = sprint

            # If we couldn't allocate all work, mark as beyond planning horizon
            completion_status = 'scheduled' if remaining_work <= 0 else 'beyond_horizon'

            timeline.append({
                'epic_key': epic['key'],
                'epic_name': epic['name'],
                'total_points': epic['total_points'],
                'completed_points': epic['completed_points'],
                'remaining_points': epic['remaining_points'],
                'start_sprint': start_sprint['sprint_number'] if start_sprint else None,
                'end_sprint': end_sprint['sprint_number'] if end_sprint else None,
                'start_date': start_sprint['start_date'] if start_sprint else None,
                'end_date': end_sprint['end_date'] if end_sprint else None,
                'sprint_count': len(epic_sprints),
                'status': completion_status
            })

        return timeline, available_capacity

    def generate_gantt_data(
        self,
        timeline: list[dict[str, Any]],
        sprint_projections: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate data structure suitable for Gantt chart visualisation."""
        gantt_rows = []

        for item in timeline:
            if item['status'] == 'beyond_horizon':
                continue

            gantt_rows.append({
                'task': f"{item['epic_key']}: {item['epic_name']}",
                'start': item['start_date'],
                'end': item['end_date'],
                'duration_sprints': item['sprint_count'],
                'points': item['remaining_points']
            })

        return {
            'tasks': gantt_rows,
            'sprint_boundaries': [
                {
                    'sprint': s['sprint_number'],
                    'start': s['start_date'],
                    'end': s['end_date']
                }
                for s in sprint_projections
            ]
        }
