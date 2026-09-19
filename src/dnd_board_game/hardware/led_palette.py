from __future__ import annotations

RGBColor = tuple[int, int, int]


class LedColor:
    """Semantic LED palette for board feedback.

    Keep game/rules code talking about intent instead of raw RGB values.
    """

    PANEL_ACTION: RGBColor = (30, 110, 255)
    PANEL_BONUS_ACTION: RGBColor = (255, 120, 20)
    PANEL_MOVEMENT: RGBColor = (40, 220, 95)
    PANEL_TURN_CONTROL: RGBColor = (255, 255, 255)
    PANEL_FREE_ACTION: RGBColor = (200, 170, 65)
    PANEL_MINUS: RGBColor = (217, 0, 0)
    PANEL_PLUS: RGBColor = (0, 217, 0)
    PANEL_ACCEPT: RGBColor = (0, 68, 217)
    PANEL_BACK: RGBColor = (217, 136, 0)

    ACTIVE_ACTOR: RGBColor = (255, 255, 255)
    PLAYER_START_ZONE: RGBColor = (0, 220, 255)
    ALLY: RGBColor = (0, 220, 255)
    VISIBLE_ALLY: RGBColor = (80, 180, 200)
    LEGAL_ABILITY_TARGET: RGBColor = (0, 65, 75)
    SELECTED_ABILITY_TARGET: RGBColor = (0, 220, 255)

    LEGAL_MOVEMENT: RGBColor = (0, 110, 160)
    MOVEMENT_RANGE: RGBColor = (0, 80, 220)
    PLAYER_MOVEMENT_PATH: RGBColor = (255, 210, 0)
    MOVEMENT_DESTINATION: RGBColor = (0, 255, 120)
    MOVEMENT_COMMITTED: RGBColor = (0, 255, 120)

    LEGAL_ATTACK_TARGET: RGBColor = (0, 80, 220)
    SELECTED_ATTACK_TARGET: RGBColor = (0, 80, 220)
    ATTACK_HIT: RGBColor = (0, 255, 120)
    ATTACK_MISS: RGBColor = (255, 0, 0)
    ATTACK_CRITICAL_HIT: RGBColor = (255, 210, 0)
    RANGED_PROJECTILE: RGBColor = (255, 190, 40)

    ENEMY: RGBColor = (255, 0, 80)
    STEALTH_OBSERVER_SEES: RGBColor = (255, 120, 0)
    STEALTH_OBSERVER_UNAWARE: RGBColor = (0, 220, 255)
    MENU_PINK: RGBColor = (255, 0, 180)
    MENU_WHITE: RGBColor = (255, 255, 255)
    ACTION_BASIC: RGBColor = (255, 210, 0)
    ACTION_ATTACK: RGBColor = (255, 45, 45)
    ACTION_MAGIC: RGBColor = (180, 0, 255)
    ACTION_SUPPORT: RGBColor = (0, 220, 255)
    ACTION_MANEUVER: RGBColor = (255, 120, 0)
    ACTION_ITEM: RGBColor = (0, 255, 120)
    ACTION_EQUIPMENT: RGBColor = (180, 180, 200)
    VISIBLE_ENEMY_OUT_OF_RANGE: RGBColor = (120, 0, 45)
    ENEMY_MOVEMENT_PATH: RGBColor = (220, 0, 0)
    ENEMY_MOVEMENT_DESTINATION: RGBColor = (255, 120, 0)
    ENEMY_FLEE_PATH: RGBColor = (255, 0, 180)
    ENEMY_ESCAPE_DESTINATION: RGBColor = (0, 220, 255)
    ENEMY_REGROUP_PATH: RGBColor = (255, 190, 40)
    ENEMY_GUARD_DESTINATION: RGBColor = (180, 0, 255)
    ACTOR_DEFEATED: RGBColor = (255, 0, 0)

    INTERACTIVE_OBJECT: RGBColor = (0, 255, 120)
    SETUP_FOOTPRINT: RGBColor = (0, 65, 30)
    INTERACTION_SUCCESS: RGBColor = (0, 255, 120)
    INTERACTION_FAILURE: RGBColor = (255, 0, 0)
    MULTI_OPTION_TILE: RGBColor = (180, 120, 40)
    MENU_PURPLE: RGBColor = (180, 0, 255)

    DIFFICULT_TERRAIN: RGBColor = (255, 120, 0)
    BLOCKING_TERRAIN: RGBColor = (180, 0, 0)
    MARKER: RGBColor = (255, 210, 0)
    AREA_CENTER_RANGE: RGBColor = (90, 70, 20)
    AREA_EFFECT: RGBColor = (255, 170, 0)
    AREA_ANCHOR: RGBColor = (255, 255, 255)
    AURA_BLESS_DIM: RGBColor = (0, 55, 18)
    AURA_BLESS_ACTIVE: RGBColor = (0, 220, 85)
    AURA_DIVINE_CARE_DIM: RGBColor = (70, 48, 0)
    AURA_DIVINE_CARE_ACTIVE: RGBColor = (255, 190, 35)
    AURA_HEALING_DIM: RGBColor = (0, 45, 55)
    AURA_HEALING_ACTIVE: RGBColor = (0, 220, 255)
    INVALID_SELECTION: RGBColor = (255, 0, 0)


# Identity colors belong to party slots, not character records.  A character
# keeps the same slot (and therefore color) for the whole loaded game.
PARTY_IDENTITY_COLORS: tuple[RGBColor, ...] = (
    (255, 45, 45),    # 1: red
    (45, 120, 255),   # 2: blue
    (40, 220, 105),   # 3: green
    (190, 65, 255),   # 4: purple
    (255, 180, 35),   # 5: orange
)


LED_COLOR_NAMES_PL: dict[RGBColor, str] = {
    LedColor.ACTIVE_ACTOR: "biały",
    LedColor.ATTACK_MISS: "czerwony",
    LedColor.MOVEMENT_RANGE: "niebieski",
    LedColor.INTERACTIVE_OBJECT: "zielony",
    LedColor.MARKER: "żółty",
    LedColor.AREA_CENTER_RANGE: "przygaszony żółty",
    LedColor.AREA_EFFECT: "jasnopomarańczowy",
    LedColor.AURA_BLESS_ACTIVE: "zielony",
    LedColor.AURA_DIVINE_CARE_ACTIVE: "złoty",
    LedColor.AURA_HEALING_ACTIVE: "turkusowy",
    LedColor.ENEMY_MOVEMENT_DESTINATION: "pomarańczowy",
    LedColor.STEALTH_OBSERVER_SEES: "pomarańczowy",
    LedColor.STEALTH_OBSERVER_UNAWARE: "turkusowy",
    LedColor.MENU_PURPLE: "fioletowy",
    LedColor.MENU_PINK: "różowy",
    LedColor.MENU_WHITE: "biały",
    LedColor.ACTION_BASIC: "żółty",
    LedColor.ACTION_ATTACK: "czerwony",
    LedColor.ACTION_MAGIC: "fioletowy",
    LedColor.ACTION_SUPPORT: "turkusowy",
    LedColor.ACTION_MANEUVER: "pomarańczowy",
    LedColor.ACTION_ITEM: "zielony",
    LedColor.ACTION_EQUIPMENT: "srebrny",
    LedColor.PLAYER_START_ZONE: "turkusowy",
    LedColor.MULTI_OPTION_TILE: "brązowy",
    LedColor.BLOCKING_TERRAIN: "ciemnoczerwony",
    LedColor.DIFFICULT_TERRAIN: "pomarańczowy",
    PARTY_IDENTITY_COLORS[0]: "czerwony",
    PARTY_IDENTITY_COLORS[1]: "niebieski",
    PARTY_IDENTITY_COLORS[2]: "zielony",
    PARTY_IDENTITY_COLORS[3]: "fioletowy",
    PARTY_IDENTITY_COLORS[4]: "pomarańczowy",
}


def led_color_name_pl(color: RGBColor) -> str:
    return LED_COLOR_NAMES_PL.get(color, "kolor specjalny")
