const boardElement = document.getElementById("board");
const pendingIndicator = document.getElementById("pending-indicator");
const lastClickLabel = document.getElementById("last-click");
const backgroundInput = document.getElementById("background-input");
const backgroundClearButton = document.getElementById("background-clear");
const dims = window.BOARD_DIMENSIONS || { rows: 15, cols: 20 };

boardElement.style.gridTemplateColumns = `repeat(${dims.cols}, 32px)`;

const cells = Array.from({ length: dims.rows }, () => Array(dims.cols).fill(null));

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
    return cell;
}

for (let row = 0; row < dims.rows; row += 1) {
    for (let col = 0; col < dims.cols; col += 1) {
        const cell = createCell(row, col);
        boardElement.appendChild(cell);
        cells[row][col] = cell;
    }
}

async function handleCellClick(row, col) {
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
    for (let row = 0; row < dims.rows; row += 1) {
        for (let col = 0; col < dims.cols; col += 1) {
            const cell = cells[row][col];
            const display = colorToDisplay(state?.[row]?.[col]);
            if (display) {
                const [r, g, b] = display.rgb;
                cell.style.backgroundColor = `rgba(${r}, ${g}, ${b}, ${display.alpha.toFixed(3)})`;
                cell.classList.add("active");
            } else {
                cell.style.backgroundColor = "";
                cell.classList.remove("active");
            }
        }
    }
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

backgroundInput?.addEventListener("change", handleBackgroundFile);
backgroundClearButton?.addEventListener("click", () => {
    if (backgroundInput) {
        backgroundInput.value = "";
    }
    clearBoardBackground();
    showToast("Usunięto tło planszy.");
});
