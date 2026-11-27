#!/usr/bin/env python3
"""Draw random seeds from a project's draw tables to break generative ruts.

A language model asked to "pick something random" from a table it can see does
not sample — it drifts toward whatever rhymes with the prose it just wrote, so a
score set in a smoky club keeps drawing cocktail lounges and jazz. This does the
sampling outside the model: real RNG over the lists in the project's
`draw-tables-flat.md`, which stays the single source of truth (edit the Markdown
and the draws change).

The source file is found by walking up from --from to the repo root and taking
the nearest copy, so a campaign or a single adventure can override its system's
tables. See context_stack.py for that rule.

Each slot offers three candidates rather than one, so an author still exercises
judgment about what fits the adventure — but only among options the dice put on
the table. Some slots also carry a WILDCARD: an instruction to invent a fourth
option in the same register, seeded by the three drawn but printed on no chart.
The drawn text is a starting angle, never a line to quote.

Section and list names come from the tables themselves; `list` prints them. The
mode shortcuts below assume the section names the Blades '68 Score Rolodex uses
(Streets / People / General Descriptions / …); on tables organized differently,
use `draw` with names from `list`.

Usage:
  ./rolodex.py list                        # every list name, for reference
  ./rolodex.py draw casino/areas           # one slot
  ./rolodex.py draw looks traits -n 5      # several slots, 5 candidates each
  ./rolodex.py location casino             # areas + items + obstacles + dressing
  ./rolodex.py npc                         # name, look, style, profession, trait
  ./rolodex.py street                      # weather, sounds, smells, obstacles
  ./rolodex.py threats                     # physical + social opposition
  ./rolodex.py --from <adventure-dir> npc  # resolve tables from that adventure
  ./rolodex.py location old-mansion --seed 4821   # replay an earlier draw
"""
import argparse
import difflib
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context_stack

NUMBERED = re.compile(r'^\d+\.\s+(.*)')
HEADING = re.compile(r'^(#{2,4})\s+(.*)')

# A prose pool is a heading whose body is one long comma list (the name pools on
# p.434) rather than a numbered table. Below this many commas it is a sentence.
POOL_MIN_ITEMS = 8

# How often a slot also asks for something off-chart.
WILD_DEFAULT = 0.25

DRESSING = ['General Descriptions/Building Style',
            'General Descriptions/Color Schemes',
            'General Descriptions/Details']

STREET = ['Streets/Street Descriptions', 'Streets/Street Types',
          'Streets/Street Sounds', 'Streets/Street Smells',
          'Streets/Street Obstacles', 'General Descriptions/Buildings: Common',
          'General Descriptions/Building Style']

NPC = ['People/Looks', 'People/Styles', 'People/Professions',
       'People/Traits', 'People/Interests']

THREATS = ['Physical Threats', 'Social Threats']

PREAMBLE = """These are SEEDS, not content. For each slot, take the one candidate that could
belong in the adventure already in play, then write past it — change the period
detail, the scale, who it belongs to, why it is there. A drawn entry is an angle
of attack, not a line to reproduce. Drop any slot where nothing earns a place."""


def parse(path):
    """-> {'Section/List/Sub': [entries]} in document order."""
    lists, trail, key = {}, [], None
    for line in path.read_text().split('\n'):
        h = HEADING.match(line)
        if h:
            depth, title = len(h.group(1)), h.group(2).strip()
            trail = trail[:depth - 2] + [title]
            key = '/'.join(trail)
            continue
        if key is None or key.startswith('Contents'):
            continue
        item = NUMBERED.match(line)
        if item:
            lists.setdefault(key, []).append(item.group(1).strip())
        elif line.strip() and not lists.get(key):
            # Only a heading with no table of its own can hold a prose pool;
            # this keeps the italic "Also ... etc." trailers out of the draws.
            pool = [p.strip() for p in line.strip().strip('*_').split(',')]
            pool = [p for p in pool if p and not p.startswith('Book p')]
            if len(pool) >= POOL_MIN_ITEMS:
                lists.setdefault(key, []).extend(pool)
    return lists


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def resolve(keys, query, what='list'):
    """Match a loose query ('casino/areas', 'looks') to exactly one key."""
    q = norm(query)
    exact = [k for k in keys if norm(k) == q]
    tail = [k for k in keys if norm(k.split('/')[-1]) == q]
    loose = [k for k in keys if q in norm(k)]
    for hits in (exact, tail, loose):
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            sys.exit(f'"{query}" is ambiguous:\n  ' + '\n  '.join(hits))
    near = difflib.get_close_matches(q, [norm(k) for k in keys], n=3, cutoff=0.4)
    hint = f'\nDid you mean: {", ".join(near)}' if near else ''
    sys.exit(f'No {what} matches "{query}". Try `rolodex.py list`.{hint}')


def draw(lists, key, rng, n, wild):
    picks = rng.sample(lists[key], min(n, len(lists[key])))
    lines = [f'{i}. {p}' for i, p in enumerate(picks, 1)]
    if rng.random() < wild:
        lines.append(f'{len(picks) + 1}. WILDCARD — invent something else in this '
                     'register, suggested by the above but on no chart.')
    return lines


def render(lists, keys, rng, n, wild):
    out = []
    for key in keys:
        out.append('')
        out.append(key.upper())
        out += ['  ' + l for l in draw(lists, key, rng, n, wild)]
    return out


def name_pools(lists, rng):
    """Given names are three d6-gated pools in the book; roll which one first."""
    given = [k for k in lists if re.match(r'People/Names/\d', k)]
    return [rng.choice(given), 'People/Names/Family Names']


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('mode', choices=['list', 'draw', 'location', 'npc', 'street', 'threats'])
    ap.add_argument('query', nargs='*', help='list name(s) for draw, section for location')
    ap.add_argument('-n', type=int, default=3, help='candidates per slot (default 3)')
    ap.add_argument('--wild', type=float, default=WILD_DEFAULT,
                    help=f'chance a slot invites an off-chart option (default {WILD_DEFAULT})')
    ap.add_argument('--seed', type=int, help='replay an earlier draw')
    ap.add_argument('--from', dest='start', type=Path, default=Path('.'),
                    help='adventure file or dir whose context stack holds the tables')
    ap.add_argument('--file', type=Path, help='use this tables file instead of resolving one')
    args = ap.parse_args()

    source = args.file or context_stack.resolve(args.start, 'draw-tables-flat')
    if source is None:
        sys.exit(f'No draw-tables-flat.md in the context stack above {args.start.resolve()}.\n'
                 'Run context_stack.py to see the stack, or pass --file.')

    lists = parse(source)
    if not lists:
        sys.exit(f'No lists found in {source}')

    if args.mode == 'list':
        section = None
        for key in lists:
            head = key.split('/')[0]
            if head != section:
                section, _ = head, print(f'\n{head}')
            print(f'  {key}  ({len(lists[key])})')
        return

    seed = args.seed if args.seed is not None else random.randrange(10000)
    rng = random.Random(seed)

    if args.mode == 'draw':
        if not args.query:
            sys.exit('draw needs at least one list name')
        keys = [resolve(list(lists), q) for q in args.query]
    elif args.mode == 'location':
        if not args.query:
            sys.exit('location needs a section, e.g. `location casino`')
        sections = dict.fromkeys(k.split('/')[0] for k in lists)
        head = resolve(list(sections), args.query[0], 'section')
        keys = [k for k in lists if k.startswith(head + '/')] + DRESSING
    elif args.mode == 'npc':
        keys = name_pools(lists, rng) + NPC
    elif args.mode == 'street':
        keys = [rng.choice(['Streets/Weather/Bluetime', 'Streets/Weather/Night'])] + STREET
    else:
        keys = THREATS

    print(f'Draw — seed {seed}  ({source})')
    print(PREAMBLE)
    print('\n'.join(render(lists, keys, rng, args.n, args.wild)))


if __name__ == '__main__':
    main()
