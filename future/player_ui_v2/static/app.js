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
    actionScene: document.getElementById("action-scene"),
    actionSceneBody: document.getElementById("action-scene-body"),
    actionHelp: document.getElementById("action-help"),
    actionHelpBody: document.getElementById("action-help-body"),
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
    view: {
        sessionId: null,
        revision: 0,
        activePrompt: null,
        focusCard: null,
        idleState: null,
        journal: [],
        debugFeed: [],
    },
    currentMapId: null,
    currentMapLabel: null,
    completedObjectives: new Set(),
    scenarioFinished: false,
    eventSource: null,
    runtimePoll: null,
    debugOpen: false,
    naturalMode: "none",
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

function inlineMarkdown(text) {
    return escapeHtml(text)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/`(.+?)`/g, "<code>$1</code>");
}

function markdownish(text) {
    const lines = String(text || "").replace(/\r/g, "").split("\n");
    const blocks = [];
    let paragraph = [];
    let list = [];

    const flushParagraph = () => {
        if (!paragraph.length) return;
        blocks.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
        paragraph = [];
    };

    const flushList = () => {
        if (!list.length) return;
        blocks.push(`<ul>${list.map((item) => `<li>${inlineMarkdown(item)}</li>`).join("")}</ul>`);
        list = [];
    };

    lines.forEach((line) => {
        const trimmed = String(line || "").trim();
        if (!trimmed) {
            flushParagraph();
            flushList();
            return;
        }
        const heading = trimmed.match(/^#{1,3}\s+(.+)$/);
        if (heading) {
            flushParagraph();
            flushList();
            blocks.push(`<h3>${inlineMarkdown(heading[1])}</h3>`);
            return;
        }
        const bullet = trimmed.match(/^[-*]\s+(.+)$/);
        if (bullet) {
            flushParagraph();
            list.push(bullet[1]);
            return;
        }
        flushList();
        paragraph.push(trimmed);
    });

    flushParagraph();
    flushList();
    return blocks.join("");
}

function normalizedText(text) {
    return String(text || "").replace(/\s+/g, " ").trim();
}

function sameMeaning(a, b) {
    const left = normalizedText(a);
    const right = normalizedText(b);
    return Boolean(left) && left === right;
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
        prompt_key: String(prompt.prompt_key || prompt.communication?.context?.prompt_key || ""),
        kind: String(prompt.kind || "info"),
        title: prompt.title || prompt.prompt || "Prompt",
        prompt: prompt.prompt || prompt.title || "",
        subtitle: prompt.subtitle || prompt.summary || "",
        prompt_long: prompt.prompt_long || prompt.body_markdown || "",
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
        details_markdown: prompt.details_markdown || "",
        summary: prompt.summary || "",
        scope_key: prompt.scope_key || "",
    };
}

function normalizeCard(card) {
    if (!card) return null;
    return {
        id: String(card.id || ""),
        prompt_key: String(card.prompt_key || card.communication?.context?.prompt_key || ""),
        seq: Number(card.seq || 0),
        kind: String(card.kind || "narration"),
        title: card.title || "Karta",
        summary: card.summary || "",
        body_markdown: card.body_markdown || "",
        details_markdown: card.details_markdown || "",
        priority: card.priority || "info",
        scope_key: card.scope_key || "system",
        dedupe_key: card.dedupe_key || "",
        communication: card.communication || {},
    };
}

function promptDisplayId(item) {
    if (!item) return "";
    const stable = String(item.prompt_key || item.communication?.context?.prompt_key || "").trim();
    const instanceId = String(item.id || "").trim();
    if (stable && instanceId) return `ID: ${stable} · #${instanceId}`;
    if (stable) return `ID: ${stable}`;
    if (instanceId) return `#${instanceId}`;
    return "";
}

function syncViewState(viewState) {
    const previousPromptId = state.view.activePrompt?.id || null;
    state.view = {
        sessionId: viewState?.session_id || null,
        revision: Number(viewState?.revision || 0),
        activePrompt: normalizePrompt(viewState?.active_prompt),
        focusCard: normalizeCard(viewState?.focus_card),
        idleState: normalizeCard(viewState?.idle_state),
        journal: Array.isArray(viewState?.journal) ? viewState.journal.map(normalizeCard).filter(Boolean) : [],
        debugFeed: Array.isArray(viewState?.debug_feed) ? viewState.debug_feed.map(normalizeCard).filter(Boolean) : [],
    };
    if (state.view.sessionId) {
        state.sessionId = state.view.sessionId;
    }
    const nextPromptId = state.view.activePrompt?.id || null;
    if (previousPromptId !== nextPromptId) {
        state.selectedChoiceIndex = -1;
    }
    state.completedObjectives = new Set();
    state.scenarioFinished = false;
    state.view.journal.forEach((entry) => {
        inferScenarioStateFromText([entry.title, entry.summary, entry.body_markdown].filter(Boolean).join("\n"));
    });
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
        syncViewState(null);
        state.initiative = { round: null, order: [], active_id: null };
        state.activeActor = null;
        state.promptDrafts.clear();
        state.lastRenderedPromptId = null;
        state.currentMapId = null;
        state.currentMapLabel = null;
        state.completedObjectives = new Set();
        state.scenarioFinished = false;
        state.sessionId = event.session_id || state.sessionId;
        renderAll();
        queueMicrotask(() => {
            refreshViewState().catch(() => {});
        });
        return;
    }

    if (event.type === "view_state") {
        syncViewState(payload);
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

    if (["log", "info", "narration", "idle_hint"].includes(event.type)) {
        const mapMatch = String(payload.message || payload.text || "").match(/Wejście na mapę:\s*(.+?)\.?$/i);
        if (mapMatch && mapMatch[1]) handleMapEntry(mapMatch[1].trim());
        inferScenarioStateFromText(String(payload.message || payload.text || ""));
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
    const [viewPayload, catalogPayload, runtimePayload] = await Promise.all([
        fetchJson("/api/view-state"),
        fetchJson("/api/catalog"),
        fetchJson("/api/runtime/status"),
    ]);
    state.sessionId = viewPayload.session?.id || null;
    state.catalog = catalogPayload.catalog || { heroes: [], scenarios: [] };
    state.scenario = state.catalog.scenarios[0] || null;
    syncViewState(viewPayload.view_state || null);
    state.runtimeStatus = runtimePayload.runtime_status || state.runtimeStatus;
    if (state.scenario) refs.startTagline.textContent = state.scenario.tagline || refs.startTagline.textContent;
    renderAll();
}

async function refreshViewState() {
    const payload = await fetchJson("/api/view-state");
    state.sessionId = payload.session?.id || state.sessionId;
    syncViewState(payload.view_state || null);
    renderAll();
}

function activeCardData() {
    if (state.view.activePrompt) {
        const prompt = state.view.activePrompt;
        const communication = prompt.communication || {};
        const title = communication.title || prompt.title || prompt.prompt || "Prompt";
        const summaryCandidate = communication.summary || prompt.summary || prompt.subtitle || prompt.prompt || "";
        const bodyCandidate = communication.body_markdown || prompt.prompt_long || "";
        const deduped = dedupeCardText(title, summaryCandidate, bodyCandidate);
        const focusCard = state.view.focusCard;
        let details = communication.details_markdown || prompt.details_markdown || "";
        if (!details && focusCard) {
            details = [focusCard.title, focusCard.body_markdown || focusCard.details_markdown || ""].filter(Boolean).join("\n\n");
        }
        return {
            title: deduped.title,
            summary: deduped.summary,
            body: deduped.body,
            details,
            communication,
            prompt,
        };
    }
    if (state.view.focusCard) {
        const card = state.view.focusCard;
        const deduped = dedupeCardText(
            card.title,
            card.summary || "",
            card.body_markdown || "",
        );
        return {
            title: deduped.title,
            summary: deduped.summary,
            body: deduped.body,
            details: card.details_markdown || "",
            communication: card.communication || {},
            prompt: null,
        };
    }
    if (state.view.idleState) {
        const idle = state.view.idleState;
        return {
            title: idle.title,
            summary: idle.summary || "",
            body: idle.body_markdown || "",
            details: idle.details_markdown || "",
            communication: idle.communication || {},
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

function derivedInstructionText(card) {
    const prompt = card.prompt;
    const communication = card.communication || {};
    const cta = String(communication.cta || "").trim();
    if (cta) return cta;
    const continueHint = String(communication.context?.continue || "").trim();
    if (continueHint) return continueHint;
    if (!prompt) {
        if (String(communication.semantic_type || "").toLowerCase() === "result") {
            return "Zapoznaj się z wynikiem bieżącej akcji.";
        }
        return "";
    }
    if (prompt.kind === "choice") {
        return promptChoices(prompt).length
            ? "Wybierz jedną z dostępnych opcji."
            : "Wpisz odpowiedź i zatwierdź ją, aby kontynuować.";
    }
    if (prompt.kind === "roll") {
        return "Wpisz wynik rzutu i zatwierdź go, aby rozliczyć akcję.";
    }
    if (prompt.kind === "info") {
        return "Przeczytaj komunikat i potwierdź, aby przejść dalej.";
    }
    return "Wpisz odpowiedź i zatwierdź ją, aby kontynuować.";
}

function promptCommandLines(prompt) {
    if (!prompt) return [];
    if (isBoardScanCancelPrompt(prompt)) {
        return [
            "**Kliknij `Anuluj`**, jeśli chcesz przerwać bieżący wybór na planszy.",
            "**`Esc`** anuluje bieżący wybór.",
        ];
    }
    if (prompt.kind === "choice" && promptChoices(prompt).length) {
        const lines = [
            "**`8` / `2` albo strzałki** zmieniają zaznaczenie.",
            "**`Enter`** zatwierdza aktualną opcję.",
            "**Kliknięcie opcji** zatwierdza ją od razu.",
        ];
        if (promptCancelChoice(prompt)) {
            lines.push("**`Esc`** anuluje bieżący wybór.");
        }
        return lines;
    }
    if (prompt.kind === "roll") {
        return [
            "**Wpisz wynik rzutu** w polu odpowiedzi.",
            "**`Enter`** wysyła wynik do gry.",
            "**`Nat 20`** i **`Nat 1`** oznaczają wynik naturalny.",
        ];
    }
    if (prompt.kind === "info") {
        return ["**`Enter`** potwierdza komunikat i przechodzi do kolejnego kroku."];
    }
    return [
        "**Wpisz odpowiedź** w polu tekstowym.",
        "**`Enter`** zatwierdza odpowiedź.",
    ];
}

function promptCommandSummary(prompt) {
    if (!prompt) return "";
    if (isBoardScanCancelPrompt(prompt)) {
        return "Esc anuluje skan planszy.";
    }
    if (prompt.kind === "choice" && promptChoices(prompt).length) {
        const hasCancel = Boolean(promptCancelChoice(prompt));
        return hasCancel
            ? "8/2 lub strzałki: wybór · Enter: zatwierdź · Esc: anuluj"
            : "8/2 lub strzałki: wybór · Enter: zatwierdź";
    }
    if (prompt.kind === "roll") {
        return "Wpisz wynik · Enter: wyślij · Nat 20/Nat 1: wynik naturalny";
    }
    if (prompt.kind === "info") {
        return "Enter: dalej";
    }
    return "Enter: zatwierdź";
}

function shouldShowCommandHelp(card, details, nextLines) {
    const prompt = card.prompt;
    if (!prompt) return false;
    return Boolean(details || nextLines.length || promptCommandLines(prompt).length);
}

function buildActionHelp(card, instructionLead) {
    const communication = card.communication || {};
    const blocks = [];
    const details = String(card.details || "").trim();
    if (details) blocks.push(details);

    const nextLines = [];
    const nextHint = String(communication.context?.next || "").trim();
    const continueHint = String(communication.context?.continue || "").trim();
    if (nextHint) nextLines.push(nextHint);
    if (continueHint && !sameMeaning(continueHint, instructionLead)) nextLines.push(continueHint);
    if (nextLines.length) {
        blocks.push(`### Dalej\n${nextLines.map((line) => `- ${line}`).join("\n")}`);
    }

    const commands = promptCommandLines(card.prompt);
    if (commands.length && shouldShowCommandHelp(card, details, nextLines)) {
        blocks.push(`### Komendy\n${commands.map((line) => `- ${line}`).join("\n")}`);
    }
    return blocks.join("\n\n").trim();
}

function buildActionSections(card) {
    const summary = String(card.summary || "").trim();
    let body = String(card.body || "").trim();
    const instructionLead = derivedInstructionText(card);

    if (!body && instructionLead && !sameMeaning(summary, instructionLead)) {
        body = instructionLead;
    } else if (body && instructionLead && !sameMeaning(body, instructionLead) && !sameMeaning(summary, instructionLead)) {
        body = `${body}\n\n**Dalej:** ${instructionLead}`;
    }

    let scene = summary;
    if (!scene) {
        scene = body;
        body = "";
    } else if (body && !sameMeaning(summary, body)) {
        scene = `${summary}\n\n${body}`;
        body = "";
    }

    const help = buildActionHelp(card, instructionLead);
    return { scene, help };
}

function renderActionCard() {
    const card = activeCardData();
    const communication = card.communication || {};
    const sections = buildActionSections(card);
    refs.actionChannel.textContent = String(communication.channel || "ready");
    refs.actionTitle.textContent = card.title || "Czekam na wydarzenia";
    refs.actionPriority.textContent = String(communication.priority || "info");
    refs.actionPriority.className = "badge";
    if (communication.priority === "action") refs.actionPriority.classList.add("badge-action");
    else if (communication.priority === "result") refs.actionPriority.classList.add("badge-result");
    else if (communication.priority === "debug") refs.actionPriority.classList.add("badge-debug");
    else refs.actionPriority.classList.add("badge-idle");
    refs.actionSceneBody.innerHTML = markdownish(sections.scene);
    refs.actionScene.classList.toggle("hidden", !sections.scene);
    refs.actionHelpBody.innerHTML = markdownish(sections.help);
    refs.actionHelp.classList.toggle("hidden", !sections.help);

    const progress = communication.progress || null;
    const current = Number(progress?.current ?? 0);
    const total = Number(progress?.total ?? 0);
    const percentage = total > 0 ? Math.max(0, Math.min(100, Math.round((current / total) * 100))) : 0;
    refs.actionProgress.classList.toggle("hidden", !progress || total <= 0);
    refs.actionProgressLabel.textContent = progress?.label || "Postęp";
    refs.actionProgressValue.textContent = total > 0 ? `${current}/${total}` : "0/0";
    refs.actionProgressBar.style.width = `${percentage}%`;

    const metaParts = [];
    const displayId = promptDisplayId(card.prompt || card);
    if (displayId) metaParts.push(displayId);
    if (card.prompt) metaParts.push(promptCommandSummary(card.prompt));
    refs.promptMeta.textContent = metaParts.filter(Boolean).join(" · ");

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

function promptCancelChoice(prompt) {
    const choices = promptChoices(prompt);
    return choices.find((choice) => {
        const raw = String(choice.raw || "").trim().toLowerCase();
        const label = String(choice.label || "").trim().toLowerCase();
        return raw.includes("cancel") || raw.includes("anuluj") || label.includes("anuluj");
    }) || null;
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
    const choices = promptChoices(state.view.activePrompt);
    if (!choices.length) return;
    ensureSelectedChoiceIndex(choices);
    const length = choices.length;
    state.selectedChoiceIndex = (state.selectedChoiceIndex + delta + length) % length;
    updateChoiceSelectionUI();
}

function submitSelectedChoice() {
    const choices = promptChoices(state.view.activePrompt);
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
        const choices = promptChoices(state.view.activePrompt);
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
    const choices = promptChoices(state.view.activePrompt);
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
    const promptId = state.view.activePrompt?.id;
    if (!promptId) return;
    await fetchJson(`/api/prompts/${promptId}/response`, {
        method: "POST",
        body: JSON.stringify({ answer }),
    });
    state.promptDrafts.delete(promptId);
    const refreshed = await fetchJson("/api/view-state");
    syncViewState(refreshed.view_state || null);
    state.naturalMode = "none";
    state.selectedChoiceIndex = -1;
    renderAll();
}

function submitCancelChoice() {
    const cancelChoice = promptCancelChoice(state.view.activePrompt);
    if (!cancelChoice) return false;
    answerPrompt(cancelChoice.raw).catch((error) => window.alert(error.message));
    return true;
}

function isBoardScanCancelPrompt(prompt) {
    return String(prompt?.source || "").trim().toLowerCase() === "board_scan_cancel";
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
        const wounds = Number.isFinite(Number(entry.wounds)) ? Number(entry.wounds) : null;
        const maxHp = Number.isFinite(Number(entry.max_hp)) ? Number(entry.max_hp) : null;
        const woundLine = wounds === null ? "" : `Rany ${escapeHtml(maxHp ? `${wounds}/${maxHp}` : String(wounds))}`;
        const statuses = Array.isArray(entry.statuses)
            ? entry.statuses.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 4)
            : [];
        const statusLine = statuses.length ? statuses.join(", ") : "";
        return `
            <article class="initiative-entry${active ? " active" : ""}">
                <strong class="initiative-order">${index + 1}. ${escapeHtml(label)}</strong>
                <div class="initiative-line">Init ${escapeHtml(score)}${escapeHtml(modifier)}</div>
                ${woundLine ? `<div class="initiative-line">${woundLine}</div>` : ""}
                ${statusLine ? `<div class="initiative-line">${escapeHtml(statusLine)}</div>` : ""}
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
    if (!state.view.journal.length) {
        refs.journalList.innerHTML = `<div class="empty-state">Brak wpisów.</div>`;
    } else {
        refs.journalList.innerHTML = state.view.journal.map((entry) => `
            <article class="journal-entry">
                <div class="journal-entry-head">
                    <strong>${escapeHtml(entry.title)}</strong>
                    <small>${escapeHtml(entry.kind)}</small>
                </div>
                ${promptDisplayId(entry) ? `<div class="journal-entry-id">${escapeHtml(promptDisplayId(entry))}</div>` : ""}
                ${entry.summary ? `<div class="journal-entry-summary">${escapeHtml(entry.summary)}</div>` : ""}
                ${entry.body_markdown ? `<div class="journal-entry-body">${markdownish(entry.body_markdown || "")}</div>` : ""}
            </article>
        `).join("");
    }
    if (!state.view.debugFeed.length) {
        refs.debugList.innerHTML = `<div class="empty-state">Brak wpisów debug.</div>`;
    } else {
        refs.debugList.innerHTML = state.view.debugFeed.map((entry) => `
            <article class="debug-entry">
                <strong>${escapeHtml(entry.title)}</strong>
                <small>${escapeHtml(entry.kind)}</small>
                ${promptDisplayId(entry) ? `<div class="journal-entry-id">${escapeHtml(promptDisplayId(entry))}</div>` : ""}
                <div>${markdownish(entry.body_markdown || "")}</div>
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
    if (!state.view.activePrompt) return;
    if (state.view.activePrompt.kind === "info" && !state.view.activePrompt.choices.length) {
        answerPrompt("ok").catch((error) => window.alert(error.message));
        return;
    }
    const raw = refs.promptInput.value.trim();
    if (!raw && state.view.activePrompt.kind !== "roll") return;
    if (state.view.activePrompt.kind === "roll") {
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
    const promptId = state.view.activePrompt?.id;
    if (!promptId) return;
    state.promptDrafts.set(promptId, refs.promptInput.value);
});

document.addEventListener("keydown", (event) => {
    if (state.screen !== "game") return;
    if (!state.view.activePrompt) return;
    if (_isUpNavigationKey(event)) {
        const target = event.target;
        const isTypingTarget = target instanceof HTMLInputElement && !target.classList.contains("hidden");
        if (!isTypingTarget && promptChoices(state.view.activePrompt).length) {
            event.preventDefault();
            moveSelectedChoice(-1);
        }
        return;
    }
    if (_isDownNavigationKey(event)) {
        const target = event.target;
        const isTypingTarget = target instanceof HTMLInputElement && !target.classList.contains("hidden");
        if (!isTypingTarget && promptChoices(state.view.activePrompt).length) {
            event.preventDefault();
            moveSelectedChoice(1);
        }
        return;
    }
    if (event.key === "Escape") {
        if (submitCancelChoice()) {
            event.preventDefault();
        }
        return;
    }
    if (event.key !== "Enter") return;
    const target = event.target;
    if (target instanceof HTMLTextAreaElement) return;
    if (isBoardScanCancelPrompt(state.view.activePrompt)) {
        return;
    }
    if (state.view.activePrompt.kind === "info" && !state.view.activePrompt.choices.length) {
        event.preventDefault();
        answerPrompt("ok").catch((error) => window.alert(error.message));
        return;
    }
    const isTypingTarget = target instanceof HTMLInputElement && !target.classList.contains("hidden");
    if (!isTypingTarget && promptChoices(state.view.activePrompt).length) {
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
