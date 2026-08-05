#!/usr/bin/env bash
# Point git at the versioned hooks in .githooks/ (git hooks are not cloned).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
echo "core.hooksPath -> .githooks (pre-push runs pytest + the gate ladder)"
