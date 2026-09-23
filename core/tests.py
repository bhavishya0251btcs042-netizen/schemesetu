from datetime import date
from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from core.models import Scheme, ApprovedInstitution, Application, Achievement, InstitutionAttended
from core.forms import ProfileForm, ApplicationForm
from core.eligibility import evaluate, match_all, normalize_institution_name, matches_institution

User = get_user_model()


class EligibilityEngineTest(TestCase):
    def setUp(self):
        # Unrestricted scheme
        self.open_scheme = Scheme.objects.create(
            name="Open Scholarship",
            short_desc="For all college students.",
            benefits="Allowance",
            documents_required="Marksheet",
            max_income=500000,
            min_age=16,
            max_age=30,
            education_level="undergraduate",
            restrict_to_listed_institutions=False,
        )

        # Restricted scheme with approved institutions
        self.restricted_scheme = Scheme.objects.create(
            name="Premier Technical Scholarship",
            short_desc="Only for approved technical institutes.",
            benefits="Full fee waiver",
            documents_required="Bonafide certificate",
            max_income=800000,
            min_age=17,
            max_age=30,
            education_level="undergraduate",
            restrict_to_listed_institutions=True,
        )
        self.approved_inst1 = ApprovedInstitution.objects.create(
            scheme=self.restricted_scheme,
            name="DBS Global University",
            city="Dehradun",
            state="Uttarakhand",
        )
        self.approved_inst2 = ApprovedInstitution.objects.create(
            scheme=self.restricted_scheme,
            name="Indian Institute of Technology Delhi",
            city="New Delhi",
            state="Delhi",
        )

    def test_unrestricted_scheme_accepts_any_institution(self):
        profile = {
            "name": "Rohan Verma",
            "age": 20,
            "annual_income": 300000,
            "category": "general",
            "gender": "male",
            "education_level": "undergraduate",
            "current_institution": "Random XYZ College",
            "is_student": True,
        }
        ok, reasons = evaluate(self.open_scheme, profile)
        self.assertTrue(ok)
        reason_texts = [r[1] for r in reasons]
        self.assertTrue(any("Open to all" in r for r in reason_texts))

    def test_restricted_scheme_passes_matching_institution(self):
        profile = {
            "name": "Pooja Singh",
            "age": 21,
            "annual_income": 400000,
            "category": "general",
            "gender": "female",
            "education_level": "undergraduate",
            "current_institution": "dbs global university, dehradun",
            "is_student": True,
        }
        ok, reasons = evaluate(self.restricted_scheme, profile)
        self.assertTrue(ok)
        reason_texts = [r[1] for r in reasons]
        self.assertTrue(any("on the approved list" in r for r in reason_texts))

    def test_restricted_scheme_matches_from_institutions_attended_list(self):
        profile = {
            "name": "Amit Kumar",
            "age": 22,
            "annual_income": 350000,
            "category": "obc",
            "gender": "male",
            "education_level": "undergraduate",
            "current_institution": "Unlisted Polytechnic",
            "institutions_attended": [
                {"name": "IIT Delhi"},
                {"name": "Local High School"},
            ],
            "is_student": True,
        }
        ok, reasons = evaluate(self.restricted_scheme, profile)
        self.assertTrue(ok)
        reason_texts = [r[1] for r in reasons]
        self.assertTrue(any("on the approved list" in r for r in reason_texts))

    def test_restricted_scheme_fails_unapproved_institution(self):
        profile = {
            "name": "Vikram Sen",
            "age": 20,
            "annual_income": 200000,
            "category": "sc",
            "gender": "male",
            "education_level": "undergraduate",
            "current_institution": "Unknown Unapproved Institute",
            "is_student": True,
        }
        ok, reasons = evaluate(self.restricted_scheme, profile)
        self.assertFalse(ok)
        fails = [r[1] for r in reasons if r[0] == "fail"]
        self.assertTrue(any("not in this scholarship's approved list" in f for f in fails))

    def test_institution_normalization_and_fuzzy_matching(self):
        inst = self.approved_inst1  # DBS Global University
        self.assertTrue(matches_institution("DBS Global University", inst))
        self.assertTrue(matches_institution("  dbs   global   university  ", inst))
        self.assertTrue(matches_institution("DBS Global University, Dehradun", inst))
        self.assertTrue(matches_institution("D.B.S. Global University", inst))


class ApplicationFlowIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test user and authenticate — required now that check/apply are login-protected
        self.test_user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_login(self.test_user)
        self.scheme = Scheme.objects.create(
            name="Merit Fellowship",
            short_desc="Direct application test fellowship.",
            benefits="Grant Rs 25,000",
            documents_required="College ID",
            max_income=600000,
            min_age=16,
            max_age=32,
            education_level="undergraduate",
            restrict_to_listed_institutions=False,
        )

    def test_check_profile_submission_and_results(self):
        post_data = {
            "name": "Kavya Nair",
            "date_of_birth": "2003-05-14",
            "age": 23,
            "gender": "female",
            "category": "general",
            "annual_income": 350000,
            "state": "Kerala",
            "district": "Ernakulam",
            "phone": "9876543210",
            "email": "kavya@example.com",
            "education_level": "undergraduate",
            "current_course": "B.Sc Physics",
            "current_institution": "DBS Global University",
            "current_year": "3rd Year",
            "latest_percentage": "88%",
            "board_10th": "CBSE",
            "percentage_10th": "92%",
            "board_12th": "CBSE",
            "percentage_12th": "90%",
            "is_student": "on",
            "employment_status": "student",
            # Repeatable achievements
            "ach_title": ["State Physics Talent Search"],
            "ach_level": ["state"],
            "ach_year": ["2023"],
            "ach_desc": ["First Rank"],
            # Repeatable institutions
            "inst_name": ["St. Teresa High School"],
            "inst_type": ["school"],
            "inst_board": ["CBSE"],
            "inst_city": ["Kochi"],
            "inst_state": ["Kerala"],
            "inst_years": ["2019-2021"],
        }
        res = self.client.post(reverse("core:check"), post_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Scholarship Matches for You")
        self.assertContains(res, "Apply here")

    def test_in_app_apply_saves_application_and_related_models(self):
        post_data = {
            "applicant_name": "Siddharth Roy",
            "date_of_birth": "2004-01-10",
            "age": 22,
            "gender": "male",
            "category": "obc",
            "annual_income": 280000,
            "state": "West Bengal",
            "district": "Kolkata",
            "phone": "9812345678",
            "email": "siddharth@example.com",
            "education_level": "undergraduate",
            "current_course": "B.Tech Mechanical",
            "current_institution": "DBS Global University",
            "current_year": "2nd Year",
            "latest_percentage": "8.4 CGPA",
            "employment_status": "student",
            # Achievements formset
            "achievements-TOTAL_FORMS": "1",
            "achievements-INITIAL_FORMS": "0",
            "achievements-MIN_NUM_FORMS": "0",
            "achievements-MAX_NUM_FORMS": "1000",
            "achievements-0-title": "National Coding Hackathon",
            "achievements-0-level": "national",
            "achievements-0-year": "2024",
            "achievements-0-description": "Finalist team",
            # Institutions formset
            "institutions-TOTAL_FORMS": "1",
            "institutions-INITIAL_FORMS": "0",
            "institutions-MIN_NUM_FORMS": "0",
            "institutions-MAX_NUM_FORMS": "1000",
            "institutions-0-name": "Calcutta Boys School",
            "institutions-0-institution_type": "school",
            "institutions-0-board_affiliation": "ICSE",
            "institutions-0-city": "Kolkata",
            "institutions-0-state": "West Bengal",
            "institutions-0-years_attended": "2018-2022",
        }
        res = self.client.post(reverse("core:apply", args=[self.scheme.pk]), post_data, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Application.objects.count(), 1)
        app = Application.objects.first()
        self.assertTrue(app.tracking_id.startswith("DAC"))
        self.assertEqual(app.applicant_name, "Siddharth Roy")
        self.assertEqual(app.achievements.count(), 1)
        self.assertEqual(app.achievements.first().title, "National Coding Hackathon")
        self.assertEqual(app.institutions_attended.count(), 1)
        self.assertEqual(app.institutions_attended.first().name, "Calcutta Boys School")

        # Check tracking page with DAC tracking id
        track_res = self.client.get(reverse("core:track") + f"?tracking_id={app.tracking_id}")
        self.assertEqual(track_res.status_code, 200)
        self.assertContains(track_res, app.tracking_id)
        self.assertContains(track_res, "Siddharth Roy")
        self.assertContains(track_res, "Calcutta Boys School")
        self.assertContains(track_res, "National Coding Hackathon")

    def test_scheme_detail_contains_apply_here_and_no_official_portal_link(self):
        res = self.client.get(reverse("core:scheme_detail", args=[self.scheme.pk]))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Apply here")
        self.assertNotContains(res, "Official portal")
        self.assertNotContains(res, "Official site")

    def test_auto_age_calculation_from_dob(self):
        # DOB 20 years ago
        birth_year = date.today().year - 20
        form = ProfileForm(data={
            "name": "Test User",
            "date_of_birth": f"{birth_year}-01-01",
            "gender": "male",
            "category": "general",
            "annual_income": 150000,
            "education_level": "undergraduate",
            "age": 99,  # Should be auto-corrected based on DOB
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["age"], 20)

    def test_responsive_meta_tag_and_dac_footer_on_all_pages(self):
        urls = [
            reverse("core:home"),
            reverse("core:check"),
            reverse("core:track"),
            reverse("core:scheme_detail", args=[self.scheme.pk]),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200)
            self.assertContains(res, 'meta name="viewport" content="width=device-width, initial-scale=1.0"')
            self.assertContains(res, "Powered by DAC")
            self.assertContains(res, "DBS Global University R&amp;D and S&amp;I Cell")
            self.assertContains(res, 'class="nav-toggle"')

    def test_admin_registration(self):
        self.assertIn(Scheme, site._registry)
        self.assertIn(ApprovedInstitution, site._registry)
        self.assertIn(Application, site._registry)
