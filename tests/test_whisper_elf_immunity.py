import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin  # noqa: E402
from statuses import BLINDED_STATUS  # noqa: E402
from statuses.race.elfs.heritages.whisper_elf import WHISPER_ELF_STATUS  # noqa: E402


class DummyHero(StatusMixin):
    def __init__(self):
        self.statuses = []


def test_whisper_elf_does_not_block_blinded_status():
    hero = DummyHero()
    hero.add_status(WHISPER_ELF_STATUS)
    added = hero.add_status(BLINDED_STATUS)
    assert added
    assert hero.has_status(BLINDED_STATUS)
