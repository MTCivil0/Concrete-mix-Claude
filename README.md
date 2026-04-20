# Concrete Mix Design Claude

AI-assisted concrete mix proportioning based on **ACI 211.1**, powered by Claude (Anthropic).

Accepts your aggregate lab data, exposure conditions, and project context —
returns structured mix proportions, durability flags, SCM compatibility notes,
and a downloadable report.

---

## Project Structure

```
concrete-mix-copilot/
├── app.py                  ← Main Streamlit app (run this)
├── requirements.txt        ← Python dependencies
├── .env.example            ← Copy to .env and add your API key
├── .gitignore
├── README.md
├── src/
│   ├── __init__.py
│   ├── aci211.py           ← All ACI 211.1 lookup tables and calculations
│   ├── claude_client.py    ← Claude API calls and prompt logic
│   ├── schemas.py          ← Data classes for inputs and outputs
│   └── reporting.py        ← Markdown/text report generation
└── examples/
    ├── demo_case_01.md     ← F2 exposure, river gravel, 5% PCC
    └── demo_case_02.md     ← F3 + C2, crushed limestone, fly ash blend
```

---

## Step-by-Step Setup

### Step 1 — Install Python (if not already)

Download Python 3.11 or newer from https://python.org
Verify in terminal: `python --version`

### Step 2 — Get your Anthropic API key

1. Go to https://console.anthropic.com
2. Create an account → API Keys → Create Key
3. Copy the key (starts with `sk-ant-...`)

### Step 3 — Download this project

Either clone with git or download the folder as a ZIP.

```bash
cd Desktop
# if using git:
git clone <your-repo-url>
cd concrete-mix-copilot
```

### Step 4 — Create a virtual environment

```bash
python -m venv venv

# Activate it:
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 5 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 6 — Add your API key

```bash
cp .env.example .env
```

Open `.env` in any text editor and replace the placeholder:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Step 7 — Run the app

```bash
streamlit run app.py
```

Your browser opens automatically at http://localhost:8501

---

## How It Works

1. Fill in your project inputs (exposure class, target f'c, aggregate properties)
2. Enter SCM percentages including PCC if applicable
3. Paste any field notes or project context
4. Click **Run Mix Design Analysis**
5. Review proportions, durability flags, and ACI compliance notes
6. Download the Markdown report

---

## Demo Mode vs Live Mode

| | Demo Mode | Live Mode |
|---|---|---|
| API calls | None | Yes (uses Claude) |
| Cost | Free | ~$0.01–0.05 per analysis |
| Output | Realistic sample | Real AI analysis |

Toggle in the sidebar. Use Demo Mode for testing the workflow.

---

## Notes

- PCC (Precipitated Calcium Carbonate) is modeled as an inert micro-filler.
  Optimal range: 3–8%. At 5%, expect ~+5–9% compressive strength gain
  from particle packing effect (no reactive contribution to hydration).
- All ACI 211.1 lookup tables are embedded in `src/aci211.py`.
- This tool provides preliminary guidance only — not a substitute for
  a licensed structural engineer or certified concrete technologist.
