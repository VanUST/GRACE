# GRACE Context Master (CLI Tool)

**`grace-ctx`** is a command-line utility for generating high-fidelity LLM contexts using the **GRACE** (Graph-based Architectures) and **AAG** (Actor-Action-Goal) frameworks.

Designed to be installed once and run anywhere, it automates the retrieval of research, code skeletons, and documentation to create a single XML context file. This ensures LLMs remain hallucination-free and strictly aligned with your project requirements, whether you are building from scratch or refactoring legacy spaghetti code.

## 📦 Installation

This tool is designed to be installed as a global CLI command.

1. **Clone/Download** this repository to a stable location (e.g., `~/tools/grace-context-master`).
2. **Install** in editable mode:

```bash
cd ~/tools/grace-context-master
pip install -e .

```

3. **Verify:**
You can now run `grace-ctx` from *any* terminal window.

```bash
grace-ctx --help

```

---

## 🚀 Quick Start

### 1. Project Setup

Go to **any** project folder where you want to use LLM assistance. You do not need to copy the script. Just create these configuration files in your project root:

| File | Status | Description |
| --- | --- | --- |
| **`TASK.md`** | **Required** | The "Mission Statement". Describe what you want the LLM to do. |
| **`specs/MANUAL_RULES.md`** | *Optional* | "Axioms" or strict business rules the LLM must obey (overrides research). |
| **`SOURCES.txt`** | *Optional* | List of URLs or PDF paths for the **RESEARCH** phase. |

### 2. The Commands

The general syntax is:
`grace-ctx [MODE] [OPTIONS]`

#### Modes

* **`RESEARCH`**: Scrapes `SOURCES.txt` and `MANUAL_RULES.md` to create a knowledge base.
* **`ARCHITECT`**: Analyzes `specs/KNOWLEDGE.md` + your code structure to design architecture.
* **`DEVELOPER`**: Reads `specs/ARCHITECTURE.md` + strict contracts to generate code.

#### Options

* `--src [dirs...]`: Specify source folders (default: `src`).
* `--legacy`: trigger **Legacy Mode** (see below).

---

## 🛠 Usage Workflows

### A. The "Greenfield" Flow (New Features)

Use this for new projects or clean, AAG-compliant codebases.

1. **Define the Task:** Edit `TASK.md`.
2. **Research (Optional):**
```bash
grace-ctx RESEARCH

```


*Output:* `context_research.xml`. Upload to LLM -> Save result as `specs/KNOWLEDGE.md`.
3. **Design:**
```bash
grace-ctx ARCHITECT --src src

```


*Output:* `context_architect.xml`. Upload to LLM -> Save result as `specs/ARCHITECTURE.md`.
4. **Code:**
```bash
grace-ctx DEVELOPER --src src

```


*Output:* `context_developer.xml`. Upload to LLM -> LLM writes the code.

---

### B. The "Legacy" Flow (Refactoring)

Use this for existing projects that are **not** GRACE/AAG compliant.

**Key Differences:**

* **Full Context:** Reads full file contents (not just skeletons) so the Architect understands the implementation details.
* **Refactoring Prompts:** Injects specific instructions to "Audit," "Plan Migration," and "Wrap Legacy Logic."

**Example:**
Refactoring a messy `lib` folder and `scripts` folder.

1. **Audit & Plan:**
```bash
grace-ctx ARCHITECT --src lib scripts --legacy

```


*The LLM will produce a "Migration Strategy" in `specs/ARCHITECTURE.md`.*
2. **Refactor:**
```bash
grace-ctx DEVELOPER --src lib scripts --legacy

```


*The LLM will rewrite code to fit the new architecture while preserving original business logic.*

---

## 📂 Configuration Details

### `specs/MANUAL_RULES.md`

This file is your "God Mode". Anything written here is treated as an immutable fact by the LLM. Use it for:

* Proprietary formulas.
* Strict business constraints ("Users cannot delete invoices").
* Architecture decisions ("Must use PostgreSQL, not Mongo").

### `SOURCES.txt`

A simple list of line-separated sources.

* **URLs:** `https://api.example.com/v1/docs`
* **PDFs:** `/home/user/downloads/whitepaper.pdf` (Requires `docling` installed).

---

## 🔧 Troubleshooting

**"Command not found: grace-ctx"**

* Ensure you ran `pip install -e .` inside the tool's directory.
* Check that your Python `Scripts` or `bin` folder is in your system `PATH`.

**PDFs are ignored**

* The tool requires `docling` for PDF support. Run `pip install docling`.

**Context file is too large**

* If `context_developer.xml` exceeds the LLM's context window, run the command on specific subdirectories:
```bash
grace-ctx DEVELOPER --src src/auth src/utils

```