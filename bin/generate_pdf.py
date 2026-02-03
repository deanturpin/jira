#!/usr/bin/env python3
"""Generate PDF reports combining dashboard metrics and Gantt charts."""

import os
import sys
import io
import base64
import math
from datetime import datetime
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, PageTemplate, Frame, NextPageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image as PILImage

from jira_client import JiraClient
from velocity_calculator import VelocityCalculator
import requests


def create_velocity_chart(velocity_data, velocity_stats, actual_velocity=None):
    """Create velocity trend chart as temporary image.

    Args:
        velocity_data: List of sprint velocity data
        velocity_stats: Velocity statistics (may contain target velocity if set)
        actual_velocity: Actual historical velocity (if target velocity is active)
    """
    if not velocity_data:
        return None

    fig, ax = plt.subplots(figsize=(10, 4))

    sprint_names = [s['sprint_name'] for s in velocity_data]
    completed_points = [s['completed_points'] for s in velocity_data]

    x = range(len(sprint_names))
    ax.bar(x, completed_points, color='#667eea', alpha=0.7, label='Completed Points')

    # Show both target and actual velocity lines if target is set
    if actual_velocity is not None:
        # Target velocity line (using velocity_stats['mean'] which contains target)
        target_velocity = velocity_stats['mean']
        ax.axhline(y=target_velocity, color='orange', linestyle='--', linewidth=2, label=f'Target: {target_velocity:.1f}')
        # Actual velocity line
        ax.axhline(y=actual_velocity, color='green', linestyle='--', linewidth=2, label=f'Actual Mean: {actual_velocity:.1f}')
    else:
        # Just show mean velocity line
        ax.axhline(y=velocity_stats['mean'], color='#cc4748', linestyle='--', linewidth=2, label=f'Mean: {velocity_stats["mean"]:.1f}')

    ax.set_xlabel('Sprint', fontweight='bold')
    ax.set_ylabel('Story Points', fontweight='bold')
    ax.set_title('Sprint Velocity History', fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(sprint_names, rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()

    # Save to bytes buffer
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def get_jira_colour_hex(colour_key):
    """Map Jira colour keys to actual Jira hex values."""
    # Actual Jira epic colours from https://gist.github.com/jusuchin85/efa658429befb73916b40b1e1a773762
    colour_map = {
        'color_1': '#8d542e',   # Brown
        'color_2': '#ff8b00',   # Orange
        'color_3': '#ffab01',   # Light orange
        'color_4': '#0052cc',   # Blue (default)
        'color_5': '#505f79',   # Grey-blue
        'color_6': '#5fa321',   # Green
        'color_7': '#cd4288',   # Pink/Magenta
        'color_8': '#5143aa',   # Purple
        'color_9': '#ff8f73',   # Coral/Salmon
        'color_10': '#2584ff',  # Bright blue
        'color_11': '#018da6',  # Teal
        'color_12': '#6b778c',  # Grey
        'color_13': '#03875a',  # Dark green
        'color_14': '#de350a',  # Red/Orange-red
    }
    return colors.HexColor(colour_map.get(colour_key, colour_map['color_4']))


def create_header_footer(canvas_obj, doc):
    """Add header and footer to each page."""
    canvas_obj.saveState()

    # Footer
    canvas_obj.setFont('Helvetica', 8)
    canvas_obj.setFillColor(colors.grey)
    canvas_obj.drawString(
        30 * mm,
        10 * mm,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    canvas_obj.drawRightString(
        doc.pagesize[0] - 30 * mm,
        10 * mm,
        f"Page {doc.page}"
    )

    canvas_obj.restoreState()


def generate_project_pdf(client, project_key, board_id, team_size, jira_url, target_velocity=None, exclude_epics=None):
    """Generate PDF report for a single project.

    Args:
        exclude_epics: List of epic numbers to exclude (e.g., ['123', '456'])
    """
    if exclude_epics is None:
        exclude_epics = []

    # Convert to full epic keys for filtering
    exclude_keys = {f"{project_key.upper()}-{num}" for num in exclude_epics}

    # Get velocity data
    print("Fetching velocity data...")
    velocity_calc = VelocityCalculator(client)
    velocity_data = velocity_calc.get_historical_velocity(board_id, months=6)
    velocity_stats = velocity_calc.calculate_velocity_stats(velocity_data)

    # Apply target velocity if set (prefer parameter over environment variable)
    if target_velocity is None:
        target_velocity = os.getenv('TARGET_VELOCITY') or os.getenv('VELOCITY_OVERRIDE')  # Fallback to old name
        if target_velocity:
            target_velocity = float(target_velocity)

    is_target_velocity = bool(target_velocity)
    actual_velocity = None
    if target_velocity:
        actual_velocity = velocity_stats['mean']
        velocity_stats['mean'] = target_velocity

    avg_velocity = velocity_stats['mean']

    # Get epic data
    print("Fetching epic data...")
    url = os.getenv('JIRA_URL').rstrip('/')
    auth = (os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

    # Fetch epics from board API (has colour info)
    board_epic_response = requests.get(
        f'{url}/rest/agile/1.0/board/{board_id}/epic',
        auth=auth,
        headers={'Accept': 'application/json'},
        params={'maxResults': 200}
    )

    board_epics = board_epic_response.json().get('values', []) if board_epic_response.status_code == 200 else []
    board_epic_keys = {e['key'] for e in board_epics}

    # Fetch all project epics via JQL to catch any not on board
    jql_response = requests.post(
        f'{url}/rest/api/3/search/jql',
        auth=auth,
        headers=headers,
        json={
            'jql': f'project = {project_key.upper()} AND type = Epic',
            'maxResults': 200,
            'fields': ['summary', 'status', 'customfield_10021']  # customfield_10021 is Flagged
        }
    )

    # Combine: board epics have colour, JQL epics fill gaps
    epics = list(board_epics)  # Start with board epics (have colours)

    # Create flagged status lookup from JQL response
    flagged_epics = {}
    if jql_response.status_code == 200:
        jql_epics = jql_response.json().get('issues', [])
        for issue in jql_epics:
            # Store flagged status (customfield_10021)
            is_flagged = issue['fields'].get('customfield_10021') is not None
            flagged_epics[issue['key']] = is_flagged

            # Add epics from JQL that aren't in board (won't have colour)
            if issue['key'] not in board_epic_keys:
                status_name = issue['fields'].get('status', {}).get('name', '').lower()
                is_done = status_name in ['done', 'closed', 'resolved']
                epics.append({
                    'key': issue['key'],
                    'summary': issue['fields'].get('summary', 'Unnamed'),
                    'name': issue['fields'].get('summary', 'Unnamed'),
                    'done': is_done,
                    'color': {'key': 'color_4'}  # default colour for non-board epics
                })

    # Filter out excluded epics
    active_epics = [e for e in epics if not e.get('done', False) and e['key'] not in exclude_keys]
    if exclude_keys:
        print(f"  Excluding epics: {', '.join(sorted(exclude_keys))}")

    if active_epics:

        # Get remaining points for each epic
        epic_data = []
        for epic in active_epics:
            epic_key = epic['key']
            epic_name = epic.get('summary', epic.get('name', 'Unnamed'))
            epic_colour = epic.get('color', {}).get('key', 'color_4')

            issue_response = requests.post(
                f'{url}/rest/api/3/search/jql',
                auth=auth,
                headers=headers,
                json={
                    'jql': f'parent = {epic_key}',
                    'maxResults': 200,
                    'fields': ['customfield_10016', 'customfield_10026', 'customfield_10031', 'status']
                }
            )

            if issue_response.status_code != 200:
                continue

            issues = issue_response.json().get('issues', [])

            total_points = 0.0
            completed_points = 0.0
            for issue in issues:
                points = issue['fields'].get('customfield_10016') or issue['fields'].get('customfield_10026') or issue['fields'].get('customfield_10031')
                points = float(points) if points else 0.0
                total_points += points

                status = issue['fields'].get('status', {}).get('name', '').lower()
                if status in ['done', 'closed', 'resolved']:
                    completed_points += points

            remaining_points = total_points - completed_points

            if remaining_points > 0:
                epic_data.append({
                    'epic_key': epic_key,
                    'epic_name': epic_name,
                    'total_points': total_points,
                    'completed_points': completed_points,
                    'remaining_points': remaining_points,
                    'progress_pct': (completed_points / total_points * 100) if total_points > 0 else 0,
                    'colour': epic_colour
                })

    # Sort by remaining work (most first) to prioritise high-value epics
    epic_data.sort(key=lambda e: e['remaining_points'], reverse=True)

    # Calculate parallel completion dates
    from datetime import datetime, timedelta
    if velocity_data:
        last_sprint_end = datetime.fromisoformat(velocity_data[-1]['end_date'].replace('Z', '+00:00'))
    else:
        last_sprint_end = datetime.now()

    project_start = last_sprint_end + timedelta(days=1)
    velocity_per_person = avg_velocity / team_size if team_size > 0 else avg_velocity

    tracks = [project_start for _ in range(team_size)]

    for epic in epic_data:
        sprints_needed = epic['remaining_points'] / velocity_per_person if velocity_per_person > 0 else 0
        days_needed = int(sprints_needed * 7)
        if days_needed < 1:
            days_needed = 1

        earliest_track_idx = min(range(len(tracks)), key=lambda i: tracks[i])
        start_date = tracks[earliest_track_idx]
        end_date = start_date + timedelta(days=days_needed)

        epic['est_completion'] = end_date.strftime('%Y-%m-%d')
        epic['assigned_dev'] = earliest_track_idx + 1

        tracks[earliest_track_idx] = end_date + timedelta(days=1)

    # Calculate totals
    total_remaining = sum(e['remaining_points'] for e in epic_data)
    final_completion = max(tracks).strftime('%Y-%m-%d') if epic_data else 'N/A'
    sprints_remaining = int(total_remaining / avg_velocity) if avg_velocity > 0 else 0

    # Create PDF
    print(f"Generating PDF for {project_key.upper()}...")
    output_file = f'../public/{project_key}.pdf'

    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    # Define page templates for mixed orientation
    portrait_frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id='portrait_frame'
    )
    landscape_frame = Frame(
        20*mm, 20*mm,
        landscape(A4)[0] - 40*mm,
        landscape(A4)[1] - 40*mm,
        id='landscape_frame'
    )

    portrait_template = PageTemplate(id='portrait', frames=[portrait_frame], pagesize=A4)
    landscape_template = PageTemplate(id='landscape', frames=[landscape_frame], pagesize=landscape(A4))

    doc.addPageTemplates([portrait_template, landscape_template])

    story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=15,
        alignment=TA_CENTER
    )
    story.append(Paragraph(f"{project_key.upper()} Planning Report", title_style))

    # Timestamp
    timestamp_style = ParagraphStyle(
        'Timestamp',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", timestamp_style))
    story.append(Spacer(1, 5*mm))

    # Metrics summary table (portrait-optimised)
    velocity_label = 'Target Velocity' if is_target_velocity else 'Average Velocity'
    if is_target_velocity:
        velocity_text = f'{avg_velocity:.0f} pts/sprint (target)\n{actual_velocity:.0f} pts/sprint (actual)'
    else:
        velocity_text = f'{avg_velocity:.0f} pts/sprint\n± {velocity_stats["std_dev"]:.0f}'

    metrics_data = [
        ['Team Size', velocity_label, 'Remaining Work', 'Projected Completion'],
        [
            f'{team_size} developers',
            velocity_text,
            f'{total_remaining:.0f} points\n{len(epic_data)} epics',
            f'{final_completion}\n~{sprints_remaining} sprints'
        ]
    ]

    metrics_table = Table(metrics_data, colWidths=[42*mm, 42*mm, 42*mm, 44*mm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    story.append(metrics_table)
    story.append(Spacer(1, 8*mm))

    # Sprint velocity trend combined with summary on first page
    velocity_chart_buf = create_velocity_chart(velocity_data, velocity_stats, actual_velocity)
    if velocity_chart_buf:
        velocity_img = Image(velocity_chart_buf, width=170*mm, height=70*mm)
        story.append(velocity_img)

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        f"Showing {len(velocity_data)} most recent sprints. "
        f"Latest sprint: {velocity_data[-1]['completed_points']:.0f} points. "
        f"Coefficient of variation: {(velocity_stats['std_dev']/velocity_stats['mean']*100):.0f}%",
        ParagraphStyle('small', parent=styles['Normal'], fontSize=8)
    ))

    # Switch to landscape for Gantt chart
    story.append(NextPageTemplate('landscape'))
    story.append(PageBreak())

    # Gantt chart on landscape page
    gantt_path = f'../public/{project_key}_gantt.png'
    if os.path.exists(gantt_path):
        img = Image(gantt_path, width=250*mm, height=140*mm, kind='proportional')
        story.append(img)
    else:
        story.append(Paragraph("Gantt chart not found. Run generate_gantt.py first.", styles['Normal']))

    # Switch back to portrait for Epic Breakdown
    story.append(NextPageTemplate('portrait'))
    story.append(PageBreak())

    # Calculate per-developer velocity
    per_dev_velocity = avg_velocity / team_size if team_size > 0 else 0

    # Epic breakdown table
    epic_table_data = [
        ['Epic', 'Name', 'Remaining', 'Completed', 'Total', 'Progress', 'Weeks']
    ]

    # Build table and collect colour styling
    epic_table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]

    for idx, epic in enumerate(epic_data):
        row_idx = idx + 1  # +1 because of header row

        # Calculate weeks for 1 developer (sprints are 1 week each)
        # Round up to next whole week
        weeks_needed = epic['remaining_points'] / per_dev_velocity if per_dev_velocity > 0 else 0
        weeks_needed = math.ceil(weeks_needed)

        # Add flag indicator if epic is flagged
        epic_name = epic['epic_name']
        epic_key_text = epic['epic_key']
        if flagged_epics.get(epic['epic_key'], False):
            epic_key_text = f"{epic['epic_key']} 🛑"  # Stop sign after epic number

        # Create clickable link to Jira epic
        epic_url = f"{jira_url}/browse/{epic['epic_key']}"
        epic_key_link = f'<link href="{epic_url}" color="white">{epic_key_text}</link>'
        epic_key_display = Paragraph(epic_key_link, styles['Normal'])

        epic_table_data.append([
            epic_key_display,
            epic_name[:35] + '...' if len(epic_name) > 35 else epic_name,
            f"{epic['remaining_points']:.0f}",
            f"{epic['completed_points']:.0f}",
            f"{epic['total_points']:.0f}",
            f"{epic['progress_pct']:.0f}%",
            f"{weeks_needed}"
        ])

        # Add colour bar to left of epic key (red if flagged, otherwise epic colour)
        if flagged_epics.get(epic['epic_key'], False):
            epic_colour = colors.HexColor('#DC143C')  # Crimson red for flagged
            text_colour = colors.white  # White text on red
        else:
            epic_colour = get_jira_colour_hex(epic['colour'])
            text_colour = colors.white

        epic_table_styles.append(('BACKGROUND', (0, row_idx), (0, row_idx), epic_colour))
        epic_table_styles.append(('TEXTCOLOR', (0, row_idx), (0, row_idx), text_colour))
        epic_table_styles.append(('FONTSIZE', (0, row_idx), (0, row_idx), 11))  # Larger font for epic key

    epic_table = Table(epic_table_data, colWidths=[22*mm, 55*mm, 16*mm, 16*mm, 16*mm, 16*mm, 16*mm])
    epic_table.setStyle(TableStyle(epic_table_styles))

    story.append(epic_table)

    # Add historical trends chart if it exists
    trends_path = f'../public/{project_key}_trends.png'
    if os.path.exists(trends_path):
        story.append(PageBreak())
        story.append(Paragraph('Historical Planning Trends', title_style))
        story.append(Spacer(1, 5*mm))
        trends_img = Image(trends_path, width=170*mm, height=127.5*mm, kind='proportional')
        story.append(trends_img)
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(
            "Tracks how planning estimates change over time. "
            "Use to detect scope creep, velocity drift, and estimate accuracy.",
            ParagraphStyle('small', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
        ))

    # Build PDF
    doc.build(story, onFirstPage=create_header_footer, onLaterPages=create_header_footer)

    print(f"✓ PDF report saved: {output_file}")
    return output_file


def main():
    """Generate PDF reports for all configured projects."""
    load_dotenv()

    required_vars = ['JIRA_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN']
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
    jira_url = os.getenv('JIRA_URL', '').rstrip('/')

    # Find all project configurations
    projects = []
    i = 1
    while True:
        project_key = os.getenv(f'JIRA_PROJECT_KEY_{i}')
        board_id = os.getenv(f'JIRA_BOARD_ID_{i}')

        if not project_key or not board_id:
            break

        team_size = int(os.getenv(f'TEAM_SIZE_{i}', '5'))
        target_velocity = os.getenv(f'TARGET_VELOCITY_{i}')
        exclude_epics = os.getenv(f'EXCLUDE_EPICS_{i}', '')
        exclude_list = [epic.strip() for epic in exclude_epics.split(',') if epic.strip()]
        projects.append({
            'key': project_key.lower(),
            'board_id': int(board_id),
            'team_size': team_size,
            'target_velocity': float(target_velocity) if target_velocity else None,
            'exclude_epics': exclude_list
        })
        i += 1

    if not projects:
        project_key = os.getenv('JIRA_PROJECT_KEY')
        board_id = os.getenv('JIRA_BOARD_ID')

        if not project_key or not board_id:
            print("Error: No project configuration found")
            sys.exit(1)

        team_size = int(os.getenv('TEAM_SIZE', '5'))
        target_velocity = os.getenv('TARGET_VELOCITY')
        exclude_epics = os.getenv('EXCLUDE_EPICS', '')
        exclude_list = [epic.strip() for epic in exclude_epics.split(',') if epic.strip()]
        projects.append({
            'key': project_key.lower(),
            'board_id': int(board_id),
            'team_size': team_size,
            'target_velocity': float(target_velocity) if target_velocity else None,
            'exclude_epics': exclude_list
        })

    print(f"\nFound {len(projects)} project(s) to process\n")

    # Generate PDF for each project
    output_files = []
    for project in projects:
        print(f"{'='*60}")
        print(f"Processing project: {project['key'].upper()}")
        print(f"{'='*60}")

        output_file = generate_project_pdf(
            client,
            project['key'],
            project['board_id'],
            project['team_size'],
            jira_url,
            project.get('target_velocity'),
            project.get('exclude_epics', [])
        )
        output_files.append(output_file)
        print()

    print(f"\n{'='*60}")
    print(f"✓ All PDF reports generated successfully")
    print(f"{'='*60}")
    for output_file in output_files:
        print(f"  {output_file}")


if __name__ == '__main__':
    main()
