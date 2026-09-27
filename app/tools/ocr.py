"""
OCR utilities for Mirai Gijutsu.

Purpose:
    Image/document -> extracted text

Designed for:
    - Aadhaar card photographs
    - Land records
    - Government documents
    - English + Kannada documents

Does NOT:
    - Send WhatsApp messages
    - Run FastAPI
    - Manage LangGraph
    - Decide PM-KISAN eligibility
    - Store user data

Main integration functions:
    extract_text(image_path) -> str
    extract_aadhaar_text(image_path) -> str
    extract_document_text(image_path) -> str
"""

# External Libraries
import os
import re
import shutil
from pathlib import Path
from typing import Union

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageOps


PathLike = Union[str, os.PathLike]


# ============================================================================
# CUSTOM ERROR
# ============================================================================

class OCRProcessingError(RuntimeError):
    """Raised when OCR processing fails."""


# ============================================================================
# TESSERACT CONFIGURATION
# ============================================================================

def _configure_tesseract() -> None:
    """
    Find the Tesseract executable.

    Priority:
        1. TESSERACT_CMD environment variable
        2. Tesseract in PATH
        3. Default Windows installation path
    """

    configured_path = os.getenv("TESSERACT_CMD")

    if configured_path:
        pytesseract.pytesseract.tesseract_cmd = configured_path
        return

    if shutil.which("tesseract"):
        return

    windows_path = Path(
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    if windows_path.exists():
        pytesseract.pytesseract.tesseract_cmd = str(
            windows_path
        )


def _check_tesseract() -> None:
    """Check whether Tesseract is available."""

    _configure_tesseract()

    try:
        pytesseract.get_tesseract_version()

    except Exception as exc:
        raise OCRProcessingError(
            "Tesseract OCR was not found. "
            "Install Tesseract or set TESSERACT_CMD."
        ) from exc


# ============================================================================
# FILE VALIDATION
# ============================================================================

def _validate_image(
    image_path: PathLike
) -> Path:
    """Validate the supplied image."""

    path = Path(image_path)

    if not path.exists():
        raise OCRProcessingError(
            f"Image file not found: {path}"
        )

    if not path.is_file():
        raise OCRProcessingError(
            f"Path is not a file: {path}"
        )

    if path.stat().st_size == 0:
        raise OCRProcessingError(
            f"Image file is empty: {path}"
        )

    return path


# ============================================================================
# IMAGE LOADING
# ============================================================================

def _load_image(
    image_path: Path
) -> np.ndarray:
    """
    Load image safely.

    EXIF orientation is applied so phone photographs
    are not incorrectly rotated due to camera metadata.
    """

    try:

        with Image.open(image_path) as image:

            image = ImageOps.exif_transpose(
                image
            )

            image = image.convert(
                "RGB"
            )

            rgb = np.array(
                image
            )

        return cv2.cvtColor(
            rgb,
            cv2.COLOR_RGB2BGR
        )

    except Exception as exc:

        raise OCRProcessingError(
            f"Unable to read image: {image_path}"
        ) from exc


# ============================================================================
# ROTATION
# ============================================================================

def _rotate(
    image: np.ndarray,
    angle: int
) -> np.ndarray:
    """Rotate an image by 0, 90, 180 or 270 degrees."""

    if angle == 0:
        return image

    if angle == 90:
        return cv2.rotate(
            image,
            cv2.ROTATE_90_CLOCKWISE
        )

    if angle == 180:
        return cv2.rotate(
            image,
            cv2.ROTATE_180
        )

    if angle == 270:
        return cv2.rotate(
            image,
            cv2.ROTATE_90_COUNTERCLOCKWISE
        )

    raise ValueError(
        "Angle must be 0, 90, 180 or 270."
    )


# ============================================================================
# RESIZE
# ============================================================================

def _resize_for_ocr(
    image: np.ndarray
) -> np.ndarray:
    """
    Upscale smaller images.

    This helps when the farmer sends a relatively
    small phone photograph.
    """

    height, width = image.shape[:2]

    largest_dimension = max(
        height,
        width
    )

    if largest_dimension >= 2000:
        return image

    return cv2.resize(
        image,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_CUBIC
    )


# ============================================================================
# QR CODE MASKING
# ============================================================================

def _mask_qr(
    image: np.ndarray
) -> np.ndarray:
    """
    Try to hide a QR code before OCR.

    The QR code is not needed for visible-text OCR.
    """

    result = image.copy()

    try:

        detector = cv2.QRCodeDetector()

        _, points, _ = detector.detectAndDecode(
            image
        )

        if points is not None:

            points = points.astype(
                np.int32
            )

            cv2.fillConvexPoly(
                result,
                points.reshape(
                    -1,
                    2
                ),
                (255, 255, 255)
            )

    except Exception:
        # Failure to detect a QR code is harmless.
        pass

    return result


# ============================================================================
# PREPROCESSING
# ============================================================================

def _preprocess(
    image: np.ndarray
) -> np.ndarray:
    """
    Prepare a camera photograph for OCR.

    Used as a second OCR candidate. The original
    image is also tested because aggressive processing
    can sometimes make a clean document worse.
    """

    image = _resize_for_ocr(
        image
    )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # Improve local contrast.
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    gray = clahe.apply(
        gray
    )

    # Reduce small camera noise.
    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    # Adaptive threshold.
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    return binary


# ============================================================================
# CHARACTER VALIDATION
# ============================================================================

def _allowed_character(
    char: str
) -> bool:
    """
    Return True when a character is reasonable OCR output.

    Supports:
        English
        Kannada
        Hindi
        digits
        common punctuation
    """

    return (
        char.isalnum()
        or "\u0C80" <= char <= "\u0CFF"   # Kannada
        or "\u0900" <= char <= "\u097F"   # Hindi
        or char in ".:/-"
    )


def _is_reasonable_word(
    text: str,
    confidence: float,
    minimum_confidence: float
) -> bool:
    """
    Reject obvious OCR garbage.

    This is deliberately conservative for QR/background noise.
    """

    if not text:
        return False

    if confidence < minimum_confidence:
        return False

    allowed = 0
    rejected = 0

    for char in text:

        if _allowed_character(char):
            allowed += 1
        else:
            rejected += 1

    total = allowed + rejected

    if total == 0:
        return False

    # Reject symbol-heavy garbage.
    if rejected / total > 0.25:
        return False

    # Ignore isolated random characters.
    if len(text) == 1 and not text.isdigit():
        return False

    return True


# ============================================================================
# GENERAL TEXT CLEANING
# ============================================================================

def _clean_text(
    text: str
) -> str:
    """Normalize whitespace while preserving lines."""

    output = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        line = re.sub(
            r"\s+",
            " ",
            line
        )

        output.append(
            line
        )

    return "\n".join(
        output
    ).strip()


# ============================================================================
# OCR ENGINE
# ============================================================================

def _run_ocr(
    image: np.ndarray,
    *,
    language: str,
    psm: int,
    minimum_confidence: float
) -> tuple[str, float, int]:
    """
    Run Tesseract and return only filtered words.

    Returns:
        (
            cleaned_text,
            average_confidence,
            word_count
        )
    """

    config = (
        f"--oem 3 --psm {psm}"
    )

    try:

        data = pytesseract.image_to_data(
            image,
            lang=language,
            config=config,
            output_type=pytesseract.Output.DICT
        )

    except Exception as exc:

        raise OCRProcessingError(
            "Tesseract OCR failed."
        ) from exc

    accepted_words = []

    for index, raw_text in enumerate(
        data["text"]
    ):

        text = raw_text.strip()

        try:
            confidence = float(
                data["conf"][index]
            )

        except (
            TypeError,
            ValueError
        ):
            continue

        if not _is_reasonable_word(
            text,
            confidence,
            minimum_confidence
        ):
            continue

        accepted_words.append(
            {
                "text": text,
                "confidence": confidence,
                "left": data["left"][index],
                "block": data["block_num"][index],
                "paragraph": data["par_num"][index],
                "line": data["line_num"][index],
            }
        )

    if not accepted_words:
        return "", 0.0, 0

    # Group using block + paragraph + line.
    grouped_lines = {}

    for item in accepted_words:

        key = (
            item["block"],
            item["paragraph"],
            item["line"]
        )

        grouped_lines.setdefault(
            key,
            []
        ).append(
            item
        )

    lines = []

    for key in sorted(
        grouped_lines
    ):

        words = grouped_lines[key]

        words.sort(
            key=lambda item: item["left"]
        )

        line = " ".join(
            item["text"]
            for item in words
        )

        if line:
            lines.append(
                line
            )

    text = _clean_text(
        "\n".join(lines)
    )

    if not text:
        return "", 0.0, 0

    average_confidence = sum(
        item["confidence"]
        for item in accepted_words
    ) / len(accepted_words)

    return (
        text,
        average_confidence,
        len(accepted_words)
    )


# ============================================================================
# GENERIC OCR
# ============================================================================

def extract_text(
    image_path: PathLike,
    *,
    language: str | None = None,
    psm: int | None = None,
    preprocess: bool | None = None
) -> str:
    """
    Generic OCR function.

    Example:

        extract_text(
            "document.jpg",
            language="eng+kan"
        )
    """

    path = _validate_image(
        image_path
    )

    _check_tesseract()

    language = (
        language
        or os.getenv(
            "OCR_LANG",
            "eng"
        )
    )

    try:

        psm_value = int(
            psm
            if psm is not None
            else os.getenv(
                "OCR_PSM",
                "3"
            )
        )

    except ValueError as exc:

        raise OCRProcessingError(
            "OCR_PSM must be an integer."
        ) from exc

    if preprocess is None:

        preprocess_value = (
            os.getenv(
                "OCR_PREPROCESS",
                "false"
            ).lower()
            in {
                "1",
                "true",
                "yes",
                "on"
            }
        )

    else:

        preprocess_value = preprocess

    image = _load_image(
        path
    )

    if preprocess_value:

        image = _preprocess(
            image
        )

    text, _, _ = _run_ocr(
        image,
        language=language,
        psm=psm_value,
        minimum_confidence=50.0
    )

    return text


# ============================================================================
# AADHAAR-SPECIFIC CLEANING
# ============================================================================

def _clean_aadhaar_text(
    text: str
) -> str:
    """
    Remove common Aadhaar OCR artifacts.

    Important:
        We do NOT delete all numbers.

    Kept:
        - 4-digit years
        - Aadhaar number groups
        - meaningful numeric fields

    Removed:
        - isolated 1-2 digit OCR noise
        - symbols
        - numbers incorrectly attached to Male/Female
    """

    output_lines = []

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # Normalize whitespace.
        line = re.sub(
            r"\s+",
            " ",
            line
        )

        # Remove leading/trailing OCR punctuation.
        line = re.sub(
            r"^[|~`_=+*#@<>]+",
            "",
            line
        )

        line = re.sub(
            r"[|~`_=+*#@<>]+$",
            "",
            line
        )

        line = line.strip()

        if not line:
            continue

        # ------------------------------------------------------------
        # Fix "Male 13", "Female 12", etc.
        #
        # Only applied to gender lines so legitimate numbers
        # elsewhere are not destroyed.
        # ------------------------------------------------------------

        if re.search(
            r"(?i)\b(male|female)\b",
            line
        ):

            line = re.sub(
                r"(?i)\b(male|female)\b"
                r"[\s|:;,\-]*\d{1,2}\b",
                r"\1",
                line
            )

        # ------------------------------------------------------------
        # Remove random punctuation tokens.
        # ------------------------------------------------------------

        tokens = line.split()

        cleaned_tokens = []

        for token in tokens:

            token = token.strip(
                "|~`_=+*#@<>[]{}()"
            )

            if not token:
                continue

            # --------------------------------------------------------
            # Keep 4-digit years.
            # --------------------------------------------------------

            if re.fullmatch(
                r"(19|20)\d{2}",
                token
            ):
                cleaned_tokens.append(
                    token
                )
                continue

            # --------------------------------------------------------
            # Keep 4-digit numeric groups.
            #
            # Important for Aadhaar numbers.
            # --------------------------------------------------------

            if re.fullmatch(
                r"\d{4}",
                token
            ):
                cleaned_tokens.append(
                    token
                )
                continue

            # --------------------------------------------------------
            # Remove isolated 1-2 digit OCR garbage.
            #
            # Example:
            #     Male 13
            #
            # The gender-specific regex above usually catches this,
            # but this provides another cleanup layer.
            # --------------------------------------------------------

            if re.fullmatch(
                r"\d{1,2}",
                token
            ):

                # Don't remove a number from a gender line
                # only if it somehow belongs to a legitimate
                # date-like field.
                if not re.search(
                    r"(?i)\b(dob|date|birth)\b",
                    line
                ):
                    continue

            cleaned_tokens.append(
                token
            )

        line = " ".join(
            cleaned_tokens
        ).strip()

        if not line:
            continue

        # ------------------------------------------------------------
        # Remove lines containing only punctuation.
        # ------------------------------------------------------------

        meaningful = re.sub(
            r"[^A-Za-z0-9\u0C80-\u0CFF\u0900-\u097F]",
            "",
            line
        )

        if not meaningful:
            continue

        # Ignore one-character garbage lines.
        if len(meaningful) == 1:
            continue

        output_lines.append(
            line
        )

    return "\n".join(
        output_lines
    ).strip()


# ============================================================================
# AADHAAR RESULT SCORING
# ============================================================================

AADHAAR_KEYWORDS = (
    "government",
    "india",
    "year",
    "birth",
    "male",
    "female",
    "address",
    "bhuvan",
    "bhavan",
    "ಭಾರತ",
    "ಸರ್ಕಾರ",
    "ಹುಟ್ಟಿದ",
    "ಜನ್ಮ",
)


def _score_aadhaar_result(
    text: str,
    confidence: float,
    word_count: int
) -> float:
    """
    Score an OCR candidate.

    OCR confidence is the primary factor.
    Aadhaar-related terms provide additional evidence.
    """

    score = confidence * 1.5

    lower_text = text.lower()

    for keyword in AADHAAR_KEYWORDS:

        if keyword.lower() in lower_text:
            score += 15.0

    # Reward useful text length.
    score += min(
        len(text) / 15.0,
        35.0
    )

    # Reward multiple recognized words.
    score += min(
        word_count,
        30
    )

    # Reward a possible Aadhaar-number grouping.
    if re.search(
        r"\b\d{4}\s+\d{4}\s+\d{4}\b",
        text
    ):
        score += 30.0

    # Reward a year.
    if re.search(
        r"\b(19|20)\d{2}\b",
        text
    ):
        score += 10.0

    return score


# ============================================================================
# AADHAAR OCR
# ============================================================================

def extract_aadhaar_text(
    image_path: PathLike
) -> str:
    """
    Extract text from an English + Kannada Aadhaar photograph.

    Handles:
        - 0/90/180/270 degree rotation
        - phone photographs
        - moderate blur
        - uneven lighting
        - QR code interference
        - English + Kannada

    Returns:
        Cleaned OCR text.
    """

    path = _validate_image(
        image_path
    )

    _check_tesseract()

    language = os.getenv(
        "AADHAAR_OCR_LANG",
        "eng+kan"
    )

    try:

        minimum_confidence = float(
            os.getenv(
                "AADHAAR_OCR_MIN_CONFIDENCE",
                "50"
            )
        )

    except ValueError as exc:

        raise OCRProcessingError(
            "AADHAAR_OCR_MIN_CONFIDENCE "
            "must be numeric."
        ) from exc

    image = _load_image(
        path
    )

    best_text = ""
    best_score = -1.0

    # Try all common phone-camera orientations.
    for angle in (
        0,
        90,
        180,
        270
    ):

        rotated = _rotate(
            image,
            angle
        )

        # Remove QR code where possible.
        clean = _mask_qr(
            rotated
        )

        # Upscale.
        clean = _resize_for_ocr(
            clean
        )

        # ============================================================
        # CANDIDATE 1: ORIGINAL IMAGE
        # ============================================================

        text, confidence, word_count = _run_ocr(
            clean,
            language=language,
            psm=6,
            minimum_confidence=minimum_confidence
        )

        if text:

            score = _score_aadhaar_result(
                text,
                confidence,
                word_count
            )

            if score > best_score:

                best_score = score
                best_text = text

        # ============================================================
        # CANDIDATE 2: PREPROCESSED IMAGE
        # ============================================================

        processed = _preprocess(
            clean
        )

        text, confidence, word_count = _run_ocr(
            processed,
            language=language,
            psm=6,
            minimum_confidence=minimum_confidence
        )

        if text:

            score = _score_aadhaar_result(
                text,
                confidence,
                word_count
            )

            if score > best_score:

                best_score = score
                best_text = text

    if not best_text:

        raise OCRProcessingError(
            "No readable text was detected "
            "in the Aadhaar image."
        )

    # Final Aadhaar-specific cleanup.
    # Final Aadhaar-specific cleanup.
    final_text = _clean_aadhaar_text(
        best_text
    )

    if not final_text:
        raise OCRProcessingError(
            "OCR detected text, but no usable "
            "Aadhaar text remained after filtering."
        )

    # ---> TOKEN BLOAT FIX <---
    # Search for the 12-digit pattern (e.g., 1234 5678 9012)
    id_match = re.search(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", final_text)
    
    if id_match:
        # Return exactly 12 digits. Reduces LLM payload from ~2000 tokens to 4 tokens.
        return f"{id_match.group(1)}{id_match.group(2)}{id_match.group(3)}"

    # Fallback: Truncate aggressively to prevent Groq API crashes if the regex misses
    return final_text[:300]
    return final_text


# ============================================================================
# LAND RECORD / GOVERNMENT DOCUMENT OCR
# ============================================================================

def extract_document_text(
    image_path: PathLike
) -> str:
    """
    Extract text from land records and
    other government documents.

    Unlike Aadhaar OCR, this function does NOT
    aggressively remove small numbers because
    land records may legitimately contain:
        - survey numbers
        - plot numbers
        - acre values
        - document numbers
    """

    language = os.getenv(
        "DOCUMENT_OCR_LANG",
        "eng+kan"
    )

    try:

        psm = int(
            os.getenv(
                "DOCUMENT_OCR_PSM",
                "3"
            )
        )

    except ValueError as exc:

        raise OCRProcessingError(
            "DOCUMENT_OCR_PSM must be an integer."
        ) from exc

    preprocess = (
        os.getenv(
            "DOCUMENT_OCR_PREPROCESS",
            "false"
        ).lower()
        in {
            "1",
            "true",
            "yes",
            "on"
        }
    )

    raw_text = extract_text(
        image_path,
        language=language,
        psm=psm,
        preprocess=preprocess
    )
    
    # Land records are massive. Strip excess whitespace and hard-cap at 600 characters 
    # to protect the LangGraph memory state from rate-limit crashes.
    cleaned_doc = re.sub(r"\s+", " ", raw_text).strip()
    return cleaned_doc[:600]