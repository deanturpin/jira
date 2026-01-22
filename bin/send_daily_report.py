#!/usr/bin/env python3
"""Send daily Jira report via email with PDF attachment."""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import requests
import base64

load_dotenv()


def send_email_with_attachment(to_email, pdf_path):
    """Send email via Resend API with PDF attachment."""
    resend_api_key = os.getenv('RESEND_API_KEY')
    if not resend_api_key:
        print("Error: RESEND_API_KEY not found in environment")
        sys.exit(1)

    # Read PDF file and encode as base64
    with open(pdf_path, 'rb') as f:
        pdf_content = base64.b64encode(f.read()).decode('utf-8')

    project_key = os.path.basename(pdf_path).replace('_', ' ').replace('.pdf', '').upper()
    today = datetime.now().strftime('%Y-%m-%d')

    # Simple HTML email body
    html_body = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #667eea;">📊 Jira Daily Report</h2>
        <p>Project: <strong>{project_key}</strong></p>
        <p>Date: {today}</p>
        <p>Your daily planning report is attached as a PDF.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #888;">
            Generated automatically by Jira Planning Tools
        </p>
    </body>
    </html>
    """

    payload = {
        'from': 'hello@turpin.dev',
        'to': [to_email],
        'subject': f'📊 Jira Daily Report - {project_key} - {today}',
        'html': html_body,
        'attachments': [
            {
                'filename': os.path.basename(pdf_path),
                'content': pdf_content,
            }
        ]
    }

    response = requests.post(
        'https://api.resend.com/emails',
        headers={
            'Authorization': f'Bearer {resend_api_key}',
            'Content-Type': 'application/json',
        },
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✓ Email sent successfully!")
        print(f"  Message ID: {result.get('id')}")
        print(f"  To: {to_email}")
        print(f"  Attachment: {os.path.basename(pdf_path)}")
    else:
        print(f"✗ Email failed: {response.status_code}")
        print(f"  Response: {response.text}")
        sys.exit(1)


def main():
    """Send daily reports for all projects."""
    if len(sys.argv) < 2:
        print("Usage: python send_daily_report.py <email@example.com>")
        sys.exit(1)

    to_email = sys.argv[1]

    # Find all PDF reports in public directory
    public_dir = os.path.join(os.path.dirname(__file__), '..', 'public')
    pdf_files = [f for f in os.listdir(public_dir) if f.endswith('.pdf')]

    if not pdf_files:
        print("Error: No PDF reports found in public/")
        print("Run 'make' first to generate reports")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF report(s)")
    print()

    for pdf_file in pdf_files:
        pdf_path = os.path.join(public_dir, pdf_file)
        print(f"Sending {pdf_file}...")
        send_email_with_attachment(to_email, pdf_path)
        print()


if __name__ == '__main__':
    main()
