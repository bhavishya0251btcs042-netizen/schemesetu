from datetime import date
from django import forms
from django.forms import inlineformset_factory

from .models import (
    Application,
    Achievement,
    InstitutionAttended,
    CATEGORY_CHOICES,
    GENDER_CHOICES,
    EDU_CHOICES,
    EMPLOYMENT_CHOICES,
    DISABILITY_CHOICES,
    ACHIEVEMENT_LEVEL_CHOICES,
    INSTITUTION_TYPE_CHOICES,
)


class ProfileForm(forms.Form):
    # Personal details
    name = forms.CharField(
        max_length=200,
        required=True,
        label="Full name",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Ananya Sharma"}),
    )
    date_of_birth = forms.DateField(
        required=False,
        label="Date of birth",
        widget=forms.DateInput(attrs={"type": "date", "id": "id_dob"}),
    )
    age = forms.IntegerField(
        min_value=1,
        max_value=120,
        label="Age (years)",
        widget=forms.NumberInput(attrs={"id": "id_age", "placeholder": "e.g. 20"}),
    )
    gender = forms.ChoiceField(
        choices=[g for g in GENDER_CHOICES if g[0] != "any"],
        label="Gender",
    )
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        label="Social category",
    )
    state = forms.CharField(
        max_length=100,
        required=False,
        label="State of residence",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Uttar Pradesh, Delhi, Maharashtra"}),
    )
    district = forms.CharField(
        max_length=100,
        required=False,
        label="District",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Dehradun, Lucknow, Central Delhi"}),
    )
    address = forms.CharField(
        required=False,
        label="Residential address",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "House/Flat no., Street, Locality"}),
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        label="Phone number",
        widget=forms.TextInput(attrs={"placeholder": "e.g. 9876543210"}),
    )
    email = forms.EmailField(
        required=False,
        label="Email address",
        widget=forms.EmailInput(attrs={"placeholder": "e.g. ananya@example.com"}),
    )
    aadhaar_linked = forms.BooleanField(
        required=False,
        label="Bank account is linked to Aadhaar (DBT active)",
    )
    annual_income = forms.IntegerField(
        min_value=0,
        label="Annual family income (Rs)",
        widget=forms.NumberInput(attrs={"placeholder": "e.g. 240000"}),
    )
    disability_status = forms.ChoiceField(
        choices=DISABILITY_CHOICES,
        initial="no",
        required=False,
        label="Person with Disability (PwD)",
    )

    # Academic details
    education_level = forms.ChoiceField(
        choices=[e for e in EDU_CHOICES if e[0] != "any"],
        label="Current education level",
    )
    current_course = forms.CharField(
        max_length=150,
        required=False,
        label="Current course / stream",
        widget=forms.TextInput(attrs={"placeholder": "e.g. B.Tech Computer Science, Class 12 PCM"}),
    )
    current_institution = forms.CharField(
        max_length=200,
        required=False,
        label="Current school / college name",
        widget=forms.TextInput(
            attrs={"placeholder": "e.g. DBS Global University, IIT Delhi, Delhi Public School"}
        ),
    )
    current_year = forms.CharField(
        max_length=50,
        required=False,
        label="Current year / semester",
        widget=forms.TextInput(attrs={"placeholder": "e.g. 2nd Year, 3rd Semester, Class 12"}),
    )
    latest_percentage = forms.CharField(
        max_length=20,
        required=False,
        label="Latest % or CGPA",
        widget=forms.TextInput(attrs={"placeholder": "e.g. 84.5% or 8.6 CGPA"}),
    )
    board_10th = forms.CharField(
        max_length=100,
        required=False,
        label="10th Board",
        widget=forms.TextInput(attrs={"placeholder": "e.g. CBSE, ICSE, State Board"}),
    )
    percentage_10th = forms.CharField(
        max_length=20,
        required=False,
        label="10th % / CGPA",
        widget=forms.TextInput(attrs={"placeholder": "e.g. 88%"}),
    )
    board_12th = forms.CharField(
        max_length=100,
        required=False,
        label="12th Board",
        widget=forms.TextInput(attrs={"placeholder": "e.g. CBSE, ISC, State Board"}),
    )
    percentage_12th = forms.CharField(
        max_length=20,
        required=False,
        label="12th % / CGPA",
        widget=forms.TextInput(attrs={"placeholder": "e.g. 85%"}),
    )
    is_student = forms.BooleanField(
        required=False,
        initial=True,
        label="I am currently an active student",
    )

    # Professional & other details
    employment_status = forms.ChoiceField(
        choices=EMPLOYMENT_CHOICES,
        initial="student",
        required=False,
        label="Employment / Internship status",
    )
    achievements_notes = forms.CharField(
        required=False,
        label="Key academic & extra-curricular achievements summary",
        widget=forms.Textarea(
            attrs={"rows": 2, "placeholder": "e.g. State Olympiad rank holder, published paper, school topper"}
        ),
    )
    scholarships_availed = forms.CharField(
        required=False,
        label="Scholarships already availed (if any)",
        widget=forms.Textarea(
            attrs={"rows": 2, "placeholder": "Mention names and amounts if currently receiving any scholarship"}
        ),
    )
    subscribe_alerts = forms.BooleanField(
        required=False,
        initial=True,
        label="Automatically notify me when new matching scholarships are released",
    )

    def clean(self):
        cleaned_data = super().clean()
        dob = cleaned_data.get("date_of_birth")
        age = cleaned_data.get("age")
        if dob:
            today = date.today()
            calc_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if calc_age >= 0:
                cleaned_data["age"] = calc_age
        elif age is None:
            self.add_error("age", "Please enter your age or date of birth.")
        return cleaned_data

    def as_profile(self):
        d = self.cleaned_data
        dob = d.get("date_of_birth")
        return {
            "name": d.get("name", ""),
            "date_of_birth": dob.isoformat() if dob else "",
            "age": d.get("age", 0),
            "gender": d.get("gender", "other"),
            "category": d.get("category", "general"),
            "state": d.get("state", ""),
            "district": d.get("district", ""),
            "address": d.get("address", ""),
            "phone": d.get("phone", ""),
            "email": d.get("email", ""),
            "aadhaar_linked": d.get("aadhaar_linked", False),
            "annual_income": d.get("annual_income", 0),
            "disability_status": d.get("disability_status", "no"),
            "education_level": d.get("education_level", "undergraduate"),
            "current_course": d.get("current_course", ""),
            "current_institution": d.get("current_institution", ""),
            "current_year": d.get("current_year", ""),
            "latest_percentage": d.get("latest_percentage", ""),
            "board_10th": d.get("board_10th", ""),
            "percentage_10th": d.get("percentage_10th", ""),
            "board_12th": d.get("board_12th", ""),
            "percentage_12th": d.get("percentage_12th", ""),
            "is_student": d.get("is_student", True),
            "employment_status": d.get("employment_status", "student"),
            "achievements_notes": d.get("achievements_notes", ""),
            "scholarships_availed": d.get("scholarships_availed", ""),
            "subscribe_alerts": d.get("subscribe_alerts", True),
        }


class ApplicationForm(forms.ModelForm):
    subscribe_alerts = forms.BooleanField(
        required=False,
        initial=True,
        label="Automatically notify me when new matching scholarships are released",
    )
    class Meta:
        model = Application
        fields = [
            # Personal
            "applicant_name",
            "date_of_birth",
            "age",
            "gender",
            "category",
            "state",
            "district",
            "address",
            "phone",
            "email",
            "aadhaar_linked",
            "annual_income",
            "disability_status",
            # Academic
            "education_level",
            "current_course",
            "current_institution",
            "current_year",
            "latest_percentage",
            "board_10th",
            "percentage_10th",
            "board_12th",
            "percentage_12th",
            # Professional / Other
            "employment_status",
            "achievements_notes",
            "scholarships_availed",
        ]
        labels = {
            "applicant_name": "Full name",
            "date_of_birth": "Date of birth",
            "annual_income": "Annual family income (Rs)",
            "phone": "Phone number",
            "email": "Email address",
            "aadhaar_linked": "Bank account is linked to Aadhaar (DBT active)",
            "disability_status": "Person with Disability (PwD)",
            "education_level": "Current education level",
            "current_course": "Current course / stream",
            "current_institution": "Current school / college name",
            "current_year": "Current year / semester",
            "latest_percentage": "Latest % or CGPA",
            "board_10th": "10th Board",
            "percentage_10th": "10th % / CGPA",
            "board_12th": "12th Board",
            "percentage_12th": "12th % / CGPA",
            "employment_status": "Employment / Internship status",
            "achievements_notes": "Key achievements summary",
            "scholarships_availed": "Scholarships already availed (if any)",
        }
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date", "id": "id_app_dob"}),
            "age": forms.NumberInput(attrs={"id": "id_app_age"}),
            "gender": forms.Select(choices=[g for g in GENDER_CHOICES if g[0] != "any"]),
            "education_level": forms.Select(choices=[e for e in EDU_CHOICES if e[0] != "any"]),
            "address": forms.Textarea(attrs={"rows": 2}),
            "achievements_notes": forms.Textarea(attrs={"rows": 2}),
            "scholarships_availed": forms.Textarea(attrs={"rows": 2}),
            "current_institution": forms.TextInput(
                attrs={"placeholder": "e.g. DBS Global University, IIT Delhi, Delhi Public School"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "disability_status" in self.fields:
            self.fields["disability_status"].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("disability_status"):
            cleaned_data["disability_status"] = "no"
        dob = cleaned_data.get("date_of_birth")
        age = cleaned_data.get("age")
        if dob:
            today = date.today()
            calc_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if calc_age >= 0:
                cleaned_data["age"] = calc_age
        elif age is None:
            self.add_error("age", "Please enter your age or date of birth.")
        return cleaned_data


class AchievementForm(forms.ModelForm):
    class Meta:
        model = Achievement
        fields = ["title", "level", "year", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. State Science Olympiad Gold Medal"}),
            "level": forms.Select(choices=ACHIEVEMENT_LEVEL_CHOICES),
            "year": forms.TextInput(attrs={"placeholder": "e.g. 2024"}),
            "description": forms.TextInput(attrs={"placeholder": "Details, organizing body, or rank"}),
        }


class InstitutionAttendedForm(forms.ModelForm):
    class Meta:
        model = InstitutionAttended
        fields = ["name", "institution_type", "board_affiliation", "city", "state", "years_attended"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Delhi Public School / DBS Global University"}),
            "institution_type": forms.Select(choices=INSTITUTION_TYPE_CHOICES),
            "board_affiliation": forms.TextInput(attrs={"placeholder": "e.g. CBSE / ICSE / AICTE"}),
            "city": forms.TextInput(attrs={"placeholder": "e.g. Dehradun"}),
            "state": forms.TextInput(attrs={"placeholder": "e.g. Uttarakhand"}),
            "years_attended": forms.TextInput(attrs={"placeholder": "e.g. 2021-2023"}),
        }


AchievementFormSet = inlineformset_factory(
    Application,
    Achievement,
    form=AchievementForm,
    extra=1,
    can_delete=True,
)

InstitutionAttendedFormSet = inlineformset_factory(
    Application,
    InstitutionAttended,
    form=InstitutionAttendedForm,
    extra=1,
    can_delete=True,
)
