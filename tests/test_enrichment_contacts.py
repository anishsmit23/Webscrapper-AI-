from app.enrichment import clean_text, extract_address, extract_emails, looks_like_address


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
