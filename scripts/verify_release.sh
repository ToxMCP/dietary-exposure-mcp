#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-${ROOT}/artifacts/releases/v0.1.0-rc1}"
OUT="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "${OUT}")"
ARTIFACT_ROOT="${ROOT}/artifacts/releases"
case "${OUT}" in
  "${ARTIFACT_ROOT}"/*) ;;
  *)
    printf 'Release output must be inside %s\n' "${ARTIFACT_ROOT}" >&2
    exit 2
    ;;
esac
TMP="$(mktemp -d "${TMPDIR:-/tmp}/dietary-mcp-release.XXXXXX")"
trap 'rm -rf "${TMP}"' EXIT

cd "${ROOT}"

# Python 3.12.13 skips .pth files carrying macOS' hidden filesystem flag.
# Keeping src explicit makes editable-install tests deterministic; the clean
# wheel smoke test below independently verifies the built distribution.
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
# Keep release bytes stable across metadata-only and repository-hygiene commits.
# A package-definition change deliberately advances the epoch.
VERSION_SOURCE_DATE_EPOCH="$(git log -1 --format=%at -- pyproject.toml)"
if [[ -z "${VERSION_SOURCE_DATE_EPOCH}" ]]; then
  printf 'Could not derive SOURCE_DATE_EPOCH from pyproject.toml history.\n' >&2
  exit 2
fi
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-${VERSION_SOURCE_DATE_EPOCH}}"

uv sync --frozen --all-extras --group release
uv run ruff check src/dietary_mcp tests scripts
uv run python scripts/vendor_verify.py
uv run python scripts/public_release_audit.py
uv run python scripts/verify_openfoodtox3_migration.py
uv run python scripts/scientific_invariants_gate.py --json
uv run pytest -W error

uv run dietary-mcp-generate-artifacts
uv run dietary-mcp-validate

rm -rf "${OUT}"
mkdir -p "${OUT}/dist"
uv build --quiet --out-dir "${OUT}/dist"
uv run python scripts/normalize_sdist.py --epoch "${SOURCE_DATE_EPOCH}" "${OUT}"/dist/*.tar.gz

mkdir -p "${TMP}/repro-dist"
uv build --quiet --out-dir "${TMP}/repro-dist"
uv run python scripts/normalize_sdist.py --epoch "${SOURCE_DATE_EPOCH}" "${TMP}"/repro-dist/*.tar.gz
for artifact in "${OUT}"/dist/*; do
  cmp --silent "${artifact}" "${TMP}/repro-dist/$(basename "${artifact}")" || {
    printf 'Non-reproducible package artifact: %s\n' "$(basename "${artifact}")" >&2
    exit 1
  }
done

uv run python scripts/verify_distribution_public_files.py "${OUT}/dist"

DIETARY_MCP_RELEASE_DIST_DIR="${OUT}/dist" uv run python -m dietary_mcp.release_artifacts
git diff --exit-code -- docs/contracts docs/releases schemas/examples defaults validation config

uv run bandit -r src -x tests --severity-level medium
uv export --quiet --frozen --no-dev --no-emit-project --format requirements-txt --output-file "${TMP}/runtime-requirements.txt"
uv run pip-audit --requirement "${TMP}/runtime-requirements.txt" --desc
gitleaks detect --source . --config .gitleaks.toml --redact --no-banner

uv run twine check "${OUT}"/dist/*

uv venv --python 3.12 "${TMP}/smoke-venv"
WHEEL="$(find "${OUT}/dist" -maxdepth 1 -name '*.whl' -print -quit)"
uv pip install --python "${TMP}/smoke-venv/bin/python" "${WHEEL}"
env -u PYTHONPATH "${TMP}/smoke-venv/bin/python" -c \
  'import dietary_mcp, pathlib, sys; path = pathlib.Path(dietary_mcp.__file__).resolve(); prefix = pathlib.Path(sys.prefix).resolve(); assert path.is_relative_to(prefix), f"import escaped clean venv: {path}"; print(path)'
env -u PYTHONPATH "${TMP}/smoke-venv/bin/dietary-mcp" --help >/dev/null

env -u PYTHONPATH uv run cyclonedx-py environment \
  --pyproject pyproject.toml \
  --mc-type application \
  --output-reproducible \
  --output-format JSON \
  --output-file "${OUT}/python-sbom.cdx.json" \
  "${TMP}/smoke-venv/bin/python"

{
  (
    cd "${OUT}/dist"
    shasum -a 256 *
  )
  (
    cd "${OUT}"
    shasum -a 256 python-sbom.cdx.json
  )
} > "${OUT}/SHA256SUMS"

printf 'Dietary MCP release verification passed.\nArtifacts: %s\n' "${OUT}"
