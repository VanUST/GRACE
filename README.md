# GRACE Context Generator (`grace-ctx`)

**`grace-ctx`** is a CLI utility that generates high-fidelity, token-optimized contexts for Large Language Models (LLMs). It automates the "Context-Driven Development" workflow by aggregating your code, research, and documentation into structured XML packets that LLMs can digest easily.

It keeps your project root clean by centralizing all context and specification files into a hidden `.grace/` directory.

## 📦 Installation

1. **Clone** this repository to a stable location (e.g., `~/tools/grace-context`).
2. **Install** in editable mode:

```bash
cd ~/tools/grace-context
pip install -e .

```

3. **Verify:**
Run `grace-ctx --help` from any terminal.

### Optional Dependencies

To enable PDF parsing for research mode:

```bash
pip install docling

```

---

## 🚀 Quick Start

Navigate to your project folder. You do not need to copy the script.

**1. The "Mission" Flag**
Instead of editing a text file for every task, pass your goal directly via the `-m` (or `--mission`) flag.

**2. Generate Context**
Run the command corresponding to your current stage of development.

```bash
# Example: Fixing a bug
grace-ctx DEVELOPER -m "Fix the race condition in the user login flow." --src src

```

**3. Feed the LLM**
Upload the generated file (e.g., `.grace/context_developer.xml`) to your LLM (Claude, GPT-4, etc.).

---

## 🛠 Usage Workflows

### 1. The "Architect" Flow (New Features)

Use this when adding new modules to an existing codebase.

1. **Run:**
```bash
grace-ctx ARCHITECT -m "Design a plugin system for payment gateways." --src src

```


* *What it does:* Scans your code structure (skeletons only) to save tokens, and asks the LLM to design the new feature.


2. **Upload:** `.grace/context_architect.xml`
3. **LLM Output:** Ask the LLM to write the design to `.grace/ARCHITECTURE.md`.

### 2. The "Developer" Flow (Implementation)

Use this to write code based on an architecture or to fix bugs.

1. **Run:**
```bash
grace-ctx DEVELOPER -m "Implement the Stripe payment adapter based on the architecture." --src src

```


* *What it does:* Bundles the architecture docs + raw source code + your specific mission.


2. **Upload:** `.grace/context_developer.xml`
3. **LLM Output:** The LLM produces the actual code.

### 3. The "Refactor" Flow (Legacy Overhaul)

Use this when you want to redesign a messy system from scratch.

1. **Run:**
```bash
grace-ctx REFACTOR -m "Rewrite the authentication logic to be stateless." --src src/legacy_auth

```


* *What it does:* Reads **raw code** (deep logic analysis) instead of skeletons, and instructs the LLM to ignore current patterns and design a *new* ideal state.



### 4. The "Research" Flow (Knowledge Gathering)

Use this before writing code if the domain is complex (e.g., Physics simulations, Legal tech).

1. **Setup:** Create a `SOURCES.txt` file with URLs or PDF paths.
2. **Run:**
```bash
grace-ctx RESEARCH -m "Research best practices for lattice boltzmann methods."

```


3. **Upload:** `.grace/context_research.xml`
4. **LLM Output:** Ask LLM to save findings to `.grace/KNOWLEDGE.md`.

---

## 📂 Project Structure

After running the tool, your project will look like this. **Note that your root directory remains clean.**

```text
my-project/
├── .grace/                 # [Hidden] The Brain of your project
│   ├── context_developer.xml  # Upload this to LLM
│   ├── ARCHITECTURE.md     # (Optional) LLM-generated plan
│   ├── KNOWLEDGE.md        # (Optional) Research notes
│   └── MANUAL_RULES.md     # (Optional) User-defined axioms
├── src/                    # Your actual code
├── SOURCES.txt             # (Optional) List of research URLs
└── .gitignore

```

## ⚙️ Configuration Files

You can add these optional files to control the context generation:

| File | Location | Description |
| --- | --- | --- |
| **`MANUAL_RULES.md`** | `.grace/` | **The Axioms.** Rules here override everything else. (e.g., "Always use snake_case", "Never use libraries X, Y"). |
| **`SOURCES.txt`** | Root | A list of URLs or local file paths (PDFs supported) for the **RESEARCH** mode to scrape. |

## 🛡️ .gitignore

It is highly recommended to ignore the generated context folder to prevent bloating your git history.

```text
# .gitignore
.grace/

```