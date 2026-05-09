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
    mastheadShell: document.getElementById("masthead-shell"),
    mastheadTitle: document.getElementById("masthead-title"),
    mastheadEyebrow: document.getElementById("masthead-eyebrow"),
    mastheadSummaryStatus: document.getElementById("masthead-summary-status"),
    audioToggle: document.getElementById("audio-toggle"),
    audioVolume: document.getElementById("audio-volume"),
    audioStatus: document.getElementById("audio-status"),
    runtimeErrorModal: document.getElementById("runtime-error-modal"),
    runtimeErrorTitle: document.getElementById("runtime-error-title"),
    runtimeErrorBody: document.getElementById("runtime-error-body"),
    btnRuntimeRetry: document.getElementById("btn-runtime-retry"),
    btnRuntimeDismiss: document.getElementById("btn-runtime-dismiss"),
    startTitle: document.getElementById("start-title"),
    startTagline: document.getElementById("start-tagline"),
    startAside: document.getElementById("start-aside"),
    btnBegin: document.getElementById("btn-begin"),
    btnAssemblyBack: document.getElementById("btn-assembly-back"),
    btnDefaultParty: document.getElementById("btn-default-party"),
    btnAssemblyNext: document.getElementById("btn-assembly-next"),
    btnBriefingBack: document.getElementById("btn-briefing-back"),
    btnStartRuntime: document.getElementById("btn-start-runtime"),
    btnBoardReset: document.getElementById("btn-board-reset"),
    btnStopRuntime: document.getElementById("btn-stop-runtime"),
    btnToggleDebug: document.getElementById("btn-toggle-debug"),
    btnResultRestart: document.getElementById("btn-result-restart"),
    btnResultBack: document.getElementById("btn-result-back"),
    selectionSummary: document.getElementById("selection-summary"),
    partyGrid: document.getElementById("party-grid"),
    briefingTitle: document.getElementById("briefing-title"),
    briefingIntro: document.getElementById("briefing-intro"),
    briefingStakes: document.getElementById("briefing-stakes"),
    briefingSceneArt: document.getElementById("briefing-scene-art"),
    briefingPoints: document.getElementById("briefing-points"),
    briefingObjectives: document.getElementById("briefing-objectives"),
    topScenario: document.getElementById("top-scenario"),
    topMap: document.getElementById("top-map"),
    topChapter: document.getElementById("top-chapter"),
    topObjective: document.getElementById("top-objective"),
    adventureDrawer: document.getElementById("adventure-drawer"),
    adventureDrawerStatus: document.getElementById("adventure-drawer-status"),
    actorRailLabel: document.getElementById("actor-rail-label"),
    actorInfoBody: document.getElementById("actor-info-body"),
    teamList: document.getElementById("team-list"),
    initiativeList: document.getElementById("initiative-list"),
    objectiveList: document.getElementById("objective-list"),
    transitionList: document.getElementById("transition-list"),
    journalList: document.getElementById("journal-list"),
    debugList: document.getElementById("debug-list"),
    actionChannel: document.getElementById("action-channel"),
    actionCard: document.querySelector(".action-card"),
    actionTitle: document.getElementById("action-title"),
    actionPriority: document.getElementById("action-priority"),
    currentSceneArt: document.getElementById("current-scene-art"),
    activeActorPanel: document.getElementById("active-actor-panel"),
    activeActorPortrait: document.getElementById("active-actor-portrait"),
    activeActorName: document.getElementById("active-actor-name"),
    activeActorMeta: document.getElementById("active-actor-meta"),
    actionScene: document.getElementById("action-scene"),
    actionSceneBody: document.getElementById("action-scene-body"),
    actionHelp: document.getElementById("action-help"),
    actionHelpBody: document.getElementById("action-help-body"),
    actionProgress: document.getElementById("action-progress"),
    actionProgressLabel: document.getElementById("action-progress-label"),
    actionProgressValue: document.getElementById("action-progress-value"),
    actionProgressBar: document.getElementById("action-progress-bar"),
    promptMeta: document.getElementById("prompt-meta"),
    diceOverlay: document.getElementById("dice-overlay"),
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
    assetManifest: null,
    assetManifestUrl: "",
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
    diceRoll: null,
    diceRollTimer: null,
    audioEnabled: false,
    audioPreferenceLocked: false,
    audioVolume: 0.58,
    playedAudioCues: new Set(),
    currentAmbienceKey: "",
};

function escapeHtml(text) {
    return String(text == null ? "" : text)
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

function firstMeaningfulLine(value) {
    return String(value || "")
        .split(/\n+/)
        .map((line) => line.trim())
        .find(Boolean) || "";
}

function isGenericPromptTitle(value) {
    const text = normalizedText(value).toLowerCase();
    return ["mistrz gry", "prompt", "karta", "komunikat"].includes(text);
}

function isGenericPromptSummary(value) {
    const text = normalizedText(value).toLowerCase();
    return ["co się dzieje", "co sie dzieje", "co robić teraz", "co robic teraz"].includes(text);
}

function focusCardTitleCandidate(focusCard) {
    if (!focusCard) return "";
    const candidates = [
        focusCard.title,
        focusCard.summary,
        focusCard.body_markdown,
    ].map(firstMeaningfulLine).filter(Boolean);
    return candidates.find((candidate) => !isGenericPromptTitle(candidate) && !isGenericPromptSummary(candidate)) || "";
}

function normalizedAssetKey(value) {
    return String(value || "")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
}

function resolveAssetUrl(path) {
    const raw = String(path || "").trim();
    if (!raw) return "";
    if (/^(https?:|data:|blob:)/i.test(raw) || raw.startsWith("/")) return raw;
    const base = String(state.assetManifest?.base_path || "/assets/ui_v2/bandit_cave/").replace(/\/?$/, "/");
    return `${base}${raw.replace(/^\/+/, "")}`;
}

function assetSection(sectionName) {
    const section = state.assetManifest?.[sectionName];
    return section && typeof section === "object" ? section : {};
}

function findAssetEntry(sectionName, idOrLabel) {
    const key = normalizedAssetKey(idOrLabel);
    if (!key) return null;
    const section = assetSection(sectionName);
    if (section[key]) return section[key];
    for (const entry of Object.values(section)) {
        if (!entry || typeof entry !== "object") continue;
        if (normalizedAssetKey(entry.id) === key || normalizedAssetKey(entry.label) === key) return entry;
    }
    return null;
}

function fallbackAssetImage(kind) {
    const fallbacks = state.assetManifest?.fallbacks || {};
    const entry = fallbacks[kind] || fallbacks.choice || {};
    return resolveAssetUrl(entry.image || "/static/placeholder.png");
}

function audioEntrySource(entry) {
    if (!entry) return "";
    if (typeof entry === "string") return resolveAssetUrl(entry);
    if (typeof entry === "object") return resolveAssetUrl(entry.audio || entry.src || entry.path || "");
    return "";
}

function scenarioAudioCue(key) {
    const scenarioCue = scenarioConfig()?.audio_cues?.[key];
    if (scenarioCue) return scenarioCue;
    return findAssetEntry("narration", key) || findAssetEntry("music", key) || findAssetEntry("sfx", key);
}

function resolveChoiceImage(choice) {
    const explicit = choice.image || choice.thumbnail;
    if (explicit) return resolveAssetUrl(explicit);

    const candidates = [choice.asset_id, choice.spell_id, choice.raw, choice.id, choice.label].filter(Boolean);
    for (const candidate of candidates) {
        const spell = findAssetEntry("spells", candidate);
        if (spell?.image) return resolveAssetUrl(spell.image);
    }
    if (choice.spell_tier) {
        const spellFallback = findAssetEntry("spells", choice.spell_tier);
        if (spellFallback?.image) return resolveAssetUrl(spellFallback.image);
    }
    for (const candidate of candidates) {
        const action = findAssetEntry("actions", candidate);
        if (action?.image) return resolveAssetUrl(action.image);
    }
    const category = normalizedAssetKey(choice.category);
    if (["movement", "combat", "generic", "utility", "turn"].includes(category)) {
        return fallbackAssetImage("action");
    }
    if (category === "class" || choice.spell_id || choice.spell_tier) {
        return fallbackAssetImage("spell");
    }
    return fallbackAssetImage("choice");
}

function resolveActorImage(actor) {
    if (!actor) return fallbackAssetImage("actor");
    const explicit = actor.image || actor.portrait || actor.portrait_image;
    if (explicit) return resolveAssetUrl(explicit);
    const id = String(actor.id || actor.asset_id || "").trim();
    if (id && state.heroes.has(id)) {
        const hero = state.heroes.get(id);
        if (hero?.image) return resolveAssetUrl(hero.image);
    }
    const candidates = [actor.asset_id, actor.id, actor.name].filter(Boolean);
    const kind = normalizedAssetKey(actor.kind);
    for (const candidate of candidates) {
        const sectionName = kind === "enemy" ? "enemies" : "characters";
        const entry = findAssetEntry(sectionName, candidate) || findAssetEntry("enemies", candidate) || findAssetEntry("characters", candidate);
        if (entry?.image) return resolveAssetUrl(entry.image);
    }
    return fallbackAssetImage(kind === "enemy" ? "enemy" : "actor");
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
    const previousScreen = state.screen;
    if (previousScreen && previousScreen !== name) {
        audioManager.stopVoiceovers();
    }
    state.screen = name;
    document.body.dataset.screen = name;
    if (refs.mastheadShell) refs.mastheadShell.open = name !== "game";
    Object.entries(screens).forEach(([key, node]) => {
        if (!node) return;
        node.classList.toggle("screen-active", key === name);
    });
    updateScenarioAudio();
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

const audioManager = (() => {
    const loops = { music: null, ambience: null };
    const voiceovers = new Set();
    let enabled = false;
    let volume = state.audioVolume;

    function applyVolume(audio, multiplier = 1) {
        if (!audio) return;
        audio.volume = Math.max(0, Math.min(1, volume * multiplier));
    }

    function stopLoop(slot) {
        const current = loops[slot];
        if (current) {
            current.pause();
            current.src = "";
        }
        loops[slot] = null;
    }

    function stopVoiceovers() {
        voiceovers.forEach((audio) => {
            try {
                audio.pause();
                audio.src = "";
            } catch (_error) {
                // ignore stale audio handles
            }
        });
        voiceovers.clear();
    }

    function playLoop(slot, src, multiplier = 0.55) {
        const resolved = resolveAssetUrl(src);
        if (!enabled || !resolved) {
            stopLoop(slot);
            return;
        }
        if (loops[slot] && loops[slot]._assetSrc === resolved) {
            applyVolume(loops[slot], multiplier);
            return;
        }
        stopLoop(slot);
        const audio = new Audio(resolved);
        audio.loop = true;
        audio.preload = "auto";
        audio._assetSrc = resolved;
        applyVolume(audio, multiplier);
        loops[slot] = audio;
        audio.play().catch(() => {});
    }

    function playOneShot(src, multiplier = 0.75, { voiceover = false } = {}) {
        const resolved = resolveAssetUrl(src);
        if (!enabled || !resolved) return;
        if (voiceover) stopVoiceovers();
        const audio = new Audio(resolved);
        audio.preload = "auto";
        applyVolume(audio, multiplier);
        if (voiceover) {
            voiceovers.add(audio);
            const cleanup = () => voiceovers.delete(audio);
            audio.addEventListener("ended", cleanup, { once: true });
            audio.addEventListener("error", cleanup, { once: true });
        }
        audio.play().catch(() => {});
    }

    return {
        setEnabled(next) {
            enabled = Boolean(next);
            if (!enabled) {
                stopLoop("music");
                stopLoop("ambience");
                stopVoiceovers();
            }
        },
        setVolume(next) {
            volume = Math.max(0, Math.min(1, Number(next) || 0));
            applyVolume(loops.music, 0.55);
            applyVolume(loops.ambience, 0.5);
        },
        playLoop,
        playVoice(src) {
            playOneShot(src, 0.88, { voiceover: true });
        },
        playSfx(src) {
            playOneShot(src, 0.7);
        },
        stopVoiceovers,
    };
})();

function scenarioConfig() {
    return state.scenario || state.catalog.scenarios[0] || null;
}

function runtimeScenarioIsActive() {
    const runtimeState = String(state.runtimeStatus?.state || "").trim().toLowerCase();
    return ["starting", "running"].includes(runtimeState);
}

function playAudioCueOnce(key) {
    if (!state.audioEnabled || state.playedAudioCues.has(key)) return;
    const src = audioEntrySource(scenarioAudioCue(key));
    if (!src) return;
    state.playedAudioCues.add(key);
    audioManager.playVoice(src);
}

function playPromptAudioOnce(prompt) {
    if (!prompt || !prompt.audio) return;
    const key = `prompt:${prompt.id}:audio`;
    if (!state.audioEnabled || state.playedAudioCues.has(key)) return;
    const src = audioEntrySource(prompt.audio);
    if (!src) return;
    state.playedAudioCues.add(key);
    audioManager.playVoice(src);
}

function enableAudioFromGesture() {
    if (state.audioEnabled || state.audioPreferenceLocked) return;
    state.audioEnabled = true;
}

function updateAudioControls() {
    if (!refs.audioToggle || !refs.audioStatus) return;
    refs.audioToggle.textContent = state.audioEnabled ? "Audio on" : "Audio off";
    refs.audioStatus.textContent = state.audioEnabled ? "Audio" : "Muted";
    refs.audioStatus.className = "badge";
    refs.audioStatus.classList.add(state.audioEnabled ? "badge-running" : "badge-idle");
    if (refs.audioVolume) refs.audioVolume.value = String(Math.round(state.audioVolume * 100));
}

function updateScenarioAudio() {
    audioManager.setEnabled(state.audioEnabled);
    audioManager.setVolume(state.audioVolume);
    if (!state.audioEnabled) {
        updateAudioControls();
        return;
    }
    const musicSrc = audioEntrySource(scenarioAudioCue("music_default") || findAssetEntry("music", "default"));
    if (musicSrc) audioManager.playLoop("music", musicSrc, 0.5);
    if (state.screen === "assembly") playAudioCueOnce("party_assembly");
    if (state.screen === "briefing") playAudioCueOnce("briefing_intro");

    const ambienceKey = state.currentMapId ? `ambience_${state.currentMapId}` : "";
    if (ambienceKey && ambienceKey !== state.currentAmbienceKey) {
        state.currentAmbienceKey = ambienceKey;
        const ambienceSrc = audioEntrySource(scenarioAudioCue(ambienceKey) || findAssetEntry("music", state.currentMapId));
        if (ambienceSrc) audioManager.playLoop("ambience", ambienceSrc, 0.45);
    }
    updateAudioControls();
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

function sceneImageForMap(mapId) {
    const key = normalizedAssetKey(mapId);
    if (!key) return "";
    const scene = findAssetEntry("scenes", key);
    return scene?.image ? resolveAssetUrl(scene.image) : "";
}

function renderSceneArt(element, mapId) {
    if (!element) return;
    const image = sceneImageForMap(mapId);
    element.classList.toggle("hidden", !image);
    element.style.backgroundImage = image ? `url("${image}")` : "";
}

function updateHeroSelection(heroId) {
    const current = new Set(state.selectedHeroIds);
    if (current.has(heroId)) current.delete(heroId);
    else if (current.size < 6) current.add(heroId);
    state.selectedHeroIds = Array.from(current);
    renderAssembly();
}

function scenarioDefaultPartyIds() {
    const ids = Array.isArray(scenarioConfig()?.default_party_ids)
        ? scenarioConfig().default_party_ids
        : [];
    return ids.map((item) => String(item || "").trim().toLowerCase()).filter(Boolean);
}

function selectedPartyMatchesDefault() {
    const defaults = scenarioDefaultPartyIds();
    if (!defaults.length || defaults.length !== state.selectedHeroIds.length) return false;
    return defaults.every((heroId, index) => heroId === state.selectedHeroIds[index]);
}

function selectDefaultPartyForCurrentScenario() {
    const defaults = scenarioDefaultPartyIds();
    if (!defaults.length) return false;
    const available = new Set(state.catalog.heroes.map((hero) => String(hero.id || "").trim().toLowerCase()));
    const selected = defaults.filter((heroId) => available.has(heroId));
    if (!selected.length) return false;
    state.selectedHeroIds = selected.slice(0, 6);
    renderAssembly();
    return true;
}

function renderAssembly() {
    refs.partyGrid.innerHTML = "";
    if (!state.catalog.heroes.length) {
        refs.partyGrid.innerHTML = `<div class="empty-state">Brak zapisanych bohaterów w <code>data/heroes</code>.</div>`;
        refs.btnAssemblyNext.disabled = true;
        refs.selectionSummary.textContent = "Brak dostępnych postaci.";
        return;
    }
    const defaults = scenarioDefaultPartyIds();
    if (refs.btnDefaultParty) {
        refs.btnDefaultParty.hidden = defaults.length === 0;
        const available = new Set(state.catalog.heroes.map((hero) => String(hero.id || "").trim().toLowerCase()));
        refs.btnDefaultParty.disabled = !defaults.some((heroId) => available.has(heroId));
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
        selectedPartyMatchesDefault()
            ? `Wybrano domyślną drużynę ${scenarioConfig()?.title || "kampanii"} (${state.selectedHeroIds.length} bohaterów).`
            : state.selectedHeroIds.length > 0
            ? `Wybrano ${state.selectedHeroIds.length} bohaterów.`
            : "Wybierz od 1 do 6 bohaterów.";
}

function renderBriefing() {
    const scenario = scenarioConfig();
    if (!scenario) return;
    refs.briefingTitle.textContent = scenario.briefing_title || scenario.title || "Misja";
    refs.briefingIntro.textContent = scenario.briefing_intro || "";
    refs.briefingStakes.textContent = scenario.stakes || "";
    const firstChapter = Array.isArray(scenario.chapters) ? scenario.chapters[0] : null;
    renderSceneArt(refs.briefingSceneArt, firstChapter?.map_id || "");
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

function renderScenarioChrome() {
    const scenario = scenarioConfig();
    const title = scenario?.title || "The Game";
    const tagline = scenario?.tagline || "Wybierz scenariusz i rozpocznij grę.";
    if (refs.mastheadTitle) refs.mastheadTitle.textContent = `The Game · ${title}`;
    if (refs.mastheadEyebrow) refs.mastheadEyebrow.textContent = `The Game · ${title}`;
    if (refs.startTitle) refs.startTitle.textContent = title;
    if (refs.startTagline) refs.startTagline.textContent = tagline;
    if (refs.startAside) {
        const objective = Array.isArray(scenario?.primary_objectives) ? scenario.primary_objectives[0] : null;
        refs.startAside.textContent = objective?.description || scenario?.briefing_intro || tagline;
    }
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
    if (refs.mastheadSummaryStatus) {
        const audio = state.audioEnabled ? "audio on" : "audio off";
        const board = boardBackend ? boardBackend : "board -";
        refs.mastheadSummaryStatus.textContent = `${runtimeState} · ${board} · ${audio}`;
    }
    if (refs.btnBoardReset) {
        refs.btnBoardReset.disabled =
            !(runtimeState === "running" || runtimeState === "starting") ||
            !state.runtimeStatus.scenario_id ||
            !Array.isArray(state.runtimeStatus.hero_ids) ||
            !state.runtimeStatus.hero_ids.length;
    }
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
        audio: prompt.audio || prompt.voiceover || "",
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

function promptCompactDisplayId(item) {
    if (!item) return "";
    const instanceId = String(item.id || "").trim();
    return instanceId ? `Slajd #${instanceId}` : promptDisplayId(item);
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
        playPromptAudioOnce(state.view.activePrompt);
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
        const previousId = String(state.activeActor?.id || "");
        state.activeActor = payload;
        if (state.audioEnabled && String(payload.id || "") && String(payload.id || "") !== previousId) {
            audioManager.playSfx(audioEntrySource(scenarioAudioCue("active_actor")));
        }
        renderAll();
        return;
    }

    if (event.type === "dice_roll") {
        state.diceRoll = { ...payload, nonce: Date.now() };
        if (state.diceRollTimer) window.clearTimeout(state.diceRollTimer);
        renderDiceOverlay();
        state.diceRollTimer = window.setTimeout(() => {
            state.diceRoll = null;
            renderDiceOverlay();
        }, 3200);
        return;
    }

    if (["log", "info", "narration", "idle_hint"].includes(event.type)) {
        if (payload.audio) {
            audioManager.playVoice(audioEntrySource(payload.audio));
        }
        const mapMatch = String(payload.message || payload.text || "").match(/Wejście na mapę:\s*(.+?)\.?$/i);
        if (mapMatch && mapMatch[1]) handleMapEntry(mapMatch[1].trim());
        inferScenarioStateFromText(String(payload.message || payload.text || ""));
        if (/szczek|pies|dog/i.test(String(payload.message || payload.text || payload.summary || ""))) {
            playAudioCueOnce("hint_dog_barking");
        }
        updateScenarioAudio();
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
    state.runtimeStatus = runtimePayload.runtime_status || state.runtimeStatus;
    const activeRuntimeScenarioId = runtimeScenarioIsActive() ? state.runtimeStatus.scenario_id : "";
    const preferredScenarioId = String(
        activeRuntimeScenarioId || state.catalog.initial_scenario_id || "",
    ).trim();
    state.scenario =
        state.catalog.scenarios.find((scenario) => scenario.id === preferredScenarioId) ||
        state.catalog.scenarios[0] ||
        null;
    if (!state.selectedHeroIds.length) {
        selectDefaultPartyForCurrentScenario();
    }
    state.assetManifestUrl = String(state.scenario?.asset_manifest || "").trim();
    if (state.assetManifestUrl) {
        try {
            state.assetManifest = await fetchJson(state.assetManifestUrl);
        } catch (_error) {
            state.assetManifest = null;
        }
    }
    syncViewState(viewPayload.view_state || null);
    renderAll();
    updateScenarioAudio();
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
        const rawTitle = communication.title || prompt.title || prompt.prompt || "Prompt";
        const rawSummary = communication.summary || prompt.summary || prompt.subtitle || "";
        const focusCard = state.view.focusCard;
        const focusTitle = focusCardTitleCandidate(focusCard);
        const bodyCandidate = communication.body_markdown || prompt.prompt_long || "";
        const title = isGenericPromptTitle(rawTitle)
            ? (focusTitle || firstMeaningfulLine(bodyCandidate) || rawTitle)
            : rawTitle;
        const summaryCandidate = isGenericPromptSummary(rawSummary) || sameMeaning(rawSummary, title)
            ? ""
            : rawSummary;
        const deduped = dedupeCardText(title, summaryCandidate, bodyCandidate);
        let details = communication.details_markdown || prompt.details_markdown || "";
        if (!details && focusCard && !sameMeaning(focusTitle, deduped.title)) {
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
    if (prompt.kind === "choice" && promptChoices(prompt).length) {
        const lines = [
            "**`8` / `2` albo strzałki** zmieniają zaznaczenie.",
            "**`Enter`** zatwierdza aktualną opcję.",
            "**Kliknięcie opcji** pokazuje jej opis.",
            "**Przycisk Potwierdź** wysyła zaznaczoną opcję.",
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
    if (prompt.kind === "choice" && promptChoices(prompt).length) {
        const hasCancel = Boolean(promptCancelChoice(prompt));
        return hasCancel
            ? "8/2 lub strzałki: wybór · Enter/przycisk: zatwierdź · Esc: anuluj"
            : "8/2 lub strzałki: wybór · Enter/przycisk: zatwierdź";
    }
    if (prompt.kind === "roll") {
        return "Wpisz wynik · Enter: wyślij · Nat 20/Nat 1: wynik naturalny";
    }
    if (prompt.kind === "info") {
        return "Enter: dalej";
    }
    return "Enter: zatwierdź";
}

function isRollLikePrompt(prompt) {
    if (!prompt) return false;
    const layout = String(prompt.layout || "").toLowerCase();
    return prompt.kind === "roll" || layout === "test" || layout === "damage";
}

function isCompactPromptCard(card, sections) {
    const prompt = card?.prompt;
    if (!prompt || isRollLikePrompt(prompt) || promptChoices(prompt).length) return false;
    const mode = String(prompt.input_mode || "").trim().toLowerCase();
    if (mode && mode !== "confirm") return false;
    if (String(sections?.help || "").trim()) return false;
    if (String(sections?.disclosureBody || "").trim()) return false;
    return prompt.kind === "info" && String(sections?.scene || "").trim().length <= 900;
}

function shouldShowCommandHelp(card, details, nextLines) {
    const prompt = card.prompt;
    if (!prompt) return false;
    return Boolean(details || nextLines.length || promptCommandLines(prompt).length);
}

function nextInstructionText(card) {
    const communication = card.communication || {};
    const next = String(communication.context?.next || "").trim();
    if (!next) return "";
    const cta = String(communication.cta || "").trim();
    if (cta && sameMeaning(next, cta)) return "";
    return `**Dalej:** ${next}`;
}

function buildActionHelp(card) {
    const blocks = [];
    const next = nextInstructionText(card);
    if (next) blocks.push(next);
    const details = String(card.details || "").trim();
    if (details) blocks.push(details);
    return blocks.join("\n\n").trim();
}

function compactChoicePromptText(text) {
    const raw = String(text || "").trim();
    if (!raw) return { preview: "", full: "" };

    const maxLines = 6;
    const maxChars = 520;
    const lines = raw.split("\n");
    const kept = [];
    let charCount = 0;
    let truncated = false;

    for (const line of lines) {
        const nextCharCount = charCount + line.length + 1;
        if (kept.length >= maxLines || nextCharCount > maxChars) {
            truncated = true;
            break;
        }
        kept.push(line);
        charCount = nextCharCount;
    }

    if (!truncated) return { preview: raw, full: "" };
    const preview = kept.length ? kept.join("\n").trim() : raw.slice(0, maxChars).trim();
    return { preview: `${preview}\n\n...`, full: raw };
}

function buildActionSections(card) {
    const summary = String(card.summary || "").trim();
    let body = String(card.body || "").trim();
    const prompt = card.prompt;

    if (isRollLikePrompt(prompt)) {
        return {
            scene: summary,
            help: String(card.details || "").trim(),
            disclosureTitle: "Szczegóły rzutu",
            disclosureBody: body && !sameMeaning(body, summary) ? body : "",
        };
    }

    if (prompt?.kind === "choice" && promptChoices(prompt).length) {
        const fullScene = [
            summary,
            body && !sameMeaning(summary, body) ? body : "",
        ].filter(Boolean).join("\n\n");
        const compacted = compactChoicePromptText(fullScene);
        return {
            scene: compacted.preview,
            help: buildActionHelp(card),
            disclosureTitle: "Pełny opis",
            disclosureBody: compacted.full,
        };
    }

    let scene = summary;
    if (!scene) {
        scene = body;
        body = "";
    } else if (body && !sameMeaning(summary, body)) {
        scene = `${summary}\n\n${body}`;
        body = "";
    }

    const help = buildActionHelp(card);
    return { scene, help, disclosureTitle: "", disclosureBody: "" };
}

function activeActorEntry() {
    if (state.activeActor?.id) return state.activeActor;
    if (state.initiative.active_id && Array.isArray(state.initiative.order)) {
        return state.initiative.order.find((entry) => String(entry.id || "") === String(state.initiative.active_id || "")) || null;
    }
    return null;
}

function actorActionsLabel(actor) {
    const total = Number(actor?.actions_total);
    const used = Number(actor?.actions_used);
    const remaining = Number(actor?.actions_remaining);
    if (!Number.isFinite(total) || total <= 0) return "";
    const safeUsed = Number.isFinite(used)
        ? Math.max(0, Math.min(total, used))
        : Number.isFinite(remaining)
        ? Math.max(0, Math.min(total, total - remaining))
        : 0;
    return `Akcje ${safeUsed}/${total}`;
}

function renderActiveActorFocus() {
    if (!refs.activeActorPanel) return;
    const actor = activeActorEntry();
    if (!actor?.id) {
        refs.activeActorPanel.classList.add("hidden");
        refs.activeActorName.textContent = "-";
        refs.activeActorMeta.textContent = "";
        refs.activeActorPortrait.style.backgroundImage = "";
        return;
    }
    const image = resolveActorImage(actor);
    const kind = String(actor.kind || "").trim().toLowerCase();
    const meta = [];
    if (kind) meta.push(kind === "hero" ? "Bohater" : kind === "enemy" ? "Przeciwnik" : kind);
    if (actor.current ?? actor.effective_initiative ?? actor.initiative) {
        meta.push(`Init ${actor.current ?? actor.effective_initiative ?? actor.initiative}`);
    }
    const actions = actorActionsLabel(actor);
    if (actions) meta.push(actions);
    refs.activeActorName.textContent = actor.name || actor.id || "Aktor";
    refs.activeActorMeta.textContent = meta.join(" · ");
    refs.activeActorPortrait.style.backgroundImage = image ? `url("${image}")` : "";
    refs.activeActorPanel.classList.remove("hidden");
}

function toggleAdventureDrawer() {
    if (!refs.adventureDrawer) return;
    const nextOpen = !refs.adventureDrawer.open;
    if (nextOpen && refs.mastheadShell) refs.mastheadShell.open = true;
    refs.adventureDrawer.open = nextOpen;
}

function renderActionCard() {
    const card = activeCardData();
    const communication = card.communication || {};
    const sections = buildActionSections(card);
    const prompt = card.prompt || null;
    const compactPrompt = isCompactPromptCard(card, sections);
    refs.actionCard?.classList.toggle("prompt-roll-card", isRollLikePrompt(prompt));
    refs.actionCard?.classList.toggle("prompt-compact-card", compactPrompt);
    renderActiveActorFocus();
    refs.actionChannel.textContent = String(communication.channel || "ready");
    refs.actionTitle.textContent = card.title || "Czekam na wydarzenia";
    refs.actionPriority.textContent = String(communication.priority || "info");
    refs.actionPriority.className = "badge";
    if (communication.priority === "action") refs.actionPriority.classList.add("badge-action");
    else if (communication.priority === "result") refs.actionPriority.classList.add("badge-result");
    else if (communication.priority === "debug") refs.actionPriority.classList.add("badge-debug");
    else refs.actionPriority.classList.add("badge-idle");
    renderSceneArt(refs.currentSceneArt, state.currentMapId || "");
    const disclosureHtml = sections.disclosureBody
        ? `<details class="prompt-disclosure"><summary>${escapeHtml(sections.disclosureTitle || "Szczegóły")}</summary><div class="prose compact">${markdownish(sections.disclosureBody)}</div></details>`
        : "";
    const sceneHtml = [
        sections.scene ? markdownish(sections.scene) : "",
        disclosureHtml,
    ].filter(Boolean).join("");
    refs.actionSceneBody.innerHTML = sceneHtml;
    refs.actionScene.classList.toggle("hidden", !sceneHtml);
    const helpHtml = sections.help ? markdownish(sections.help) : "";
    refs.actionHelpBody.innerHTML = helpHtml;
    refs.actionHelp.classList.toggle("hidden", !helpHtml);

    const progress = communication.progress || null;
    const current = Number(progress?.current ?? 0);
    const total = Number(progress?.total ?? 0);
    const percentage = total > 0 ? Math.max(0, Math.min(100, Math.round((current / total) * 100))) : 0;
    refs.actionProgress.classList.toggle("hidden", !progress || total <= 0);
    refs.actionProgressLabel.textContent = progress?.label || "Postęp";
    refs.actionProgressValue.textContent = total > 0 ? `${current}/${total}` : "0/0";
    refs.actionProgressBar.style.width = `${percentage}%`;

    const metaParts = [];
    const displayId = compactPrompt ? promptCompactDisplayId(card.prompt || card) : promptDisplayId(card.prompt || card);
    if (displayId) metaParts.push(displayId);
    const commandSummary = promptCommandSummary(card.prompt);
    if (commandSummary && !compactPrompt) metaParts.push(commandSummary);
    refs.promptMeta.textContent = metaParts.filter(Boolean).join(" · ");

    renderPrompt(prompt);
}

function promptChoices(prompt) {
    if (!prompt) return [];
    if (prompt.choice_meta.length) {
        return prompt.choice_meta.map((item, index) => ({
            id: item.raw || String(index),
            label: item.label || item.raw || `Opcja ${index + 1}`,
            desc: item.desc_short || item.short_desc || item.desc || "",
            detail: item.desc || item.details_markdown || item.description || item.desc_short || item.short_desc || "",
            raw: item.raw || item.label || String(index),
            category: item.category || "",
            icon: item.icon || "",
            image: item.image || item.thumbnail || "",
            thumbnail: item.thumbnail || item.image || "",
            asset_id: item.asset_id || "",
            spell_id: item.spell_id || "",
            spell_tier: item.spell_tier || item.tier || "",
            key: item.key || "",
        }));
    }
    return prompt.choices.map((item, index) => ({
        id: String(index),
        label: String(item),
        desc: "",
        detail: "",
        raw: String(item),
        category: "",
        icon: "",
        image: "",
        thumbnail: "",
        asset_id: "",
        spell_id: "",
        spell_tier: "",
        key: "",
    }));
}

function promptCancelChoice(prompt) {
    if (prompt?.cancel_enabled) {
        const answer = String(prompt.cancel_answer || "cancel");
        const choices = promptChoices(prompt);
        return choices.find((choice) => String(choice.raw || "").trim().toLowerCase() === answer.trim().toLowerCase()) || {
            raw: answer,
            label: "Anuluj",
        };
    }
    const choices = promptChoices(prompt);
    return choices.find((choice) => {
        const raw = String(choice.raw || "").trim().toLowerCase();
        const label = String(choice.label || "").trim().toLowerCase();
        return raw.includes("cancel") || raw.includes("anuluj") || label.includes("anuluj");
    }) || null;
}

function promptConfirmEnabled(prompt) {
    return !prompt || prompt.confirm_enabled !== false;
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
    if (!isRollLikePrompt(prompt)) return null;

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
    const targetDc = [
        stack.target_dc,
        stack.dc,
        stack.target_ac,
        prompt.communication?.context?.target_dc,
        prompt.communication?.context?.dc,
        prompt.communication?.context?.target_ac,
    ].map((value) => Number(value)).find((value) => Number.isFinite(value) && value > 0) || null;
    return {
        title: layout === "damage" ? "Składniki obrażeń" : "Składniki modyfikatora",
        total,
        components,
        targetDc: layout === "damage" ? null : targetDc,
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
        ${breakdown.targetDc ? `
            <div class="roll-breakdown-note">
                DC/AC ${escapeHtml(breakdown.targetDc)}: sukces od ${escapeHtml(breakdown.targetDc)}, krytyczny sukces od ${escapeHtml(breakdown.targetDc + 10)}, krytyczna porażka przy ${escapeHtml(breakdown.targetDc - 10)} lub mniej.
            </div>
        ` : ""}
    `;
    refs.rollBreakdown.classList.remove("hidden");
}

function renderDiceOverlay() {
    if (!refs.diceOverlay) return;
    const roll = state.diceRoll;
    if (!roll) {
        refs.diceOverlay.classList.add("hidden");
        refs.diceOverlay.innerHTML = "";
        return;
    }
    const rolls = Array.isArray(roll.rolls) ? roll.rolls.map((item) => Number(item || 0)).filter((item) => Number.isFinite(item)) : [];
    const faces = rolls.length ? rolls : [Number(roll.total || 0)];
    refs.diceOverlay.innerHTML = `
        <div class="dice-copy">
            <span>${escapeHtml(roll.label || "Rzut przeciwnika")}</span>
            <strong>${escapeHtml(roll.actor_name || "Przeciwnik")}${roll.target_name ? ` -> ${escapeHtml(roll.target_name)}` : ""}</strong>
            <small>${escapeHtml(roll.formula || roll.roll_type || "k20")}</small>
        </div>
        <div class="dice-faces">
            ${faces.map((face) => `<span class="die-face">${escapeHtml(face)}</span>`).join("")}
        </div>
        <div class="dice-total">${escapeHtml(roll.total ?? "")}</div>
    `;
    refs.diceOverlay.classList.remove("hidden");
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
    if (!promptConfirmEnabled(state.view.activePrompt)) return;
    const choices = promptChoices(state.view.activePrompt);
    if (!choices.length) return;
    ensureSelectedChoiceIndex(choices);
    const choice = choices[state.selectedChoiceIndex];
    if (!choice) return;
    audioManager.playSfx(audioEntrySource(scenarioAudioCue("choice_confirm")));
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
    const image = resolveChoiceImage(choice);
    const thumb = image ? `<img class="choice-thumb" src="${escapeHtml(image)}" alt="" loading="lazy">` : "";
    const desc = choice.desc ? `<span>${escapeHtml(choice.desc)}</span>` : "";
    button.innerHTML = `
        <div class="choice-btn-head">
            <div class="choice-btn-title">${thumb}${icon}<strong>${escapeHtml(choice.label)}</strong></div>
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
    });
    button.addEventListener("dblclick", () => {
        if (!promptConfirmEnabled(state.view.activePrompt)) return;
        const choices = promptChoices(state.view.activePrompt);
        const nextIndex = choices.findIndex((entry) => entry.raw === choice.raw);
        if (nextIndex >= 0) {
            state.selectedChoiceIndex = nextIndex;
            updateChoiceSelectionUI();
        }
        audioManager.playSfx(audioEntrySource(scenarioAudioCue("choice_confirm")));
        answerPrompt(choice.raw).catch((error) => window.alert(error.message));
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
    refs.choiceDetailBody.innerHTML = markdownish(choice.detail || choice.desc || "Brak dodatkowego opisu tej opcji.");
    refs.choiceDetail.classList.remove("hidden");
}

function clearActivePromptView(promptId) {
    const activeId = state.view.activePrompt?.id || null;
    if (promptId && activeId && String(activeId) !== String(promptId)) return;
    state.view.activePrompt = null;
    state.view.focusCard = null;
    refs.promptForm.classList.add("hidden");
    refs.promptInput.value = "";
    refs.choiceList.innerHTML = "";
    refs.choiceDetail.classList.add("hidden");
    refs.choiceDetailTitle.textContent = "";
    refs.choiceDetailBody.innerHTML = "";
    refs.rollBreakdown.innerHTML = "";
    refs.rollBreakdown.classList.add("hidden");
    state.lastRenderedPromptId = null;
    state.selectedChoiceIndex = -1;
    renderAll();
}

async function answerPrompt(answer) {
    const promptId = state.view.activePrompt?.id;
    if (!promptId) return;
    const cancelAnswer = String(state.view.activePrompt?.cancel_answer || "cancel").trim().toLowerCase();
    const isCancelAnswer = String(answer || "").trim().toLowerCase() === cancelAnswer;
    if (!promptConfirmEnabled(state.view.activePrompt) && !isCancelAnswer) return;
    audioManager.stopVoiceovers();
    clearActivePromptView(promptId);
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
    requestBoardScanCancel().catch(() => null);
    return true;
}

async function requestBoardScanCancel() {
    await fetchJson("/api/runtime/cancel-scan", {
        method: "POST",
        body: JSON.stringify({ reason: "prompt_cancel" }),
    });
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
    refs.promptSubmit.disabled = false;
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

    const needsChoiceConfirm = choices.length > 0;
    const needsInput = prompt.kind === "roll" || (!choices.length && prompt.kind !== "info");
    const isConfirmOnly = prompt.kind === "info" && !choices.length;
    const confirmEnabled = promptConfirmEnabled(prompt);
    if (needsChoiceConfirm || needsInput || isConfirmOnly) {
        refs.promptForm.classList.remove("hidden");
        refs.promptInput.classList.toggle("hidden", isConfirmOnly || needsChoiceConfirm);
        refs.promptInput.placeholder = prompt.kind === "roll"
            ? (prompt.answer_placeholder || "Wpisz wynik rzutu...")
            : "Wpisz odpowiedź...";
        refs.naturalControls.classList.toggle("hidden", prompt.kind !== "roll");
        refs.promptSubmit.textContent = needsChoiceConfirm
            ? "Potwierdź wybór (Enter)"
            : isConfirmOnly
            ? "Potwierdź (Enter)"
            : "Potwierdź";
        refs.promptSubmit.disabled = !confirmEnabled;
        if (promptChanged) {
            queueMicrotask(() => {
                if (isConfirmOnly || needsChoiceConfirm) refs.promptSubmit.focus();
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
    const activeActor = actorInfoEntry();
    if (!entries.length) {
        refs.teamList.innerHTML = `<div class="empty-state">Brak danych o drużynie.</div>`;
        return;
    }
    refs.teamList.innerHTML = entries.map((hero) => {
        const active = String(hero.id || "") === String(activeActor?.id || "");
        const hp = hero.max_hp && hero.wounds != null ? Math.max(0, Number(hero.max_hp) - Number(hero.wounds || 0)) : hero.max_hp;
        const tags = Array.isArray(hero.statuses) ? hero.statuses.slice(0, 4).join(", ") : "";
        const image = resolveActorImage(hero);
        return `
            <article class="team-card${active ? " active" : ""}">
                <img class="team-avatar" src="${escapeHtml(image)}" alt="" loading="lazy">
                <div class="team-copy">
                    <strong>${escapeHtml(hero.name || hero.id || "Hero")}</strong>
                    <div class="team-meta">
                        <span>${escapeHtml((hero.class_id || "-").replaceAll("_", " "))}</span>
                        <span>HP ${hp ?? "-"}</span>
                        <span>AC ${hero.ac ?? "-"}</span>
                        <span>Speed ${hero.speed_feet ?? hero.base_speed_feet ?? "-"}</span>
                    </div>
                    <div class="team-note">${escapeHtml(tags || hero.note || "")}</div>
                </div>
            </article>
        `;
    }).join("");
}

function renderInitiative() {
    const hasInitiative = Array.isArray(state.initiative.order) && state.initiative.order.length;
    refs.teamList.classList.toggle("hidden", Boolean(hasInitiative));
    refs.initiativeList.classList.toggle("hidden", !hasInitiative);
    if (refs.actorRailLabel) {
        refs.actorRailLabel.textContent = hasInitiative
            ? `Inicjatywa${state.initiative.round ? ` · Runda ${state.initiative.round}` : ""}`
            : "Drużyna";
    }
    if (!hasInitiative) {
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
        const actionLine = actorActionsLabel(entry);
        const statuses = Array.isArray(entry.statuses)
            ? entry.statuses.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 4)
            : [];
        const statusLine = statuses.length ? statuses.join(", ") : "";
        const image = resolveActorImage(entry);
        return `
            <article class="initiative-entry${active ? " active" : ""}">
                <img class="initiative-avatar" src="${escapeHtml(image)}" alt="" loading="lazy">
                <div class="initiative-copy">
                    <strong class="initiative-order">${index + 1}. ${escapeHtml(label)}</strong>
                    <div class="initiative-line">Init ${escapeHtml(score)}${escapeHtml(modifier)}</div>
                    ${actionLine ? `<div class="initiative-line">${escapeHtml(actionLine)}</div>` : ""}
                    ${woundLine ? `<div class="initiative-line">${woundLine}</div>` : ""}
                    ${statusLine ? `<div class="initiative-line">${escapeHtml(statusLine)}</div>` : ""}
                </div>
            </article>
        `;
    }).join("");
}

function actorInfoEntry() {
    const active = activeActorEntry();
    if (active?.id) return active;
    const heroes = currentTeamEntries();
    return heroes.length ? heroes[0] : null;
}

function actorInfoRows(actor) {
    if (!actor) return [];
    const rows = [];
    const kind = String(actor.kind || "").trim().toLowerCase();
    if (kind) rows.push(["Typ", kind === "hero" ? "Bohater" : kind === "enemy" ? "Przeciwnik" : kind]);
    const hp = actor.max_hp && actor.wounds != null ? Math.max(0, Number(actor.max_hp) - Number(actor.wounds || 0)) : actor.hp;
    if (hp != null || actor.max_hp != null) rows.push(["HP", actor.max_hp != null ? `${hp ?? "-"} / ${actor.max_hp}` : String(hp)]);
    if (actor.ac != null) rows.push(["AC", actor.ac]);
    const speed = actor.speed_feet ?? actor.base_speed_feet ?? actor.speed;
    if (speed != null) rows.push(["Speed", speed]);
    const initiative = actor.current ?? actor.effective_initiative ?? actor.initiative;
    if (initiative != null) rows.push(["Inicjatywa", initiative]);
    const position = actor.position || actor.pos;
    if (Array.isArray(position) && position.length >= 2) rows.push(["Pole", `(${position[0]}, ${position[1]})`]);
    if (actor.class_id) rows.push(["Klasa", String(actor.class_id).replaceAll("_", " ")]);
    if (actor.ancestry_id) rows.push(["Pochodzenie", String(actor.ancestry_id).replaceAll("_", " ")]);
    return rows;
}

function renderActorInfo() {
    if (!refs.actorInfoBody) return;
    const actor = actorInfoEntry();
    if (!actor) {
        refs.actorInfoBody.innerHTML = `<div class="empty-state">Brak aktywnego bohatera.</div>`;
        return;
    }
    const image = resolveActorImage(actor);
    const rows = actorInfoRows(actor);
    const statuses = Array.isArray(actor.statuses)
        ? actor.statuses.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
    refs.actorInfoBody.innerHTML = `
        <div class="actor-info-card">
            <img class="actor-info-portrait" src="${escapeHtml(image)}" alt="" loading="lazy">
            <div>
                <div class="panel-kicker">Aktywny uczestnik</div>
                <h3>${escapeHtml(actor.name || actor.id || "Aktor")}</h3>
                <div class="actor-info-grid">
                    ${rows.map(([label, value]) => `
                        <div>
                            <span>${escapeHtml(label)}</span>
                            <strong>${escapeHtml(value)}</strong>
                        </div>
                    `).join("")}
                </div>
            </div>
        </div>
        ${statuses.length ? `
            <div class="actor-info-statuses">
                ${statuses.slice(0, 18).map((status) => `<span>${escapeHtml(status)}</span>`).join("")}
            </div>
        ` : `<div class="empty-state">Brak statusów do pokazania.</div>`}
    `;
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
    refs.topScenario.textContent = scenario?.title || "Scenariusz";
    refs.topMap.textContent = state.currentMapLabel || "-";
    refs.topChapter.textContent = chapter?.chapter_title || "-";
    refs.topObjective.textContent = objective?.label || (state.scenarioFinished ? "Scenariusz zakończony" : "-");
    if (refs.adventureDrawerStatus) {
        refs.adventureDrawerStatus.textContent = objective?.label
            ? `Cel: ${objective.label}`
            : state.scenarioFinished
            ? "Scenariusz zakończony"
            : "Dziennik przygody";
    }
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
    renderScenarioChrome();
    renderRuntimeBadge();
    renderRuntimeErrorModal();
    updateAudioControls();
    renderAssembly();
    renderBriefing();
    renderTopbar();
    renderActionCard();
    renderTeam();
    renderInitiative();
    renderActorInfo();
    renderObjectives();
    renderTransitions();
    renderJournal();
    renderDiceOverlay();
    renderResult();
}

async function startRuntime() {
    refs.btnStartRuntime.disabled = true;
    try {
        audioManager.stopVoiceovers();
        state.dismissedRuntimeErrorKey = null;
        const payload = await fetchJson("/api/runtime/start", {
            method: "POST",
            body: JSON.stringify({
                scenario_id: scenarioConfig()?.id || "bandit_cave",
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
    audioManager.stopVoiceovers();
    const payload = await fetchJson("/api/runtime/stop", { method: "POST", body: JSON.stringify({}) });
    state.runtimeStatus = payload.runtime_status || state.runtimeStatus;
    renderAll();
}

async function retryRuntime() {
    refs.btnRuntimeRetry.disabled = true;
    try {
        audioManager.stopVoiceovers();
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

async function resetBoardRuntime() {
    if (!window.confirm("Zresetować połączenie z planszą bez restartu scenariusza?")) {
        return;
    }
    refs.btnBoardReset.disabled = true;
    try {
        audioManager.stopVoiceovers();
        state.dismissedRuntimeErrorKey = null;
        const payload = await fetchJson("/api/runtime/board-reset", { method: "POST", body: JSON.stringify({}) });
        state.sessionId = payload.session_id || state.sessionId;
        state.runtimeStatus = payload.runtime_status || state.runtimeStatus;
        setScreen("game");
        renderAll();
    } finally {
        refs.btnBoardReset.disabled = false;
        renderRuntimeBadge();
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

refs.btnBegin.addEventListener("click", () => {
    enableAudioFromGesture();
    setScreen("assembly");
});
refs.audioToggle.addEventListener("click", () => {
    state.audioPreferenceLocked = true;
    state.audioEnabled = !state.audioEnabled;
    updateScenarioAudio();
});
refs.audioVolume.addEventListener("input", () => {
    state.audioVolume = Math.max(0, Math.min(1, Number(refs.audioVolume.value || 0) / 100));
    updateScenarioAudio();
});
refs.btnAssemblyBack.addEventListener("click", () => setScreen("start"));
refs.btnDefaultParty?.addEventListener("click", () => {
    selectDefaultPartyForCurrentScenario();
});
refs.btnAssemblyNext.addEventListener("click", () => {
    if (!state.selectedHeroIds.length) return;
    enableAudioFromGesture();
    setScreen("briefing");
});
refs.btnBriefingBack.addEventListener("click", () => setScreen("assembly"));
refs.btnStartRuntime.addEventListener("click", () => startRuntime().catch((error) => window.alert(error.message)));
refs.btnBoardReset.addEventListener("click", () => resetBoardRuntime().catch((error) => window.alert(error.message)));
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
    if (!promptConfirmEnabled(state.view.activePrompt)) return;
    if (promptChoices(state.view.activePrompt).length) {
        submitSelectedChoice();
        return;
    }
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
    if (event.key === "*") {
        const target = event.target;
        const isTypingTarget = target instanceof HTMLInputElement && !target.classList.contains("hidden");
        if (!isTypingTarget) {
            event.preventDefault();
            toggleAdventureDrawer();
        }
        return;
    }
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
    if (event.key === "Backspace" || event.key === "Escape") {
        const target = event.target;
        const isTypingTarget = target instanceof HTMLInputElement && !target.classList.contains("hidden");
        if (event.key === "Backspace" && isTypingTarget) return;
        if (submitCancelChoice()) {
            event.preventDefault();
        }
        return;
    }
    if (event.key !== "Enter") return;
    const target = event.target;
    if (target instanceof HTMLTextAreaElement) return;
    if (!promptConfirmEnabled(state.view.activePrompt)) {
        event.preventDefault();
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
