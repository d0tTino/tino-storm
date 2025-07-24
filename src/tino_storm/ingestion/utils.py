import httpx
from io import BytesIO

try:  # optional dependencies for OCR
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None

try:
    import pytesseract
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None


def ocr_image(url: str) -> str:
    """Download an image from ``url`` and return extracted text using pytesseract."""
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        image = Image.open(BytesIO(resp.content))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception:
        return ""
