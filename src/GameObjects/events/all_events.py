# Import wszystkich eventów, aby zarejestrować je w registry.
# Używaj poprzez `import GameObjects.events.all_events` przed dispatch.

from . import move_event  # noqa: F401
from . import stealth_event  # noqa: F401
from . import seek_event  # noqa: F401
from . import interaction_event  # noqa: F401
from . import cancel_action_event  # noqa: F401
from . import end_turn_event  # noqa: F401
from . import delay_event  # noqa: F401
from . import attack_sword_event  # noqa: F401
from . import magic_missile_event  # noqa: F401
from . import phase_events  # noqa: F401
from . import enemy_move_event  # noqa: F401
from . import enemy_attack_melee_event  # noqa: F401
