import uuid
from django.db import models

CATEGORY_CHOICES = [
    ("general", "General"),
    ("obc", "OBC"),
    ("sc", "SC"),
    ("st", "ST"),
    ("ews", "EWS"),
    ("minority", "Minority"),
]
GENDER_CHOICES = [
    ("any", "Any"),
    ("female", "Female"),
    ("male", "Male"),
    ("other", "Other"),
]
EDU_CHOICES = [
    ("any", "Any"),
    ("school", "School"),
    ("undergraduate", "Undergraduate"),
    ("postgraduate", "Postgraduate"),
    ("phd", "PhD"),
]
EMPLOYMENT_CHOICES = [
    ("student", "Student / Not employed"),
    ("intern", "Internship"),
    ("employed", "Employed / Working"),
    ("other", "Other"),
]
DISABILITY_CHOICES = [
    ("no", "No"),
    ("yes", "Yes"),
]
ACHIEVEMENT_LEVEL_CHOICES = [
    ("school", "School"),
    ("state", "State"),
    ("national", "National"),
    ("international", "International"),
]
INSTITUTION_TYPE_CHOICES = [
    ("school", "School"),
    ("college", "College"),
    ("university", "University"),
]


class Scheme(models.Model):
    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=100, default="Government Services")
    department = models.CharField(max_length=200, blank=True)
    short_desc = models.CharField(max_length=300, help_text="One-line summary in plain words")
    benefits = models.TextField(help_text="One benefit per line")
    documents_required = models.TextField(help_text="One document per line")
    apply_url = models.URLField(blank=True)

    # Eligibility criteria
    max_income = models.PositiveIntegerField(
        null=True, blank=True, help_text="Annual family income cap in INR; blank = no cap"
    )
    min_age = models.PositiveIntegerField(default=0)
    max_age = models.PositiveIntegerField(default=120)
    allowed_categories = models.CharField(
        max_length=200, blank=True,
        help_text="Comma-separated codes (sc,st,obc,ews,minority,general); blank = all",
    )
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="any")
    education_level = models.CharField(max_length=20, choices=EDU_CHOICES, default="any")
    state = models.CharField(max_length=100, blank=True, help_text="Blank = all India")
    students_only = models.BooleanField(default=False)

    # Institution eligibility restriction
    restrict_to_listed_institutions = models.BooleanField(
        default=False,
        help_text="Restrict eligibility to listed approved institutions only",
    )

    class Meta:
        ordering = ["name"]

    def benefit_list(self):
        return [b.strip() for b in self.benefits.splitlines() if b.strip()]

    def document_list(self):
        return [d.strip() for d in self.documents_required.splitlines() if d.strip()]

    def category_list(self):
        return [c.strip().lower() for c in self.allowed_categories.split(",") if c.strip()]

    def __str__(self):
        return self.name


class ApprovedInstitution(models.Model):
    scheme = models.ForeignKey(
        Scheme, on_delete=models.CASCADE, related_name="approved_institutions"
    )
    name = models.CharField(max_length=200, help_text="Approved school / college / university name")
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Approved Institution"
        verbose_name_plural = "Approved Institutions"

    def __str__(self):
        location = f" ({self.city}, {self.state})" if self.city and self.state else (f" ({self.city})" if self.city else "")
        return f"{self.name}{location}"


class Application(models.Model):
    STATUS = [
        ("submitted", "Submitted"),
        ("under_review", "Under review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    tracking_id = models.CharField(max_length=12, unique=True, editable=False)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="applications")

    # Personal details
    applicant_name = models.CharField(max_length=200, verbose_name="Full name")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date of birth")
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    aadhaar_linked = models.BooleanField(
        default=False, verbose_name="Aadhaar-linked bank account"
    )
    annual_income = models.PositiveIntegerField(verbose_name="Family annual income (Rs)")
    disability_status = models.CharField(
        max_length=10, choices=DISABILITY_CHOICES, default="no", blank=True, verbose_name="Disability status"
    )

    # Academic details
    education_level = models.CharField(max_length=20, choices=EDU_CHOICES, verbose_name="Current education level")
    current_course = models.CharField(max_length=150, blank=True, verbose_name="Current course / stream")
    current_institution = models.CharField(max_length=200, blank=True, verbose_name="Current institution name")
    current_year = models.CharField(max_length=50, blank=True, verbose_name="Current year / semester")
    latest_percentage = models.CharField(max_length=20, blank=True, verbose_name="Latest % or CGPA")
    board_10th = models.CharField(max_length=100, blank=True, verbose_name="10th Board")
    percentage_10th = models.CharField(max_length=20, blank=True, verbose_name="10th % / CGPA")
    board_12th = models.CharField(max_length=100, blank=True, verbose_name="12th Board")
    percentage_12th = models.CharField(max_length=20, blank=True, verbose_name="12th % / CGPA")

    # Professional & other details
    employment_status = models.CharField(
        max_length=50, blank=True, choices=EMPLOYMENT_CHOICES, default="student", verbose_name="Employment / Internship status"
    )
    achievements_notes = models.TextField(blank=True, verbose_name="Key achievements summary")
    scholarships_availed = models.TextField(blank=True, verbose_name="Scholarships already availed (if any)")

    status = models.CharField(max_length=20, choices=STATUS, default="submitted")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            self.tracking_id = "DAC" + uuid.uuid4().hex[:6].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_id} - {self.scheme.name}"


class Achievement(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="achievements"
    )
    title = models.CharField(max_length=200, verbose_name="Achievement title")
    level = models.CharField(
        max_length=50, choices=ACHIEVEMENT_LEVEL_CHOICES, default="school", verbose_name="Level"
    )
    year = models.CharField(max_length=20, blank=True, verbose_name="Year")
    description = models.TextField(blank=True, verbose_name="Description")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.title} ({self.get_level_display()})"


class InstitutionAttended(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="institutions_attended"
    )
    name = models.CharField(max_length=200, verbose_name="Institution name")
    institution_type = models.CharField(
        max_length=50, choices=INSTITUTION_TYPE_CHOICES, default="school", verbose_name="Type"
    )
    board_affiliation = models.CharField(
        max_length=150, blank=True, verbose_name="Board / Affiliation"
    )
    city = models.CharField(max_length=100, blank=True, verbose_name="City")
    state = models.CharField(max_length=100, blank=True, verbose_name="State")
    years_attended = models.CharField(max_length=50, blank=True, verbose_name="Years attended")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class StudentSubscriber(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    age = models.PositiveIntegerField(default=18)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="any")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="general")
    annual_income = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=100, blank=True)
    education_level = models.CharField(max_length=20, choices=EDU_CHOICES, default="undergraduate")
    current_institution = models.CharField(max_length=200, blank=True)
    is_student = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, help_text="Set to false to unsubscribe from alerts")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def as_profile(self):
        """Convert subscriber into a profile dict for the eligibility engine."""
        return {
            "name": self.name,
            "email": self.email,
            "age": self.age,
            "gender": self.gender,
            "category": self.category,
            "annual_income": self.annual_income,
            "state": self.state,
            "education_level": self.education_level,
            "current_institution": self.current_institution,
            "is_student": self.is_student,
            "institutions_attended": [],
        }


class NotificationLog(models.Model):
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("read", "Read"),
    ]
    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("in_app", "In-App"),
        ("sms", "SMS"),
    ]
    subscriber = models.ForeignKey(
        StudentSubscriber, on_delete=models.CASCADE, related_name="notifications"
    )
    scheme = models.ForeignKey(
        Scheme, on_delete=models.CASCADE, related_name="notifications"
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="email")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    subject = models.CharField(max_length=250)
    message = models.TextField()
    matched_reasons = models.TextField(blank=True, help_text="Summary of matching criteria")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("subscriber", "scheme")

    def __str__(self):
        return f"Alert to {self.subscriber.email} for {self.scheme.name} ({self.status})"

    @property
    def match_reasons(self):
        """Non-empty matched_reasons text."""
        return self.matched_reasons.strip()

    @property
    def match_reasons_list(self):
        """Return matched_reasons as a list of non-empty lines."""
        if not self.matched_reasons:
            return []
        return [r.strip() for r in self.matched_reasons.splitlines() if r.strip()]
