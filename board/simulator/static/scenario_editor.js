const boardElement = document.getElementById("board");
const modeButtonsContainer = document.getElementById("mode-buttons");
const resetWallSelectionButton = document.getElementById("reset-wall-selection");
const clearBoardButton = document.getElementById("clear-board");
const wallTypeSelect = document.getElementById("wall-type");
const wallHardnessInput = document.getElementById("wall-hardness");
const featuresListElement = document.getElementById("features-list");
const addFeatureButton = document.getElementById("add-feature");
const wallsListElement = document.getElementById("walls-list");
const selectionInfo = document.getElementById("selection-info");
const scenarioSelect = document.getElementById("scenario-select");
const scenarioNameInput = document.getElementById("scenario-name");
const loadScenarioButton = document.getElementById("load-scenario");
const saveScenarioButton = document.getElementById("save-scenario");
const downloadScenarioButton = document.getElementById("download-scenario");
const startingInfo = document.getElementById("starting-info");
const startingListElement = document.getElementById("starting-list");
const clearStartingButton = document.getElementById("clear-starting");
const toastTemplate = document.getElementById("toast-template");
const featureTemplate = document.getElementById("feature-row-template");
const backgroundInput = document.getElementById("background-input");
const backgroundClearButton = document.getElementById("background-clear");

const dims = window.BOARD_DIMENSIONS || { rows: 15, cols: 20 };
const wallPresets = Array.isArray(window.WALL_PRESETS) ? window.WALL_PRESETS : [];

const MODE_TERRAIN_BASIC = "terrain-basic";
const MODE_TERRAIN_BLOCKED = "terrain-blocked";
const MODE_OBSTACLE = "obstacle";
const MODE_WALL = "wall";
const MODE_STARTING = "starting";

let currentMode = MODE_TERRAIN_BASIC;
let wallSelection = { first: null, second: null };
let cells = [];
let wallOverlay;

const state = {
    startingPositions: [],
    blockedFields: new Set(),
    obstacles: new Set(),
    walls: [], // {a:{row,col}, b:{row,col}, type, hardness, features}
};

const posKey = (row, col) => `${row},${col}`;
const edgeKey = (a, b) => {
    const first = `${a.row},${a.col}`;
    const second = `${b.row},${b.col}`;
    return first < second ? `${first}|${second}` : `${second}|${first}`;
};

function showToast(message) {
    if (!toastTemplate) return;
    const toast = toastTemplate.content.firstElementChild.cloneNode(true);
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2800);
}

function createCell(row, col) {
    const cell = document.createElement("div");
    cell.className = "cell";
    cell.dataset.row = row;
    cell.dataset.col = col;
    cell.title = `R${row} C${col}`;
    cell.addEventListener("click", () => handleCellClick(row, col));
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

function renderCells() {
    const startingIndexByKey = new Map();
    state.startingPositions.forEach(([row, col], index) => {
        startingIndexByKey.set(posKey(row, col), index + 1);
    });

    for (let r = 0; r < dims.rows; r += 1) {
        for (let c = 0; c < dims.cols; c += 1) {
            const cell = cells[r][c];
            const key = posKey(r, c);
            cell.classList.toggle("terrain-blocked", state.blockedFields.has(key));
            cell.classList.toggle("has-obstacle", state.obstacles.has(key));
            const startIndex = startingIndexByKey.get(key);
            cell.classList.toggle("starting-position", Boolean(startIndex));

            let marker = cell.querySelector(".start-marker");
            if (!marker) {
                marker = document.createElement("div");
                marker.className = "start-marker";
                cell.appendChild(marker);
            }
            if (startIndex) {
                marker.textContent = startIndex;
                marker.style.display = "flex";
            } else {
                marker.textContent = "";
                marker.style.display = "none";
            }
        }
    }
    renderWallOverlay();
}

function renderWallsList() {
    if (!wallsListElement) return;
    wallsListElement.innerHTML = "";
    if (!state.walls.length) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = "Brak ścian.";
        wallsListElement.appendChild(empty);
        renderWallOverlay();
        return;
    }

    state.walls.forEach((wall, index) => {
        const row = document.createElement("div");
        row.className = "wall-row";

        const label = document.createElement("div");
        label.className = "wall-label";
        const typeLabel = wall.type || "wall";
        const hardnessLabel = wall.hardness != null ? `, hardness=${wall.hardness}` : "";
        label.textContent = `${typeLabel}: (${wall.a.row},${wall.a.col}) ↔ (${wall.b.row},${wall.b.col})${hardnessLabel}`;

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "wall-remove";
        removeBtn.textContent = "Usuń";
        removeBtn.addEventListener("click", () => {
            state.walls.splice(index, 1);
            renderWallsList();
            renderCells();
        });

        row.append(label, removeBtn);
        wallsListElement.appendChild(row);
    });
    renderWallOverlay();
}

function resetWallSelection() {
    wallSelection = { first: null, second: null };
    selectionInfo.textContent = "W trybie Wall kliknij dwa pola, aby dodać ścianę.";
    renderCells();
}

function updateStartingInfo() {
    if (!startingInfo) return;
    const count = state.startingPositions.length;
    startingInfo.textContent =
        count === 0
            ? "Brak pozycji startowych. W trybie Start klikaj pola, aby je dodać."
            : `Pozycje startowe: ${count}. Kolejność wg dodawania.`;
}

function renderStartingList() {
    if (!startingListElement) return;
    startingListElement.innerHTML = "";
    if (!state.startingPositions.length) {
        const empty = document.createElement("p");
        empty.className = "muted";
        empty.textContent = "Brak pozycji startowych.";
        startingListElement.appendChild(empty);
        return;
    }
    state.startingPositions.forEach(([row, col], index) => {
        const rowEl = document.createElement("div");
        rowEl.className = "starting-row";

        const label = document.createElement("span");
        label.className = "starting-label";
        label.textContent = `#${index + 1}: (${row}, ${col})`;

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "starting-remove";
        removeBtn.textContent = "Usuń";
        removeBtn.addEventListener("click", () => {
            state.startingPositions.splice(index, 1);
            renderCells();
            renderStartingList();
            updateStartingInfo();
        });

        rowEl.append(label, removeBtn);
        startingListElement.appendChild(rowEl);
    });
}

function applyPresetToControls(presetId) {
    const preset = wallPresets.find((p) => p.id === presetId);
    if (!preset) return;
    wallHardnessInput.value = preset.hardness ?? "";
    featuresListElement.innerHTML = "";
    Object.entries(preset.features || {}).forEach(([key, value]) => addFeatureRow(key, value));
}

function addFeatureRow(key = "", value = "") {
    if (!featureTemplate) return;
    const row = featureTemplate.content.firstElementChild.cloneNode(true);
    row.querySelector(".feature-key").value = key;
    row.querySelector(".feature-value").value = value;
    row.querySelector(".feature-remove").addEventListener("click", () => row.remove());
    featuresListElement.appendChild(row);
}

function readFeaturesFromForm() {
    const features = {};
    featuresListElement.querySelectorAll(".feature-row").forEach((row) => {
        const key = row.querySelector(".feature-key").value.trim();
        if (!key) return;
        const value = row.querySelector(".feature-value").value;
        features[key] = value;
    });
    return features;
}

function addOrUpdateWall(a, b) {
    const type = wallTypeSelect.value || "wall";
    const hardnessRaw = wallHardnessInput.value === "" ? null : Number(wallHardnessInput.value);
    const hardness = Number.isFinite(hardnessRaw) ? hardnessRaw : null;
    const features = readFeaturesFromForm();
    const key = edgeKey(a, b);
    const existingIndex = state.walls.findIndex((w) => edgeKey(w.a, w.b) === key);
    const wallData = { a, b, type, hardness, features };
    if (existingIndex >= 0) {
        state.walls[existingIndex] = wallData;
    } else {
        state.walls.push(wallData);
    }
    renderWallsList();
    renderCells();
    resetWallSelection();
    showToast("Dodano/zmieniono ścianę.");
}

function handleCellClick(row, col) {
    const key = posKey(row, col);
    if (currentMode === MODE_TERRAIN_BASIC) {
        state.blockedFields.delete(key);
        state.obstacles.delete(key);
        renderCells();
        return;
    }
    if (currentMode === MODE_TERRAIN_BLOCKED) {
        state.obstacles.delete(key);
        state.blockedFields.add(key);
        renderCells();
        return;
    }
    if (currentMode === MODE_OBSTACLE) {
        if (state.obstacles.has(key)) {
            state.obstacles.delete(key);
        } else {
            state.blockedFields.delete(key);
            state.obstacles.add(key);
        }
        renderCells();
        return;
    }
    if (currentMode === MODE_STARTING) {
        const existingIndex = state.startingPositions.findIndex(
            ([r, c]) => r === row && c === col,
        );
        if (existingIndex >= 0) {
            state.startingPositions.splice(existingIndex, 1);
        } else {
            state.blockedFields.delete(key);
            state.obstacles.delete(key);
            state.startingPositions.push([row, col]);
        }
        renderCells();
        renderStartingList();
        updateStartingInfo();
        return;
    }
    if (currentMode === MODE_WALL) {
        if (!wallSelection.first) {
            wallSelection.first = { row, col };
            selectionInfo.textContent = `Wybrano pierwszy punkt: (${row}, ${col}). Wybierz drugi.`;
        } else {
            wallSelection.second = { row, col };
            selectionInfo.textContent = `Punkty: (${wallSelection.first.row}, ${wallSelection.first.col}) ↔ (${row}, ${col}).`;
            addOrUpdateWall(wallSelection.first, wallSelection.second);
        }
        renderCells();
        return;
    }
}

function handleBackgroundFile(event) {
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
}

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll(".mode-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.mode === mode);
    });
    if (mode !== MODE_WALL) {
        resetWallSelection();
    }
}

function renderWallTypeOptions() {
    if (!wallTypeSelect) return;
    wallTypeSelect.innerHTML = "";
    wallPresets.forEach((preset) => {
        const opt = document.createElement("option");
        opt.value = preset.id;
        opt.textContent = preset.label;
        wallTypeSelect.appendChild(opt);
    });
    const first = wallPresets[0];
    if (first) {
        wallTypeSelect.value = first.id;
        applyPresetToControls(first.id);
    }
}

function buildScenarioPayload() {
    return {
        starting_positions: state.startingPositions,
        blocked_fields: Array.from(state.blockedFields).map((k) => k.split(",").map(Number)),
        obstacles: Array.from(state.obstacles).map((k) => k.split(",").map(Number)),
        walls: state.walls.map((w) => ({
            a: [w.a.row, w.a.col],
            b: [w.b.row, w.b.col],
            type: w.type,
            hardness: w.hardness,
            features: w.features,
        })),
    };
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

function setStateFromScenario(scenario) {
    state.startingPositions = Array.isArray(scenario?.starting_positions)
        ? scenario.starting_positions.map((p) => [p[0], p[1]])
        : [];

    state.blockedFields = new Set(
        Array.isArray(scenario?.blocked_fields)
            ? scenario.blocked_fields.map((p) => posKey(p[0], p[1]))
            : [],
    );
    state.obstacles = new Set(
        Array.isArray(scenario?.obstacles)
            ? scenario.obstacles.map((p) => posKey(p[0], p[1]))
            : [],
    );
    state.walls = Array.isArray(scenario?.walls)
        ? scenario.walls.map((w) => ({
            a: { row: w.a[0], col: w.a[1] },
            b: { row: w.b[0], col: w.b[1] },
            type: w.type || "wall",
            hardness: w.hardness ?? null,
            features: w.features || {},
        }))
        : [];

    renderStartingList();
    updateStartingInfo();
    renderCells();
    renderWallsList();
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
    state.blockedFields.clear();
    state.obstacles.clear();
    state.walls = [];
    state.startingPositions = [];
    resetWallSelection();
    renderWallsList();
    renderStartingList();
    updateStartingInfo();
    renderCells();
}

function renderWallOverlay() {
    if (!wallOverlay || !boardElement) return;
    wallOverlay.innerHTML = "";
    if (!state.walls.length) return;

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

    state.walls.forEach((wall) => {
        const cellA = cells?.[wall.a.row]?.[wall.a.col];
        const cellB = cells?.[wall.b.row]?.[wall.b.col];
        if (!cellA || !cellB) return;
        const a = makeCenter(cellA);
        const b = makeCenter(cellB);

        const segment = document.createElement("div");
        segment.className = "wall-line";

        if (wall.a.row === wall.b.row) {
            // Ściana pionowa między sąsiadami w poziomie (ten sam wiersz)
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
        } else if (wall.a.col === wall.b.col) {
            // Ściana pozioma między sąsiadami w pionie (ta sama kolumna)
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
            // diagonalna -> kropka w środku
            segment.classList.add("wall-line-diag");
            const midX = (a.x + b.x) / 2;
            const midY = (a.y + b.y) / 2;
            segment.style.left = `${midX - dotSize / 2}px`;
            segment.style.top = `${midY - dotSize / 2}px`;
            segment.style.width = `${dotSize}px`;
            segment.style.height = `${dotSize}px`;
        }

        wallOverlay.appendChild(segment);
    });
}

function wireEvents() {
    modeButtonsContainer?.querySelectorAll(".mode-btn").forEach((btn) => {
        btn.addEventListener("click", () => setMode(btn.dataset.mode));
    });
    resetWallSelectionButton?.addEventListener("click", resetWallSelection);
    clearBoardButton?.addEventListener("click", clearObjects);
    wallTypeSelect?.addEventListener("change", (e) => applyPresetToControls(e.target.value));
    addFeatureButton?.addEventListener("click", () => addFeatureRow());
    loadScenarioButton?.addEventListener("click", () => loadScenario(scenarioSelect.value));
    saveScenarioButton?.addEventListener("click", saveScenario);
    downloadScenarioButton?.addEventListener("click", downloadScenario);
    backgroundInput?.addEventListener("change", handleBackgroundFile);
    backgroundClearButton?.addEventListener("click", () => {
        if (backgroundInput) backgroundInput.value = "";
        clearBoardBackground();
        showToast("Usunięto tło planszy.");
    });
    clearStartingButton?.addEventListener("click", () => {
        state.startingPositions = [];
        renderCells();
        renderStartingList();
        updateStartingInfo();
        showToast("Wyczyszczono pozycje startowe.");
    });
}

function init() {
    buildBoard();
    renderWallTypeOptions();
    renderCells();
    renderStartingList();
    updateStartingInfo();
    wireEvents();
    refreshScenarioList();
    showToast("Edytor scenariuszy gotowy.");
}

init();
