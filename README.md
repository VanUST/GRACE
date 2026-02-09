# GRACE Context Master (CLI Tool)

**`grace-ctx`** is a command-line utility for generating high-fidelity LLM contexts using the **GRACE** (Graph-based Architectures) and **AAG** (Actor-Action-Goal) frameworks.

It aggregates your research, code, and documentation into a single, structured XML file tailored for LLMs. This keeps your project root clean by centralizing all generated contexts into a hidden `.grace/` folder.

## 📦 Installation

1. **Clone/Download** this repository to a stable location (e.g., `~/tools/grace-context-master`).
2. **Install** in editable mode:

```bash
cd ~/tools/grace-context-master
pip install -e .

```

3. **Verify:**
Run `grace-ctx --help` from any terminal.

---

## 🚀 Quick Start

### 1. Project Setup

Navigate to **any** project folder. You do not need to copy the script. Just create the configuration files:

| File | Status | Description |
| --- | --- | --- |
| **`TASK.md`** | **Required** | The "Mission Statement". E.g., *"Refactor the auth module."* |
| **`specs/MANUAL_RULES.md`** | *Optional* | Your strict logic/axioms (overrides research). |
| **`SOURCES.txt`** | *Optional* | List of URLs or PDF paths for research. |

### 2. Run the Tool

Run the command corresponding to your current development stage. **All outputs are saved in the `.grace/` folder.**

```bash
# 1. Research Phase (if needed)
grace-ctx RESEARCH
# Output: .grace/context_research.xml

# 2. Architect Phase
grace-ctx ARCHITECT --src src
# Output: .grace/context_architect.xml

# 3. Developer Phase
grace-ctx DEVELOPER --src src
# Output: .grace/context_developer.xml

```

---

## 🛠 Usage Workflows

### A. The "Greenfield" Flow (New Features)

Use this for new projects or clean codebases.

1. **Research:** Run `grace-ctx RESEARCH`. Upload `.grace/context_research.xml` to LLM. Ask it to generate `specs/KNOWLEDGE.md`.
2. **Architect:** Run `grace-ctx ARCHITECT`. Upload `.grace/context_architect.xml`. Ask it to generate `specs/ARCHITECTURE.md`.
3. **Develop:** Run `grace-ctx DEVELOPER`. Upload `.grace/context_developer.xml`. The LLM writes the code.

### B. The "Legacy" Flow (Refactoring)

Use this for existing "spaghetti code" projects.

**Key Difference:** Uses the `--legacy` flag to inject refactoring instructions and read full file contents during the architecture phase.

```bash
# Example: Refactoring a messy 'lib' folder
grace-ctx ARCHITECT --src lib --legacy

```

* **Output:** `.grace/context_architect.xml`
* **LLM Instruction:** "Audit this code and create a Migration Strategy in `specs/ARCHITECTURE.md`."

---

## ⚙️ Configuration & Best Practices

### The `.grace/` Folder

The tool automatically creates a `.grace/` directory in your project root to store the heavy XML context files.

**Recommendation:** Add this to your `.gitignore` to keep your repo clean.

```text
# .gitignore
.grace/

```

### Advanced Options

**Multi-Folder Parsing:**
If your source code is split (e.g., backend/frontend), list them all:

```bash
grace-ctx DEVELOPER --src backend frontend shared

```

**Manual Rules (The "Axiom" Layer):**
Create `specs/MANUAL_RULES.md` to force specific constraints. Content here is treated as "Immutable Truth" by the LLM.

* *Example:* "Tax calculations must always round UP to the nearest integer."

### PDF Support

To parse PDFs listed in `SOURCES.txt`, you must install the optional dependency:

```bash
pip install docling

```

---

## 📂 Example Project Structure

After running the tool, your project will look like this:

```text
my-project/
├── .grace/                 # [Generated] Hidden folder for contexts
│   ├── context_research.xml
│   └── context_developer.xml
├── src/                    # Your code
├── specs/
│   ├── MANUAL_RULES.md     # Your rules
│   └── ARCHITECTURE.md     # LLM generated plan
├── TASK.md                 # Your prompt
└── .gitignore

```