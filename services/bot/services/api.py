import logging
import httpx
from typing import Optional, Dict, Any, List
from config import settings

logger = logging.getLogger(__name__)

class BackendAPI:
    def __init__(self):
        self.base_url = settings.backend_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Look up user by Telegram ID via internal endpoint."""
        try:
            resp = await self.client.get(f"/internal/users/by-telegram/{telegram_id}")
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning("Backend API get_user failed: %s", e)
        return None

    async def search_subjects(self, query: str, token: str) -> List[Dict[str, Any]]:
        """Search subjects with user token."""
        try:
            resp = await self.client.get(
                f"/subjects/search?q={query}",
                headers={"Authorization": f"Bearer {token}"}
            )
            if resp.status_code == 200:
                return resp.json().get("items", [])
        except Exception as e:
            logger.warning("Backend API search failed: %s", e)
        return []

    async def create_support_ticket(self, user_token: str, subject: str, message: str) -> bool:
        """Create a support ticket."""
        try:
            resp = await self.client.post(
                "/support",
                json={"subject": subject, "message": message},
                headers={"Authorization": f"Bearer {user_token}"}
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning("Backend API support ticket failed: %s", e)
            return False

    async def close(self):
        await self.client.aclose()


backend_api = BackendAPI()
