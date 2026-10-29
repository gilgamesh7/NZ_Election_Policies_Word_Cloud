#!/usr/bin/env bash
# run_notebook.sh - Execute the NZ Political Party Policies Word Cloud Jupyter Notebook

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"
NOTEBOOK_FILE="${SCRIPT_DIR}/notebooks/nz_policy_wordcloud.ipynb"

if [ ! -f "${VENV_PYTHON}" ]; then
    echo "Error: Virtual environment not found at .venv."
    echo "Please create the environment first:"
    echo "  uv venv .venv --python 3.14"
    echo "  uv pip install --python .venv/bin/python -e '.[dev]'"
    exit 1
fi

if [ ! -f "${NOTEBOOK_FILE}" ]; then
    echo "Error: Notebook not found at ${NOTEBOOK_FILE}."
    exit 1
fi

echo "======================================================================"
echo "Starting NZ Policy Word Cloud Jupyter Notebook..."
echo "Project Directory: ${SCRIPT_DIR}"
echo "Notebook: ${NOTEBOOK_FILE}"
echo "======================================================================"

# Check for help flag
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: ./run_notebook.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  (no args)           Launch Jupyter Lab / Notebook in your browser"
    echo "  --execute           Run the notebook headlessly end-to-end and save outputs"
    echo "  --headless          Alias for --execute"
    echo "  --help, -h          Show this help message"
    exit 0
fi

# If an argument --execute or --headless is passed, execute the notebook non-interactively
if [[ "${1:-}" == "--execute" || "${1:-}" == "--headless" ]]; then
    echo "Executing notebook in headless/batch mode..."
    "${SCRIPT_DIR}/.venv/bin/jupyter" nbconvert \
        --to notebook \
        --execute "${NOTEBOOK_FILE}" \
        --output "${SCRIPT_DIR}/notebooks/nz_policy_wordcloud_executed.ipynb"
    echo "Headless execution finished. Output saved to notebooks/nz_policy_wordcloud_executed.ipynb"
    exit 0
fi

# Default: Start Jupyter Lab / Notebook server opening the notebook
if command -v "${SCRIPT_DIR}/.venv/bin/jupyter-lab" >/dev/null 2>&1; then
    "${SCRIPT_DIR}/.venv/bin/jupyter" lab "${NOTEBOOK_FILE}"
else
    "${SCRIPT_DIR}/.venv/bin/jupyter" notebook "${NOTEBOOK_FILE}"
fi
