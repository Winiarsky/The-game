function pretty(value) {
    return String(value || "").replace(/_/g, " ").trim();
}

function statusTone(name = "") {
    const txt = String(name).toLowerCase();
    const badKeywords = ["poison", "wound", "bleed", "stun", "prone", "fear", "slow", "curse", "burn", "exhaust"];
    const goodKeywords = ["bless", "shield", "heroism", "haste", "buff", "guard", "aid", "inspire", "rage"];
    if (badKeywords.some((key) => txt.includes(key))) return "bad";
    if (goodKeywords.some((key) => txt.includes(key))) return "good";
    return "neutral";
}

function currentHp(hero) {
    const woundsNum = Number(hero.wounds ?? 0);
    const maxHpNum = Number(hero.maxHp ?? 0);
    if (Number.isNaN(woundsNum) || Number.isNaN(maxHpNum) || maxHpNum <= 0) {
        return null;
    }
    return Math.max(0, maxHpNum - woundsNum);
}

export function resolveArmorClass(hero) {
    if (!hero || typeof hero !== "object") return null;
    const base = Number(hero.acBase ?? hero.ac_base);
    const modifier = Number(hero.acModifier ?? hero.ac_modifier ?? 0);
    if (!Number.isNaN(base)) {
        const safeModifier = Number.isNaN(modifier) ? 0 : modifier;
        return base + safeModifier;
    }
    const total = Number(hero.ac);
    if (!Number.isNaN(total)) return total;
    return null;
}

function armorClassBreakdown(hero) {
    if (!hero || typeof hero !== "object") return "AC -";
    const total = resolveArmorClass(hero);
    const base = Number(hero.acBase ?? hero.ac_base);
    const modifier = Number(hero.acModifier ?? hero.ac_modifier ?? 0);
    if (total == null) return "AC -";
    if (Number.isNaN(base)) return `AC ${total}`;
    if (!modifier) return `AC ${base}`;
    const sign = modifier > 0 ? "+" : "-";
    return `AC ${total} (${base} ${sign} ${Math.abs(modifier)})`;
}

function formatPos(pos) {
    if (!Array.isArray(pos) || pos.length < 2) return "-";
    return `(${pos[0]}, ${pos[1]})`;
}

function spellSlotLabel(tier) {
    const raw = String(tier || "").toLowerCase().trim();
    if (!raw) return "";
    if (raw === "cantrip") return "Cantripy";
    if (raw.startsWith("rank_")) return `R${raw.slice(5)}`;
    return raw.replace(/_/g, " ");
}

function normalizeSpellcasting(rawSpellcasting) {
    if (!rawSpellcasting || typeof rawSpellcasting !== "object") return null;
    const asDict = (value) => (value && typeof value === "object" && !Array.isArray(value) ? value : {});
    const asList = (value) => (Array.isArray(value) ? value : []);
    return {
        enabled: Boolean(rawSpellcasting.enabled),
        className: rawSpellcasting.class_name || rawSpellcasting.className || "",
        focusPoints: Number(rawSpellcasting.focus_points ?? rawSpellcasting.focusPoints ?? 0) || 0,
        focusPoolMax: Number(rawSpellcasting.focus_pool_max ?? rawSpellcasting.focusPoolMax ?? 0) || 0,
        slotTotal: asDict(rawSpellcasting.slot_total || rawSpellcasting.slotTotal),
        slotRemaining: asDict(rawSpellcasting.slot_remaining || rawSpellcasting.slotRemaining),
        knownCounts: asDict(rawSpellcasting.known_counts || rawSpellcasting.knownCounts),
        knownSpells: asDict(rawSpellcasting.known_spells || rawSpellcasting.knownSpells),
    };
}

function spellcastingSummary(hero) {
    const spellcasting = normalizeSpellcasting(hero?.spellcasting);
    if (!spellcasting) return [];
    const rows = [];
    if (spellcasting.focusPoolMax > 0) {
        rows.push(`Focus ${spellcasting.focusPoints}/${spellcasting.focusPoolMax}`);
    }
    Object.keys(spellcasting.slotTotal)
        .sort()
        .forEach((tier) => {
            const total = Number(spellcasting.slotTotal[tier]);
            if (Number.isNaN(total) || total <= 0 || tier === "cantrip") return;
            const remaining = Number(spellcasting.slotRemaining[tier]);
            rows.push(`${spellSlotLabel(tier)} ${Number.isNaN(remaining) ? total : remaining}/${total}`);
        });
    return rows;
}

function spellListLine(spellcasting, tier) {
    if (!spellcasting || typeof spellcasting !== "object") return "";
    const raw = spellcasting.knownSpells && typeof spellcasting.knownSpells === "object" ? spellcasting.knownSpells[tier] : [];
    const list = Array.isArray(raw) ? raw : [];
    if (!list.length) return "";
    return list.map((item) => pretty(item)).join(", ");
}

function skillRanksShort(hero) {
    const ranks = hero.skillRanks && typeof hero.skillRanks === "object" ? hero.skillRanks : {};
    const trained = Array.isArray(hero.trainedSkills) ? hero.trainedSkills : [];
    const trainedIds = new Set(
        trained
            .map((item) => String(item || "").toLowerCase().trim())
            .filter(Boolean),
    );
    const allIds = new Set([
        ...Object.keys(ranks || {}).map((item) => String(item || "").toLowerCase().trim()),
        ...trainedIds,
    ]);
    const order = [
        "acrobatics",
        "arcana",
        "athletics",
        "crafting",
        "deception",
        "diplomacy",
        "intimidation",
        "medicine",
        "nature",
        "occultism",
        "performance",
        "religion",
        "society",
        "stealth",
        "survival",
        "thievery",
    ];
    const rows = [];
    order.forEach((skillId) => {
        if (!allIds.has(skillId)) return;
        const rawRank = String(ranks[skillId] || (trainedIds.has(skillId) ? "trained" : "untrained"))
            .toLowerCase()
            .trim();
        if (!rawRank || rawRank === "untrained") return;
        rows.push(`${pretty(skillId)} (${pretty(rawRank)})`);
    });
    return rows.join(", ");
}

function loreShort(hero) {
    return Array.isArray(hero.loreSkills) && hero.loreSkills.length ? hero.loreSkills.join(", ") : "";
}

function buildRosterEntries({ heroesMap, activeActorId, heroSelectPreview }) {
    const entries = Array.from(heroesMap.values()).map((hero) => ({
        ...hero,
        isPreview: false,
        isSynthetic: false,
    }));
    if (heroSelectPreview) {
        entries.unshift({
            ...heroSelectPreview,
            isPreview: true,
            isSynthetic: true,
        });
    }
    return entries.sort((left, right) => {
        const leftActive = String(left.id || "") === String(activeActorId || "");
        const rightActive = String(right.id || "") === String(activeActorId || "");
        if (leftActive !== rightActive) return leftActive ? -1 : 1;
        if (Boolean(left.creationInProgress) !== Boolean(right.creationInProgress)) {
            return left.creationInProgress ? -1 : 1;
        }
        return String(left.name || "").localeCompare(String(right.name || ""), "pl");
    });
}

function resolveDetailHero({
    rosterEntries,
    heroesMap,
    selectedHeroId,
    activeActorId,
    activePromptSource,
    creationPreviewHeroId,
}) {
    const selected = rosterEntries.find((entry) => String(entry.id || "") === String(selectedHeroId || ""));
    if (selected) return selected;

    if (activePromptSource === "hero_select") {
        const preview = rosterEntries.find((entry) => Boolean(entry.isPreview));
        if (preview) return preview;
    }

    if (activePromptSource === "character_creation" || creationPreviewHeroId) {
        const creationPreview =
            rosterEntries.find((entry) => String(entry.id || "") === String(creationPreviewHeroId || "")) ||
            Array.from(heroesMap.values()).find((entry) => Boolean(entry?.creationInProgress));
        if (creationPreview) return creationPreview;
    }

    const active = rosterEntries.find((entry) => String(entry.id || "") === String(activeActorId || ""));
    if (active) return active;

    return rosterEntries[0] || null;
}

function detailContextText(hero, activeActorId) {
    if (!hero) return "Brak aktywnego bohatera.";
    if (hero.isPreview) return "Podgląd wyboru bohatera";
    if (hero.creationInProgress) return "Podgląd tworzenia postaci";
    if (String(hero.id || "") === String(activeActorId || "")) return "Aktywny bohater";
    return "Wybrany bohater";
}

export function coerceHeroPreview(rawPreview, fallbackLabel = "", placeholderImage = "/static/placeholder.png") {
    const preview = rawPreview && typeof rawPreview === "object" ? rawPreview : {};
    const asDict = (value) => (value && typeof value === "object" && !Array.isArray(value) ? value : {});
    const asList = (value) => (Array.isArray(value) ? value : []);
    const name = String(preview.name || fallbackLabel || "Bohater");
    const levelValue = Number.parseInt(String(preview.level ?? ""), 10);
    return {
        id: String(preview.character_id || preview.characterId || preview.id || "__hero_select_preview__"),
        name,
        level: Number.isNaN(levelValue) ? null : levelValue,
        statuses: asList(preview.statuses),
        note: String(preview.note || "Podgląd bohatera"),
        wounds: preview.wounds ?? 0,
        pos: preview.pos ?? null,
        initiative: preview.initiative ?? null,
        image: preview.image || preview.portrait_image || placeholderImage,
        characterId: preview.character_id || preview.characterId || null,
        classId: preview.class_id || preview.classId || null,
        ancestryId: preview.ancestry_id || preview.ancestryId || null,
        heritageId: preview.heritage_id || preview.heritageId || null,
        ac: preview.ac ?? null,
        acBase: preview.ac_base ?? preview.acBase ?? preview.ac ?? null,
        acModifier: preview.ac_modifier ?? preview.acModifier ?? 0,
        maxHp: preview.max_hp ?? preview.maxHp ?? null,
        baseSpeedFeet: preview.speed_feet ?? preview.base_speed_feet ?? preview.baseSpeedFeet ?? null,
        abilityScores: asDict(preview.ability_scores || preview.abilityScores),
        abilityModifiers: asDict(preview.ability_modifiers || preview.abilityModifiers),
        skillRanks: asDict(preview.skill_ranks || preview.skillRanks),
        saveRanks: asDict(preview.save_ranks || preview.saveRanks),
        perceptionRank: preview.perception_rank || preview.perceptionRank || null,
        trainedSkills: asList(preview.trained_skills || preview.trainedSkills),
        loreSkills: asList(preview.lore_skills || preview.loreSkills),
        backgroundLabel: preview.background_label || preview.backgroundLabel || null,
        backgroundFeatId: preview.background_feat_id || preview.backgroundFeatId || null,
        handSlots: asDict(preview.hand_slots || preview.handSlots),
        moneyText: preview.money_text || preview.moneyText || null,
        bulkSummary: asDict(preview.bulk_summary || preview.bulkSummary),
        inventoryItems: asList(preview.inventory_items || preview.inventoryItems),
        spellcasting: normalizeSpellcasting(preview.spellcasting),
        creationInProgress: false,
    };
}

export function renderHeroesPanel({
    refs,
    heroesMap,
    activeActorId,
    activePromptSource,
    creationPreviewHeroId,
    selectedHeroId,
    heroSelectPreview,
    placeholderImage,
    onSelectHero,
    cloneCreationAbilityDefaults,
}) {
    const { heroesRoster, heroesDetail, heroDetailContext } = refs;
    if (!heroesRoster || !heroesDetail || !heroDetailContext) {
        return { selectedHeroId: null, detailHeroId: null };
    }

    const rosterEntries = buildRosterEntries({
        heroesMap,
        activeActorId,
        heroSelectPreview,
    });

    heroesRoster.innerHTML = "";
    if (!rosterEntries.length) {
        heroesRoster.classList.add("empty-note");
        heroesRoster.textContent = "Brak danych o bohaterach.";
        heroesDetail.className = "heroes-detail empty-note";
        heroesDetail.textContent = "Brak danych o bohaterze.";
        heroDetailContext.textContent = "Brak aktywnego bohatera.";
        return { selectedHeroId: null, detailHeroId: null };
    }

    heroesRoster.classList.remove("empty-note");
    rosterEntries.forEach((hero) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "hero-roster-item";
        const isSelected = String(hero.id || "") === String(selectedHeroId || "");
        const isActive = String(hero.id || "") === String(activeActorId || "");
        if (isSelected) item.classList.add("selected");
        if (isActive) item.classList.add("active");
        if (hero.creationInProgress || hero.isPreview) item.classList.add("preview");

        const portrait = document.createElement("div");
        portrait.className = "hero-roster-portrait";
        portrait.style.backgroundImage = `url('${hero.image || placeholderImage}')`;

        const body = document.createElement("div");
        body.className = "hero-roster-body";

        const head = document.createElement("div");
        head.className = "hero-roster-head";
        const name = document.createElement("div");
        name.className = "hero-roster-name";
        name.textContent = hero.name || "Bohater";
        head.appendChild(name);

        const flags = document.createElement("div");
        flags.className = "hero-roster-flags";
        if (isActive) {
            const flag = document.createElement("span");
            flag.className = "hero-roster-flag active";
            flag.textContent = "Aktywny";
            flags.appendChild(flag);
        }
        if (hero.creationInProgress) {
            const flag = document.createElement("span");
            flag.className = "hero-roster-flag preview";
            flag.textContent = "Preview";
            flags.appendChild(flag);
        } else if (hero.isPreview) {
            const flag = document.createElement("span");
            flag.className = "hero-roster-flag preview";
            flag.textContent = "Select";
            flags.appendChild(flag);
        }
        if (flags.children.length) {
            head.appendChild(flags);
        }

        const hpNow = currentHp(hero);
        const meta = document.createElement("div");
        meta.className = "hero-roster-meta";
        const metaRows = [
            hpNow != null ? `HP ${hpNow}/${hero.maxHp ?? "-"}` : "HP -",
            armorClassBreakdown(hero),
            `Pozycja ${formatPos(hero.pos)}`,
        ];
        metaRows.push(...spellcastingSummary(hero).slice(0, 2));
        meta.textContent = metaRows.join(" · ");

        const statuses = Array.isArray(hero.statuses) ? hero.statuses : [];
        const statusRow = document.createElement("div");
        statusRow.className = "hero-roster-statuses";
        if (statuses.length) {
            statuses.slice(0, 3).forEach((status) => {
                const pill = document.createElement("span");
                pill.className = `status-pill ${statusTone(status)}`;
                pill.textContent = status;
                statusRow.appendChild(pill);
            });
            if (statuses.length > 3) {
                const more = document.createElement("span");
                more.className = "status-pill neutral";
                more.textContent = `+${statuses.length - 3}`;
                statusRow.appendChild(more);
            }
        } else {
            const pill = document.createElement("span");
            pill.className = "status-pill neutral";
            pill.textContent = "brak statusów";
            statusRow.appendChild(pill);
        }

        body.appendChild(head);
        body.appendChild(meta);
        body.appendChild(statusRow);
        item.appendChild(portrait);
        item.appendChild(body);
        item.addEventListener("click", () => onSelectHero(String(hero.id || "")));
        heroesRoster.appendChild(item);
    });

    const detailHero = resolveDetailHero({
        rosterEntries,
        heroesMap,
        selectedHeroId,
        activeActorId,
        activePromptSource,
        creationPreviewHeroId,
    });
    const resolvedSelectedHeroId = detailHero ? String(detailHero.id || "") : null;
    heroDetailContext.textContent = detailContextText(detailHero, activeActorId);

    if (!detailHero) {
        heroesDetail.className = "heroes-detail empty-note";
        heroesDetail.textContent = "Brak danych o bohaterze.";
        return { selectedHeroId: null, detailHeroId: null };
    }

    heroesDetail.className = "heroes-detail";

    const statuses = Array.isArray(detailHero.statuses) ? detailHero.statuses : [];
    const statusPills = statuses.length
        ? statuses.map((status) => `<span class="status-pill ${statusTone(status)}">${status}</span>`).join("")
        : '<span class="status-pill neutral">brak statusów</span>';

    const noteLine = detailHero.note ? `<div class="hero-notes">Etap: ${detailHero.note}</div>` : "";
    const levelLine = detailHero.level != null ? `Poziom ${detailHero.level}` : "Poziom -";
    const backgroundFeatLabel = detailHero.backgroundFeatId
        ? String(detailHero.backgroundFeatId).replace(/_/g, " ")
        : "";
    const backgroundFeatLine = backgroundFeatLabel
        ? `<div class="hero-notes">Background feat: ${backgroundFeatLabel}</div>`
        : "";
    const previewInstinctLine = detailHero.previewBarbarianInstinctId
        ? `<div class="hero-notes">Instynkt: ${pretty(detailHero.previewBarbarianInstinctId)}</div>`
        : "";
    const backgroundSkillsLine = detailHero.backgroundSkillTrainingUi
        ? `<div class="hero-notes">BG skille/Lore: ${detailHero.backgroundSkillTrainingUi}</div>`
        : "";
    const backgroundBoostsLine = detailHero.backgroundAbilityBoostsUi
        ? `<div class="hero-notes">BG ability boosts: ${detailHero.backgroundAbilityBoostsUi}</div>`
        : "";
    const classLabel = detailHero.classId ? pretty(detailHero.classId) : "-";
    const ancestryLabel = detailHero.ancestryId ? pretty(detailHero.ancestryId) : "-";
    const heritageLabel = detailHero.heritageId ? pretty(detailHero.heritageId) : "-";
    const hpNow = currentHp(detailHero);
    const hpLine = `HP: ${hpNow != null ? hpNow : "-"}/${detailHero.maxHp ?? "-"} · Rany: ${detailHero.wounds ?? "-"}`;
    const speedLine = `${armorClassBreakdown(detailHero)} · Speed: ${detailHero.baseSpeedFeet ?? "-"} ft`;
    const saves = detailHero.saveRanks && typeof detailHero.saveRanks === "object" ? detailHero.saveRanks : {};
    const saveLine = `Save: F ${pretty(saves.fortitude || "untrained")} · R ${pretty(saves.reflex || "untrained")} · W ${pretty(saves.will || "untrained")}`;
    const perceptionLine = `Percepcja: ${pretty(detailHero.perceptionRank || "untrained")}`;
    const rawScores = detailHero.abilityScores && typeof detailHero.abilityScores === "object" ? detailHero.abilityScores : {};
    const rawMods = detailHero.abilityModifiers && typeof detailHero.abilityModifiers === "object" ? detailHero.abilityModifiers : {};
    const missingAbilityScores = !rawScores || Object.keys(rawScores).length === 0;
    const defaults = cloneCreationAbilityDefaults();
    const creationContextForHero =
        detailHero.creationInProgress ||
        String(detailHero.id || "") === "__creation_preview__" ||
        activePromptSource === "character_creation";
    const scores = creationContextForHero && missingAbilityScores ? defaults.abilityScores : rawScores;
    const mods = creationContextForHero && missingAbilityScores ? defaults.abilityModifiers : rawMods;
    const abilityOrder = [
        ["strength", "STR"],
        ["dexterity", "DEX"],
        ["constitution", "CON"],
        ["intelligence", "INT"],
        ["wisdom", "WIS"],
        ["charisma", "CHA"],
    ];
    const abilityLine = abilityOrder
        .map(([id, short]) => {
            if (scores[id] == null) return "";
            const modRaw = Number(mods[id] ?? 0);
            const modText = `${modRaw >= 0 ? "+" : ""}${modRaw}`;
            return `<span class="hero-ability-chip">${short} ${scores[id]} (${modText})</span>`;
        })
        .filter(Boolean)
        .join("");
    const abilitiesBody = abilityLine || `<div class="hero-notes">Brak danych o cechach.</div>`;
    const skillRanksLabel = skillRanksShort(detailHero) || "brak wytrenowanych";
    const loreLabel = loreShort(detailHero) || "-";
    const handSlots = detailHero.handSlots || {};
    const leftHand = handSlots.left?.label || "Pusta ręka";
    const rightHand = handSlots.right?.label || "Pusta ręka";
    const handMode = handSlots.mode_label || handSlots.mode || "";
    const handsLine = `Ręce: L=${leftHand} · P=${rightHand}${handMode ? ` · ${handMode}` : ""}`;
    const moneyLine = detailHero.moneyText ? `Sakiewka: ${detailHero.moneyText}` : "Sakiewka: -";
    const bulkLine =
        detailHero.bulkSummary && typeof detailHero.bulkSummary === "object"
            ? `Bulk: ${detailHero.bulkSummary.total_display || "-"} / ${detailHero.bulkSummary.encumbered_limit_display || "-"} (enc.)`
            : "Bulk: -";
    const inventoryItems = Array.isArray(detailHero.inventoryItems) ? detailHero.inventoryItems : [];
    const inventoryLabel = inventoryItems.length ? inventoryItems.join(", ") : "brak";
    const spellcasting = normalizeSpellcasting(detailHero.spellcasting);
    const spellSummaryRows = spellcastingSummary(detailHero);
    const slotLine = spellSummaryRows.length ? spellSummaryRows.join(" · ") : "Brak liczników slotów.";
    const cantripLine = spellListLine(spellcasting, "cantrip");
    const rank1Line = spellListLine(spellcasting, "rank_1");
    const focusLine = spellListLine(spellcasting, "focus");
    const section = (title, body) =>
        `<div class="hero-section"><div class="hero-section-title">${title}</div><div class="hero-section-body">${body}</div></div>`;

    const identityBody = `
        <div class="hero-stats">${levelLine}</div>
        <div class="hero-stats">Klasa: ${classLabel}</div>
        <div class="hero-stats">Rasa: ${ancestryLabel}</div>
        <div class="hero-stats">Heritage: ${heritageLabel}</div>
        ${detailHero.backgroundLabel ? `<div class="hero-stats">Background: ${detailHero.backgroundLabel}</div>` : ""}
        ${backgroundFeatLine}
        ${previewInstinctLine}
        ${backgroundSkillsLine}
        ${backgroundBoostsLine}
        ${noteLine}
    `;
    const combatBody = `
        <div class="hero-stats">${hpLine}</div>
        <div class="hero-stats">${speedLine}</div>
        <div class="hero-stats">${saveLine}</div>
        <div class="hero-stats">${perceptionLine}</div>
        <div class="hero-stats">Pozycja: ${formatPos(detailHero.pos)}</div>
    `;
    const skillsBody = `
        <div class="hero-notes">Biegłości: ${skillRanksLabel}</div>
        <div class="hero-notes">Lore: ${loreLabel}</div>
    `;
    const statusBody = `
        <div class="hero-statuses">${statusPills}</div>
        <div class="hero-notes">Lista: ${statuses.length ? statuses.join(", ") : "brak"}</div>
    `;
    const equipmentBody = `
        <div class="hero-stats">${handsLine}</div>
        <div class="hero-stats">${moneyLine}</div>
        <div class="hero-stats">${bulkLine}</div>
        <div class="hero-notes">Ekwipunek: ${inventoryLabel}</div>
    `;
    const magicBody = spellcasting
        ? `
        <div class="hero-stats">${slotLine}</div>
        <div class="hero-notes">Cantripy: ${cantripLine || "brak"}</div>
        <div class="hero-notes">Czary R1: ${rank1Line || "brak"}</div>
        <div class="hero-notes">Focus spelle: ${focusLine || "brak"}</div>
    `
        : `<div class="hero-notes">Brak aktywnego spellcasting runtime.</div>`;

    heroesDetail.innerHTML = `
        <div class="hero-card detail-card ${String(detailHero.id || "") === String(activeActorId || "") ? "active" : ""}">
            <div class="hero-row detail-row">
                <div class="hero-info">
                    <div class="hero-name">${detailHero.name}</div>
                    ${section("Tożsamość", identityBody)}
                    ${section("Walka", combatBody)}
                    ${section("Cechy", abilitiesBody)}
                    ${section("Skille", skillsBody)}
                    ${section("Statusy", statusBody)}
                    ${section("Ekwipunek", equipmentBody)}
                    ${section("Magia", magicBody)}
                </div>
                <div class="hero-portrait detail-portrait" style="background-image: url('${detailHero.image || placeholderImage}')"></div>
            </div>
        </div>
    `;

    return {
        selectedHeroId: resolvedSelectedHeroId,
        detailHeroId: resolvedSelectedHeroId,
    };
}
