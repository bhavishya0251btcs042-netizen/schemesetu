"""Rule-based eligibility engine: matches a citizen profile against a scheme's criteria."""
import re

COMMON_ACRONYMS = {
    "iit": "indian institute of technology",
    "nit": "national institute of technology",
    "iiit": "indian institute of information technology",
    "bits": "birla institute of technology and science",
    "dps": "delhi public school",
    "dtu": "delhi technological university",
    "du": "delhi university",
    "jnu": "jawaharlal nehru university",
    "bhu": "banaras hindu university",
    "amu": "aligarh muslim university",
    "kv": "kendriya vidyalaya",
    "jnv": "jawahar navodaya vidyalaya",
}


def normalize_institution_name(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    expanded = [COMMON_ACRONYMS.get(t, t) for t in tokens]
    return " ".join(" ".join(expanded).split())


def matches_institution(cand_name, approved_inst):
    norm_cand = normalize_institution_name(cand_name)
    norm_appr = normalize_institution_name(approved_inst.name)
    if not norm_cand or not norm_appr:
        return False
    # Exact or substring containment
    if norm_appr in norm_cand or norm_cand in norm_appr:
        return True

    # Token-set overlap matching
    cand_tokens = set(norm_cand.split()) - {"of", "in", "and", "the", "&"}
    appr_tokens = set(norm_appr.split()) - {"of", "in", "and", "the", "&"}
    if cand_tokens and appr_tokens:
        if cand_tokens.issubset(appr_tokens) or appr_tokens.issubset(cand_tokens):
            return True
        intersection = cand_tokens.intersection(appr_tokens)
        if len(intersection) >= 2 and (len(intersection) >= len(appr_tokens) * 0.6 or len(intersection) >= len(cand_tokens) * 0.6):
            return True

    return False


def check_institution_eligibility(scheme, profile):
    """
    Check if the student's current institution or any attended institution matches the scheme's approved list.
    Returns (ok, reason_tuple).
    """
    if not scheme.restrict_to_listed_institutions:
        return True, ("pass", "✓ Open to all recognized schools, colleges & universities")

    approved_qs = list(scheme.approved_institutions.all())
    if not approved_qs:
        return True, ("pass", "✓ Open to all recognized schools, colleges & universities")

    # Collect candidate institutions from current and past institutions
    candidates = []
    current_inst = profile.get("current_institution", "")
    if current_inst and str(current_inst).strip():
        candidates.append(str(current_inst).strip())

    for item in profile.get("institutions_attended", []):
        name = ""
        if isinstance(item, dict):
            name = item.get("name", "").strip()
        elif hasattr(item, "name"):
            name = item.name.strip()
        elif isinstance(item, str):
            name = item.strip()
        if name and name not in candidates:
            candidates.append(name)

    if not candidates:
        return False, ("fail", "✗ Your institution is not in this scholarship's approved list")

    for cand in candidates:
        for appr in approved_qs:
            if matches_institution(cand, appr):
                return True, ("pass", f"✓ Your institution ({appr.name}) is on the approved list")

    return False, ("fail", "✗ Your institution is not in this scholarship's approved list")


def evaluate(scheme, profile):
    """Return (is_eligible, reasons) where reasons is a list of (status, text)."""
    reasons = []
    ok = True

    # 1. Income check
    if scheme.max_income is not None:
        income = profile.get("annual_income") or 0
        if income <= scheme.max_income:
            reasons.append(("pass", f"Income within limit (up to Rs {scheme.max_income:,})"))
        else:
            reasons.append(("fail", f"Income above the limit (up to Rs {scheme.max_income:,})"))
            ok = False

    # 2. Age check
    age = profile.get("age") or 0
    if scheme.min_age <= age <= scheme.max_age:
        reasons.append(("pass", f"Age within {scheme.min_age}-{scheme.max_age}"))
    else:
        reasons.append(("fail", f"Age must be between {scheme.min_age} and {scheme.max_age}"))
        ok = False

    # 3. Category check
    cats = scheme.category_list()
    if cats:
        cat = (profile.get("category") or "").lower()
        if cat in cats:
            reasons.append(("pass", "Your category is covered"))
        else:
            labels = ", ".join(c.upper() for c in cats)
            reasons.append(("fail", f"Only for: {labels}"))
            ok = False

    # 4. Gender check
    if scheme.gender != "any":
        user_gender = profile.get("gender")
        if user_gender and user_gender != scheme.gender:
            reasons.append(("fail", f"For {scheme.get_gender_display()} applicants only"))
            ok = False
        elif user_gender == scheme.gender:
            reasons.append(("pass", f"For {scheme.get_gender_display()} applicants"))

    # 5. Education level check
    if scheme.education_level != "any":
        user_edu = profile.get("education_level") or profile.get("current_education_level")
        if user_edu and user_edu != scheme.education_level:
            reasons.append(("fail", f"Requires {scheme.get_education_level_display()} level"))
            ok = False
        elif user_edu == scheme.education_level:
            reasons.append(("pass", f"Education level matches ({scheme.get_education_level_display()})"))

    # 6. State check
    if scheme.state:
        user_state = (profile.get("state") or "").strip().lower()
        if user_state == scheme.state.strip().lower():
            reasons.append(("pass", f"Available in {scheme.state}"))
        else:
            reasons.append(("fail", f"Only for residents of {scheme.state}"))
            ok = False

    # 7. Student check
    if scheme.students_only:
        is_stud = (
            profile.get("is_student")
            or profile.get("employment_status") == "student"
            or bool(profile.get("current_institution"))
        )
        if not is_stud:
            reasons.append(("fail", "For current students only"))
            ok = False
        else:
            reasons.append(("pass", "Current student status confirmed"))

    # 8. Approved institution check
    inst_ok, inst_reason = check_institution_eligibility(scheme, profile)
    reasons.append(inst_reason)
    if not inst_ok:
        ok = False

    return ok, reasons


def match_all(schemes, profile):
    """Split schemes into eligible and near-miss lists, each with reasons."""
    eligible, others = [], []
    for scheme in schemes:
        ok, reasons = evaluate(scheme, profile)
        entry = {
            "scheme": scheme,
            "reasons": reasons,
            "fails": [r for r in reasons if r[0] == "fail"],
        }
        (eligible if ok else others).append(entry)
    others.sort(key=lambda e: len(e["fails"]))
    return eligible, others
