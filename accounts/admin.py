from django.contrib import admin
from .models import OTPRecord

@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display = ("email", "otp_code", "created_at", "is_used")
    list_filter = ("is_used", "created_at")
    search_fields = ("email", "otp_code")
    readonly_fields = ("created_at",)
