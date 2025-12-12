"""Background tasks."""
import time
from datetime import datetime
from typing import Any, Dict


def send_email_task(to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Simulate sending an email.

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        Task result dictionary
    """
    print(f"[{datetime.now()}] Sending email to {to}")
    print(f"Subject: {subject}")
    print(f"Body: {body[:100]}...")

    # Simulate work
    time.sleep(2)

    return {
        "status": "sent",
        "to": to,
        "sent_at": datetime.now().isoformat(),
    }


def process_data_task(data_id: str, options: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Simulate data processing.

    Args:
        data_id: ID of data to process
        options: Processing options

    Returns:
        Task result dictionary
    """
    print(f"[{datetime.now()}] Processing data: {data_id}")
    print(f"Options: {options}")

    # Simulate work
    time.sleep(3)

    return {
        "status": "processed",
        "data_id": data_id,
        "records_processed": 1000,
        "processed_at": datetime.now().isoformat(),
    }


def generate_report_task(report_type: str, parameters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Simulate report generation.

    Args:
        report_type: Type of report
        parameters: Report parameters

    Returns:
        Task result dictionary
    """
    print(f"[{datetime.now()}] Generating report: {report_type}")
    print(f"Parameters: {parameters}")

    # Simulate work
    time.sleep(4)

    return {
        "status": "generated",
        "report_type": report_type,
        "report_url": f"/reports/{report_type}_{datetime.now().timestamp()}.pdf",
        "generated_at": datetime.now().isoformat(),
    }


def cleanup_old_jobs_task(days: int = 7) -> Dict[str, Any]:
    """
    Cleanup old jobs.

    Args:
        days: Number of days to keep jobs

    Returns:
        Task result dictionary
    """
    print(f"[{datetime.now()}] Cleaning up jobs older than {days} days")

    # Simulate work
    time.sleep(1)

    return {
        "status": "cleaned",
        "jobs_deleted": 42,
        "cleaned_at": datetime.now().isoformat(),
    }
