const boardElement = document.getElementById("board");
const categorySelect = document.getElementById("category-select");
const categoryVisibilityButton = document.getElementById("category-visibility");
const resetSelectionButton = document.getElementById("reset-selection");
const deleteModeButton = document.getElementById("delete-mode");
const clearBoardButton = document.getElementById("clear-board");
const scenarioSelect = document.getElementById("scenario-select");
const scenarioNameInput = document.getElementById("scenario-name");
const loadScenarioButton = document.getElementById("load-scenario");
const saveScenarioButton = document.getElementById("save-scenario");
const downloadScenarioButton = document.getElementById("download-scenario");
const startingInfo = document.getElementById("starting-info");
const clearStartingButton = document.getElementById("clear-starting");
const objectListElement = document.getElementById("object-list");
const selectionInfo = document.getElementById("selection-info");
const toastTemplate = document.getElementById("toast-template");
const backgroundInput = document.getElementById("background-input");
const backgroundClearButton = document.getElementById("background-clear");
const roomsPanel = document.getElementById("rooms-panel");
const roomsListElement = document.getElementById("rooms-list");
const roomNameInput = document.getElementById("room-name");
const roomColorInput = document.getElementById("room-color");
const addRoomButton = document.getElementById("add-room");
const clearRoomSelectionButton = document.getElementById("clear-room-selection");
const clearRoomAssignmentsButton = document.getElementById("clear-room-assignments");
const roomSelectionInfo = document.getElementById("room-selection-info");

const dims = window.BOARD_DIMENSIONS || { rows: 30, cols: 20 };

const VIRTUAL_START_META = {
    category: "Starting",
    object_id: "starting_position",
    label: "Pozycja startowa",
    color: "#6ba34f",
    placement: "cell",
};

const ROOMS_CATEGORY = "Rooms";

const state = {
    startingPositions: [],
    cellObjects: new Map(), // key -> [{category, object_id, label, color}]
    edgeObjects: [], // [{category, object_id, label, color, a:{row,col}, b:{row,col}}]
    hiddenCategories: new Set(),
    hiddenObjects: new Set(),
    library: [], // [{category, objects:[]}]
    metaIndex: new Map(), // key -> meta
    selection: null, // meta
    deleteMode: false,
    pendingEdgeStart: null, // {row,col}
    rooms: [], // [{id,name,color}]
    roomAssignments: new Map(), // key -> Set<roomId>
    roomSelection: new Set(), // Set<posKey>
};

const OBJECT_SHORT_CODES = {
    blocked_field: "BL",
    forest_field: "CV",
    bushes_field: "DT",
    rumble_field: "RB",
    simple_obstacle: "OB",
    simple_wall: "WL",
    goblin_warrior: "GW",
    goblin_dog: "GD",
    goblin_commando: "GC",
    dart_launcher_trap: "TR",
};

let cells = [];
let wallOverlay;

const posKey = (row, col) => `${row},${col}`;
const edgeKey = (a, b) => {
    const first = `${a.row},${a.col}`;
    const second = `${b.row},${b.col}`;
    return first < second ? `${first}|${second}` : `${second}|${first}`;
};
const metaKey = (meta) => `${meta.category}:${meta.object_id}`;
const normalizePosition = (pos) => {
    if (Array.isArray(pos) && pos.length >= 2) {
        return [Number(pos[0]), Number(pos[1])];
    }
    if (pos && typeof pos === "object" && "row" in pos && "col" in pos) {
        return [Number(pos.row), Number(pos.col)];
    }
    return pos;
};
const swapRowCol = (pos) => (Array.isArray(pos) && pos.length >= 2 ? [pos[1], pos[0]] : pos);
const toScenarioPosition = (pos) => swapRowCol(normalizePosition(pos));
const fromScenarioPosition = (pos) => swapRowCol(normalizePosition(pos));
const isRoomsCategory = () => categorySelect?.value === ROOMS_CATEGORY;
const hslToHex = (h, s, l) => {
    const a = (s / 100) * Math.min(l / 100, 1 - l / 100);
    const f = (n) => {
        const k = (n + h / 30) % 12;
        const color = l / 100 - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
        return Math.round(255 * color)
            .toString(16)
            .padStart(2, "0");
    };
    return `#${f(0)}${f(8)}${f(4)}`;
};
const randomRoomColor = () => hslToHex(Math.floor(Math.random() * 360), 60, 65);

function objectShortCode(label, objectId) {
    const objectKey = String(objectId || "").trim().toLowerCase();
    if (objectKey && OBJECT_SHORT_CODES[objectKey]) {
        return OBJECT_SHORT_CODES[objectKey];
    }
    const source = String(label || objectId || "?")
        .toUpperCase()
        .replace(/[^A-Z0-9]+/g, "");
    if (!source) return "?";
    return source.slice(0, 2);
}

function getRoomById(roomId) {
    return state.rooms.find((room) => room.id === roomId);
}

function countAssignments(roomId) {
    let count = 0;
    state.roomAssignments.forEach((value) => {
        if (value?.has?.(roomId)) count += 1;
    });
    return count;
}

function showToast(message) {
    if (!toastTemplate) return;
    const toast = toastTemplate.content.firstElementChild.cloneNode(true);
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2800);
}

function openConfigEditor(meta, existingConfig = undefined) {
    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.className = "config-overlay";
        overlay.style.position = "fixed";
        overlay.style.inset = "0";
        overlay.style.background = "rgba(0,0,0,0.45)";
        overlay.style.display = "flex";
        overlay.style.alignItems = "center";
        overlay.style.justifyContent = "center";
        overlay.style.zIndex = "9999";

        const panel = document.createElement("div");
        panel.className = "config-panel";
        panel.style.width = "420px";
        panel.style.maxWidth = "90vw";
        panel.style.background = "#fff";
        panel.style.borderRadius = "8px";
        panel.style.boxShadow = "0 10px 30px rgba(0,0,0,0.35)";
        panel.style.padding = "16px";
        panel.style.display = "flex";
        panel.style.flexDirection = "column";
        panel.style.gap = "10px";

        const title = document.createElement("h3");
        title.textContent = `Konfiguracja: ${meta.label || meta.object_id}`;
        title.style.margin = "0";

        const hint = document.createElement("p");
        hint.textContent = 'Wpisz JSON (np. {"loot":["gold"]}). Puste pole oznacza domyślne wartości.';
        hint.style.margin = "0";
        hint.style.color = "#444";
        hint.style.fontSize = "0.9rem";

        const textarea = document.createElement("textarea");
        textarea.style.width = "100%";
        textarea.style.minHeight = "160px";
        textarea.style.fontFamily = "monospace";
        textarea.style.fontSize = "0.9rem";
        textarea.style.padding = "8px";
        textarea.style.borderRadius = "6px";
        textarea.style.border = "1px solid #ccc";
        textarea.value = existingConfig ? JSON.stringify(existingConfig, null, 2) : "";

        const error = document.createElement("div");
        error.style.color = "#b00020";
        error.style.fontSize = "0.9rem";
        error.style.minHeight = "1.2em";

        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.justifyContent = "flex-end";

        const btnCancel = document.createElement("button");
        btnCancel.textContent = "Anuluj";
        btnCancel.type = "button";
        const btnSave = document.createElement("button");
        btnSave.textContent = "Zapisz";
        btnSave.type = "button";

        actions.append(btnCancel, btnSave);
        panel.append(title, hint, textarea, error, actions);
        overlay.append(panel);
        document.body.appendChild(overlay);

        const cleanup = () => overlay.remove();

        btnCancel.addEventListener("click", () => {
            cleanup();
            resolve(null);
        });
        overlay.addEventListener("click", (event) => {
            if (event.target === overlay) {
                cleanup();
                resolve(null);
            }
        });
        btnSave.addEventListener("click", () => {
            const raw = textarea.value.trim();
            if (!raw) {
                cleanup();
                resolve(undefined);
                return;
            }
            try {
                const parsed = JSON.parse(raw);
                cleanup();
                resolve(parsed);
            } catch (err) {
                error.textContent = "Niepoprawny JSON.";
            }
        });
    });
}

function ensureCell(row, col) {
    return cells?.[row]?.[col];
}

function ensureObjectContainer(cell) {
    let container = cell.querySelector(".cell-objects");
    if (!container) {
        container = document.createElement("div");
        container.className = "cell-objects";
        cell.appendChild(container);
    }
    return container;
}

function createCell(row, col) {
    const cell = document.createElement("div");
    cell.className = "cell";
    cell.dataset.row = row;
    cell.dataset.col = col;
    cell.title = `R${row} C${col}`;
    cell.addEventListener("click", (event) => handleCellClick(row, col, event));
    cell.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        handleCellClick(row, col, event, true);
    });

    const startMarker = document.createElement("div");
    startMarker.className = "start-marker";
    cell.appendChild(startMarker);

    const roomMarker = document.createElement("div");
    roomMarker.className = "room-marker";
    cell.appendChild(roomMarker);

    return cell;
}

function buildBoard() {
    if (!boardElement) return;
    boardElement.style.gridTemplateColumns = `repeat(${dims.cols}, 32px)`;
    cells = Array.from({ length: dims.rows }, () => Array(dims.cols).fill(null));
    for (let r = 0; r < dims.rows; r += 1) {
        for (let c = 0; c < dims.cols; c += 1) {
            const cell = createCell(r, c);
            cells[r][c] = cell;
            boardElement.appendChild(cell);
        }
    }
    wallOverlay = document.createElement("div");
    wallOverlay.className = "wall-overlay";
    boardElement.appendChild(wallOverlay);
}

function setBoardBackgroundImage(dataUrl) {
    if (!boardElement) return;
    boardElement.style.backgroundImage = `url(${dataUrl})`;
    boardElement.classList.add("has-background-image");
}

function clearBoardBackground() {
    if (!boardElement) return;
    boardElement.style.backgroundImage = "";
    boardElement.classList.remove("has-background-image");
}

function renderStartingMarkers() {
    const hidden =
        state.hiddenCategories.has(VIRTUAL_START_META.category) ||
        state.hiddenObjects.has(metaKey(VIRTUAL_START_META));
    const indexByKey = new Map();
    state.startingPositions.forEach(([row, col], idx) => indexByKey.set(posKey(row, col), idx + 1));
    for (let r = 0; r < dims.rows; r += 1) {
        for (let c = 0; c < dims.cols; c += 1) {
            const cell = ensureCell(r, c);
            const marker = cell.querySelector(".start-marker");
            if (hidden) {
                marker.textContent = "";
                marker.style.display = "none";
                cell.classList.remove("starting-position");
                continue;
            }
            const idx = indexByKey.get(posKey(r, c));
            if (idx) {
                marker.textContent = idx;
                marker.style.display = "flex";
                cell.classList.add("starting-position");
            } else {
                marker.textContent = "";
                marker.style.display = "none";
                cell.classList.remove("starting-position");
            }
        }
    }
}

function updateRoomSelectionInfo() {
    if (!roomSelectionInfo) return;
    const count = state.roomSelection.size;
    roomSelectionInfo.textContent =
        count === 0
            ? "Zaznacz pola na planszy, a następnie kliknij „Przydziel” przy wybranym pokoju."
            : `Zaznaczone pola: ${count}. Kliknij „Przydziel”, aby nadać pokój.`;
}

function renderRoomOverlay() {
    const roomsActive = isRoomsCategory();
    if (boardElement) {
        boardElement.classList.toggle("rooms-mode", roomsActive);
    }
    for (let r = 0; r < dims.rows; r += 1) {
        for (let c = 0; c < dims.cols; c += 1) {
            const cell = ensureCell(r, c);
            const marker = cell.querySelector(".room-marker");
            const key = posKey(r, c);
            const roomIds = state.roomAssignments.get(key) || new Set();
            const rooms = Array.from(roomIds)
                .map((id) => getRoomById(id))
                .filter(Boolean);
            const selected = state.roomSelection.has(key);

            cell.classList.toggle("rooms-active", roomsActive && rooms.length > 0);
            cell.classList.toggle("room-selected", roomsActive && selected);

            marker.innerHTML = "";
            if (roomsActive && rooms.length) {
                const primary = rooms[0];
                cell.style.setProperty("--room-color", primary?.color || "#888");
                marker.style.display = "flex";
                rooms.slice(0, 3).forEach((room, index) => {
                    const pill = document.createElement("span");
                    pill.className = "room-pill";
                    pill.textContent = room.name || room.id || `Room ${index + 1}`;
                    pill.style.background = room.color || "#888";
                    marker.append(pill);
                });
                if (rooms.length > 3) {
                    const more = document.createElement("span");
                    more.className = "room-pill room-pill-more";
                    more.textContent = `+${rooms.length - 3}`;
                    marker.append(more);
                }
            } else {
                cell.style.removeProperty("--room-color");
                marker.style.display = "none";
            }
        }
    }
}

function getObjectsAtCell(row, col, { includeHidden = false } = {}) {
    const items = state.cellObjects.get(posKey(row, col)) || [];
    return items.filter((item) => {
        if (includeHidden) return true;
        if (state.hiddenCategories.has(item.category)) return false;
        if (state.hiddenObjects.has(metaKey(item))) return false;
        return true;
    });
}

function renderCellObjects(row, col) {
    const cell = ensureCell(row, col);
    const container = ensureObjectContainer(cell);
    container.innerHTML = "";
    const objects = getObjectsAtCell(row, col);
    if (!objects.length) return;
    objects.slice(0, 3).forEach((obj, index) => {
        const marker = document.createElement("div");
        marker.className = "object-marker";
        marker.style.background = obj.color || "#444";
        marker.textContent = objectShortCode(obj.label, obj.object_id);
        container.appendChild(marker);
    });
    if (objects.length > 3) {
        const more = document.createElement("div");
        more.className = "object-marker more-marker";
        more.textContent = `+${objects.length - 3}`;
        more.style.left = `${3 * 14}px`;
        container.appendChild(more);
    }
}

function renderCells() {
    for (let r = 0; r < dims.rows; r += 1) {
        for (let c = 0; c < dims.cols; c += 1) {
            renderCellObjects(r, c);
        }
    }
    renderStartingMarkers();
    renderRoomOverlay();
    renderEdgeOverlay();
}

function renderEdgeOverlay() {
    if (!wallOverlay || !boardElement) return;
    wallOverlay.innerHTML = "";
    if (!state.edgeObjects.length) return;

    const boardRect = boardElement.getBoundingClientRect();
    const thickness = 6;
    const dotSize = 10;

    const makeCenter = (cell) => {
        const rect = cell.getBoundingClientRect();
        return {
            x: rect.left - boardRect.left + rect.width / 2,
            y: rect.top - boardRect.top + rect.height / 2,
        };
    };

    state.edgeObjects.forEach((edge, idx) => {
        if (state.hiddenCategories.has(edge.category) || state.hiddenObjects.has(metaKey(edge))) {
            return;
        }
        const cellA = ensureCell(edge.a.row, edge.a.col);
        const cellB = ensureCell(edge.b.row, edge.b.col);
        if (!cellA || !cellB) return;
        const a = makeCenter(cellA);
        const b = makeCenter(cellB);

        const segment = document.createElement("div");
        segment.className = "wall-line";
        segment.style.background = edge.color || "#555";

        if (edge.a.row === edge.b.row) {
            segment.classList.add("wall-line-v");
            const rectA = cellA.getBoundingClientRect();
            const rectB = cellB.getBoundingClientRect();
            const left = (rectA.right + rectB.left) / 2 - boardRect.left;
            const top = Math.min(rectA.top, rectB.top) - boardRect.top;
            const height = Math.max(rectA.height, rectB.height);
            segment.style.left = `${left - thickness / 2}px`;
            segment.style.top = `${top}px`;
            segment.style.width = `${thickness}px`;
            segment.style.height = `${height}px`;
        } else if (edge.a.col === edge.b.col) {
            segment.classList.add("wall-line-h");
            const rectA = cellA.getBoundingClientRect();
            const rectB = cellB.getBoundingClientRect();
            const top = (rectA.bottom + rectB.top) / 2 - boardRect.top;
            const left = Math.min(rectA.left, rectB.left) - boardRect.left;
            const width = Math.max(rectA.width, rectB.width);
            segment.style.left = `${left}px`;
            segment.style.top = `${top - thickness / 2}px`;
            segment.style.width = `${width}px`;
            segment.style.height = `${thickness}px`;
        } else {
            segment.classList.add("wall-line-diag");
            const midX = (a.x + b.x) / 2;
            const midY = (a.y + b.y) / 2;
            const diagLength = Math.hypot(cellA.getBoundingClientRect().width, cellA.getBoundingClientRect().height) * 0.65;
            const dr = edge.b.row - edge.a.row;
            const dc = edge.b.col - edge.a.col;
            const orientationClass = dr * dc > 0 ? "wall-line-diag-desc" : "wall-line-diag-asc";
            segment.classList.add(orientationClass);
            segment.style.left = `${midX - diagLength / 2}px`;
            segment.style.top = `${midY - thickness / 2}px`;
            segment.style.width = `${diagLength}px`;
            segment.style.height = `${thickness}px`;
        }

        segment.dataset.edgeIndex = String(idx);
        segment.title = `${edge.label || edge.object_id || "edge"} (${edge.a.row},${edge.a.col}) ↔ (${edge.b.row},${edge.b.col})`;
        segment.addEventListener("click", (event) => handleEdgeClick(edge, event));
        segment.addEventListener("dblclick", (event) => handleEdgeClick(edge, event, true));
        wallOverlay.appendChild(segment);
    });
}

function clearRoomSelection() {
    state.roomSelection.clear();
    updateRoomSelectionInfo();
    renderRoomOverlay();
}

async function handleEdgeClick(edge, event, forceConfig = false) {
    event?.preventDefault?.();
    event?.stopPropagation?.();
    const meta = getMeta(edge.category, edge.object_id) || edge;
    if (state.deleteMode) {
        removeEdgeObject(meta, edge.a, edge.b);
        renderCells();
        showToast("Usunięto krawędź.");
        return;
    }
    const wantsConfig =
        forceConfig ||
        event?.altKey ||
        event?.metaKey ||
        event?.ctrlKey ||
        event?.shiftKey ||
        event?.button === 2 ||
        (event?.detail >= 2);
    if (!wantsConfig) return;
    const defaultCfg = meta.default_config || meta.defaultConfig;
    const config = await openConfigEditor(meta, edge.config ?? defaultCfg);
    if (config === null) return;
    edge.config = config;
}

function toggleRoomSelection(row, col) {
    const key = posKey(row, col);
    if (state.roomSelection.has(key)) {
        state.roomSelection.delete(key);
    } else {
        state.roomSelection.add(key);
    }
    updateRoomSelectionInfo();
    renderRoomOverlay();
}

function assignRoom(roomId) {
    if (!state.roomSelection.size) {
        showToast("Najpierw zaznacz pola na planszy.");
        return;
    }
    state.roomSelection.forEach((key) => {
        const existing = state.roomAssignments.get(key) || new Set();
        existing.add(roomId);
        state.roomAssignments.set(key, existing);
    });
    clearRoomSelection();
    renderRoomsList();
    showToast("Przydzielono pokój do zaznaczonych pól.");
}

function clearAssignmentsForSelection() {
    if (!state.roomSelection.size) {
        showToast("Brak zaznaczonych pól do wyczyszczenia.");
        return;
    }
    let removed = 0;
    state.roomSelection.forEach((key) => {
        if (state.roomAssignments.delete(key)) {
            removed += 1;
        }
    });
    clearRoomSelection();
    renderRoomsList();
    showToast(removed ? `Usunięto przydział z ${removed} pól.` : "Zaznaczone pola nie miały przypisanych pokoi.");
}

function addRoom(name, color) {
    const safeName = (name || "").trim() || "Nowy pokój";
    const roomColor = color || randomRoomColor();
    const idBase = safeName.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "") || "room";
    let uniqueId = idBase;
    let idx = 1;
    while (state.rooms.some((room) => room.id === uniqueId)) {
        uniqueId = `${idBase}-${idx += 1}`;
    }
    state.rooms.push({ id: uniqueId, name: safeName, color: roomColor });
    if (roomColorInput) {
        roomColorInput.value = roomColor.startsWith("#") ? roomColor : roomColor;
    }
    if (roomNameInput) {
        roomNameInput.value = "";
    }
    renderRoomsList();
    showToast(`Dodano pokój: ${safeName}.`);
}

function removeRoom(roomId) {
    const before = state.rooms.length;
    state.rooms = state.rooms.filter((room) => room.id !== roomId);
    if (before !== state.rooms.length) {
        let removedAssignments = 0;
        const keysToCleanup = [];
        state.roomAssignments.forEach((value, key) => {
            if (value?.has?.(roomId)) {
                value.delete(roomId);
                removedAssignments += 1;
                if (value.size === 0) {
                    keysToCleanup.push(key);
                } else {
                    state.roomAssignments.set(key, value);
                }
            }
        });
        keysToCleanup.forEach((key) => state.roomAssignments.delete(key));
        clearRoomSelection();
        renderRoomsList();
        renderRoomOverlay();
        showToast(`Usunięto pokój (${removedAssignments} pól bez przydziału).`);
    }
}

function setSelection(meta) {
    state.selection = meta;
    state.pendingEdgeStart = null;
    if (!meta) {
        selectionInfo.textContent = "Wybierz obiekt, aby go wstawiać.";
        return;
    }
    const placementLabel = meta.placement === "edge" ? " (krawędzie)" : "";
    selectionInfo.textContent = `Wybrano: ${meta.label}${placementLabel}.`;
}

function toggleDeleteMode() {
    state.deleteMode = !state.deleteMode;
    deleteModeButton.textContent = state.deleteMode ? "Tryb usuwania: włączony" : "Tryb usuwania: wyłączony";
}

function addCellObject(meta, row, col, config = undefined) {
    const key = posKey(row, col);
    const list = state.cellObjects.get(key) || [];
    const exists = list.some((obj) => obj.category === meta.category && obj.object_id === meta.object_id);
    if (!exists) {
        list.push({
            category: meta.category,
            object_id: meta.object_id,
            label: meta.label,
            color: meta.color,
            config,
        });
        state.cellObjects.set(key, list);
    } else if (config !== undefined) {
        // Uaktualnij istniejący wpis konfigiem.
        list.forEach((obj) => {
            if (obj.category === meta.category && obj.object_id === meta.object_id) {
                obj.config = config;
            }
        });
        state.cellObjects.set(key, list);
    }
}

function removeCellObject(meta, row, col) {
    const key = posKey(row, col);
    const list = state.cellObjects.get(key);
    if (!list) return;
    const filtered = list.filter((obj) => !(obj.category === meta.category && obj.object_id === meta.object_id));
    if (filtered.length) {
        state.cellObjects.set(key, filtered);
    } else {
        state.cellObjects.delete(key);
    }
}

function removeAllFromCell(row, col) {
    state.cellObjects.delete(posKey(row, col));
    state.edgeObjects = state.edgeObjects.filter(
        (edge) => !(edge.a.row === row && edge.a.col === col) && !(edge.b.row === row && edge.b.col === col),
    );
}

function toggleCellObject(meta, row, col, config = undefined) {
    const key = posKey(row, col);
    const list = state.cellObjects.get(key) || [];
    const exists = list.some((obj) => obj.category === meta.category && obj.object_id === meta.object_id);
    if (exists) {
        removeCellObject(meta, row, col);
    } else {
        addCellObject(meta, row, col, config);
    }
}

function findEdge(meta, a, b) {
    const key = edgeKey(a, b);
    return state.edgeObjects.find((edge) => edgeKey(edge.a, edge.b) === key && metaKey(edge) === metaKey(meta));
}

function addEdgeObject(meta, a, b, config = undefined) {
    if (findEdge(meta, a, b)) return;
    state.edgeObjects.push({
        category: meta.category,
        object_id: meta.object_id,
        label: meta.label,
        color: meta.color,
        a,
        b,
        config,
    });
}

function removeEdgeObject(meta, a, b) {
    const key = edgeKey(a, b);
    state.edgeObjects = state.edgeObjects.filter(
        (edge) => !(edgeKey(edge.a, edge.b) === key && metaKey(edge) === metaKey(meta)),
    );
}

async function handleEdgePlacement(meta, row, col, event, forceConfig = false) {
    if (!state.pendingEdgeStart) {
        state.pendingEdgeStart = { row, col };
        selectionInfo.textContent = `Wybrano pierwszy punkt: (${row}, ${col}). Kliknij drugi.`;
        return;
    }
    const start = state.pendingEdgeStart;
    const end = { row, col };
    state.pendingEdgeStart = null;
    const already = findEdge(meta, start, end);
    const wantsConfig =
        forceConfig ||
        event?.altKey ||
        event?.metaKey ||
        event?.ctrlKey ||
        event?.shiftKey ||
        event?.button === 2 ||
        (event?.detail >= 2);
    if (state.deleteMode) {
        if (already) {
            removeEdgeObject(meta, start, end);
            showToast("Usunięto krawędź.");
        }
    } else if (already) {
        if (wantsConfig) {
            const defaultCfg = meta.default_config || meta.defaultConfig;
            const config = await openConfigEditor(meta, already.config ?? defaultCfg);
            if (config !== null) {
                already.config = config;
                showToast("Zapisano konfigurację krawędzi.");
            }
        } else {
            removeEdgeObject(meta, start, end);
            showToast("Usunięto istniejącą krawędź (toggle).");
        }
    } else {
        let config;
        if (wantsConfig) {
            const defaultCfg = meta.default_config || meta.defaultConfig;
            config = await openConfigEditor(meta, defaultCfg);
            if (config === null) {
                renderCells();
                return;
            }
        }
        addEdgeObject(meta, start, end, config);
        showToast("Dodano krawędź.");
    }
    renderCells();
}

function handleStartingPlacement(row, col) {
    const idx = state.startingPositions.findIndex(([r, c]) => r === row && c === col);
    if (idx >= 0) {
        state.startingPositions.splice(idx, 1);
    } else {
        state.startingPositions.push([row, col]);
    }
    updateStartingInfo();
    renderStartingMarkers();
    renderCellObjects(row, col);
}

async function handleCellClick(row, col, event, forceConfig = false) {
    if (isRoomsCategory()) {
        toggleRoomSelection(row, col);
        return;
    }
    const meta = state.selection;
    if (meta && meta.object_id === VIRTUAL_START_META.object_id) {
        handleStartingPlacement(row, col);
        return;
    }
    if (state.deleteMode && !meta) {
        removeAllFromCell(row, col);
        renderCells();
        return;
    }
    if (!meta) {
        showToast("Wybierz obiekt, aby wstawiać.");
        return;
    }
    if (meta.placement === "edge") {
        await handleEdgePlacement(meta, row, col, event, forceConfig);
        return;
    }
    const wantsConfig =
        forceConfig ||
        event?.altKey ||
        event?.metaKey ||
        event?.ctrlKey ||
        event?.shiftKey ||
        event?.button === 2 ||
        (event?.detail >= 2); // double-click jako skrót do konfiguracji
    if (wantsConfig && !state.deleteMode) {
        event?.preventDefault?.();
        event?.stopPropagation?.();
        const key = posKey(row, col);
        const existing = (state.cellObjects.get(key) || []).find(
            (obj) => obj.category === meta.category && obj.object_id === meta.object_id,
        );
        const defaultCfg = meta.default_config || meta.defaultConfig;
        const config = await openConfigEditor(meta, existing?.config ?? defaultCfg);
        if (config === null) return; // anulowano
        addCellObject(meta, row, col, config);
        renderCellObjects(row, col);
        return;
    }
    if (state.deleteMode) {
        removeCellObject(meta, row, col);
    } else {
        toggleCellObject(meta, row, col);
    }
    renderCellObjects(row, col);
}

function updateStartingInfo() {
    if (!startingInfo) return;
    const count = state.startingPositions.length;
    startingInfo.textContent =
        count === 0
            ? "Brak pozycji startowych. Wybierz obiekt 'Pozycja startowa' i klikaj pola, aby dodać."
            : `Pozycje startowe: ${count}. Kolejność wg dodawania.`;
}

function toggleCategoryVisibility() {
    const category = categorySelect.value;
    if (!category) return;
    if (state.hiddenCategories.has(category)) {
        state.hiddenCategories.delete(category);
    } else {
        state.hiddenCategories.add(category);
    }
    renderCells();
    renderObjectList();
}

function toggleObjectVisibility(meta) {
    const key = metaKey(meta);
    if (state.hiddenObjects.has(key)) {
        state.hiddenObjects.delete(key);
    } else {
        state.hiddenObjects.add(key);
    }
    renderCells();
    renderObjectList();
}

function renderRoomsList() {
    if (!roomsListElement) return;
    roomsListElement.innerHTML = "";
    if (!state.rooms.length) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = "Brak zdefiniowanych pokoi. Dodaj nazwę i kolor, a potem kliknij „+ Dodaj pokój”.";
        roomsListElement.append(empty);
        return;
    }

    state.rooms.forEach((room) => {
        const row = document.createElement("div");
        row.className = "room-row";

        const color = document.createElement("span");
        color.className = "room-color";
        color.style.background = room.color || "#7c6bf3";

        const name = document.createElement("span");
        name.className = "room-name";
        name.textContent = room.name || room.id;

        const meta = document.createElement("span");
        meta.className = "room-meta";
        meta.textContent = `${countAssignments(room.id)} pól`;

        const actions = document.createElement("div");
        actions.className = "room-actions";

        const assignBtn = document.createElement("button");
        assignBtn.type = "button";
        assignBtn.textContent = "Przydziel";
        assignBtn.addEventListener("click", () => assignRoom(room.id));

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "room-delete";
        deleteBtn.textContent = "Usuń";
        deleteBtn.addEventListener("click", () => removeRoom(room.id));

        actions.append(assignBtn, deleteBtn);
        row.append(color, name, meta, actions);
        roomsListElement.append(row);
    });
}

function renderObjectList() {
    if (!objectListElement) return;
    objectListElement.innerHTML = "";
    if (isRoomsCategory()) {
        const info = document.createElement("p");
        info.className = "muted";
        info.textContent = "Tryb pokoi: zaznacz pola na planszy, a poniżej dodaj/podepnij pokój.";
        objectListElement.append(info);
        return;
    }
    const category = categorySelect.value;
    const group = state.library.find((g) => g.category === category);
    if (!group) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = "Brak obiektów w tej kategorii.";
        objectListElement.appendChild(empty);
        return;
    }

    group.objects.forEach((obj) => {
        const row = document.createElement("div");
        row.className = "object-row";

        const info = document.createElement("div");
        info.className = "object-info";

        const dot = document.createElement("span");
        dot.className = "object-dot";
        dot.style.background = obj.color || "#555";

        const label = document.createElement("span");
        label.className = "object-label";
        label.textContent = obj.label || obj.object_id;

        info.append(dot, label);

        const actions = document.createElement("div");
        actions.className = "object-actions";

        const eye = document.createElement("button");
        eye.type = "button";
        eye.className = "icon-btn";
        const key = metaKey(obj);
        const hidden = state.hiddenCategories.has(obj.category) || state.hiddenObjects.has(key);
        eye.textContent = hidden ? "🙈" : "👁";
        eye.title = hidden ? "Pokaż" : "Ukryj";
        eye.addEventListener("click", () => toggleObjectVisibility(obj));

        const useBtn = document.createElement("button");
        useBtn.type = "button";
        useBtn.textContent = state.selection && metaKey(state.selection) === key ? "Wybrano" : "Użyj";
        useBtn.disabled = state.selection && metaKey(state.selection) === key;
        useBtn.addEventListener("click", () => setSelection(obj));

        actions.append(eye, useBtn);
        row.append(info, actions);
        objectListElement.appendChild(row);
    });
}

function renderCategoryOptions() {
    if (!categorySelect) return;
    categorySelect.innerHTML = "";
    state.library.forEach((group) => {
        const opt = document.createElement("option");
        opt.value = group.category;
        opt.textContent = group.category;
        categorySelect.appendChild(opt);
    });
    if (state.library.length) {
        categorySelect.value = state.library[0].category;
    }
}

function updateCategoryUI() {
    const roomsActive = isRoomsCategory();
    if (roomsPanel) {
        roomsPanel.hidden = !roomsActive;
        roomsPanel.style.display = roomsActive ? "flex" : "none";
    }
    if (roomsActive) {
        state.selection = null;
        state.pendingEdgeStart = null;
        if (selectionInfo) {
            selectionInfo.textContent = "Tryb pokoi: zaznacz pola na planszy, potem kliknij „Przydziel”.";
        }
        updateRoomSelectionInfo();
    } else if (!state.selection && selectionInfo) {
        selectionInfo.textContent = "Kliknij „Użyj”, aby wybrać obiekt i wstawiać go klikając pola. Ikonka oka ukrywa/odsłania obiekty.";
    }
    if (!roomsActive) {
        clearRoomSelection();
        if (roomSelectionInfo) {
            roomSelectionInfo.textContent = "";
        }
        if (roomsListElement) {
            roomsListElement.innerHTML = "";
        }
    }
    renderRoomsList();
    renderRoomOverlay();
    renderObjectList();
}

async function loadGameObjects() {
    try {
        const response = await fetch("/api/game-objects");
        const data = await response.json();
        const categories = data.categories || [];
        categories.push({ category: ROOMS_CATEGORY, objects: [] });
        // dodaj wirtualną kategorię startów
        categories.push({ category: VIRTUAL_START_META.category, objects: [VIRTUAL_START_META] });
        state.library = categories;
        state.metaIndex.clear();
        categories.forEach((group) => {
            group.objects.forEach((obj) => {
                state.metaIndex.set(metaKey(obj), obj);
            });
        });
        renderCategoryOptions();
        renderObjectList();
        const firstRealCategory = categories.find(
            (group) => group.category !== ROOMS_CATEGORY && group.category !== VIRTUAL_START_META.category && group.objects.length,
        );
        if (firstRealCategory) {
            categorySelect.value = firstRealCategory.category;
            setSelection(firstRealCategory.objects[0]);
        }
        updateCategoryUI();
    } catch (error) {
        console.error("Nie udało się pobrać GameObjects", error);
        showToast("Błąd ładowania GameObjects.");
    }
}

function buildScenarioPayload() {
    const objectsByKey = new Map();
    const edgesByKey = new Map();
    const roomPositions = new Map();

    state.cellObjects.forEach((list, key) => {
        list.forEach((obj) => {
            const meta = getMeta(obj.category, obj.object_id) || obj;
            const objectKey = metaKey(meta);
            if (!objectsByKey.has(objectKey)) {
                objectsByKey.set(objectKey, { ...meta, positions: [], instances: [] });
            }
            const scenarioPos = toScenarioPosition(key.split(",").map(Number));
            if (!Array.isArray(scenarioPos)) return;
            if (obj.config !== undefined) {
                objectsByKey.get(objectKey).instances.push({ position: scenarioPos, config: obj.config });
            } else {
                objectsByKey.get(objectKey).positions.push(scenarioPos);
            }
        });
    });

    state.edgeObjects.forEach((edge) => {
        const meta = getMeta(edge.category, edge.object_id) || edge;
        const objectKey = metaKey(meta);
        if (!edgesByKey.has(objectKey)) {
            edgesByKey.set(objectKey, { ...meta, edges: [] });
        }
        const aPos = toScenarioPosition([edge.a.row, edge.a.col]);
        const bPos = toScenarioPosition([edge.b.row, edge.b.col]);
        if (!Array.isArray(aPos) || !Array.isArray(bPos)) return;
        const edgePayload = { a: aPos, b: bPos };
        if (edge.config !== undefined) {
            edgePayload.config = edge.config;
        }
        edgesByKey.get(objectKey).edges.push(edgePayload);
    });

    state.roomAssignments.forEach((roomIds, key) => {
        const coords = key.split(",").map(Number);
        const scenarioPos = toScenarioPosition(coords);
        if (!Array.isArray(scenarioPos)) return;
        Array.from(roomIds || []).forEach((roomId) => {
            const list = roomPositions.get(roomId) || [];
            list.push(scenarioPos);
            roomPositions.set(roomId, list);
        });
    });

    const rooms = state.rooms.map((room) => ({
        id: room.id,
        name: room.name,
        color: room.color,
        positions: roomPositions.get(room.id) || [],
    }));

    const objects = [
        ...Array.from(objectsByKey.values(), (o) => ({
            category: o.category,
            object_id: o.object_id,
            label: o.label,
            color: o.color,
            placement: "cell",
            positions: o.positions,
            instances: o.instances,
        })),
        ...Array.from(edgesByKey.values(), (o) => ({
            category: o.category,
            object_id: o.object_id,
            label: o.label,
            color: o.color,
            placement: "edge",
            edges: o.edges,
        })),
    ];

    // Wsteczna kompatybilność z polami blocked/obstacles/walls
    const blocked_fields = [];
    const obstacles = [];
    objects.forEach((obj) => {
        if (obj.category === "Terrains" && obj.object_id === "blocked_field") {
            blocked_fields.push(...(obj.positions || []));
        }
        if (obj.category === "Obstacles" && obj.object_id === "simple_obstacle") {
            obstacles.push(...(obj.positions || []));
        }
    });
    const wallIds = new Set(["simple_wall", "basic_wall"]);
    const walls = state.edgeObjects
        .filter((edge) => edge.category === "Walls" && wallIds.has(edge.object_id))
        .map((edge) => ({
            a: toScenarioPosition([edge.a.row, edge.a.col]),
            b: toScenarioPosition([edge.b.row, edge.b.col]),
            type: edge.object_id === "basic_wall" ? "simple_wall" : edge.object_id,
        }));

    return {
        starting_positions: state.startingPositions
            .map((pos) => toScenarioPosition(pos))
            .filter((pos) => Array.isArray(pos)),
        rooms,
        objects,
        blocked_fields,
        obstacles,
        walls,
    };
}

async function saveScenario() {
    const name = (scenarioNameInput.value || "scenario_edited").trim();
    if (!name) {
        showToast("Podaj nazwę scenariusza.");
        return;
    }
    const payload = buildScenarioPayload();
    try {
        const response = await fetch(`/api/scenarios/${encodeURIComponent(name)}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd zapisu");
        }
        showToast("Zapisano scenariusz.");
        refreshScenarioList(name);
    } catch (error) {
        showToast(`Błąd zapisu: ${error.message}`);
    }
}

function downloadScenario() {
    const name = (scenarioNameInput.value || "scenario_edited").replace(/\.[^/.]+$/, "");
    const payload = buildScenarioPayload();
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

function getMeta(category, objectId) {
    return state.metaIndex.get(`${category}:${objectId}`);
}

function applyObjects(objects = []) {
    state.cellObjects.clear();
    state.edgeObjects = [];
    objects.forEach((obj) => {
        const placement = obj.placement || "cell";
        if (placement === "edge" && Array.isArray(obj.edges)) {
            obj.edges.forEach((edge) => {
                if (!edge?.a || !edge?.b) return;
                const aPos = fromScenarioPosition(edge.a);
                const bPos = fromScenarioPosition(edge.b);
                if (!Array.isArray(aPos) || !Array.isArray(bPos)) return;
                const [aRow, aCol] = aPos;
                const [bRow, bCol] = bPos;
                addEdgeObject(
                    obj,
                    { row: aRow, col: aCol },
                    { row: bRow, col: bCol },
                    edge.config,
                );
            });
        } else if (Array.isArray(obj.instances)) {
            obj.instances.forEach((inst) => {
                const normalized = fromScenarioPosition(inst.position || inst.pos);
                if (!Array.isArray(normalized)) return;
                const [row, col] = normalized;
                addCellObject(obj, row, col, inst.config);
            });
        } else if (Array.isArray(obj.positions)) {
            obj.positions.forEach((pos) => {
                const normalized = fromScenarioPosition(pos);
                if (!Array.isArray(normalized)) return;
                const [row, col] = normalized;
                addCellObject(obj, row, col);
            });
        }
    });
}

function applyRooms(rooms = []) {
    state.rooms = [];
    state.roomAssignments.clear();
    const usedIds = new Set();
    rooms.forEach((room, index) => {
        const baseId = (room?.id || room?.name || `room-${index + 1}`).toString();
        let uniqueId = baseId;
        let suffix = 1;
        while (usedIds.has(uniqueId)) {
            uniqueId = `${baseId}-${suffix += 1}`;
        }
        usedIds.add(uniqueId);
        const name = room?.name || uniqueId;
        const color = room?.color || randomRoomColor();
        state.rooms.push({ id: uniqueId, name, color });

        const positions = Array.isArray(room?.positions) ? room.positions : [];
        positions.forEach((pos) => {
            const normalized = fromScenarioPosition(pos);
            if (!Array.isArray(normalized)) return;
            const [row, col] = normalized;
            const key = posKey(row, col);
            const existing = state.roomAssignments.get(key) || new Set();
            existing.add(uniqueId);
            state.roomAssignments.set(key, existing);
        });
    });
}

function setStateFromScenario(scenario) {
    state.startingPositions = Array.isArray(scenario?.starting_positions)
        ? scenario.starting_positions
              .map((p) => fromScenarioPosition(p))
              .filter((pos) => Array.isArray(pos))
        : [];

    applyRooms(Array.isArray(scenario?.rooms) ? scenario.rooms : []);

    // Wczytaj nowe pole objects (jeśli jest).
    if (Array.isArray(scenario?.objects)) {
        applyObjects(scenario.objects);
    } else {
        state.cellObjects.clear();
        state.edgeObjects = [];
    }

    // Wczytaj pola legacy do obiektów, jeśli nie ma nowych.
    if (!Array.isArray(scenario?.objects)) {
        const blocked = Array.isArray(scenario?.blocked_fields) ? scenario.blocked_fields : [];
        const obstacles = Array.isArray(scenario?.obstacles) ? scenario.obstacles : [];
        const walls = Array.isArray(scenario?.walls) ? scenario.walls : [];

        const defaultPlainMeta = getMeta("Terrains", "plain_field") || {
            category: "Terrains",
            object_id: "plain_field",
            label: "Zwykłe pole",
            color: "#7cb342",
            placement: "cell",
        };

        const blockedMeta = getMeta("Terrains", "blocked_field") || {
            category: "Terrains",
            object_id: "blocked_field",
            label: "Pole zablokowane",
            color: "#c44",
        };
        // Jeśli brak pól blokujących, wypełnij edytor zwykłym terenem, by pokazać plan.
        if (!blocked.length) {
            state.cellObjects.clear();
            // w scenariuszu brak terenu => pokaż zwykłe pola jako domyślne (bez zapisywania).
            // Zakładamy rozmiar z mapy (rooms/start/objects już ustawiły w state), więc tu nic nie dodajemy.
        }
        blocked.forEach((pos) => {
            const normalized = fromScenarioPosition(pos);
            if (!Array.isArray(normalized)) return;
            const [row, col] = normalized;
            addCellObject(blockedMeta, row, col);
        });

        const obstacleMeta = getMeta("Obstacles", "simple_obstacle") || {
            category: "Obstacles",
            object_id: "simple_obstacle",
            label: "Przeszkoda",
            color: "#333",
        };
        obstacles.forEach((pos) => {
            const normalized = fromScenarioPosition(pos);
            if (!Array.isArray(normalized)) return;
            const [row, col] = normalized;
            addCellObject(obstacleMeta, row, col);
        });

        const defaultWallMeta =
            getMeta("Walls", "simple_wall") ||
            getMeta("Walls", "basic_wall") || {
                category: "Walls",
                object_id: "simple_wall",
                label: "Ściana",
                color: "#555",
                placement: "edge",
            };
        walls.forEach((wall) => {
            if (!wall?.a || !wall?.b) return;
            const aPos = fromScenarioPosition(wall.a);
            const bPos = fromScenarioPosition(wall.b);
            if (!Array.isArray(aPos) || !Array.isArray(bPos)) return;
            const [aRow, aCol] = aPos;
            const [bRow, bCol] = bPos;
            const wallType = wall?.type || wall?.object_id;
            const wallMeta = getMeta("Walls", wallType) || defaultWallMeta;
            addEdgeObject(
                wallMeta,
                { row: aRow, col: aCol },
                { row: bRow, col: bCol },
            );
        });
    }

    updateStartingInfo();
    renderCells();
    renderObjectList();
    renderRoomsList();
    renderRoomOverlay();
}

async function loadScenario(name) {
    if (!name) return;
    try {
        const response = await fetch(`/api/scenarios/${encodeURIComponent(name)}`);
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd wczytywania");
        }
        setStateFromScenario(data.scenario || {});
        showToast(`Wczytano scenariusz ${name}.`);
    } catch (error) {
        showToast(`Nie udało się wczytać: ${error.message}`);
    }
}

async function refreshScenarioList(selectName) {
    try {
        const response = await fetch("/api/scenarios");
        const data = await response.json();
        const scenarios = data.scenarios || [];
        scenarioSelect.innerHTML = "";
        if (!scenarios.length) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "(brak plików)";
            scenarioSelect.appendChild(opt);
            return;
        }
        scenarios.forEach((name) => {
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = name;
            scenarioSelect.appendChild(opt);
        });
        if (selectName && scenarios.includes(selectName)) {
            scenarioSelect.value = selectName;
        }
    } catch (error) {
        console.error("Nie udało się pobrać listy scenariuszy", error);
    }
}

function clearObjects() {
    state.cellObjects.clear();
    state.edgeObjects = [];
    state.pendingEdgeStart = null;
    state.roomAssignments.clear();
    clearRoomSelection();
    renderRoomsList();
    renderRoomOverlay();
    renderCells();
}

function wireEvents() {
    categorySelect?.addEventListener("change", () => {
        updateCategoryUI();
    });
    categoryVisibilityButton?.addEventListener("click", toggleCategoryVisibility);
    resetSelectionButton?.addEventListener("click", () => setSelection(null));
    deleteModeButton?.addEventListener("click", toggleDeleteMode);
    clearBoardButton?.addEventListener("click", clearObjects);
    loadScenarioButton?.addEventListener("click", () => loadScenario(scenarioSelect.value));
    saveScenarioButton?.addEventListener("click", saveScenario);
    downloadScenarioButton?.addEventListener("click", downloadScenario);
    backgroundInput?.addEventListener("change", (event) => {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }
        if (!file.type.startsWith("image/")) {
            showToast("Wybierz plik graficzny.");
            event.target.value = "";
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            setBoardBackgroundImage(reader.result);
            showToast(`Ustawiono tło: ${file.name}`);
        };
        reader.onerror = () => {
            showToast("Nie udało się wczytać obrazu.");
        };
        reader.readAsDataURL(file);
    });
    backgroundClearButton?.addEventListener("click", () => {
        if (backgroundInput) backgroundInput.value = "";
        clearBoardBackground();
        showToast("Usunięto tło planszy.");
    });
    clearStartingButton?.addEventListener("click", () => {
        state.startingPositions = [];
        updateStartingInfo();
        renderStartingMarkers();
        showToast("Wyczyszczono pozycje startowe.");
    });
    addRoomButton?.addEventListener("click", () => addRoom(roomNameInput?.value, roomColorInput?.value));
    clearRoomSelectionButton?.addEventListener("click", clearRoomSelection);
    clearRoomAssignmentsButton?.addEventListener("click", clearAssignmentsForSelection);
}

async function init() {
    buildBoard();
    wireEvents();
    await loadGameObjects();
    renderCells();
    refreshScenarioList();
    updateStartingInfo();
    showToast("Edytor scenariuszy gotowy.");
}

init();
