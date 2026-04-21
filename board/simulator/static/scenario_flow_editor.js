const flowSelect = document.getElementById("flow-select");
const flowLoadButton = document.getElementById("flow-load");
const flowRefreshButton = document.getElementById("flow-refresh");
const flowSaveButton = document.getElementById("flow-save");
const flowDownloadButton = document.getElementById("flow-download");
const flowNameInput = document.getElementById("flow-name");
const flowLabelInput = document.getElementById("flow-label");
const flowDescriptionInput = document.getElementById("flow-description");
const entryMapSelect = document.getElementById("entry-map-id");
const flowStatus = document.getElementById("flow-status");
const mapCatalogStatus = document.getElementById("map-catalog-status");
const mapsList = document.getElementById("maps-list");
const transitionsList = document.getElementById("transitions-list");
const flagsList = document.getElementById("flags-list");
const eventsList = document.getElementById("events-list");
const objectivesList = document.getElementById("objectives-list");
const checkpointTransitionSelect = document.getElementById("checkpoint-transition");
const mapAddButton = document.getElementById("map-add");
const transitionAddButton = document.getElementById("transition-add");
const flagAddButton = document.getElementById("flag-add");
const eventAddButton = document.getElementById("event-add");
const objectiveAddButton = document.getElementById("objective-add");
const toastTemplate = document.getElementById("toast-template");

const TRIGGER_OPTIONS = [
    "map_start",
    "exit_enter",
    "exit_interact",
    "object_revealed",
    "combat_end",
    "flag_set",
];

const state = {
    catalog: { runtime: [], layered: [] },
    flow: {
        format: "scenario_flow_v1",
        scenario_id: "",
        label: "",
        description: "",
        entry_map_id: "",
        maps: [],
        transitions: [],
        global_flags: {},
        events: [],
        objectives: [],
        checkpoint_policy: { transition: "auto" },
    },
};

function showToast(message) {
    if (!toastTemplate) return;
    const toast = toastTemplate.content.firstElementChild.cloneNode(true);
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2800);
}

function parseJsonField(raw, fallback) {
    const text = String(raw || "").trim();
    if (!text) return fallback;
    return JSON.parse(text);
}

function optionList(values, selected) {
    return values
        .map((value) => `<option value="${value}" ${value === selected ? "selected" : ""}>${value}</option>`)
        .join("");
}

function mapIds() {
    return state.flow.maps.map((item) => item.map_id).filter(Boolean);
}

function syncHeaderFields() {
    flowNameInput.value = state.flow.scenario_id || "";
    flowLabelInput.value = state.flow.label || "";
    flowDescriptionInput.value = state.flow.description || "";
    const ids = mapIds();
    entryMapSelect.innerHTML = ids.length ? optionList(ids, state.flow.entry_map_id) : '<option value="">(brak map)</option>';
    if (state.flow.entry_map_id && ids.includes(state.flow.entry_map_id)) {
        entryMapSelect.value = state.flow.entry_map_id;
    }
}

function renderMaps() {
    const catalogRuntime = state.catalog.runtime || [];
    const catalogLayered = state.catalog.layered || [];
    mapsList.innerHTML = "";
    if (!state.flow.maps.length) {
        mapsList.innerHTML = '<p class="muted">Brak map w scenariuszu.</p>';
        syncHeaderFields();
        return;
    }
    state.flow.maps.forEach((map, index) => {
        const row = document.createElement("div");
        row.className = "flow-row";
        const sourceOptions = map.source_type === "layered" ? catalogLayered : catalogRuntime;
        row.innerHTML = `
            <div class="form-row">
                <label>map_id</label>
                <input data-role="map_id" value="${map.map_id || ""}">
                <label>source_type</label>
                <select data-role="source_type">
                    <option value="runtime" ${map.source_type === "runtime" ? "selected" : ""}>runtime</option>
                    <option value="layered" ${map.source_type === "layered" ? "selected" : ""}>layered</option>
                </select>
                <label>source</label>
                <select data-role="source">${optionList(sourceOptions, map.source || "")}</select>
            </div>
            <div class="form-row">
                <label>label</label>
                <input data-role="label" value="${map.label || ""}">
                <button type="button" data-action="remove">Usuń mapę</button>
            </div>
        `;
        row.querySelectorAll("input, select").forEach((input) => {
            input.addEventListener("change", () => {
                map[input.dataset.role] = input.value;
                if (input.dataset.role === "source_type") {
                    map.source = "";
                    renderMaps();
                    return;
                }
                syncHeaderFields();
                renderTransitions();
                renderEvents();
            });
        });
        row.querySelector('[data-action="remove"]').addEventListener("click", () => {
            state.flow.maps.splice(index, 1);
            if (state.flow.entry_map_id === map.map_id) {
                state.flow.entry_map_id = "";
            }
            renderAll();
        });
        mapsList.appendChild(row);
    });
    syncHeaderFields();
}

function renderTransitions() {
    const ids = mapIds();
    transitionsList.innerHTML = "";
    if (!state.flow.transitions.length) {
        transitionsList.innerHTML = '<p class="muted">Brak przejść.</p>';
        return;
    }
    state.flow.transitions.forEach((transition, index) => {
        const row = document.createElement("div");
        row.className = "flow-row";
        row.innerHTML = `
            <div class="form-row">
                <label>id</label>
                <input data-role="id" value="${transition.id || ""}">
                <label>from_map_id</label>
                <select data-role="from_map_id">${optionList(ids, transition.from_map_id || "")}</select>
                <label>exit_id</label>
                <input data-role="exit_id" value="${transition.exit_id || ""}">
            </div>
            <div class="form-row">
                <label>to_map_id</label>
                <select data-role="to_map_id">${optionList(ids, transition.to_map_id || "")}</select>
                <label>target_entry_anchor_id</label>
                <input data-role="target_entry_anchor_id" value="${transition.target_entry_anchor_id || ""}">
            </div>
            <div class="form-row">
                <label>conditions</label>
                <textarea data-role="conditions" rows="2">${JSON.stringify(transition.conditions || [], null, 2)}</textarea>
                <button type="button" data-action="remove">Usuń przejście</button>
            </div>
        `;
        row.querySelectorAll("input, select, textarea").forEach((input) => {
            input.addEventListener("change", () => {
                if (input.dataset.role === "conditions") {
                    transition.conditions = parseJsonField(input.value, []);
                } else {
                    transition[input.dataset.role] = input.value;
                }
            });
        });
        row.querySelector('[data-action="remove"]').addEventListener("click", () => {
            state.flow.transitions.splice(index, 1);
            renderTransitions();
        });
        transitionsList.appendChild(row);
    });
}

function renderFlags() {
    flagsList.innerHTML = "";
    const entries = Object.entries(state.flow.global_flags || {});
    if (!entries.length) {
        flagsList.innerHTML = '<p class="muted">Brak flag.</p>';
        return;
    }
    entries.forEach(([flag, value]) => {
        const row = document.createElement("div");
        row.className = "flow-row";
        row.innerHTML = `
            <div class="form-row">
                <label>flag</label>
                <input data-role="flag" value="${flag}">
                <label>value</label>
                <input data-role="value" value="${JSON.stringify(value)}">
                <button type="button" data-action="remove">Usuń flagę</button>
            </div>
        `;
        const flagInput = row.querySelector('[data-role="flag"]');
        const valueInput = row.querySelector('[data-role="value"]');
        flagInput.addEventListener("change", () => {
            const nextFlag = flagInput.value.trim();
            const nextValue = parseJsonField(valueInput.value, false);
            delete state.flow.global_flags[flag];
            state.flow.global_flags[nextFlag] = nextValue;
            renderFlags();
        });
        valueInput.addEventListener("change", () => {
            const nextFlag = flagInput.value.trim();
            state.flow.global_flags[nextFlag] = parseJsonField(valueInput.value, false);
        });
        row.querySelector('[data-action="remove"]').addEventListener("click", () => {
            delete state.flow.global_flags[flag];
            renderFlags();
        });
        flagsList.appendChild(row);
    });
}

function renderEvents() {
    const ids = mapIds();
    eventsList.innerHTML = "";
    if (!state.flow.events.length) {
        eventsList.innerHTML = '<p class="muted">Brak eventów.</p>';
        return;
    }
    state.flow.events.forEach((event, index) => {
        const row = document.createElement("div");
        row.className = "flow-row";
        row.innerHTML = `
            <div class="form-row">
                <label>id</label>
                <input data-role="id" value="${event.id || ""}">
                <label>trigger</label>
                <select data-role="trigger">${optionList(TRIGGER_OPTIONS, event.trigger || "map_start")}</select>
                <label>map_id</label>
                <select data-role="map_id"><option value="">(global)</option>${optionList(ids, event.map_id || "")}</select>
            </div>
            <div class="form-row">
                <label>target_id</label>
                <input data-role="target_id" value="${event.target_id || ""}">
                <label>once</label>
                <input data-role="once" type="checkbox" ${event.once ? "checked" : ""}>
            </div>
            <div class="form-row">
                <label>conditions</label>
                <textarea data-role="conditions" rows="2">${JSON.stringify(event.conditions || [], null, 2)}</textarea>
            </div>
            <div class="form-row">
                <label>actions</label>
                <textarea data-role="actions" rows="3">${JSON.stringify(event.actions || [], null, 2)}</textarea>
                <button type="button" data-action="remove">Usuń event</button>
            </div>
        `;
        row.querySelectorAll("input, select, textarea").forEach((input) => {
            input.addEventListener("change", () => {
                const role = input.dataset.role;
                if (role === "once") {
                    event.once = input.checked;
                    return;
                }
                if (role === "conditions" || role === "actions") {
                    event[role] = parseJsonField(input.value, []);
                    return;
                }
                event[role] = input.value;
            });
        });
        row.querySelector('[data-action="remove"]').addEventListener("click", () => {
            state.flow.events.splice(index, 1);
            renderEvents();
        });
        eventsList.appendChild(row);
    });
}

function renderObjectives() {
    objectivesList.innerHTML = "";
    if (!state.flow.objectives.length) {
        objectivesList.innerHTML = '<p class="muted">Brak celów.</p>';
        return;
    }
    state.flow.objectives.forEach((objective, index) => {
        const row = document.createElement("div");
        row.className = "flow-row";
        row.innerHTML = `
            <div class="form-row">
                <label>id</label>
                <input data-role="id" value="${objective.id || ""}">
                <label>label</label>
                <input data-role="label" value="${objective.label || ""}">
                <button type="button" data-action="remove">Usuń cel</button>
            </div>
            <div class="form-row">
                <label>description</label>
                <textarea data-role="description" rows="2">${objective.description || ""}</textarea>
            </div>
        `;
        row.querySelectorAll("input, textarea").forEach((input) => {
            input.addEventListener("change", () => {
                objective[input.dataset.role] = input.value;
            });
        });
        row.querySelector('[data-action="remove"]').addEventListener("click", () => {
            state.flow.objectives.splice(index, 1);
            renderObjectives();
        });
        objectivesList.appendChild(row);
    });
}

function renderAll() {
    renderMaps();
    renderTransitions();
    renderFlags();
    renderEvents();
    renderObjectives();
    syncHeaderFields();
}

function buildPayload() {
    return {
        format: "scenario_flow_v1",
        scenario_id: (flowNameInput.value || state.flow.scenario_id || "").trim(),
        label: (flowLabelInput.value || "").trim(),
        description: flowDescriptionInput.value || "",
        entry_map_id: entryMapSelect.value || "",
        maps: state.flow.maps.map((item) => ({
            map_id: item.map_id,
            source_type: item.source_type,
            source: item.source,
            label: item.label,
        })),
        transitions: state.flow.transitions.map((item) => ({
            id: item.id,
            from_map_id: item.from_map_id,
            exit_id: item.exit_id,
            to_map_id: item.to_map_id,
            target_entry_anchor_id: item.target_entry_anchor_id,
            conditions: item.conditions || [],
        })),
        global_flags: state.flow.global_flags,
        events: state.flow.events.map((item) => ({
            id: item.id,
            trigger: item.trigger,
            map_id: item.map_id || undefined,
            target_id: item.target_id || undefined,
            once: !!item.once,
            conditions: item.conditions || [],
            actions: item.actions || [],
        })),
        objectives: state.flow.objectives.map((item) => ({
            id: item.id,
            label: item.label,
            description: item.description || "",
        })),
        checkpoint_policy: {
            transition: checkpointTransitionSelect.value || "auto",
        },
    };
}

async function refreshFlowList(selectName) {
    const response = await fetch("/api/scenario-flows");
    const data = await response.json();
    const flows = data.scenario_flows || [];
    flowSelect.innerHTML = "";
    if (!flows.length) {
        flowSelect.innerHTML = '<option value="">(brak)</option>';
        return;
    }
    flows.forEach((name) => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        flowSelect.appendChild(opt);
    });
    if (selectName && flows.includes(selectName)) {
        flowSelect.value = selectName;
    }
}

async function refreshCatalog() {
    try {
        const response = await fetch("/api/scenario-map-catalog");
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd katalogu map");
        }
        state.catalog = data.catalog || { runtime: [], layered: [] };
        mapCatalogStatus.textContent = `Runtime: ${state.catalog.runtime.length}, layered: ${state.catalog.layered.length}`;
        renderMaps();
    } catch (error) {
        mapCatalogStatus.textContent = `Błąd katalogu map: ${error.message}`;
    }
}

async function loadFlow(name) {
    if (!name) return;
    try {
        const response = await fetch(`/api/scenario-flows/${encodeURIComponent(name)}`);
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd wczytywania flow");
        }
        state.flow = {
            format: "scenario_flow_v1",
            scenario_id: data.scenario_flow.scenario_id || name,
            label: data.scenario_flow.label || name,
            description: data.scenario_flow.description || "",
            entry_map_id: data.scenario_flow.entry_map_id || "",
            maps: Array.isArray(data.scenario_flow.maps) ? data.scenario_flow.maps : [],
            transitions: Array.isArray(data.scenario_flow.transitions) ? data.scenario_flow.transitions : [],
            global_flags: data.scenario_flow.global_flags || {},
            events: Array.isArray(data.scenario_flow.events) ? data.scenario_flow.events : [],
            objectives: Array.isArray(data.scenario_flow.objectives) ? data.scenario_flow.objectives : [],
            checkpoint_policy: data.scenario_flow.checkpoint_policy || { transition: "auto" },
        };
        checkpointTransitionSelect.value = state.flow.checkpoint_policy.transition || "auto";
        renderAll();
        flowStatus.textContent = `Wczytano flow: ${name}`;
        showToast(`Wczytano flow ${name}.`);
    } catch (error) {
        flowStatus.textContent = `Błąd wczytywania: ${error.message}`;
        showToast(`Nie udało się wczytać flow: ${error.message}`);
    }
}

async function saveFlow() {
    const payload = buildPayload();
    const name = payload.scenario_id;
    if (!name) {
        showToast("Podaj scenario_id.");
        return;
    }
    try {
        const response = await fetch(`/api/scenario-flows/${encodeURIComponent(name)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd zapisu flow");
        }
        state.flow = {
            format: "scenario_flow_v1",
            scenario_id: data.scenario_flow.scenario_id,
            label: data.scenario_flow.label || name,
            description: data.scenario_flow.description || "",
            entry_map_id: data.scenario_flow.entry_map_id || "",
            maps: data.scenario_flow.maps || [],
            transitions: data.scenario_flow.transitions || [],
            global_flags: data.scenario_flow.global_flags || {},
            events: data.scenario_flow.events || [],
            objectives: data.scenario_flow.objectives || [],
            checkpoint_policy: data.scenario_flow.checkpoint_policy || { transition: "auto" },
        };
        checkpointTransitionSelect.value = state.flow.checkpoint_policy.transition || "auto";
        renderAll();
        await refreshFlowList(name);
        flowStatus.textContent = `Zapisano flow: ${name}`;
        showToast(`Zapisano flow ${name}.`);
    } catch (error) {
        flowStatus.textContent = `Błąd zapisu: ${error.message}`;
        showToast(`Nie udało się zapisać flow: ${error.message}`);
    }
}

function downloadFlow() {
    const payload = buildPayload();
    const name = payload.scenario_id || "scenario_flow";
    const blob = new Blob([JSON.stringify(payload, null, 4)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${name}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

function wireEvents() {
    flowRefreshButton?.addEventListener("click", () => refreshFlowList(flowSelect.value));
    flowLoadButton?.addEventListener("click", () => loadFlow(flowSelect.value));
    flowSaveButton?.addEventListener("click", saveFlow);
    flowDownloadButton?.addEventListener("click", downloadFlow);
    flowNameInput?.addEventListener("change", () => {
        state.flow.scenario_id = flowNameInput.value.trim();
    });
    flowLabelInput?.addEventListener("change", () => {
        state.flow.label = flowLabelInput.value;
    });
    flowDescriptionInput?.addEventListener("change", () => {
        state.flow.description = flowDescriptionInput.value;
    });
    entryMapSelect?.addEventListener("change", () => {
        state.flow.entry_map_id = entryMapSelect.value;
    });
    checkpointTransitionSelect?.addEventListener("change", () => {
        state.flow.checkpoint_policy.transition = checkpointTransitionSelect.value;
    });
    mapAddButton?.addEventListener("click", () => {
        state.flow.maps.push({ map_id: "", source_type: "runtime", source: "", label: "" });
        renderMaps();
    });
    transitionAddButton?.addEventListener("click", () => {
        state.flow.transitions.push({
            id: "",
            from_map_id: state.flow.entry_map_id || mapIds()[0] || "",
            exit_id: "",
            to_map_id: mapIds()[0] || "",
            target_entry_anchor_id: "",
            conditions: [],
        });
        renderTransitions();
    });
    flagAddButton?.addEventListener("click", () => {
        state.flow.global_flags[`flag_${Object.keys(state.flow.global_flags).length + 1}`] = false;
        renderFlags();
    });
    eventAddButton?.addEventListener("click", () => {
        state.flow.events.push({
            id: "",
            trigger: "map_start",
            map_id: state.flow.entry_map_id || "",
            target_id: "",
            once: false,
            conditions: [],
            actions: [],
        });
        renderEvents();
    });
    objectiveAddButton?.addEventListener("click", () => {
        state.flow.objectives.push({ id: "", label: "", description: "" });
        renderObjectives();
    });
}

wireEvents();
renderAll();
refreshCatalog();
refreshFlowList("bandit_cave");
