"""
KCNA Examination Preparatory App
---------------------------------
A Flask + SQLite web app for practicing for the Kubernetes and Cloud
Native Associate (KCNA) certification exam.

Run with:
    python app.py

Then open http://127.0.0.1:8000 in your browser (override with the PORT
environment variable, e.g. PORT=5050 python app.py).
"""
import os
import random
from datetime import datetime, timezone

from flask import Flask, render_template, jsonify, request, abort

import database
from build_bundles import seed_database

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def ensure_seeded():
    from build_bundles import NUM_BUNDLES
    database.init_db()
    bundles = database.get_bundles()
    needs_reseed = (
        not bundles
        or len(bundles) != NUM_BUNDLES
        or not all(database.bundle_has_questions(b["id"]) for b in bundles)
    )
    if needs_reseed:
        seed_database()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    bundles = database.get_bundles()
    # attach best score / attempt count per bundle for a nicer dashboard
    history = database.get_history(limit=1000)
    stats = {}
    for h in history:
        bid = h["bundle_id"]
        stats.setdefault(bid, {"attempts": 0, "best_score": 0, "passed": False})
        stats[bid]["attempts"] += 1
        if h["score"] and h["score"] > stats[bid]["best_score"]:
            stats[bid]["best_score"] = h["score"]
        if h["passed"]:
            stats[bid]["passed"] = True
    for b in bundles:
        b["stats"] = stats.get(b["id"], {"attempts": 0, "best_score": 0, "passed": False})
    return render_template("dashboard.html", bundles=bundles)


@app.route("/bundle/<int:bundle_id>/start")
def start_exam(bundle_id):
    bundle = database.get_bundle(bundle_id)
    if not bundle:
        abort(404)
    questions = database.get_questions_for_bundle(bundle_id)
    if not questions:
        abort(404)

    attempt_id = database.create_attempt(
        bundle_id=bundle_id,
        started_at=now_iso(),
        total_questions=len(questions),
    )

    # Shuffle question order per attempt (nice touch, keeps it fresh),
    # and shuffle option order too, without ever leaking the correct answer.
    rng = random.Random(attempt_id)
    q_order = questions[:]
    rng.shuffle(q_order)

    safe_questions = []
    for q in q_order:
        letters = list(q["options"].keys())
        rng.shuffle(letters)
        shuffled_options = [{"key": k, "text": q["options"][k]} for k in letters]
        safe_questions.append({
            "id": q["id"],
            "question": q["question"],
            "options": shuffled_options,
            "domain": q["domain"],
        })

    return render_template(
        "exam.html",
        bundle=bundle,
        attempt_id=attempt_id,
        questions=safe_questions,
        duration_minutes=bundle["duration_minutes"],
    )


@app.route("/result/<int:attempt_id>")
def result_page(attempt_id):
    attempt = database.get_attempt(attempt_id)
    if not attempt or attempt["status"] != "completed":
        abort(404)
    bundle = database.get_bundle(attempt["bundle_id"])
    import json as _json
    answers = _json.loads(attempt["answers_json"])
    domain_breakdown = _json.loads(attempt["domain_breakdown_json"])
    return render_template(
        "result.html",
        attempt=attempt,
        bundle=bundle,
        answers=answers,
        domain_breakdown=domain_breakdown,
    )


@app.route("/history")
def history_page():
    history = database.get_history(limit=100)
    return render_template("history.html", history=history)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

PASS_SCORE = 850  # out of 1000


@app.route("/api/submit/<int:attempt_id>", methods=["POST"])
def submit_exam(attempt_id):
    attempt = database.get_attempt(attempt_id)
    if not attempt:
        return jsonify({"error": "Attempt not found"}), 404
    if attempt["status"] == "completed":
        return jsonify({"error": "Attempt already submitted", "attempt_id": attempt_id}), 400

    payload = request.get_json(force=True, silent=True) or {}
    submitted_answers = payload.get("answers", {})  # { question_id(str): "A" }
    elapsed_seconds = int(payload.get("elapsed_seconds", 0))

    questions = database.get_questions_for_bundle(attempt["bundle_id"])
    q_by_id = {str(q["id"]): q for q in questions}

    total = len(questions)
    correct_count = 0
    domain_stats = {}
    detailed_answers = []

    for q in questions:
        qid = str(q["id"])
        user_choice = submitted_answers.get(qid)
        is_correct = (user_choice == q["correct"])
        if is_correct:
            correct_count += 1

        d = domain_stats.setdefault(q["domain"], {"correct": 0, "total": 0})
        d["total"] += 1
        if is_correct:
            d["correct"] += 1

        detailed_answers.append({
            "question_id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "correct": q["correct"],
            "user_choice": user_choice,
            "is_correct": is_correct,
            "explanation": q["explanation"],
            "domain": q["domain"],
            "competency": q["competency"],
        })

    score = round((correct_count / total) * 1000) if total else 0
    passed = score >= PASS_SCORE

    database.submit_attempt(
        attempt_id=attempt_id,
        submitted_at=now_iso(),
        time_taken_seconds=elapsed_seconds,
        correct_count=correct_count,
        total_questions=total,
        score=score,
        passed=passed,
        answers=detailed_answers,
        domain_breakdown=domain_stats,
    )

    return jsonify({
        "attempt_id": attempt_id,
        "score": score,
        "passed": passed,
        "correct_count": correct_count,
        "total_questions": total,
        "redirect": f"/result/{attempt_id}",
    })


@app.route("/api/bundles")
def api_bundles():
    return jsonify(database.get_bundles())


if __name__ == "__main__":
    ensure_seeded()
    port = int(os.environ.get("PORT", 8000))
    app.run(debug=True, host="0.0.0.0", port=port)
