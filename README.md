# KCNA Exam Prep

A self-contained web app for practicing the Kubernetes and Cloud Native
Associate (KCNA) exam: **12** 60-question bundles, a 70-minute countdown per
attempt, automatic scoring out of 1000, and a full answer review with
explanations.

## Question bank

The bank has **758 questions** in total:

- **350** were extracted from the uploaded `KCNA-exam-prep.pdf` (every
  question, its answer choices, correct answer, explanation, domain, and
  competency tag).
- **408** were newly written to fill out the bank for 12 bundles, covering
  standard, well-established KCNA topics in the same style: direct
  questions, four answer choices, one correct answer, and a short
  explanation. No scraped or copied exam-dump content was used.

All 758 questions are tagged into five domains, matching the official KCNA
curriculum weighting (Kubernetes Fundamentals 46%, Container Orchestration
22%, Cloud Native Architecture 16%, Observability 8%, Application Delivery
8%), with Kubernetes Fundamentals split into two halves and Observability +
Application Delivery merged into one:

| Domain | Weight | Questions per 60-question bundle |
|---|---|---|
| Kubernetes core concepts, architecture, and basic resources | 23% | 14 |
| Advanced Kubernetes objects, storage, and networking | 23% | 14 |
| Container Orchestration | 22% | 13 |
| Cloud Native Architecture | 16% | 10 |
| Observability & Delivery | 16% | 9 |

Each of the 12 bundles draws 720 questions total from the 758-question pool
with **zero repeats across bundles** — every bundle is a distinct, weighted
60-question exam.

## Requirements

- Python 3.9+
- No other services required — data is stored locally in a SQLite file
  (`kcna.db`), created automatically on first run.


## Project Structure

```
kcna-prep-app/
├── app.py                      # Flask routes: pages + JSON scoring API      (214 lines)
├── database.py                 # SQLite schema + data access helpers        (207 lines)
├── build_bundles.py             # Builds 12 weighted bundles from the bank   (115 lines)
├── requirements.txt             # Flask, gunicorn
├── start.sh / stop.sh           # Run/stop the app detached in the background
├── kcna.db                      # SQLite database (auto-created/reseeded)
│
├── data/
│   └── questions_bank.json      # 758 questions: question, options, correct
│                                 # answer, explanation, domain, competency
│
├── templates/                   # Jinja2 HTML
│   ├── base.html                 # Shared layout, header/nav
│   ├── dashboard.html            # 12-bundle grid
│   ├── exam.html                 # Timed exam shell
│   ├── result.html               # Score, domain breakdown, review
│   └── history.html              # Past attempts table
│
├── static/
│   ├── css/style.css             # Design system (711 lines)
│   └── js/exam.js                # Timer, navigation, submission (187 lines)
│
└── README.md
```


## Setup

```bash
cd kcna-prep-app
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser. This runs in the
foreground — closing the terminal stops the app.

### Running detached (in the background)

Use the included helper scripts:

```bash
./start.sh   # starts the app in the background, safe to close your terminal
./stop.sh    # stops it
```

`start.sh` seeds the database if needed, then launches with `gunicorn`
(production WSGI server, 2 workers) if it's installed, falling back to
Flask's own dev server otherwise. It writes the process id to `app.pid` and
logs to `app.log` (`tail -f app.log` to watch them). `stop.sh` reads
`app.pid` and shuts it down cleanly.

To run detached without the scripts:

```bash
# with gunicorn (recommended)
gunicorn -w 2 -b 0.0.0.0:5000 --daemon --pid app.pid app:app

# or with plain nohup
nohup python3 app.py > app.log 2>&1 &
```

The database and its 5 bundles (300 questions) are built automatically the
first time you run `app.py`. If you ever want to reset all bundles and wipe
every recorded attempt, stop the app and run:

```bash
rm kcna.db
python build_bundles.py
```

## How it works

- **Dashboard** (`/`) — lists the 5 bundles with your best score and pass/fail
  status on each.
- **Exam** (`/bundle/<id>/start`) — starts a timed attempt. Question order and
  answer-choice order are shuffled per attempt so retakes stay meaningful. A
  question navigator on the side lets you jump between questions and shows
  which ones you've answered. The exam auto-submits when the 70-minute clock
  runs out.
- **Scoring** — on submit, the server (never the browser) checks your answers
  against the stored correct answers and computes a score out of 1000
  (`correct_count / total * 1000`, rounded). **850/1000 is a pass** — exactly
  51 of 60 questions correct.
- **Results** (`/result/<attempt_id>`) — pass/fail banner, score breakdown by
  KCNA domain, and a filterable, question-by-question review with the correct
  answer, your answer, and the original explanation for every question.
- **History** (`/history`) — every completed attempt across all bundles.

## Project structure

```
kcna_app/
  app.py              Flask routes (pages + JSON API)
  database.py         SQLite schema and data access helpers
  build_bundles.py    Builds the 12 weighted bundles from the question bank
  data/
    questions_bank.json  758 questions (question, options, correct answer,
                          explanation, domain, competency)
  templates/           Jinja2 HTML templates
  static/
    css/style.css      Design system
    js/exam.js          Timer, navigation, and submission logic
  start.sh / stop.sh   Run the app detached in the background
  kcna.db              SQLite database (created on first run)
```

## Notes

- Passing score of 850/1000 corresponds exactly to 51/60 correct answers.
- If you edit `build_bundles.py`'s `NUM_BUNDLES` or `DOMAIN_PLAN`, delete
  `kcna.db` and restart the app (or run `python build_bundles.py`) to
  reseed — `app.py` also auto-detects a bundle-count mismatch and reseeds
  automatically on startup.
- Each domain's question pool must have at least `per_bundle_count ×
  NUM_BUNDLES` questions for `build_bundles.py` to succeed without repeats;
  it will raise a clear error if a domain runs short.
