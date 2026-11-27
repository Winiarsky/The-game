#!/usr/bin/env python3
"""Report the context an adventure inherits from the directories above it.

An adventure is not self-contained. The directories enclosing it hold the canon
it leans on — campaign continuity one level up, setting and system reference
above that — and how many layers there are varies by project (system/campaign/
adventure, sometimes with a session layer below). Every rpg-* skill needs the
same answer here, so the walk lives in one place instead of being improvised
from `ls` each session.

Two resolution rules, because the two kinds of inherited file want opposite
treatment:

  Accumulate   Prose reference — lore, rules, campaign notes, PC sheets. Every
               layer counts. Read broad to narrow; where layers disagree the
               narrower one wins.
  Nearest-wins  The named ASSETS below. Exactly one answer is wanted, and it is
               the copy closest to the adventure, so a campaign or a single
               adventure can override its system.

Usage:
  ./context_stack.py                        # walk up from the current directory
  ./context_stack.py path/to/adventure.md   # or from an adventure file or dir
  ./context_stack.py -a <dir> --asset art_style     # one resolved path, or nothing
"""
import argparse
import re
import sys
from pathlib import Path

# Named assets, resolved nearest-wins. Patterns are matched against the
# lowercased filename with '_' folded to '-', so art_style.md and art-style.md
# are the same asset. Legacy alternates keep a project working before it renames.
ASSETS = {
    'art_style': [r'art-?style\.md'],
    'draw-tables': [r'draw-?tables\.md', r'.*rolodex(?!.*flat).*\.md'],
    'draw-tables-flat': [r'draw-?tables-?flat\.md', r'.*rolodex.*flat.*\.md'],
}


def find_root(start, explicit=None):
    """Outermost directory to walk to: the repo, else $HOME, else /."""
    if explicit:
        return Path(explicit).resolve()
    for d in [start, *start.parents]:
        if (d / '.git').exists():
            return d
    home = Path.home().resolve()
    return home if home in start.parents or home == start else Path(start.anchor)


def layers(start, root):
    """Adventure dir first, then each ancestor out to root inclusive."""
    out, d = [], start
    while True:
        out.append(d)
        if d == root or d.parent == d:
            break
        d = d.parent
    return out


def key(name):
    return name.lower().replace('_', '-')


def classify(d):
    """-> (assets {name: Path}, other .md files) for one directory."""
    assets, other = {}, []
    for f in sorted(p for p in d.glob('*.md') if p.is_file()):
        for asset, patterns in ASSETS.items():
            if any(re.fullmatch(p, key(f.name)) for p in patterns):
                assets.setdefault(asset, f)
                break
        else:
            other.append(f)
    return assets, other


def stack(start, root=None):
    """-> (root, [(dir, assets, other) innermost-first], resolved {asset: Path}).

    `resolved` is nearest-wins: the innermost layer that carries an asset owns it.
    """
    start = Path(start).resolve()
    if start.is_file():
        start = start.parent
    root = find_root(start, root)
    if root not in [start, *start.parents]:
        root = start                      # a path outside the root: don't walk past it
    found, resolved = [], {}
    for d in layers(start, root):
        assets, other = classify(d)
        found.append((d, assets, other))
        for name, path in assets.items():
            resolved.setdefault(name, path)
    return root, found, resolved


def resolve(start, asset, root=None):
    """The nearest copy of one named asset, or None."""
    return stack(start, root)[2].get(asset)


def lines(path):
    try:
        return sum(1 for _ in path.open(errors='replace'))
    except OSError:
        return 0


def report(start, root=None):
    root, found, resolved = stack(start, root)
    adventure = found[0][0]
    rel = lambda p: str(p.relative_to(root)) if root in p.parents else p.name
    out = [f'Context stack — {adventure}', f'root: {root}', '',
           'Read broad → narrow. Where two layers disagree, the narrower wins.',
           'Named assets resolve nearest-wins (marked *).', '']

    for i, (d, assets, other) in reversed(list(enumerate(found))):
        label = {0: 'adventure'}.get(i, '')
        if d == root:
            label = 'project root'
        elif i == len(found) - 2 and len(found) > 2:
            label = 'outermost content layer — usually the System'
        name = '.' if d == root else rel(d) + '/'
        out.append(f'L{i}  {name}' + (f'   ({label})' if label else ''))
        for asset in ASSETS:
            if asset in assets:
                mark = '*' if resolved.get(asset) == assets[asset] else ' '
                out.append(f'      {mark} {asset}: {assets[asset].name} ({lines(assets[asset])})')
        if other:
            out.append('        ' + '  '.join(f'{f.name} ({lines(f)})' for f in other))

    out += ['', 'Resolved assets:']
    for asset in ASSETS:
        hit = resolved.get(asset)
        out.append(f'  {asset:17} {rel(hit) if hit else "— none in the stack"}')
    if 'draw-tables-flat' in resolved:
        out += ['', 'Draw from the tables with real RNG rather than picking yourself:',
                f'  {Path(__file__).parent / "rolodex.py"} --from {adventure} npc']
    out += ['', '(N) = line count. Grep a long reference file for the entities your',
            'adventure names; do not read it top-down.']
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('path', nargs='?', default='.', help='adventure file or directory')
    ap.add_argument('-a', dest='path_alt', help='alias for path, matching cast-npc.py')
    ap.add_argument('--root', help='stop the walk here instead of at the repo root')
    ap.add_argument('--asset', choices=list(ASSETS),
                    help='print just this resolved path; exit 1 if the stack has none')
    args = ap.parse_args()
    start = Path(args.path_alt or args.path)
    if not start.exists():
        sys.exit(f'No such path: {start}')
    if args.asset:
        hit = resolve(start, args.asset, args.root)
        if not hit:
            sys.exit(1)
        print(hit)
        return
    print(report(start, args.root))


if __name__ == '__main__':
    main()
