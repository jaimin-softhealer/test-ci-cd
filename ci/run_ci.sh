#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="${CI_REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BEFORE_SHA="${1:-0000000000000000000000000000000000000000}"
AFTER_SHA="${2:?after SHA is required}"
AUTHOR_EMAIL="${3:-}"
ACTOR="${4:-}"
REPO_SLUG="${CI_REPO_SLUG:-jaimin-softhealer/test-ci-cd}"
BRANCH="${CI_BRANCH:-main}"
ODOO_IMAGE="${ODOO_CI_IMAGE:-test-ci-cd/odoo-ci:18.0-py3.11}"
ODOO_SRC="${ODOO_SRC:-/opt/odoo}"
DB_HOST="${CI_DB_HOST:-test-ci-cd-postgres}"
DB_PORT="${CI_DB_PORT:-5432}"
DB_USER="${POSTGRES_USER:-odoo}"
DB_PASSWORD="${POSTGRES_PASSWORD:-odoo}"
DB_PREFIX="${POSTGRES_DB:-odoo_test}"
DOCKER_NETWORK="${CI_DOCKER_NETWORK:-test-ci-cd-ci}"
LOG_DIR="${CI_LOG_DIR:-$REPO_DIR/logs}"
GITHUB_API="https://api.github.com"

mkdir -p "$LOG_DIR" "$REPO_DIR/review-output"
exec > >(tee -a "$LOG_DIR/${AFTER_SHA}.log") 2>&1

post_status() {
    local state="$1"
    local description="$2"
    [ -n "${GITHUB_TOKEN:-}" ] || return 0
    local payload
    payload="$(jq -n \
        --arg state "$state" \
        --arg target "${CI_STATUS_TARGET_URL:-https://github.com/$REPO_SLUG/commit/$AFTER_SHA}" \
        --arg description "$description" \
        --arg context "${CI_STATUS_CONTEXT:-odoo-local-webhook-ci}" \
        '{state: $state, target_url: $target, description: $description, context: $context}')"
    curl --fail-with-body --silent --show-error -X POST \
        -H 'Accept: application/vnd.github+json' \
        -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H 'X-GitHub-Api-Version: 2022-11-28' \
        "$GITHUB_API/repos/$REPO_SLUG/statuses/$AFTER_SHA" -d "$payload" >/dev/null
}

cleanup() {
    local exit_code=$?
    if [ "$exit_code" -eq 0 ]; then
        post_status success 'Odoo tests and standards review passed'
    else
        post_status failure 'Odoo CI failed; inspect the local CI log'
    fi
    rmdir "$LOG_DIR/ci.lock" 2>/dev/null || true
    exit "$exit_code"
}
trap cleanup EXIT

mkdir "$LOG_DIR/ci.lock" 2>/dev/null || { echo 'Another CI run is active'; exit 2; }
post_status pending 'Odoo tests are running on the local webhook runner'

git -C "$REPO_DIR" fetch --no-tags origin "$BRANCH"
git -C "$REPO_DIR" checkout --detach "$AFTER_SHA"

if [ "$BEFORE_SHA" = "0000000000000000000000000000000000000000" ]; then
    CHANGED_FILES="$(git -C "$REPO_DIR" ls-tree -r --name-only "$AFTER_SHA")"
else
    CHANGED_FILES="$(git -C "$REPO_DIR" diff --name-only "$BEFORE_SHA" "$AFTER_SHA")"
fi

CHANGED_FILES_JSON="$(printf '%s\n' "$CHANGED_FILES" | jq -R -s -c 'split("\n") | map(select(length > 0))')"
MODULES="$(
    while IFS= read -r file; do
        [ -n "$file" ] || continue
        dir="$(dirname "$file")"
        while [ "$dir" != "." ] && [ "$dir" != "/" ]; do
            if [ -f "$REPO_DIR/$dir/__manifest__.py" ]; then
                jq -n --arg name "$(basename "$dir")" --arg addons_path "$(dirname "$dir")" \
                    '{name: $name, addons_path: $addons_path}'
                break
            fi
            dir="$(dirname "$dir")"
        done
    done <<< "$CHANGED_FILES"
    ) | jq -s -c 'unique_by(.name, .addons_path)')"

echo "Commit: $AFTER_SHA"
echo "Changed files: $CHANGED_FILES_JSON"
echo "Changed modules: $MODULES"

python3 "$REPO_DIR/tools/odoo_standards_review.py" \
    --repo-root "$REPO_DIR" \
    --changed-files-json "$CHANGED_FILES_JSON" \
    --json-output "$REPO_DIR/review-output/odoo-review.json" \
    --markdown-output "$REPO_DIR/review-output/odoo-review.md"

if [ "$(jq 'length' "$REPO_DIR/review-output/odoo-review.json")" -gt 0 ]; then
    cat "$REPO_DIR/review-output/odoo-review.md"
    exit 1
fi

while IFS= read -r module_json; do
    module_name="$(jq -r '.name' <<< "$module_json")"
    addons_path="$(jq -r '.addons_path' <<< "$module_json")"
    db_name="${DB_PREFIX}_${module_name}"
    docker run --rm --platform linux/amd64 \
        --network "$DOCKER_NETWORK" \
        -v "$REPO_DIR:/workspace" -w /workspace "$ODOO_IMAGE" \
        python "$ODOO_SRC/odoo-bin" -d "$db_name" -i "$module_name" \
        --test-enable --test-tags="/$module_name" --stop-after-init \
        --without-demo=True --addons-path="$ODOO_SRC/addons,/workspace/$addons_path" \
        --db_host="$DB_HOST" --db_port="$DB_PORT" \
        --db_user="$DB_USER" --db_password="$DB_PASSWORD"
done < <(jq -c '.[]' <<< "$MODULES")
