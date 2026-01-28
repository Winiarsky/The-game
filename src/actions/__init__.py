"""Actions package initializer to register all available actions."""

# Import actions for side effects (registration via decorator)
from . import move  # noqa: F401
from . import interact  # noqa: F401
from . import seek  # noqa: F401
from . import stealth  # noqa: F401
from . import attack  # noqa: F401
from . import special  # noqa: F401
