"""One-shot setup: seed schemes, approved institutions, and create an admin user. Safe to run repeatedly."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import ApprovedInstitution, Scheme, StudentSubscriber

SCHEMES = [
    {
        "name": "Post-Matric Scholarship (SC/ST/OBC)",
        "department": "Ministry of Social Justice & Empowerment",
        "short_desc": "Financial help for SC, ST and OBC students studying after class 10.",
        "benefits": "Full or partial tuition fee reimbursement\nMonthly maintenance allowance\nBook and stationery grant",
        "documents_required": "Caste certificate\nIncome certificate\nAadhaar card\nBank passbook\nPrevious marksheet",
        "apply_url": "",
        "max_income": 250000,
        "min_age": 15,
        "max_age": 35,
        "allowed_categories": "sc,st,obc",
        "education_level": "any",
        "students_only": True,
        "restrict_to_listed_institutions": False,
        "approved_institutions": [],
    },
    {
        "name": "Pragati Scholarship for Girls (AICTE)",
        "department": "All India Council for Technical Education",
        "short_desc": "Support for girl students in AICTE-approved technical and engineering institutions.",
        "benefits": "Rs 50,000 per year tuition & contingency support\nDirect Bank Transfer (DBT)\nEmpowers female technical aspirants",
        "documents_required": "Income certificate\nAdmission proof from AICTE approved institute\nAadhaar card\nBank passbook\nClass 12 marksheet",
        "apply_url": "",
        "max_income": 800000,
        "min_age": 17,
        "max_age": 30,
        "gender": "female",
        "education_level": "undergraduate",
        "students_only": True,
        "restrict_to_listed_institutions": True,
        "approved_institutions": [
            {"name": "DBS Global University", "city": "Dehradun", "state": "Uttarakhand"},
            {"name": "Indian Institute of Technology Delhi", "city": "New Delhi", "state": "Delhi"},
            {"name": "Delhi Technological University", "city": "Delhi", "state": "Delhi"},
            {"name": "National Institute of Technology", "city": "Kurukshetra", "state": "Haryana"},
            {"name": "Birla Institute of Technology and Science", "city": "Pilani", "state": "Rajasthan"},
        ],
    },
    {
        "name": "Central Sector Scheme of Scholarship",
        "department": "Department of Higher Education",
        "short_desc": "Merit scholarship for college toppers enrolled in recognized universities and colleges.",
        "benefits": "Rs 12,000 per year for undergraduate studies\nRs 20,000 per year for post-graduate studies",
        "documents_required": "Class 12 marksheet\nIncome certificate\nAadhaar card\nBank passbook\nCollege ID / Bonafide",
        "apply_url": "",
        "max_income": 450000,
        "min_age": 17,
        "max_age": 30,
        "education_level": "undergraduate",
        "students_only": True,
        "restrict_to_listed_institutions": True,
        "approved_institutions": [
            {"name": "DBS Global University", "city": "Dehradun", "state": "Uttarakhand"},
            {"name": "St. Stephen's College", "city": "Delhi", "state": "Delhi"},
            {"name": "Lady Shri Ram College", "city": "New Delhi", "state": "Delhi"},
            {"name": "Loyola College", "city": "Chennai", "state": "Tamil Nadu"},
            {"name": "Fergusson College", "city": "Pune", "state": "Maharashtra"},
            {"name": "St. Xavier's College", "city": "Mumbai", "state": "Maharashtra"},
        ],
    },
    {
        "name": "PM-YASASVI Scholarship (OBC/EBC)",
        "department": "Ministry of Social Justice & Empowerment",
        "short_desc": "Scholarship for OBC, EBC and DNT students in classes 9 to 12.",
        "benefits": "Annual scholarship for school students\nCovers tuition and hostel costs",
        "documents_required": "Caste certificate\nIncome certificate\nAadhaar card\nSchool bonafide\nBank passbook",
        "apply_url": "",
        "max_income": 250000,
        "min_age": 13,
        "max_age": 20,
        "allowed_categories": "obc",
        "education_level": "school",
        "students_only": True,
        "restrict_to_listed_institutions": False,
        "approved_institutions": [],
    },
    {
        "name": "Merit Scholarship for EWS Students",
        "department": "State Education Department",
        "short_desc": "Merit-based aid for Economically Weaker Section students.",
        "benefits": "Tuition fee waiver\nAnnual maintenance grant",
        "documents_required": "EWS certificate\nIncome certificate\nAadhaar card\nMarksheet\nBank passbook",
        "apply_url": "",
        "max_income": 800000,
        "min_age": 15,
        "max_age": 30,
        "allowed_categories": "ews",
        "education_level": "any",
        "students_only": True,
        "restrict_to_listed_institutions": False,
        "approved_institutions": [],
    },
    {
        "name": "Post-Matric Scholarship for Minorities",
        "department": "Ministry of Minority Affairs",
        "short_desc": "Financial support for students from notified minority communities.",
        "benefits": "Admission and tuition fee support\nMaintenance allowance",
        "documents_required": "Minority community declaration\nIncome certificate\nAadhaar card\nMarksheet\nBank passbook",
        "apply_url": "",
        "max_income": 200000,
        "min_age": 15,
        "max_age": 35,
        "allowed_categories": "minority",
        "education_level": "any",
        "students_only": True,
        "restrict_to_listed_institutions": False,
        "approved_institutions": [],
    },
    {
        "name": "National Means-cum-Merit Scholarship",
        "department": "Department of School Education & Literacy",
        "short_desc": "Scholarship to help meritorious students continue school in approved secondary schools.",
        "benefits": "Rs 12,000 per year through classes 9 to 12",
        "documents_required": "Class 8 marksheet\nIncome certificate\nAadhaar card\nSchool bonafide\nBank passbook",
        "apply_url": "",
        "max_income": 350000,
        "min_age": 13,
        "max_age": 16,
        "education_level": "school",
        "students_only": True,
        "restrict_to_listed_institutions": True,
        "approved_institutions": [
            {"name": "Delhi Public School", "city": "New Delhi", "state": "Delhi"},
            {"name": "Kendriya Vidyalaya", "city": "Dehradun", "state": "Uttarakhand"},
            {"name": "St. Xavier's High School", "city": "Mumbai", "state": "Maharashtra"},
            {"name": "Jawahar Navodaya Vidyalaya", "city": "Haridwar", "state": "Uttarakhand"},
        ],
    },
    {
        "name": "State Merit Scholarship (Uttar Pradesh)",
        "department": "UP Department of Education",
        "short_desc": "Merit scholarship for students who are residents of Uttar Pradesh.",
        "benefits": "Annual merit award\nRenewable each year on good results",
        "documents_required": "Domicile certificate\nIncome certificate\nAadhaar card\nMarksheet\nBank passbook",
        "apply_url": "",
        "max_income": 500000,
        "min_age": 15,
        "max_age": 30,
        "state": "Uttar Pradesh",
        "education_level": "any",
        "students_only": True,
        "restrict_to_listed_institutions": False,
        "approved_institutions": [],
    },
]


class Command(BaseCommand):
    help = "Seed sample schemes, approved institutions, and create the default admin user."

    def handle(self, *args, **options):
        schemes_created = 0
        institutions_created = 0

        for data in SCHEMES:
            scheme_data = {k: v for k, v in data.items() if k != "approved_institutions"}
            approved_list = data.get("approved_institutions", [])

            scheme, created = Scheme.objects.get_or_create(
                name=scheme_data["name"],
                defaults=scheme_data,
            )
            if not created:
                # Keep fields synchronized
                for key, val in scheme_data.items():
                    setattr(scheme, key, val)
                scheme.save()
            else:
                schemes_created += 1

            for inst_data in approved_list:
                _, inst_created = ApprovedInstitution.objects.get_or_create(
                    scheme=scheme,
                    name=inst_data["name"],
                    defaults={
                        "city": inst_data.get("city", ""),
                        "state": inst_data.get("state", ""),
                    },
                )
                if inst_created:
                    institutions_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Schemes ready: {Scheme.objects.count()} total ({schemes_created} new). "
                f"Approved institutions ready: {ApprovedInstitution.objects.count()} total ({institutions_created} new)."
            )
        )

        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@dac.local", "admin123")
            self.stdout.write(
                self.style.SUCCESS("Admin created  ->  username: admin  password: admin123")
            )
        else:
            self.stdout.write("Admin user already exists.")

        # Seed demo subscribers so sync_scholarships --notify-all is immediately demonstrable
        DEMO_SUBSCRIBERS = [
            {
                "name": "Ananya Sharma",
                "email": "ananya@dbs.edu.in",
                "age": 20,
                "gender": "female",
                "category": "general",
                "annual_income": 300000,
                "state": "Uttarakhand",
                "education_level": "undergraduate",
                "current_institution": "DBS Global University",
                "is_student": True,
                "is_active": True,
            },
            {
                "name": "Rohan Verma",
                "email": "rohan@iitd.ac.in",
                "age": 22,
                "gender": "male",
                "category": "sc",
                "annual_income": 180000,
                "state": "Delhi",
                "education_level": "undergraduate",
                "current_institution": "IIT Delhi",
                "is_student": True,
                "is_active": True,
            },
            {
                "name": "Priya Singh",
                "email": "priya@dbs.edu.in",
                "age": 19,
                "gender": "female",
                "category": "obc",
                "annual_income": 220000,
                "state": "Uttarakhand",
                "education_level": "undergraduate",
                "current_institution": "DBS Global University",
                "is_student": True,
                "is_active": True,
            },
        ]
        subs_created = 0
        for sub_data in DEMO_SUBSCRIBERS:
            _, created = StudentSubscriber.objects.get_or_create(
                email=sub_data["email"], defaults=sub_data
            )
            if created:
                subs_created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo subscribers ready: {StudentSubscriber.objects.count()} total ({subs_created} new). "
                "Run: python manage.py sync_scholarships --notify-all"
            )
        )

        # Ensure default admin superuser exists
        User = get_user_model()
        admin_username = "admin"
        admin_email = "admin@schemesetu.dac.gov.in"
        admin_password = "Admin@12345"
        admin_user = User.objects.filter(username=admin_username).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                first_name="Admin",
                last_name="Superuser",
            )
        else:
            admin_user.set_password(admin_password)
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Admin superuser verified: username='{admin_username}', password='{admin_password}'"
            )
        )


