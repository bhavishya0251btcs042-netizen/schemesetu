from pathlib import Path
from django.conf import settings

_CSS_PATH = Path(__file__).resolve().parent / "static" / "css" / "style.css"
try:
    INLINE_CSS = _CSS_PATH.read_text(encoding="utf-8")
except Exception:
    INLINE_CSS = ""

def branding(request):
    return {
        "PRODUCT_NAME": getattr(settings, "PRODUCT_NAME", "SchemeSetu"),
        "PRODUCT_TAGLINE": getattr(settings, "PRODUCT_TAGLINE", "AI Citizen Services Navigator"),
        "DAC_FOOTER": getattr(settings, "DAC_FOOTER", "Powered by DAC"),
        "INLINE_CSS": INLINE_CSS,
    }
