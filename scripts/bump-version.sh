#!/usr/bin/env bash
# Bump die Version und legt einen CHANGELOG-Eintrag an.
# Usage:
#   ./scripts/bump-version.sh patch     # 0.2.1 → 0.2.2
#   ./scripts/bump-version.sh minor     # 0.2.1 → 0.3.0
#   ./scripts/bump-version.sh major     # 0.2.1 → 1.0.0
#   ./scripts/bump-version.sh 0.5.7     # explizit
set -euo pipefail

cd "$(dirname "$0")/.."

MANIFEST="custom_components/haushaltsdoku/manifest.json"
CHANGELOG="CHANGELOG.md"

if [ $# -lt 1 ]; then
  echo "Usage: $0 {patch|minor|major|<x.y.z>}" >&2
  exit 1
fi

CURRENT=$(python3 -c "import json; print(json.load(open('${MANIFEST}'))['version'])")
echo "Aktuelle Version: $CURRENT"

case "$1" in
  patch|minor|major)
    NEW=$(python3 - "$CURRENT" "$1" <<'PY'
import sys
cur, kind = sys.argv[1], sys.argv[2]
parts = [int(p) for p in cur.split(".")]
while len(parts) < 3:
    parts.append(0)
major, minor, patch = parts[:3]
if kind == "patch":
    patch += 1
elif kind == "minor":
    minor += 1
    patch = 0
elif kind == "major":
    major += 1
    minor = 0
    patch = 0
print(f"{major}.{minor}.{patch}")
PY
)
    ;;
  *)
    if [[ ! "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.]+)?$ ]]; then
      echo "✗ Ungültige Version: $1" >&2
      exit 1
    fi
    NEW="$1"
    ;;
esac

echo "Neue Version:     $NEW"
read -p "Fortfahren? [y/N] " -n 1 -r
echo
[[ $REPLY =~ ^[Yy]$ ]] || { echo "Abgebrochen."; exit 0; }

# manifest.json updaten
python3 - "$MANIFEST" "$NEW" <<'PY'
import json, sys
path, new = sys.argv[1], sys.argv[2]
data = json.load(open(path))
data["version"] = new
with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"✓ {path} → {new}")
PY

# CHANGELOG-Eintrag vorne einfügen (nach dem Header)
TODAY=$(date +%Y-%m-%d)
python3 - "$CHANGELOG" "$NEW" "$TODAY" <<'PY'
import sys, re
path, ver, today = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path).read()
new_section = f"""## [{ver}] — {today}

### Hinzugefügt
- _todo_

### Geändert
- _todo_

### Entfernt
- _todo_

"""
# Einfügen vor erster "## ["
pattern = re.compile(r"^## \[", re.M)
m = pattern.search(text)
if m:
    out = text[:m.start()] + new_section + text[m.start():]
else:
    out = text + "\n" + new_section
open(path, "w").write(out)
print(f"✓ {path} um Sektion [{ver}] erweitert")
PY

echo
echo "→ Trage deine Änderungen unter '## [$NEW]' im CHANGELOG nach."
echo "→ Commit + Tag:"
echo "    git add ${MANIFEST} ${CHANGELOG}"
echo "    git commit -m \"chore: release v${NEW}\""
echo "    git tag v${NEW}"
echo "    git push && git push --tags"
