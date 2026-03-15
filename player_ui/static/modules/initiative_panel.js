export function renderInitiativePanel(refs, initiativeState) {
    const {
        initiativeList,
        initiativeSummary,
        initActiveName,
        initNextName,
        initRoundNum,
    } = refs;

    if (!initiativeList) return;
    const { order, activeId, round } = initiativeState;
    if (!order || order.length === 0) {
        initiativeList.classList.add("empty-note");
        initiativeList.textContent = "Brak danych o inicjatywie.";
        if (initiativeSummary) {
            initiativeSummary.classList.add("hidden");
        }
        return;
    }

    if (initiativeSummary) {
        initiativeSummary.classList.remove("hidden");
    }
    initiativeList.classList.remove("empty-note");
    initiativeList.innerHTML = "";

    const activeIdx = order.findIndex((entry) => String(entry.id) === String(activeId));
    const activeEntry = activeIdx >= 0 ? order[activeIdx] : null;
    const nextEntry = activeIdx >= 0 && order.length > 1 ? order[(activeIdx + 1) % order.length] : null;
    if (initActiveName) initActiveName.textContent = activeEntry ? activeEntry.name : "-";
    if (initNextName) initNextName.textContent = nextEntry ? nextEntry.name : "-";
    if (initRoundNum) initRoundNum.textContent = round ?? "-";

    order.forEach((entry) => {
        const card = document.createElement("div");
        card.className = "initiative-card " + (entry.kind === "hero" ? "hero" : "enemy");
        if (String(entry.id) === String(activeId)) {
            card.classList.add("active");
        }
        if (entry.done) {
            card.classList.add("done");
        }

        const name = document.createElement("div");
        name.className = "initiative-name";
        name.textContent = entry.name || "aktor";

        const vals = document.createElement("div");
        vals.className = "initiative-vals";
        const base = entry.base ?? entry.current;
        const current = entry.current ?? base;
        const delta = entry.delta || 0;
        const hasDelta = delta !== 0;
        vals.textContent = `${current}`;
        if (hasDelta) {
            const deltaEl = document.createElement("span");
            deltaEl.className = "delta " + (delta < 0 ? "negative" : "positive");
            deltaEl.textContent = delta < 0 ? `↓ ${Math.abs(delta)}` : `↑ ${delta}`;
            vals.appendChild(deltaEl);

            const baseEl = document.createElement("span");
            baseEl.className = "delta";
            baseEl.textContent = `(${base})`;
            vals.appendChild(baseEl);
        }

        card.appendChild(name);
        card.appendChild(vals);
        initiativeList.appendChild(card);
    });
}
