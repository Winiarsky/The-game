from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from layered_scenarios import compile_layered_scenario, load_layered_scenario


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO_FLOWS_DIR = PROJECT_ROOT / "scenario_flows"
DEFAULT_SCENARIOS_DIR = PROJECT_ROOT / "scenarios"
DEFAULT_LAYERED_SCENARIOS_DIR = PROJECT_ROOT / "scenarios_layered"
SCENARIO_FLOW_FORMAT = "scenario_flow_v1"


@dataclass(slots=True)
class ScenarioMapRef:
    map_id: str
    source: str
    source_type: str = "runtime"
    label: str = ""


def list_scenario_flow_names(flows_dir: Path | None = None) -> list[str]:
    root = Path(flows_dir or DEFAULT_SCENARIO_FLOWS_DIR)
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.json") if path.is_file())


def scenario_flow_path(name: str, flows_dir: Path | None = None) -> Path:
    safe_name = Path(str(name or "")).stem
    if not safe_name:
        raise ValueError("Nazwa flow scenariusza jest wymagana.")
    return Path(flows_dir or DEFAULT_SCENARIO_FLOWS_DIR) / f"{safe_name}.json"


def load_scenario_flow(name_or_path: str | Path, *, flows_dir: Path | None = None) -> dict[str, Any]:
    path = Path(str(name_or_path))
    if not path.exists():
        path = scenario_flow_path(str(name_or_path), flows_dir=flows_dir)
    payload = json.loads(path.read_text(encoding="utf-8"))
    normalized = validate_scenario_flow(payload)
    normalized["_source_path"] = str(path)
    return normalized


def map_catalog(
    *,
    scenarios_dir: Path | None = None,
    layered_dir: Path | None = None,
) -> dict[str, list[str]]:
    runtime_root = Path(scenarios_dir or DEFAULT_SCENARIOS_DIR)
    layered_root = Path(layered_dir or DEFAULT_LAYERED_SCENARIOS_DIR)
    runtime_names = sorted(path.stem for path in runtime_root.glob("*.json")) if runtime_root.exists() else []
    layered_names = sorted(path.stem for path in layered_root.glob("*.json")) if layered_root.exists() else []
    return {"runtime": runtime_names, "layered": layered_names}


def _normalize_map_ref(raw: dict[str, Any]) -> ScenarioMapRef:
    if not isinstance(raw, dict):
        raise ValueError("Każda mapa scenariusza musi być obiektem.")
    map_id = str(raw.get("map_id") or raw.get("id") or "").strip()
    source = str(raw.get("source") or "").strip()
    source_type = str(raw.get("source_type") or raw.get("kind") or "runtime").strip().lower() or "runtime"
    label = str(raw.get("label") or map_id).strip()
    if not map_id:
        raise ValueError("Mapa scenariusza wymaga map_id.")
    if not source:
        raise ValueError(f"Mapa '{map_id}' wymaga pola source.")
    if source_type not in {"runtime", "layered"}:
        raise ValueError(f"Mapa '{map_id}' ma nieobsługiwany source_type '{source_type}'.")
    return ScenarioMapRef(map_id=map_id, source=source, source_type=source_type, label=label)


def _normalize_conditions(raw_conditions: Any) -> list[dict[str, Any]]:
    conditions: list[dict[str, Any]] = []
    for condition in list(raw_conditions or []):
        if not isinstance(condition, dict):
            raise ValueError("Każdy condition musi być obiektem.")
        kind = str(condition.get("type") or condition.get("kind") or "").strip().lower()
        if not kind:
            raise ValueError(f"Condition wymaga pola type/kind: {condition!r}")
        normalized = dict(condition)
        normalized["type"] = kind
        conditions.append(normalized)
    return conditions


def _normalize_actions(raw_actions: Any) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for action in list(raw_actions or []):
        if not isinstance(action, dict):
            raise ValueError("Każda akcja eventu musi być obiektem.")
        kind = str(action.get("type") or action.get("kind") or "").strip().lower()
        if not kind:
            raise ValueError(f"Akcja wymaga pola type/kind: {action!r}")
        normalized = dict(action)
        normalized["type"] = kind
        actions.append(normalized)
    return actions


def _normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Każdy event musi być obiektem.")
    event_id = str(raw.get("id") or "").strip()
    trigger = str(raw.get("trigger") or raw.get("trigger_type") or "").strip().lower()
    if not event_id:
        raise ValueError("Event wymaga id.")
    if not trigger:
        raise ValueError(f"Event '{event_id}' wymaga trigger.")
    return {
        **dict(raw),
        "id": event_id,
        "trigger": trigger,
        "map_id": str(raw.get("map_id") or "").strip() or None,
        "target_id": str(raw.get("target_id") or raw.get("object_id") or raw.get("exit_id") or "").strip() or None,
        "conditions": _normalize_conditions(raw.get("conditions")),
        "actions": _normalize_actions(raw.get("actions")),
        "once": bool(raw.get("once", False)),
    }


def _normalize_transition(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Każde przejście musi być obiektem.")
    transition_id = str(raw.get("id") or "").strip()
    from_map_id = str(raw.get("from_map_id") or raw.get("from") or "").strip()
    exit_id = str(raw.get("exit_id") or "").strip()
    to_map_id = str(raw.get("to_map_id") or raw.get("to") or "").strip()
    target_anchor = str(raw.get("target_entry_anchor_id") or raw.get("entry_anchor_id") or "").strip()
    if not transition_id:
        raise ValueError("Transition wymaga id.")
    if not from_map_id or not exit_id or not to_map_id or not target_anchor:
        raise ValueError(f"Transition '{transition_id}' wymaga from_map_id, exit_id, to_map_id i target_entry_anchor_id.")
    return {
        **dict(raw),
        "id": transition_id,
        "from_map_id": from_map_id,
        "exit_id": exit_id,
        "to_map_id": to_map_id,
        "target_entry_anchor_id": target_anchor,
        "conditions": _normalize_conditions(raw.get("conditions")),
    }


def resolve_map_payload(map_ref: ScenarioMapRef | dict[str, Any]) -> dict[str, Any]:
    if isinstance(map_ref, dict):
        map_ref = _normalize_map_ref(map_ref)
    source_path = Path(map_ref.source)
    if map_ref.source_type == "layered":
        if not source_path.exists():
            source_path = DEFAULT_LAYERED_SCENARIOS_DIR / f"{map_ref.source}.json"
        layered = load_layered_scenario(source_path, layered_dir=DEFAULT_LAYERED_SCENARIOS_DIR)
        compiled = compile_layered_scenario(layered)
        compiled.setdefault("metadata", {})
        compiled["metadata"] = {
            **dict(compiled.get("metadata") or {}),
            "resolved_map_id": map_ref.map_id,
            "resolved_source_type": "layered",
        }
        return compiled

    if not source_path.exists():
        source_path = DEFAULT_SCENARIOS_DIR / f"{map_ref.source}.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload = copy.deepcopy(payload)
    payload.setdefault("metadata", {})
    payload["metadata"] = {
        **dict(payload.get("metadata") or {}),
        "resolved_map_id": map_ref.map_id,
        "resolved_source_type": "runtime",
    }
    return payload


def inspect_runtime_map_logic(runtime_payload: dict[str, Any]) -> dict[str, dict[str, list[list[int]]]]:
    exits: dict[str, list[list[int]]] = {}
    anchors: dict[str, list[list[int]]] = {}
    for obj in list(runtime_payload.get("objects") or []):
        if str(obj.get("category") or "").strip() != "Interactables":
            continue
        object_id = str(obj.get("object_id") or "").strip()
        for inst in list(obj.get("instances") or []):
            if not isinstance(inst, dict):
                continue
            pos = inst.get("position") or inst.get("pos")
            config = dict(inst.get("config") or {})
            if not isinstance(pos, list) and not isinstance(pos, tuple):
                continue
            normalized_pos = [int(pos[0]), int(pos[1])]
            if object_id == "scenario_exit":
                exit_id = str(config.get("exit_id") or "").strip()
                if exit_id:
                    exits.setdefault(exit_id, []).append(normalized_pos)
            if object_id == "entry_anchor":
                anchor_id = str(config.get("entry_anchor_id") or "").strip()
                if anchor_id:
                    anchors.setdefault(anchor_id, []).append(normalized_pos)
    return {"exits": exits, "anchors": anchors}


def validate_scenario_flow(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Scenario flow musi być obiektem JSON.")
    format_name = str(payload.get("format") or "").strip().lower()
    if format_name != SCENARIO_FLOW_FORMAT:
        raise ValueError(f"Scenario flow musi mieć format='{SCENARIO_FLOW_FORMAT}'.")

    scenario_id = str(payload.get("scenario_id") or payload.get("id") or "").strip()
    entry_map_id = str(payload.get("entry_map_id") or "").strip()
    if not scenario_id:
        raise ValueError("Scenario flow wymaga scenario_id.")
    maps = [_normalize_map_ref(item) for item in list(payload.get("maps") or [])]
    if not maps:
        raise ValueError("Scenario flow wymaga co najmniej jednej mapy.")
    map_ids = [item.map_id for item in maps]
    if len(set(map_ids)) != len(map_ids):
        raise ValueError("map_id w scenario flow muszą być unikalne.")
    if not entry_map_id:
        raise ValueError("Scenario flow wymaga entry_map_id.")
    if entry_map_id not in set(map_ids):
        raise ValueError(f"entry_map_id '{entry_map_id}' nie istnieje w maps[].")

    transitions = [_normalize_transition(item) for item in list(payload.get("transitions") or [])]
    events = [_normalize_event(item) for item in list(payload.get("events") or [])]
    global_flags = dict(payload.get("global_flags") or {})
    objectives = list(payload.get("objectives") or [])
    checkpoint_policy = dict(payload.get("checkpoint_policy") or {})

    map_logic_index: dict[str, dict[str, dict[str, list[list[int]]]]] = {}
    for map_ref in maps:
        runtime_payload = resolve_map_payload(map_ref)
        logic = inspect_runtime_map_logic(runtime_payload)
        map_logic_index[map_ref.map_id] = logic
        duplicate_exits = [key for key, positions in logic["exits"].items() if len(positions) > 1]
        duplicate_anchors = [key for key, positions in logic["anchors"].items() if len(positions) > 1]
        if duplicate_exits:
            raise ValueError(
                f"Mapa '{map_ref.map_id}' zawiera zduplikowane exit_id na wielu instancjach: {duplicate_exits}."
            )
        if duplicate_anchors:
            raise ValueError(
                f"Mapa '{map_ref.map_id}' zawiera zduplikowane entry_anchor_id na wielu instancjach: {duplicate_anchors}."
            )

    if not map_logic_index.get(entry_map_id, {}).get("anchors"):
        raise ValueError(f"Mapa wejściowa '{entry_map_id}' musi zawierać co najmniej jeden entry_anchor.")

    for transition in transitions:
        from_map_id = transition["from_map_id"]
        to_map_id = transition["to_map_id"]
        exit_id = transition["exit_id"]
        target_anchor = transition["target_entry_anchor_id"]
        if from_map_id not in map_logic_index:
            raise ValueError(f"Transition '{transition['id']}' odwołuje się do nieznanej mapy źródłowej '{from_map_id}'.")
        if to_map_id not in map_logic_index:
            raise ValueError(f"Transition '{transition['id']}' odwołuje się do nieznanej mapy docelowej '{to_map_id}'.")
        if exit_id not in map_logic_index[from_map_id]["exits"]:
            raise ValueError(f"Transition '{transition['id']}' używa nieznanego exit_id '{exit_id}' na mapie '{from_map_id}'.")
        if target_anchor not in map_logic_index[to_map_id]["anchors"]:
            raise ValueError(
                f"Transition '{transition['id']}' używa nieznanego entry_anchor_id '{target_anchor}' na mapie '{to_map_id}'."
            )

    known_flags = set(str(key).strip() for key in global_flags.keys())
    known_transition_ids = {str(item["id"]).strip() for item in transitions}
    known_map_ids = set(map_ids)
    for event in events:
        if event["map_id"] and event["map_id"] not in known_map_ids:
            raise ValueError(f"Event '{event['id']}' odwołuje się do nieznanej mapy '{event['map_id']}'.")
        if event["trigger"] in {"object_revealed", "exit_enter", "exit_interact"}:
            if not event["map_id"] or not event["target_id"]:
                raise ValueError(f"Event '{event['id']}' wymaga map_id i target_id dla triggera '{event['trigger']}'.")
        for condition in event["conditions"]:
            kind = str(condition.get("type") or "").strip().lower()
            if kind == "flag":
                flag = str(condition.get("flag") or "").strip()
                if flag and flag not in known_flags:
                    raise ValueError(f"Event '{event['id']}' używa nieznanej flagi '{flag}' w conditions.")
            if kind == "visited_map":
                map_id = str(condition.get("map_id") or "").strip()
                if map_id and map_id not in known_map_ids:
                    raise ValueError(f"Event '{event['id']}' używa nieznanej mapy '{map_id}' w conditions.")
        for action in event["actions"]:
            kind = str(action.get("type") or "").strip().lower()
            if kind in {"set_flag", "clear_flag"}:
                flag = str(action.get("flag") or "").strip()
                if not flag:
                    raise ValueError(f"Event '{event['id']}' ma akcję '{kind}' bez flag.")
                known_flags.add(flag)
            if kind == "go_to_map":
                map_id = str(action.get("map_id") or "").strip()
                anchor = str(action.get("entry_anchor_id") or action.get("target_entry_anchor_id") or "").strip()
                if map_id not in known_map_ids:
                    raise ValueError(f"Event '{event['id']}' kieruje do nieznanej mapy '{map_id}'.")
                if anchor and anchor not in map_logic_index[map_id]["anchors"]:
                    raise ValueError(f"Event '{event['id']}' używa nieznanego anchor '{anchor}' na mapie '{map_id}'.")
            if kind == "activate_transition":
                transition_id = str(action.get("transition_id") or "").strip()
                if transition_id and transition_id not in known_transition_ids:
                    raise ValueError(f"Event '{event['id']}' używa nieznanego transition_id '{transition_id}'.")

    return {
        "format": SCENARIO_FLOW_FORMAT,
        "scenario_id": scenario_id,
        "label": str(payload.get("label") or scenario_id),
        "description": str(payload.get("description") or ""),
        "entry_map_id": entry_map_id,
        "maps": [
            {
                "map_id": item.map_id,
                "source": item.source,
                "source_type": item.source_type,
                "label": item.label,
            }
            for item in maps
        ],
        "transitions": transitions,
        "global_flags": global_flags,
        "events": events,
        "objectives": objectives,
        "checkpoint_policy": checkpoint_policy,
        "map_logic_index": map_logic_index,
    }
