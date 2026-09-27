import os
import logging
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()
logger = logging.getLogger(__name__)

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

client = Client(ACCOUNT_SID, AUTH_TOKEN) if ACCOUNT_SID and AUTH_TOKEN else None

def send_message(to_number: str, text: str, media_url: str = None) -> bool:
    """Sends a WhatsApp message (and optional media) back via Twilio Sandbox."""
    if not client:
        print("ERROR: Twilio client not initialized.")
        return False

    # Force the whatsapp prefix on both numbers to guarantee it routes correctly
    final_to = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
    final_from = "whatsapp:+14155238886"

    print(f"\n--- DEBUG POST --- \nSending from: {final_from} \nSending to: {final_to}")
    if media_url:
        print(f"Attaching Media URL: {media_url}")

    try:
        kwargs = {
            "body": text,
            "from_": final_from,
            "to": final_to
        }
        
        # If the webhook passed an audio URL, attach it to the Twilio payload
        if media_url:
            kwargs["media_url"] = [media_url]
            
        client.messages.create(**kwargs)
        return True
    except Exception as e:
        print(f"ERROR sending message: {e}")
        return False