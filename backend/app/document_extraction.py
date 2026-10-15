"""Local-only document extraction with explicit uncertainty and provenance.

PDF text-layer extraction is not OCR. Image OCR requires the optional
Tesseract executable and language packs; it never auto-verifies credit evidence.
"""
import re
from pathlib import Path
from typing import Any

SOURCES = {
    "turnover": [
        r"(?:annual\s+turnover|gross\s+sales|turnover|annual\s+sales|வருவாய்|வருமானம்)"
        r"\s*[:=\-]?\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)"
    ],
}

def heuristic_candidates(text: str) -> dict[str, list[int | float]]:
    """Unverified local text suggestions, never authoritative credit data."""
    result: dict[str, list[int | float]] = {}
    for key, patterns in SOURCES.items():
        seen = set()
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                raw = match.group(1).replace(",", "")
                try:
                    amount = float(raw)
                except ValueError:
                    continue
                if not 0 <= amount <= 1_000_000_000_000:
                    continue
                parsed: int | float = int(amount) if amount.is_integer() else amount
                seen.add(parsed)
        if seen:
            result[key] = sorted(seen)[:15]
    return result

def extract_text(path: Path, mime: str, language: str = "eng") -> dict[str, Any]:
    """Use PDF text layer or optional local Tesseract; no cloud processing."""
    if not re.fullmatch(r"[a-z]{3}(\+[a-z]{3}){0,3}", language):
        raise ValueError("Use installed Tesseract ISO-639-3 language packs e.g. eng+tam")
    if mime == "application/pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("Install backend OCR extras: pip install -e '.[ocr]'")
        try:
            with path.open("rb") as fp:
                reader = PdfReader(fp, strict=False)
                if len(reader.pages) > 15:
                    raise ValueError("15-page text PDF extraction limit")
                text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError("PDF text extraction failed") from exc
        engine = "pypdf_text_layer_NOT_OCR"
    elif mime in ("image/png", "image/jpeg"):
        try:
            from PIL import Image
            import pytesseract
        except ImportError:
            raise RuntimeError("Image OCR requires pip install -e '.[ocr]' and system Tesseract")
        try:
            with Image.open(path) as image:
                image.load()
                if image.width * image.height > 15_000_000:
                    raise ValueError("Image exceeds 15 megapixel OCR limit")
                text = pytesseract.image_to_string(image, lang=language, timeout=20)
        except ValueError:
            raise
        except Exception as exc:
            raise RuntimeError("Tesseract unavailable, language pack missing or OCR timed out") from exc
        engine = "local_tesseract_ocr"
    else:
        raise ValueError("Unsupported media type")
    limited_text = text[:20000]
    return {
        "engine": engine,
        "language": language,
        "text": limited_text,
        "truncated": len(text) > len(limited_text),
        "status": "text_extracted" if limited_text.strip() else "no_text",
        "candidates": heuristic_candidates(limited_text),
        "verified": False,
        "notice": "Heuristic extractions may be wrong. A human must inspect the document and verify any evidence used for loan decisions.",
    }
