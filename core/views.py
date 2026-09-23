from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .eligibility import match_all
from .explainer import explain
from .forms import (
    ApplicationForm,
    ProfileForm,
    AchievementForm,
    InstitutionAttendedForm,
)
from .models import (
    Application,
    Achievement,
    InstitutionAttended,
    Scheme,
    StudentSubscriber,
    NotificationLog,
    ACHIEVEMENT_LEVEL_CHOICES,
    INSTITUTION_TYPE_CHOICES,
)

PROFILE_KEY = "citizen_profile"


def _extract_repeatable_profile_data(post_data):
    """Extract dynamic achievement and institution attended lists from POST."""
    ach_titles = post_data.getlist("ach_title")
    ach_levels = post_data.getlist("ach_level")
    ach_years = post_data.getlist("ach_year")
    ach_descs = post_data.getlist("ach_desc")
    achievements = []
    for i in range(len(ach_titles)):
        title = ach_titles[i].strip()
        if title:
            achievements.append({
                "title": title,
                "level": ach_levels[i] if i < len(ach_levels) else "school",
                "year": ach_years[i].strip() if i < len(ach_years) else "",
                "description": ach_descs[i].strip() if i < len(ach_descs) else "",
            })

    inst_names = post_data.getlist("inst_name")
    inst_types = post_data.getlist("inst_type")
    inst_boards = post_data.getlist("inst_board")
    inst_cities = post_data.getlist("inst_city")
    inst_states = post_data.getlist("inst_state")
    inst_years = post_data.getlist("inst_years")
    institutions = []
    for i in range(len(inst_names)):
        name = inst_names[i].strip()
        if name:
            institutions.append({
                "name": name,
                "institution_type": inst_types[i] if i < len(inst_types) else "school",
                "board_affiliation": inst_boards[i].strip() if i < len(inst_boards) else "",
                "city": inst_cities[i].strip() if i < len(inst_cities) else "",
                "state": inst_states[i].strip() if i < len(inst_states) else "",
                "years_attended": inst_years[i].strip() if i < len(inst_years) else "",
            })

    return achievements, institutions


def home(request):
    try:
        scheme_count = Scheme.objects.count()
        restricted_count = Scheme.objects.filter(restrict_to_listed_institutions=True).count()
    except Exception:
        # DB not yet available (e.g. first Vercel deploy before migrate runs)
        scheme_count = 0
        restricted_count = 0
    return render(
        request,
        "home.html",
        {
            "scheme_count": scheme_count,
            "restricted_count": restricted_count,
        },
    )


@login_required
def check(request):
    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            profile_data = form.as_profile()
            achievements, institutions = _extract_repeatable_profile_data(request.POST)
            profile_data["achievements"] = achievements
            profile_data["institutions_attended"] = institutions
            request.session[PROFILE_KEY] = profile_data

            email = (profile_data.get("email") or "").strip().lower()
            if email and profile_data.get("subscribe_alerts"):
                StudentSubscriber.objects.update_or_create(
                    email=email,
                    defaults={
                        "name": profile_data.get("name", "Student"),
                        "phone": profile_data.get("phone", ""),
                        "age": profile_data.get("age", 18),
                        "gender": profile_data.get("gender", "any"),
                        "category": profile_data.get("category", "general"),
                        "annual_income": profile_data.get("annual_income", 0),
                        "state": profile_data.get("state", ""),
                        "education_level": profile_data.get("education_level", "undergraduate"),
                        "current_institution": profile_data.get("current_institution", ""),
                        "is_student": profile_data.get("is_student", True),
                        "is_active": True,
                    },
                )
            return redirect("core:results")
    else:
        profile_data = request.session.get(PROFILE_KEY, {})
        initial = {k: v for k, v in profile_data.items() if k not in ("achievements", "institutions_attended")}
        form = ProfileForm(initial=initial if initial else None)

    saved_profile = request.session.get(PROFILE_KEY, {})
    return render(
        request,
        "profile_form.html",
        {
            "form": form,
            "achievements": saved_profile.get("achievements", []),
            "institutions": saved_profile.get("institutions_attended", []),
            "achievement_levels": ACHIEVEMENT_LEVEL_CHOICES,
            "institution_types": INSTITUTION_TYPE_CHOICES,
        },
    )


def results(request):
    profile = request.session.get(PROFILE_KEY)
    if not profile:
        messages.info(request, "Please fill your profile details first.")
        return redirect("core:check")

    schemes_qs = Scheme.objects.prefetch_related("approved_institutions").all()
    eligible, others = match_all(schemes_qs, profile)
    return render(
        request,
        "results.html",
        {
            "profile": profile,
            "eligible": eligible,
            "others": others,
        },
    )


def scheme_detail(request, pk):
    scheme = get_object_or_404(
        Scheme.objects.prefetch_related("approved_institutions"), pk=pk
    )
    return render(
        request,
        "scheme_detail.html",
        {
            "scheme": scheme,
            "explanation": explain(scheme),
            "approved_institutions": scheme.approved_institutions.all(),
        },
    )


@login_required
def apply(request, pk):
    scheme = get_object_or_404(
        Scheme.objects.prefetch_related("approved_institutions"), pk=pk
    )
    profile = request.session.get(PROFILE_KEY, {})
    ach_initial = profile.get("achievements", [])
    inst_initial = profile.get("institutions_attended", [])

    extra_ach = max(1, len(ach_initial))
    extra_inst = max(1, len(inst_initial))

    AchFormSetCls = inlineformset_factory(
        Application,
        Achievement,
        form=AchievementForm,
        extra=extra_ach,
        can_delete=True,
    )
    InstFormSetCls = inlineformset_factory(
        Application,
        InstitutionAttended,
        form=InstitutionAttendedForm,
        extra=extra_inst,
        can_delete=True,
    )

    if request.method == "POST":
        form = ApplicationForm(request.POST)
        achievement_formset = AchFormSetCls(request.POST, prefix="achievements")
        institution_formset = InstFormSetCls(request.POST, prefix="institutions")

        if form.is_valid() and achievement_formset.is_valid() and institution_formset.is_valid():
            application = form.save(commit=False)
            application.scheme = scheme
            application.save()

            # Save achievements
            for ach_form in achievement_formset.forms:
                if ach_form.cleaned_data and not ach_form.cleaned_data.get("DELETE", False):
                    title = ach_form.cleaned_data.get("title")
                    if title:
                        ach = ach_form.save(commit=False)
                        ach.application = application
                        ach.save()

            # Save institutions attended
            for inst_form in institution_formset.forms:
                if inst_form.cleaned_data and not inst_form.cleaned_data.get("DELETE", False):
                    name = inst_form.cleaned_data.get("name")
                    if name:
                        inst = inst_form.save(commit=False)
                        inst.application = application
                        inst.save()

            # Auto-subscribe student to scholarship alerts if opted-in
            sub_email = (form.cleaned_data.get("email") or "").strip().lower()
            if sub_email and form.cleaned_data.get("subscribe_alerts"):
                StudentSubscriber.objects.update_or_create(
                    email=sub_email,
                    defaults={
                        "name": application.applicant_name,
                        "phone": application.phone or "",
                        "age": application.age or 18,
                        "gender": application.gender or "any",
                        "category": application.category or "general",
                        "annual_income": application.annual_income or 0,
                        "state": application.state or "",
                        "education_level": application.education_level or "undergraduate",
                        "current_institution": application.current_institution or "",
                        "is_student": True,
                        "is_active": True,
                    },
                )

            messages.success(
                request,
                f"Application submitted successfully for {scheme.name}. Your tracking ID is {application.tracking_id}.",
            )
            return redirect("core:application_detail", tracking_id=application.tracking_id)
        else:
            messages.error(request, "Please correct the errors in the form before submitting.")
    else:
        # Pre-fill from session profile
        initial = {
            "applicant_name": profile.get("name", ""),
            "date_of_birth": profile.get("date_of_birth", ""),
            "age": profile.get("age"),
            "gender": profile.get("gender"),
            "category": profile.get("category"),
            "state": profile.get("state", ""),
            "district": profile.get("district", ""),
            "address": profile.get("address", ""),
            "phone": profile.get("phone", ""),
            "email": profile.get("email", ""),
            "aadhaar_linked": profile.get("aadhaar_linked", False),
            "annual_income": profile.get("annual_income"),
            "disability_status": profile.get("disability_status", "no"),
            "education_level": profile.get("education_level"),
            "current_course": profile.get("current_course", ""),
            "current_institution": profile.get("current_institution", ""),
            "current_year": profile.get("current_year", ""),
            "latest_percentage": profile.get("latest_percentage", ""),
            "board_10th": profile.get("board_10th", ""),
            "percentage_10th": profile.get("percentage_10th", ""),
            "board_12th": profile.get("board_12th", ""),
            "percentage_12th": profile.get("percentage_12th", ""),
            "employment_status": profile.get("employment_status", "student"),
            "achievements_notes": profile.get("achievements_notes", ""),
            "scholarships_availed": profile.get("scholarships_availed", ""),
        }
        form = ApplicationForm(initial={k: v for k, v in initial.items() if v is not None})
        achievement_formset = AchFormSetCls(
            queryset=Achievement.objects.none(),
            initial=ach_initial if ach_initial else None,
            prefix="achievements",
        )
        institution_formset = InstFormSetCls(
            queryset=InstitutionAttended.objects.none(),
            initial=inst_initial if inst_initial else None,
            prefix="institutions",
        )

    return render(
        request,
        "apply.html",
        {
            "scheme": scheme,
            "form": form,
            "achievement_formset": achievement_formset,
            "institution_formset": institution_formset,
        },
    )


def application_detail(request, tracking_id):
    application = get_object_or_404(
        Application.objects.select_related("scheme").prefetch_related(
            "achievements", "institutions_attended"
        ),
        tracking_id=tracking_id,
    )
    return render(request, "application_detail.html", {"application": application})


def track(request):
    application = None
    tracking_id = request.GET.get("tracking_id", "").strip()
    if tracking_id:
        application = (
            Application.objects.filter(tracking_id__iexact=tracking_id)
            .select_related("scheme")
            .prefetch_related("achievements", "institutions_attended")
            .first()
        )
        if not application:
            messages.error(request, f"No application found with tracking ID '{tracking_id}'.")

    recent = Application.objects.select_related("scheme").all()[:10]
    return render(
        request,
        "track.html",
        {
            "application": application,
            "recent": recent,
            "tracking_id": tracking_id,
        },
    )


@login_required
def notifications_inbox(request):
    """Notification Centre: look up personalised scholarship alerts by email."""
    email = request.GET.get("email", "").strip().lower()
    subscriber = None
    notifications = []
    if email:
        subscriber = StudentSubscriber.objects.filter(email__iexact=email, is_active=True).first()
        if subscriber:
            notifications = subscriber.notifications.select_related("scheme").order_by("-created_at")
        else:
            messages.error(request, f"No active subscriber found for email: {email}")
    return render(
        request,
        "notifications.html",
        {
            "subscriber": subscriber,
            "notifications": notifications,
            "email_query": email,
        },
    )

