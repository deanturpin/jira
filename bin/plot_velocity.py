#!/usr/bin/env python3
"""Plot velocity chart for all sprints."""

import os
import sys
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

from jira_client import JiraClient
from velocity_calculator import VelocityCalculator


def main():
    """Generate velocity chart."""
    load_dotenv()

    required_vars = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN', 'JIRA_BOARD_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    print("Connecting to Jira...")
    client = JiraClient(
        url=os.getenv('JIRA_URL'),
        email=os.getenv('JIRA_EMAIL'),
        api_token=os.getenv('JIRA_API_TOKEN')
    )

    velocity_calc = VelocityCalculator(client)
    board_id = int(os.getenv('JIRA_BOARD_ID'))
    project_key = os.getenv('JIRA_PROJECT_KEY', 'project').lower()

    print("Fetching completed sprints (last 6 months)...")
    # Fetch completed sprints from last 6 months
    sprints = client.get_board_sprints(board_id)
    completed_sprints = [
        s for s in sprints
        if s.get('state') == 'closed' and s.get('endDate')
    ]

    # Filter to last 6 months
    from datetime import timezone, timedelta
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=6 * 30)
    completed_sprints = [
        s for s in completed_sprints
        if datetime.fromisoformat(s['endDate'].replace('Z', '+00:00')) >= cutoff_date
    ]

    if not completed_sprints:
        print("No completed sprints found in last 6 months.")
        sys.exit(1)

    # Sort chronologically
    completed_sprints.sort(
        key=lambda s: datetime.fromisoformat(s['endDate'].replace('Z', '+00:00'))
    )

    print(f"Found {len(completed_sprints)} completed sprints")
    print("Calculating velocity for each sprint...")

    velocity_data = []
    for sprint in completed_sprints:
        issues = client.get_sprint_issues(sprint['id'])
        velocity_data.append(velocity_calc.calculate_sprint_velocity(sprint, issues))

    # Extract data for plotting
    sprint_names = [v['sprint_name'] for v in velocity_data]
    end_dates = [datetime.fromisoformat(v['end_date'].replace('Z', '+00:00')) for v in velocity_data]
    completed_points = [v['completed_points'] for v in velocity_data]
    committed_points = [v['total_points'] for v in velocity_data]

    # Calculate moving average
    window_size = 3
    moving_avg = []
    for i in range(len(completed_points)):
        start_idx = max(0, i - window_size + 1)
        window = completed_points[start_idx:i + 1]
        moving_avg.append(sum(window) / len(window))

    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot bars for committed and completed
    x_positions = range(len(sprint_names))
    width = 0.35

    bars1 = ax.bar([x - width/2 for x in x_positions], committed_points,
                    width, label='Committed', color='lightblue', alpha=0.7)
    bars2 = ax.bar([x + width/2 for x in x_positions], completed_points,
                    width, label='Completed', color='darkblue', alpha=0.7)

    # Plot moving average line
    ax.plot(x_positions, moving_avg, color='red', linewidth=2,
            marker='o', label=f'{window_size}-Sprint Moving Average')

    # Add mean line
    mean_velocity = sum(completed_points) / len(completed_points)
    ax.axhline(y=mean_velocity, color='green', linestyle='--',
               linewidth=2, label=f'Average ({mean_velocity:.1f} pts)')

    # Formatting
    ax.set_xlabel('Sprint', fontsize=12, fontweight='bold')
    ax.set_ylabel('Story Points', fontsize=12, fontweight='bold')
    ax.set_title('Sprint Velocity Analysis', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(sprint_names, rotation=45, ha='right')
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Add value labels on bars
    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}',
                   ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    # Save to file
    output_file = f'../public/{project_key}_velocity_chart.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nChart saved to: {output_file}")

    # Print statistics
    print("\n=== Velocity Statistics ===")
    print(f"Total sprints analysed: {len(completed_points)}")
    print(f"Average velocity: {mean_velocity:.1f} points/sprint")
    print(f"Minimum: {min(completed_points):.1f} points")
    print(f"Maximum: {max(completed_points):.1f} points")
    print(f"Latest sprint: {completed_points[-1]:.1f} points")

    if len(completed_points) > 1:
        import statistics
        std_dev = statistics.stdev(completed_points)
        print(f"Standard deviation: {std_dev:.1f} points")
        print(f"Coefficient of variation: {(std_dev/mean_velocity)*100:.1f}%")

    # Don't show plot interactively - just save to file
    # plt.show()


if __name__ == '__main__':
    main()
