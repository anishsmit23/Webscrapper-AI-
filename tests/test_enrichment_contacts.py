from app.enrichment import (
    Page,
    clean_text,
    discover_from_home,
    extract_address,
    extract_emails,
    infer_names,
    local_business_insights,
    looks_like_address,
    repair_education_profile,
)


def test_clean_text_preserves_mailto_and_tel_links() -> None:
    html = """
    <html>
      <body>
        <a href="mailto:SMU.Helpdesk@smu.edu.in?subject=Admissions">Email us</a>
        <a href="tel:+91-9732947000">Call</a>
      </body>
    </html>
    """

    text, _ = clean_text(html)

    assert "Hidden Contact Links" in text
    assert "Email Link: SMU.Helpdesk@smu.edu.in" in text
    assert "Phone Link: +91-9732947000" in text
    assert extract_emails(text) == ["smu.helpdesk@smu.edu.in"]


def test_extract_address_accepts_university_address_without_pin_code() -> None:
    text = """
    Contact Us
    Sikkim Manipal University
    Address
    5th Mile, Tadong, Gangtok, East Sikkim, Sikkim, India
    Phone: +91 9732947000
    Email: smu.helpdesk@smu.edu.in
    """

    address = extract_address(text)

    assert address == "5th Mile, Tadong, Gangtok, East Sikkim, Sikkim, India"
    assert looks_like_address(address)


def test_extract_address_rejects_ranking_sentence() -> None:
    text = """
    National Assessment and Accreditation Council Top Private Universities Ranked in India
    India's Top 20 Technical Universities (Pvt.)
    Admissions open for B.Tech, MBA and MCA
    """

    assert extract_address(text) == ""
    assert not looks_like_address(
        "National Assessment and Accreditation Council Top Private Universities Ranked in India"
    )


def test_extract_address_rejects_program_label_mixed_with_phone() -> None:
    text = """
    Contact
    Tadong Campus ( Medical, Nursing, Physiotherapy, Allied Health, Biotechnology,
    Hospital Administration, Humanities Social Sciences and Liberal Arts ) +91 90836 18855
    """

    assert extract_address(text) == ""
    assert not looks_like_address(
        "Tadong Campus ( Medical, Nursing, Physiotherapy, Allied Health, Biotechnology, Hospital Administration, Humanities Social Sciences and Liberal Arts ) +91 90836 18855"
    )


def test_extract_address_rejects_testimonial_prose_with_country() -> None:
    text = """
    Received when I was a student at SMU.
    Also, the advanced subjects taught in SMU really makes you stand out amongst the many lot of students in this field.
    When I moved to Canada
    """

    bad_address = (
        "Received when I was a student at SMU. Also, the advanced subjects taught in SMU really makes you "
        "stand out amongst the many lot of students in this field. When I moved to Canada"
    )

    assert extract_address(text) == ""
    assert not looks_like_address(bad_address)


def test_infer_names_uses_known_section_path_for_smit() -> None:
    pages = [
        Page(
            url="https://www.smu.edu.in/smit/",
            kind="home",
            html="<html><title>SMIT | Sikkim Manipal University</title><h1>Welcome</h1></html>",
            text="Sikkim Manipal Institute of Technology offers B.Tech M.Tech MBA MCA admissions",
            title="SMIT | Sikkim Manipal University",
        )
    ]

    _, company_name = infer_names(pages, "https://www.smu.edu.in/smit/")

    assert company_name == "Sikkim Manipal Institute Of Technology"


def test_infer_names_does_not_invent_unknown_acronym_expansion() -> None:
    pages = [
        Page(
            url="https://example.edu/abcd/",
            kind="home",
            html="<html><title>ABCD | Example University</title><h1>Welcome</h1></html>",
            text="Admissions campus degree programs",
            title="ABCD | Example University",
        )
    ]

    _, company_name = infer_names(pages, "https://example.edu/abcd/")

    assert company_name != "Sikkim Manipal Institute Of Technology"


def test_discover_from_home_adds_section_fallback_paths() -> None:
    urls = discover_from_home("https://www.smu.edu.in/smit/", "<html></html>")

    assert "https://www.smu.edu.in/smit/contact-us" in urls
    assert "https://www.smu.edu.in/smit/admissions" in urls


def test_education_fallback_does_not_localize_students_to_campus() -> None:
    text = "Sikkim Majitar B.Tech M.Tech MBA admissions placements campus"

    insights = local_business_insights(text, "Sikkim Manipal Institute Of Technology")

    assert "at India" not in insights["core_service"]
    assert "across India" in insights["target_customer"]
    assert "from Sikkim" not in insights["target_customer"]


def test_repair_education_profile_removes_local_overfit() -> None:
    profile = {
        "target_customer": "Prospective students from Sikkim, Majitar evaluating B.Tech programs.",
        "probable_pain_point": "Finding credible B.Tech programs in Sikkim, Majitar.",
    }

    repair_education_profile(profile, "University campus admissions B.Tech M.Tech MBA placement")

    assert "across India" in profile["target_customer"]
    assert "from Sikkim" not in profile["target_customer"]
    assert "in Sikkim" not in profile["probable_pain_point"]
