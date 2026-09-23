"""Plain-language explainer: turns a scheme record into simple, readable sentences."""


def explain(scheme):
    lines = []
    dept = f" run by {scheme.department}" if scheme.department else ""
    lines.append(f"{scheme.name} is a government scholarship/scheme{dept}.")
    lines.append("In simple words: " + scheme.short_desc.rstrip(".") + ".")

    benefits = scheme.benefit_list()
    if benefits:
        lines.append("What you get: " + "; ".join(benefits) + ".")

    who = []
    if scheme.max_income is not None:
        who.append(f"family income up to Rs {scheme.max_income:,} a year")
    cats = scheme.category_list()
    if cats:
        who.append("category " + ", ".join(c.upper() for c in cats))
    if scheme.gender != "any":
        who.append(f"{scheme.get_gender_display().lower()} applicants")
    if scheme.education_level != "any":
        who.append(f"{scheme.get_education_level_display().lower()} students")
    if scheme.state:
        who.append(f"residents of {scheme.state}")
    if scheme.students_only:
        who.append("current students")

    if who:
        lines.append("Who can apply: " + ", ".join(who) + ".")

    # Institution requirement note
    if scheme.restrict_to_listed_institutions:
        appr = list(scheme.approved_institutions.all()[:5])
        if appr:
            sample_names = ", ".join(a.name for a in appr)
            more = " and others" if scheme.approved_institutions.count() > 5 else ""
            lines.append(
                f"Institution restriction: Must be enrolled in an approved institution ({sample_names}{more})."
            )
        else:
            lines.append("Institution restriction: Restricted to listed partner institutions.")
    else:
        lines.append("Institution eligibility: Open to students from all recognized schools, colleges, and universities across India.")

    docs = scheme.document_list()
    if docs:
        lines.append("Keep these documents ready: " + ", ".join(docs) + ".")

    return lines
