#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PY="${PYTHON:-python3}"

# Tell Python what the wrapper path is so it can exclude it from counts.
export PROJMETRICS_EXCLUDE_SELF="${0:A}"

exec "$PY" "$SCRIPT_DIR/projmetrics.py" "$@"

