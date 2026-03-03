const screenMenu = document.getElementById("screen-menu");
const screenGame = document.getElementById("screen-game");
const logList = document.getElementById("log-list");
const logLast = document.getElementById("log-last");
const logFab = document.getElementById("log-fab");
const logModal = document.getElementById("log-modal");
const logClose = document.getElementById("log-close");
const heroesList = document.getElementById("heroes-list");
const initiativeList = document.getElementById("initiative-list");
const initiativeSummary = document.getElementById("initiative-summary");
const initActiveName = document.getElementById("init-active-name");
const initNextName = document.getElementById("init-next-name");
const initRoundNum = document.getElementById("init-round-num");
const actionIllustration = document.getElementById("action-illustration");
const actionTitle = document.getElementById("action-title");
const actionText = document.getElementById("action-text");
const actionPrompt = document.getElementById("action-prompt");
const actionChoices = document.getElementById("action-choices");
const actionDesc = document.getElementById("action-desc");
const actionForm = document.getElementById("action-form");
const actionAnswer = document.getElementById("action-answer");
const rollNaturalControls = document.getElementById("roll-natural-controls");
const nat20Toggle = document.getElementById("nat20-toggle");
const nat1Toggle = document.getElementById("nat1-toggle");
const natModeHint = document.getElementById("nat-mode-hint");
const actionKind = document.getElementById("action-kind");
const actionSource = document.getElementById("action-source");
const modsBox = document.getElementById("action-mods");
const modsPenCirc = document.getElementById("mods-pen-circ");
const modsBonCirc = document.getElementById("mods-bon-circ");
const modsPenStat = document.getElementById("mods-pen-stat");
const modsBonStat = document.getElementById("mods-bon-stat");
const modsPenItem = document.getElementById("mods-pen-item");
const modsBonItem = document.getElementById("mods-bon-item");
const topbar = document.getElementById("topbar");
const topbarToggle = document.getElementById("topbar-toggle");
const eventFeed = document.getElementById("event-feed");
const statusScenario = document.getElementById("status-scenario");
const statusActor = document.getElementById("status-actor");
const statusNext = document.getElementById("status-next");
const statusRound = document.getElementById("status-round");
const statusPrompt = document.getElementById("status-prompt");
const PLACEHOLDER_IMAGE = "/static/placeholder.png";

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
let confirmMode = false;
let storedSelection = "";
let layoutMode = "info";
let rollNaturalMode = "none";
const DIGIT_BUFFER_MS = 600;
const pathToast = document.getElementById("path-toast");
let activePathId = null;
let initiativeState = { order: [], activeId: null, round: 1 };
let activeActorId = null;
let lastLoggedRound = null;
let lastLoggedActiveActorId = null;
actionForm.classList.add("hidden");

function _isNaturalRollPrompt(prompt) {
    if (!prompt) return false;
    const kind = String(prompt.kind || "").toLowerCase();
    const layout = String(prompt.layout || "").toLowerCase();
    if (layout === "damage") return false;
    return layout === "test" || kind === "roll";
}

function _setNaturalMode(mode) {
    const next = mode === "nat20" || mode === "nat1" ? mode : "none";
    rollNaturalMode = next;
    if (nat20Toggle) nat20Toggle.classList.toggle("active", next === "nat20");
    if (nat1Toggle) nat1Toggle.classList.toggle("active", next === "nat1");
}

function _cycleNaturalMode() {
    if (rollNaturalMode === "none") _setNaturalMode("nat20");
    else if (rollNaturalMode === "nat20") _setNaturalMode("nat1");
    else _setNaturalMode("none");
}

function _renderNaturalControls(prompt) {
    const visible = _isNaturalRollPrompt(prompt);
    if (!rollNaturalControls) return;
    if (!visible) {
        rollNaturalControls.classList.add("hidden");
        return;
    }
    rollNaturalControls.classList.remove("hidden");
    if (natModeHint) {
        natModeHint.textContent = "* : brak -> nat20 -> nat1";
    }
    _setNaturalMode(rollNaturalMode);
}

if (nat20Toggle) {
    nat20Toggle.addEventListener("click", () => {
        _setNaturalMode(rollNaturalMode === "nat20" ? "none" : "nat20");
    });
}
if (nat1Toggle) {
    nat1Toggle.addEventListener("click", () => {
        _setNaturalMode(rollNaturalMode === "nat1" ? "none" : "nat1");
    });
}

function setIllustration(imageUrl) {
    const src = imageUrl || PLACEHOLDER_IMAGE;
    if (src) {
        actionIllustration.style.backgroundImage = `url(${src})`;
        actionIllustration.style.backgroundSize = "cover";
        actionIllustration.style.backgroundPosition = "center";
    } else {
        actionIllustration.style.backgroundImage = "";
    }
}

function clearMods() {
    [modsPenCirc, modsBonCirc, modsPenStat, modsBonStat, modsPenItem, modsBonItem].forEach((el) => {
        if (el) el.innerHTML = "";
    });
    modsBox.classList.add("hidden");
}

function renderMods(mods = {}) {
    const { penCirc = [], bonCirc = [], penStat = [], bonStat = [], penItem = [], bonItem = [] } = mods;
    const fill = (el, arr) => {
        if (!el) return;
        el.innerHTML = "";
        arr.forEach((item, idx) => {
            const li = document.createElement("li");
            li.className = idx === 0 ? "top" : "";
            const label = document.createElement("span");
            label.textContent = item.label || item.tag || item.name || "mod";
            const val = document.createElement("span");
            val.className = "mods-value";
            val.textContent = item.value != null ? item.value : "";
            li.appendChild(label);
            li.appendChild(val);
            el.appendChild(li);
        });
    };
    clearMods();
    const hasAny =
        penCirc.length || bonCirc.length || penStat.length || bonStat.length || penItem.length || bonItem.length;
    if (!hasAny) return;
    fill(modsPenCirc, penCirc);
    fill(modsBonCirc, bonCirc);
    fill(modsPenStat, penStat);
    fill(modsBonStat, bonStat);
    fill(modsPenItem, penItem);
    fill(modsBonItem, bonItem);
    modsBox.classList.remove("hidden");
}

function showMenu() {
    screenMenu.classList.remove("hidden");
    screenGame.classList.add("hidden");
}

function showGame() {
    screenMenu.classList.add("hidden");
    screenGame.classList.remove("hidden");
}

function str(value, fallback = "-") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
}

function actorNameById(id) {
    if (!id) return "-";
    const fromInit = initiativeState.order.find((entry) => String(entry.id) === String(id));
    if (fromInit && fromInit.name) return fromInit.name;
    const fromHero = heroes.get(id);
    if (fromHero && fromHero.name) return fromHero.name;
    return String(id);
}

function currentPromptLabel() {
    if (!activePrompt) return "Brak";
    const kind = str(activePrompt.kind || activePrompt.layout || layoutMode || "prompt");
    const choicesCount = Array.isArray(activePrompt.choices) ? activePrompt.choices.length : currentChoices.length;
    return choicesCount ? `${kind} (${choicesCount})` : kind;
}

function initiativePointers() {
    const order = Array.isArray(initiativeState.order) ? initiativeState.order : [];
    if (!order.length) {
        return { active: "-", next: "-" };
    }
    const activeIdx = order.findIndex((entry) => String(entry.id) === String(initiativeState.activeId));
    if (activeIdx === -1) {
        return { active: "-", next: order[0]?.name || "-" };
    }
    const active = order[activeIdx]?.name || "-";
    const next = order.length > 1 ? order[(activeIdx + 1) % order.length]?.name || "-" : "-";
    return { active, next };
}

function updateSessionSummary() {
    const pointers = initiativePointers();
    const activeLabel = activeActorId ? actorNameById(activeActorId) : pointers.active;
    if (statusScenario) statusScenario.textContent = str(currentScenario);
    if (statusActor) statusActor.textContent = str(activeLabel);
    if (statusNext) statusNext.textContent = str(pointers.next);
    if (statusRound) statusRound.textContent = str(initiativeState.round);
    if (statusPrompt) statusPrompt.textContent = currentPromptLabel();
}

function appendTag(container, tag) {
    if (!container || !tag) return;
    const tagEl = document.createElement("span");
    tagEl.className = "tag";
    tagEl.textContent = tag;
    container.appendChild(tagEl);
}

function addEventFeedEntry(text, meta, variant = "", tag = "") {
    if (!eventFeed) return;
    const empty = eventFeed.querySelector(".event-feed-empty");
    if (empty) empty.remove();
    const item = document.createElement("li");
    item.className = "event-item" + (variant ? ` ${variant}` : "");

    const main = document.createElement("div");
    main.className = "event-main";
    appendTag(main, tag);
    const textEl = document.createElement("span");
    textEl.textContent = str(text, "");
    main.appendChild(textEl);

    const metaEl = document.createElement("div");
    metaEl.className = "event-meta";
    metaEl.textContent = str(meta, "");

    item.appendChild(main);
    item.appendChild(metaEl);
    eventFeed.prepend(item);

    while (eventFeed.children.length > 8) {
        eventFeed.removeChild(eventFeed.lastChild);
    }
}

function addLogEntry(text, meta, variant = "", tag = "", image = "") {
    const item = document.createElement("li");
    item.className = "log-item" + (variant ? ` ${variant}` : "");

    if (image) {
        const thumbWrap = document.createElement("div");
        thumbWrap.className = "log-thumb-wrap";
        const thumb = document.createElement("img");
        thumb.className = "log-thumb";
        thumb.src = image;
        thumb.alt = "";
        thumbWrap.appendChild(thumb);
        item.appendChild(thumbWrap);
    }

    const body = document.createElement("div");
    body.className = "log-body";
    const logText = document.createElement("div");
    logText.className = "log-text";
    appendTag(logText, tag);
    const textEl = document.createElement("span");
    textEl.textContent = str(text, "");
    logText.appendChild(textEl);
    const metaEl = document.createElement("div");
    metaEl.className = "meta";
    metaEl.textContent = str(meta, "");
    body.appendChild(logText);
    body.appendChild(metaEl);
    item.appendChild(body);

    logList.prepend(item);
    if (logLast) {
        logLast.innerHTML = "";
        appendTag(logLast, tag);
        const lastText = document.createElement("span");
        lastText.textContent = str(text, "");
        logLast.appendChild(lastText);
    }
    addEventFeedEntry(text, meta, variant, tag);
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

function samePos(a, b) {
    if (!Array.isArray(a) || !Array.isArray(b)) return false;
    if (a.length < 2 || b.length < 2) return false;
    return Number(a[0]) === Number(b[0]) && Number(a[1]) === Number(b[1]);
}

function formatPos(pos) {
    if (!Array.isArray(pos) || pos.length < 2) return "-";
    return `(${pos[0]}, ${pos[1]})`;
}

function arrayDiff(previous, next) {
    const prevSet = new Set((previous || []).map((item) => String(item)));
    const nextSet = new Set((next || []).map((item) => String(item)));
    const added = [...nextSet].filter((item) => !prevSet.has(item));
    const removed = [...prevSet].filter((item) => !nextSet.has(item));
    return { added, removed };
}

function buildHeroUpdateLog(previous, current) {
    if (!previous) {
        return {
            message: `${current.name} dołącza do sceny na ${formatPos(current.pos)}.`,
            variant: "info",
        };
    }
    const changes = [];
    let variant = "info";

    if (previous.wounds !== current.wounds) {
        changes.push(`Rany: ${str(previous.wounds)} -> ${str(current.wounds)}`);
        const before = Number(previous.wounds);
        const after = Number(current.wounds);
        if (!Number.isNaN(before) && !Number.isNaN(after)) {
            if (after > before) variant = "warning";
            else if (after < before && variant !== "warning") variant = "success";
        }
    }
    if (!samePos(previous.pos, current.pos) && (previous.pos || current.pos)) {
        changes.push(`Pozycja: ${formatPos(previous.pos)} -> ${formatPos(current.pos)}`);
    }
    if (previous.initiative !== current.initiative) {
        changes.push(`Inicjatywa: ${str(previous.initiative)} -> ${str(current.initiative)}`);
    }
    const statusesDiff = arrayDiff(previous.statuses, current.statuses);
    if (statusesDiff.added.length) {
        changes.push(`+ status: ${statusesDiff.added.join(", ")}`);
        if (variant !== "warning") variant = "success";
    }
    if (statusesDiff.removed.length) {
        changes.push(`- status: ${statusesDiff.removed.join(", ")}`);
    }
    if (!changes.length && previous.note !== current.note && current.note) {
        changes.push(`Notatka: ${current.note}`);
    }
    if (!changes.length) return null;
    return { message: `${current.name}: ${changes.join(" · ")}`, variant };
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
        const promptTag = payload.kind === "choice" ? "Wybór" : payload.kind === "info" ? "Info" : "Rzut";
        const sourceNote = payload.source ? ` [${payload.source}]` : "";
        const choicesCount = Array.isArray(payload.choices) ? payload.choices.length : 0;
        const choicesNote = choicesCount ? ` (${choicesCount} opcji)` : "";
        addLogEntry(`Nowy prompt${sourceNote}: ${payload.prompt}${choicesNote}`, meta, "info", promptTag);
        updateSessionSummary();
        return;
    }
    if (type === "special_preview") {
        const title = payload.name || payload.slug || "Zdolność specjalna";
        actionTitle.textContent = title;
        actionText.textContent = payload.desc || "";
        setIllustration(payload.image);
        addLogEntry(`Zdolność: ${title}`, meta, "info", "Special");
        updateSessionSummary();
        return;
    }
    if (type === "info") {
        renderPrompt({
            id: `info-${Date.now()}`,
            prompt: payload.text || payload.message || "Informacja",
            kind: "info",
            choices: [],
            source: payload.source || "",
            image: payload.image || null,
        });
        addLogEntry(payload.text || payload.message || "Info", meta, "info", payload.source || "Info");
        return;
    }
    if (type === "idle_hint") {
        if (!activePrompt) {
            actionTitle.textContent = payload.title || "Czekam na działania...";
            actionText.textContent = payload.text || "";
        }
        return;
    }
    if (type === "prompt_answered") {
        addLogEntry(`Odpowiedź (${payload.prompt || ""}): ${payload.answer}`, meta, "success", "Prompt");
        if (activePrompt && String(activePrompt.id) === String(payload.id)) {
            closePrompt();
        }
        updateSessionSummary();
        return;
    }
    if (type === "hero_snapshot" || type === "hero") {
        const id = payload.id || payload.object_id || payload.name || "hero";
        const previous = heroes.get(id);
        const current = {
            id,
            name: payload.name || id,
            statuses: payload.statuses || [],
            note: payload.note,
            wounds: payload.wounds,
            pos: payload.pos,
            initiative: payload.initiative,
            image: payload.image,
        };
        heroes.set(id, current);
        renderHeroes();
        const heroLog = buildHeroUpdateLog(previous, current);
        if (heroLog) {
            addLogEntry(heroLog.message, meta, heroLog.variant, "Bohater");
        }
        updateSessionSummary();
        return;
    }
    if (type === "active_actor_changed") {
        const prev = activeActorId;
        activeActorId = payload.id || null;
        renderHeroes();
        if (String(prev) !== String(activeActorId)) {
            if (activeActorId) {
                const actorLabel = payload.name || actorNameById(activeActorId);
                addLogEntry(`Aktywna tura: ${actorLabel}`, meta, "info", "Tura");
            } else {
                addLogEntry("Brak aktywnego aktora.", meta, "info", "Tura");
            }
            lastLoggedActiveActorId = activeActorId;
        }
        updateSessionSummary();
        return;
    }
    if (type === "narration") {
        addLogEntry(payload.message || "Narrator", meta, "info", "Narrator");
        return;
    }
    if (type === "action") {
        if (!activePrompt) {
            const actor = payload.actor?.name || payload.actor?.id || "Aktor";
            const actionId = str(payload.action_id || "akcja", "akcja").replace(/_/g, " ");
            const target = payload.target?.name || payload.target?.id;
            actionTitle.textContent = actor;
            actionText.textContent = target ? `${actionId} -> ${target}` : actionId;
        }
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
            round: payload.round ?? null,
        };
        activeActorId = initiativeState.activeId || null;
        if (initiativeState.round && initiativeState.round !== lastLoggedRound) {
            addLogEntry(`Runda ${initiativeState.round} start`, meta, "info", "Runda");
            lastLoggedRound = initiativeState.round;
        }
        if (initiativeState.activeId && String(lastLoggedActiveActorId) !== String(initiativeState.activeId)) {
            addLogEntry(`Aktywna tura: ${actorNameById(initiativeState.activeId)}`, meta, "info", "Tura");
            lastLoggedActiveActorId = initiativeState.activeId;
        }
        if (!initiativeState.activeId) {
            lastLoggedActiveActorId = null;
        }
        renderInitiative();
        updateSessionSummary();
        return;
    }
    // domyślnie traktujemy jako log
    const level = (payload.level || "").toLowerCase();
    let variant = "";
    if (level === "error") variant = "error";
    else if (level === "warn" || level === "warning") variant = "warning";
    addLogEntry(payload.message || type, meta, variant, payload.tag || "", payload.image || "");
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
        updateSessionSummary();
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

if (logFab && logModal) {
    logFab.addEventListener("click", () => {
        logModal.classList.toggle("hidden");
    });
}
if (logClose && logModal) {
    logClose.addEventListener("click", () => {
        logModal.classList.add("hidden");
    });
}
if (logModal) {
    logModal.addEventListener("click", (evt) => {
        if (evt.target === logModal) {
            logModal.classList.add("hidden");
        }
    });
}

if (topbarToggle && topbar) {
    topbarToggle.addEventListener("click", () => {
        topbar.classList.toggle("collapsed");
        topbarToggle.textContent = topbar.classList.contains("collapsed") ? "▼" : "▲";
    });
}

// start in menu and connect SSE
showMenu();
updateSessionSummary();
connectStream();
fetchPendingPrompts();
setInterval(fetchPendingPrompts, 2000);

// --- Prompt panel logic ---

actionForm.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    if (!activePrompt) return;
    if (activePrompt.kind === "info") {
        const infoId = String(activePrompt.id || "");
        if (infoId.startsWith("info-")) {
            closePrompt();
            return;
        }
        await sendPromptAnswer("ok");
        return;
    }

    // specjalny flow dla wyboru akcji z potwierdzeniem
    if (layoutMode === "action_select" && !confirmMode) {
        storedSelection = actionAnswer.value.trim();
        if (!storedSelection) return;
        // przejście do potwierdzenia
        confirmMode = true;
        actionTitle.textContent = storedSelection;
        actionText.textContent = activePrompt.action_desc || activePrompt.desc || "Potwierdź tę akcję.";
        actionAnswer.classList.add("input-hidden");
        actionChoices.innerHTML = "";
        const confirmChoices = normalizeChoices({
            choices: ["Accept", "Decline"],
            choice_meta: [
                { raw: "Accept", label: "Accept", desc: "Zatwierdź i procesuj.", key: "+" },
                { raw: "Decline", label: "Decline", desc: "Wróć do wyboru akcji.", key: "-" },
            ],
        });
        currentChoices = confirmChoices.map((c) => c.raw);
        choiceMeta = confirmChoices;
        selectedChoiceIndex = 0;
        confirmChoices.forEach((c, idx) => {
            const pill = document.createElement("div");
            pill.className = "choice-pill";
            pill.innerHTML =
                '<div class="label"><span class="key">' +
                (c.key || String(idx + 1)) +
                "</span>" +
                (c.label || "") +
                "</div>" +
                (c.desc ? '<div class="desc">' + c.desc + "</div>" : "");
            pill.addEventListener("click", () => selectChoice(idx));
            actionChoices.appendChild(pill);
        });
        updateChoiceHighlight();
        updateChoiceDesc();
        return;
    }

    if (layoutMode === "action_select" && confirmMode) {
        const choice = currentChoices[selectedChoiceIndex] || "Decline";
        if (choice.toLowerCase().startsWith("decline")) {
            // reset do wyboru akcji, czysty filtr
            confirmMode = false;
            storedSelection = "";
            actionChoices.innerHTML = "";
            actionDesc.textContent = "";
            actionAnswer.value = "";
            actionAnswer.classList.remove("input-hidden");
            actionAnswer.placeholder = "Nazwa akcji...";
            currentChoices = [];
            choiceMeta = [];
            selectedChoiceIndex = -1;
            return;
        }
        // Accept — zwracamy wpisaną akcję
        await sendPromptAnswer(storedSelection);
        return;
    }

    let answer = actionAnswer.value.trim();
    if (!answer && currentChoices.length > 0 && selectedChoiceIndex >= 0) {
        answer = currentChoices[selectedChoiceIndex];
    }
    if (!answer) return;
    await sendPromptAnswer(answer);
});

async function sendPromptAnswer(answer) {
    try {
        let finalAnswer = answer;
        if (_isNaturalRollPrompt(activePrompt)) {
            const parsed = Number.parseInt(String(answer).trim(), 10);
            if (!Number.isNaN(parsed)) {
                finalAnswer = {
                    roll: parsed,
                    natural_mode: rollNaturalMode,
                };
            }
        }
        await fetch(`/api/prompts/${activePrompt.id}/response`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer: finalAnswer }),
        });
        actionAnswer.value = "";
        closePrompt();
    } catch (err) {
        console.error(err);
    }
}

document.addEventListener("keydown", (evt) => {
    if (evt.key === "Escape" && logModal && !logModal.classList.contains("hidden")) {
        logModal.classList.add("hidden");
        return;
    }
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
    if (_isNaturalRollPrompt(activePrompt) && evt.key === "*") {
        evt.preventDefault();
        _cycleNaturalMode();
        _renderNaturalControls(activePrompt);
        return;
    }
    if (layoutMode === "equip_nav") {
        const key = evt.key;
        const map = {
            ArrowUp: "up",
            ArrowDown: "down",
            ArrowRight: "transfer",
            ArrowLeft: "drop",
            "8": "up",
            "2": "down",
            "6": "transfer",
            "4": "drop",
            "5": "toggle",
            Enter: "toggle",
            "0": "exit",
            Escape: "exit",
        };
        const cmd = map[key];
        if (cmd) {
            evt.preventDefault();
            sendPromptAnswer(cmd);
            return;
        }
    }
    if (layoutMode === "action_select" && confirmMode && evt.key === "Escape") {
        evt.preventDefault();
        // manual decline -> reset filtra
        confirmMode = false;
        storedSelection = "";
        actionChoices.innerHTML = "";
        actionDesc.textContent = "";
        actionAnswer.value = "";
        actionAnswer.classList.remove("input-hidden");
        actionAnswer.placeholder = "Nazwa akcji...";
        currentChoices = [];
        choiceMeta = [];
        selectedChoiceIndex = -1;
        return;
    }
    if (activePrompt.kind === "info") {
        if (evt.key === "Enter") {
            evt.preventDefault();
            const infoId = String(activePrompt.id || "");
            if (infoId.startsWith("info-")) {
                closePrompt();
            } else {
                actionForm.dispatchEvent(new Event("submit", { cancelable: true }));
            }
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
    layoutMode = prompt.layout || prompt.kind || "info";
    confirmMode = false;
    storedSelection = "";
    rollNaturalMode = "none";
    actionTitle.textContent = prompt.title || prompt.prompt || "Akcja";
    actionText.textContent = prompt.subtitle || "";
    const promptBody = prompt.prompt_long || (layoutMode === "dialog" ? prompt.prompt : "");
    actionPrompt.textContent = promptBody || "";
    actionPrompt.classList.toggle("hidden", !promptBody);
    setIllustration(prompt.image);
    actionKind.textContent = "";
    actionKind.classList.add("hidden");
    actionSource.textContent = "";
    actionSource.classList.add("hidden");
    actionChoices.innerHTML = "";
    actionDesc.textContent = "";
    clearMods();

    const normalized = normalizeChoices(prompt);
    currentChoices = normalized.map((c) => c.raw);
    choiceMeta = normalized;
    selectedChoiceIndex = normalized.length ? 0 : -1;

    const ensureChoiceList = (list) => {
        list.forEach((c, idx) => {
            const pill = document.createElement("div");
            pill.className = "choice-pill";
            pill.innerHTML =
                '<div class="label"><span class="key">' +
                (c.key || String(idx + 1)) +
                "</span>" +
                (c.label || "") +
                "</div>" +
                (c.desc ? '<div class="desc">' + c.desc + "</div>" : "");
            pill.addEventListener("click", () => {
                selectChoice(idx);
            });
            actionChoices.appendChild(pill);
        });
    };

    if (layoutMode === "dialog" || layoutMode === "interact") {
        ensureChoiceList(normalized);
        actionAnswer.value = normalized[0]?.raw || "";
        actionAnswer.classList.add("input-hidden");
        actionAnswer.required = false;
        updateChoiceHighlight();
        updateChoiceDesc();
        actionText.classList.add("hidden");
        actionPrompt.classList.add("hidden");
        actionDesc.classList.add("hidden");
    } else if (layoutMode === "action_select") {
        // pierwszy krok: wpisz nazwę akcji
        actionTitle.textContent = prompt.title || "Wybierz akcję";
        actionText.textContent = prompt.subtitle || "Wpisz nazwę akcji i Enter.";
        actionAnswer.placeholder = "Nazwa akcji...";
        actionAnswer.value = "";
        actionAnswer.required = true;
        actionAnswer.classList.remove("input-hidden");
    } else if (layoutMode === "test" || layoutMode === "damage") {
        actionAnswer.placeholder = prompt.answer_placeholder || "Podaj wynik (liczba)...";
        actionAnswer.value = "";
        actionAnswer.required = true;
        actionAnswer.classList.remove("input-hidden");
        if (prompt.modifiers) {
            renderMods(prompt.modifiers);
        }
    } else if (prompt.kind === "info") {
        actionAnswer.value = "";
        actionAnswer.placeholder = "Enter aby zamknąć";
        actionAnswer.required = false;
        actionAnswer.classList.add("input-hidden");
    } else if (normalized.length > 0) {
        ensureChoiceList(normalized);
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
    _renderNaturalControls(prompt);
    actionForm.classList.remove("hidden");
    updateSessionSummary();
    actionAnswer.focus();
}

function closePrompt() {
    activePrompt = null;
    confirmMode = false;
    storedSelection = "";
    layoutMode = "info";
    rollNaturalMode = "none";
    actionForm.classList.add("hidden");
    actionChoices.innerHTML = "";
    actionDesc.textContent = "";
    actionDesc.classList.remove("hidden");
    actionPrompt.textContent = "";
    actionPrompt.classList.add("hidden");
    actionTitle.textContent = "Czekam na działania...";
    actionText.textContent = "";
    actionText.classList.remove("hidden");
    clearMods();
    _renderNaturalControls(null);
    updateSessionSummary();
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
    if (selectedChoiceIndex === idx) {
        // toggle expansion
        choiceMeta[idx].expanded = !choiceMeta[idx].expanded;
    } else {
        selectedChoiceIndex = idx;
        choiceMeta = choiceMeta.map((c, i) => ({ ...c, expanded: i === idx ? true : c.expanded && i === idx }));
    }
    actionAnswer.value = currentChoices[idx];
    updateChoiceHighlight();
    updateChoiceDesc();
}

function updateChoiceHighlight() {
    const pills = actionChoices.querySelectorAll(".choice-pill");
    pills.forEach((pill, i) => {
        const isSelected = i === selectedChoiceIndex;
        const isExpanded = choiceMeta[i]?.expanded;
        pill.classList.toggle("selected", isSelected);
        pill.classList.toggle("expanded", isExpanded);
        if (isSelected) {
            pill.scrollIntoView({ block: "nearest", inline: "nearest" });
        }
    });
}

function updateChoiceDesc() {
    const idx = choiceMeta.findIndex((c) => c.expanded);
    if (idx === -1) {
        actionDesc.textContent = "";
        return;
    }
    actionDesc.textContent = choiceMeta[idx].desc || "";
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
    // prefer structured choice_meta if provided
    if (Array.isArray(prompt.choice_meta) && prompt.choice_meta.length) {
        return prompt.choice_meta.map((c) => ({
            raw: c.raw || c.label || "",
            label: c.label || c.raw || "",
            desc: c.desc || "",
            key: c.key || "",
        }));
    }
    const rawChoices = Array.isArray(prompt.choices) ? prompt.choices : [];
    const cardMap = {
        accept: "+",
        decline: "-",
        move: "1",
        interact: "2",
        seek: "3",
        stealth: "4",
        test_attack: "5",
        special: "6",
        delay: "7",
        end: "8",
    };
    return rawChoices.map((raw) => {
        const norm = String(raw).trim();
        const lowerNorm = norm.toLowerCase();
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
        const mapped =
            cardMap[title.toLowerCase()] ||
            cardMap[lowerNorm] ||
            (key ? cardMap[key.toLowerCase()] : undefined) ||
            key;
        const label = mapped ? `${mapped} · ${title}` : title;
        const effectiveKey = mapped || key || (title.length === 1 ? title : "");
        return { raw: norm, label, desc, key: effectiveKey };
    });
}

// --- Path info toast ---

function showPathInfo(payload = {}) {
    const id = payload.id || `path-${Date.now()}`;
    activePathId = id;
    const parts = [];
    if (payload.steps != null) parts.push(`${payload.steps} pól`);
    if (payload.feet != null) parts.push(`${payload.feet} stóp`);
    const steps = parts.length ? `Ścieżka: ${parts.join(" · ")}` : "Wyznaczam trasę...";
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
        const isActive = String(hero.id || "") === String(activeActorId || "");
        card.className = "hero-card" + (isActive ? " active" : "");
        const heroImg = hero.image || PLACEHOLDER_IMAGE;
        const statuses = hero.statuses && hero.statuses.length
            ? hero.statuses.map((s) => `<span class="status-pill ${statusTone(s)}">${s}</span>`).join("")
            : '<span class="status-pill neutral">brak</span>';
        card.innerHTML = `
            <div class="hero-row">
                <div class="hero-info">
                    <div class="hero-name">${hero.name}</div>
                    <div class="hero-stats">Inicjatywa: ${hero.initiative ?? "-"}</div>
                    <div class="hero-statuses">${statuses}</div>
                    <div class="hero-stats">Rany: ${hero.wounds ?? "-"}</div>
                    <div class="hero-notes">${hero.note || ""}</div>
                </div>
                <div class="hero-portrait" style="background-image: url('${heroImg}')"></div>
            </div>
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
