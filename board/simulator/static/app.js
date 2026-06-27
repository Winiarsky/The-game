const boardElement = document.getElementById("board");
const pendingIndicator = document.getElementById("pending-indicator");
const lastClickLabel = document.getElementById("last-click");
const cancelScanButton = document.getElementById("cancel-scan");
const backgroundInput = document.getElementById("background-input");
const backgroundClearButton = document.getElementById("background-clear");
const modeInputs = document.querySelectorAll('input[name="board-mode"]');
const orientationInputs = document.querySelectorAll('input[name="board-orientation"]');
const figuresListElement = document.getElementById("figures-list");
const addFigureButton = document.getElementById("add-figure");
const scenarioSelect = document.getElementById("scenario-select");
const scenarioReloadButton = document.getElementById("scenario-reload");
const scenarioLoadButton = document.getElementById("scenario-load");
const scenarioToggleButton = document.getElementById("scenario-toggle");
const scenarioStatus = document.getElementById("scenario-status");
const scenarioFlowSelect = document.getElementById("scenario-flow-select");
const scenarioFlowReloadButton = document.getElementById("scenario-flow-reload");
const scenarioFlowStartButton = document.getElementById("scenario-flow-start");
const scenarioFlowStatus = document.getElementById("scenario-flow-status");
const encounterBiomeSelect = document.getElementById("encounter-biome");
const encounterThreatSelect = document.getElementById("encounter-threat");
const encounterLayoutSelect = document.getElementById("encounter-layout");
const encounterFormationPackSelect = document.getElementById("encounter-formation-pack");
const encounterPresetSelect = document.getElementById("encounter-preset");
const encounterSeedInput = document.getElementById("encounter-seed");
const encounterGenerateButton = document.getElementById("encounter-generate");
const encounterStartButton = document.getElementById("encounter-start");
const encounterStatus = document.getElementById("encounter-status");
const simulatorResetButton = document.getElementById("simulator-reset");
const runtimeStopButton = document.getElementById("runtime-stop");
const runtimeStatus = document.getElementById("runtime-status");
const heroesListElement = document.getElementById("heroes-list");
const heroesDefaultPartyButton = document.getElementById("heroes-default-party");
const heroesReloadButton = document.getElementById("heroes-reload");
const dims = window.BOARD_DIMENSIONS || { rows: 30, cols: 20 };
const posKey = (row, col) => `${row},${col}`;

const ORIENTATION_LANDSCAPE = "landscape";
const ORIENTATION_PORTRAIT = "portrait";
let boardOrientation = localStorage.getItem("boardOrientation") || ORIENTATION_LANDSCAPE;
if (![ORIENTATION_LANDSCAPE, ORIENTATION_PORTRAIT].includes(boardOrientation)) {
    boardOrientation = ORIENTATION_LANDSCAPE;
}

let cells = Array.from({ length: dims.rows }, () => Array(dims.cols).fill(null));
let wallOverlay;
const MODE_BOARD = "board";
const MODE_MOVE = "move";
const SECRET_OBJECT_IDS = new Set(["hidden_enemy_spawn", "trap_tile", "dart_launcher_trap", "hidden_cache"]);
let currentMode = MODE_BOARD;

const FIGURE_COLORS = [
    "#f94144",
    "#f3722c",
    "#f9c74f",
    "#90be6d",
    "#43aa8b",
    "#577590",
    "#b5179e",
    "#ff7b00",
];

const figures = [];
let nextFigureNumber = 1;
let selectedFigureId = null;
let latestBoardState = [];
let availableHeroes = [];
const selectedHeroIds = new Set();
const DEFAULT_PARTY_BY_SCENARIO = {
    ashen_oath: ["cedric", "freya", "kord", "christopher", "lorielen", "jimi"],
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
    scenario_exit: "EX",
    entry_anchor: "EN",
};

function normalizeScenarioPos(pos) {
    if (Array.isArray(pos) && pos.length >= 2) {
        return [Number(pos[0]), Number(pos[1])];
    }
    if (pos && typeof pos === "object" && "row" in pos && "col" in pos) {
        return [Number(pos.col), Number(pos.row)];
    }
    return null;
}

function fromScenarioPosition(pos) {
    const normalized = normalizeScenarioPos(pos);
    if (!normalized) return null;
    const [col, row] = normalized;
    return { row, col };
}

function scenarioObjectCode(label, objectId) {
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

const scenarioState = {
    name: null,
    blocked: new Set(),
    obstacles: new Set(),
    walls: [],
    cellObjects: new Map(),
    edgeObjects: [],
    startingPositions: new Set(),
    startingLabels: new Map(),
    visible: false,
};

function colorToDisplay(rgb) {
    if (!Array.isArray(rgb)) {
        return null;
    }
    const [r = 0, g = 0, b = 0] = rgb.map((component) => Math.max(0, Math.min(255, Number(component) || 0)));
    const maxValue = Math.max(r, g, b);
    if (maxValue <= 0) {
        return null;
    }
    const normalized = [
        Math.round((r / maxValue) * 255),
        Math.round((g / maxValue) * 255),
        Math.round((b / maxValue) * 255),
    ];
    const alpha = Math.min(1, maxValue / 255);
    return { rgb: normalized, alpha };
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

function createCell(row, col) {
    const cell = document.createElement("div");
    cell.className = "cell";
    cell.dataset.row = row;
    cell.dataset.col = col;
    cell.title = `R${row} C${col}`;
    cell.addEventListener("click", () => handleCellClick(row, col));

    const startMarker = document.createElement("div");
    startMarker.className = "start-marker";
    cell.appendChild(startMarker);

    const figureMarker = document.createElement("div");
    figureMarker.className = "figure-marker";
    cell.appendChild(figureMarker);

    const scenarioMarkers = document.createElement("div");
    scenarioMarkers.className = "cell-objects scenario-objects";
    cell.appendChild(scenarioMarkers);
    return cell;
}

function viewDimensions() {
    if (boardOrientation === ORIENTATION_LANDSCAPE) {
        return { rows: dims.cols, cols: dims.rows };
    }
    return { rows: dims.rows, cols: dims.cols };
}

function backendPositionForView(viewRow, viewCol) {
    if (boardOrientation === ORIENTATION_LANDSCAPE) {
        return { row: viewCol, col: viewRow };
    }
    return { row: viewRow, col: viewCol };
}

function rebuildBoardGrid() {
    if (!boardElement) return;
    const view = viewDimensions();
    boardElement.innerHTML = "";
    boardElement.style.gridTemplateColumns = `repeat(${view.cols}, 32px)`;
    boardElement.classList.toggle("orientation-landscape", boardOrientation === ORIENTATION_LANDSCAPE);
    boardElement.classList.toggle("orientation-portrait", boardOrientation === ORIENTATION_PORTRAIT);
    cells = Array.from({ length: dims.rows }, () => Array(dims.cols).fill(null));
    for (let viewRow = 0; viewRow < view.rows; viewRow += 1) {
        for (let viewCol = 0; viewCol < view.cols; viewCol += 1) {
            const { row, col } = backendPositionForView(viewRow, viewCol);
            const cell = createCell(row, col);
            boardElement.appendChild(cell);
            cells[row][col] = cell;
        }
    }
    wallOverlay = document.createElement("div");
    wallOverlay.className = "wall-overlay";
    boardElement.appendChild(wallOverlay);
}

function setBoardOrientation(orientation) {
    boardOrientation = orientation === ORIENTATION_PORTRAIT ? ORIENTATION_PORTRAIT : ORIENTATION_LANDSCAPE;
    localStorage.setItem("boardOrientation", boardOrientation);
    orientationInputs.forEach((input) => {
        input.checked = input.value === boardOrientation;
    });
    rebuildBoardGrid();
    applyBoardState();
    showToast(boardOrientation === ORIENTATION_LANDSCAPE ? "Widok planszy: poziomy." : "Widok planszy: pionowy.");
}

rebuildBoardGrid();

async function handleCellClick(row, col) {
    if (currentMode === MODE_MOVE) {
        handleMoveModeClick(row, col);
        return;
    }
    try {
        const response = await fetch("/simulate/click", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ row, col }),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Nieznany błąd");
        }
        lastClickLabel.textContent = `Ostatnie kliknięcie: (${row}, ${col})`;
        showToast(`Wysłano kliknięcie (${row}, ${col})`);
    } catch (error) {
        showToast(`Błąd wysyłania kliknięcia: ${error.message}`);
    }
}

function applyBoardState(state) {
    if (state) {
        latestBoardState = state;
    }
    const viewState = state || latestBoardState || [];
    for (let row = 0; row < dims.rows; row += 1) {
        for (let col = 0; col < dims.cols; col += 1) {
            const cell = cells[row][col];
            const display = colorToDisplay(viewState?.[row]?.[col]);
            if (display) {
                const [r, g, b] = display.rgb;
                cell.style.backgroundColor = `rgba(${r}, ${g}, ${b}, ${display.alpha.toFixed(3)})`;
                cell.classList.add("active");
            } else {
                cell.style.backgroundColor = "";
                cell.classList.remove("active");
            }
            const key = posKey(row, col);
            const scenarioOn = scenarioState.visible;
            cell.classList.toggle("terrain-blocked", scenarioOn && scenarioState.blocked.has(key));
            cell.classList.toggle("has-obstacle", scenarioOn && scenarioState.obstacles.has(key));
            cell.classList.toggle("starting-position", scenarioOn && scenarioState.startingPositions.has(key));
            const startMarker = cell.querySelector(".start-marker");
            if (startMarker) {
                startMarker.textContent = scenarioOn ? (scenarioState.startingLabels.get(key) || "S") : "";
            }
        }
    }
    renderScenarioObjects();
    renderScenarioEdgesAndWalls();
    updateFigureMarkers();
}

function updatePendingIndicator(count) {
    if (cancelScanButton) {
        cancelScanButton.disabled = count <= 0;
    }
    if (count > 0) {
        pendingIndicator.textContent = `Oczekiwanie na kliknięcie... (${count})`;
        pendingIndicator.style.color = "#b30000";
    } else {
        pendingIndicator.textContent = "Brak aktywnych zapytań scan_board.";
        pendingIndicator.style.color = "#111";
    }
}

async function refreshState() {
    try {
        const response = await fetch("/state");
        const data = await response.json();
        applyBoardState(data.state || []);
        updatePendingIndicator(data.pending_scans || 0);
    } catch (error) {
        console.error("Nie udało się pobrać stanu planszy:", error);
    }
}

function showToast(message) {
    const template = document.getElementById("toast-template");
    if (!template) {
        return;
    }
    const toast = template.content.firstElementChild.cloneNode(true);
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

async function requestCancelScan() {
    try {
        const response = await fetch("/simulate/cancel_scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Nieznany błąd");
        }
        lastClickLabel.textContent = "Ostatnia akcja: anulowano aktywny scan.";
        showToast("Wysłano anulowanie aktywnego scan_board.");
    } catch (error) {
        showToast(`Błąd anulowania scan_board: ${error.message}`);
    }
}

refreshState();
setInterval(refreshState, 600);

function findFigureById(id) {
    return figures.find((figure) => figure.id === id);
}

function findFigureAt(row, col) {
    return figures.find(
        (figure) => figure.position && figure.position.row === row && figure.position.col === col,
    );
}

function nextFigureId(prefix = "F") {
    let id = "";
    do {
        id = `${prefix}${nextFigureNumber}`;
        nextFigureNumber += 1;
    } while (findFigureById(id));
    return id;
}

function shortMarker(name, fallbackIndex) {
    const source = String(name || "").trim();
    if (!source) {
        return `P${fallbackIndex + 1}`;
    }
    const parts = source.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return source.slice(0, 2).toUpperCase();
}

function updateFigureMarkers() {
    for (let row = 0; row < dims.rows; row += 1) {
        for (let col = 0; col < dims.cols; col += 1) {
            const cell = cells[row][col];
            const marker = cell.querySelector(".figure-marker");
            const figure = findFigureAt(row, col);
            if (figure) {
                cell.classList.add("has-figure");
                marker.textContent = figure.marker || figure.label;
                marker.style.backgroundColor = figure.color;
            } else {
                cell.classList.remove("has-figure");
                marker.textContent = "";
                marker.style.backgroundColor = "";
            }
        }
    }
}

function renderFiguresList() {
    if (!figuresListElement) return;
    figuresListElement.innerHTML = "";
    if (!figures.length) {
        const empty = document.createElement("p");
        empty.className = "figures-empty";
        empty.textContent = "Brak figurek. Dodaj nową, aby rozpocząć.";
        figuresListElement.appendChild(empty);
        return;
    }

    figures.forEach((figure) => {
        const row = document.createElement("div");
        row.className = "figure-row";

        const selectButton = document.createElement("button");
        selectButton.type = "button";
        selectButton.className = `figure-select${figure.id === selectedFigureId ? " active" : ""}`;

        const dot = document.createElement("span");
        dot.className = "figure-dot";
        dot.style.backgroundColor = figure.color;

        const label = document.createElement("span");
        label.textContent = figure.name || figure.label;

        selectButton.append(dot, label);
        selectButton.addEventListener("click", () => {
            if (selectedFigureId === figure.id) {
                selectedFigureId = null;
            } else {
                selectedFigureId = figure.id;
            }
            renderFiguresList();
        });

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "figure-delete";
        deleteButton.title = "Usuń figurkę";
        deleteButton.textContent = "×";
        deleteButton.addEventListener("click", (event) => {
            event.stopPropagation();
            removeFigure(figure.id);
        });

        row.append(selectButton, deleteButton);
        figuresListElement.appendChild(row);
    });
}

function addFigure(options = {}) {
    const index = figures.findIndex((figure) => figure.id === options.id);
    const isExisting = index !== -1;
    const figureNumber = isExisting ? null : nextFigureNumber;
    const figure = {
        id: options.id || nextFigureId("F"),
        label: options.label || (figureNumber ? `F${figureNumber}` : "Figura"),
        marker: options.marker || options.label || (figureNumber ? `F${figureNumber}` : "F"),
        name: options.name || options.label || (figureNumber ? `Figurka ${figureNumber}` : "Figurka"),
        color: options.color || FIGURE_COLORS[figures.length % FIGURE_COLORS.length],
        position: options.position ? { ...options.position } : null,
        isHero: Boolean(options.isHero),
    };
    if (isExisting) {
        figures[index] = { ...figures[index], ...figure };
    } else {
        figures.push(figure);
    }
    if (!options.keepSelection) {
        selectedFigureId = figure.id;
    }
    renderFiguresList();
    updateFigureMarkers();
    if (!options.silent) {
        showToast(`Dodano figurkę ${figure.name || figure.label}. Kliknij na planszy w trybie przesuwania, aby ją ustawić.`);
    }
}

function removeFigure(id) {
    const index = figures.findIndex((figure) => figure.id === id);
    if (index === -1) return;
    figures.splice(index, 1);
    if (selectedFigureId === id) {
        selectedFigureId = null;
    }
    renderFiguresList();
    updateFigureMarkers();
}

function handleMoveModeClick(row, col) {
    if (!selectedFigureId) {
        const figureAtCell = findFigureAt(row, col);
        if (figureAtCell) {
            selectedFigureId = figureAtCell.id;
            renderFiguresList();
            showToast(`Zaznaczono ${figureAtCell.name || figureAtCell.label}.`);
        } else {
            showToast("Wybierz figurkę z panelu, aby ją przenieść.");
        }
        return;
    }
    const figure = findFigureById(selectedFigureId);
    if (!figure) {
        selectedFigureId = null;
        renderFiguresList();
        return;
    }
    const occupied = findFigureAt(row, col);
    if (occupied && occupied.id !== figure.id) {
        showToast("To pole jest już zajęte inną figurką.");
        return;
    }

    figure.position = { row, col };
    updateFigureMarkers();
    renderFiguresList();
    showToast(`Przeniesiono ${figure.name || figure.label} na (${row}, ${col}).`);
}

function setMode(mode) {
    currentMode = mode;
    if (mode === MODE_BOARD) {
        showToast("Tryb planszy: kliknięcia wysyłają scan_board.");
    } else {
        showToast("Tryb przesuwania figurek: kliknięcia tylko ustawiają figurki.");
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

function setScenarioData(scenario) {
    const blocked = Array.isArray(scenario?.blocked_fields)
        ? scenario.blocked_fields
              .map((pos) => fromScenarioPosition(pos))
              .filter((pos) => pos !== null)
        : [];
    scenarioState.blocked = new Set(blocked.map((pos) => posKey(pos.row, pos.col)));

    const obstacles = Array.isArray(scenario?.obstacles)
        ? scenario.obstacles
              .map((pos) => fromScenarioPosition(pos))
              .filter((pos) => pos !== null)
        : [];
    scenarioState.obstacles = new Set(obstacles.map((pos) => posKey(pos.row, pos.col)));

    scenarioState.walls = Array.isArray(scenario?.walls)
        ? scenario.walls
              .map((wall) => {
                  const a = fromScenarioPosition(wall?.a);
                  const b = fromScenarioPosition(wall?.b);
                  if (!a || !b) return null;
                  return { a, b, color: wall?.color || "#555", label: wall?.type || "wall" };
              })
              .filter((wall) => wall !== null)
        : [];

    const starts = Array.isArray(scenario?.starting_positions)
        ? scenario.starting_positions
              .map((pos) => fromScenarioPosition(pos))
              .filter((pos) => pos !== null)
        : [];
    scenarioState.startingPositions = new Set(starts.map((pos) => posKey(pos.row, pos.col)));
    scenarioState.startingLabels = new Map(
        starts.map((pos, index) => [posKey(pos.row, pos.col), String(index + 1)]),
    );

    scenarioState.cellObjects = new Map();
    scenarioState.edgeObjects = [];
    const objects = Array.isArray(scenario?.objects) ? scenario.objects : [];
    objects.forEach((obj) => {
        if (!obj || obj.category === "Rooms" || obj.category === "Starting") return;
        if (SECRET_OBJECT_IDS.has(obj.object_id)) return;
        const placement = obj.placement || "cell";
        if (placement === "cell") {
            const addObj = (pos) => {
                const normalized = fromScenarioPosition(pos);
                if (!normalized) return;
                const key = posKey(normalized.row, normalized.col);
                const list = scenarioState.cellObjects.get(key) || [];
                list.push({
                    label: obj.label || obj.object_id || "?",
                    code: scenarioObjectCode(obj.label, obj.object_id),
                    color: obj.color || "#555",
                });
                scenarioState.cellObjects.set(key, list);
            };
            if (Array.isArray(obj.instances)) {
                obj.instances.forEach((inst) => addObj(inst.position || inst.pos));
            }
            if (Array.isArray(obj.positions)) {
                obj.positions.forEach((pos) => addObj(pos));
            }
        } else if (placement === "edge" && Array.isArray(obj.edges)) {
            obj.edges.forEach((edge) => {
                if (!edge?.a || !edge?.b) return;
                const a = fromScenarioPosition(edge.a);
                const b = fromScenarioPosition(edge.b);
                if (!a || !b) return;
                scenarioState.edgeObjects.push({
                    a,
                    b,
                    color: obj.color || "#555",
                    label: obj.label || obj.object_id || "edge",
                    category: obj.category,
                    object_id: obj.object_id,
                });
            });
        }
    });
    applyBoardState();
}

async function refreshScenarioList(selectName) {
    if (!scenarioSelect) return;
    try {
        const response = await fetch("/api/scenarios");
        const data = await response.json();
        const scenarios = data.scenarios || [];
        scenarioSelect.innerHTML = "";
        if (!scenarios.length) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "(brak)";
            scenarioSelect.appendChild(opt);
            if (scenarioStatus) {
                scenarioStatus.textContent = "Brak dostępnych scenariuszy.";
            }
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

async function refreshScenarioFlowList(selectName) {
    if (!scenarioFlowSelect) return;
    try {
        const response = await fetch("/api/scenario-flows");
        const data = await response.json();
        const flows = data.scenario_flows || [];
        scenarioFlowSelect.innerHTML = "";
        if (!flows.length) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "(brak)";
            scenarioFlowSelect.appendChild(opt);
            if (scenarioFlowStatus) {
                scenarioFlowStatus.textContent = "Brak dostępnych flow scenariuszy.";
            }
            return;
        }
        flows.forEach((name) => {
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = name;
            scenarioFlowSelect.appendChild(opt);
        });
        if (selectName && flows.includes(selectName)) {
            scenarioFlowSelect.value = selectName;
        }
        if (scenarioFlowStatus) {
            scenarioFlowStatus.textContent = `Wybrany flow: ${scenarioFlowSelect.value || flows[0]}`;
        }
        if (!selectedHeroIds.size) {
            selectDefaultPartyForScenario(scenarioFlowSelect.value || flows[0]);
        }
        updateDefaultPartyButton();
    } catch (error) {
        console.error("Nie udało się pobrać listy flow scenariuszy", error);
    }
}

function renderScenarioObjects() {
    const scenarioOn = scenarioState.visible;
    for (let row = 0; row < dims.rows; row += 1) {
        for (let col = 0; col < dims.cols; col += 1) {
            const cell = cells[row][col];
            const container = cell.querySelector(".scenario-objects");
            if (!container) continue;
            container.innerHTML = "";
            if (!scenarioOn) continue;
            const objects = scenarioState.cellObjects.get(posKey(row, col)) || [];
            if (!objects.length) continue;
            const maxMarkers = 3;
            objects.slice(0, maxMarkers).forEach((obj, idx) => {
                const marker = document.createElement("div");
                marker.className = "object-marker";
                marker.style.background = obj.color || "#555";
                marker.textContent = obj.code || scenarioObjectCode(obj.label, "");
                container.appendChild(marker);
            });
            if (objects.length > maxMarkers) {
                const more = document.createElement("div");
                more.className = "object-marker more-marker";
                more.textContent = `+${objects.length - maxMarkers}`;
                more.style.left = `${maxMarkers * 14}px`;
                container.appendChild(more);
            }
        }
    }
}

function renderScenarioEdgesAndWalls() {
    if (!wallOverlay) return;
    wallOverlay.innerHTML = "";
    if (!scenarioState.visible) return;

    const boardRect = boardElement.getBoundingClientRect();
    const thickness = 6;

    const renderSegment = (a, b, color) => {
        const cellA = cells?.[a.row]?.[a.col];
        const cellB = cells?.[b.row]?.[b.col];
        if (!cellA || !cellB) return;
        const rectA = cellA.getBoundingClientRect();
        const rectB = cellB.getBoundingClientRect();
        const segment = document.createElement("div");
        segment.className = "wall-line";
        segment.style.background = color || "#555";
        if (a.row === b.row) {
            segment.classList.add("wall-line-v");
            const left = (rectA.right + rectB.left) / 2 - boardRect.left;
            const top = Math.min(rectA.top, rectB.top) - boardRect.top;
            const height = Math.max(rectA.height, rectB.height);
            segment.style.left = `${left - thickness / 2}px`;
            segment.style.top = `${top}px`;
            segment.style.width = `${thickness}px`;
            segment.style.height = `${height}px`;
        } else if (a.col === b.col) {
            segment.classList.add("wall-line-h");
            const top = (rectA.bottom + rectB.top) / 2 - boardRect.top;
            const left = Math.min(rectA.left, rectB.left) - boardRect.left;
            const width = Math.max(rectA.width, rectB.width);
            segment.style.left = `${left}px`;
            segment.style.top = `${top - thickness / 2}px`;
            segment.style.width = `${width}px`;
            segment.style.height = `${thickness}px`;
        } else {
            segment.classList.add("wall-line-diag");
            const midX =
                (rectA.left + rectA.width / 2 + rectB.left + rectB.width / 2) / 2 - boardRect.left;
            const midY =
                (rectA.top + rectA.height / 2 + rectB.top + rectB.height / 2) / 2 - boardRect.top;
            const diagLength = Math.hypot(rectA.width, rectA.height) * 0.65;
            const dr = b.row - a.row;
            const dc = b.col - a.col;
            const orientationClass = dr * dc > 0 ? "wall-line-diag-desc" : "wall-line-diag-asc";
            segment.classList.add(orientationClass);
            segment.style.left = `${midX - diagLength / 2}px`;
            segment.style.top = `${midY - thickness / 2}px`;
            segment.style.width = `${diagLength}px`;
            segment.style.height = `${thickness}px`;
        }
        wallOverlay.appendChild(segment);
    };

    scenarioState.walls.forEach((wall) => {
        renderSegment(wall.a, wall.b, wall.color || "#555");
    });
    scenarioState.edgeObjects.forEach((edge) => {
        renderSegment(edge.a, edge.b, edge.color || "#8b5");
    });
}

async function loadScenario(name) {
    if (!name) {
        showToast("Wybierz scenariusz.");
        return;
    }
    try {
        const response = await fetch(`/api/scenarios/${encodeURIComponent(name)}`);
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd wczytywania");
        }
        scenarioState.name = name;
        setScenarioData(data.scenario || {});
        scenarioStatus.textContent = `Załadowano: ${name}`;
        showToast(`Wczytano scenariusz ${name}.`);
    } catch (error) {
        showToast(`Nie udało się wczytać scenariusza: ${error.message}`);
    }
}

function toggleScenarioVisibility() {
    scenarioState.visible = !scenarioState.visible;
    scenarioToggleButton.textContent = scenarioState.visible ? "Ukryj elementy scenariusza" : "Pokaż elementy scenariusza";
    if (scenarioStatus) {
        const nameLabel = scenarioState.name ? ` (${scenarioState.name})` : "";
        scenarioStatus.textContent = `${scenarioState.visible ? "Widoczne" : "Ukryte"}${nameLabel}`;
    }
    applyBoardState();
}

function renderHeroesList() {
    if (!heroesListElement) return;
    heroesListElement.innerHTML = "";
    if (!availableHeroes.length) {
        const empty = document.createElement("p");
        empty.className = "figures-empty";
        empty.textContent = "Brak zapisanych bohaterów.";
        heroesListElement.appendChild(empty);
        return;
    }
    availableHeroes.forEach((hero, index) => {
        const row = document.createElement("label");
        row.className = "hero-option";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = selectedHeroIds.has(hero.character_id);
        checkbox.addEventListener("change", () => {
            if (checkbox.checked) {
                selectedHeroIds.add(hero.character_id);
            } else {
                selectedHeroIds.delete(hero.character_id);
            }
        });

        const text = document.createElement("span");
        text.innerHTML = `<strong>${hero.name}</strong> <small>${hero.class_id || "class?"}, lvl ${hero.level || 1}</small>`;

        row.append(checkbox, text);
        heroesListElement.appendChild(row);
    });
}

function defaultPartyForScenario(scenarioName) {
    return DEFAULT_PARTY_BY_SCENARIO[String(scenarioName || "").trim().toLowerCase()] || [];
}

function selectDefaultPartyForScenario(scenarioName) {
    const defaults = defaultPartyForScenario(scenarioName);
    if (!defaults.length) return false;
    const availableIds = new Set(availableHeroes.map((hero) => String(hero.character_id || "").trim().toLowerCase()));
    const selected = defaults.filter((heroId) => availableIds.has(heroId));
    if (!selected.length) return false;
    selectedHeroIds.clear();
    selected.forEach((heroId) => selectedHeroIds.add(heroId));
    renderHeroesList();
    return true;
}

function updateDefaultPartyButton() {
    if (!heroesDefaultPartyButton) return;
    const defaults = defaultPartyForScenario(scenarioFlowSelect?.value || "");
    heroesDefaultPartyButton.disabled = !defaults.length;
}

async function refreshHeroesList() {
    if (!heroesListElement) return;
    try {
        const response = await fetch("/api/heroes");
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd pobierania bohaterów");
        }
        const heroes = Array.isArray(data.heroes) ? data.heroes : [];
        availableHeroes = heroes;
        const validIds = new Set(heroes.map((hero) => hero.character_id));
        [...selectedHeroIds].forEach((characterId) => {
            if (!validIds.has(characterId)) {
                selectedHeroIds.delete(characterId);
            }
        });
        if (!selectedHeroIds.size && !selectDefaultPartyForScenario(scenarioFlowSelect?.value || "")) {
            heroes.slice(0, 6).forEach((hero) => selectedHeroIds.add(hero.character_id));
        }
        updateDefaultPartyButton();
        renderHeroesList();
    } catch (error) {
        heroesListElement.innerHTML = "";
        const empty = document.createElement("p");
        empty.className = "figures-empty";
        empty.textContent = `Nie udało się pobrać bohaterów: ${error.message}`;
        heroesListElement.appendChild(empty);
    }
}

function applySelectedHeroesToStartingPositions(startingPositions) {
    const starts = Array.isArray(startingPositions)
        ? startingPositions.map((pos) => fromScenarioPosition(pos)).filter((pos) => pos !== null)
        : [];
    for (let index = figures.length - 1; index >= 0; index -= 1) {
        if (figures[index].isHero) {
            if (selectedFigureId === figures[index].id) {
                selectedFigureId = null;
            }
            figures.splice(index, 1);
        }
    }

    const selectedHeroes = availableHeroes.filter((hero) => selectedHeroIds.has(hero.character_id));
    selectedHeroes.slice(0, starts.length).forEach((hero, index) => {
        const start = starts[index];
        addFigure({
            id: `hero:${hero.character_id}`,
            label: `P${index + 1}`,
            marker: shortMarker(hero.name, index),
            name: hero.name,
            color: FIGURE_COLORS[index % FIGURE_COLORS.length],
            position: start,
            isHero: true,
            silent: true,
            keepSelection: index !== 0,
        });
    });
    renderFiguresList();
    updateFigureMarkers();
}

function currentEncounterRequest() {
    return {
        biome: encounterBiomeSelect?.value || "forest",
        threat: encounterThreatSelect?.value || "moderate",
        layout: encounterLayoutSelect?.value || "losowy",
        formation_pack: encounterFormationPackSelect?.value || "losowy",
        preset: encounterPresetSelect?.value || "losowy",
        seed: encounterSeedInput?.value || "",
    };
}

function selectedHeroIdsList() {
    return availableHeroes
        .filter((hero) => selectedHeroIds.has(hero.character_id))
        .map((hero) => hero.character_id);
}

function applyEncounterResponse(data) {
    const metadata = data.metadata || {};
    scenarioState.name = `encounter:${metadata.layout || "random"}:${metadata.seed || "seed"}`;
    setScenarioData(data.scenario || {});
    scenarioState.visible = true;
    scenarioToggleButton.textContent = "Ukryj elementy scenariusza";
    if (scenarioStatus) {
        scenarioStatus.textContent = `Widoczne (${scenarioState.name})`;
    }
    if (encounterSeedInput && metadata.seed) {
        encounterSeedInput.value = String(metadata.seed);
    }
    if (encounterThreatSelect && metadata.threat) {
        encounterThreatSelect.value = String(metadata.threat);
    }
    if (encounterFormationPackSelect && metadata.formation_pack) {
        encounterFormationPackSelect.value = String(metadata.formation_pack);
    }
    applyBoardState();
    applySelectedHeroesToStartingPositions(data.scenario?.starting_positions || []);
    if (encounterStatus) {
        encounterStatus.textContent =
            `Wygenerowano encounter: ${metadata.biome || "?"}, ${metadata.layout || "?"}, pack ${metadata.formation_pack || "?"}, seed ${metadata.seed || "?"}, XP ${metadata.xp_total || 0}/${metadata.xp_budget || 0}.`;
    }
}

function setRuntimeStatus(data) {
    if (!runtimeStatus) return;
    if (!data || !data.running) {
        runtimeStatus.textContent = "Runtime gry nie działa.";
        return;
    }
    const uiUrl = data.ui_url || "";
    if (uiUrl) {
        runtimeStatus.innerHTML = `Runtime działa (PID ${data.pid || "?"}). UI gracza: <a href="${uiUrl}" target="_blank" rel="noopener noreferrer">${uiUrl}</a>`;
        return;
    }
    runtimeStatus.textContent = `Runtime działa (PID ${data.pid || "?"}).`;
}

async function refreshRuntimeStatus() {
    try {
        const response = await fetch("/api/runtime/status");
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd statusu runtime");
        }
        setRuntimeStatus(data);
    } catch (error) {
        if (runtimeStatus) {
            runtimeStatus.textContent = `Błąd statusu runtime: ${error.message}`;
        }
    }
}

async function generateEncounter() {
    encounterGenerateButton.disabled = true;
    if (encounterStatus) {
        encounterStatus.textContent = "Generowanie encountera...";
    }
    try {
        const response = await fetch("/api/encounters/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                biome: encounterBiomeSelect?.value || "forest",
                threat: encounterThreatSelect?.value || "moderate",
                layout: encounterLayoutSelect?.value || "losowy",
                formation_pack: encounterFormationPackSelect?.value || "losowy",
                preset: encounterPresetSelect?.value || "losowy",
                seed: encounterSeedInput?.value || "",
            }),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd generowania encountera");
        }
        applyEncounterResponse(data);
        showToast("Wygenerowano proceduralny encounter.");
    } catch (error) {
        if (encounterStatus) {
            encounterStatus.textContent = `Błąd: ${error.message}`;
        }
        showToast(`Nie udało się wygenerować encountera: ${error.message}`);
    } finally {
        encounterGenerateButton.disabled = false;
    }
}

async function startEncounterRuntime() {
    const heroIds = selectedHeroIdsList();
    if (!heroIds.length) {
        showToast("Wybierz co najmniej jednego bohatera.");
        return;
    }
    encounterStartButton.disabled = true;
    if (runtimeStatus) {
        runtimeStatus.textContent = "Uruchamianie runtime gry...";
    }
    try {
        const response = await fetch("/api/runtime/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                ...currentEncounterRequest(),
                hero_ids: heroIds,
            }),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd uruchamiania runtime");
        }
        applyEncounterResponse(data);
        setRuntimeStatus(data.runtime || {});
        showToast("Uruchomiono pełny encounter.");
    } catch (error) {
        if (runtimeStatus) {
            runtimeStatus.textContent = `Błąd runtime: ${error.message}`;
        }
        showToast(`Nie udało się uruchomić encountera: ${error.message}`);
    } finally {
        encounterStartButton.disabled = false;
    }
}

async function startScenarioFlowRuntime() {
    const heroIds = selectedHeroIdsList();
    if (!heroIds.length) {
        showToast("Wybierz co najmniej jednego bohatera.");
        return;
    }
    const scenario = scenarioFlowSelect?.value || "";
    if (!scenario) {
        showToast("Wybierz flow scenariusza.");
        return;
    }
    scenarioFlowStartButton.disabled = true;
    if (runtimeStatus) {
        runtimeStatus.textContent = "Uruchamianie runtime scenariusza...";
    }
    try {
        const response = await fetch("/api/runtime/start-scenario", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                scenario,
                hero_ids: heroIds,
            }),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd uruchamiania scenariusza");
        }
        setRuntimeStatus(data.runtime || {});
        if (scenarioFlowStatus) {
            scenarioFlowStatus.textContent = `Uruchomiono flow scenariusza: ${scenario}`;
        }
        showToast(`Uruchomiono scenariusz ${scenario}.`);
    } catch (error) {
        if (runtimeStatus) {
            runtimeStatus.textContent = `Błąd runtime: ${error.message}`;
        }
        showToast(`Nie udało się uruchomić scenariusza: ${error.message}`);
    } finally {
        scenarioFlowStartButton.disabled = false;
    }
}

async function stopEncounterRuntime() {
    runtimeStopButton.disabled = true;
    try {
        const response = await fetch("/api/runtime/stop", { method: "POST" });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd zatrzymania runtime");
        }
        setRuntimeStatus(data.runtime || {});
        showToast(data.stopped ? "Zatrzymano runtime gry." : "Runtime nie był uruchomiony.");
    } catch (error) {
        if (runtimeStatus) {
            runtimeStatus.textContent = `Błąd zatrzymania runtime: ${error.message}`;
        }
        showToast(`Nie udało się zatrzymać runtime: ${error.message}`);
    } finally {
        runtimeStopButton.disabled = false;
    }
}

async function resetSimulator() {
    simulatorResetButton.disabled = true;
    try {
        const response = await fetch("/api/reset", { method: "POST" });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.error || "Błąd resetu");
        }
        latestBoardState = [];
        scenarioState.name = null;
        scenarioState.visible = false;
        setScenarioData({});
        figures.splice(0, figures.length);
        selectedFigureId = null;
        renderFiguresList();
        updateFigureMarkers();
        if (scenarioStatus) {
            scenarioStatus.textContent = "Brak danych scenariusza.";
        }
        if (encounterStatus) {
            encounterStatus.textContent = "Symulator zresetowany.";
        }
        scenarioToggleButton.textContent = "Pokaż elementy scenariusza";
        lastClickLabel.textContent = "Nie zarejestrowano kliknięć.";
        showToast(`Zresetowano symulator. Usunięto ${data.cleared_clicks || 0} oczekujących kliknięć.`);
    } catch (error) {
        if (encounterStatus) {
            encounterStatus.textContent = `Błąd resetu: ${error.message}`;
        }
        showToast(`Nie udało się zresetować symulatora: ${error.message}`);
    } finally {
        simulatorResetButton.disabled = false;
    }
}

backgroundInput?.addEventListener("change", handleBackgroundFile);
backgroundClearButton?.addEventListener("click", () => {
    if (backgroundInput) {
        backgroundInput.value = "";
    }
    clearBoardBackground();
    showToast("Usunięto tło planszy.");
});

modeInputs.forEach((input) => {
    input.addEventListener("change", (event) => {
        if (event.target.checked) {
            setMode(event.target.value === MODE_MOVE ? MODE_MOVE : MODE_BOARD);
        }
    });
});

orientationInputs.forEach((input) => {
    input.checked = input.value === boardOrientation;
    input.addEventListener("change", (event) => {
        if (event.target.checked) {
            setBoardOrientation(event.target.value);
        }
    });
});

cancelScanButton?.addEventListener("click", () => {
    requestCancelScan();
});

document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (currentMode !== MODE_BOARD) return;
    if (!cancelScanButton || cancelScanButton.disabled) return;
    event.preventDefault();
    requestCancelScan();
});

addFigureButton?.addEventListener("click", () => addFigure());
scenarioReloadButton?.addEventListener("click", () => refreshScenarioList(scenarioState.name));
scenarioLoadButton?.addEventListener("click", () => loadScenario(scenarioSelect?.value));
scenarioToggleButton?.addEventListener("click", async () => {
    if (!scenarioState.name) {
        await loadScenario(scenarioSelect?.value);
    }
    toggleScenarioVisibility();
});
scenarioFlowReloadButton?.addEventListener("click", () => refreshScenarioFlowList(scenarioFlowSelect?.value));
scenarioFlowSelect?.addEventListener("change", () => {
    updateDefaultPartyButton();
    if (!selectDefaultPartyForScenario(scenarioFlowSelect.value) && !selectedHeroIds.size) {
        availableHeroes.slice(0, 6).forEach((hero) => selectedHeroIds.add(hero.character_id));
        renderHeroesList();
    }
});
scenarioFlowStartButton?.addEventListener("click", startScenarioFlowRuntime);
encounterGenerateButton?.addEventListener("click", generateEncounter);
encounterStartButton?.addEventListener("click", startEncounterRuntime);
simulatorResetButton?.addEventListener("click", resetSimulator);
runtimeStopButton?.addEventListener("click", stopEncounterRuntime);
heroesDefaultPartyButton?.addEventListener("click", () => {
    if (!selectDefaultPartyForScenario(scenarioFlowSelect?.value || "")) {
        showToast("Ten scenariusz nie ma skonfigurowanej domyślnej drużyny.");
    }
});
heroesReloadButton?.addEventListener("click", refreshHeroesList);

renderFiguresList();
renderHeroesList();
refreshHeroesList();
refreshRuntimeStatus();
setInterval(refreshRuntimeStatus, 2000);
refreshScenarioFlowList("bandit_cave");
refreshScenarioList("scenario_1").then(() => {
    if (scenarioSelect && scenarioSelect.value) {
        loadScenario(scenarioSelect.value);
    }
});
