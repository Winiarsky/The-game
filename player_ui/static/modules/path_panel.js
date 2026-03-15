function _formatPos(value) {
    if (Array.isArray(value) && value.length >= 2) {
        return `(${value[0]}, ${value[1]})`;
    }
    if (value && typeof value === "object") {
        const hasCol = value.col !== undefined || value.x !== undefined;
        const hasRow = value.row !== undefined || value.y !== undefined;
        if (hasCol && hasRow) {
            const col = value.col ?? value.x;
            const row = value.row ?? value.y;
            return `(${col}, ${row})`;
        }
    }
    if (value === null || value === undefined || value === "") {
        return "-";
    }
    return String(value);
}

function _updateSummary(refs, state) {
    const {
        pathSummary,
        pathRequested,
        pathConfirmed,
        pathCost,
        pathBudget,
        pathStatus,
        pathHint,
    } = refs;
    if (!pathSummary) return;
    const data = state.data || null;
    if (!data) {
        pathSummary.classList.add("hidden");
        if (pathRequested) pathRequested.textContent = "-";
        if (pathConfirmed) pathConfirmed.textContent = "-";
        if (pathCost) pathCost.textContent = "-";
        if (pathBudget) pathBudget.textContent = "-";
        if (pathStatus) pathStatus.textContent = "-";
        if (pathHint) pathHint.textContent = "";
        return;
    }
    pathSummary.classList.remove("hidden");
    if (pathRequested) pathRequested.textContent = _formatPos(data.requestedTarget);
    if (pathConfirmed) pathConfirmed.textContent = _formatPos(data.confirmedTarget);
    if (pathCost) pathCost.textContent = data.costText || "-";
    if (pathBudget) pathBudget.textContent = data.budgetText || "-";
    if (pathStatus) {
        pathStatus.textContent = data.statusText || "-";
        pathStatus.dataset.tone = data.statusTone || "neutral";
    }
    if (pathHint) pathHint.textContent = data.hintText || "";
}

export function showPathPreview(refs, payload = {}, currentState = { activeId: null, data: null }) {
    const id = payload.id || `path-${Date.now()}`;
    const requestedTarget = payload.requested_target ?? payload.requestedTarget ?? payload.target ?? null;
    const confirmedTarget = payload.target ?? null;
    const steps = payload.steps != null ? `${payload.steps} pól` : null;
    const feet = payload.feet != null ? `${payload.feet} stóp` : null;
    const budgetText = payload.budget_feet != null ? `${payload.budget_feet} stóp` : "-";
    const isTrimmed = Boolean(payload.trimmed);
    const isEnemy = String(payload.path_type || "").toLowerCase() === "enemy";
    const statusText = isTrimmed ? "Przycięta" : isEnemy ? "Ruch wroga" : "Do potwierdzenia";
    const statusTone = isTrimmed ? "warning" : isEnemy ? "enemy" : "info";
    const actorName = String(payload.actor_name || "").trim();
    let hintText = isEnemy
        ? "Wróg potwierdza ruch na wskazanym polu."
        : "Kliknij ostatnie podświetlone pole, aby wykonać ruch.";
    if (isTrimmed) {
        hintText = "Docelowy klik był poza budżetem ruchu, więc trasa została przycięta do najdalszego legalnego pola.";
    }
    if (payload.difficult) {
        hintText = `${hintText} Trasa obejmuje trudny teren (+5 stóp za pole).`;
    }

    const costText = [steps, feet].filter(Boolean).join(" · ") || "-";
    const toastParts = [];
    if (actorName) toastParts.push(actorName);
    if (confirmedTarget) toastParts.push(_formatPos(confirmedTarget));
    if (costText && costText !== "-") toastParts.push(costText);

    if (refs.pathToast) {
        refs.pathToast.textContent = toastParts.length ? toastParts.join(" · ") : "Wyznaczam trasę...";
        refs.pathToast.classList.remove("hidden");
    }

    const nextState = {
        activeId: id,
        data: {
            requestedTarget,
            confirmedTarget,
            costText,
            budgetText,
            statusText,
            statusTone,
            hintText,
        },
    };
    _updateSummary(refs, nextState);
    return nextState;
}

export function clearPathPreview(refs, currentState = { activeId: null, data: null }, id = null) {
    if (id && currentState.activeId && id !== currentState.activeId) {
        return currentState;
    }
    if (refs.pathToast) {
        refs.pathToast.classList.add("hidden");
    }
    const nextState = { activeId: null, data: null };
    _updateSummary(refs, nextState);
    return nextState;
}
