#!/usr/bin/env bash
# Rebuild static/vendor/lucide-subset.min.js from the icon list below.
# Usage: ./scripts/build-lucide-subset.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/static/vendor/lucide-subset.min.js"
WORKDIR="$(mktemp -d)"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

ICONS=(
  alert-circle apple arrow-left baby banknote bell bookmark bookmark-check bookmark-x
  briefcase car check check-circle check-circle-2 chevron-down chevron-left chevron-right
  clock cog dumbbell external-link eye eye-off file-pen-line flag flower-2 folder-heart
  hammer handshake home image image-plus inbox key-round layout-dashboard layout-grid
  lock-keyhole log-in log-out mail mail-check map-pin menu message-circle message-square-warning
  messages-square paw-print pencil phone plus reply save search send settings share-2
  shield-alert shield-check shopping-bag smartphone sofa sparkles star store tag trash-2
  user user-plus wifi-off wrench x zap zoom-in zoom-out shirt
)

cd "$WORKDIR"
npm init -y >/dev/null
npm install lucide@0.469.0 esbuild --silent

python3 - "$WORKDIR" <<'PY'
import sys
from pathlib import Path
icons = """
alert-circle apple arrow-left baby banknote bell bookmark bookmark-check bookmark-x
briefcase car check check-circle check-circle-2 chevron-down chevron-left chevron-right
clock cog dumbbell external-link eye eye-off file-pen-line flag flower-2 folder-heart
hammer handshake home image image-plus inbox key-round layout-dashboard layout-grid
lock-keyhole log-in log-out mail mail-check map-pin menu message-circle message-square-warning
messages-square paw-print pencil phone plus reply save search send settings share-2
shield-alert shield-check shopping-bag smartphone sofa sparkles star store tag trash-2
user user-plus wifi-off wrench x zap zoom-in zoom-out shirt
""".split()
def pascal(name):
    return "".join(p.capitalize() for p in name.split("-"))
names = sorted(set(icons))
imports = ",\n  ".join(pascal(n) for n in names)
obj = ",\n  ".join(pascal(n) for n in names)
Path(sys.argv[1], "entry.js").write_text(
    f"""import {{ createIcons,
  {imports}
}} from 'lucide';

const icons = {{
  {obj}
}};

function createIconsBound(opts = {{}}) {{
  return createIcons({{ icons, ...opts }});
}}

window.lucide = {{ createIcons: createIconsBound, icons }};
"""
)
print(f"bundling {len(names)} icons")
PY

npx esbuild entry.js --bundle --minify --format=iife --outfile="$OUT"
gzip -9 -k -f "$OUT"
wc -c "$OUT" "$OUT.gz"
