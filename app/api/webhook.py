import os
from pathlib import Path
from fastapi import APIRouter, Request, BackgroundTasks, Response, status
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage

from app.api.meta_client import send_message
from app.api.media import download_media
from app.agent.graph import app_graph
from app.tools.speech import speech_to_text, text_to_speech  

router = APIRouter(prefix="/webhook", tags=["Webhook"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

active_sessions = {}

# <-- NEW ROUTE: Twilio needs a public URL to download the audio reply -->
@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        return FileResponse(file_path, media_type="audio/ogg")
    return Response(status_code=status.HTTP_404_NOT_FOUND)

async def process_incoming_message(from_number: str, text_payload: str, media_url: str | None, media_type: str | None, base_url: str):
    if from_number not in active_sessions:
        active_sessions[from_number] = {
            "phone_number": from_number,
            "messages": [],
            "is_eligible": None,
            "rejection_reason": None,
            "aadhaar_number": None,
            "land_survey_number": None,
            "bank_account_verified": None,
            "missing_fields": [],
            "human_escalation_required": False
        }

    state = active_sessions[from_number]
    user_prompt = text_payload.strip()
    
    # Reset media path for this turn
    state["media_path"] = None
    is_voice = False

    if media_url:
        media_bytes = await download_media(media_url)
        if media_bytes:
            # 1. Voice Note Processing (STT)
            if media_type and "audio" in media_type:
                is_voice = True
                audio_file = UPLOAD_DIR / f"{from_number}_temp_audio.ogg"
                with open(audio_file, "wb") as f:
                    f.write(media_bytes)

                try:
                    print("\n[System] Transcribing voice note...")
                    user_prompt = speech_to_text(audio_file)
                    print(f"[Whisper]: {user_prompt}")
                except Exception as e:
                    print(f"[STT Error]: {e}")
                    user_prompt = "Voice note received, but transcription failed."

            # 2. Document Image Processing (Handoff to LangGraph)
            elif media_type and "image" in media_type:
                image_file = UPLOAD_DIR / f"{from_number}_temp_image.png"
                with open(image_file, "wb") as f:
                    f.write(media_bytes)

                # Send the path to graph.py so it can properly route and validate OCR
                state["media_path"] = str(image_file)
                if not user_prompt:
                    user_prompt = "I have uploaded my document image."

    if not user_prompt:
        return

    # Invoke LangGraph
    state["messages"].append(HumanMessage(content=user_prompt))
    new_state = app_graph.invoke(state)
    active_sessions[from_number] = new_state

    # Transmit response back to WhatsApp
    # Transmit response back to WhatsApp
    last_message = new_state["messages"][-1]
    if last_message.type == "ai":
        reply_text = last_message.content.strip()
        
        # FAILSAFE: If the LLM blanks out or Whisper hallucinates, never send an empty string
        if not reply_text:
            reply_text = "I'm sorry, I couldn't understand that clearly. Could you please repeat your question in English, Hindi, or Kannada?"
        
        # 3. Voice Output Generation (TTS)
        # 3. Voice Output Generation (TTS)
        if is_voice:
            reply_filename = f"{from_number}_reply_audio.ogg"
            reply_path = UPLOAD_DIR / reply_filename
            try:
                print("[System] Generating voice reply...")
                # Use the async function and actually await it
                await text_to_speech(reply_text, str(reply_path))
                
                # Create the public ngrok URL for Twilio
                public_audio_url = f"{base_url}/webhook/audio/{reply_filename}"
                
                send_message(from_number, reply_text, media_url=public_audio_url)
            except Exception as e:
                print(f"[TTS Error]: {e}")
                # Fallback to text if FFmpeg or Edge-TTS fails
                send_message(from_number, reply_text)
        else:
            send_message(from_number, reply_text)

@router.post("")
async def receive_twilio_whatsapp(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()

    raw_from = form_data.get("From", "")
    from_number = raw_from.replace("whatsapp:", "")
    body_text = form_data.get("Body", "")
    num_media = int(form_data.get("NumMedia", 0))

    media_url = form_data.get("MediaUrl0") if num_media > 0 else None
    media_type = form_data.get("MediaContentType0") if num_media > 0 else None
    
    # Grab the active ngrok URL dynamically
    base_url = str(request.base_url).rstrip("/")

    background_tasks.add_task(
        process_incoming_message,
        from_number=from_number,
        text_payload=body_text,
        media_url=media_url,
        media_type=media_type,
        base_url=base_url
    )

    return Response(content="<Response></Response>", media_type="application/xml", status_code=status.HTTP_200_OK)