const screenMenu = document.getElementById("screen-menu");
const screenGame = document.getElementById("screen-game");
const logList = document.getElementById("log-list");
const logLast = document.getElementById("log-last");
const logDrawer = document.getElementById("log-drawer");
const logToggle = document.getElementById("log-toggle");
const heroesList = document.getElementById("heroes-list");
const initiativeList = document.getElementById("initiative-list");
const initiativeSummary = document.getElementById("initiative-summary");
const initActiveName = document.getElementById("init-active-name");
const initNextName = document.getElementById("init-next-name");
const initRoundNum = document.getElementById("init-round-num");
const actionIllustration = document.getElementById("action-illustration");
const actionTitle = document.getElementById("action-title");
const actionText = document.getElementById("action-text");
const actionChoices = document.getElementById("action-choices");
const actionDesc = document.getElementById("action-desc");
const actionForm = document.getElementById("action-form");
const actionAnswer = document.getElementById("action-answer");
const actionKind = document.getElementById("action-kind");
const actionSource = document.getElementById("action-source");
const topbar = document.getElementById("topbar");
const topbarToggle = document.getElementById("topbar-toggle");

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
const pathToast = document.getElementById("path-toast");
let activePathId = null;
let initiativeState = { order: [], activeId: null, round: 1 };
let lastLoggedRound = null;
actionForm.classList.add("hidden");

function showMenu() {
    screenMenu.classList.remove("hidden");
    screenGame.classList.add("hidden");
}

function showGame() {
    screenMenu.classList.add("hidden");
    screenGame.classList.remove("hidden");
}

function addLogEntry(text, meta, variant = "", tag = "") {
    const item = document.createElement("li");
    item.className = "log-item" + (variant ? ` ${variant}` : "");
    item.innerHTML = `
        <div>${tag ? `<span class="tag">${tag}</span>` : ""}${text}</div>
        <div class="meta">${meta || ""}</div>
    `;
    logList.prepend(item);
    if (logLast) {
        logLast.innerHTML = `${tag ? `<span class="tag">${tag}</span>` : ""}${text}`;
    }
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
        addLogEntry(`Nowy rzut: ${payload.prompt}`, meta, "info", "Rzut");
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
        addLogEntry(payload.text || payload.message || "Info", meta, "info", payload.source || "Info");
        return;
    }
    if (type === "prompt_answered") {
        addLogEntry(`Rzut rozstrzygnięty (${payload.prompt || ""}): ${payload.answer}`, meta, "success", "Rzut");
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
        addLogEntry(`Aktualny bohater: ${payload.name || ""}`, meta, "info", "Bohater");
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
        if (initiativeState.round && initiativeState.round !== lastLoggedRound) {
            addLogEntry(`Runda ${initiativeState.round} start`, meta, "info", "Runda");
            lastLoggedRound = initiativeState.round;
        }
        renderInitiative();
        return;
    }
    // domyślnie traktujemy jako log
    const level = (payload.level || "").toLowerCase();
    let variant = "";
    if (level === "error") variant = "error";
    else if (level === "warn" || level === "warning") variant = "warning";
    addLogEntry(payload.message || type, meta, variant);
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
const scenarioButtons = Array.from(document.querySelectorAll(".scenario-btn"));
let scenarioIndex = 0;
function highlightScenario(idx) {
    scenarioButtons.forEach((b, i) => {
        if (i === idx) b.classList.add("selected");
        else b.classList.remove("selected");
    });
}
if (scenarioButtons.length) {
    highlightScenario(scenarioIndex);
}

if (logToggle && logDrawer) {
    logToggle.addEventListener("click", () => {
        logDrawer.classList.toggle("collapsed");
    });
    if (logLast) {
        logLast.addEventListener("click", () => {
            logDrawer.classList.toggle("collapsed");
        });
    }
}

if (topbarToggle && topbar) {
    topbarToggle.addEventListener("click", () => {
        topbar.classList.toggle("collapsed");
        topbarToggle.textContent = topbar.classList.contains("collapsed") ? "▼" : "▲";
    });
}
if (topbar && !topbar.classList.contains("collapsed")) {
    topbar.classList.add("collapsed");
    if (topbarToggle) topbarToggle.textContent = "▼";
}

// start in menu and connect SSE
showMenu();
connectStream();
fetchPendingPrompts();
setInterval(fetchPendingPrompts, 2000);

// --- Prompt panel logic ---

actionForm.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    if (!activePrompt) return;
    if (activePrompt.kind === "info") {
        closePrompt();
        return;
    }
    let answer = actionAnswer.value.trim();
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
        actionAnswer.value = "";
        closePrompt();
    } catch (err) {
        console.error(err);
    }
});

document.addEventListener("keydown", (evt) => {
    // scenario wybór w menu
    if (!screenMenu.classList.contains("hidden") && screenGame.classList.contains("hidden")) {
        if (evt.key === "ArrowDown" || evt.key === "ArrowRight") {
            evt.preventDefault();
            if (scenarioButtons.length) {
                scenarioIndex = (scenarioIndex + 1) % scenarioButtons.length;
                highlightScenario(scenarioIndex);
            }
        }
        if (evt.key === "ArrowUp" || evt.key === "ArrowLeft") {
            evt.preventDefault();
            if (scenarioButtons.length) {
                scenarioIndex = (scenarioIndex - 1 + scenarioButtons.length) % scenarioButtons.length;
                highlightScenario(scenarioIndex);
            }
        }
        if (evt.key === "Enter" && scenarioButtons.length) {
            evt.preventDefault();
            scenarioButtons[scenarioIndex].click();
        }
    }

    if (!activePrompt) return;
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

            if (digitBuffer.length >= 2 || currentChoices.length < 10) {
                const num = parseInt(digitBuffer, 10);
                if (!isNaN(num) && num >= 1 && num <= currentChoices.length) {
                    selectChoice(num - 1);
                    digitBuffer = "";
                    clearTimeout(digitTimer);
                    digitTimer = null;
                } else if (digitBuffer.length >= 2) {
                    digitBuffer = "";
                }
            }
        }
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
            actionForm.dispatchEvent(new Event("submit", { cancelable: true }));
        }
    }
});

function openPrompt(prompt) {
    activePrompt = prompt;
    renderedPrompts.add(prompt.id);
    actionTitle.textContent = prompt.prompt || "Akcja";
    actionText.textContent = prompt.source ? `Źródło: ${prompt.source}` : "";
    actionKind.textContent = prompt.kind || "prompt";
    actionKind.classList.toggle("hidden", !prompt.kind);
    actionSource.textContent = prompt.source ? `Źródło: ${prompt.source}` : "";
    actionSource.classList.toggle("hidden", !prompt.source);
    actionChoices.innerHTML = "";
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
        actionChoices.appendChild(pill);
    });
    if (prompt.kind === "info") {
        actionAnswer.value = "";
        actionAnswer.placeholder = "Enter aby zamknąć";
        actionAnswer.required = false;
        actionAnswer.classList.add("input-hidden");
    } else if (normalized.length > 0) {
        actionAnswer.value = normalized[0].raw;
        actionAnswer.classList.add("input-hidden");
        actionAnswer.required = false;
        updateChoiceHighlight();
        updateChoiceDesc();
    } else {
        actionAnswer.placeholder = "Twoja odpowiedź...";
        actionAnswer.required = true;
        actionAnswer.classList.remove("input-hidden");
    }
    actionForm.classList.remove("hidden");
    actionAnswer.focus();
}

function closePrompt() {
    activePrompt = null;
    actionForm.classList.add("hidden");
    actionChoices.innerHTML = "";
    actionDesc.textContent = "";
    actionTitle.textContent = "Czekam na działania...";
    actionText.textContent = "";
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
    actionAnswer.value = currentChoices[idx];
    updateChoiceHighlight();
    updateChoiceDesc();
}

function updateChoiceHighlight() {
    const pills = actionChoices.querySelectorAll(".choice-pill");
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
        actionDesc.textContent = "";
        return;
    }
    actionDesc.textContent = choiceMeta[selectedChoiceIndex].desc || "";
}

function statusTone(name = "") {
    const txt = String(name).toLowerCase();
    const badKeywords = ["poison", "wound", "bleed", "stun", "prone", "fear", "slow", "curse", "burn", "exhaust"];
    const goodKeywords = ["bless", "shield", "heroism", "haste", "buff", "guard", "aid", "inspire", "rage"];
    if (badKeywords.some((k) => txt.includes(k))) return "bad";
    if (goodKeywords.some((k) => txt.includes(k))) return "good";
    return "neutral";
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
    const target = payload.target ? ` → cel ${payload.target}` : "";
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
        const statuses = hero.statuses && hero.statuses.length
            ? hero.statuses.map((s) => `<span class="status-pill ${statusTone(s)}">${s}</span>`).join("")
            : '<span class="status-pill neutral">brak</span>';
        card.innerHTML = `
            <div class="hero-name">${hero.name}</div>
            <div class="hero-stats">Inicjatywa: ${hero.initiative ?? "-"}</div>
            <div class="hero-statuses">${statuses}</div>
            <div class="hero-stats">Rany: ${hero.wounds ?? "-"}</div>
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
        initiativeSummary.classList.add("hidden");
        return;
    }
    initiativeSummary.classList.remove("hidden");
    initiativeList.classList.remove("empty-note");
    initiativeList.innerHTML = "";

    const activeIdx = order.findIndex((entry) => String(entry.id) === String(activeId));
    const activeEntry = activeIdx >= 0 ? order[activeIdx] : null;
    const nextEntry = activeIdx >= 0 && order.length > 1 ? order[(activeIdx + 1) % order.length] : null;
    initActiveName.textContent = activeEntry ? activeEntry.name : "-";
    initNextName.textContent = nextEntry ? nextEntry.name : "-";
    initRoundNum.textContent = round ?? "-";

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
        const delta = entry.delta || 0;
        const hasDelta = delta !== 0;
        vals.textContent = `${current}`;
        if (hasDelta) {
            const deltaEl = document.createElement("span");
            deltaEl.className = "delta " + (delta < 0 ? "negative" : "positive");
            deltaEl.textContent = delta < 0 ? `↓ ${Math.abs(delta)}` : `↑ ${delta}`;
            vals.appendChild(deltaEl);
            const baseEl = document.createElement("span");
            baseEl.className = "delta";
            baseEl.textContent = `(${base})`;
            vals.appendChild(baseEl);
        }
        card.appendChild(name);
        card.appendChild(vals);
        initiativeList.appendChild(card);
    });
}
