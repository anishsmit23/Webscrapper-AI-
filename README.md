<div align="center">

<br/>

```
  ✦  I N T E L L I E N R I C H  ✦
```

### *Turn any company website into actionable intelligence — in seconds.*

<br/>

[![Python](https://img.shields.io/badge/Python_3.12-f0ede8?style=flat-square&logo=python&logoColor=0d0d0d)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-f0ede8?style=flat-square&logo=fastapi&logoColor=0d0d0d)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini_1.5_Flash-f0ede8?style=flat-square&logo=google&logoColor=0d0d0d)](https://ai.google.dev/)
[![Render](https://img.shields.io/badge/Deployed_on_Render-f0ede8?style=flat-square&logo=render&logoColor=0d0d0d)](https://render.com/)

<br/>

---

</div>

<br/>

## ✦ &nbsp; What Does This Do?

You paste a company's website link. The system does the rest.

It visits the website, reads the important pages, pulls out real contact details, and uses AI to figure out what the company actually does, who they sell to, and how you could reach out to them — all in one clean, structured result.

No manual research. No copy-pasting. No guessing.

<br/>

---

<br/>

## ✦ &nbsp; What You Get Back

For every website you submit, the system hands you a complete profile:

<br/>

| &nbsp;&nbsp;Field&nbsp;&nbsp; | &nbsp;&nbsp;What It Tells You&nbsp;&nbsp; |
|:---|:---|
| 🏢 &nbsp; **Website Name** | The name you gave it, or what the site calls itself |
| 🔤 &nbsp; **Company Name** | The official company name from the website |
| 📍 &nbsp; **Address** | Physical address, if publicly listed |
| 📞 &nbsp; **Phone Number** | Contact number found on the site |
| 📧 &nbsp; **Email(s)** | All publicly visible email addresses |
| 💼 &nbsp; **Core Service** | What they actually do — specific, not vague |
| 🎯 &nbsp; **Target Customer** | Who they're selling to |
| 💡 &nbsp; **Pain Point** | The problem their customers are trying to solve |
| ✉️ &nbsp; **Outreach Opener** | A ready-to-use first message tailored to them |

<br/>

---

<br/>

## ✦ &nbsp; How It Works

> *No magic. Just smart, careful steps.*

<br/>

```
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │   1. You submit a URL                                   │
  │        ↓                                                │
  │   2. System finds the right pages to read               │
  │      ( About · Contact · Services · Products )          │
  │        ↓                                                │
  │   3. Reads and cleans the text                          │
  │      ( removes menus, footers, cookie banners )         │
  │        ↓                                                │
  │   4. Extracts emails & phone numbers directly           │
  │      ( no AI involved — facts only )                    │
  │        ↓                                                │
  │   5. Sends cleaned text to Gemini AI                    │
  │      ( for business insight fields only )               │
  │        ↓                                                │
  │   6. Returns a clean, structured profile                │
  │        ↓                                                │
  │   7. Saves it so you can view it anytime                │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
```

<br/>

The key design decision: **AI only reasons. It never invents facts.**
Contact details come directly from the website text. If something isn't there, the system returns an empty field — not a guess.

<br/>

---

<br/>

## ✦ &nbsp; Project Layout

```
intellienrich/
│
├── app/
│   ├── main.py              ← Web server & API routes
│   ├── enrichment.py        ← Scraping, cleaning & AI logic
│   └── db.py                ← Saves results to database
│
├── static/
│   └── index.html           ← The web interface
│
├── data/
│   └── seed_companies.json  ← Pre-loaded sample results
│
├── colab/
│   └── company_enrichment_colab.ipynb   ← Standalone notebook
│
├── requirements.txt
├── render.yaml
└── README.md                ← You are here ✦
```

<br/>

---

<br/>

## ✦ &nbsp; Run It Yourself

> *Takes about 3 minutes from scratch.*

<br/>

**Step 1 — Set up a clean environment**

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac / Linux
```

<br/>

**Step 2 — Install what it needs**

```bash
pip install -r requirements.txt
```

<br/>

**Step 3 — Add your Gemini API key**

```bash
copy .env.example .env
```

Open `.env` and fill in:

```env
GEMINI_API_KEY=your_key_here
```

<br/>

**Step 4 — Start the app**

```bash
uvicorn app.main:app --reload
```

Then open your browser at **http://127.0.0.1:8000** ✦

<br/>

---

<br/>

## ✦ &nbsp; API at a Glance

<br/>

**Check if the server is running**

```http
GET /health
```
```json
{ "status": "ok" }
```

<br/>

**Enrich a company**

```http
POST /enrich
```

Send:
```json
{
  "website_name": "Stripe",
  "url": "https://stripe.com"
}
```

Get back:
```json
{
  "website_name": "Stripe",
  "company_name": "Stripe, Inc.",
  "address": "",
  "mobile_number": "",
  "mail": ["support@stripe.com"],
  "core_service": "Payment infrastructure for internet businesses",
  "target_customer": "Startups and enterprises processing online payments",
  "probable_pain_point": "Complex payment integration slowing down product launches",
  "outreach_opener": "Hi Stripe team — your developer-first onboarding stood out. I'd love to share how similar fintech platforms have reduced integration drop-off for their enterprise clients."
}
```

<br/>

**See all saved results**

```http
GET /results
```

Returns every enriched company, newest first.

<br/>

---

<br/>

## ✦ &nbsp; Deploy to Render (Free)

The repo includes a ready-to-go `render.yaml`. Here's all you need to do:

<br/>

```
  1.  Push your code to a GitHub repository

  2.  Go to render.com → New → Web Service

  3.  Connect your GitHub repo

  4.  Render reads render.yaml automatically:
        Build:  pip install -r requirements.txt
        Start:  uvicorn app.main:app --host 0.0.0.0 --port $PORT

  5.  Add one environment variable in Render dashboard:
        GEMINI_API_KEY = your_key_here

  6.  Hit Deploy — you get a public URL in ~2 minutes ✦
```

<br/>

> 💡 &nbsp; **Free tier note:** The server sleeps after 15 minutes of no activity. The first request after sleep takes about 30 seconds to wake up. Completely normal — just a free-tier thing.

<br/>

---

<br/>

## ✦ &nbsp; Google Colab Notebook

For the research pipeline submission, use the self-contained notebook at:

```
colab/company_enrichment_colab.ipynb
```

A judge can open it, run all cells top to bottom, paste in a list of URLs when asked, and receive a perfectly formatted JSON result — no setup, no extra files needed.

**Input format:**
```json
["https://stripe.com", "https://notion.so", "https://zapier.com"]
```

**Before sharing:** make sure your Gemini key is set inside the notebook:
```python
os.environ["GEMINI_API_KEY"] = "your-key-here"
```

Then share with **Anyone with the link** on Google Colab.

<br/>

---

<br/>

## ✦ &nbsp; Good to Know

<br/>

```
  ⏱  Enrichment takes 15–30 seconds per URL
     ( live scraping + AI processing — this is expected )

  🚫  Some websites actively block automated visitors
     ( the system returns a safe partial result, never crashes )

  🖼  Content inside images or behind login walls can't be read
     ( only publicly visible text is used )

  ✉️  Contact details are never invented
     ( if an email isn't on the site, it won't appear in results )
```

<br/>

---

<br/>

## ✦ &nbsp; Submission Checklist

- [x] Backend API
- [x] Web interface
- [x] SQLite result storage
- [x] Render deployment config
- [x] Python version pinned to 3.12
- [x] `.env.example` included
- [x] Google Colab notebook
- [x] Required JSON schema
- [x] `/results` endpoint
- [x] Pre-loaded sample companies

<br/>

---

<br/>

<div align="center">

*Built for reliable enrichment, clean demos, and fast evaluation.*

```
  ✦
```

</div>
#   W e b s c r a p p e r - A I -  
 