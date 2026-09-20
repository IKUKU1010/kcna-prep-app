(function () {
  const root = document.getElementById("exam-root");
  const attemptId = root.dataset.attemptId;
  const durationMinutes = parseFloat(root.dataset.durationMinutes);
  const questions = JSON.parse(document.getElementById("questions-data").textContent);

  const state = {
    current: 0,
    answers: {}, // question_id -> letter
    secondsLeft: Math.round(durationMinutes * 60),
    startTs: Date.now(),
    submitted: false,
  };

  const els = {
    body: document.getElementById("question-body"),
    timer: document.getElementById("timer"),
    progressFill: document.getElementById("progress-fill"),
    progressLabel: document.getElementById("progress-label"),
    qgrid: document.getElementById("qgrid"),
    btnPrev: document.getElementById("btn-prev"),
    btnNext: document.getElementById("btn-next"),
    btnSubmit: document.getElementById("btn-submit"),
    btnSubmitSide: document.getElementById("btn-submit-side"),
    modal: document.getElementById("submit-modal"),
    modalTitle: document.getElementById("modal-title"),
    modalBody: document.getElementById("modal-body"),
    modalCancel: document.getElementById("modal-cancel"),
    modalConfirm: document.getElementById("modal-confirm"),
  };

  function fmtTime(totalSeconds) {
    const s = Math.max(0, totalSeconds);
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  }

  function renderQuestion() {
    const q = questions[state.current];
    const selected = state.answers[q.id];
    els.body.innerHTML = `
      <div class="domain-tag">${escapeHtml(q.domain)}</div>
      <div class="qnum">Question ${state.current + 1} of ${questions.length}</div>
      <h2>${escapeHtml(q.question)}</h2>
      <div class="options" role="radiogroup" aria-label="Answer options">
        ${q.options.map(opt => `
          <label class="option-row ${selected === opt.key ? "selected" : ""}" data-key="${opt.key}">
            <input type="radio" name="q_${q.id}" value="${opt.key}" ${selected === opt.key ? "checked" : ""}>
            <span class="letter">${opt.key}</span>
            <span class="text">${escapeHtml(opt.text)}</span>
          </label>
        `).join("")}
      </div>
    `;

    els.body.querySelectorAll(".option-row").forEach(row => {
      row.addEventListener("click", () => {
        state.answers[q.id] = row.dataset.key;
        renderQuestion();
        renderGrid();
      });
    });

    els.progressLabel.textContent = `Question ${state.current + 1} of ${questions.length}`;
    els.progressFill.style.width = `${((state.current + 1) / questions.length) * 100}%`;

    els.btnPrev.disabled = state.current === 0;
    const isLast = state.current === questions.length - 1;
    els.btnNext.style.display = isLast ? "none" : "inline-flex";
    els.btnSubmit.style.display = isLast ? "inline-flex" : "none";
  }

  function renderGrid() {
    els.qgrid.innerHTML = questions.map((q, i) => {
      const answered = state.answers[q.id] !== undefined;
      const isCurrent = i === state.current;
      return `<button class="${answered ? "answered" : ""} ${isCurrent ? "current" : ""}" data-idx="${i}" title="Question ${i + 1}">${i + 1}</button>`;
    }).join("");
    els.qgrid.querySelectorAll("button").forEach(btn => {
      btn.addEventListener("click", () => {
        state.current = parseInt(btn.dataset.idx, 10);
        renderQuestion();
        renderGrid();
      });
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  els.btnPrev.addEventListener("click", () => {
    if (state.current > 0) {
      state.current -= 1;
      renderQuestion();
      renderGrid();
    }
  });

  els.btnNext.addEventListener("click", () => {
    if (state.current < questions.length - 1) {
      state.current += 1;
      renderQuestion();
      renderGrid();
    }
  });

  function openSubmitModal(auto) {
    const answeredCount = Object.keys(state.answers).length;
    const unanswered = questions.length - answeredCount;
    if (auto) {
      els.modalTitle.textContent = "Time's up";
      els.modalBody.textContent = `Your 70 minutes are up. Submitting now with ${answeredCount} of ${questions.length} questions answered.`;
      els.modalCancel.style.display = "none";
    } else {
      els.modalTitle.textContent = "Submit this exam?";
      els.modalBody.textContent = unanswered > 0
        ? `You still have ${unanswered} unanswered question${unanswered === 1 ? "" : "s"}. Submitting now will score those as incorrect.`
        : "You've answered all questions. Once submitted you can't change your answers.";
      els.modalCancel.style.display = "inline-flex";
    }
    els.modal.classList.add("open");
  }

  [els.btnSubmit, els.btnSubmitSide].forEach(b => b.addEventListener("click", () => openSubmitModal(false)));
  els.modalCancel.addEventListener("click", () => els.modal.classList.remove("open"));
  els.modalConfirm.addEventListener("click", () => submitExam());

  async function submitExam() {
    if (state.submitted) return;
    state.submitted = true;
    clearInterval(timerHandle);
    els.modalConfirm.textContent = "Submitting…";
    els.modalConfirm.disabled = true;

    const elapsed = Math.round(durationMinutes * 60) - state.secondsLeft;
    try {
      const res = await fetch(`/api/submit/${attemptId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers: state.answers, elapsed_seconds: elapsed }),
      });
      const data = await res.json();
      if (data.redirect) {
        window.location.href = data.redirect;
      } else {
        alert("Something went wrong submitting your exam. Please try again.");
        state.submitted = false;
        els.modalConfirm.textContent = "Submit now";
        els.modalConfirm.disabled = false;
      }
    } catch (e) {
      alert("Network error while submitting. Please check your connection and try again.");
      state.submitted = false;
      els.modalConfirm.textContent = "Submit now";
      els.modalConfirm.disabled = false;
    }
  }

  function tick() {
    state.secondsLeft -= 1;
    els.timer.textContent = fmtTime(state.secondsLeft);
    els.timer.classList.toggle("warn", state.secondsLeft <= 300 && state.secondsLeft > 60);
    els.timer.classList.toggle("danger", state.secondsLeft <= 60);
    if (state.secondsLeft <= 0) {
      clearInterval(timerHandle);
      openSubmitModal(true);
      submitExam();
    }
  }

  els.timer.textContent = fmtTime(state.secondsLeft);
  const timerHandle = setInterval(tick, 1000);

  window.addEventListener("beforeunload", (e) => {
    if (!state.submitted) {
      e.preventDefault();
      e.returnValue = "";
    }
  });

  renderQuestion();
  renderGrid();
})();
