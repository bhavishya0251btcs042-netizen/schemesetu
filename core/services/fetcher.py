"""Automated Scholarship Ingestion Engine.

Fetches scholarship announcements from external platform feeds (JSON/REST APIs or scraping)
and normalizes criteria into SchemeSetu's Scheme and ApprovedInstitution models.
Designed to work seamlessly both online and offline with zero external dependencies.
"""
import json
import logging
import urllib.request
from typing import Dict, List, Tuple

from core.models import ApprovedInstitution, Scheme

logger = logging.getLogger(__name__)

# Official External Sources Feeds Registry
EXTERNAL_PORTAL_FEEDS = [
    {
        "name": "AICTE Swanath Scholarship Scheme",
        "department": "All India Council for Technical Education (AICTE)",
        "domain": "Technical Education",
        "short_desc": "Financial assistance for orphans, children of deceased parents (COVID-19), and children of Armed Forces personnel pursuing technical degrees.",
        "benefits": "Rs 50,000 per annum for tuition & hostel expenses\nDirect Benefit Transfer (DBT) each academic year\nLaptop and book allowance",
        "documents_required": "Death certificate of parents / Armed forces certificate\nIncome certificate\nAdmission letter in AICTE approved institution\nAadhaar card\nMarksheet of 12th / Diploma",
        "max_income": 800000,
        "min_age": 16,
        "max_age": 30,
        "allowed_categories": "",
        "gender": "any",
        "education_level": "undergraduate",
        "state": "",
        "students_only": True,
        "restrict_to_listed_institutions": True,
        "approved_institutions": [
            {"name": "DBS Global University", "city": "Dehradun", "state": "Uttarakhand"},
            {"name": "Indian Institute of Technology Delhi", "city": "New Delhi", "state": "Delhi"},
            {"name": "Delhi Technological University", "city": "Delhi", "state": "Delhi"},
            {"name": "National Institute of Technology", "city": "Kurukshetra", "state": "Haryana"},
        ],
    },
    {
        "name": "UGC Ishan Uday Special Scholarship (NER)",
        "department": "University Grants Commission (UGC)",
        "domain": "Higher Education",
        "short_desc": "Special scholarship scheme for North Eastern Region students enrolled in general and professional degree courses.",
        "benefits": "Rs 5,400 per month for general degree courses\nRs 7,800 per month for technical/medical courses\nDisbursed directly into Aadhaar-linked bank account",
        "documents_required": "Domicile certificate of North Eastern Region (NER)\nAnnual family income certificate\nAadhaar card\nCollege admission bonafide\n12th marksheet",
        "max_income": 450000,
        "min_age": 17,
        "max_age": 28,
        "allowed_categories": "",
        "gender": "any",
        "education_level": "undergraduate",
        "state": "",
        "students_only": True,
        "restrict_to_listed_institutions": False,
        "approved_institutions": [],
    },
    {
        "name": "Prime Minister's Research Fellowship (PMRF)",
        "department": "Ministry of Education",
        "domain": "Doctoral Research",
        "short_desc": "Prestige doctoral fellowship for top students undertaking PhD programs in Science and Technology.",
        "benefits": "Rs 70,000 per month for first 2 years\nRs 75,000 per month for 3rd year\nRs 80,000 per month for 4th & 5th years\nAnnual research grant of Rs 2 Lakhs",
        "documents_required": "Undergraduate/Master's degree certificate with minimum 8.0 CGPA\nResearch proposal & statement of purpose\nAadhaar card\nRecommendation letters",
        "max_income": None,
        "min_age": 21,
        "max_age": 35,
        "allowed_categories": "",
        "gender": "any",
        "education_level": "phd",
        "state": "",
        "students_only": True,
        "restrict_to_listed_institutions": True,
        "approved_institutions": [
            {"name": "Indian Institute of Technology Delhi", "city": "New Delhi", "state": "Delhi"},
            {"name": "DBS Global University", "city": "Dehradun", "state": "Uttarakhand"},
            {"name": "Birla Institute of Technology and Science", "city": "Pilani", "state": "Rajasthan"},
        ],
    },
    {
        "name": "National Overseas Scholarship for SC/ST Students",
        "department": "Ministry of Social Justice & Empowerment",
        "domain": "International Education",
        "short_desc": "Financial assistance to low-income SC, ST, and De-notified Nomadic Tribe students for pursuing Master's and PhD abroad.",
        "benefits": "Full tuition fees paid directly to international university\nAnnual maintenance allowance USD 15,400 / GBP 9,900\nAirfare and health insurance covered",
        "documents_required": "Caste certificate\nIncome certificate under Rs 8 Lakh\nOffer letter from accredited top 500 global university\nPassport\n10th, 12th & Degree marksheets",
        "max_income": 800000,
        "min_age": 18,
        "max_age": 35,
        "allowed_categories": "sc,st",
        "gender": "any",
        "education_level": "postgraduate",
        "state": "",
        "students_only": True,
        "restrict_to_listed_institutions": False,
        "approved_institutions": [],
    },
]


class ScholarshipFetcher:
    """Ingests and normalizes external scholarship opportunities."""

    def __init__(self, source_url: str = None):
        self.source_url = source_url

    def fetch_feed_data(self) -> List[Dict]:
        """Fetch raw data from live network endpoint or fallback to portal registry."""
        if self.source_url:
            try:
                req = urllib.request.Request(
                    self.source_url,
                    headers={"User-Agent": "SchemeSetu-Scholarship-Crawler/1.0"},
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw = response.read().decode("utf-8")
                    data = json.loads(raw)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "scholarships" in data:
                        return data["scholarships"]
            except Exception as e:
                logger.warning(
                    f"External URL fetch failed ({e}). Falling back to official portal feeds registry."
                )

        return EXTERNAL_PORTAL_FEEDS

    def sync_to_database(self, custom_records: List[Dict] = None) -> Tuple[List[Scheme], List[Scheme]]:
        """
        Sync incoming records into Scheme and ApprovedInstitution models.
        Returns (new_schemes, updated_schemes).
        """
        records = custom_records if custom_records is not None else self.fetch_feed_data()
        new_schemes = []
        updated_schemes = []

        for item in records:
            name = item.get("name", "").strip()
            if not name:
                continue

            defaults = {
                "department": item.get("department", ""),
                "domain": item.get("domain", "Government Services"),
                "short_desc": item.get("short_desc", ""),
                "benefits": item.get("benefits", ""),
                "documents_required": item.get("documents_required", ""),
                "max_income": item.get("max_income"),
                "min_age": item.get("min_age", 0),
                "max_age": item.get("max_age", 120),
                "allowed_categories": item.get("allowed_categories", ""),
                "gender": item.get("gender", "any"),
                "education_level": item.get("education_level", "any"),
                "state": item.get("state", ""),
                "students_only": item.get("students_only", True),
                "restrict_to_listed_institutions": item.get("restrict_to_listed_institutions", False),
            }

            scheme, created = Scheme.objects.get_or_create(name=name, defaults=defaults)
            if created:
                new_schemes.append(scheme)
            else:
                for k, v in defaults.items():
                    setattr(scheme, k, v)
                scheme.save()
                updated_schemes.append(scheme)

            # Sync approved institutions
            approved_list = item.get("approved_institutions", [])
            for inst in approved_list:
                inst_name = inst.get("name", "").strip()
                if inst_name:
                    ApprovedInstitution.objects.get_or_create(
                        scheme=scheme,
                        name=inst_name,
                        defaults={
                            "city": inst.get("city", ""),
                            "state": inst.get("state", ""),
                        },
                    )

        return new_schemes, updated_schemes
