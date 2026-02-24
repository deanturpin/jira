#!/usr/bin/env python3
"""Log planning statistics over time for trend analysis."""

import csv
import os
from datetime import datetime
from pathlib import Path


class StatsLogger:
    """Track changes in planning estimates over time."""

    def __init__(self, stats_dir='../stats'):
        """Initialise logger with stats directory."""
        self.stats_dir = Path(stats_dir)
        self.stats_dir.mkdir(exist_ok=True)

    def log_epic_stats(self, project_key, epic_data):
        """Log per-epic statistics to track progress over time.

        Args:
            project_key: Project identifier
            epic_data: List of epic data dicts with keys: epic_key, epic_name,
                      remaining_points, completed_points, total_points, progress_pct
        """
        epic_stats_file = self.stats_dir / f"{project_key}_epics_history.csv"
        timestamp = datetime.now().isoformat()

        # Check if file exists to determine if we need headers
        file_exists = epic_stats_file.exists()

        # Write epic stats
        with open(epic_stats_file, 'a', newline='') as f:
            fieldnames = ['timestamp', 'epic_key', 'epic_name', 'remaining_points',
                         'completed_points', 'total_points', 'progress_pct']
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for epic in epic_data:
                writer.writerow({
                    'timestamp': timestamp,
                    'epic_key': epic['epic_key'],
                    'epic_name': epic['epic_name'],
                    'remaining_points': epic['remaining_points'],
                    'completed_points': epic['completed_points'],
                    'total_points': epic['total_points'],
                    'progress_pct': epic['progress_pct']
                })

    def get_epic_deltas(self, project_key):
        """Get the change in remaining points for each epic since last run.

        Returns:
            Dict mapping epic_key to delta in remaining_points.
            Negative = epic got closer to completion (good)
            Positive = epic got further away (scope increase)
            Zero = no change
        """
        epic_stats_file = self.stats_dir / f"{project_key}_epics_history.csv"

        if not epic_stats_file.exists():
            return {}

        with open(epic_stats_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if len(rows) < 2:
            return {}

        # Get unique timestamps (sorted)
        timestamps = sorted(set(r['timestamp'] for r in rows))
        if len(timestamps) < 2:
            return {}

        latest = timestamps[-1]
        previous = timestamps[-2]

        # Build maps of epic_key -> remaining_points for each timestamp
        latest_epics = {r['epic_key']: float(r['remaining_points'])
                       for r in rows if r['timestamp'] == latest}
        previous_epics = {r['epic_key']: float(r['remaining_points'])
                         for r in rows if r['timestamp'] == previous}

        # Calculate deltas
        deltas = {}
        for epic_key, current_remaining in latest_epics.items():
            if epic_key in previous_epics:
                delta = current_remaining - previous_epics[epic_key]
                deltas[epic_key] = delta
            # If epic is new, no delta

        return deltas

    def log_planning_stats(self, project_key, epic_timeline, velocity_stats, team_size, target_velocity=None):
        """Log current planning statistics to CSV file.

        Args:
            project_key: Project identifier
            epic_timeline: List of epic timeline data
            velocity_stats: Velocity statistics dict
            team_size: Number of developers
            target_velocity: Target velocity if set
        """
        stats_file = self.stats_dir / f"{project_key}_history.csv"

        # Calculate aggregate statistics
        timestamp = datetime.now().isoformat()
        total_epics = len(epic_timeline)
        total_points = sum(e['remaining_points'] for e in epic_timeline)

        # Find completion date (latest end date)
        completion_date = max(e['end_date'][:10] for e in epic_timeline) if epic_timeline else 'N/A'

        # Calculate total duration in weeks
        if epic_timeline:
            start_date = min(e['start_date'][:10] for e in epic_timeline)
            end_date = max(e['end_date'][:10] for e in epic_timeline)
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            total_weeks = (end_dt - start_dt).days / 7.0
        else:
            total_weeks = 0.0

        # Determine which velocity is being used
        avg_velocity = velocity_stats['mean']
        actual_velocity = velocity_stats.get('actual_mean', avg_velocity)
        using_target = target_velocity is not None

        # Create record
        record = {
            'timestamp': timestamp,
            'date': timestamp[:10],
            'time': timestamp[11:19],
            'total_epics': total_epics,
            'total_points': total_points,
            'completion_date': completion_date,
            'total_weeks': round(total_weeks, 1),
            'team_size': team_size,
            'velocity_mean': round(avg_velocity, 1),
            'velocity_median': round(velocity_stats.get('median', 0), 1),
            'velocity_stddev': round(velocity_stats.get('stddev', 0), 1),
            'using_target_velocity': using_target,
            'target_velocity': round(target_velocity, 1) if target_velocity else 'N/A',
            'actual_velocity': round(actual_velocity, 1)
        }

        # Check if file exists to determine if we need headers
        file_exists = stats_file.exists()

        # Append to CSV
        with open(stats_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=record.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)

        print(f"✓ Stats logged: {stats_file}")

        return record

    def get_history(self, project_key):
        """Read historical stats for a project.

        Returns:
            List of stats records (dicts)
        """
        stats_file = self.stats_dir / f"{project_key}_history.csv"

        if not stats_file.exists():
            return []

        with open(stats_file, 'r') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def generate_trend_chart(self, project_key):
        """Generate visualization of planning trends over time.

        Creates a chart showing how estimates have changed.
        """
        history = self.get_history(project_key)

        if len(history) < 2:
            print(f"Not enough history to generate trend chart (need at least 2 data points)")
            return None

        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from datetime import datetime as dt

        # Parse data
        dates = [dt.fromisoformat(r['timestamp']) for r in history]
        total_points = [float(r['total_points']) for r in history]
        total_epics = [int(r['total_epics']) for r in history]
        completion_dates = [r['completion_date'] for r in history]

        # Create figure with subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))

        # Plot 1: Total remaining points over time
        ax1.plot(dates, total_points, marker='o', linewidth=2, markersize=6, color='#0052cc')
        ax1.set_ylabel('Total Story Points', fontsize=11, fontweight='bold')
        ax1.set_title(f'{project_key.upper()} Planning Trends Over Time',
                     fontsize=14, fontweight='bold', pad=15)
        ax1.grid(True, alpha=0.3)

        # Plot 2: Number of epics over time
        ax2.plot(dates, total_epics, marker='s', linewidth=2, markersize=6, color='#de350a')
        ax2.set_ylabel('Number of Epics', fontsize=11, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # Plot 3: Projected completion date over time
        # Convert completion dates to datetime for plotting
        completion_dts = []
        plot_dates = []
        for i, comp_date in enumerate(completion_dates):
            if comp_date != 'N/A':
                try:
                    completion_dts.append(dt.strptime(comp_date, '%Y-%m-%d'))
                    plot_dates.append(dates[i])
                except ValueError:
                    pass

        if completion_dts:
            ax3.plot(plot_dates, completion_dts, marker='d', linewidth=2, markersize=6, color='#5fa321')
            ax3.set_ylabel('Projected Completion', fontsize=11, fontweight='bold')
            ax3.set_xlabel('Measurement Date', fontsize=11, fontweight='bold')
            ax3.grid(True, alpha=0.3)

            # Format y-axis as dates
            import matplotlib.dates as mdates
            ax3.yaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax3.yaxis.get_majorticklabels(), rotation=45, ha='right')

        # Format x-axis for all plots
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()

        # Save chart
        output_file = f'../public/{project_key}_trends.png'
        fig.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✓ Trend chart saved: {output_file}")

        return output_file
