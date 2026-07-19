#!/bin/sh
set -eu

escape_js() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

cat > /usr/share/nginx/html/runtime-config.js <<EOF
window.__AGENTMESH_CONFIG__ = {
  VITE_API_URL: "$(escape_js "${AGENTMESH_API_URL:-}")",
  VITE_API_TIMEOUT_MS: "$(escape_js "${AGENTMESH_API_TIMEOUT_MS:-90000}")",
  VITE_BLOCK_EXPLORER_TX_URL: "$(escape_js "${BLOCK_EXPLORER_TX_URL:-}")",
  VITE_GOOGLE_OAUTH_ENABLED: "$(escape_js "${GOOGLE_OAUTH_ENABLED:-false}")",
  VITE_SUPABASE_URL: "$(escape_js "${SUPABASE_URL:-}")",
  VITE_SUPABASE_PUBLISHABLE_KEY: "$(escape_js "${SUPABASE_PUBLISHABLE_KEY:-}")",
  VITE_TURNSTILE_SITE_KEY: "$(escape_js "${TURNSTILE_SITE_KEY:-}")"
}
EOF
