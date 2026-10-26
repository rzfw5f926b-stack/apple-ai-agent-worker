#!/bin/bash
# Send one prompt to Apple's cloud model through a shortcut; fall back to the
# on-device `fm` CLI if every shortcut fails (guardrail, usage limit, too long).
#
#   examples/delegate.sh "Summarize in one sentence: ..."
#   cat article.txt | examples/delegate.sh
#
# Env:
#   SHORTCUTS_CHAIN  shortcut names to try in order, separated by "|"
#                    (default: "Ask Apple Cloud|Ask Apple Cloud Pro")
#   NO_FM=1          do not fall back to the on-device model
#
# Exit 0 with the answer on stdout; non-zero if every backend failed.
# Which backend answered is printed to stderr as "[backend] name".
set -u

CHAIN="${SHORTCUTS_CHAIN:-Ask Apple Cloud|Ask Apple Cloud Pro}"
if [ $# -gt 0 ]; then prompt="$1"; else prompt="$(cat)"; fi
[ -n "$prompt" ] || { echo "empty prompt" >&2; exit 2; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
printf '%s' "$prompt" > "$tmp/in.txt"

IFS='|' read -r -a shortcuts <<< "$CHAIN"
for sc in "${shortcuts[@]}"; do
  rm -f "$tmp/out.txt"
  # The -o file name must end in .txt, otherwise nothing is written.
  # Success = exit 0 AND a non-empty output file.
  if perl -e 'alarm 300; exec @ARGV' shortcuts run "$sc" -i "$tmp/in.txt" -o "$tmp/out.txt" 2> "$tmp/err.txt" \
     && [ -s "$tmp/out.txt" ]; then
    echo "[backend] $sc" >&2
    cat "$tmp/out.txt"
    exit 0
  fi
  echo "[$sc failed] $(tr -d '\n' < "$tmp/err.txt")" >&2
done

[ "${NO_FM:-0}" = 1 ] && exit 1
# On-device fallback: 8192-token context, weak at arithmetic and dates.
if perl -e 'alarm 120; exec @ARGV' fm respond --no-stream < "$tmp/in.txt" > "$tmp/fm.txt" 2> "$tmp/err.txt" \
   && [ -s "$tmp/fm.txt" ]; then
  echo "[backend] fm" >&2
  sed $'s/\x1b\\[[0-9;]*m//g' "$tmp/fm.txt"
  exit 0
fi
echo "[fm failed] $(tr -d '\n' < "$tmp/err.txt")" >&2
exit 1
