# External Libraries
import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")


async def download_media(media_url: str) -> bytes | None:
    """
    Downloads incoming WhatsApp images or audio notes from Twilio using HTTP Basic Auth.
    Returns raw binary data for downstream OCR or speech processing.
    """
    if not ACCOUNT_SID or not AUTH_TOKEN:
        logger.error("Missing Twilio credentials for media download.")
        return None

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(media_url, auth=(ACCOUNT_SID, AUTH_TOKEN))
            if response.status_code == 200:
                logger.info(f"Successfully downloaded media ({len(response.content)} bytes)")
                return response.content
            else:
                logger.error(f"Failed to fetch media: Status {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error downloading media from {media_url}: {e}")
        return None