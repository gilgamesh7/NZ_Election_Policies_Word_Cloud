# NZ_Election_Policies_Word_Cloud
Collect publicly accessible policy text from NZ political party websites supplied by the user, analyse the language used, and generate a word cloud for each party.  Word clouds and term rankings describe patterns in the collected text, they do not establish a party's intent, the quality of its policies, or the likely effects of those policies.

> [!IMPORTANT]
> **System Compatibility:** This project is designed and tested exclusively for **Apple Silicon (M1 and above)** running **macOS Tahoe** with **Python 3.14+**.

## Installation & Environment Setup

### 1. Clone the repository
```bash
git clone https://github.com/vrbabu/NZ_Election_Policies_Word_Cloud.git
cd NZ_Election_Policies_Word_Cloud
```

### 2. Set up virtual environment and install dependencies
This project uses [`uv`](https://github.com/astral-sh/uv) for fast and deterministic package management:
```bash
# Create a virtual environment using Python 3.14
uv venv .venv --python 3.14

# Install the package in editable mode along with development and notebook dependencies
uv pip install --python .venv/bin/python -e ".[dev]"
```

### 3. Run automated tests
Verify the installation by running the test suite:
```bash
.venv/bin/pytest
```

### 4. Running the Jupyter Notebook
You can launch the Jupyter Notebook directly using the provided shell script in the project root:
```bash
./run_notebook.sh
```
Or run the complete pipeline non-interactively / headlessly:
```bash
./run_notebook.sh --execute
```
Alternatively, launch standard Jupyter Lab:
```bash
# Activate the virtual environment
source .venv/bin/activate

# Launch Jupyter Lab or Notebook
jupyter lab
# Or: jupyter notebook
```
Open `notebooks/nz_policy_wordcloud.ipynb` from the Jupyter interface.

## Known Scope and Limitations

1. **HTML-Only Collection (Version 1.0):**
   - The crawler only retrieves and processes HTML pages (`text/html` or `application/xhtml+xml`).
   - Binary files, downloadable PDFs, presentations, audio/video streams, and archives linked on policy pages are excluded by design to prevent binary parsing corruption and resource exhaustion.
2. **JavaScript-Rendered SPAs:**
   - As per the safety and security specification, JavaScript is not executed by the crawler. Text dynamically generated entirely client-side via JavaScript Single-Page Applications is not collected.
3. **Link Depth Restriction:**
   - Link discovery strictly follows direct first-level links (`depth = 1`) found on starting pages within the configured hostnames. Links deeper than level 1 are not followed.
4. **Analytical Neutrality:**
   - Term frequency describes repetition in collected text.
   - TF-IDF highlights relative distinctiveness specifically among the political parties included in a given run.
   - Outputs describe language patterns only and do not constitute an evaluation, ranking, or endorsement of any political party or policy quality.


# agy CLI
- Install if not already done : 
    - curl -fsSL https://antigravity.google/cli/install.sh | bash
    - echo 'export PATH="/Users/vrbabu/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
- agy --version NOTE : Antigravity CLI updates itself in place whenever a newer release is available. But you can trigger that manually at any time with agy update.
- To authenticate : agy
- To get available models : agy models
- Set model from list : /model
- agy --effort high
- Non-interactive / Print mode : agy -p "Explain the Game of Life rules" --model gemini-3.8-flash-high
- Check your remaining allowance : /usage or /quota
- Change model : /model (model name)

