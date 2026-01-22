"""Calculate team velocity and capacity from historical sprint data."""

from datetime import datetime, timedelta
from typing import Any
import statistics


class VelocityCalculator:
    """Calculates velocity metrics from sprint data."""

    def __init__(self, jira_client):
        self.client = jira_client

    def calculate_sprint_velocity(self, sprint: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate velocity metrics for a single sprint."""
        total_points = 0.0
        completed_points = 0.0

        for issue in issues:
            points = self.client.get_story_points(issue)
            total_points += points
            if self.client.is_issue_completed(issue):
                completed_points += points

        return {
            'sprint_name': sprint.get('name', 'Unknown'),
            'sprint_id': sprint.get('id'),
            'state': sprint.get('state', 'unknown'),
            'start_date': sprint.get('startDate'),
            'end_date': sprint.get('endDate'),
            'total_points': total_points,
            'completed_points': completed_points,
            'completion_rate': completed_points / total_points if total_points > 0 else 0.0
        }

    def get_historical_velocity(self, board_id: int, num_sprints: int = 6) -> list[dict[str, Any]]:
        """Get velocity data for the last N completed sprints."""
        sprints = self.client.get_board_sprints(board_id)

        # Filter to completed sprints only and sort by end date
        completed_sprints = [
            s for s in sprints
            if s.get('state') == 'closed' and s.get('endDate')
        ]
        completed_sprints.sort(
            key=lambda s: datetime.fromisoformat(s['endDate'].replace('Z', '+00:00')),
            reverse=True
        )

        velocity_data = []
        for sprint in completed_sprints[:num_sprints]:
            issues = self.client.get_sprint_issues(sprint['id'])
            velocity_data.append(self.calculate_sprint_velocity(sprint, issues))

        # Return in chronological order
        return list(reversed(velocity_data))

    def calculate_average_velocity(self, velocity_data: list[dict[str, Any]]) -> float:
        """Calculate average completed points across sprints."""
        if not velocity_data:
            return 0.0

        completed_points = [v['completed_points'] for v in velocity_data]
        return statistics.mean(completed_points)

    def calculate_velocity_stats(self, velocity_data: list[dict[str, Any]]) -> dict[str, float]:
        """Calculate statistical metrics for velocity."""
        if not velocity_data:
            return {'mean': 0.0, 'median': 0.0, 'std_dev': 0.0, 'min': 0.0, 'max': 0.0}

        completed_points = [v['completed_points'] for v in velocity_data]

        return {
            'mean': statistics.mean(completed_points),
            'median': statistics.median(completed_points),
            'std_dev': statistics.stdev(completed_points) if len(completed_points) > 1 else 0.0,
            'min': min(completed_points),
            'max': max(completed_points)
        }

    def project_sprint_capacity(
        self,
        velocity_data: list[dict[str, Any]],
        num_future_sprints: int = 10,
        confidence_factor: float = 0.8
    ) -> list[dict[str, Any]]:
        """Project future sprint capacity based on historical velocity."""
        avg_velocity = self.calculate_average_velocity(velocity_data)
        conservative_velocity = avg_velocity * confidence_factor

        if not velocity_data:
            last_sprint_end = datetime.now()
        else:
            last_sprint_end = datetime.fromisoformat(
                velocity_data[-1]['end_date'].replace('Z', '+00:00')
            )

        projections = []
        for i in range(1, num_future_sprints + 1):
            sprint_start = last_sprint_end + timedelta(days=1)
            sprint_end = sprint_start + timedelta(weeks=1)  # 1-week sprints

            projections.append({
                'sprint_number': i,
                'start_date': sprint_start.isoformat(),
                'end_date': sprint_end.isoformat(),
                'projected_capacity': conservative_velocity,
                'optimistic_capacity': avg_velocity
            })

            last_sprint_end = sprint_end

        return projections
