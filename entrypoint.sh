#!/bin/bash
set -e

# Framework entrypoint — minimal, infrastructure-agnostic.
#
# Wrapper-specific concerns (private Git remotes, VLAN routing, iptables
# defense-in-depth, auto-pull, background loops) live in the consumer's
# wrapper entrypoint, which delegates here via `exec`. The framework
# itself only knows how to:
#   1. Resolve its own paths
#   2. Make the cache writable for the coach user
#   3. Start Claude Code inside a tmux session
#
# Environment expectations:
#   COACH_HOME      — absolute path to the athlete wrapper repo
#                     (defaults to one level above this script's directory,
#                      i.e. the wrapper that contains framework/ as subdir)
#   FRAMEWORK_HOME  — absolute path to the framework subdir (defaults to
#                     this script's parent directory)

# Resolve framework dir = directory containing this script
FRAMEWORK_HOME="${FRAMEWORK_HOME:-$(cd "$(dirname "$0")" && pwd)}"
# Resolve wrapper root = parent of framework dir (unless explicitly set)
COACH_HOME="${COACH_HOME:-$(dirname "$FRAMEWORK_HOME")}"

# Ensure cache is writable by coach user (may be root-owned after volume mounts)
chown -R coach:coach "$COACH_HOME/cache" 2>/dev/null || true

# Start tmux session as non-root coach user with Claude Code
su coach -c "tmux new-session -d -s coach -c $COACH_HOME"
su coach -c "tmux send-keys -t coach 'while true; do claude --channels \"plugin:telegram@claude-plugins-official\" --dangerously-skip-permissions; echo \"[coach] Claude exited — restarting in 3s...\"; sleep 3; done' Enter"

# Keep container alive (user attaches via: docker exec -it --user coach <container-name> tmux attach -t coach)
tail -f /dev/null
