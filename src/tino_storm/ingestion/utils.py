import httpx
from io import BytesIO
from PIL import Image
import pytesseract


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
