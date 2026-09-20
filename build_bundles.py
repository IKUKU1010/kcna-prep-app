"""
Builds 12 exam bundles (60 questions each) from data/questions_bank.json,
weighted to match official KCNA domain proportions, and seeds them into
SQLite.

KCNA domain weights (Linux Foundation curriculum), 46% for "Kubernetes
Fundamentals" split here into two equal halves, and Observability (8%) +
Application Delivery (8%) combined into one 16% domain:

    Kubernetes core concepts, architecture, and basic resources   23%
    Advanced Kubernetes objects, storage, and networking          23%
    Container Orchestration                                       22%
    Cloud Native Architecture                                     16%
    Observability & Delivery                                      16%

Run this once before starting the app (app.py also auto-runs it if the
DB is empty or the bundle count doesn't match):

    python build_bundles.py
"""
import json
import os
import random

import database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BANK_PATH = os.path.join(BASE_DIR, "data", "questions_bank.json")

NUM_BUNDLES = 12
QUESTIONS_PER_BUNDLE = 60
DURATION_MINUTES = 70
SEED = 42  # deterministic shuffling so re-running gives the same bundles

# Domain -> number of questions per 60-question bundle (weights sum to 100%,
# per-bundle counts sum to exactly 60).
DOMAIN_PLAN = [
    ("Kubernetes core concepts, architecture, and basic resources", 14),
    ("Advanced Kubernetes objects, storage, and networking", 14),
    ("Container Orchestration", 13),
    ("Cloud Native Architecture", 10),
    ("Observability & Delivery", 9),
]
assert sum(n for _, n in DOMAIN_PLAN) == QUESTIONS_PER_BUNDLE

BUNDLE_META = [(f"KCNA Practice Exam {i}",
                "Full-length practice exam weighted across all five KCNA domains.")
               for i in range(1, NUM_BUNDLES + 1)]


def load_bank():
    with open(BANK_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_bundles(questions):
    rng = random.Random(SEED)

    by_domain = {}
    for q in questions:
        by_domain.setdefault(q["domain"], []).append(q)

    for domain in by_domain:
        rng.shuffle(by_domain[domain])

    bundles = [[] for _ in range(NUM_BUNDLES)]

    for domain, per_bundle in DOMAIN_PLAN:
        pool = by_domain.get(domain, [])
        needed = per_bundle * NUM_BUNDLES
        if len(pool) < needed:
            raise ValueError(
                f"Not enough questions in domain '{domain}': "
                f"have {len(pool)}, need {needed} for {NUM_BUNDLES} bundles "
                f"of {per_bundle} each."
            )
        idx = 0
        for b in range(NUM_BUNDLES):
            bundles[b].extend(pool[idx: idx + per_bundle])
            idx += per_bundle

    for b in range(NUM_BUNDLES):
        rng.shuffle(bundles[b])
        assert len(bundles[b]) == QUESTIONS_PER_BUNDLE, len(bundles[b])

    return bundles


def seed_database():
    database.init_db()
    questions = load_bank()
    bundles = build_bundles(questions)

    for i, (name, desc) in enumerate(BUNDLE_META, start=1):
        database.upsert_bundle(i, name, desc, QUESTIONS_PER_BUNDLE, DURATION_MINUTES)
        database.clear_questions_for_bundle(i)
        bundle_questions = bundles[i - 1]
        for pos, q in enumerate(bundle_questions, start=1):
            database.insert_question(
                bundle_id=i,
                position=pos,
                question=q["question"],
                options=q["options"],
                correct=q["correct"],
                explanation=q["explanation"],
                domain=q["domain"],
                competency=q["competency"],
            )
        print(f"Seeded bundle {i} ({name}) with {len(bundle_questions)} questions.")

    database.prune_bundles(NUM_BUNDLES)


if __name__ == "__main__":
    seed_database()
