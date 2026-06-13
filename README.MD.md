<div align="center">

# 🧠 IntelliEnrich

### Turn any company website into actionable intelligence, in seconds.

[![Python](https://img.shields.io/badge/Python_3.12-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini_1.5_Flash-8e75ff?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Render](https://img.shields.io/badge/Deployed_on_Render-46e3b7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)

<br>

🌐 **Live Demo:** [https://ai-company-enrichment-49m7.onrender.com](https://ai-company-enrichment-49m7.onrender.com)

<br>

</div>

---

## ✨ What Does This Do?

You paste a company website link. The system does the rest.

It visits the website, reads the important pages, pulls out real contact details, and uses AI to figure out what the company does, who they sell to, and how you could reach out to them.

**No manual research. No copy-pasting. No guessing.**

---

## 📋 What You Get Back

For every website you submit, the system returns a complete profile.

| Field | What It Tells You |
|:---|:---|
| 🏷️ Website Name | The name you gave it, or what the site calls itself |
| 🏢 Company Name | The official company name from the website |
| 📍 Address | Physical address, if publicly listed |
| 📞 Phone Number | Contact number found on the site |
| ✉️ Emails | All publicly visible email addresses |
| 🎯 Core Service | What they actually do, specific not vague |
| 👤 Target Customer | Who they are selling to |
| 😫 Pain Point | The problem their customers are trying to solve |
| 💬 Outreach Opener | A ready-to-use first message tailored to them |

---

## ⚙️ How It Works

No magic. Just smart careful steps.

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Submit URL │──▶│ Find Pages  │───▶│ Clean Text  │───▶│ Extract     │
│             │    │ About,      │    │ Remove      │    │ Emails &    │
│             │    │ Contact,    │    │ Menus,      │    │ Phone       │
│             │    │ Services    │    │ Footers     │    │ Numbers     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                              │
                                                              ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  View &     │◄───│    Save     │◄───│  Return     │◄───│  Gemini AI  │
│  Export     │    │  Profile    │    │  Result     │    │  Analysis   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

1. ✅ You submit a URL
2. 🔍 System finds the right pages: About, Contact, Services, Products
3. 🧹 Reads and cleans the text, removing menus, footers, and cookie banners
4. 📇 Extracts emails and phone numbers directly without using AI
5. 🤖 Sends cleaned text to Gemini AI for business insight fields only
6. 📊 Returns a clean structured profile
7. 💾 Saves it so you can view it anytime

> 🔑 **The key design decision:** AI only reasons. It never invents facts. If something is not on the site, the system returns an empty field, not a guess.

---

## 🚀 Quick Start

### Step 1 — Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Add your Gemini API key

Create `.env` from the example file and set:

```env
GEMINI_API_KEY=your_key_here
```

### Step 4 — Start the app

```bash
uvicorn app.main:app --reload
```

Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📡 API Reference

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Check if the server is running |
| `POST` | `/enrich` | Enrich a company by URL |
| `GET` | `/results` | Returns all saved companies, newest first |

### Example: Enrich a Company

```bash
curl -X POST "https://ai-company-enrichment-49m7.onrender.com/enrich" \
  -H "Content-Type: application/json" \
  -d '{"website_name": "Stripe", "url": "https://stripe.com"}'
```

---

## 🌍 Deploy to Render for Free

1. Push your code to GitHub
2. Go to [render.com](https://render.com), click **New**, then **Web Service**
3. Connect your GitHub repo
4. **Build command:** `pip install -r requirements.txt`
5. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variable: `GEMINI_API_KEY = your_key_here`
7. Click **Deploy** and get a public URL in about 2 minutes

> 💡 **Note:** Free tier sleeps after 15 minutes. First request after sleep takes about 30 seconds.

---

## 📁 Project Layout

```
intellienrich/
├──  app/
│   ├── main.py              # FastAPI entry point
│   ├── enrichment.py        # Scraping & AI logic
│   └── db.py                # SQLite database layer
├──  static/
│   └── index.html           # Web dashboard UI
├──  data/
│   └── seed_companies.json  # Pre-loaded sample data
├──  colab/
│   └── company_enrichment_colab.ipynb  # Google Colab notebook
├── requirements.txt         # Python dependencies
├── render.yaml              # Render deployment config
├── .env.example             # Environment variable template
└── README.md                # This file
```

---

## 📓 Google Colab Notebook

**Location:** `colab/company_enrichment_colab.ipynb`

Open it, run all cells, paste in URLs when prompted, and receive formatted JSON output.

> 🔐 Before sharing, add your key inside the notebook and share with **Anyone with the link**.

---

## ⚠️ Good to Know

| | |
|:---|:---|
| ⏱️ | Enrichment takes **15 to 30 seconds** per URL |
| 🛡️ | Some websites block scrapers. The system returns a **partial result** and never crashes |
| 🔒 | Content behind logins or inside images **cannot be read** |
| ✋ | Contact details are **never invented** — if not found, the field stays empty |

---

## ✅ Submission Checklist

- [x] Backend API (FastAPI)
- [x] Web interface (HTML Dashboard)
- [x] SQLite storage
- [x] Render deployment config
- [x] Python 3.12 pinned
- [x] `.env.example` included
- [x] Google Colab notebook
- [x] Required JSON schema
- [x] `/results` endpoint
- [x] Pre-loaded sample companies

---

<div align="center">

Built for reliable enrichment, clean demos, and fast evaluation.

**[🌐 Live Demo](https://ai-company-enrichment-49m7.onrender.com)** · **[📁 GitHub](https://github.com/anishsmit23)** · **[📧 Contact](mailto:anishhyd995@gmail.com)**

</div>
