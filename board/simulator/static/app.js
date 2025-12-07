const boardElement = document.getElementById("board");
const pendingIndicator = document.getElementById("pending-indicator");
const lastClickLabel = document.getElementById("last-click");
const backgroundInput = document.getElementById("background-input");
const backgroundClearButton = document.getElementById("background-clear");
const modeInputs = document.querySelectorAll('input[name="board-mode"]');
const figuresListElement = document.getElementById("figures-list");
const addFigureButton = document.getElementById("add-figure");
const scenarioSelect = document.getElementById("scenario-select");
const scenarioReloadButton = document.getElementById("scenario-reload");
const scenarioLoadButton = document.getElementById("scenario-load");
const scenarioToggleButton = document.getElementById("scenario-toggle");
const scenarioStatus = document.getElementById("scenario-status");
const dims = window.BOARD_DIMENSIONS || { rows: 15, cols: 20 };

boardElement.style.gridTemplateColumns = `repeat(${dims.cols}, 32px)`;

const cells = Array.from({ length: dims.rows }, () => Array(dims.cols).fill(null));
let wallOverlay;
const MODE_BOARD = "board";
const MODE_MOVE = "move";
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

const scenarioState = {
    name: null,
    blocked: new Set(),
    obstacles: new Set(),
    walls: [],
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
    const figureMarker = document.createElement("div");
    figureMarker.className = "figure-marker";
    cell.appendChild(figureMarker);
    return cell;
}

for (let row = 0; row < dims.rows; row += 1) {
    for (let col = 0; col < dims.cols; col += 1) {
        const cell = createCell(row, col);
        boardElement.appendChild(cell);
        cells[row][col] = cell;
    }
}
wallOverlay = document.createElement("div");
wallOverlay.className = "wall-overlay";
boardElement.appendChild(wallOverlay);

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
            const key = `${row},${col}`;
            const scenarioOn = scenarioState.visible;
            cell.classList.toggle("terrain-blocked", scenarioOn && scenarioState.blocked.has(key));
            cell.classList.toggle("has-obstacle", scenarioOn && scenarioState.obstacles.has(key));
        }
    }
    renderScenarioWalls();
    updateFigureMarkers();
}

function updatePendingIndicator(count) {
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

function updateFigureMarkers() {
    for (let row = 0; row < dims.rows; row += 1) {
        for (let col = 0; col < dims.cols; col += 1) {
            const cell = cells[row][col];
            const marker = cell.querySelector(".figure-marker");
            const figure = findFigureAt(row, col);
            if (figure) {
                cell.classList.add("has-figure");
                marker.textContent = figure.label;
                marker.style.backgroundColor = figure.color;
            } else {
                cell.classList.remove("has-figure");
                marker.textContent = "";
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
        label.textContent = figure.label;

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

function addFigure() {
    const figureNumber = nextFigureNumber;
    nextFigureNumber += 1;
    const figure = {
        id: `F${figureNumber}`,
        label: `F${figureNumber}`,
        color: FIGURE_COLORS[(figureNumber - 1) % FIGURE_COLORS.length],
        position: null,
    };
    figures.push(figure);
    selectedFigureId = figure.id;
    renderFiguresList();
    showToast(`Dodano figurkę ${figure.label}. Kliknij na planszy w trybie przesuwania, aby ją ustawić.`);
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
            showToast(`Zaznaczono ${figureAtCell.label}.`);
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
    showToast(`Przeniesiono ${figure.label} na (${row}, ${col}).`);
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
    scenarioState.blocked = new Set(
        Array.isArray(scenario?.blocked_fields)
            ? scenario.blocked_fields.map((p) => `${p[0]},${p[1]}`)
            : [],
    );
    scenarioState.obstacles = new Set(
        Array.isArray(scenario?.obstacles)
            ? scenario.obstacles.map((p) => `${p[0]},${p[1]}`)
            : [],
    );
    scenarioState.walls = Array.isArray(scenario?.walls)
        ? scenario.walls.map((w) => ({
              a: { row: w.a[0], col: w.a[1] },
              b: { row: w.b[0], col: w.b[1] },
          }))
        : [];
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

function renderScenarioWalls() {
    if (!wallOverlay) return;
    wallOverlay.innerHTML = "";
    if (!scenarioState.visible) return;

    const boardRect = boardElement.getBoundingClientRect();
    const thickness = 6;
    const dotSize = 10;

    scenarioState.walls.forEach((wall) => {
        const cellA = cells?.[wall.a.row]?.[wall.a.col];
        const cellB = cells?.[wall.b.row]?.[wall.b.col];
        if (!cellA || !cellB) return;
        const rectA = cellA.getBoundingClientRect();
        const rectB = cellB.getBoundingClientRect();

        const segment = document.createElement("div");
        segment.className = "wall-line";

        if (wall.a.row === wall.b.row) {
            // ściana pionowa między sąsiadami w poziomie
            segment.classList.add("wall-line-v");
            const left = (rectA.right + rectB.left) / 2 - boardRect.left;
            const top = Math.min(rectA.top, rectB.top) - boardRect.top;
            const height = Math.max(rectA.height, rectB.height);
            segment.style.left = `${left - thickness / 2}px`;
            segment.style.top = `${top}px`;
            segment.style.width = `${thickness}px`;
            segment.style.height = `${height}px`;
        } else if (wall.a.col === wall.b.col) {
            // ściana pozioma między sąsiadami w pionie
            segment.classList.add("wall-line-h");
            const top = (rectA.bottom + rectB.top) / 2 - boardRect.top;
            const left = Math.min(rectA.left, rectB.left) - boardRect.left;
            const width = Math.max(rectA.width, rectB.width);
            segment.style.left = `${left}px`;
            segment.style.top = `${top - thickness / 2}px`;
            segment.style.width = `${width}px`;
            segment.style.height = `${thickness}px`;
        } else {
            // diagonalna -> kropka
            segment.classList.add("wall-line-diag");
            const midX = (rectA.left + rectA.width / 2 + rectB.left + rectB.width / 2) / 2 - boardRect.left;
            const midY = (rectA.top + rectA.height / 2 + rectB.top + rectB.height / 2) / 2 - boardRect.top;
            segment.style.left = `${midX - dotSize / 2}px`;
            segment.style.top = `${midY - dotSize / 2}px`;
            segment.style.width = `${dotSize}px`;
            segment.style.height = `${dotSize}px`;
        }

        wallOverlay.appendChild(segment);
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

addFigureButton?.addEventListener("click", addFigure);

scenarioReloadButton?.addEventListener("click", () => refreshScenarioList(scenarioState.name));
scenarioLoadButton?.addEventListener("click", () => loadScenario(scenarioSelect?.value));
scenarioToggleButton?.addEventListener("click", async () => {
    if (!scenarioState.name) {
        await loadScenario(scenarioSelect?.value);
    }
    toggleScenarioVisibility();
});

renderFiguresList();
refreshScenarioList("scenario_1").then(() => {
    if (scenarioSelect && scenarioSelect.value) {
        loadScenario(scenarioSelect.value);
    }
});
