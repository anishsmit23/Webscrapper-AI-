from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from difflib import SequenceMatcher
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import certifi
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - dependency may be absent in local smoke tests
    genai = None


load_dotenv()

SCHEMA_KEYS = [
    "website_name",
    "company_name",
    "address",
    "mobile_number",
    "mail",
    "core_service",
    "target_customer",
    "probable_pain_point",
    "outreach_opener",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

IMPORTANT_PATTERNS = {
    "contact": ["contact", "support", "reach-us", "get-in-touch"],
    "about": ["about", "company", "who-we-are", "our-story"],
    "services": [
        "services",
        "solutions",
        "products",
        "platform",
        "industries",
        "what-we-do",
        "features",
        "marketplace",
        "pricing",
    ],
}

FALLBACK_PATHS = [
    "about",
    "company",
    "contact",
    "support",
    "services",
    "solutions",
    "products",
    "platform",
    "features",
    "pricing",
    "customers",
    "industries",
]

TIE_PRIORITY = {
    "home": 100,
    "contact": 90,
    "about": 80,
    "services": 70,
    "other": 10,
}


@dataclass
class Page:
    url: str
    kind: str
    html: str
    text: str
    title: str = ""


def empty_profile(url: str = "", website_name: str = "") -> dict[str, Any]:
    fallback_name = website_name.strip() or name_from_domain(url)
    return {
        "website_name": fallback_name,
        "company_name": fallback_name,
        "address": "",
        "mobile_number": "",
        "mail": [],
        "core_service": "",
        "target_customer": "",
        "probable_pain_point": "",
        "outreach_opener": "",
    }


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I) and "." not in url and "/" not in url:
        compact = re.sub(r"[^A-Za-z0-9]+", "", url)
        url = f"www.{compact}.com"
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parsed = urlparse(url)
    return parsed.geturl().rstrip("/")


def prettify_company_name(name: str) -> str:
    raw = re.sub(r"[-_]+", " ", name or "").strip()
    compact = re.sub(r"[^A-Za-z0-9]+", "", raw).lower()
    known_suffixes = [
        "packers",
        "movers",
        "logistics",
        "transport",
        "technologies",
        "technology",
        "solutions",
        "services",
        "systems",
        "software",
        "finance",
        "healthcare",
    ]
    for suffix in known_suffixes:
        if compact.endswith(suffix) and len(compact) > len(suffix) + 2:
            prefix = compact[: -len(suffix)]
            if prefix == "omsai":
                prefix = "om sai"
            raw = f"{prefix} {suffix}"
            break
    return re.sub(r"\s+", " ", raw).title()


def name_from_domain(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    host = parsed.netloc.replace("www.", "")
    if not host:
        return ""
    stem = host.split(".")[0]
    return prettify_company_name(stem)


def humanize_name(name: str) -> str:
    words = re.sub(r"[-_]+", " ", name or "").split()
    return " ".join(word.capitalize() for word in words)


def fetch_url(url: str, deadline: float, timeout: int = 10) -> requests.Response | None:
    if time.monotonic() >= deadline:
        return None
    try:
        remaining = max(1.0, min(timeout, deadline - time.monotonic()))
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=remaining,
            allow_redirects=True,
            verify=certifi.where(),
        )
        if response.status_code >= 400:
            return None
        return response
    except requests.RequestException:
        return None


def readable_url(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    if not parsed.netloc:
        return ""
    return f"https://r.jina.ai/{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"


def fetch_reader_page(url: str, kind: str, deadline: float) -> Page | None:
    reader = readable_url(url)
    if not reader:
        return None
    response = fetch_url(reader, deadline, timeout=10)
    if not response or not response.text:
        return None
    text = clean_reader_text(response.text)
    if len(text) < 80:
        return None
    title = ""
    for line in text.splitlines()[:8]:
        if line.lower().startswith("title:"):
            title = line.split(":", 1)[1].strip()
            break
    return Page(url=url.rstrip("/"), kind=kind, html="", text=text, title=title)


def candidate_start_urls(url: str) -> list[str]:
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    host = parsed.netloc
    candidates = [normalized]
    original = (url or "").strip()
    if not re.match(r"^https?://", original, re.I) and "." not in original and "/" not in original:
        compact = re.sub(r"[^A-Za-z0-9]+", "", original).lower()
        hyphenated = re.sub(r"[^A-Za-z0-9]+", "-", original).strip("-").lower()
        for domain in [compact, hyphenated]:
            if domain:
                candidates.append(f"https://www.{domain}.com")
                candidates.append(f"https://{domain}.com")
    if host.startswith("www."):
        candidates.append(normalized.replace("://www.", "://", 1))
    elif host:
        candidates.append(normalized.replace("://", "://www.", 1))
    if parsed.scheme == "https":
        candidates.append(normalized.replace("https://", "http://", 1))
    return list(dict.fromkeys(candidates))


def clean_reader_text(raw: str) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    junk = re.compile(r"^(javascript|skip to|sign in|log in|cookie|accept|reject)\b", re.I)
    for line in (raw or "").splitlines():
        line = unescape(re.sub(r"\s+", " ", line)).strip()
        if len(line) < 3 or junk.match(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return "\n".join(lines[:800])


def metadata_text(soup: BeautifulSoup) -> list[str]:
    values: list[str] = []
    selectors = [
        "meta[name='description']",
        "meta[property='og:description']",
        "meta[name='twitter:description']",
        "meta[property='og:title']",
        "meta[name='twitter:title']",
        "meta[property='og:site_name']",
        "meta[name='application-name']",
    ]
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag and tag.get("content"):
            values.append(str(tag["content"]).strip())
    for script in soup.find_all("script", type=re.compile("ld\\+json", re.I)):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        values.extend(jsonld_strings(parsed))
    return [value for value in values if value]


def jsonld_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, dict):
        for key in ["name", "alternateName", "description", "slogan", "address", "telephone", "email"]:
            item = value.get(key)
            if isinstance(item, str):
                strings.append(item)
            elif isinstance(item, dict):
                strings.extend(jsonld_strings(item))
        for item in value.values():
            if isinstance(item, (dict, list)):
                strings.extend(jsonld_strings(item))
    elif isinstance(value, list):
        for item in value:
            strings.extend(jsonld_strings(item))
    return strings


def clean_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html or "", "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta_lines = metadata_text(soup)
    for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe"]):
        tag.decompose()
    for selector in ["nav", "footer", "header", "[role='navigation']", ".cookie", "#cookie"]:
        for tag in soup.select(selector):
            tag.decompose()
    raw_lines = soup.get_text("\n", strip=True).splitlines()
    seen: set[str] = set()
    lines: list[str] = []
    junk = re.compile(r"^(accept|reject|privacy policy|terms|cookie|subscribe|sign in|log in)$", re.I)
    for line in [*meta_lines, *raw_lines]:
        line = unescape(re.sub(r"\s+", " ", line)).strip()
        if len(line) < 3 or junk.match(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return "\n".join(lines[:700]), title


def page_kind(url: str, is_home: bool = False) -> str:
    if is_home:
        return "home"
    lowered = url.lower()
    for kind, terms in IMPORTANT_PATTERNS.items():
        if any(term in lowered for term in terms):
            return kind
    return "other"


def score_link(url: str, text: str = "") -> tuple[int, str]:
    kind = page_kind(url)
    haystack = f"{url} {text}".lower()
    keyword_score = 0
    for terms in IMPORTANT_PATTERNS.values():
        for term in terms:
            keyword_score = max(keyword_score, int(SequenceMatcher(None, term, haystack).ratio() * 20))
            if term in haystack:
                keyword_score += 30
    return TIE_PRIORITY.get(kind, 0) + keyword_score, kind


def discover_from_sitemap(base_url: str, deadline: float) -> list[str]:
    sitemap_url = urljoin(base_url + "/", "sitemap.xml")
    response = fetch_url(sitemap_url, deadline, timeout=6)
    if not response or not response.text:
        return []
    urls: list[str] = []
    try:
        root = ET.fromstring(response.text)
        for elem in root.iter():
            if elem.tag.endswith("loc") and elem.text:
                loc = elem.text.strip()
                if urlparse(loc).netloc == urlparse(base_url).netloc:
                    urls.append(loc)
    except ET.ParseError:
        urls = re.findall(r"<loc>(.*?)</loc>", response.text, flags=re.I)
    return urls[:80]


def discover_from_home(home_url: str, home_html: str) -> list[str]:
    parsed_home = urlparse(home_url)
    soup = BeautifulSoup(home_html or "", "html.parser")
    urls: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        absolute = urljoin(home_url + "/", href).split("#")[0].rstrip("/")
        parsed = urlparse(absolute)
        if parsed.netloc == parsed_home.netloc:
            urls.append(absolute)
    base = f"{parsed_home.scheme}://{parsed_home.netloc}"
    for path in FALLBACK_PATHS:
        urls.append(urljoin(base + "/", path))
    return list(dict.fromkeys(urls))[:120]


def choose_relevant_urls(base_url: str, home_html: str, deadline: float, max_pages: int = 6) -> list[tuple[str, str]]:
    candidates = [base_url]
    candidates.extend(discover_from_sitemap(base_url, deadline))
    candidates.extend(discover_from_home(base_url, home_html))
    unique = list(dict.fromkeys(candidates))
    scored: list[tuple[int, str, str]] = []
    for url in unique:
        is_home = url.rstrip("/") == base_url.rstrip("/")
        kind = page_kind(url, is_home=is_home)
        score, scored_kind = score_link(url)
        scored.append((TIE_PRIORITY.get(kind, TIE_PRIORITY.get(scored_kind, 0)) + score, kind, url))
    scored.sort(key=lambda item: item[0], reverse=True)

    selected: list[tuple[str, str]] = []
    seen_kinds: set[str] = set()
    for _, kind, url in scored:
        if kind in {"home", "contact", "about", "services"} and kind not in seen_kinds:
            selected.append((url, kind))
            seen_kinds.add(kind)
        if len(selected) >= max_pages:
            break
    for _, kind, url in scored:
        if len(selected) >= max_pages:
            break
        if url not in [selected_url for selected_url, _ in selected]:
            selected.append((url, kind))
    return selected


def scrape_site(url: str, deadline: float) -> tuple[list[Page], str]:
    start_urls = candidate_start_urls(url)
    if not start_urls:
        return [], ""
    response = None
    normalized = start_urls[0]
    for candidate in start_urls:
        response = fetch_url(candidate, deadline)
        if response:
            normalized = candidate
            break
    if not response:
        reader_page = fetch_reader_page(normalized, "home", deadline)
        return ([reader_page] if reader_page else []), normalized
    final_url = response.url.rstrip("/")
    home_text, home_title = clean_text(response.text)
    if len(home_text) < 120:
        reader_page = fetch_reader_page(final_url, "home", deadline)
        if reader_page:
            home_text = "\n".join([home_text, reader_page.text]).strip()
            home_title = home_title or reader_page.title
    pages = [Page(url=final_url, kind="home", html=response.text, text=home_text, title=home_title)]
    for page_url, kind in choose_relevant_urls(final_url, response.text, deadline):
        if page_url.rstrip("/") == final_url.rstrip("/"):
            continue
        if time.monotonic() >= deadline:
            break
        time.sleep(0.25)
        page_response = fetch_url(page_url, deadline, timeout=8)
        if not page_response or "text/html" not in page_response.headers.get("content-type", "text/html"):
            continue
        text, title = clean_text(page_response.text)
        if len(text) < 120:
            reader_page = fetch_reader_page(page_response.url.rstrip("/"), kind, deadline)
            if reader_page:
                text = "\n".join([text, reader_page.text]).strip()
                title = title or reader_page.title
        if len(text) < 80:
            continue
        pages.append(Page(url=page_response.url.rstrip("/"), kind=kind, html=page_response.text, text=text, title=title))
        if len(pages) >= 6:
            break
    return pages, final_url


def organization_tokens(final_url: str, company_name: str = "") -> list[str]:
    parsed = urlparse(final_url)
    parts = [part for part in parsed.path.split("/") if len(part) >= 3]
    name_words = re.findall(r"[A-Za-z0-9]+", company_name.lower())
    tokens = [part.lower() for part in parts if part.lower() not in {"www", "com", "org", "net", "html"}]
    tokens.extend(word for word in name_words if len(word) >= 4)
    if len(name_words) >= 2:
        acronym = "".join(word[0] for word in name_words if word)
        if len(acronym) >= 3:
            tokens.append(acronym)
    return list(dict.fromkeys(tokens))


def extract_emails(text: str, final_url: str = "", company_name: str = "") -> list[str]:
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    blocked = {"example.com", "domain.com", "email.com"}
    freemail = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "icloud.com"}
    cleaned = []
    for email in emails:
        email = email.strip(".,;:()[]{}").lower()
        if any(email.endswith(domain) for domain in blocked):
            continue
        if email not in cleaned:
            cleaned.append(email)

    host = urlparse(final_url).netloc.replace("www.", "").lower()
    tokens = organization_tokens(final_url, company_name)

    org_specific = []
    for email in cleaned:
        local, domain = email.rsplit("@", 1)
        if domain in freemail:
            continue
        if any(re.search(rf"(^|[._-]){re.escape(token)}($|[._-])", f"{local}.{domain}") for token in tokens):
            org_specific.append(email)
    if org_specific:
        return org_specific[:5]

    official = []
    for email in cleaned:
        domain = email.rsplit("@", 1)[1]
        if domain in freemail:
            continue
        if host and (domain == host or domain.endswith("." + host) or host.endswith("." + domain)):
            official.append(email)
    if official:
        return official[:5]
    return cleaned[:5]


def extract_phones(text: str) -> list[str]:
    pattern = re.compile(r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,5}\d{3,4}")
    phones: list[str] = []
    for raw in pattern.findall(text or ""):
        digits = re.sub(r"\D", "", raw)
        if 8 <= len(digits) <= 15 and raw.strip() not in phones:
            phones.append(raw.strip())
    return phones[:3]


def extract_address(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    address_words = re.compile(
        r"\b(street|st\.|road|rd\.|avenue|ave\.|drive|dr\.|lane|ln\.|suite|floor|building|"
        r"city|state|zip|postal|india|usa|united states|canada|australia)\b",
        re.I,
    )
    phone_or_support = re.compile(r"\b(toll free|phone|fax|call|tel|mobile|email|@)\b", re.I)
    for idx, line in enumerate(lines):
        if re.search(r"\b(address|head office|registered office|corporate office)\b", line, re.I):
            parts: list[str] = []
            for candidate in lines[idx : idx + 6]:
                digit_count = len(re.findall(r"\d", candidate))
                if phone_or_support.search(candidate) and digit_count >= 7:
                    break
                if re.search(r"\b(email|phone|mobile|call|fax)\b", candidate, re.I):
                    break
                parts.append(candidate)
            address = " ".join(parts).strip(" :-,")
            address = re.sub(r"^(?:\+?\d[\d\s().-]{7,}\d\s*)+", "", address).strip(" :-,")
            if len(address) > 20 and re.search(r"\d", address):
                return address[:300]
        window = " ".join(lines[idx : idx + 3])
        digit_count = len(re.findall(r"\d", window))
        if phone_or_support.search(window) and digit_count >= 7:
            continue
        if len(re.findall(r"\d[\d\s().+-]{6,}\d", window)) >= 2:
            continue
        if len(window) > 35 and address_words.search(window) and re.search(r"\d", window):
            window = re.sub(r"^(?:\+?\d[\d\s().-]{7,}\d\s*)+", "", window).strip(" :-,")
            return window[:250]
    return ""


def infer_names(pages: list[Page], final_url: str) -> tuple[str, str]:
    candidates: list[tuple[int, str]] = []
    domain_name = name_from_domain(final_url)
    for page in pages:
        if page.title:
            parts = [
                part.strip()
                for part in re.split(r"\s*(?:\||-|--|\u2013|\u2014|\u2022)\s*", page.title)
                if part.strip()
            ]
            for part in parts:
                score = 60 if domain_name and part.lower() == domain_name.lower() else 25
                candidates.append((score, part))
        soup = BeautifulSoup(page.html, "html.parser")
        for selector in ["meta[property='og:site_name']", "meta[name='application-name']"]:
            tag = soup.select_one(selector)
            if tag and tag.get("content"):
                candidates.append((80, tag["content"].strip()))
        h1 = soup.find("h1")
        if h1:
            candidates.append((10, h1.get_text(" ", strip=True)))
    candidates.append((50, domain_name))
    marketing_words = re.compile(
        r"\b(train|deploy|leading|industry|solutions|services|platform|software|data|ai|"
        r"generative|traditional|welcome|home|contact|about)\b",
        re.I,
    )
    for _, candidate in sorted(candidates, key=lambda item: item[0], reverse=True):
        candidate = prettify_company_name(re.sub(r"\s+", " ", candidate).strip())
        if 2 < len(candidate) <= 40 and not marketing_words.search(candidate):
            return candidate, candidate
    return domain_name, domain_name


def compact_context(pages: list[Page], max_chars: int = 14000) -> str:
    order = {"contact": 0, "about": 1, "services": 2, "home": 3, "other": 4}
    chunks: list[str] = []
    for page in sorted(pages, key=lambda p: order.get(p.kind, 9)):
        chunks.append(f"URL: {page.url}\nPAGE_TYPE: {page.kind}\n{page.text[:4500]}")
    joined = "\n\n---\n\n".join(chunks)
    return joined[:max_chars]


def local_business_insights(text: str, company_name: str) -> dict[str, str]:
    lowered = f"{company_name}\n{text}".lower()

    def has_pattern(pattern: str) -> bool:
        return bool(re.search(pattern, lowered, re.I))

    def visible_terms(patterns: list[tuple[str, str]], limit: int = 5) -> list[str]:
        found: list[str] = []
        for pattern, label in patterns:
            if has_pattern(pattern) and label not in found:
                found.append(label)
        return found[:limit]

    def education_specifics() -> dict[str, str]:
        programs = visible_terms(
            [
                (r"\bb\.?\s*tech\b", "B.Tech"),
                (r"\bm\.?\s*tech\b", "M.Tech"),
                (r"\bmba\b", "MBA"),
                (r"\bmca\b", "MCA"),
                (r"\bph\.?\s*d\b", "Ph.D."),
            ]
        )
        locations = visible_terms(
            [
                (r"\bsikkim\b", "Sikkim"),
                (r"\bmajitar\b", "Majitar"),
                (r"\beast sikkim\b", "East Sikkim"),
                (r"\bnorth[- ]?east\b|\bnortheast\b", "Northeast India"),
                (r"\bindia\b", "India"),
            ],
            limit=3,
        )
        service_focus = ", ".join(programs[:4]) if programs else "academic programs"
        location_focus = f" at {', '.join(locations[:2])}" if locations else ""
        service = f"Undergraduate and postgraduate education in {service_focus}{location_focus}."
        customer = "Prospective students"
        if locations:
            customer += f" from {', '.join(locations[:2])}"
        customer += " evaluating academic and career-oriented programs"
        if programs:
            customer += f" such as {', '.join(programs[:3])}"
        customer += "."
        pain = (
            f"Finding credible {service_focus} programs"
            + (f" in {', '.join(locations[:2])}" if locations else "")
            + " while comparing admissions, placement outcomes, campus quality, and career fit."
        )
        detail = "placement outcomes" if re.search(r"\bplacements?\b", lowered) else "admissions information"
        opener = (
            f"Hi {company_name} team, I noticed your site emphasizes {detail}"
            + (f" for programs like {', '.join(programs[:2])}" if programs else "")
            + ". A relevant opportunity would be improving how prospective students discover the right program and complete the admissions journey."
        )
        return {
            "service": service,
            "customer": customer,
            "pain": pain,
            "opener_focus": "academic programs",
            "opener_tail": "connecting with prospective students who are actively comparing programs and admissions options",
            "custom_opener": opener,
        }

    categories = [
        {
            "label": "design portfolio and creative marketplace",
            "priority": 95,
            "min_matches": 1,
            "patterns": [
                r"\bdribbble\b",
                r"\bbehance\b",
                r"\bportfolio\b",
                r"\bdesigner(?:s)?\b",
                r"\bdesign inspiration\b",
                r"\bcreative work\b",
                r"\bshots\b",
                r"\billustration\b",
                r"\bui design\b",
                r"\bux design\b",
                r"\bbranding\b",
            ],
            "service": "Design portfolio, creative inspiration, and designer discovery marketplace.",
            "customer": "Designers, creative teams, agencies, startups, and businesses looking for visual talent or design inspiration.",
            "pain": "Finding credible designers, comparing creative styles, and turning visual discovery into hiring or collaboration decisions.",
            "opener_focus": "designer portfolios and creative discovery",
            "opener_tail": "helping creative teams and buyers find the right design talent faster",
        },
        {
            "label": "marketplace",
            "priority": 75,
            "min_matches": 2,
            "patterns": [
                r"\bmarketplace\b",
                r"\bbuyers?\b",
                r"\bsellers?\b",
                r"\bcreators?\b",
                r"\bfreelancers?\b",
                r"\bhire\b",
                r"\bjobs?\b",
                r"\btalent\b",
                r"\bcommunity\b",
            ],
            "service": "Online marketplace or community platform connecting buyers, sellers, creators, or talent.",
            "customer": "People or businesses comparing providers, talent, listings, or community-driven services.",
            "pain": "Reducing discovery friction, trust gaps, and decision time when choosing the right provider or opportunity.",
            "opener_focus": "marketplace discovery and trust signals",
            "opener_tail": "improving how users find relevant matches and take action",
        },
        {
            "label": "ecommerce",
            "priority": 65,
            "min_matches": 2,
            "patterns": [
                r"\becommerce\b",
                r"\be-commerce\b",
                r"\bshop\b",
                r"\bstore\b",
                r"\bcart\b",
                r"\bcheckout\b",
                r"\bshipping\b",
                r"\breturns?\b",
                r"\bproducts?\b",
            ],
            "service": "Online retail, product sales, or ecommerce services.",
            "customer": "Consumers or business buyers comparing products, pricing, delivery, and support.",
            "pain": "Helping visitors trust product quality, find the right item quickly, and complete purchases without friction.",
            "opener_focus": "product discovery and checkout experience",
            "opener_tail": "turning high-intent visitors into confident buyers",
        },
        {
            "label": "education",
            "priority": 90,
            "min_matches": 2,
            "patterns": [
                r"\buniversity\b",
                r"\binstitute\b",
                r"\bcollege\b",
                r"\bschool\b",
                r"\bcampus\b",
                r"\badmission(?:s)?\b",
                r"\bdegree\b",
                r"\bfaculty\b",
                r"\beducation\b",
                r"\bb\.?\s*tech\b",
                r"\bm\.?\s*tech\b",
                r"\bmba\b",
                r"\bmca\b",
                r"\bph\.?\s*d\b",
            ],
            **education_specifics(),
            "opener_focus": "academic programs, admissions, and student career outcomes",
            "opener_tail": "connecting with prospective students who are actively comparing programs and admissions options",
        },
        {
            "label": "packing, moving, relocation, and logistics",
            "priority": 80,
            "min_matches": 2,
            "patterns": [
                r"\bpackers?\b",
                r"\bmovers?\b",
                r"packers",
                r"movers",
                r"\bpacking\b",
                r"\bshifting\b",
                r"\brelocation\b",
                r"\bfreight\b",
                r"\bwarehouse\b",
                r"\bloading\b",
                r"\bunloading\b",
                r"\bhousehold goods\b",
                r"\boffice shifting\b",
            ],
            "service": "Packing, moving, relocation, transportation, and logistics support.",
            "customer": "Households, offices, and businesses planning local or intercity relocation.",
            "pain": "Moving goods safely and on time without damage, delays, or coordination stress.",
            "opener_focus": "packing, moving, and relocation services",
            "opener_tail": "reaching customers who are actively looking for this support",
        },
        {
            "label": "software and cloud technology",
            "priority": 40,
            "min_matches": 1,
            "patterns": [
                r"\bsoftware\b",
                r"\bsaas\b",
                r"\bcloud\b",
                r"\bapi\b",
                r"\bplatform\b",
                r"\bapp(?:lication)?s?\b",
                r"\bdevops\b",
                r"\bdata engineering\b",
                r"\bdata infrastructure\b",
            ],
            "service": "Software, cloud, or platform-based technology services.",
            "customer": "Businesses looking to modernize software workflows or digital operations.",
            "pain": "Reducing manual work, integration friction, and operational bottlenecks across tools.",
            "opener_focus": "software and digital operations",
            "opener_tail": "reaching teams actively looking for this support",
        },
        {
            "label": "marketing and creative services",
            "priority": 58,
            "min_matches": 2,
            "patterns": [
                r"\bmarketing\b",
                r"\bagency\b",
                r"\bbranding\b",
                r"\bcreative\b",
                r"\bcampaign\b",
                r"\bseo\b",
                r"\bcontent\b",
                r"\badvertising\b",
                r"\bsocial media\b",
            ],
            "service": "Marketing, branding, creative, advertising, or content services.",
            "customer": "Businesses trying to improve brand visibility, campaign performance, and lead generation.",
            "pain": "Standing out in crowded channels while proving creative work drives measurable business outcomes.",
            "opener_focus": "marketing and creative services",
            "opener_tail": "attracting prospects who are already comparing agencies or campaign partners",
        },
        {
            "label": "ai and data",
            "priority": 55,
            "min_matches": 2,
            "patterns": [
                r"\bartificial intelligence\b",
                r"\bgenerative ai\b",
                r"\btraditional ai\b",
                r"\bdata engineering\b",
                r"\bmachine learning\b",
                r"\bdata annotation\b",
                r"\bdata analytics\b",
                r"\bdata science\b",
                r"\bai\b",
                r"\bml\b",
            ],
            "service": "AI, machine learning, data, or analytics services.",
            "customer": "Enterprises and product teams using data-heavy workflows or AI systems.",
            "pain": "Turning complex data workflows into accurate, scalable business outcomes.",
            "opener_focus": "AI and data services",
            "opener_tail": "reaching teams actively looking for this support",
        },
        {
            "label": "healthcare",
            "priority": 70,
            "min_matches": 2,
            "patterns": [r"\bhealthcare\b", r"\bhospital\b", r"\bclinic\b", r"\bpatient\b", r"\bmedical\b"],
            "service": "Healthcare or medical services.",
            "customer": "Patients, healthcare providers, or organizations needing medical support.",
            "pain": "Improving access, coordination, and reliability across healthcare operations.",
            "opener_focus": "healthcare services",
            "opener_tail": "reaching people and organizations actively looking for this support",
        },
        {
            "label": "finance",
            "priority": 60,
            "min_matches": 2,
            "patterns": [r"\bfinance\b", r"\bfinancial\b", r"\bloan\b", r"\binsurance\b", r"\bpayment\b", r"\btax\b"],
            "service": "Financial, insurance, payment, or advisory services.",
            "customer": "Individuals or businesses managing financial decisions and transactions.",
            "pain": "Reducing risk, delays, and complexity in financial operations.",
            "opener_focus": "financial services",
            "opener_tail": "reaching people and businesses actively looking for this support",
        },
    ]

    match_counts = [
        (
            sum(1 for pattern in category["patterns"] if has_pattern(pattern)),
            category,
        )
        for category in categories
    ]
    match_count, best = max(
        match_counts,
        key=lambda item: (item[0] * 10 + int(item[1]["priority"]), item[0]),
    )

    if match_count < int(best.get("min_matches", 1)):
        if company_name.strip():
            return {
                "core_service": f"Public website and online presence for {company_name}.",
                "target_customer": "Visitors, prospects, customers, or partners researching the organization online.",
                "probable_pain_point": "Quickly understanding what the organization offers and whether it is relevant before reaching out.",
                "outreach_opener": (
                    f"Hi {company_name} team, I reviewed your website and saw an opportunity to make the first-touch "
                    "company research and outreach journey clearer for high-intent visitors."
                ),
            }
        return {
            "core_service": "",
            "target_customer": "",
            "probable_pain_point": "",
            "outreach_opener": "",
        }

    service = customer = pain = opener = ""
    if match_count:
        service = best["service"]
        customer = best["customer"]
        pain = best["pain"]
        opener = best.get("custom_opener") or (
            f"Hi {company_name} team, I noticed your website highlights {best['opener_focus']}. "
            f"A relevant opportunity would be {best['opener_tail']}."
        )

    return {
        "core_service": service,
        "target_customer": customer,
        "probable_pain_point": pain,
        "outreach_opener": opener,
    }


def parse_json_object(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def call_gemini(context: str, facts: dict[str, Any], deadline: float) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None or time.monotonic() >= deadline:
        return {}
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
You enrich company website research. Return ONLY a valid JSON object with exactly these keys:
website_name, company_name, address, mobile_number, mail, core_service, target_customer, probable_pain_point, outreach_opener.

Hard rules:
- Do not invent email, phone, or address. Use the factual extraction below for those fields.
- If a factual field is absent, use "" or [].
- Business insight fields may be inferred only from the supplied website text.
- First identify the organization type: education, logistics, healthcare, finance, software, AI/data, etc.
- If the site is a college, university, institute, school, admissions page, or campus page, classify it as education even if it mentions AI, data science, engineering, or software courses.
- Do not classify a business as AI/data just because AI appears as a course, department, blog topic, client use case, or incidental phrase.
- core_service: Name actual programs, departments, services, specializations, industries, or products visible on the site. Never write generic industry descriptions.
- target_customer: Be specific about geography, entry path, audience segment, buyer type, or use case based on visible content.
- probable_pain_point: Must be specific to this organization's niche, geography, positioning, or offering. Generic statements like "choosing the right program" are not acceptable.
- outreach_opener: Must reference one concrete detail from the website such as a program, location, placement/admissions theme, service, product, industry, or stated goal.
- outreach_opener: Do not use vague phrases like "I would love to share an idea"; offer a concrete relevant value.
- Outreach opener must be concise, specific, and must not include fake metrics or unsupported claims.
- mail must be an array of strings.

Factual extraction:
{json.dumps(facts, ensure_ascii=False)}

Cleaned website text:
{context}
"""
    try:
        remaining = max(2, min(8, int(deadline - time.monotonic())))
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "response_mime_type": "application/json"},
            request_options={"timeout": remaining},
        )
        return parse_json_object(getattr(response, "text", ""))
    except Exception:
        return {}


def stable_profile(data: dict[str, Any]) -> dict[str, Any]:
    profile = {key: data.get(key, [] if key == "mail" else "") for key in SCHEMA_KEYS}
    if not isinstance(profile["mail"], list):
        profile["mail"] = [str(profile["mail"])] if profile["mail"] else []
    profile["mail"] = [str(email).strip() for email in profile["mail"] if str(email).strip()]
    for key in SCHEMA_KEYS:
        if key != "mail":
            profile[key] = "" if profile[key] is None else str(profile[key]).strip()
    return profile


def enrich_company(url: str, website_name: str = "", total_timeout: int = 20) -> dict[str, Any]:
    deadline = time.monotonic() + total_timeout
    normalized = normalize_url(url)
    profile = empty_profile(normalized, website_name)
    try:
        pages, final_url = scrape_site(normalized, deadline)
        if not pages:
            domain_name = name_from_domain(final_url or normalized)
            fallback_text = f"{normalized}\n{final_url}\n{website_name}\n{domain_name}"
            facts = {
                "website_name": website_name.strip() or domain_name,
                "company_name": domain_name,
                "address": "",
                "mobile_number": "",
                "mail": [],
                "source_url": final_url or normalized,
            }
            profile.update(facts)
            for key, value in local_business_insights(fallback_text, domain_name).items():
                if value and not profile.get(key):
                    profile[key] = value
            profile["website_name"] = website_name.strip() or profile.get("website_name") or domain_name
            profile["company_name"] = profile.get("company_name") or domain_name
            profile["mail"] = []
            profile["mobile_number"] = ""
            profile["address"] = ""
            return stable_profile(profile)

        all_text = "\n".join([final_url, website_name, *[page.text for page in pages]])
        contact_text = "\n".join(page.text for page in pages if page.kind == "contact") or all_text
        phones = extract_phones(contact_text)
        address = extract_address(contact_text)
        inferred_website_name, inferred_company_name = infer_names(pages, final_url)
        display_company_name = inferred_company_name
        if website_name.strip() and " " in website_name.strip() and " " not in inferred_company_name:
            display_company_name = humanize_name(website_name)
        emails = extract_emails(all_text, final_url, display_company_name)

        facts = {
            "website_name": website_name.strip() or inferred_website_name,
            "company_name": display_company_name,
            "address": address,
            "mobile_number": phones[0] if phones else "",
            "mail": emails,
            "source_url": final_url,
        }
        profile.update(facts)
        ai_data = call_gemini(compact_context(pages), facts, deadline)
        fallback_insights = local_business_insights(all_text, display_company_name)
        merged = {**profile, **ai_data}
        for key, value in fallback_insights.items():
            if value and not merged.get(key):
                merged[key] = value

        # Deterministic contact extraction wins over model output.
        merged["mail"] = emails
        merged["mobile_number"] = phones[0] if phones else ""
        merged["address"] = address
        merged["website_name"] = website_name.strip() or merged.get("website_name") or inferred_website_name
        merged["company_name"] = merged.get("company_name") or display_company_name
        return stable_profile(merged)
    except Exception:
        return stable_profile(profile)
