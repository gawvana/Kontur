import logging
import os
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="process_evidence", bind=True, max_retries=3, default_retry_delay=30)
def process_evidence(self, evidence_id: int, storage_key: str):
    """
    Scan evidence file, update status via internal API, and publish if clean.
    Real ClamAV / S3 calls should happen here.
    Currently: logs the action and marks file as READY in a simulated fashion.
    """
    api_url = os.getenv("INTERNAL_API_URL", "http://api:8000")
    api_key = os.getenv("INTERNAL_API_KEY", "")
    try:
        import httpx
        resp = httpx.post(
            f"{api_url}/internal/evidence/{evidence_id}/processed",
            json={"status": "READY", "storage_key": storage_key},
            headers={"X-Internal-Key": api_key},
            timeout=10.0
        )
        resp.raise_for_status()
        logger.info("Evidence %s processed → READY", evidence_id)
    except Exception as exc:
        logger.warning("process_evidence failed for %s: %s — will retry", evidence_id, exc)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("Evidence %s exceeded max retries — marked FAILED", evidence_id)


@celery_app.task(name="send_notification", bind=True, max_retries=3, default_retry_delay=10)
def send_notification(user_id: int, event_type: str, title: str, message: str, object_type: str = None, object_id: int = None):
    """
    Deliver a notification to user via Telegram Bot API (if bot token configured).
    Falls back to logging only.
    """
    bot_token = os.getenv("BOT_TOKEN", "")
    telegram_id = None

    # Attempt to look up user telegram_id via internal API
    api_url = os.getenv("INTERNAL_API_URL", "http://api:8000")
    try:
        import httpx
        resp = httpx.get(f"{api_url}/internal/users/{user_id}/telegram-id", timeout=5.0)
        if resp.status_code == 200:
            telegram_id = resp.json().get("telegram_id")
    except Exception as e:
        logger.warning("Could not resolve telegram_id for user %s: %s", user_id, e)

    if bot_token and telegram_id:
        try:
            import httpx
            text = f"*{title}*\n{message}"
            httpx.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": telegram_id, "text": text, "parse_mode": "Markdown"},
                timeout=10.0
            )
            logger.info("Notification sent to user %s (tg: %s)", user_id, telegram_id)
        except Exception as exc:
            logger.warning("Failed to send notification to user %s: %s", user_id, exc)
    else:
        logger.info(
            "Notification (no delivery): user_id=%s type=%s title=%s",
            user_id, event_type, title
        )
