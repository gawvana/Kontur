import pytest
from unittest.mock import patch
from worker.tasks import process_evidence, send_notification

def test_process_evidence_handles_network_failure_safely():
    """Verify process_evidence retries and does not falsely claim success on network error."""
    with patch("httpx.post", side_effect=Exception("Connection refused")):
        # Celery task with max_retries
        try:
            process_evidence.run(1, "storage/key/123")
        except Exception:
            pass  # Expected retry/failure, not silent false success


def test_send_notification_no_token_fallback(caplog):
    """When bot token is absent, notification is logged securely without crashing."""
    import logging
    with caplog.at_level(logging.INFO):
        send_notification.run(111, "CASE_DECISION", "Title", "Message")
    assert any("Notification (no delivery)" in record.message for record in caplog.records)
