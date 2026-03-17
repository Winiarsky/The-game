import { PLACEHOLDER_IMAGE, refs } from "./modules/dom.js";
import { renderHeroesPanel, coerceHeroPreview, resolveArmorClass } from "./modules/heroes_panel.js";
import { renderInitiativePanel } from "./modules/initiative_panel.js";
import { clearPathPreview, showPathPreview } from "./modules/path_panel.js";

const {
    screenMenu,
    screenGame,
    logList,
    logLast,
    logFab,
    debugUndoBtn,
    logModal,
    logClose,
    initiativeList,
    initiativeSummary,
    initActiveName,
    initNextName,
    initRoundNum,
    actionIllustration,
    actionTitle,
    actionText,
    actionPrompt,
    actionChoices,
    actionDesc,
    actionForm,
    actionAnswer,
    rollNaturalControls,
    nat20Toggle,
    nat1Toggle,
    natModeHint,
    actionKind,
    actionSource,
    modsBox,
    modsPenCirc,
    modsBonCirc,
    modsPenStat,
    modsBonStat,
    modsPenItem,
    modsBonItem,
    topbar,
    topbarToggle,
    eventFeed,
    statusScenario,
    statusActor,
    statusNext,
    statusRound,
    statusPrompt,
} = refs;

let currentScenario = null;
let currentSessionId = null;
let eventSource = null;
const renderedPrompts = new Set();
const heroes = new Map();
let promptQueue = [];
let activePrompt = null;
let currentChoices = [];
let selectedChoiceIndex = -1;
let choiceMeta = [];
let confirmMode = false;
let storedSelection = "";
let layoutMode = "info";
let rollNaturalMode = "none";
let fileImagePayload = null;
let rollStackState = null;
let pathState = { activeId: null, data: null };
let initiativeState = { order: [], activeId: null, round: 1 };
let activeActorId = null;
let lastLoggedRound = null;
let lastLoggedActiveActorId = null;
let creationPreviewHeroId = null;
let selectedHeroId = null;
const CREATION_PREVIEW_FALLBACK_ID = "__creation_preview__";
let menuNumpadContext = null;
actionForm.classList.add("hidden");
const DEBUG_UNDO_COMMAND = "__debug_undo__";
const DEFAULT_CREATION_ABILITY_SCORES = {
    strength: 10,
    dexterity: 10,
    constitution: 10,
    intelligence: 10,
    wisdom: 10,
    charisma: 10,
};
const DEFAULT_CREATION_ABILITY_MODIFIERS = {
    strength: 0,
    dexterity: 0,
    constitution: 0,
    intelligence: 0,
    wisdom: 0,
    charisma: 0,
};

function _cloneCreationAbilityDefaults() {
    return {
        abilityScores: { ...DEFAULT_CREATION_ABILITY_SCORES },
        abilityModifiers: { ...DEFAULT_CREATION_ABILITY_MODIFIERS },
    };
}

function _resetMenuNumpadContext() {
    menuNumpadContext = null;
    if (actionChoices) {
        actionChoices.classList.remove("choice-columns-mode");
    }
}

function _isGroupedMenuNumpad() {
    if (!menuNumpadContext || !menuNumpadContext.enabled) return false;
    const groups = menuNumpadContext.groups || {};
    return Array.isArray(groups.filters) && Array.isArray(groups.list) && groups.filters.length > 0 && groups.list.length > 0;
}

function _groupIndices(name) {
    if (!_isGroupedMenuNumpad()) return [];
    return Array.isArray(menuNumpadContext.groups?.[name]) ? menuNumpadContext.groups[name] : [];
}

function _setGroupedMenuActive(name) {
    if (!_isGroupedMenuNumpad()) return;
    const groupName = name === "filters" ? "filters" : "list";
    const indices = _groupIndices(groupName);
    if (!indices.length) return;
    menuNumpadContext.activeGroup = groupName;
    if (!indices.includes(selectedChoiceIndex)) {
        selectChoice(indices[0]);
        return;
    }
    updateChoiceHighlight();
}

function _moveGroupedMenuSelection(delta) {
    if (!_isGroupedMenuNumpad()) return false;
    const step = Number.parseInt(String(delta || 0), 10);
    if (!step) return false;
    const groupName = menuNumpadContext.activeGroup === "filters" ? "filters" : "list";
    const indices = _groupIndices(groupName);
    if (!indices.length) return false;
    let currentPos = indices.indexOf(selectedChoiceIndex);
    if (currentPos < 0) currentPos = 0;
    const nextPos = (currentPos + (step > 0 ? 1 : -1) + indices.length) % indices.length;
    selectChoice(indices[nextPos]);
    return true;
}

function _isNaturalRollPrompt(prompt) {
    if (!prompt) return false;
    const kind = String(prompt.kind || "").toLowerCase();
    const layout = String(prompt.layout || "").toLowerCase();
    if (layout === "damage") return false;
    return layout === "test" || kind === "roll";
}

function _setNaturalMode(mode) {
    const next = mode === "nat20" || mode === "nat1" ? mode : "none";
    rollNaturalMode = next;
    if (nat20Toggle) nat20Toggle.classList.toggle("active", next === "nat20");
    if (nat1Toggle) nat1Toggle.classList.toggle("active", next === "nat1");
}

function _cycleNaturalMode() {
    if (rollNaturalMode === "none") _setNaturalMode("nat20");
    else if (rollNaturalMode === "nat20") _setNaturalMode("nat1");
    else _setNaturalMode("none");
}

function _isUpNavigationKey(evt) {
    const key = String(evt?.key || "");
    const code = String(evt?.code || "");
    return key === "8" || key === "ArrowUp" || code === "Numpad8";
}

function _isDownNavigationKey(evt) {
    const key = String(evt?.key || "");
    const code = String(evt?.code || "");
    return key === "2" || key === "ArrowDown" || code === "Numpad2";
}

function _renderNaturalControls(prompt) {
    const visible = _isNaturalRollPrompt(prompt);
    if (!rollNaturalControls) return;
    if (!visible) {
        rollNaturalControls.classList.add("hidden");
        return;
    }
    rollNaturalControls.classList.remove("hidden");
    if (natModeHint) {
        natModeHint.textContent = "* : brak -> nat20 -> nat1";
    }
    _setNaturalMode(rollNaturalMode);
}

if (nat20Toggle) {
    nat20Toggle.addEventListener("click", () => {
        _setNaturalMode(rollNaturalMode === "nat20" ? "none" : "nat20");
    });
}
if (nat1Toggle) {
    nat1Toggle.addEventListener("click", () => {
        _setNaturalMode(rollNaturalMode === "nat1" ? "none" : "nat1");
    });
}

function setIllustration(imageUrl) {
    const src = imageUrl || PLACEHOLDER_IMAGE;
    if (src) {
        actionIllustration.style.backgroundImage = `url(${src})`;
        actionIllustration.style.backgroundSize = "cover";
        actionIllustration.style.backgroundPosition = "center";
    } else {
        actionIllustration.style.backgroundImage = "";
    }
}

function _renderFileImagePicker() {
    fileImagePayload = null;
    actionChoices.innerHTML = "";
    actionDesc.classList.remove("hidden");
    actionDesc.textContent = "Wybierz plik obrazu portretu, ustaw kadr (przeciągnij + zoom), potem Enter.";

    const wrapper = document.createElement("div");
    wrapper.className = "file-picker";

    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*,.jpg,.jpeg,.png,.webp,.svg";
    input.className = "file-picker-input";

    const hint = document.createElement("div");
    hint.className = "file-picker-hint";
    hint.textContent = "Obsługiwane formaty: JPG, PNG, WEBP, SVG. Przeciągnij obraz, aby przesunąć kadr.";

    const cropWrap = document.createElement("div");
    cropWrap.className = "file-cropper hidden";

    const cropCanvas = document.createElement("canvas");
    cropCanvas.className = "file-cropper-canvas";
    cropCanvas.width = 320;
    cropCanvas.height = 400;
    cropCanvas.setAttribute("aria-label", "Edytor kadru portretu");

    const zoomWrap = document.createElement("label");
    zoomWrap.className = "file-cropper-zoom";
    zoomWrap.textContent = "Zoom";

    const zoomInput = document.createElement("input");
    zoomInput.type = "range";
    zoomInput.min = "100";
    zoomInput.max = "300";
    zoomInput.step = "1";
    zoomInput.value = "100";
    zoomInput.disabled = true;

    const zoomValue = document.createElement("span");
    zoomValue.className = "file-cropper-zoom-value";
    zoomValue.textContent = "100%";
    zoomWrap.appendChild(zoomInput);
    zoomWrap.appendChild(zoomValue);

    const cropHint = document.createElement("div");
    cropHint.className = "file-cropper-hint";
    cropHint.textContent = "Przeciągnij obraz, aby ustawić pozycję w ramce.";

    cropWrap.appendChild(cropCanvas);
    cropWrap.appendChild(zoomWrap);
    cropWrap.appendChild(cropHint);

    const cropState = {
        image: null,
        imageWidth: 0,
        imageHeight: 0,
        zoom: 1,
        minScale: 1,
        scale: 1,
        offsetX: 0,
        offsetY: 0,
        dragging: false,
        dragLastX: 0,
        dragLastY: 0,
        outputMime: "image/jpeg",
        filename: "",
    };

    const _clamp = (value, min, max) => Math.min(max, Math.max(min, value));

    const _clampOffsets = () => {
        const scaledWidth = cropState.imageWidth * cropState.scale;
        const scaledHeight = cropState.imageHeight * cropState.scale;
        const maxOffsetX = Math.max(0, (scaledWidth - cropCanvas.width) / 2);
        const maxOffsetY = Math.max(0, (scaledHeight - cropCanvas.height) / 2);
        cropState.offsetX = _clamp(cropState.offsetX, -maxOffsetX, maxOffsetX);
        cropState.offsetY = _clamp(cropState.offsetY, -maxOffsetY, maxOffsetY);
    };

    const _exportCropPayload = () => {
        if (!cropState.image) return null;
        const scaledWidth = cropState.imageWidth * cropState.scale;
        const scaledHeight = cropState.imageHeight * cropState.scale;
        const drawX = (cropCanvas.width - scaledWidth) / 2 + cropState.offsetX;
        const drawY = (cropCanvas.height - scaledHeight) / 2 + cropState.offsetY;
        const sourceX = _clamp((0 - drawX) / cropState.scale, 0, cropState.imageWidth);
        const sourceY = _clamp((0 - drawY) / cropState.scale, 0, cropState.imageHeight);
        const sourceW = _clamp(cropCanvas.width / cropState.scale, 1, cropState.imageWidth - sourceX);
        const sourceH = _clamp(cropCanvas.height / cropState.scale, 1, cropState.imageHeight - sourceY);

        const outCanvas = document.createElement("canvas");
        outCanvas.width = 640;
        outCanvas.height = 800;
        const outCtx = outCanvas.getContext("2d");
        if (!outCtx) return null;
        outCtx.drawImage(
            cropState.image,
            sourceX,
            sourceY,
            sourceW,
            sourceH,
            0,
            0,
            outCanvas.width,
            outCanvas.height
        );
        const dataUrl =
            cropState.outputMime === "image/jpeg"
                ? outCanvas.toDataURL(cropState.outputMime, 0.92)
                : outCanvas.toDataURL(cropState.outputMime);
        return {
            filename: cropState.filename || "portrait.jpg",
            mime: cropState.outputMime,
            data_url: dataUrl,
        };
    };

    const _renderCrop = () => {
        const ctx = cropCanvas.getContext("2d");
        if (!ctx) return;
        ctx.clearRect(0, 0, cropCanvas.width, cropCanvas.height);
        if (!cropState.image) return;
        cropState.scale = cropState.minScale * cropState.zoom;
        _clampOffsets();
        const drawWidth = cropState.imageWidth * cropState.scale;
        const drawHeight = cropState.imageHeight * cropState.scale;
        const drawX = (cropCanvas.width - drawWidth) / 2 + cropState.offsetX;
        const drawY = (cropCanvas.height - drawHeight) / 2 + cropState.offsetY;
        ctx.drawImage(cropState.image, drawX, drawY, drawWidth, drawHeight);
        fileImagePayload = _exportCropPayload();
    };

    input.addEventListener("change", () => {
        const file = input.files && input.files[0] ? input.files[0] : null;
        if (!file) {
            fileImagePayload = null;
            cropWrap.classList.add("hidden");
            zoomInput.disabled = true;
            actionDesc.textContent = "Wybierz plik obrazu portretu, ustaw kadr (przeciągnij + zoom), potem Enter.";
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            fileImagePayload = null;
            cropWrap.classList.add("hidden");
            zoomInput.disabled = true;
            actionDesc.textContent = "Plik jest za duży (limit: 5 MB).";
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            const dataUrl = String(reader.result || "");
            const image = new Image();
            image.onload = () => {
                cropState.image = image;
                cropState.imageWidth = Math.max(1, image.naturalWidth || image.width || 1);
                cropState.imageHeight = Math.max(1, image.naturalHeight || image.height || 1);
                cropState.zoom = 1;
                cropState.offsetX = 0;
                cropState.offsetY = 0;
                cropState.filename = file.name || "portrait.jpg";
                if (file.type === "image/png" || file.type === "image/webp") {
                    cropState.outputMime = file.type;
                } else {
                    cropState.outputMime = "image/jpeg";
                }
                cropState.minScale = Math.max(
                    cropCanvas.width / cropState.imageWidth,
                    cropCanvas.height / cropState.imageHeight
                );
                zoomInput.value = "100";
                zoomValue.textContent = "100%";
                zoomInput.disabled = false;
                cropWrap.classList.remove("hidden");
                _renderCrop();
                const kb = Math.max(1, Math.round(file.size / 1024));
                actionDesc.textContent = `Wybrano: ${file.name} (${kb} KB). Przesuń/zoomuj i naciśnij Enter.`;
            };
            image.onerror = () => {
                fileImagePayload = null;
                cropWrap.classList.add("hidden");
                zoomInput.disabled = true;
                actionDesc.textContent = "Nie udało się odczytać obrazu.";
            };
            image.src = dataUrl;
        };
        reader.onerror = () => {
            fileImagePayload = null;
            cropWrap.classList.add("hidden");
            zoomInput.disabled = true;
            actionDesc.textContent = "Nie udało się odczytać pliku.";
        };
        reader.readAsDataURL(file);
    });

    zoomInput.addEventListener("input", () => {
        const raw = Number.parseInt(String(zoomInput.value || "100"), 10);
        const value = Number.isNaN(raw) ? 100 : Math.min(300, Math.max(100, raw));
        cropState.zoom = value / 100;
        zoomValue.textContent = `${value}%`;
        _renderCrop();
    });

    cropCanvas.addEventListener("pointerdown", (event) => {
        if (!cropState.image) return;
        cropState.dragging = true;
        cropState.dragLastX = event.clientX;
        cropState.dragLastY = event.clientY;
        cropCanvas.setPointerCapture(event.pointerId);
    });

    cropCanvas.addEventListener("pointermove", (event) => {
        if (!cropState.dragging || !cropState.image) return;
        const rect = cropCanvas.getBoundingClientRect();
        const ratioX = rect.width > 0 ? cropCanvas.width / rect.width : 1;
        const ratioY = rect.height > 0 ? cropCanvas.height / rect.height : 1;
        const deltaX = (event.clientX - cropState.dragLastX) * ratioX;
        const deltaY = (event.clientY - cropState.dragLastY) * ratioY;
        cropState.dragLastX = event.clientX;
        cropState.dragLastY = event.clientY;
        cropState.offsetX += deltaX;
        cropState.offsetY += deltaY;
        _renderCrop();
    });

    const _endDrag = (event) => {
        cropState.dragging = false;
        try {
            cropCanvas.releasePointerCapture(event.pointerId);
        } catch (_err) {
            // ignore
        }
    };

    cropCanvas.addEventListener("pointerup", _endDrag);
    cropCanvas.addEventListener("pointercancel", _endDrag);
    cropCanvas.addEventListener("pointerleave", () => {
        cropState.dragging = false;
    });

    wrapper.appendChild(input);
    wrapper.appendChild(hint);
    wrapper.appendChild(cropWrap);
    actionChoices.appendChild(wrapper);
    input.focus();
}

function clearMods() {
    [modsPenCirc, modsBonCirc, modsPenStat, modsBonStat, modsPenItem, modsBonItem].forEach((el) => {
        if (el) el.innerHTML = "";
    });
    modsBox.classList.add("hidden");
}

function renderMods(mods = {}) {
    const { penCirc = [], bonCirc = [], penStat = [], bonStat = [], penItem = [], bonItem = [] } = mods;
    const fill = (el, arr) => {
        if (!el) return;
        el.innerHTML = "";
        arr.forEach((item, idx) => {
            const li = document.createElement("li");
            li.className = idx === 0 ? "top" : "";
            const label = document.createElement("span");
            label.textContent = item.label || item.tag || item.name || "mod";
            const val = document.createElement("span");
            val.className = "mods-value";
            val.textContent = item.value != null ? item.value : "";
            li.appendChild(label);
            li.appendChild(val);
            el.appendChild(li);
        });
    };
    clearMods();
    const hasAny =
        penCirc.length || bonCirc.length || penStat.length || bonStat.length || penItem.length || bonItem.length;
    if (!hasAny) return;
    fill(modsPenCirc, penCirc);
    fill(modsBonCirc, bonCirc);
    fill(modsPenStat, penStat);
    fill(modsBonStat, bonStat);
    fill(modsPenItem, penItem);
    fill(modsBonItem, bonItem);
    modsBox.classList.remove("hidden");
}

function _toInt(value, fallback = 0) {
    const parsed = Number.parseInt(String(value ?? ""), 10);
    return Number.isNaN(parsed) ? fallback : parsed;
}

function _isRollStackPrompt(prompt) {
    if (!prompt) return false;
    const layout = String(prompt.layout || "").toLowerCase();
    if (layout !== "test" && layout !== "damage") return false;
    if (prompt.roll_stack && typeof prompt.roll_stack === "object") return true;
    return !!(prompt.modifiers && typeof prompt.modifiers === "object");
}

function _modifierBucketTotal(mods, bonusKey, penaltyKey) {
    const bonuses = Array.isArray(mods?.[bonusKey]) ? mods[bonusKey] : [];
    const penalties = Array.isArray(mods?.[penaltyKey]) ? mods[penaltyKey] : [];
    const plus = bonuses.reduce((acc, row) => acc + Math.abs(_toInt(row?.value, 0)), 0);
    const minus = penalties.reduce((acc, row) => acc + Math.abs(_toInt(row?.value, 0)), 0);
    return plus - minus;
}

function _buildRollStackSeed(prompt) {
    const stack = prompt?.roll_stack && typeof prompt.roll_stack === "object" ? prompt.roll_stack : {};
    const components = [];
    const seedComponents = Array.isArray(stack.components) ? stack.components : [];

    if (seedComponents.length) {
        seedComponents.forEach((row, idx) => {
            const value = _toInt(row?.value, 0);
            components.push({
                id: String(row?.id || `component_${idx + 1}`),
                label: String(row?.label || `Składnik ${idx + 1}`),
                value,
                baseValue: value,
                description: String(row?.description || row?.desc || ""),
                editable: row?.editable !== false,
                isDie: false,
            });
        });
    } else {
        const mods = prompt?.modifiers && typeof prompt.modifiers === "object" ? prompt.modifiers : null;
        if (mods) {
            const derived = [
                {
                    id: "circumstance",
                    label: "Okoliczności",
                    value: _modifierBucketTotal(mods, "bonCirc", "penCirc"),
                    description: "Premie i kary circumstance.",
                },
                {
                    id: "status",
                    label: "Status",
                    value: _modifierBucketTotal(mods, "bonStat", "penStat"),
                    description: "Premie i kary status.",
                },
                {
                    id: "item",
                    label: "Przedmiot",
                    value: _modifierBucketTotal(mods, "bonItem", "penItem"),
                    description: "Premie i kary item.",
                },
            ];
            derived.forEach((row) => {
                if (!row.value) return;
                components.push({
                    ...row,
                    baseValue: row.value,
                    editable: true,
                    isDie: false,
                });
            });
        }
    }

    const componentsTotal = components.reduce((acc, row) => acc + _toInt(row.value, 0), 0);
    const hasAutoTotal = stack.auto_total_modifier !== undefined && stack.auto_total_modifier !== null;
    const autoTotal = hasAutoTotal ? _toInt(stack.auto_total_modifier, componentsTotal) : componentsTotal;

    if (autoTotal !== componentsTotal) {
        const diff = autoTotal - componentsTotal;
        components.push({
            id: "other_auto",
            label: "Pozostałe",
            value: diff,
            baseValue: diff,
            description: "Pozostały automatyczny modyfikator.",
            editable: true,
            isDie: false,
        });
    }

    return {
        defaultRoll: _toInt(stack.default_roll, 0),
        components,
    };
}

function _rollStackEditableIndices() {
    if (!rollStackState) return [];
    const list = [];
    rollStackState.fields.forEach((field, idx) => {
        if (field?.editable) list.push(idx);
    });
    return list;
}

function _rollStackEnsureFocus() {
    if (!rollStackState) return;
    const editable = _rollStackEditableIndices();
    if (!editable.length) {
        rollStackState.focusIndex = -1;
        return;
    }
    if (!editable.includes(rollStackState.focusIndex)) {
        rollStackState.focusIndex = editable[0];
    }
}

function _rollStackTotal() {
    if (!rollStackState) return 0;
    return rollStackState.fields.reduce((acc, row) => acc + _toInt(row?.value, 0), 0);
}

function _rollStackModifierDelta() {
    if (!rollStackState) return 0;
    return rollStackState.fields
        .filter((row) => !row?.isDie)
        .reduce((acc, row) => acc + (_toInt(row?.value, 0) - _toInt(row?.baseValue, 0)), 0);
}

function _renderRollStack() {
    if (!rollStackState) return;
    _rollStackEnsureFocus();
    actionChoices.innerHTML = "";
    const wrapper = document.createElement("div");
    wrapper.className = "roll-stack";
    rollStackState.fields.forEach((field, idx) => {
        const card = document.createElement("div");
        card.className = "roll-field";
        if (idx === rollStackState.focusIndex) card.classList.add("focused");
        if (!field.editable) card.classList.add("readonly");

        const label = document.createElement("div");
        label.className = "roll-field-label";
        label.textContent = field.label || field.id || "Pole";

        const value = document.createElement("div");
        value.className = "roll-field-value";
        const numeric = _toInt(field.value, 0);
        if (field.isDie) value.textContent = `${numeric}`;
        else value.textContent = `${numeric >= 0 ? "+" : ""}${numeric}`;

        const desc = document.createElement("div");
        desc.className = "roll-field-desc";
        desc.textContent = field.description || "";

        card.appendChild(label);
        card.appendChild(value);
        card.appendChild(desc);
        card.addEventListener("click", () => {
            if (!rollStackState || !field.editable) return;
            rollStackState.focusIndex = idx;
            _renderRollStack();
        });
        wrapper.appendChild(card);
    });

    const total = document.createElement("div");
    total.className = "roll-total";
    const totalLabel = rollStackState.mode === "damage" ? "Suma obrażeń" : "Suma rzutu";
    total.innerHTML = `<span>${totalLabel}</span><strong>${_rollStackTotal()}</strong>`;
    wrapper.appendChild(total);
    actionChoices.appendChild(wrapper);
    actionDesc.classList.remove("hidden");
    const baseHint = "4: poprzednie pole, 5/6: następne pole, 8: +1, 2: -1, Enter: zatwierdź.";
    actionDesc.textContent = rollStackState.mode === "damage" ? baseHint : `${baseHint} *: nat20/nat1.`;
}

function _initRollStack(prompt) {
    const mode = String(prompt?.layout || "test").toLowerCase() === "damage" ? "damage" : "test";
    const seed = _buildRollStackSeed(prompt);
    const fields = [
        {
            id: mode === "damage" ? "damage_roll" : "d20",
            label: mode === "damage" ? "Rzut kości obrażeń" : "Rzut k20",
            value: _toInt(seed.defaultRoll, 0),
            baseValue: _toInt(seed.defaultRoll, 0),
            description: mode === "damage" ? "Wpisz surowy wynik kości obrażeń." : "Wpisz surowy wynik kości d20.",
            editable: true,
            isDie: true,
        },
        ...seed.components,
    ];
    rollStackState = {
        fields,
        mode,
        focusIndex: 0,
    };
    _renderRollStack();
}

function _moveRollStackFocus(step) {
    if (!rollStackState) return;
    const editable = _rollStackEditableIndices();
    if (!editable.length) return;
    const currentPos = Math.max(0, editable.indexOf(rollStackState.focusIndex));
    const nextPos = (currentPos + step + editable.length) % editable.length;
    rollStackState.focusIndex = editable[nextPos];
    _renderRollStack();
}

function _adjustRollStackFocused(delta) {
    if (!rollStackState) return;
    const idx = rollStackState.focusIndex;
    if (idx < 0 || idx >= rollStackState.fields.length) return;
    const row = rollStackState.fields[idx];
    if (!row?.editable) return;
    row.value = _toInt(row.value, 0) + delta;
    _renderRollStack();
}

function _rollStackAnswerPayload() {
    if (!rollStackState) return null;
    const dieRow = rollStackState.fields.find((row) => row?.isDie) || rollStackState.fields[0];
    const rawRoll = _toInt(dieRow?.value, 0);
    return {
        roll: rawRoll,
        raw_roll: rawRoll,
        modifier_delta: _rollStackModifierDelta(),
        computed_total: _rollStackTotal(),
        natural_mode: rollNaturalMode,
        roll_stack_values: rollStackState.fields.map((row) => ({
            id: row.id,
            value: _toInt(row.value, 0),
            base_value: _toInt(row.baseValue, 0),
        })),
    };
}

function showMenu() {
    screenMenu.classList.remove("hidden");
    screenGame.classList.add("hidden");
}

function showGame() {
    screenMenu.classList.add("hidden");
    screenGame.classList.remove("hidden");
}

function resetLocalSessionState({ sessionId = null, reason = "", showMenuScreen = true } = {}) {
    currentSessionId = sessionId || currentSessionId;
    currentScenario = null;
    heroes.clear();
    promptQueue = [];
    renderedPrompts.clear();
    activePrompt = null;
    currentChoices = [];
    selectedChoiceIndex = -1;
    choiceMeta = [];
    confirmMode = false;
    storedSelection = "";
    layoutMode = "info";
    rollNaturalMode = "none";
    fileImagePayload = null;
    rollStackState = null;
    initiativeState = { order: [], activeId: null, round: 1 };
    activeActorId = null;
    lastLoggedRound = null;
    lastLoggedActiveActorId = null;
    creationPreviewHeroId = null;
    selectedHeroId = null;
    menuNumpadContext = null;
    pathState = clearPathPreview(refs, pathState, null);

    actionForm.classList.add("hidden");
    actionChoices.innerHTML = "";
    actionDesc.textContent = "";
    actionDesc.classList.remove("hidden");
    actionPrompt.textContent = "";
    actionPrompt.classList.add("hidden");
    actionTitle.textContent = "Czekam na działania...";
    actionText.textContent = "";
    actionText.classList.remove("hidden");
    actionAnswer.value = "";
    actionAnswer.placeholder = "Wpisz odpowiedź lub wybierz kartę...";
    actionAnswer.classList.remove("input-hidden");
    clearMods();
    _renderNaturalControls(null);
    _resetMenuNumpadContext();
    setIllustration(PLACEHOLDER_IMAGE);

    if (eventFeed) {
        eventFeed.innerHTML = '<li class="event-feed-empty">Brak zdarzeń.</li>';
    }
    if (logList) {
        logList.innerHTML = "";
    }
    if (logLast) {
        logLast.textContent = reason ? `Nowa sesja UI: ${reason}.` : "Logi będą tu widoczne.";
    }
    renderHeroes();
    renderInitiative();
    updateSessionSummary();
    if (showMenuScreen) {
        showMenu();
    }
}

async function fetchSessionInfo() {
    try {
        const resp = await fetch("/api/session");
        if (!resp.ok) return null;
        const data = await resp.json();
        const nextSessionId = String(data?.session?.id || "");
        if (!nextSessionId) return null;
        if (currentSessionId && currentSessionId !== nextSessionId) {
            resetLocalSessionState({ sessionId: nextSessionId, reason: "odświeżenie sesji", showMenuScreen: true });
        } else {
            currentSessionId = nextSessionId;
        }
        return nextSessionId;
    } catch (err) {
        console.warn("Nie udało się pobrać sesji UI:", err);
        return null;
    }
}

async function resetUiSession(reason = "manual") {
    try {
        const resp = await fetch("/api/session/reset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ reason }),
        });
        const data = await resp.json();
        if (!resp.ok || !data?.ok) {
            throw new Error(data?.error || "Nie udało się zresetować sesji UI.");
        }
        resetLocalSessionState({
            sessionId: String(data?.session?.id || ""),
            reason: reason === "manual" ? "ręczny reset" : reason,
            showMenuScreen: true,
        });
    } catch (err) {
        console.warn("Reset sesji UI nie powiódł się:", err);
        resetLocalSessionState({ sessionId: currentSessionId, reason: "lokalny reset", showMenuScreen: true });
    }
}

function str(value, fallback = "-") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
}

function actorNameById(id) {
    if (!id) return "-";
    const fromInit = initiativeState.order.find((entry) => String(entry.id) === String(id));
    if (fromInit && fromInit.name) return fromInit.name;
    const fromHero = heroes.get(id);
    if (fromHero && fromHero.name) return fromHero.name;
    return String(id);
}

function activeHeroImage() {
    if (!activeActorId) return null;
    const hero = heroes.get(activeActorId);
    if (!hero) return null;
    return hero.image || null;
}

function creationPreviewImage() {
    const allHeroes = Array.from(heroes.values());
    const previewHero =
        (creationPreviewHeroId && heroes.get(creationPreviewHeroId)) ||
        allHeroes.find((item) => Boolean(item?.creationInProgress)) ||
        null;
    return previewHero?.image || null;
}

function refreshLeftIllustration() {
    const creationImage =
        String(activePrompt?.source || "").toLowerCase() === "character_creation" ? creationPreviewImage() : null;
    if (activePrompt) {
        setIllustration(activePrompt.image || creationImage || activeHeroImage() || PLACEHOLDER_IMAGE);
        return;
    }
    setIllustration(creationImage || activeHeroImage() || PLACEHOLDER_IMAGE);
}

function currentPromptLabel() {
    if (!activePrompt) return "Brak";
    const kind = str(activePrompt.kind || activePrompt.layout || layoutMode || "prompt");
    const choicesCount = Array.isArray(activePrompt.choices) ? activePrompt.choices.length : currentChoices.length;
    return choicesCount ? `${kind} (${choicesCount})` : kind;
}

function initiativePointers() {
    const order = Array.isArray(initiativeState.order) ? initiativeState.order : [];
    if (!order.length) {
        return { active: "-", next: "-" };
    }
    const activeIdx = order.findIndex((entry) => String(entry.id) === String(initiativeState.activeId));
    if (activeIdx === -1) {
        return { active: "-", next: order[0]?.name || "-" };
    }
    const active = order[activeIdx]?.name || "-";
    const next = order.length > 1 ? order[(activeIdx + 1) % order.length]?.name || "-" : "-";
    return { active, next };
}

function updateSessionSummary() {
    const pointers = initiativePointers();
    const activeLabel = activeActorId ? actorNameById(activeActorId) : pointers.active;
    if (statusScenario) statusScenario.textContent = str(currentScenario);
    if (statusActor) statusActor.textContent = str(activeLabel);
    if (statusNext) statusNext.textContent = str(pointers.next);
    if (statusRound) statusRound.textContent = str(initiativeState.round);
    if (statusPrompt) statusPrompt.textContent = currentPromptLabel();
}

function appendTag(container, tag) {
    if (!container || !tag) return;
    const tagEl = document.createElement("span");
    tagEl.className = "tag";
    tagEl.textContent = tag;
    container.appendChild(tagEl);
}

function addEventFeedEntry(text, meta, variant = "", tag = "") {
    if (!eventFeed) return;
    const empty = eventFeed.querySelector(".event-feed-empty");
    if (empty) empty.remove();
    const item = document.createElement("li");
    item.className = "event-item" + (variant ? ` ${variant}` : "");

    const main = document.createElement("div");
    main.className = "event-main";
    appendTag(main, tag);
    const textEl = document.createElement("span");
    textEl.textContent = str(text, "");
    main.appendChild(textEl);

    const metaEl = document.createElement("div");
    metaEl.className = "event-meta";
    metaEl.textContent = str(meta, "");

    item.appendChild(main);
    item.appendChild(metaEl);
    eventFeed.prepend(item);

    while (eventFeed.children.length > 8) {
        eventFeed.removeChild(eventFeed.lastChild);
    }
}

function addLogEntry(text, meta, variant = "", tag = "", image = "") {
    const item = document.createElement("li");
    item.className = "log-item" + (variant ? ` ${variant}` : "");

    if (image) {
        const thumbWrap = document.createElement("div");
        thumbWrap.className = "log-thumb-wrap";
        const thumb = document.createElement("img");
        thumb.className = "log-thumb";
        thumb.src = image;
        thumb.alt = "";
        thumbWrap.appendChild(thumb);
        item.appendChild(thumbWrap);
    }

    const body = document.createElement("div");
    body.className = "log-body";
    const logText = document.createElement("div");
    logText.className = "log-text";
    appendTag(logText, tag);
    const textEl = document.createElement("span");
    textEl.textContent = str(text, "");
    logText.appendChild(textEl);
    const metaEl = document.createElement("div");
    metaEl.className = "meta";
    metaEl.textContent = str(meta, "");
    body.appendChild(logText);
    body.appendChild(metaEl);
    item.appendChild(body);

    logList.prepend(item);
    if (logLast) {
        logLast.innerHTML = "";
        appendTag(logLast, tag);
        const lastText = document.createElement("span");
        lastText.textContent = str(text, "");
        logLast.appendChild(lastText);
    }
    addEventFeedEntry(text, meta, variant, tag);
    // limit log length
    while (logList.children.length > 60) {
        logList.removeChild(logList.lastChild);
    }
}

function renderPrompt(prompt) {
    ensureCreationPreviewFallbackFromPrompt(prompt);
    if (renderedPrompts.has(prompt.id)) return;
    renderedPrompts.add(prompt.id);
    promptQueue.push(prompt);
    processPromptQueue();
}

function samePos(a, b) {
    if (!Array.isArray(a) || !Array.isArray(b)) return false;
    if (a.length < 2 || b.length < 2) return false;
    return Number(a[0]) === Number(b[0]) && Number(a[1]) === Number(b[1]);
}

function formatPos(pos) {
    if (!Array.isArray(pos) || pos.length < 2) return "-";
    return `(${pos[0]}, ${pos[1]})`;
}

function arrayDiff(previous, next) {
    const prevSet = new Set((previous || []).map((item) => String(item)));
    const nextSet = new Set((next || []).map((item) => String(item)));
    const added = [...nextSet].filter((item) => !prevSet.has(item));
    const removed = [...prevSet].filter((item) => !nextSet.has(item));
    return { added, removed };
}

function spellSlotLabel(tier) {
    const raw = String(tier || "").toLowerCase().trim();
    if (!raw) return "";
    if (raw === "cantrip") return "Cantripy";
    if (raw.startsWith("rank_")) return `R${raw.slice(5)}`;
    return raw.replace(/_/g, " ");
}

function spellcastingCounterSummary(spellcasting) {
    if (!spellcasting || typeof spellcasting !== "object") return [];
    const rows = [];
    const focusPoints = Number(spellcasting.focusPoints ?? spellcasting.focus_points);
    const focusPoolMax = Number(spellcasting.focusPoolMax ?? spellcasting.focus_pool_max);
    if (!Number.isNaN(focusPoolMax) && focusPoolMax > 0) {
        rows.push(`Focus ${Number.isNaN(focusPoints) ? 0 : focusPoints}/${focusPoolMax}`);
    }
    const slotTotal = spellcasting.slotTotal ?? spellcasting.slot_total;
    const slotRemaining = spellcasting.slotRemaining ?? spellcasting.slot_remaining;
    const totalDict = slotTotal && typeof slotTotal === "object" ? slotTotal : {};
    const remainingDict = slotRemaining && typeof slotRemaining === "object" ? slotRemaining : {};
    Object.keys(totalDict)
        .sort()
        .forEach((tier) => {
            const total = Number(totalDict[tier]);
            if (Number.isNaN(total) || total <= 0 || tier === "cantrip") return;
            const remaining = Number(remainingDict[tier]);
            rows.push(`${spellSlotLabel(tier)} ${Number.isNaN(remaining) ? total : remaining}/${total}`);
        });
    return rows;
}

function buildHeroUpdateLog(previous, current) {
    if (!previous) {
        return {
            message: `${current.name} dołącza do sceny na ${formatPos(current.pos)}.`,
            variant: "info",
        };
    }
    const changes = [];
    let variant = "info";

    if (previous.wounds !== current.wounds) {
        changes.push(`Rany: ${str(previous.wounds)} -> ${str(current.wounds)}`);
        const before = Number(previous.wounds);
        const after = Number(current.wounds);
        if (!Number.isNaN(before) && !Number.isNaN(after)) {
            if (after > before) variant = "warning";
            else if (after < before && variant !== "warning") variant = "success";
        }
    }
    if (!samePos(previous.pos, current.pos) && (previous.pos || current.pos)) {
        changes.push(`Pozycja: ${formatPos(previous.pos)} -> ${formatPos(current.pos)}`);
    }
    if (previous.initiative !== current.initiative) {
        changes.push(`Inicjatywa: ${str(previous.initiative)} -> ${str(current.initiative)}`);
    }
    const previousAc = resolveArmorClass(previous);
    const currentAc = resolveArmorClass(current);
    if (previousAc !== currentAc && currentAc != null) {
        changes.push(`AC: ${str(previousAc)} -> ${str(currentAc)}`);
        if (variant !== "warning") variant = "success";
    }
    if (previous.baseSpeedFeet !== current.baseSpeedFeet && current.baseSpeedFeet != null) {
        changes.push(`Speed: ${str(previous.baseSpeedFeet)} -> ${str(current.baseSpeedFeet)} ft`);
        if (variant !== "warning") variant = "success";
    }
    const previousSpellRows = spellcastingCounterSummary(previous.spellcasting || {});
    const currentSpellRows = spellcastingCounterSummary(current.spellcasting || {});
    if (previousSpellRows.join(" | ") !== currentSpellRows.join(" | ") && currentSpellRows.length) {
        changes.push(`Magia: ${currentSpellRows.join(" · ")}`);
        if (variant !== "warning") variant = "success";
    }
    const statusesDiff = arrayDiff(previous.statuses, current.statuses);
    if (statusesDiff.added.length) {
        changes.push(`+ status: ${statusesDiff.added.join(", ")}`);
        if (variant !== "warning") variant = "success";
    }
    if (statusesDiff.removed.length) {
        changes.push(`- status: ${statusesDiff.removed.join(", ")}`);
    }
    if (!changes.length && previous.note !== current.note && current.note) {
        changes.push(`Notatka: ${current.note}`);
    }
    if (!changes.length) return null;
    return { message: `${current.name}: ${changes.join(" · ")}`, variant };
}

function ensureCreationPreviewFallbackFromPrompt(promptPayload = {}) {
    const source = String(promptPayload?.source || "").toLowerCase();
    if (source !== "character_creation") return;
    const hasRealCreationHero = Array.from(heroes.values()).some(
        (hero) => Boolean(hero?.creationInProgress) && String(hero?.id || "") !== CREATION_PREVIEW_FALLBACK_ID
    );
    if (hasRealCreationHero) return;

    const previous = heroes.get(CREATION_PREVIEW_FALLBACK_ID) || {};
    const defaults = _cloneCreationAbilityDefaults();
    const previousScores = previous.abilityScores && typeof previous.abilityScores === "object" ? previous.abilityScores : null;
    const previousMods = previous.abilityModifiers && typeof previous.abilityModifiers === "object" ? previous.abilityModifiers : null;
    const promptTitle = String(promptPayload?.prompt || promptPayload?.title || "").trim();
    const fallback = {
        id: CREATION_PREVIEW_FALLBACK_ID,
        name: String(previous.name || "Tworzona postać"),
        statuses: Array.isArray(previous.statuses) ? previous.statuses : [],
        note: promptTitle || previous.note || "Kreator postaci",
        wounds: previous.wounds ?? 0,
        pos: previous.pos ?? null,
        initiative: previous.initiative ?? null,
        image: promptPayload?.image || previous.image || PLACEHOLDER_IMAGE,
        characterId: previous.characterId || null,
        classId: previous.classId || null,
        ancestryId: previous.ancestryId || null,
        heritageId: previous.heritageId || null,
        ac: previous.ac ?? null,
        acBase: previous.acBase ?? previous.ac ?? null,
        acModifier: previous.acModifier ?? 0,
        maxHp: previous.maxHp ?? null,
        baseSpeedFeet: previous.baseSpeedFeet ?? null,
        abilityScores: previousScores && Object.keys(previousScores).length ? previousScores : defaults.abilityScores,
        abilityModifiers: previousMods && Object.keys(previousMods).length ? previousMods : defaults.abilityModifiers,
        skillRanks: previous.skillRanks || {},
        saveRanks: previous.saveRanks || {},
        perceptionRank: previous.perceptionRank || null,
        trainedSkills: previous.trainedSkills || [],
        loreSkills: previous.loreSkills || [],
        backgroundLabel: previous.backgroundLabel || null,
        backgroundFeatId: previous.backgroundFeatId || null,
        backgroundAbilityBoostsUi: previous.backgroundAbilityBoostsUi || null,
        backgroundSkillTrainingUi: previous.backgroundSkillTrainingUi || null,
        previewBarbarianInstinctId: previous.previewBarbarianInstinctId || null,
        creationInProgress: true,
        handSlots: previous.handSlots || null,
        coinPouch: previous.coinPouch || null,
        moneyText: previous.moneyText || null,
        bulkSummary: previous.bulkSummary || null,
        inventoryItems: previous.inventoryItems || [],
    };
    heroes.set(CREATION_PREVIEW_FALLBACK_ID, fallback);
    creationPreviewHeroId = CREATION_PREVIEW_FALLBACK_ID;
}

function handleEvent(event) {
    const type = event.type;
    const payload = event.payload || {};
    const eventSessionId = String(event.session_id || "");
    const timestamp = new Date(event.ts * 1000 || Date.now());
    const meta = timestamp.toLocaleTimeString();

    if (eventSessionId && currentSessionId && eventSessionId !== currentSessionId) {
        resetLocalSessionState({
            sessionId: eventSessionId,
            reason: "przełączenie sesji",
            showMenuScreen: false,
        });
    } else if (eventSessionId && !currentSessionId) {
        currentSessionId = eventSessionId;
    }

    if (type === "session_reset") {
        resetLocalSessionState({
            sessionId: eventSessionId || currentSessionId,
            reason: payload.reason || "reset",
            showMenuScreen: true,
        });
        return;
    }

    // gdy docierają zdarzenia, przełącz na ekran gry (jeśli jeszcze nie)
    showGame();

    if (type === "prompt") {
        ensureCreationPreviewFallbackFromPrompt(payload);
        if (String(payload?.source || "").toLowerCase() !== "character_creation") {
            heroes.delete(CREATION_PREVIEW_FALLBACK_ID);
            if (String(creationPreviewHeroId || "") === CREATION_PREVIEW_FALLBACK_ID) {
                creationPreviewHeroId = null;
            }
        }
        renderPrompt(payload);
        const promptTag = payload.kind === "choice" ? "Wybór" : payload.kind === "info" ? "Info" : "Rzut";
        const sourceNote = payload.source ? ` [${payload.source}]` : "";
        const choicesCount = Array.isArray(payload.choices) ? payload.choices.length : 0;
        const choicesNote = choicesCount ? ` (${choicesCount} opcji)` : "";
        addLogEntry(`Nowy prompt${sourceNote}: ${payload.prompt}${choicesNote}`, meta, "info", promptTag);
        updateSessionSummary();
        return;
    }
    if (type === "special_preview") {
        const title = payload.name || payload.slug || "Zdolność specjalna";
        actionTitle.textContent = title;
        actionText.textContent = payload.desc || "";
        setIllustration(payload.image);
        addLogEntry(`Zdolność: ${title}`, meta, "info", "Special");
        updateSessionSummary();
        return;
    }
    if (type === "info") {
        const infoText = payload.text || payload.message || "Info";
        const scenarioMatch = String(infoText).match(/Start scenariusza:\s*(.+)\s*$/i);
        if (scenarioMatch && scenarioMatch[1]) {
            currentScenario = String(scenarioMatch[1]).trim();
        }
        renderPrompt({
            id: `info-${Date.now()}`,
            prompt: infoText,
            kind: "info",
            choices: [],
            source: payload.source || "",
            image: payload.image || null,
        });
        addLogEntry(infoText, meta, "info", payload.source || "Info");
        updateSessionSummary();
        return;
    }
    if (type === "idle_hint") {
        if (!activePrompt) {
            actionTitle.textContent = payload.title || "Czekam na działania...";
            actionText.textContent = payload.text || "";
        }
        return;
    }
    if (type === "prompt_answered") {
        addLogEntry(`Odpowiedź (${payload.prompt || ""}): ${payload.answer}`, meta, "success", "Prompt");
        if (activePrompt && String(activePrompt.id) === String(payload.id)) {
            closePrompt();
        }
        updateSessionSummary();
        return;
    }
    if (type === "hero_snapshot" || type === "hero") {
        const id = payload.id || payload.object_id || payload.name || "hero";
        const previous = heroes.get(id);
        const current = {
            id,
            name: payload.name || id,
            statuses: payload.statuses || [],
            note: payload.note,
            wounds: payload.wounds,
            pos: payload.pos,
            initiative: payload.initiative,
            image: payload.image,
            characterId: payload.character_id || null,
            classId: payload.class_id || null,
            ancestryId: payload.ancestry_id || null,
            heritageId: payload.heritage_id || null,
            ac: payload.ac,
            acBase: payload.ac_base ?? payload.ac,
            acModifier: payload.ac_modifier ?? 0,
            maxHp: payload.max_hp,
            baseSpeedFeet: payload.speed_feet ?? payload.base_speed_feet,
            abilityScores: payload.ability_scores || {},
            abilityModifiers: payload.ability_modifiers || {},
            skillRanks: payload.skill_ranks || {},
            saveRanks: payload.save_ranks || {},
            perceptionRank: payload.perception_rank || null,
            trainedSkills: payload.trained_skills || [],
            loreSkills: payload.lore_skills || [],
            backgroundLabel: payload.background_label || null,
            backgroundFeatId: payload.background_feat_id || null,
            backgroundAbilityBoostsUi: payload.background_ability_boosts_ui || null,
            backgroundSkillTrainingUi: payload.background_skill_training_ui || null,
            previewBarbarianInstinctId: payload.preview_barbarian_instinct_id || null,
            creationInProgress: Boolean(payload.creation_in_progress),
            handSlots: payload.hand_slots || null,
            coinPouch: payload.coin_pouch || null,
            moneyText: payload.money_text || null,
            bulkSummary: payload.bulk_summary || null,
            inventoryItems: payload.inventory_items || [],
            spellcasting: payload.spellcasting || null,
        };
        if (current.creationInProgress) {
            creationPreviewHeroId = id;
            if (String(id) !== CREATION_PREVIEW_FALLBACK_ID) {
                heroes.delete(CREATION_PREVIEW_FALLBACK_ID);
            }
        } else if (String(creationPreviewHeroId || "") === String(id)) {
            creationPreviewHeroId = null;
        }
        heroes.set(id, current);
        renderHeroes();
        if (!activePrompt && String(id) === String(activeActorId || "")) {
            refreshLeftIllustration();
        }
        const heroLog = buildHeroUpdateLog(previous, current);
        if (heroLog) {
            addLogEntry(heroLog.message, meta, heroLog.variant, "Bohater");
        }
        updateSessionSummary();
        return;
    }
    if (type === "active_actor_changed") {
        const prev = activeActorId;
        activeActorId = payload.id || null;
        renderHeroes();
        if (!activePrompt) {
            refreshLeftIllustration();
        }
        if (String(prev) !== String(activeActorId)) {
            if (activeActorId) {
                const actorLabel = payload.name || actorNameById(activeActorId);
                addLogEntry(`Aktywna tura: ${actorLabel}`, meta, "info", "Tura");
            } else {
                addLogEntry("Brak aktywnego aktora.", meta, "info", "Tura");
            }
            lastLoggedActiveActorId = activeActorId;
        }
        updateSessionSummary();
        return;
    }
    if (type === "narration") {
        addLogEntry(payload.message || "Narrator", meta, "info", "Narrator");
        return;
    }
    if (type === "action") {
        if (!activePrompt) {
            const actor = payload.actor?.name || payload.actor?.id || "Aktor";
            const actionId = str(payload.action_id || "akcja", "akcja").replace(/_/g, " ");
            const target = payload.target?.name || payload.target?.id;
            actionTitle.textContent = actor;
            actionText.textContent = target ? `${actionId} -> ${target}` : actionId;
        }
        return;
    }
    if (type === "path_preview") {
        pathState = showPathPreview(refs, payload, pathState);
        addEventFeedEntry(
            `${payload.actor_name || "Ruch"} -> ${payload.target ? formatPos(payload.target) : "cel"}`,
            meta,
            payload.trimmed ? "warning" : "info",
            "Ruch",
        );
        return;
    }
    if (type === "path_clear") {
        pathState = clearPathPreview(refs, pathState, payload && payload.id);
        return;
    }
    if (type === "initiative") {
        initiativeState = {
            order: payload.order || [],
            activeId: payload.active_id || payload.activeId || null,
            round: payload.round ?? null,
        };
        activeActorId = initiativeState.activeId || null;
        if (initiativeState.round && initiativeState.round !== lastLoggedRound) {
            addLogEntry(`Runda ${initiativeState.round} start`, meta, "info", "Runda");
            lastLoggedRound = initiativeState.round;
        }
        if (initiativeState.activeId && String(lastLoggedActiveActorId) !== String(initiativeState.activeId)) {
            addLogEntry(`Aktywna tura: ${actorNameById(initiativeState.activeId)}`, meta, "info", "Tura");
            lastLoggedActiveActorId = initiativeState.activeId;
        }
        if (!initiativeState.activeId) {
            lastLoggedActiveActorId = null;
        }
        renderInitiative();
        updateSessionSummary();
        return;
    }
    // domyślnie traktujemy jako log
    const level = (payload.level || "").toLowerCase();
    let variant = "";
    if (level === "error") variant = "error";
    else if (level === "warn" || level === "warning") variant = "warning";
    addLogEntry(payload.message || type, meta, variant, payload.tag || "", payload.image || "");
}

function connectStream() {
    if (eventSource) {
        eventSource.close();
    }
    eventSource = new EventSource("/stream");
    eventSource.onmessage = (evt) => {
        try {
            const data = JSON.parse(evt.data);
            handleEvent(data);
        } catch (err) {
            console.error("Błąd parsowania zdarzenia", err);
        }
    };
    eventSource.onerror = (err) => {
        console.warn("Stream error, ponawiam za chwilę", err);
        setTimeout(connectStream, 1200);
    };
}

async function fetchPendingPrompts() {
    try {
        const resp = await fetch("/api/prompts");
        if (!resp.ok) return;
        const data = await resp.json();
        const listedSessionId = String(data?.session?.id || "");
        if (listedSessionId && currentSessionId && listedSessionId !== currentSessionId) {
            resetLocalSessionState({
                sessionId: listedSessionId,
                reason: "synchronizacja promptów",
                showMenuScreen: false,
            });
        } else if (listedSessionId && !currentSessionId) {
            currentSessionId = listedSessionId;
        }
        if (!data.prompts) return;
        const pending = data.prompts.filter((p) => p.status === "pending");
        if (pending.length) {
            showGame();
            pending.forEach((p) => renderPrompt(p));
        }
    } catch (err) {
        console.warn("Nie udało się pobrać promptów:", err);
    }
}

// --- UI actions ---

document.getElementById("btn-new-game").addEventListener("click", () => {
    resetUiSession("manual");
});
document.getElementById("btn-quit").addEventListener("click", () => {
    window.close();
});

document.querySelectorAll(".scenario-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        currentScenario = btn.dataset.scenario;
        addLogEntry(`Uruchomiono scenariusz: ${currentScenario}`, new Date().toLocaleTimeString());
        showGame();
        updateSessionSummary();
    });
});
const scenarioButtons = Array.from(document.querySelectorAll(".scenario-btn"));
let scenarioIndex = 0;
function highlightScenario(idx) {
    scenarioButtons.forEach((b, i) => {
        if (i === idx) b.classList.add("selected");
        else b.classList.remove("selected");
    });
}
if (scenarioButtons.length) {
    highlightScenario(scenarioIndex);
}

if (logFab && logModal) {
    logFab.addEventListener("click", () => {
        logModal.classList.toggle("hidden");
    });
}
if (logClose && logModal) {
    logClose.addEventListener("click", () => {
        logModal.classList.add("hidden");
    });
}
if (logModal) {
    logModal.addEventListener("click", (evt) => {
        if (evt.target === logModal) {
            logModal.classList.add("hidden");
        }
    });
}

if (topbarToggle && topbar) {
    topbarToggle.addEventListener("click", () => {
        topbar.classList.toggle("collapsed");
        topbarToggle.textContent = topbar.classList.contains("collapsed") ? "▼" : "▲";
    });
}

async function initUi() {
    showMenu();
    updateSessionSummary();
    await fetchSessionInfo();
    connectStream();
    await fetchPendingPrompts();
    setInterval(fetchPendingPrompts, 2000);
}

initUi();

// --- Prompt panel logic ---

actionForm.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    if (!activePrompt) return;
    if (activePrompt.kind === "info") {
        const infoId = String(activePrompt.id || "");
        if (infoId.startsWith("info-")) {
            closePrompt();
            return;
        }
        await sendPromptAnswer("ok");
        return;
    }
    if (layoutMode === "file_image") {
        if (!fileImagePayload) {
            actionDesc.classList.remove("hidden");
            actionDesc.textContent = "Najpierw wybierz plik obrazu portretu.";
            return;
        }
        await sendPromptAnswer(fileImagePayload);
        return;
    }
    if (rollStackState) {
        const payload = _rollStackAnswerPayload();
        if (!payload) return;
        await sendPromptAnswer(payload);
        return;
    }

    // specjalny flow dla wyboru akcji z potwierdzeniem
    if (layoutMode === "action_select" && !confirmMode) {
        storedSelection = actionAnswer.value.trim();
        if (!storedSelection) return;
        // przejście do potwierdzenia
        confirmMode = true;
        actionTitle.textContent = storedSelection;
        actionText.textContent = activePrompt.action_desc || activePrompt.desc || "Potwierdź tę akcję.";
        actionAnswer.classList.add("input-hidden");
        actionChoices.innerHTML = "";
        const confirmChoices = normalizeChoices({
            choices: ["Accept", "Decline"],
            choice_meta: [
                { raw: "Accept", label: "Potwierdź", desc: "Zatwierdź i wykonaj akcję.", key: "+" },
                { raw: "Decline", label: "Wróć", desc: "Wróć do wyboru akcji.", key: "-" },
            ],
        });
        currentChoices = confirmChoices.map((c) => c.raw);
        choiceMeta = confirmChoices;
        selectedChoiceIndex = 0;
        confirmChoices.forEach((c, idx) => {
            const pill = document.createElement("div");
            pill.className = "choice-pill";
            const displayKey = /^[0-9]+$/.test(String(c.key || "")) ? "" : (c.key || "");
            pill.innerHTML =
                '<div class="label"><span class="key">' +
                displayKey +
                "</span>" +
                (c.label || "") +
                "</div>";
            pill.addEventListener("click", () => selectChoice(idx));
            actionChoices.appendChild(pill);
        });
        updateChoiceHighlight();
        updateChoiceDesc();
        return;
    }

    if (layoutMode === "action_select" && confirmMode) {
        const choice = currentChoices[selectedChoiceIndex] || "Decline";
        if (choice.toLowerCase().startsWith("decline")) {
            // reset do wyboru akcji, czysty filtr
            confirmMode = false;
            storedSelection = "";
            actionChoices.innerHTML = "";
            actionDesc.textContent = "";
            actionAnswer.value = "";
            actionAnswer.classList.remove("input-hidden");
            actionAnswer.placeholder = "Nazwa akcji...";
            currentChoices = [];
            choiceMeta = [];
            selectedChoiceIndex = -1;
            return;
        }
        // Accept - zwracamy wpisaną akcję
        await sendPromptAnswer(storedSelection);
        return;
    }

    let answer = actionAnswer.value.trim();
    if (!answer && currentChoices.length > 0 && selectedChoiceIndex >= 0) {
        answer = currentChoices[selectedChoiceIndex];
    }
    if (!answer) return;
    await sendPromptAnswer(answer);
});

async function sendPromptAnswer(answer) {
    try {
        let finalAnswer = answer;
        if (_isNaturalRollPrompt(activePrompt)) {
            if (answer && typeof answer === "object" && !Array.isArray(answer)) {
                finalAnswer = { ...answer };
            } else {
                const parsed = Number.parseInt(String(answer).trim(), 10);
                if (!Number.isNaN(parsed)) {
                    finalAnswer = {
                        roll: parsed,
                        raw_roll: parsed,
                    };
                }
            }
            if (finalAnswer && typeof finalAnswer === "object" && !Array.isArray(finalAnswer)) {
                if (!finalAnswer.natural_mode) {
                    finalAnswer.natural_mode = rollNaturalMode;
                }
            }
        }
        await fetch(`/api/prompts/${activePrompt.id}/response`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer: finalAnswer }),
        });
        actionAnswer.value = "";
        closePrompt();
    } catch (err) {
        console.error(err);
    }
}

function requestDebugUndo() {
    if (!activePrompt) {
        addLogEntry("Debug cofnij: brak aktywnego promptu.", new Date().toLocaleTimeString(), "warning", "Debug");
        return;
    }
    sendPromptAnswer(DEBUG_UNDO_COMMAND);
}

if (debugUndoBtn) {
    debugUndoBtn.addEventListener("click", () => {
        requestDebugUndo();
    });
}

document.addEventListener("keydown", (evt) => {
    if (evt.key === "Escape" && logModal && !logModal.classList.contains("hidden")) {
        logModal.classList.add("hidden");
        return;
    }
    // scenario wybór w menu
    if (!screenMenu.classList.contains("hidden") && screenGame.classList.contains("hidden")) {
        if (_isDownNavigationKey(evt)) {
            evt.preventDefault();
            if (scenarioButtons.length) {
                scenarioIndex = (scenarioIndex + 1) % scenarioButtons.length;
                highlightScenario(scenarioIndex);
            }
        }
        if (_isUpNavigationKey(evt)) {
            evt.preventDefault();
            if (scenarioButtons.length) {
                scenarioIndex = (scenarioIndex - 1 + scenarioButtons.length) % scenarioButtons.length;
                highlightScenario(scenarioIndex);
            }
        }
        if (evt.key === "Enter" && scenarioButtons.length) {
            evt.preventDefault();
            scenarioButtons[scenarioIndex].click();
        }
    }

    if (!activePrompt) return;
    if ((evt.ctrlKey || evt.metaKey) && String(evt.key || "").toLowerCase() === "z") {
        evt.preventDefault();
        requestDebugUndo();
        return;
    }
    if (layoutMode === "file_image" && evt.key === "Enter") {
        evt.preventDefault();
        actionForm.dispatchEvent(new Event("submit", { cancelable: true }));
        return;
    }
    if (_isNaturalRollPrompt(activePrompt) && evt.key === "*") {
        evt.preventDefault();
        _cycleNaturalMode();
        _renderNaturalControls(activePrompt);
        return;
    }
    if (rollStackState) {
        if (evt.key === "4" || evt.key === "ArrowLeft") {
            evt.preventDefault();
            _moveRollStackFocus(-1);
            return;
        }
        if (evt.key === "5" || evt.key === "6" || evt.key === "ArrowRight") {
            evt.preventDefault();
            _moveRollStackFocus(1);
            return;
        }
        if (evt.key === "8" || evt.key === "ArrowUp") {
            evt.preventDefault();
            _adjustRollStackFocused(1);
            return;
        }
        if (evt.key === "2" || evt.key === "ArrowDown") {
            evt.preventDefault();
            _adjustRollStackFocused(-1);
            return;
        }
        if (evt.key === "Enter") {
            evt.preventDefault();
            actionForm.dispatchEvent(new Event("submit", { cancelable: true }));
            return;
        }
    }
    if (layoutMode === "equip_nav") {
        const key = evt.key;
        const map = {
            ArrowUp: "up",
            ArrowDown: "down",
            ArrowRight: "section_next",
            ArrowLeft: "section_prev",
            "8": "up",
            "2": "down",
            "6": "section_next",
            "4": "section_prev",
            "7": "hand_left",
            "9": "hand_right",
            "5": "toggle",
            Enter: "toggle",
            "0": "exit",
            Escape: "exit",
        };
        const cmd = map[key];
        if (cmd) {
            evt.preventDefault();
            sendPromptAnswer(cmd);
            return;
        }
    }
    if (layoutMode === "menu_numpad" && currentChoices.length > 0) {
        const groupedMenu = _isGroupedMenuNumpad();
        const selectedRaw =
            selectedChoiceIndex >= 0 && selectedChoiceIndex < currentChoices.length
                ? String(currentChoices[selectedChoiceIndex] || "")
                : "";
        const isEquipPrompt = String(activePrompt?.source || "").toLowerCase() === "equip";
        if (groupedMenu && (evt.key === "4" || evt.key === "ArrowLeft")) {
            evt.preventDefault();
            _setGroupedMenuActive("filters");
            return;
        }
        if (groupedMenu && (evt.key === "6" || evt.key === "ArrowRight")) {
            evt.preventDefault();
            _setGroupedMenuActive("list");
            return;
        }
        if (_isUpNavigationKey(evt)) {
            evt.preventDefault();
            if (!_moveGroupedMenuSelection(-1)) {
                const prev = (selectedChoiceIndex - 1 + currentChoices.length) % currentChoices.length;
                selectChoice(prev);
            }
            return;
        }
        if (_isDownNavigationKey(evt)) {
            evt.preventDefault();
            if (!_moveGroupedMenuSelection(1)) {
                const next = (selectedChoiceIndex + 1) % currentChoices.length;
                selectChoice(next);
            }
            return;
        }
        if (evt.key === "*") {
            if (isEquipPrompt && selectedRaw) {
                evt.preventDefault();
                sendPromptAnswer({ cmd: "transfer", selected: selectedRaw });
                return;
            }
            const idx = choiceMeta.findIndex((c) => String(c.key || "") === "*");
            if (idx >= 0) {
                evt.preventDefault();
                selectChoice(idx);
                actionForm.dispatchEvent(new Event("submit", { cancelable: true }));
                return;
            }
        }
        if (isEquipPrompt && (evt.key === "4" || evt.key === "ArrowLeft") && selectedRaw) {
            evt.preventDefault();
            sendPromptAnswer({ cmd: "section_prev", selected: selectedRaw });
            return;
        }
        if (isEquipPrompt && (evt.key === "6" || evt.key === "ArrowRight") && selectedRaw) {
            evt.preventDefault();
            sendPromptAnswer({ cmd: "section_next", selected: selectedRaw });
            return;
        }
        if (isEquipPrompt && evt.key === "7" && selectedRaw) {
            evt.preventDefault();
            sendPromptAnswer({ cmd: "hand_left", selected: selectedRaw });
            return;
        }
        if (isEquipPrompt && evt.key === "9" && selectedRaw) {
            evt.preventDefault();
            sendPromptAnswer({ cmd: "hand_right", selected: selectedRaw });
            return;
        }
        if (isEquipPrompt && evt.key === "/" && selectedRaw) {
            evt.preventDefault();
            sendPromptAnswer({ cmd: "drop", selected: selectedRaw });
            return;
        }
        if (evt.key === "Enter") {
            evt.preventDefault();
            actionForm.dispatchEvent(new Event("submit", { cancelable: true }));
            return;
        }
    }
    if (layoutMode === "action_select" && confirmMode && evt.key === "Escape") {
        evt.preventDefault();
        // manual decline -> reset filtra
        confirmMode = false;
        storedSelection = "";
        actionChoices.innerHTML = "";
        actionDesc.textContent = "";
        actionAnswer.value = "";
        actionAnswer.classList.remove("input-hidden");
        actionAnswer.placeholder = "Nazwa akcji...";
        currentChoices = [];
        choiceMeta = [];
        selectedChoiceIndex = -1;
        return;
    }
    if (activePrompt.kind === "info") {
        if (evt.key === "Enter") {
            evt.preventDefault();
            const infoId = String(activePrompt.id || "");
            if (infoId.startsWith("info-")) {
                closePrompt();
            } else {
                actionForm.dispatchEvent(new Event("submit", { cancelable: true }));
            }
        }
        return;
    }
    if (currentChoices.length > 0) {
        if (_isDownNavigationKey(evt)) {
            evt.preventDefault();
            const next = (selectedChoiceIndex + 1) % currentChoices.length;
            selectChoice(next);
        }
        if (_isUpNavigationKey(evt)) {
            evt.preventDefault();
            const prev = (selectedChoiceIndex - 1 + currentChoices.length) % currentChoices.length;
            selectChoice(prev);
        }
        if (evt.key === "Enter") {
            evt.preventDefault();
            actionForm.dispatchEvent(new Event("submit", { cancelable: true }));
        }
    }
});

function openPrompt(prompt) {
    activePrompt = prompt;
    renderedPrompts.add(prompt.id);
    layoutMode = prompt.layout || prompt.kind || "info";
    confirmMode = false;
    storedSelection = "";
    rollNaturalMode = "none";
    rollStackState = null;
    actionTitle.textContent = prompt.title || prompt.prompt || "Akcja";
    actionText.textContent = prompt.subtitle || "";
    const promptBody = prompt.prompt_long || (layoutMode === "dialog" ? prompt.prompt : "");
    actionPrompt.textContent = promptBody || "";
    actionPrompt.classList.toggle("hidden", !promptBody);
    const creationImage =
        String(prompt?.source || "").toLowerCase() === "character_creation" ? creationPreviewImage() : null;
    setIllustration(prompt.image || creationImage || activeHeroImage() || PLACEHOLDER_IMAGE);
    actionKind.textContent = "";
    actionKind.classList.add("hidden");
    actionSource.textContent = "";
    actionSource.classList.add("hidden");
    actionChoices.innerHTML = "";
    _resetMenuNumpadContext();
    actionDesc.textContent = "";
    clearMods();

    const normalized = normalizeChoices(prompt);
    currentChoices = normalized.map((c) => c.raw);
    choiceMeta = normalized.map((c, i) => ({ ...c, expanded: i === 0 }));
    const preferredIndex = Number.parseInt(String(prompt.preselected_index ?? ""), 10);
    if (normalized.length) {
        if (Number.isInteger(preferredIndex) && preferredIndex >= 0 && preferredIndex < normalized.length) {
            selectedChoiceIndex = preferredIndex;
        } else {
            selectedChoiceIndex = 0;
        }
    } else {
        selectedChoiceIndex = -1;
    }
    choiceMeta = normalized.map((c, i) => ({ ...c, expanded: i === selectedChoiceIndex }));

    const createChoicePill = (c, idx) => {
            const pill = document.createElement("div");
            pill.className = "choice-pill";
            pill.dataset.choiceIndex = String(idx);
            const displayKey = /^[0-9]+$/.test(String(c.key || "")) ? "" : (c.key || "");
            const labelRow = document.createElement("div");
            labelRow.className = "label";
            const keyEl = document.createElement("span");
            keyEl.className = "key";
            keyEl.textContent = displayKey;
            const labelText = document.createElement("span");
            labelText.textContent = c.label || "";
            labelRow.appendChild(keyEl);
            labelRow.appendChild(labelText);
            pill.appendChild(labelRow);
            const desc = document.createElement("div");
            desc.className = "desc";
            desc.appendChild(renderChoiceDescription(c.desc || ""));
            pill.appendChild(desc);
            pill.addEventListener("click", () => {
                selectChoice(idx);
            });
            return pill;
    };

    const ensureChoiceList = (list) => {
        list.forEach((c, idx) => {
            actionChoices.appendChild(createChoicePill(c, idx));
        });
    };

    const renderCharacterCreationShopColumns = (list) => {
        if (layoutMode !== "menu_numpad") return false;
        if (String(prompt?.source || "").toLowerCase() !== "character_creation") return false;
        const filterIndices = [];
        const listIndices = [];
        const indexToGroup = {};

        list.forEach((row, idx) => {
            const raw = String(row.raw || "").trim().toLowerCase();
            if (raw.startsWith("__filter:")) {
                filterIndices.push(idx);
                indexToGroup[idx] = "filters";
            } else {
                listIndices.push(idx);
                indexToGroup[idx] = "list";
            }
        });
        if (!filterIndices.length || !listIndices.length) return false;

        actionChoices.classList.add("choice-columns-mode");
        const columns = document.createElement("div");
        columns.className = "choice-columns";

        const filterCol = document.createElement("div");
        filterCol.className = "choice-column";
        filterCol.dataset.group = "filters";
        const filterHead = document.createElement("div");
        filterHead.className = "choice-column-head";
        filterHead.textContent = "Filtry";
        const filterHint = document.createElement("div");
        filterHint.className = "choice-column-hint";
        filterHint.textContent = "4/6: panel | 8/2: nawigacja";
        const filterList = document.createElement("div");
        filterList.className = "choice-column-list";
        filterIndices.forEach((idx) => {
            filterList.appendChild(createChoicePill(list[idx], idx));
        });
        filterCol.appendChild(filterHead);
        filterCol.appendChild(filterHint);
        filterCol.appendChild(filterList);

        const itemsCol = document.createElement("div");
        itemsCol.className = "choice-column";
        itemsCol.dataset.group = "list";
        const itemsHead = document.createElement("div");
        itemsHead.className = "choice-column-head";
        itemsHead.textContent = "Lista";
        const itemsHint = document.createElement("div");
        itemsHint.className = "choice-column-hint";
        itemsHint.textContent = "Enter: wybór";
        const itemsList = document.createElement("div");
        itemsList.className = "choice-column-list";
        listIndices.forEach((idx) => {
            itemsList.appendChild(createChoicePill(list[idx], idx));
        });
        itemsCol.appendChild(itemsHead);
        itemsCol.appendChild(itemsHint);
        itemsCol.appendChild(itemsList);

        columns.appendChild(filterCol);
        columns.appendChild(itemsCol);
        actionChoices.appendChild(columns);

        const selectedGroup = indexToGroup[selectedChoiceIndex] || "list";
        menuNumpadContext = {
            enabled: true,
            groups: { filters: filterIndices, list: listIndices },
            indexToGroup,
            activeGroup: selectedGroup,
        };
        return true;
    };

    if (layoutMode === "dialog" || layoutMode === "interact") {
        if (normalized.length > 0) {
            ensureChoiceList(normalized);
            actionAnswer.value = selectedChoiceIndex >= 0 ? currentChoices[selectedChoiceIndex] || "" : "";
            actionAnswer.classList.add("input-hidden");
            actionAnswer.required = false;
            updateChoiceHighlight();
            updateChoiceDesc();
            actionText.classList.add("hidden");
            actionPrompt.classList.add("hidden");
            actionDesc.classList.add("hidden");
        } else {
            // dialog bez opcji = zwykły prompt tekstowy (np. imię postaci)
            actionAnswer.value = "";
            actionAnswer.placeholder = prompt.answer_placeholder || "Wpisz tekst...";
            actionAnswer.required = false;
            actionAnswer.classList.remove("input-hidden");
            actionText.classList.remove("hidden");
            actionPrompt.classList.toggle("hidden", !promptBody);
            actionDesc.classList.add("hidden");
        }
    } else if (layoutMode === "file_image") {
        actionTitle.textContent = prompt.title || "Wybór portretu";
        actionText.textContent = prompt.subtitle || "Wybierz plik obrazu portretu i potwierdź Enterem.";
        actionAnswer.value = "";
        actionAnswer.required = false;
        actionAnswer.classList.add("input-hidden");
        actionPrompt.classList.toggle("hidden", !promptBody);
        actionText.classList.remove("hidden");
        _renderFileImagePicker();
    } else if (layoutMode === "action_select") {
        // pierwszy krok: wpisz nazwę akcji
        actionTitle.textContent = prompt.title || "Wybierz akcję";
        actionText.textContent = prompt.subtitle || "Wpisz nazwę akcji i potwierdź Enterem.";
        actionAnswer.placeholder = "Nazwa akcji...";
        actionAnswer.value = "";
        actionAnswer.required = true;
        actionAnswer.classList.remove("input-hidden");
    } else if (layoutMode === "test" || layoutMode === "damage") {
        const useRollStack = _isRollStackPrompt(prompt);
        if (useRollStack) {
            actionAnswer.value = "";
            actionAnswer.required = false;
            actionAnswer.classList.add("input-hidden");
            _initRollStack(prompt);
        } else {
            actionAnswer.placeholder = prompt.answer_placeholder || "Podaj wynik (liczba)...";
            actionAnswer.value = "";
            actionAnswer.required = true;
            actionAnswer.classList.remove("input-hidden");
        }
        if (prompt.modifiers) {
            renderMods(prompt.modifiers);
        }
    } else if (prompt.kind === "info" && _isStatsPrompt(prompt)) {
        actionAnswer.value = "";
        actionAnswer.placeholder = "Enter aby zamknąć";
        actionAnswer.required = false;
        actionAnswer.classList.add("input-hidden");
        actionPrompt.classList.add("hidden");
        _renderStatsPanel(prompt.prompt_long || "");
    } else if (prompt.kind === "info") {
        actionAnswer.value = "";
        actionAnswer.placeholder = "Enter aby zamknąć";
        actionAnswer.required = false;
        actionAnswer.classList.add("input-hidden");
    } else if (normalized.length > 0) {
        if (!renderCharacterCreationShopColumns(normalized)) {
            ensureChoiceList(normalized);
        }
        actionAnswer.value = selectedChoiceIndex >= 0 ? currentChoices[selectedChoiceIndex] || "" : "";
        actionAnswer.classList.add("input-hidden");
        actionAnswer.required = false;
        updateChoiceHighlight();
        updateChoiceDesc();
        actionDesc.classList.add("hidden");
    } else {
        actionAnswer.placeholder = "Twoja odpowiedź...";
        actionAnswer.required = true;
        actionAnswer.classList.remove("input-hidden");
        actionDesc.classList.remove("hidden");
    }
    _renderNaturalControls(prompt);
    actionForm.classList.remove("hidden");
    renderHeroes();
    updateSessionSummary();
    if (rollStackState) {
        _renderRollStack();
    } else {
        actionAnswer.focus();
    }
}

function closePrompt() {
    activePrompt = null;
    confirmMode = false;
    storedSelection = "";
    layoutMode = "info";
    rollNaturalMode = "none";
    fileImagePayload = null;
    rollStackState = null;
    _resetMenuNumpadContext();
    actionForm.classList.add("hidden");
    actionChoices.innerHTML = "";
    actionDesc.textContent = "";
    actionDesc.classList.remove("hidden");
    actionPrompt.textContent = "";
    actionPrompt.classList.add("hidden");
    actionTitle.textContent = "Czekam na działania...";
    actionText.textContent = "";
    actionText.classList.remove("hidden");
    clearMods();
    _renderNaturalControls(null);
    refreshLeftIllustration();
    renderHeroes();
    updateSessionSummary();
    processPromptQueue();
}

function processPromptQueue() {
    if (activePrompt) return;
    const next = promptQueue.shift();
    if (!next) return;
    openPrompt(next);
}

function selectChoice(idx) {
    if (idx < 0 || idx >= currentChoices.length) return;
    selectedChoiceIndex = idx;
    if (_isGroupedMenuNumpad()) {
        const group = menuNumpadContext.indexToGroup?.[idx];
        if (group === "filters" || group === "list") {
            menuNumpadContext.activeGroup = group;
        }
    }
    choiceMeta = choiceMeta.map((c, i) => ({ ...c, expanded: i === idx }));
    actionAnswer.value = currentChoices[idx];
    updateChoiceHighlight();
    updateChoiceDesc();
    renderHeroes();
}

function updateChoiceHighlight() {
    const pills = actionChoices.querySelectorAll(".choice-pill");
    pills.forEach((pill, fallbackIndex) => {
        const dataIndex = Number.parseInt(String(pill.dataset.choiceIndex || ""), 10);
        const idx = Number.isInteger(dataIndex) ? dataIndex : fallbackIndex;
        const isSelected = idx === selectedChoiceIndex;
        const isExpanded = choiceMeta[idx]?.expanded;
        pill.classList.toggle("selected", isSelected);
        pill.classList.toggle("expanded", isExpanded);
        if (isSelected) {
            pill.scrollIntoView({ block: "nearest", inline: "nearest" });
        }
    });
    const columns = actionChoices.querySelectorAll(".choice-column");
    columns.forEach((column) => {
        if (!_isGroupedMenuNumpad()) {
            column.classList.remove("active");
            return;
        }
        const group = String(column.dataset.group || "");
        column.classList.toggle("active", group === menuNumpadContext.activeGroup);
    });
}

function updateChoiceDesc() {
    if (actionDesc.classList.contains("hidden")) {
        return;
    }
    if (selectedChoiceIndex < 0 || selectedChoiceIndex >= choiceMeta.length) {
        actionDesc.textContent = "";
        return;
    }
    actionDesc.textContent = choiceMeta[selectedChoiceIndex]?.desc || "";
}

function _isStatsPrompt(prompt) {
    if (!prompt) return false;
    const source = String(prompt.source || "").toLowerCase();
    const title = String(prompt.title || prompt.prompt || "").toLowerCase();
    return source === "stats" || title.includes("statystyk");
}

function _renderStatsPanel(rawText) {
    actionChoices.innerHTML = "";
    const panel = document.createElement("div");
    panel.className = "stats-panel";

    const lines = String(rawText || "")
        .split("\n")
        .map((line) => String(line || "").trim())
        .filter((line) => line.length > 0);

    let section = document.createElement("div");
    section.className = "stats-section";
    const defaultHeader = document.createElement("div");
    defaultHeader.className = "stats-section-title";
    defaultHeader.textContent = "Postać";
    section.appendChild(defaultHeader);
    panel.appendChild(section);

    const appendRow = (label, value, kind = "kv") => {
        const row = document.createElement("div");
        row.className = `stats-row ${kind}`;
        if (label) {
            const key = document.createElement("span");
            key.className = "stats-key";
            key.textContent = label;
            row.appendChild(key);
        }
        const val = document.createElement("span");
        val.className = "stats-value";
        val.textContent = value || "";
        row.appendChild(val);
        section.appendChild(row);
    };

    lines.forEach((line) => {
        if (line.endsWith(":") && !line.startsWith("- ")) {
            section = document.createElement("div");
            section.className = "stats-section";
            const header = document.createElement("div");
            header.className = "stats-section-title";
            header.textContent = line.slice(0, -1).trim();
            section.appendChild(header);
            panel.appendChild(section);
            return;
        }
        if (line.startsWith("- ")) {
            appendRow("•", line.slice(2).trim(), "bullet");
            return;
        }
        const sep = line.indexOf(":");
        if (sep > 0) {
            const key = line.slice(0, sep).trim();
            const value = line.slice(sep + 1).trim();
            appendRow(key, value, "kv");
            return;
        }
        appendRow("", line, "plain");
    });

    actionChoices.appendChild(panel);
    actionDesc.classList.remove("hidden");
    actionDesc.textContent = "Enter: zamknij panel statystyk.";
}

function normalizeChoices(prompt) {
    const ensureStructuredChoiceDesc = (label, rawDesc) => {
        const sectionValue = (line) => {
            const idx = String(line || "").indexOf(":");
            if (idx < 0) return "";
            return String(line).slice(idx + 1).trim();
        };
        const normalizeBulletLine = (line) => String(line || "").replace(/^[\-\u2022]\s*/, "").trim();
        const splitEffectParts = (raw) => {
            const text = String(raw || "").trim();
            if (!text) return [];
            return text
                .split(/\r?\n/)
                .map((item) => normalizeBulletLine(item))
                .filter(Boolean)
                .flatMap((item) => item.split(/\s*\|\s*/))
                .map((item) => String(item || "").trim())
                .filter(Boolean);
        };
        const formatStructured = (fluff, when, effect) => {
            const whenText = String(when || "").trim() || "Po wybraniu tej opcji.";
            const effectParts = splitEffectParts(effect);
            if (!effectParts.length) effectParts.push("Brak dodatkowego opisu mechaniki.");
            const lines = [`Fluff: ${String(fluff || "").trim() || "Opcja wyboru."}`, "Mechanika:", `- Kiedy: ${whenText}`];
            if (effectParts.length === 1) {
                lines.push(`- Efekt: ${effectParts[0]}`);
            } else {
                lines.push("- Efekt:");
                effectParts.forEach((item) => lines.push(`  - ${item}`));
            }
            return lines.join("\n");
        };
        const desc = String(rawDesc || "").trim();
        if (!desc) {
            return formatStructured("Opcja wyboru.", "Po wybraniu tej opcji.", "Brak dodatkowego opisu mechaniki.");
        }
        const alreadyStructured =
            !desc.includes("|") &&
            /^\s*Fluff\s*:/im.test(desc) &&
            /^\s*Mechanika\s*:\s*$/im.test(desc) &&
            /^\s*-\s*Kiedy\s*:/im.test(desc) &&
            /^\s*-\s*Efekt\s*:/im.test(desc);
        if (alreadyStructured) return desc;
        let fluff = "";
        let when = "";
        let effect = "";
        let mechanics = "";

        const lines = desc.split(/\r?\n/).map((line) => String(line || "").trim()).filter(Boolean);
        if (/^\s*(NAZWA\s*:|Fluff\s*:|Mechanika\s*:|Kiedy\s*:|Efekt\s*:)/i.test(desc)) {
            lines.forEach((line) => {
                const normalized = normalizeBulletLine(line);
                if (/^Fluff\s*:/i.test(normalized)) fluff = sectionValue(normalized) || fluff;
                else if (/^Mechanika\s*:/i.test(normalized)) mechanics = sectionValue(normalized) || mechanics;
                else if (/^Kiedy\s*:/i.test(normalized)) when = sectionValue(normalized) || when;
                else if (/^Efekt\s*:/i.test(normalized)) effect = sectionValue(normalized) || effect;
            });
        } else {
            const compact = desc.replace(/\s+/g, " ").trim();
            const dotIdx = compact.indexOf(".");
            fluff = dotIdx > 0 && dotIdx < 180 ? compact.slice(0, dotIdx + 1).trim() : compact;
            mechanics = desc;
        }

        if (!fluff) {
            const compact = desc.replace(/\s+/g, " ").trim();
            const dotIdx = compact.indexOf(".");
            fluff = dotIdx > 0 && dotIdx < 180 ? compact.slice(0, dotIdx + 1).trim() : compact || "Opcja wyboru.";
        }
        const mechanicsSource = mechanics || desc;
        if (!when) {
            const whenMatch = mechanicsSource.match(/Kiedy:\s*(.*?)(?:\s*(?:\||;)\s*Efekt:|\s+Efekt:|$)/i);
            when = whenMatch && whenMatch[1] ? String(whenMatch[1]).trim() : "Po wybraniu tej opcji.";
        }
        if (!effect) {
            const effectMatch = mechanicsSource.match(/Efekt:\s*(.*)$/i);
            effect = effectMatch && effectMatch[1] ? String(effectMatch[1]).trim() : mechanicsSource;
        }
        if (!effect) effect = "Brak dodatkowego opisu mechaniki.";
        return formatStructured(fluff, when, effect);
    };
    // prefer structured choice_meta if provided
    if (Array.isArray(prompt.choice_meta) && prompt.choice_meta.length) {
        return prompt.choice_meta.map((c) => ({
            raw: c.raw || c.label || "",
            label: c.label || c.raw || "",
            desc: ensureStructuredChoiceDesc(c.label || c.raw || "", c.desc || ""),
            key: c.key || "",
            heroPreview:
                c && typeof c.hero_preview === "object" && c.hero_preview
                    ? c.hero_preview
                    : c && typeof c.heroPreview === "object" && c.heroPreview
                    ? c.heroPreview
                    : null,
        }));
    }
    const rawChoices = Array.isArray(prompt.choices) ? prompt.choices : [];
    const cardMap = {
        accept: "+",
        decline: "-",
        move: "1",
        interact: "2",
        seek: "3",
        stealth: "4",
        test_attack: "5",
        special: "6",
        delay: "7",
        end: "8",
    };
    return rawChoices.map((raw) => {
        const norm = String(raw).trim();
        const lowerNorm = norm.toLowerCase();
        let key = "";
        let head = norm;
        // prefiks przed ":" traktuj jako key (np. "1: Otwórz")
        if (norm.includes(":")) {
            const [pref, ...rest] = norm.split(":");
            if (pref.trim().length === 1) {
                key = pref.trim();
                head = rest.join(":").trim();
            }
        }
        const parts = head.split("—");
        const title = parts[0].trim();
        const desc = parts.slice(1).join("—").trim();
        const mapped =
            cardMap[title.toLowerCase()] ||
            cardMap[lowerNorm] ||
            (key ? cardMap[key.toLowerCase()] : undefined) ||
            key;
        const showMapped = mapped && !/^[0-9]+$/.test(String(mapped));
        const label = showMapped ? `${mapped} · ${title}` : title;
        const effectiveKey = mapped || key || (title.length === 1 ? title : "");
        return { raw: norm, label, desc: ensureStructuredChoiceDesc(label, desc), key: effectiveKey };
    });
}

function renderChoiceDescription(rawDesc) {
    const container = document.createElement("div");
    container.className = "desc-structured";

    const appendLabelValue = (parent, label, text, lineClass = "") => {
        const row = document.createElement("div");
        row.className = lineClass ? `desc-line ${lineClass}` : "desc-line";
        if (label) {
            const labelEl = document.createElement("span");
            labelEl.className = "desc-label";
            labelEl.textContent = `${label}:`;
            row.appendChild(labelEl);
        }
        if (text) {
            const textEl = document.createElement("span");
            textEl.className = "desc-text";
            textEl.textContent = text;
            row.appendChild(textEl);
        }
        parent.appendChild(row);
        return row;
    };

    const appendBullet = (text, nested = false) => {
        const row = document.createElement("div");
        row.className = nested ? "desc-bullet desc-bullet-nested" : "desc-bullet";
        const marker = document.createElement("span");
        marker.className = "desc-bullet-marker";
        marker.textContent = "•";
        row.appendChild(marker);

        const body = document.createElement("span");
        body.className = "desc-bullet-body";
        const trimmed = String(text || "").trim();
        const sep = trimmed.indexOf(":");
        if (sep > 0 && sep < 42) {
            const labelEl = document.createElement("span");
            labelEl.className = "desc-label";
            labelEl.textContent = `${trimmed.slice(0, sep).trim()}:`;
            body.appendChild(labelEl);
            const value = trimmed.slice(sep + 1).trim();
            if (value) {
                const valueEl = document.createElement("span");
                valueEl.className = "desc-text";
                valueEl.textContent = ` ${value}`;
                body.appendChild(valueEl);
            }
        } else {
            body.textContent = trimmed;
        }
        row.appendChild(body);
        container.appendChild(row);
    };

    const desc = String(rawDesc || "").trim();
    if (!desc) return container;

    const lines = desc.split(/\r?\n/).filter((line) => String(line || "").trim());
    lines.forEach((line) => {
        const raw = String(line || "");
        const trimmed = raw.trim();
        if (!trimmed) return;

        if (/^Fluff\s*:/i.test(trimmed)) {
            appendLabelValue(container, "Fluff", trimmed.split(":", 2)[1]?.trim() || "", "desc-fluff");
            return;
        }
        if (/^Mechanika\s*:\s*$/i.test(trimmed)) {
            const header = document.createElement("div");
            header.className = "desc-section-title";
            header.textContent = "Mechanika";
            container.appendChild(header);
            return;
        }
        if (/^-\s*(Kiedy|Efekt)\s*:/i.test(trimmed)) {
            const match = trimmed.match(/^-\s*([^:]+):\s*(.*)$/);
            const label = match?.[1]?.trim() || "";
            const value = match?.[2]?.trim() || "";
            appendLabelValue(container, label, value, "desc-topline");
            return;
        }
        if (/^\s+-\s+/.test(raw)) {
            appendBullet(raw.replace(/^\s+-\s+/, ""), true);
            return;
        }
        if (/^-\s+/.test(trimmed)) {
            appendBullet(trimmed.replace(/^-\s+/, ""), false);
            return;
        }

        const plain = document.createElement("div");
        plain.className = "desc-line desc-plain";
        plain.textContent = trimmed;
        container.appendChild(plain);
    });

    return container;
}

function _coerceHeroPreview(rawPreview, fallbackLabel = "") {
    return coerceHeroPreview(rawPreview, fallbackLabel, PLACEHOLDER_IMAGE);
}

function _currentHeroSelectPreview() {
    if (!activePrompt) return null;
    const source = String(activePrompt.source || "").toLowerCase();
    if (source !== "hero_select") return null;
    if (!Array.isArray(choiceMeta) || selectedChoiceIndex < 0 || selectedChoiceIndex >= choiceMeta.length) {
        return null;
    }
    const entry = choiceMeta[selectedChoiceIndex] || {};
    return _coerceHeroPreview(entry.heroPreview || entry.hero_preview, entry.label || "Bohater");
}

// --- Heroes rendering ---

function renderHeroes() {
    const result = renderHeroesPanel({
        refs,
        heroesMap: heroes,
        activeActorId,
        activePromptSource: String(activePrompt?.source || "").toLowerCase(),
        creationPreviewHeroId,
        selectedHeroId,
        heroSelectPreview: _currentHeroSelectPreview(),
        placeholderImage: PLACEHOLDER_IMAGE,
        onSelectHero: (heroId) => {
            selectedHeroId = heroId;
            renderHeroes();
        },
        cloneCreationAbilityDefaults: _cloneCreationAbilityDefaults,
    });
    const nextSelectedHeroId = result?.selectedHeroId || null;
    if (nextSelectedHeroId !== selectedHeroId) {
        selectedHeroId = nextSelectedHeroId;
        renderHeroesPanel({
            refs,
            heroesMap: heroes,
            activeActorId,
            activePromptSource: String(activePrompt?.source || "").toLowerCase(),
            creationPreviewHeroId,
            selectedHeroId,
            heroSelectPreview: _currentHeroSelectPreview(),
            placeholderImage: PLACEHOLDER_IMAGE,
            onSelectHero: (heroId) => {
                selectedHeroId = heroId;
                renderHeroes();
            },
            cloneCreationAbilityDefaults: _cloneCreationAbilityDefaults,
        });
    }
}

function renderInitiative() {
    renderInitiativePanel(refs, initiativeState);
}
