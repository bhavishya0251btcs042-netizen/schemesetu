from django.conf import settings

def branding(request):
    return {
        "PRODUCT_NAME": settings.PRODUCT_NAME,
        "PRODUCT_TAGLINE": settings.PRODUCT_TAGLINE,
        "DAC_FOOTER": settings.DAC_FOOTER,
    }
