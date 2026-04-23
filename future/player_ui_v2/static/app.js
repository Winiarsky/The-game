const screens = {
    start: document.getElementById("screen-start"),
    assembly: document.getElementById("screen-assembly"),
    briefing: document.getElementById("screen-briefing"),
    game: document.getElementById("screen-game"),
    result: document.getElementById("screen-result"),
};

const refs = {
    runtimeBadge: document.getElementById("runtime-badge"),
    boardBadge: document.getElementById("board-badge"),
    sessionChip: document.getElementById("session-chip"),
    runtimeErrorModal: document.getElementById("runtime-error-modal"),
    runtimeErrorTitle: document.getElementById("runtime-error-title"),
    runtimeErrorBody: document.getElementById("runtime-error-body"),
    btnRuntimeRetry: document.getElementById("btn-runtime-retry"),
    btnRuntimeDismiss: document.getElementById("btn-runtime-dismiss"),
    startTagline: document.getElementById("start-tagline"),
    btnBegin: document.getElementById("btn-begin"),
    btnAssemblyBack: document.getElementById("btn-assembly-back"),
    btnAssemblyNext: document.getElementById("btn-assembly-next"),
    btnBriefingBack: document.getElementById("btn-briefing-back"),
    btnStartRuntime: document.getElementById("btn-start-runtime"),
    btnStopRuntime: document.getElementById("btn-stop-runtime"),
    btnToggleDebug: document.getElementById("btn-toggle-debug"),
    btnResultRestart: document.getElementById("btn-result-restart"),
    btnResultBack: document.getElementById("btn-result-back"),
    selectionSummary: document.getElementById("selection-summary"),
    partyGrid: document.getElementById("party-grid"),
    briefingTitle: document.getElementById("briefing-title"),
    briefingIntro: document.getElementById("briefing-intro"),
    briefingStakes: document.getElementById("briefing-stakes"),
    briefingPoints: document.getElementById("briefing-points"),
    briefingObjectives: document.getElementById("briefing-objectives"),
    topScenario: document.getElementById("top-scenario"),
    topMap: document.getElementById("top-map"),
    topChapter: document.getElementById("top-chapter"),
    topObjective: document.getElementById("top-objective"),
    teamList: document.getElementById("team-list"),
    initiativeList: document.getElementById("initiative-list"),
    objectiveList: document.getElementById("objective-list"),
    transitionList: document.getElementById("transition-list"),
    journalList: document.getElementById("journal-list"),
    debugList: document.getElementById("debug-list"),
    actionChannel: document.getElementById("action-channel"),
    actionTitle: document.getElementById("action-title"),
    actionPriority: document.getElementById("action-priority"),
    actionSummary: document.getElementById("action-summary"),
    actionBody: document.getElementById("action-body"),
    actionDetails: document.getElementById("action-details"),
    actionDetailsBody: document.getElementById("action-details-body"),
    actionProgress: document.getElementById("action-progress"),
    actionProgressLabel: document.getElementById("action-progress-label"),
    actionProgressValue: document.getElementById("action-progress-value"),
    actionProgressBar: document.getElementById("action-progress-bar"),
    promptMeta: document.getElementById("prompt-meta"),
    rollBreakdown: document.getElementById("roll-breakdown"),
    choiceList: document.getElementById("choice-list"),
    choiceDetail: document.getElementById("choice-detail"),
    choiceDetailTitle: document.getElementById("choice-detail-title"),
    choiceDetailBody: document.getElementById("choice-detail-body"),
    promptForm: document.getElementById("prompt-form"),
    promptInput: document.getElementById("prompt-input"),
    promptSubmit: document.getElementById("prompt-submit"),
    naturalControls: document.getElementById("natural-controls"),
    resultTitle: document.getElementById("result-title"),
    resultSummary: document.getElementById("result-summary"),
    resultObjectives: document.getElementById("result-objectives"),
};

const CHOICE_SECTION_LABELS = {
    movement: "Ruch i eksploracja",
    combat: "Walka",
    generic: "Akcje ogólne",
    heritage: "Dziedzictwo",
    class: "Akcje klasowe",
    utility: "Zarządzanie",
    turn: "Tura",
};

const CHOICE_SECTION_ORDER = ["movement", "combat", "generic", "heritage", "class", "utility", "turn"];

const state = {
    screen: "start",
    catalog: { heroes: [], scenarios: [] },
    scenario: null,
    selectedHeroIds: [],
    sessionId: null,
    runtimeStatus: { state: "idle", scenario_id: null, hero_ids: [] },
    heroes: new Map(),
    initiative: { round: null, order: [], active_id: null },
    activeActor: null,
    currentPrompt: null,
    currentPromptId: null,
    promptQueue: [],
    journal: [],
    debug: [],
    latestCard: null,
    currentMapId: null,
    currentMapLabel: null,
    completedObjectives: new Set(),
    scenarioFinished: false,
    eventSource: null,
    runtimePoll: null,
    debugOpen: false,
    naturalMode: "none",
    lastIdleHint: null,
    selectedChoiceIndex: -1,
    promptDrafts: new Map(),
    lastRenderedPromptId: null,
    dismissedRuntimeErrorKey: null,
};

function escapeHtml(text) {
    return String(text || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function markdownish(text) {
    const lines = String(text || "").split(/\n+/).map((line) => line.trim()).filter(Boolean);
    if (!lines.length) return "";
    return lines
        .map((line) => {
            const safe = escapeHtml(line)
                .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                .replace(/`(.+?)`/g, "<code>$1</code>");
            return `<p>${safe}</p>`;
        })
        .join("");
}

function _isUpNavigationKey(event) {
    const key = String(event?.key || "");
    const code = String(event?.code || "");
    return key === "8" || key === "ArrowUp" || code === "Numpad8";
}

function _isDownNavigationKey(event) {
    const key = String(event?.key || "");
    const code = String(event?.code || "");
    return key === "2" || key === "ArrowDown" || code === "Numpad2";
}

function dedupeCardText(title, summaryCandidate, bodyCandidate) {
    const normalizedTitle = String(title || "").trim();
    const normalizedSummary = String(summaryCandidate || "").trim();
    const normalizedBody = String(bodyCandidate || "").trim();
    return {
        title,
        summary: normalizedSummary && normalizedSummary !== normalizedTitle ? summaryCandidate : "",
        body:
            normalizedBody && normalizedBody !== normalizedTitle && normalizedBody !== normalizedSummary
                ? bodyCandidate
                : "",
    };
}

function signedNumber(value) {
    const numeric = Number(value || 0);
    return numeric >= 0 ? `+${numeric}` : String(numeric);
}

function humanizeActionId(actionId) {
    const text = String(actionId || "").replaceAll("_", " ").trim();
    if (!text) return "Wynik akcji";
    return text.charAt(0).toUpperCase() + text.slice(1);
}

function actionResultCard(payload) {
    const actionId = String(payload.action_id || "");
    const actor = payload.actor?.name || "Aktor";
    const target = payload.target?.name || "cel";
    const damage = Number(payload.damage || 0);
    const summary = String(payload.summary || payload.message || "").trim();

    if (!actionId || actionId.endsWith("_pre")) return null;

    if (actionId === "damage_applied" && damage > 0) {
        return {
            title: "Obrażenia",
            body: `${actor} zadaje ${damage} obrażeń celowi ${target}.`,
            communication: {
                channel: "action",
                priority: "result",
                semantic_type: "result",
                title: "Obrażenia",
                body_markdown: `${actor} zadaje **${damage}** obrażeń celowi ${target}.`,
            },
        };
    }

    if (actionId.endsWith("_concealed_miss")) {
        return {
            title: "Pudło",
            body: `${actor} chybia cel ${target} przez concealed.`,
            communication: {
                channel: "action",
                priority: "result",
                semantic_type: "result",
                title: "Pudło",
                body_markdown: `${actor} chybia cel **${target}** przez concealed.`,
            },
        };
    }

    if (actionId.endsWith("_wrong_square")) {
        return {
            title: "Chybiony strzał",
            body: `${actor} oddaje strzał, ale wskazuje błędne pole.`,
            communication: {
                channel: "action",
                priority: "result",
                semantic_type: "result",
                title: "Chybiony strzał",
                body_markdown: `${actor} oddaje strzał, ale wskazuje błędne pole.`,
            },
        };
    }

    if (actionId.endsWith("_miss")) {
        const ac = payload.target_ac != null ? ` przeciw AC ${payload.target_ac}` : "";
        return {
            title: "Pudło",
            body: `${actor} nie trafia celu ${target}${ac}.`,
            communication: {
                channel: "action",
                priority: "result",
                semantic_type: "result",
                title: "Pudło",
                body_markdown: `${actor} nie trafia celu **${target}**${ac}.`,
            },
        };
    }

    if (typeof payload.critical === "boolean" || typeof payload.damage === "number") {
        const title = payload.critical ? "Trafienie krytyczne" : "Trafienie";
        const damageLine = damage > 0 ? ` Zadaje ${damage} obrażeń.` : "";
        return {
            title,
            body: `${actor} trafia cel ${target}.${damageLine}`.trim(),
            communication: {
                channel: "action",
                priority: "result",
                semantic_type: "result",
                title,
                body_markdown: `${actor} trafia cel **${target}**.${damageLine}`.trim(),
            },
        };
    }

    if (summary) {
        return {
            title: humanizeActionId(actionId),
            body: summary,
            communication: {
                channel: "action",
                priority: "result",
                semantic_type: "result",
                title: humanizeActionId(actionId),
                body_markdown: summary,
            },
        };
    }

    return null;
}

function setScreen(name) {
    state.screen = name;
    Object.entries(screens).forEach(([key, node]) => {
        if (!node) return;
        node.classList.toggle("screen-active", key === name);
    });
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });
    const payload = await response.json();
    if (!response.ok || payload.ok === false) {
        throw new Error(payload.error || `Request failed: ${url}`);
    }
    return payload;
}

function scenarioConfig() {
    return state.catalog.scenarios[0] || null;
}

function objectiveOrder() {
    const scenario = scenarioConfig();
    if (!scenario) return [];
    return [...(scenario.primary_objectives || []), ...(scenario.optional_objectives || [])];
}

function activeObjective() {
    const scenario = scenarioConfig();
    if (!scenario) return null;
    for (const objective of scenario.primary_objectives || []) {
        if (!state.completedObjectives.has(objective.id)) return objective;
    }
    for (const objective of scenario.optional_objectives || []) {
        if (!state.completedObjectives.has(objective.id)) return objective;
    }
    return null;
}

function mapChapterById(mapId) {
    const scenario = scenarioConfig();
    if (!scenario) return null;
    return (scenario.chapters || []).find((item) => item.map_id === mapId) || null;
}

function mapChapterByLabel(label) {
    const scenario = scenarioConfig();
    if (!scenario) return null;
    return (scenario.chapters || []).find((item) => item.label === label) || null;
}

function updateHeroSelection(heroId) {
    const current = new Set(state.selectedHeroIds);
    if (current.has(heroId)) current.delete(heroId);
    else if (current.size < 4) current.add(heroId);
    state.selectedHeroIds = Array.from(current);
    renderAssembly();
}

function renderAssembly() {
    refs.partyGrid.innerHTML = "";
    if (!state.catalog.heroes.length) {
        refs.partyGrid.innerHTML = `<div class="empty-state">Brak zapisanych bohaterów w <code>data/heroes</code>.</div>`;
        refs.btnAssemblyNext.disabled = true;
        refs.selectionSummary.textContent = "Brak dostępnych postaci.";
        return;
    }
    state.catalog.heroes.forEach((hero) => {
        const selected = state.selectedHeroIds.includes(hero.id);
        const card = document.createElement("article");
        card.className = `party-card${selected ? " selected" : ""}`;
        const skills = Array.isArray(hero.trained_skills) && hero.trained_skills.length
            ? hero.trained_skills.slice(0, 3).join(", ")
            : "Brak danych";
        const traits = Array.isArray(hero.key_traits) && hero.key_traits.length
            ? hero.key_traits.slice(0, 4).join(", ")
            : "Brak wyróżnionych cech";
        card.innerHTML = `
            <div class="portrait" style="background-image:url('${hero.portrait || "/static/placeholder.png"}')"></div>
            <div>
                <div class="party-name">${escapeHtml(hero.name)}</div>
                <div class="party-subtitle">${escapeHtml((hero.class_id || "-").replaceAll("_", " "))} · ${escapeHtml((hero.ancestry_id || "-").replaceAll("_", " "))}</div>
            </div>
            <div class="party-meta">
                <span>HP ${hero.hp ?? "-"}</span>
                <span>AC ${hero.ac ?? "-"}</span>
                <span>Speed ${hero.speed ?? "-"}</span>
            </div>
            <div class="party-summary">${escapeHtml(hero.summary || "")}</div>
            <div class="party-summary"><strong>Skills:</strong> ${escapeHtml(skills)}</div>
            <div class="party-summary"><strong>Cechy:</strong> ${escapeHtml(traits)}</div>
        `;
        card.addEventListener("click", () => updateHeroSelection(hero.id));
        refs.partyGrid.appendChild(card);
    });
    refs.btnAssemblyNext.disabled = state.selectedHeroIds.length === 0;
    refs.selectionSummary.textContent =
        state.selectedHeroIds.length > 0
            ? `Wybrano ${state.selectedHeroIds.length} bohaterów.`
            : "Wybierz od 1 do 4 bohaterów.";
}

function renderBriefing() {
    const scenario = scenarioConfig();
    if (!scenario) return;
    refs.briefingTitle.textContent = scenario.briefing_title || scenario.title || "Misja";
    refs.briefingIntro.textContent = scenario.briefing_intro || "";
    refs.briefingStakes.textContent = scenario.stakes || "";
    refs.briefingPoints.innerHTML = "";
    (scenario.briefing_points || []).forEach((line) => {
        const li = document.createElement("li");
        li.textContent = line;
        refs.briefingPoints.appendChild(li);
    });
    refs.briefingObjectives.innerHTML = "";
    objectiveOrder().forEach((objective) => {
        const li = document.createElement("li");
        li.textContent = `${objective.label}: ${objective.description}`;
        refs.briefingObjectives.appendChild(li);
    });
}

function renderRuntimeBadge() {
    const runtimeState = String(state.runtimeStatus.state || "idle");
    const boardBackend = String(state.runtimeStatus.board_backend || "").trim().toLowerCase();
    refs.runtimeBadge.textContent = runtimeState;
    refs.runtimeBadge.className = "badge";
    if (runtimeState === "running" || runtimeState === "starting") refs.runtimeBadge.classList.add("badge-running");
    else if (runtimeState === "error") refs.runtimeBadge.classList.add("badge-error");
    else refs.runtimeBadge.classList.add("badge-idle");

    refs.boardBadge.className = "badge";
    if (boardBackend === "hardware") {
        refs.boardBadge.textContent = "Board: Hardware";
        refs.boardBadge.classList.add("badge-hardware");
    } else if (boardBackend === "simulator") {
        refs.boardBadge.textContent = "Board: Simulator";
        refs.boardBadge.classList.add("badge-simulator");
    } else {
        refs.boardBadge.textContent = "Board: -";
        refs.boardBadge.classList.add("badge-idle");
    }
    refs.sessionChip.textContent = `Session: ${state.sessionId || "-"}`;
}

function currentRuntimeErrorKey() {
    const error = String(state.runtimeStatus.error || "").trim();
    const status = String(state.runtimeStatus.state || "");
    if (!error || status !== "error") return null;
    return [
        status,
        error,
        state.runtimeStatus.scenario_id || "",
        state.runtimeStatus.started_at || "",
        state.runtimeStatus.stopped_at || "",
    ].join("|");
}

function formatRuntimeError() {
    const raw = String(state.runtimeStatus.error || "").trim();
    const boardBackend = String(state.runtimeStatus.board_backend || "").trim().toLowerCase();
    if (/timed out/i.test(raw) && (/wled/i.test(raw) || /json\/info/i.test(raw) || boardBackend === "hardware")) {
        return {
            title: "Połączenie z LED-ami nie odpowiada",
            body:
                "Runtime nie mógł połączyć się z kontrolerem WLED. Sprawdź zasilanie, adres IP i sieć planszy, a potem użyj „Ponów połączenie”. "
                + "Restart uruchomi ponownie ten sam scenariusz z ostatnią konfiguracją drużyny.",
        };
    }
    return {
        title: "Runtime zatrzymał się z błędem",
        body: raw || "Proces gry zakończył się błędem. Spróbuj ponowić uruchomienie.",
    };
}

function renderRuntimeErrorModal() {
    const errorKey = currentRuntimeErrorKey();
    const shouldShow = Boolean(errorKey) && state.dismissedRuntimeErrorKey !== errorKey;
    refs.runtimeErrorModal.classList.toggle("hidden", !shouldShow);
    if (!shouldShow) return;
    const details = formatRuntimeError();
    refs.runtimeErrorTitle.textContent = details.title;
    refs.runtimeErrorBody.textContent = details.body;
}

function normalizePrompt(prompt) {
    if (!prompt) return null;
    return {
        id: String(prompt.id),
        kind: String(prompt.kind || "info"),
        title: prompt.title || prompt.prompt || "Prompt",
        prompt: prompt.prompt || "",
        subtitle: prompt.subtitle || "",
        prompt_long: prompt.prompt_long || "",
        choices: Array.isArray(prompt.choices) ? prompt.choices : [],
        choice_meta: Array.isArray(prompt.choice_meta) ? prompt.choice_meta : [],
        communication: prompt.communication || {},
        layout: prompt.layout || "info",
        source: prompt.source || "",
        status: prompt.status || "pending",
        answer_placeholder: prompt.answer_placeholder || "",
        modifiers: prompt.modifiers || null,
        roll_stack: prompt.roll_stack || null,
        action_desc: prompt.action_desc || "",
        desc: prompt.desc || "",
    };
}

function chooseCurrentPrompt() {
    const next = state.promptQueue.find((item) => item.status !== "answered") || null;
    const previousId = state.currentPromptId;
    state.currentPrompt = next;
    state.currentPromptId = next ? next.id : null;
    if (state.currentPromptId !== previousId) {
        state.selectedChoiceIndex = -1;
    }
}

function recordCard(entry) {
    state.latestCard = entry;
}

function addJournalEntry(kind, title, body, communication = {}, raw = {}) {
    const entry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        kind,
        title: title || "Wpis",
        body: body || "",
        communication,
        raw,
    };
    if (communication.debug_only || communication.priority === "debug") {
        state.debug.unshift(entry);
        state.debug = state.debug.slice(0, 30);
        return;
    }
    state.journal.unshift(entry);
    state.journal = state.journal.slice(0, 40);
    if (communication.priority !== "debug") recordCard(entry);
}

function inferScenarioStateFromText(text) {
    const normalized = String(text || "").toLowerCase();
    if (!normalized) return;
    if (normalized.includes("sekretne przejście") || normalized.includes("sekretne przejscie")) {
        state.completedObjectives.add("find_secret_passage");
    }
    if (normalized.includes("podziemnych doków") || normalized.includes("podziemnych dokow") || normalized.includes("smuggler docks")) {
        state.completedObjectives.add("reach_smuggler_docks");
    }
    if (normalized.includes("ostatni strażnicy doków") || normalized.includes("ostatni straznicy dokow") || normalized.includes("statek przemytników stoi bez załogi") || normalized.includes("statek przemytnikow stoi bez zalogi")) {
        state.completedObjectives.add("clear_smuggler_docks");
    }
    if (normalized.includes("odbijasz od brzegu") || normalized.includes("scenariusz zakończony") || normalized.includes("scenariusz zakonczony")) {
        state.completedObjectives.add("escape_on_ship");
        state.scenarioFinished = true;
    }
}

function handleMapEntry(label) {
    const chapter = mapChapterByLabel(label);
    if (!chapter) return;
    state.currentMapId = chapter.map_id;
    state.currentMapLabel = chapter.label;
}

function handleEvent(event) {
    const payload = event.payload || {};
    if (event.type === "session_reset") {
        state.heroes.clear();
        state.promptQueue = [];
        state.currentPrompt = null;
        state.currentPromptId = null;
        state.initiative = { round: null, order: [], active_id: null };
        state.activeActor = null;
        state.journal = [];
        state.debug = [];
        state.latestCard = null;
        state.lastIdleHint = null;
        state.promptDrafts.clear();
        state.lastRenderedPromptId = null;
        state.currentMapId = null;
        state.currentMapLabel = null;
        state.completedObjectives = new Set();
        state.scenarioFinished = false;
        state.sessionId = event.session_id || state.sessionId;
        renderAll();
        return;
    }

    if (event.type === "prompt") {
        const normalized = normalizePrompt(payload);
        if (normalized) {
            state.promptQueue.push(normalized);
            chooseCurrentPrompt();
        }
        renderAll();
        return;
    }

    if (event.type === "prompt_answered") {
        const promptId = String(payload.id || "");
        state.promptQueue = state.promptQueue.map((item) => item.id === promptId ? { ...item, status: "answered" } : item);
        chooseCurrentPrompt();
        renderAll();
        return;
    }

    if (event.type === "hero_snapshot") {
        state.heroes.set(String(payload.id || payload.name || Math.random()), payload);
        renderAll();
        return;
    }

    if (event.type === "initiative") {
        state.initiative = {
            round: payload.round ?? null,
            order: Array.isArray(payload.order) ? payload.order : [],
            active_id: payload.active_id ?? null,
        };
        renderAll();
        return;
    }

    if (event.type === "active_actor_changed") {
        state.activeActor = payload;
        renderAll();
        return;
    }

    if (event.type === "idle_hint") {
        state.lastIdleHint = {
            title: payload.title || "Wskazówka",
            body: payload.text || "",
            communication: {
                channel: "idle_hint",
                priority: "info",
                title: payload.title || "Wskazówka",
                body_markdown: payload.text || "",
                summary: payload.text || payload.title || "",
            },
        };
    }

    if (event.type === "action") {
        const card = actionResultCard(payload);
        if (card) {
            addJournalEntry("action", card.title, card.body, card.communication, payload);
            renderAll();
        }
        return;
    }

    if (["log", "info", "idle_hint"].includes(event.type)) {
        const communication = payload.communication || {};
        const title = communication.title || payload.title || payload.tag || event.type;
        const body = communication.body_markdown || payload.message || payload.text || "";
        addJournalEntry(event.type, title, body, communication, payload);
        const mapMatch = String(payload.message || payload.text || "").match(/Wejście na mapę:\s*(.+?)\.?$/i);
        if (mapMatch && mapMatch[1]) handleMapEntry(mapMatch[1].trim());
        inferScenarioStateFromText(body || title);
        renderAll();
    }
}

function connectStream() {
    if (state.eventSource) state.eventSource.close();
    const source = new EventSource("/stream");
    source.onmessage = (message) => {
        try {
            const event = JSON.parse(message.data);
            handleEvent(event);
        } catch (_error) {
            // ignore malformed chunks
        }
    };
    state.eventSource = source;
}

async function loadInitialState() {
    const [sessionPayload, catalogPayload, promptPayload, runtimePayload] = await Promise.all([
        fetchJson("/api/session"),
        fetchJson("/api/catalog"),
        fetchJson("/api/prompts"),
        fetchJson("/api/runtime/status"),
    ]);
    state.sessionId = sessionPayload.session?.id || null;
    state.catalog = catalogPayload.catalog || { heroes: [], scenarios: [] };
    state.scenario = state.catalog.scenarios[0] || null;
    state.promptQueue = (promptPayload.prompts || []).map(normalizePrompt).filter(Boolean);
    chooseCurrentPrompt();
    state.runtimeStatus = runtimePayload.runtime_status || state.runtimeStatus;
    if (state.scenario) refs.startTagline.textContent = state.scenario.tagline || refs.startTagline.textContent;
    renderAll();
}

function activeCardData() {
    if (state.currentPrompt) {
        const prompt = state.currentPrompt;
        const communication = prompt.communication || {};
        const title = communication.title || prompt.title || prompt.prompt || "Prompt";
        const summaryCandidate = communication.summary || prompt.subtitle || prompt.prompt || "";
        const bodyCandidate = communication.body_markdown || prompt.prompt_long || "";
        const deduped = dedupeCardText(title, summaryCandidate, bodyCandidate);
        return {
            title: deduped.title,
            summary: deduped.summary,
            body: deduped.body,
            details: communication.details_markdown || "",
            communication,
            prompt,
        };
    }
    if (state.lastIdleHint) {
        const deduped = dedupeCardText(
            state.lastIdleHint.title,
            state.lastIdleHint.communication.summary || state.lastIdleHint.body || "",
            state.lastIdleHint.body || "",
        );
        return {
            title: deduped.title,
            summary: deduped.summary,
            body: deduped.body,
            details: "",
            communication: state.lastIdleHint.communication || {},
            prompt: null,
        };
    }
    if (state.latestCard) {
        const deduped = dedupeCardText(
            state.latestCard.title,
            state.latestCard.communication.summary || state.latestCard.body || "",
            state.latestCard.communication.body_markdown || state.latestCard.body || "",
        );
        return {
            title: deduped.title,
            summary: deduped.summary,
            body: deduped.body,
            details: state.latestCard.communication.details_markdown || "",
            communication: state.latestCard.communication || {},
            prompt: null,
        };
    }
    return {
        title: "Czekam na wydarzenia",
        summary: "Po uruchomieniu scenariusza centralna karta pokaże bieżące instrukcje dla gracza.",
        body: "",
        details: "",
        communication: { channel: "ready", priority: "info" },
        prompt: null,
    };
}

function renderActionCard() {
    const card = activeCardData();
    const communication = card.communication || {};
    refs.actionChannel.textContent = String(communication.channel || "ready");
    refs.actionTitle.textContent = card.title || "Czekam na wydarzenia";
    refs.actionPriority.textContent = String(communication.priority || "info");
    refs.actionPriority.className = "badge";
    if (communication.priority === "action") refs.actionPriority.classList.add("badge-action");
    else if (communication.priority === "result") refs.actionPriority.classList.add("badge-result");
    else if (communication.priority === "debug") refs.actionPriority.classList.add("badge-debug");
    else refs.actionPriority.classList.add("badge-idle");
    refs.actionSummary.textContent = card.summary || "";
    refs.actionSummary.classList.toggle("hidden", !card.summary);
    refs.actionBody.innerHTML = markdownish(card.body);
    refs.actionBody.classList.toggle("hidden", !card.body);
    refs.actionDetailsBody.innerHTML = markdownish(card.details);
    refs.actionDetails.classList.toggle("hidden", !card.details);

    const progress = communication.progress || null;
    const current = Number(progress?.current ?? 0);
    const total = Number(progress?.total ?? 0);
    const percentage = total > 0 ? Math.max(0, Math.min(100, Math.round((current / total) * 100))) : 0;
    refs.actionProgress.classList.toggle("hidden", !progress || total <= 0);
    refs.actionProgressLabel.textContent = progress?.label || "Postęp";
    refs.actionProgressValue.textContent = total > 0 ? `${current}/${total}` : "0/0";
    refs.actionProgressBar.style.width = `${percentage}%`;

    refs.promptMeta.textContent = card.prompt
        ? [card.prompt.kind, card.prompt.source].filter(Boolean).join(" · ")
        : "";

    renderPrompt(card.prompt);
}

function promptChoices(prompt) {
    if (!prompt) return [];
    if (prompt.choice_meta.length) {
        return prompt.choice_meta.map((item, index) => ({
            id: item.raw || String(index),
            label: item.label || item.raw || `Opcja ${index + 1}`,
            desc: item.desc || "",
            raw: item.raw || item.label || String(index),
            category: item.category || "",
            icon: item.icon || "",
            key: item.key || "",
        }));
    }
    return prompt.choices.map((item, index) => ({
        id: String(index),
        label: String(item),
        desc: "",
        raw: String(item),
        category: "",
        icon: "",
        key: "",
    }));
}

function _modifierBucketTotal(modifiers, bonusKey, penaltyKey) {
    const bonuses = Array.isArray(modifiers?.[bonusKey]) ? modifiers[bonusKey] : [];
    const penalties = Array.isArray(modifiers?.[penaltyKey]) ? modifiers[penaltyKey] : [];
    const plus = bonuses.reduce((acc, row) => acc + Math.abs(Number(row?.value || 0)), 0);
    const minus = penalties.reduce((acc, row) => acc + Math.abs(Number(row?.value || 0)), 0);
    return plus - minus;
}

function buildRollBreakdown(prompt) {
    if (!prompt) return null;
    const layout = String(prompt.layout || "").toLowerCase();
    const isRollPrompt = prompt.kind === "roll" || layout === "test" || layout === "damage";
    if (!isRollPrompt) return null;

    const stack = prompt.roll_stack && typeof prompt.roll_stack === "object" ? prompt.roll_stack : {};
    const components = [];
    const seeded = Array.isArray(stack.components) ? stack.components : [];

    if (seeded.length) {
        seeded.forEach((row, index) => {
            components.push({
                id: String(row?.id || `component_${index + 1}`),
                label: String(row?.label || `Składnik ${index + 1}`),
                value: Number(row?.value || 0),
                description: String(row?.description || row?.desc || ""),
            });
        });
    } else if (prompt.modifiers && typeof prompt.modifiers === "object") {
        [
            ["circumstance", "Okoliczności", "Premie i kary circumstance.", "bonCirc", "penCirc"],
            ["status", "Status", "Premie i kary status.", "bonStat", "penStat"],
            ["item", "Przedmiot", "Premie i kary item.", "bonItem", "penItem"],
        ].forEach(([id, label, description, bonusKey, penaltyKey]) => {
            const value = _modifierBucketTotal(prompt.modifiers, bonusKey, penaltyKey);
            if (!value) return;
            components.push({ id, label, value, description });
        });
    }

    const componentsTotal = components.reduce((acc, row) => acc + Number(row.value || 0), 0);
    const autoTotal = stack.auto_total_modifier == null ? componentsTotal : Number(stack.auto_total_modifier || 0);
    if (autoTotal !== componentsTotal) {
        components.push({
            id: "other_auto",
            label: "Pozostałe",
            value: autoTotal - componentsTotal,
            description: "Pozostały automatyczny modyfikator z mechaniki gry.",
        });
    }
    const total = components.reduce((acc, row) => acc + Number(row.value || 0), 0);
    if (!components.length) return null;
    return {
        title: layout === "damage" ? "Składniki obrażeń" : "Składniki modyfikatora",
        total,
        components,
    };
}

function renderRollBreakdown(prompt) {
    const breakdown = buildRollBreakdown(prompt);
    if (!breakdown) {
        refs.rollBreakdown.innerHTML = "";
        refs.rollBreakdown.classList.add("hidden");
        return;
    }
    refs.rollBreakdown.innerHTML = `
        <div class="roll-breakdown-head">
            <span>${escapeHtml(breakdown.title)}</span>
            <strong>${escapeHtml(signedNumber(breakdown.total))}</strong>
        </div>
        <div class="roll-breakdown-list">
            ${breakdown.components.map((row) => `
                <article class="roll-breakdown-item">
                    <div class="roll-breakdown-row">
                        <strong>${escapeHtml(row.label)}</strong>
                        <span>${escapeHtml(signedNumber(row.value))}</span>
                    </div>
                    <div class="roll-breakdown-note">${escapeHtml(row.description || "")}</div>
                </article>
            `).join("")}
        </div>
    `;
    refs.rollBreakdown.classList.remove("hidden");
}

function ensureSelectedChoiceIndex(choices) {
    if (!choices.length) {
        state.selectedChoiceIndex = -1;
        return;
    }
    if (state.selectedChoiceIndex < 0 || state.selectedChoiceIndex >= choices.length) {
        state.selectedChoiceIndex = 0;
    }
}

function updateChoiceSelectionUI() {
    const buttons = refs.choiceList.querySelectorAll(".choice-btn");
    buttons.forEach((button, index) => {
        const selected = index === state.selectedChoiceIndex;
        button.classList.toggle("selected", selected);
        if (selected) {
            button.scrollIntoView({ block: "nearest", inline: "nearest" });
        }
    });
    renderSelectedChoiceDetail();
}

function moveSelectedChoice(delta) {
    const choices = promptChoices(state.currentPrompt);
    if (!choices.length) return;
    ensureSelectedChoiceIndex(choices);
    const length = choices.length;
    state.selectedChoiceIndex = (state.selectedChoiceIndex + delta + length) % length;
    updateChoiceSelectionUI();
}

function submitSelectedChoice() {
    const choices = promptChoices(state.currentPrompt);
    if (!choices.length) return;
    ensureSelectedChoiceIndex(choices);
    const choice = choices[state.selectedChoiceIndex];
    if (!choice) return;
    answerPrompt(choice.raw).catch((error) => window.alert(error.message));
}

function orderedChoiceSections(choices) {
    const buckets = new Map();
    choices.forEach((choice) => {
        const category = String(choice.category || "").trim().toLowerCase() || "uncategorized";
        if (!buckets.has(category)) buckets.set(category, []);
        buckets.get(category).push(choice);
    });
    const ordered = [];
    CHOICE_SECTION_ORDER.forEach((category) => {
        if (buckets.has(category)) {
            ordered.push([category, buckets.get(category)]);
            buckets.delete(category);
        }
    });
    Array.from(buckets.keys()).sort().forEach((category) => {
        ordered.push([category, buckets.get(category)]);
    });
    return ordered;
}

function createChoiceButton(choice) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "choice-btn";
    const category = String(choice.category || "").trim().toLowerCase();
    if (category) button.classList.add(`choice-cat-${category}`);
    const key = choice.key ? `<span class="choice-key">${escapeHtml(choice.key)}</span>` : "";
    const icon = choice.icon ? `<span class="choice-icon">${escapeHtml(choice.icon)}</span>` : "";
    const desc = choice.desc ? `<span>${escapeHtml(choice.desc)}</span>` : "";
    button.innerHTML = `
        <div class="choice-btn-head">
            <div class="choice-btn-title">${icon}<strong>${escapeHtml(choice.label)}</strong></div>
            ${key}
        </div>
        ${desc}
    `;
    button.addEventListener("click", () => {
        const choices = promptChoices(state.currentPrompt);
        const nextIndex = choices.findIndex((entry) => entry.raw === choice.raw);
        if (nextIndex >= 0) {
            state.selectedChoiceIndex = nextIndex;
            updateChoiceSelectionUI();
        }
        answerPrompt(choice.raw);
    });
    return button;
}

function renderSelectedChoiceDetail() {
    const choices = promptChoices(state.currentPrompt);
    if (!choices.length) {
        refs.choiceDetail.classList.add("hidden");
        refs.choiceDetailTitle.textContent = "";
        refs.choiceDetailBody.innerHTML = "";
        return;
    }
    ensureSelectedChoiceIndex(choices);
    const choice = choices[state.selectedChoiceIndex];
    if (!choice) {
        refs.choiceDetail.classList.add("hidden");
        refs.choiceDetailTitle.textContent = "";
        refs.choiceDetailBody.innerHTML = "";
        return;
    }
    refs.choiceDetailTitle.textContent = choice.label || "Opcja";
    refs.choiceDetailBody.innerHTML = markdownish(choice.desc || "Brak dodatkowego opisu tej opcji.");
    refs.choiceDetail.classList.remove("hidden");
}

async function answerPrompt(answer) {
    if (!state.currentPromptId) return;
    const promptId = state.currentPromptId;
    await fetchJson(`/api/prompts/${promptId}/response`, {
        method: "POST",
        body: JSON.stringify({ answer }),
    });
    state.promptDrafts.delete(promptId);
    state.promptQueue = state.promptQueue.map((item) => item.id === promptId ? { ...item, status: "answered", answer } : item);
    state.naturalMode = "none";
    state.selectedChoiceIndex = -1;
    chooseCurrentPrompt();
    renderAll();
}

function renderPrompt(prompt) {
    refs.choiceList.innerHTML = "";
    refs.choiceDetail.classList.add("hidden");
    refs.choiceDetailTitle.textContent = "";
    refs.choiceDetailBody.innerHTML = "";
    refs.rollBreakdown.innerHTML = "";
    refs.rollBreakdown.classList.add("hidden");
    refs.promptForm.classList.add("hidden");
    refs.naturalControls.classList.add("hidden");
    refs.promptInput.classList.remove("hidden");
    refs.promptSubmit.textContent = "Potwierdź";
    if (!prompt) {
        refs.promptInput.value = "";
        state.lastRenderedPromptId = null;
        return;
    }

    const promptChanged = state.lastRenderedPromptId !== prompt.id;
    const savedDraft = state.promptDrafts.get(prompt.id) || "";
    if (refs.promptInput.value !== savedDraft) {
        refs.promptInput.value = savedDraft;
    }
    state.lastRenderedPromptId = prompt.id;

    const choices = promptChoices(prompt);
    if (choices.length) {
        ensureSelectedChoiceIndex(choices);
        const hasCategories = choices.some((choice) => String(choice.category || "").trim());
        let renderedIndex = 0;
        if (hasCategories) {
            orderedChoiceSections(choices).forEach(([category, sectionChoices]) => {
                if (category !== "uncategorized") {
                    const header = document.createElement("div");
                    header.className = `choice-section-head cat-${category}`;
                    header.textContent = CHOICE_SECTION_LABELS[category] || category;
                    refs.choiceList.appendChild(header);
                }
                sectionChoices.forEach((choice) => {
                    const button = createChoiceButton(choice);
                    button.dataset.choiceIndex = String(renderedIndex);
                    refs.choiceList.appendChild(button);
                    renderedIndex += 1;
                });
            });
        } else {
            choices.forEach((choice) => {
                const button = createChoiceButton(choice);
                button.dataset.choiceIndex = String(renderedIndex);
                refs.choiceList.appendChild(button);
                renderedIndex += 1;
            });
        }
        updateChoiceSelectionUI();
    } else {
        state.selectedChoiceIndex = -1;
    }

    const needsInput = prompt.kind === "roll" || (!choices.length && prompt.kind !== "info");
    const isConfirmOnly = prompt.kind === "info" && !choices.length;
    if (needsInput || isConfirmOnly) {
        refs.promptForm.classList.remove("hidden");
        refs.promptInput.classList.toggle("hidden", isConfirmOnly);
        refs.promptInput.placeholder = prompt.kind === "roll"
            ? (prompt.answer_placeholder || "Wpisz wynik rzutu...")
            : "Wpisz odpowiedź...";
        refs.naturalControls.classList.toggle("hidden", prompt.kind !== "roll");
        refs.promptSubmit.textContent = isConfirmOnly ? "Potwierdź (Enter)" : "Potwierdź";
        if (promptChanged) {
            queueMicrotask(() => {
                if (isConfirmOnly) refs.promptSubmit.focus();
                else refs.promptInput.focus();
            });
        }
    }
    renderRollBreakdown(prompt);
}

function renderObjectives() {
    const items = objectiveOrder();
    if (!items.length) {
        refs.objectiveList.innerHTML = `<div class="empty-state">Brak danych o celach.</div>`;
        return;
    }
    const active = activeObjective();
    refs.objectiveList.innerHTML = items.map((objective) => {
        const done = state.completedObjectives.has(objective.id);
        const activeClass = active && active.id === objective.id ? " active" : "";
        const title = done ? `✓ ${objective.label}` : objective.label;
        return `
            <article class="objective-item${activeClass}">
                <strong>${escapeHtml(title)}</strong>
                <p>${escapeHtml(objective.description || "")}</p>
            </article>
        `;
    }).join("");
}

function currentTeamEntries() {
    return Array.from(state.heroes.values()).sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "pl"));
}

function renderTeam() {
    const entries = currentTeamEntries();
    if (!entries.length) {
        refs.teamList.innerHTML = `<div class="empty-state">Brak danych o drużynie.</div>`;
        return;
    }
    refs.teamList.innerHTML = entries.map((hero) => {
        const active = String(hero.id || "") === String(state.activeActor?.id || "");
        const hp = hero.max_hp && hero.wounds != null ? Math.max(0, Number(hero.max_hp) - Number(hero.wounds || 0)) : hero.max_hp;
        const tags = Array.isArray(hero.statuses) ? hero.statuses.slice(0, 4).join(", ") : "";
        return `
            <article class="team-card${active ? " active" : ""}">
                <strong>${escapeHtml(hero.name || hero.id || "Hero")}</strong>
                <div class="team-meta">
                    <span>${escapeHtml((hero.class_id || "-").replaceAll("_", " "))}</span>
                    <span>HP ${hp ?? "-"}</span>
                    <span>AC ${hero.ac ?? "-"}</span>
                    <span>Speed ${hero.speed_feet ?? hero.base_speed_feet ?? "-"}</span>
                </div>
                <div class="team-note">${escapeHtml(tags || hero.note || "")}</div>
            </article>
        `;
    }).join("");
}

function renderInitiative() {
    if (!Array.isArray(state.initiative.order) || !state.initiative.order.length) {
        refs.initiativeList.innerHTML = `<div class="empty-state">Brak aktywnej inicjatywy.</div>`;
        return;
    }
    refs.initiativeList.innerHTML = state.initiative.order.map((entry, index) => {
        const active = String(entry.id || "") === String(state.initiative.active_id || "");
        const label = entry.name || entry.id || `Actor ${index + 1}`;
        const current = entry.current ?? entry.effective_initiative ?? entry.initiative ?? null;
        const base = entry.base ?? entry.initiative ?? null;
        const delta = Number.isFinite(entry.delta) ? Number(entry.delta) : null;
        const score = current ?? base ?? "-";
        const modifier = delta === null || delta === 0 ? "" : ` (${delta > 0 ? "+" : ""}${delta})`;
        return `
            <article class="initiative-entry${active ? " active" : ""}">
                <strong class="initiative-order">${index + 1}. ${escapeHtml(label)}</strong>
                <div class="initiative-line">Init ${escapeHtml(score)}${escapeHtml(modifier)}</div>
            </article>
        `;
    }).join("");
}

function renderTransitions() {
    const scenario = scenarioConfig();
    if (!scenario || !state.currentMapId) {
        refs.transitionList.innerHTML = `<div class="empty-state">Brak danych o przejściach.</div>`;
        return;
    }
    const transitions = (scenario.transitions || {})[state.currentMapId] || [];
    if (!transitions.length) {
        refs.transitionList.innerHTML = `<div class="empty-state">Brak jawnych przejść dla tej mapy.</div>`;
        return;
    }
    refs.transitionList.innerHTML = transitions.map((line) => `<div class="transition-item">${escapeHtml(line)}</div>`).join("");
}

function renderJournal() {
    if (!state.journal.length) {
        refs.journalList.innerHTML = `<div class="empty-state">Brak wpisów.</div>`;
    } else {
        refs.journalList.innerHTML = state.journal.map((entry) => `
            <article class="journal-entry">
                <strong>${escapeHtml(entry.title)}</strong>
                <small>${escapeHtml(entry.kind)}</small>
                <div>${markdownish(entry.body || "")}</div>
            </article>
        `).join("");
    }
    if (!state.debug.length) {
        refs.debugList.innerHTML = `<div class="empty-state">Brak wpisów debug.</div>`;
    } else {
        refs.debugList.innerHTML = state.debug.map((entry) => `
            <article class="debug-entry">
                <strong>${escapeHtml(entry.title)}</strong>
                <small>${escapeHtml(entry.kind)}</small>
                <div>${markdownish(entry.body || "")}</div>
            </article>
        `).join("");
    }
    refs.debugList.classList.toggle("hidden", !state.debugOpen);
    refs.btnToggleDebug.textContent = state.debugOpen ? "Ukryj" : "Pokaż";
}

function renderTopbar() {
    const scenario = scenarioConfig();
    const chapter = state.currentMapId ? mapChapterById(state.currentMapId) : null;
    const objective = activeObjective();
    refs.topScenario.textContent = scenario?.title || "Bandit Cave";
    refs.topMap.textContent = state.currentMapLabel || "-";
    refs.topChapter.textContent = chapter?.chapter_title || "-";
    refs.topObjective.textContent = objective?.label || (state.scenarioFinished ? "Scenariusz zakończony" : "-");
}

function renderResult() {
    const scenario = scenarioConfig();
    refs.resultTitle.textContent = scenario?.result_title || "Scenariusz zakończony";
    refs.resultSummary.textContent = scenario?.result_summary || "Drużyna zakończyła scenariusz.";
    refs.resultObjectives.innerHTML = objectiveOrder().map((objective) => {
        const done = state.completedObjectives.has(objective.id);
        return `<div class="objective-item${done ? " active" : ""}"><strong>${done ? "✓" : "•"} ${escapeHtml(objective.label)}</strong><p>${escapeHtml(objective.description || "")}</p></div>`;
    }).join("");
}

function renderAll() {
    renderRuntimeBadge();
    renderRuntimeErrorModal();
    renderAssembly();
    renderBriefing();
    renderTopbar();
    renderActionCard();
    renderTeam();
    renderInitiative();
    renderObjectives();
    renderTransitions();
    renderJournal();
    renderResult();
}

async function startRuntime() {
    refs.btnStartRuntime.disabled = true;
    try {
        state.dismissedRuntimeErrorKey = null;
        const payload = await fetchJson("/api/runtime/start", {
            method: "POST",
            body: JSON.stringify({
                scenario_id: "bandit_cave",
                hero_ids: state.selectedHeroIds,
            }),
        });
        state.sessionId = payload.session_id;
        state.runtimeStatus = payload.runtime_status || state.runtimeStatus;
        setScreen("game");
        renderAll();
    } finally {
        refs.btnStartRuntime.disabled = false;
    }
}

async function stopRuntime() {
    const payload = await fetchJson("/api/runtime/stop", { method: "POST", body: JSON.stringify({}) });
    state.runtimeStatus = payload.runtime_status || state.runtimeStatus;
    renderAll();
}

async function retryRuntime() {
    refs.btnRuntimeRetry.disabled = true;
    try {
        state.dismissedRuntimeErrorKey = null;
        const payload = await fetchJson("/api/runtime/retry", { method: "POST", body: JSON.stringify({}) });
        state.sessionId = payload.session_id || state.sessionId;
        state.runtimeStatus = payload.runtime_status || state.runtimeStatus;
        setScreen("game");
        renderAll();
    } finally {
        refs.btnRuntimeRetry.disabled = false;
    }
}

async function pollRuntimeStatus() {
    try {
        const payload = await fetchJson("/api/runtime/status");
        state.runtimeStatus = payload.runtime_status || state.runtimeStatus;
        if (state.runtimeStatus.session_id) state.sessionId = state.runtimeStatus.session_id;
        if ((state.runtimeStatus.state === "running" || state.runtimeStatus.state === "starting") && state.screen !== "game" && !state.scenarioFinished) {
            setScreen("game");
        }
        if (state.runtimeStatus.state === "stopped" && state.scenarioFinished) {
            setScreen("result");
        }
        renderAll();
    } catch (_error) {
        // keep previous state
    }
}

refs.btnBegin.addEventListener("click", () => setScreen("assembly"));
refs.btnAssemblyBack.addEventListener("click", () => setScreen("start"));
refs.btnAssemblyNext.addEventListener("click", () => {
    if (!state.selectedHeroIds.length) return;
    setScreen("briefing");
});
refs.btnBriefingBack.addEventListener("click", () => setScreen("assembly"));
refs.btnStartRuntime.addEventListener("click", () => startRuntime().catch((error) => window.alert(error.message)));
refs.btnStopRuntime.addEventListener("click", () => stopRuntime().catch((error) => window.alert(error.message)));
refs.btnRuntimeRetry.addEventListener("click", () => retryRuntime().catch((error) => window.alert(error.message)));
refs.btnRuntimeDismiss.addEventListener("click", () => {
    state.dismissedRuntimeErrorKey = currentRuntimeErrorKey();
    renderAll();
});
refs.btnToggleDebug.addEventListener("click", () => {
    state.debugOpen = !state.debugOpen;
    renderJournal();
});
refs.btnResultRestart.addEventListener("click", async () => {
    await stopRuntime().catch(() => null);
    setScreen("assembly");
});
refs.btnResultBack.addEventListener("click", async () => {
    await stopRuntime().catch(() => null);
    setScreen("start");
});

refs.promptForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!state.currentPrompt) return;
    if (state.currentPrompt.kind === "info" && !state.currentPrompt.choices.length) {
        answerPrompt("ok").catch((error) => window.alert(error.message));
        return;
    }
    const raw = refs.promptInput.value.trim();
    if (!raw && state.currentPrompt.kind !== "roll") return;
    if (state.currentPrompt.kind === "roll") {
        if (!raw) {
            refs.promptInput.focus();
            return;
        }
        const parsed = Number.parseInt(raw, 10);
        if (Number.isNaN(parsed)) return;
        answerPrompt({ roll: parsed, raw_roll: parsed, natural_mode: state.naturalMode }).catch((error) => window.alert(error.message));
        return;
    }
    answerPrompt(raw).catch((error) => window.alert(error.message));
});

refs.promptInput.addEventListener("input", () => {
    if (!state.currentPromptId) return;
    state.promptDrafts.set(state.currentPromptId, refs.promptInput.value);
});

document.addEventListener("keydown", (event) => {
    if (state.screen !== "game") return;
    if (!state.currentPrompt) return;
    if (_isUpNavigationKey(event)) {
        const target = event.target;
        const isTypingTarget = target instanceof HTMLInputElement && !target.classList.contains("hidden");
        if (!isTypingTarget && promptChoices(state.currentPrompt).length) {
            event.preventDefault();
            moveSelectedChoice(-1);
        }
        return;
    }
    if (_isDownNavigationKey(event)) {
        const target = event.target;
        const isTypingTarget = target instanceof HTMLInputElement && !target.classList.contains("hidden");
        if (!isTypingTarget && promptChoices(state.currentPrompt).length) {
            event.preventDefault();
            moveSelectedChoice(1);
        }
        return;
    }
    if (event.key !== "Enter") return;
    const target = event.target;
    if (target instanceof HTMLTextAreaElement) return;
    if (state.currentPrompt.kind === "info" && !state.currentPrompt.choices.length) {
        event.preventDefault();
        answerPrompt("ok").catch((error) => window.alert(error.message));
        return;
    }
    const isTypingTarget = target instanceof HTMLInputElement && !target.classList.contains("hidden");
    if (!isTypingTarget && promptChoices(state.currentPrompt).length) {
        event.preventDefault();
        submitSelectedChoice();
    }
});

refs.naturalControls.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
        const next = button.dataset.natural || "none";
        state.naturalMode = state.naturalMode === next ? "none" : next;
        refs.naturalControls.querySelectorAll("button").forEach((node) => {
            node.classList.toggle("active", node.dataset.natural === state.naturalMode);
        });
    });
});

await loadInitialState();
connectStream();
state.runtimePoll = window.setInterval(() => {
    pollRuntimeStatus();
}, 2000);
