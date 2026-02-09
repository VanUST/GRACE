# GRACE Context Generator (`grace-ctx`)

**`grace-ctx`** is a CLI utility that automates "Context-Driven Development" for LLMs. It implements the **GRACE Framework** (Graph-based Architectures) to generate high-fidelity, token-optimized context packets.

Unlike standard context dumpers, `grace-ctx` structures information to leverage the specific SFT (Supervised Fine-Tuning) strengths of modern LLMs, treating code generation not as "writing" but as **"translation" from strict contracts to code.**

## 🧠 Core Philosophy

This tool is built on three key insights:

1. **Code is Translation:** LLMs are trained on massive amounts of "Instruction -> Code" pairs. They work best when "compiling" a strict logical contract into syntax, rather than "inventing" logic on the fly.
2. **The AAG Pattern:** We force the LLM to think in **Actor -> Action -> Goal** pseudo-code. This acts as a compressed "intermediate language" that bridges high-level intent and low-level syntax.
3. **Graph-First Architecture:** Before writing a single line of code, the system models the software as a dependency graph, preventing "spaghetti code" and context drift.

---

## 📦 Installation

1. **Clone** this repository:
```bash
git clone https://github.com/your-repo/grace-context.git
cd grace-context

```


2. **Install** (Editable mode recommended):
```bash
pip install -e .

```


3. **Optional:** Install PDF support for research mode:
```bash
pip install docling

```



---

## 🚀 Usage

You do not need to create configuration files for every task. Just run the tool from your project root.

### The "-m" Flag (Mission)

All commands require a `--mission` (or `-m`) flag. This injects your specific intent into the system prompt.

```bash
grace-ctx [MODE] -m "Your specific goal here" --src [source_dirs]

```

---

## 🛠️ Workflows

### 1. 🏗️ ARCHITECT Mode (The "Blueprints")

**Goal:** Design the system structure before writing code.
**Mechanism:** Scans code *skeletons* (to save tokens) and forces the LLM to output a **Dependency Graph** and **Module Contracts**.

```bash
grace-ctx ARCHITECT -m "Design a clean architecture for the new Payment Module." --src src

```

* **Output:** `.grace/context_architect.xml`
* **LLM Instruction:** "Create a Dependency Graph and write AAG Contracts for each module in `.grace/ARCHITECTURE.md`."

### 2. 👨‍💻 DEVELOPER Mode (The "Translator")

**Goal:** Implement features with zero logic drift.
**Mechanism:** Feeds the **Architecture** + **Raw Code** to the LLM. The prompt frames the task as "translating" the AAG contracts from the Architecture file into executable code.

```bash
grace-ctx DEVELOPER -m "Implement the PaymentService based on the architecture." --src src

```

* **Output:** `.grace/context_developer.xml`
* **LLM Instruction:** "Translate the contracts into Python/JS code. Do not invent new logic."

### 3. ♻️ REFACTOR Mode (Legacy Overhaul)

**Goal:** Reverse-engineer and fix messy "spaghetti code."
**Mechanism:** Ignores existing patterns. It reads **Raw Code** to understand the *business intent*, then redesigns the architecture from scratch using GRACE principles.

```bash
grace-ctx REFACTOR -m "Decouple the Auth logic from the User Controller." --src src/legacy

```

* **Output:** `.grace/context_architect.xml` (Targeting a new architecture)

### 4. 🔬 RESEARCH Mode (The "Scientist")

**Goal:** Gather domain knowledge (e.g., for Math, Science, or complex specs).
**Mechanism:** Scrapes URLs/PDFs from `SOURCES.txt` and distills them into a strict **O-M-I** (Observation-Model-Implementation) specification.

```bash
# 1. Add links to SOURCES.txt
# 2. Run:
grace-ctx RESEARCH -m "Research the mathematical model for A* Pathfinding."

```

* **Output:** `.grace/context_research.xml`

---

## 📂 Project Structure

Your project root remains clean. All context and specification files live in the hidden `.grace/` folder.

```text
my-project/
├── .grace/                 # [Hidden] Context Store
│   ├── context_architect.xml  # Upload to LLM
│   ├── ARCHITECTURE.md     # LLM-generated specs (The "Contract")
│   ├── KNOWLEDGE.md        # Research notes
│   └── MANUAL_RULES.md     # (Optional) User-defined Axioms
├── src/                    # Your code
├── SOURCES.txt             # (Optional) Research links
└── .gitignore

```

## ⚙️ Configuration (Optional)

| File | Location | Purpose |
| --- | --- | --- |
| **`MANUAL_RULES.md`** | `.grace/` | **Immutable Axioms.** Rules here override LLM training (e.g., "Always use Postgres", "Never use recursion"). |
| **`SOURCES.txt`** | Root | List of URLs or local PDF paths for the **RESEARCH** crawler. |

---

## 💡 Best Practices

1. **Iterate:** Do not skip the **ARCHITECT** step for complex tasks. 5 minutes of planning saves 5 hours of debugging.
2. **Verify Contracts:** Before running the `DEVELOPER` mode, read the generated `.grace/ARCHITECTURE.md`. If the logic is wrong there, the code *will* be wrong.
3. **Gitignore:**
```text
.grace/

```