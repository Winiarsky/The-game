const screenMenu = document.getElementById("screen-menu");
const screenGame = document.getElementById("screen-game");
const logList = document.getElementById("log-list");
const heroesList = document.getElementById("heroes-list");
const initiativeList = document.getElementById("initiative-list");

let currentScenario = null;
let eventSource = null;
const renderedPrompts = new Set();
const heroes = new Map();
let promptQueue = [];
let activePrompt = null;
let currentChoices = [];
let selectedChoiceIndex = -1;
let choiceMeta = [];
let digitBuffer = "";
let digitTimer = null;
const DIGIT_BUFFER_MS = 600;
const modal = document.getElementById("prompt-modal");
const modalTitle = document.getElementById("modal-title");
const modalText = document.getElementById("modal-text");
const modalChoices = document.getElementById("modal-choices");
const modalDesc = document.getElementById("modal-desc");
const modalForm = document.getElementById("modal-form");
const modalAnswer = document.getElementById("modal-answer");
const pathToast = document.getElementById("path-toast");
let activePathId = null;
let initiativeState = { order: [], activeId: null, round: 1 };

function showMenu() {
    screenMenu.classList.remove("hidden");
    screenGame.classList.add("hidden");
}

function showGame() {
    screenMenu.classList.add("hidden");
    screenGame.classList.remove("hidden");
}

function addLogEntry(text, meta) {
    const item = document.createElement("li");
    item.className = "log-item";
    item.innerHTML = `
        <div>${text}</div>
        <div class="meta">${meta || ""}</div>
    `;
    logList.prepend(item);
    // limit log length
    while (logList.children.length > 60) {
        logList.removeChild(logList.lastChild);
    }
}

function renderPrompt(prompt) {
    if (renderedPrompts.has(prompt.id)) return;
    renderedPrompts.add(prompt.id);
    promptQueue.push(prompt);
    processPromptQueue();
}

function handleEvent(event) {
    const type = event.type;
    const payload = event.payload || {};
    const timestamp = new Date(event.ts * 1000 || Date.now());
    const meta = timestamp.toLocaleTimeString();
    // gdy docierają zdarzenia, przełącz na ekran gry (jeśli jeszcze nie)
    showGame();

    if (type === "prompt") {
        renderPrompt(payload);
        addLogEntry(`Nowy rzut: ${payload.prompt}`, meta);
        return;
    }
    if (type === "info") {
        renderPrompt({
            id: `info-${Date.now()}`,
            prompt: payload.text || payload.message || "Informacja",
            kind: "info",
            choices: [],
            source: payload.source || "",
        });
        addLogEntry(payload.text || payload.message || "Info", meta);
        return;
    }
    if (type === "prompt_answered") {
        addLogEntry(`Rzut rozstrzygnięty (${payload.prompt || ""}): ${payload.answer}`, meta);
        if (activePrompt && String(activePrompt.id) === String(payload.id)) {
            closePrompt();
        }
        return;
    }
    if (type === "hero") {
        const id = payload.name || payload.object_id || "hero";
        heroes.set(id, {
            name: payload.name || id,
            statuses: payload.statuses || [],
            note: payload.note,
            wounds: payload.wounds,
            active: true,
            initiative: payload.initiative,
        });
        renderHeroes();
        addLogEntry(`Aktualny bohater: ${payload.name || ""}`, meta);
        return;
    }
    if (type === "path_preview") {
        showPathInfo(payload);
        return;
    }
    if (type === "path_clear") {
        clearPathInfo(payload && payload.id);
        return;
    }
    if (type === "initiative") {
        initiativeState = {
            order: payload.order || [],
            activeId: payload.active_id || payload.activeId || null,
            round: payload.round || 1,
        };
        renderInitiative();
        return;
    }
    // domyślnie traktujemy jako log
    addLogEntry(payload.message || type, meta);
}

function connectStream() {
    if (eventSource) {
        eventSource.close();
    }
    eventSource = new EventSource("/stream");
    eventSource.onmessage = (evt) => {
        try {
            const data = JSON.parse(evt.data);
            handleEvent(data);
        } catch (err) {
            console.error("Błąd parsowania zdarzenia", err);
        }
    };
    eventSource.onerror = (err) => {
        console.warn("Stream error, ponawiam za chwilę", err);
        setTimeout(connectStream, 1200);
    };
}

async function fetchPendingPrompts() {
    try {
        const resp = await fetch("/api/prompts");
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.prompts) return;
        const pending = data.prompts.filter((p) => p.status === "pending");
        if (pending.length) {
            showGame();
            pending.forEach((p) => renderPrompt(p));
        }
    } catch (err) {
        console.warn("Nie udało się pobrać promptów:", err);
    }
}

// --- UI actions ---

document.getElementById("btn-new-game").addEventListener("click", showMenu);
document.getElementById("btn-quit").addEventListener("click", () => {
    window.close();
});

document.querySelectorAll(".scenario-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        currentScenario = btn.dataset.scenario;
        addLogEntry(`Uruchomiono scenariusz: ${currentScenario}`, new Date().toLocaleTimeString());
        showGame();
    });
});

// start in menu and connect SSE
showMenu();
connectStream();
fetchPendingPrompts();
setInterval(fetchPendingPrompts, 2000);

// --- Prompt modal logic ---

modalForm.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    if (!activePrompt) return;
    const raw = modalAnswer.value.trim();
    if (activePrompt.kind === "info") {
        closePrompt();
        return;
    }
    let answer = raw;
    if (!answer && currentChoices.length > 0 && selectedChoiceIndex >= 0) {
        answer = currentChoices[selectedChoiceIndex];
    }
    if (!answer) return;
    try {
        await fetch(`/api/prompts/${activePrompt.id}/response`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer }),
        });
        modalAnswer.value = "";
        closePrompt();
    } catch (err) {
        console.error(err);
    }
});

document.addEventListener("keydown", (evt) => {
    if (modal.classList.contains("hidden") || !activePrompt) return;
    if (activePrompt.kind === "info") {
        if (evt.key === "Enter") {
            evt.preventDefault();
            closePrompt();
        }
        return;
    }
    if (currentChoices.length > 0) {
        if (/^[0-9]$/.test(evt.key)) {
            evt.preventDefault();
            digitBuffer += evt.key;
            if (digitTimer) clearTimeout(digitTimer);
            digitTimer = setTimeout(() => {
                if (digitBuffer) {
                    const num = parseInt(digitBuffer, 10);
                    if (!isNaN(num) && num >= 1 && num <= currentChoices.length) {
                        selectChoice(num - 1);
                    }
                }
                digitBuffer = "";
                digitTimer = null;
            }, DIGIT_BUFFER_MS);

            // gdy lista ma mniej niż 10 opcji lub bufor ma 2+ cyfry – próbuj od razu
            if (digitBuffer.length >= 2 || currentChoices.length < 10) {
                const num = parseInt(digitBuffer, 10);
                if (!isNaN(num) && num >= 1 && num <= currentChoices.length) {
                    selectChoice(num - 1);
                    digitBuffer = "";
                    clearTimeout(digitTimer);
                    digitTimer = null;
                } else if (digitBuffer.length >= 2) {
                    // błędny dwucyfrowy – wyczyść
                    digitBuffer = "";
                }
            }
        }
        // strzałki do nawigacji gdy opcji jest więcej niż cyfry
        if (evt.key === "ArrowDown" || evt.key === "ArrowRight") {
            evt.preventDefault();
            const next = (selectedChoiceIndex + 1) % currentChoices.length;
            selectChoice(next);
        }
        if (evt.key === "ArrowUp" || evt.key === "ArrowLeft") {
            evt.preventDefault();
            const prev = (selectedChoiceIndex - 1 + currentChoices.length) % currentChoices.length;
            selectChoice(prev);
        }
        if (evt.key === "+" || evt.key === "-") {
            const idx = choiceMeta.findIndex((c) => c.key === evt.key);
            if (idx >= 0) {
                evt.preventDefault();
                selectChoice(idx);
            }
        }
        if (evt.key === "Enter") {
            evt.preventDefault();
            modalForm.dispatchEvent(new Event("submit", { cancelable: true }));
        }
    }
});

function openPrompt(prompt) {
    activePrompt = prompt;
    renderedPrompts.add(prompt.id);
    modalTitle.textContent = prompt.prompt || "Akcja";
    modalText.textContent = prompt.source ? `Źródło: ${prompt.source}` : "";
    modalChoices.innerHTML = "";
    const normalized = normalizeChoices(prompt);
    currentChoices = normalized.map((c) => c.raw);
    choiceMeta = normalized;
    selectedChoiceIndex = normalized.length ? 0 : -1;
    normalized.forEach((c, idx) => {
        const pill = document.createElement("div");
        pill.className = "choice-pill";
        pill.textContent = c.label;
        pill.addEventListener("click", () => {
            selectChoice(idx);
        });
        modalChoices.appendChild(pill);
    });
    if (prompt.kind === "info") {
        modalAnswer.value = "";
        modalAnswer.placeholder = "Enter aby zamknąć";
        modalAnswer.required = false;
        modalAnswer.classList.add("input-hidden");
    } else if (normalized.length > 0) {
        modalAnswer.value = normalized[0].raw;
        modalAnswer.classList.add("input-hidden");
        modalAnswer.required = false;
        updateChoiceHighlight();
        updateChoiceDesc();
    } else {
        modalAnswer.placeholder = "Twoja odpowiedź...";
        modalAnswer.required = true;
        modalAnswer.classList.remove("input-hidden");
    }
    modal.classList.remove("hidden");
    if (prompt.kind === "info" || normalized.length === 0) {
        modalAnswer.focus();
    }
}

function closePrompt() {
    activePrompt = null;
    modal.classList.add("hidden");
    processPromptQueue();
}

function processPromptQueue() {
    if (activePrompt) return;
    const next = promptQueue.shift();
    if (!next) return;
    openPrompt(next);
}

function selectChoice(idx) {
    if (idx < 0 || idx >= currentChoices.length) return;
    selectedChoiceIndex = idx;
    modalAnswer.value = currentChoices[idx];
    updateChoiceHighlight();
    updateChoiceDesc();
}

function updateChoiceHighlight() {
    const pills = modalChoices.querySelectorAll(".choice-pill");
    pills.forEach((pill, i) => {
        if (i === selectedChoiceIndex) {
            pill.classList.add("selected");
        } else {
            pill.classList.remove("selected");
        }
    });
}

function updateChoiceDesc() {
    if (selectedChoiceIndex < 0 || selectedChoiceIndex >= choiceMeta.length) {
        modalDesc.textContent = "";
        return;
    }
    modalDesc.textContent = choiceMeta[selectedChoiceIndex].desc || "";
}

function normalizeChoices(prompt) {
    const rawChoices = Array.isArray(prompt.choices) ? prompt.choices : [];
    const cardMap = {
        ACCEPT: "+",
        DECLINE: "-",
        move: "1",
        interact: "2",
        seek: "3",
        stealth: "4",
        test_attack: "5",
    };
    return rawChoices.map((raw) => {
        const norm = String(raw).trim();
        let key = "";
        let head = norm;
        // prefiks przed ":" traktuj jako key (np. "1: Otwórz")
        if (norm.includes(":")) {
            const [pref, ...rest] = norm.split(":");
            if (pref.trim().length === 1) {
                key = pref.trim();
                head = rest.join(":").trim();
            }
        }
        const parts = head.split("—");
        const title = parts[0].trim();
        const desc = parts.slice(1).join("—").trim();
        const mapped = cardMap[title] || cardMap[norm] || key;
        const label = mapped ? `${mapped} · ${title}` : title;
        const effectiveKey = mapped || key || (title.length === 1 ? title : "");
        return { raw: norm, label, desc, key: effectiveKey };
    });
}

// --- Path info toast ---

function showPathInfo(payload = {}) {
    const id = payload.id || `path-${Date.now()}`;
    activePathId = id;
    const steps = payload.steps != null ? `Ścieżka: ${payload.steps} pól` : "Wyznaczam trasę...";
    const target = payload.target ? ` → ${payload.target}` : "";
    pathToast.textContent = `${steps}${target}`;
    pathToast.classList.remove("hidden");
}

function clearPathInfo(id = null) {
    if (id && activePathId && id !== activePathId) return;
    activePathId = null;
    pathToast.classList.add("hidden");
}

// --- Heroes rendering ---

function renderHeroes() {
    heroesList.innerHTML = "";
    heroes.forEach((hero) => {
        const card = document.createElement("div");
        card.className = "hero-card" + (hero.active ? " active" : "");
        card.innerHTML = `
            <div class="hero-name">${hero.name}</div>
            <div class="hero-stats">Statusy: ${hero.statuses.join(", ") || "brak"}</div>
            <div class="hero-stats">Inicjatywa: ${hero.initiative ?? "-"}</div>
            <div class="hero-notes">${hero.note || ""}</div>
        `;
        heroesList.appendChild(card);
    });
}

function renderInitiative() {
    if (!initiativeList) return;
    const { order, activeId, round } = initiativeState;
    if (!order || order.length === 0) {
        initiativeList.classList.add("empty-note");
        initiativeList.textContent = "Brak danych o inicjatywie.";
        return;
    }
    initiativeList.classList.remove("empty-note");
    initiativeList.innerHTML = "";
    const roundInfo = document.createElement("div");
    roundInfo.className = "initiative-round";
    roundInfo.textContent = `Runda ${round}`;
    initiativeList.appendChild(roundInfo);

    order.forEach((entry) => {
        const card = document.createElement("div");
        card.className = "initiative-card " + (entry.kind === "hero" ? "hero" : "enemy");
        if (String(entry.id) === String(activeId)) {
            card.classList.add("active");
        }
        if (entry.done) {
            card.classList.add("done");
        }
        const name = document.createElement("div");
        name.className = "initiative-name";
        name.textContent = entry.name || "aktor";
        const vals = document.createElement("div");
        vals.className = "initiative-vals";
        const base = entry.base ?? entry.current;
        const current = entry.current ?? base;
        const hasDelta = entry.delta && entry.delta !== 0;
        vals.textContent = hasDelta ? `${current} (${base})` : `${current}`;
        card.appendChild(name);
        card.appendChild(vals);
        initiativeList.appendChild(card);
    });
}
