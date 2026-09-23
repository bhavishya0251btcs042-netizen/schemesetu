from django.contrib import admin
from .models import (
    Application,
    ApprovedInstitution,
    Achievement,
    InstitutionAttended,
    Scheme,
    StudentSubscriber,
    NotificationLog,
)


class ApprovedInstitutionInline(admin.TabularInline):
    model = ApprovedInstitution
    extra = 1
    fields = ("name", "city", "state")


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "department",
        "max_income",
        "education_level",
        "state",
        "students_only",
        "restrict_to_listed_institutions",
    )
    search_fields = ("name", "department")
    list_filter = (
        "education_level",
        "gender",
        "students_only",
        "restrict_to_listed_institutions",
    )
    inlines = [ApprovedInstitutionInline]


@admin.register(ApprovedInstitution)
class ApprovedInstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "scheme", "city", "state")
    search_fields = ("name", "city", "state", "scheme__name")
    list_filter = ("scheme", "state")


class AchievementInline(admin.TabularInline):
    model = Achievement
    extra = 0


class InstitutionAttendedInline(admin.TabularInline):
    model = InstitutionAttended
    extra = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "tracking_id",
        "applicant_name",
        "scheme",
        "current_institution",
        "education_level",
        "category",
        "status",
        "created_at",
    )
    list_filter = ("status", "scheme", "category", "education_level")
    search_fields = ("tracking_id", "applicant_name", "current_institution", "phone", "email")
    list_editable = ("status",)
    readonly_fields = ("tracking_id", "created_at")
    inlines = [AchievementInline, InstitutionAttendedInline]


@admin.register(StudentSubscriber)
class StudentSubscriberAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "current_institution",
        "education_level",
        "category",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "email", "phone", "current_institution")
    list_filter = ("education_level", "category", "is_active", "state")
    list_editable = ("is_active",)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        "subscriber",
        "scheme",
        "channel",
        "status",
        "created_at",
    )
    search_fields = ("subscriber__name", "subscriber__email", "scheme__name", "subject")
    list_filter = ("channel", "status", "scheme")
    readonly_fields = ("subscriber", "scheme", "channel", "status", "subject", "message", "matched_reasons", "created_at")

