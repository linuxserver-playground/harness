#!/usr/bin/env bash
# SessionStart hook: tell the agent who it is working for before the first request. Whatever this prints is
# added to the session's context. It never fails the session: a broken check prints how to fix it.
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0
if ! ./harness whoami --brief 2>&1; then
  echo "harness: could not work out your role. Run ./harness doctor and ./harness whoami --refresh, and treat this session as the contributor path until then."
fi
if [[ ! -d repos/workspace ]]; then
  echo "No repos cloned yet: suggest ./harness core (about a minute) before reading code."
else
  stamp=$(git -C repos/workspace log -1 --format=%cr 2>/dev/null || echo "unknown")
  echo "repos/ is cloned (workspace last commit $stamp locally); ./harness sync brings every clone up to date."
fi
exit 0
