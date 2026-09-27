"""
Mirai Gijutsu Speech Module

Features:
    1. Speech -> Text
    2. Text -> Speech

Languages:
    - Kannada
    - Hindi
    - English

STT:
    faster-whisper

TTS:
    edge-tts -> temporary MP3 -> FFmpeg -> OGG/Opus

STT behavior:
    - Preserves the spoken language.
    - Saves transcript beside the source audio.
    - Uses UTF-8 so Kannada/Hindi are preserved.
    - Forces the requested language when provided.
    - Avoids repeated/hallucinated text where possible.

Example:

    test_kannada.ogg
        ->
    test_kannada.txt
"""

# ============================================================================
# EXTERNAL LIBRARIES
# ============================================================================

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Union

import edge_tts

try:
    from dotenv import load_dotenv

    # Load backend/.env automatically.
    load_dotenv()

except ImportError:
    # dotenv is optional. Environment variables will still work.
    pass


PathLike = Union[str, os.PathLike]


# ============================================================================
# ERROR
# ============================================================================

class SpeechProcessingError(RuntimeError):
    """Raised when speech processing fails."""


# ============================================================================
# DEFAULT TTS VOICES
# ============================================================================

DEFAULT_VOICES = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "kn": "kn-IN-SapnaNeural",
}


# ============================================================================
# WHISPER MODEL
# ============================================================================

_whisper_model: Any = None


def _get_whisper_model() -> Any:
    """
    Load Whisper only when STT is requested.

    Recommended:
        medium + CPU + int8

    For faster testing:
        small + CPU + int8
    """

    global _whisper_model

    if _whisper_model is not None:
        return _whisper_model

    try:
        from faster_whisper import WhisperModel

    except ImportError as exc:
        raise SpeechProcessingError(
            "faster-whisper is not installed.\n"
            "Run:\n"
            "pip install faster-whisper"
        ) from exc

    model_size = os.getenv(
        "WHISPER_MODEL_SIZE",
        "medium"
    ).strip()

    device = os.getenv(
        "WHISPER_DEVICE",
        "cpu"
    ).strip()

    compute_type = os.getenv(
        "WHISPER_COMPUTE_TYPE",
        "int8"
    ).strip()

    print(
        f"Loading Whisper model: {model_size}"
    )

    print(
        f"Device: {device} | Compute: {compute_type}"
    )

    try:

        _whisper_model = WhisperModel(
            model_size_or_path=model_size,
            device=device,
            compute_type=compute_type,
        )

    except Exception as exc:

        raise SpeechProcessingError(
            f"Could not load Whisper model '{model_size}'. "
            f"Device='{device}', "
            f"Compute='{compute_type}'."
        ) from exc

    return _whisper_model


# ============================================================================
# AUDIO VALIDATION
# ============================================================================

def _validate_audio(
    audio_path: PathLike
) -> Path:
    """Validate audio input."""

    path = Path(
        audio_path
    )

    if not path.exists():
        raise SpeechProcessingError(
            f"Audio file not found: {path}"
        )

    if not path.is_file():
        raise SpeechProcessingError(
            f"Audio path is not a file: {path}"
        )

    if path.stat().st_size == 0:
        raise SpeechProcessingError(
            f"Audio file is empty: {path}"
        )

    return path


# ============================================================================
# STT LANGUAGE
# ============================================================================

def _normalize_stt_language(
    language: str | None
) -> str | None:
    """Normalize STT language code."""

    if language is None:
        return None

    language = language.lower().strip()

    if language in {
        "",
        "auto",
        "detect"
    }:
        return None

    aliases = {
        "kannada": "kn",
        "kan": "kn",
        "kn-in": "kn",

        "hindi": "hi",
        "hin": "hi",
        "hi-in": "hi",

        "english": "en",
        "eng": "en",
        "en-in": "en",
    }

    language = aliases.get(
        language,
        language
    )

    if language not in {
        "kn",
        "hi",
        "en"
    }:
        raise SpeechProcessingError(
            f"Unsupported STT language: '{language}'. "
            "Use kn, hi, en or auto."
        )

    return language


# ============================================================================
# WHISPER PROMPTS
# ============================================================================

def _get_initial_prompt(
    language: str | None
) -> str | None:
    """
    Help Whisper stay in the requested language.
    """

    if language == "kn":

        return (
            "ಕನ್ನಡ ಭಾಷೆಯ ಧ್ವನಿಮುದ್ರಣ. "
            "ಕನ್ನಡ ಲಿಪಿಯಲ್ಲಿ ಮಾತ್ರ ಮಾತನಾಡಿದ ಪದಗಳನ್ನು "
            "ನಿಖರವಾಗಿ ಬರೆಯಿರಿ."
        )

    if language == "hi":

        return (
            "यह हिंदी भाषा का ऑडियो है। "
            "देवनागरी लिपि में बोले गए शब्दों को "
            "सटीक रूप से लिखें।"
        )

    if language == "en":

        return (
            "This is English speech. "
            "Transcribe the spoken words accurately in English."
        )

    return None


# ============================================================================
# REPETITION CLEANUP
# ============================================================================

def _remove_repeated_phrases(
    text: str
) -> str:
    """
    Remove obvious Whisper repetition.

    Example:
        "ನಮಸ್ಕಾರ ನಮಸ್ಕಾರ ನಮಸ್ಕಾರ ನಮಸ್ಕಾರ"

    becomes approximately:
        "ನಮಸ್ಕಾರ"

    This only removes obvious repeated blocks.
    """

    text = text.strip()

    if not text:
        return ""

    words = text.split()

    if len(words) < 8:
        return text

    # Remove repeated complete halves.
    for size in range(
        1,
        min(len(words) // 2, 20) + 1
    ):

        pattern = words[:size]

        repeated = True

        index = size

        count = 1

        while index + size <= len(words):

            if words[
                index:index + size
            ] != pattern:

                repeated = False
                break

            count += 1
            index += size

        if repeated and count >= 3:

            remainder = words[index:]

            return " ".join(
                pattern + remainder
            ).strip()

    return text


def _clean_transcript(
    text: str
) -> str:
    """Clean whitespace and obvious repetitions."""

    text = text.strip()

    if not text:
        return ""

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n+",
        " ",
        text
    )

    text = text.strip()

    text = _remove_repeated_phrases(
        text
    )

    return text


# ============================================================================
# SAVE TRANSCRIPT
# ============================================================================

def _get_transcript_path(
    audio_path: PathLike
) -> Path:
    """
    Save transcript beside audio.

    Example:
        test_kannada.ogg
        ->
        test_kannada.txt
    """

    audio = Path(
        audio_path
    )

    return audio.with_suffix(
        ".txt"
    )


def _save_transcript(
    text: str,
    audio_path: PathLike
) -> Path:
    """
    Save transcript as UTF-8.
    """

    transcript_path = _get_transcript_path(
        audio_path
    )

    try:

        transcript_path.write_text(
            text,
            encoding="utf-8"
        )

    except OSError as exc:

        raise SpeechProcessingError(
            f"Could not save transcript: "
            f"{transcript_path}"
        ) from exc

    return transcript_path


# ============================================================================
# SPEECH -> TEXT
# ============================================================================

def transcribe_audio(
    audio_path: PathLike,
    *,
    language: str | None = None,
    translate_to_english: bool = False,
    save_transcript: bool = True
) -> dict[str, Any]:
    """
    Convert speech to text.

    Args:
        audio_path:
            OGG / MP3 / WAV / M4A etc.

        language:
            kn = Kannada
            hi = Hindi
            en = English
            None/auto = automatic detection

        translate_to_english:
            False = preserve spoken language
            True = translate into English

        save_transcript:
            Save .txt beside the audio.

    Returns:
        {
            "text": "...",
            "language": "kn",
            "language_probability": 0.99,
            "transcript_path": "test_kannada.txt"
        }
    """

    path = _validate_audio(
        audio_path
    )

    selected_language = _normalize_stt_language(
        language
    )

    model = _get_whisper_model()

    task = (
        "translate"
        if translate_to_english
        else "transcribe"
    )

    prompt = _get_initial_prompt(
        selected_language
    )

    try:

        segments, info = model.transcribe(

            str(path),

            # Force language if supplied.
            language=selected_language,

            # Never translate unless explicitly requested.
            task=task,

            # More reliable decoding.
            beam_size=int(
                os.getenv(
                    "WHISPER_BEAM_SIZE",
                    "5"
                )
            ),

            best_of=int(
                os.getenv(
                    "WHISPER_BEST_OF",
                    "5"
                )
            ),

            temperature=0.0,

            # Remove silence.
            vad_filter=True,

            # Avoid previous segment causing repetition.
            condition_on_previous_text=False,

            # Reject obvious hallucinations.
            compression_ratio_threshold=2.4,

            log_prob_threshold=-1.0,

            no_speech_threshold=0.6,

            # Language-specific context.
            initial_prompt=prompt,
        )

        parts = []

        for segment in segments:

            segment_text = getattr(
                segment,
                "text",
                ""
            )

            segment_text = segment_text.strip()

            if segment_text:

                parts.append(
                    segment_text
                )

        transcript = " ".join(
            parts
        )

        transcript = _clean_transcript(
            transcript
        )

        detected_language = getattr(
            info,
            "language",
            None
        )

        language_probability = getattr(
            info,
            "language_probability",
            None
        )

        # ---> ADD THESE TWO LINES RIGHT HERE <---
        if detected_language not in {"kn", "hi", "en"}:
            detected_language = "hi" if detected_language == "ur" else "en"

        # Save the transcript in the same folder.
        transcript_path = None

        if save_transcript:

            transcript_path = _save_transcript(
                transcript,
                path
            )

        return {
            "text": transcript,
            "language": detected_language,
            "language_probability": language_probability,
            "transcript_path": (
                str(transcript_path)
                if transcript_path
                else None
            )
        }

    except Exception as exc:

        raise SpeechProcessingError(
            f"Speech-to-text failed for '{path}'. "
            f"Original error: {exc}"
        ) from exc


# ============================================================================
# SIMPLE SPEECH -> TEXT
# ============================================================================

def speech_to_text(
    audio_path: PathLike,
    *,
    language: str | None = None
) -> str:
    """
    Speech -> Text.

    Use explicit language whenever possible.

    Kannada:
        language="kn"

    Hindi:
        language="hi"

    English:
        language="en"
    """

    result = transcribe_audio(
        audio_path,
        language=language,
        translate_to_english=False,
        save_transcript=True
    )

    return result["text"]


# ============================================================================
# SPEECH -> ENGLISH
# ============================================================================

def speech_to_english(
    audio_path: PathLike
) -> str:
    """
    Translate speech into English text.
    """

    result = transcribe_audio(
        audio_path,
        language=None,
        translate_to_english=True,
        save_transcript=True
    )

    return result["text"]


# ============================================================================
# FIND FFMPEG
# ============================================================================

def _find_ffmpeg() -> str:
    """Find FFmpeg."""

    ffmpeg = shutil.which(
        "ffmpeg"
    )

    if ffmpeg:
        return ffmpeg

    configured = os.getenv(
        "FFMPEG_PATH"
    )

    if configured:

        path = Path(
            configured
        )

        if path.exists():
            return str(path)

    common_paths = [

        Path(
            r"C:\ffmpeg\bin\ffmpeg.exe"
        ),

        Path(
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
        ),

        Path(
            r"C:\ffmpeg\ffmpeg-9.0.2-essentials_build\bin\ffmpeg.exe"
        ),
    ]

    for path in common_paths:

        if path.exists():
            return str(path)

    raise SpeechProcessingError(
        "FFmpeg was not found.\n"
        "Set FFMPEG_PATH in .env or add FFmpeg to PATH."
    )


# ============================================================================
# OGG OUTPUT
# ============================================================================

def _prepare_ogg_output(
    output_path: PathLike
) -> Path:
    """Always use .ogg."""

    output = Path(
        output_path
    )

    if output.suffix.lower() != ".ogg":

        output = output.with_suffix(
            ".ogg"
        )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    return output


# ============================================================================
# MP3 -> OGG OPUS
# ============================================================================

def _convert_mp3_to_ogg(
    mp3_path: Path,
    ogg_path: Path
) -> None:
    """Convert MP3 to OGG/Opus."""

    ffmpeg = _find_ffmpeg()

    bitrate = os.getenv(
        "TTS_OGG_BITRATE",
        "32k"
    )

    command = [

        ffmpeg,

        "-y",

        "-i",
        str(mp3_path),

        "-vn",

        "-c:a",
        "libopus",

        "-b:a",
        bitrate,

        "-application",
        "voip",

        str(ogg_path),
    ]

    try:

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

    except OSError as exc:

        raise SpeechProcessingError(
            "Could not start FFmpeg."
        ) from exc

    if result.returncode != 0:

        raise SpeechProcessingError(
            "FFmpeg failed during OGG conversion.\n"
            f"{result.stderr}"
        )


# ============================================================================
# TTS LANGUAGE DETECTION
# ============================================================================

def _detect_tts_language(
    text: str
) -> str:
    """Detect language from Unicode script."""

    if not text.strip():

        raise SpeechProcessingError(
            "Cannot detect language from empty text."
        )

    # Kannada.
    if re.search(
        r"[\u0C80-\u0CFF]",
        text
    ):
        return "kn"

    # Hindi.
    if re.search(
        r"[\u0900-\u097F]",
        text
    ):
        return "hi"

    # Otherwise English.
    return "en"


def _normalize_tts_language(
    language: str | None,
    text: str
) -> str:

    if language is None:

        return _detect_tts_language(
            text
        )

    language = language.lower().strip()

    if language in {
        "auto",
        "detect"
    }:

        return _detect_tts_language(
            text
        )

    aliases = {
        "kannada": "kn",
        "kan": "kn",
        "kn-in": "kn",

        "hindi": "hi",
        "hin": "hi",
        "hi-in": "hi",

        "english": "en",
        "eng": "en",
        "en-in": "en",
    }

    language = aliases.get(
        language,
        language
    )

    if language not in {
        "kn",
        "hi",
        "en"
    }:

        raise SpeechProcessingError(
            f"Unsupported TTS language: '{language}'."
        )

    return language


# ============================================================================
# TTS VOICE
# ============================================================================

def _get_voice(
    language: str,
    voice: str | None = None
) -> str:

    if voice:
        return voice

    env_name = (
        f"TTS_VOICE_{language.upper()}"
    )

    configured_voice = os.getenv(
        env_name
    )

    if configured_voice:
        return configured_voice

    voice = DEFAULT_VOICES.get(
        language
    )

    if not voice:

        raise SpeechProcessingError(
            f"No TTS voice configured for '{language}'."
        )

    return voice


# ============================================================================
# TTS TEXT CLEANING
# ============================================================================

def _clean_tts_text(
    text: str
) -> str:

    if not isinstance(
        text,
        str
    ):

        raise SpeechProcessingError(
            "TTS text must be a string."
        )

    text = text.strip()

    if not text:

        raise SpeechProcessingError(
            "TTS text cannot be empty."
        )

    return re.sub(
        r"[ \t]+",
        " ",
        text
    )


# ============================================================================
# TEXT -> SPEECH
# ============================================================================

async def text_to_speech(
    text: str,
    output_path: PathLike,
    *,
    language: str = "auto",
    voice: str | None = None
) -> str:
    """
    Text -> OGG/Opus.

    Process:

        Text
          ↓
        Edge TTS
          ↓
        temporary MP3
          ↓
        FFmpeg
          ↓
        OGG/Opus
    """

    text = _clean_tts_text(
        text
    )

    selected_language = _normalize_tts_language(
        language,
        text
    )

    selected_voice = _get_voice(
        selected_language,
        voice
    )

    final_output = _prepare_ogg_output(
        output_path
    )

    temporary_directory = Path(
        tempfile.mkdtemp(
            prefix="mirai_tts_"
        )
    )

    temporary_mp3 = (
        temporary_directory
        / "speech.mp3"
    )

    try:

        # ------------------------------------------------------------
        # Edge TTS
        # ------------------------------------------------------------

        communicator = edge_tts.Communicate(
            text=text,
            voice=selected_voice
        )

        await communicator.save(
            str(temporary_mp3)
        )

        if not temporary_mp3.exists():

            raise SpeechProcessingError(
                "Edge TTS did not create the temporary MP3."
            )

        if temporary_mp3.stat().st_size == 0:

            raise SpeechProcessingError(
                "Edge TTS created an empty MP3."
            )

        # ------------------------------------------------------------
        # MP3 -> OGG/Opus
        # ------------------------------------------------------------

        _convert_mp3_to_ogg(
            temporary_mp3,
            final_output
        )

        if not final_output.exists():

            raise SpeechProcessingError(
                "OGG output file was not created."
            )

        if final_output.stat().st_size == 0:

            raise SpeechProcessingError(
                "OGG output file is empty."
            )

        return str(
            final_output
        )

    except SpeechProcessingError:

        raise

    except Exception as exc:

        raise SpeechProcessingError(
            f"Text-to-speech failed. "
            f"Language='{selected_language}', "
            f"Voice='{selected_voice}'. "
            f"Original error: {exc}"
        ) from exc

    finally:

        # Delete temporary MP3.
        try:

            if temporary_mp3.exists():
                temporary_mp3.unlink()

            temporary_directory.rmdir()

        except OSError:

            pass


# ============================================================================
# SYNCHRONOUS TTS
# ============================================================================

def text_to_speech_sync(
    text: str,
    output_path: PathLike,
    *,
    language: str = "auto",
    voice: str | None = None
) -> str:
    """Synchronous Text -> OGG/Opus."""

    try:

        return asyncio.run(
            text_to_speech(
                text,
                output_path,
                language=language,
                voice=voice
            )
        )

    except SpeechProcessingError:

        raise

    except RuntimeError as exc:

        raise SpeechProcessingError(
            "text_to_speech_sync() cannot run "
            "inside an active asyncio event loop."
        ) from exc


# ============================================================================
# KANNADA
# ============================================================================

async def kannada_to_speech(
    text: str,
    output_path: PathLike
) -> str:

    return await text_to_speech(
        text,
        output_path,
        language="kn"
    )


def kannada_to_speech_sync(
    text: str,
    output_path: PathLike
) -> str:

    return text_to_speech_sync(
        text,
        output_path,
        language="kn"
    )


# ============================================================================
# HINDI
# ============================================================================

async def hindi_to_speech(
    text: str,
    output_path: PathLike
) -> str:

    return await text_to_speech(
        text,
        output_path,
        language="hi"
    )


def hindi_to_speech_sync(
    text: str,
    output_path: PathLike
) -> str:

    return text_to_speech_sync(
        text,
        output_path,
        language="hi"
    )


# ============================================================================
# ENGLISH
# ============================================================================

async def english_to_speech(
    text: str,
    output_path: PathLike
) -> str:

    return await text_to_speech(
        text,
        output_path,
        language="en"
    )


def english_to_speech_sync(
    text: str,
    output_path: PathLike
) -> str:

    return text_to_speech_sync(
        text,
        output_path,
        language="en"
    )