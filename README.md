# GRACE Workflow Manager

A modern, CLI-callable GUI application built with CustomTkinter for managing the GRACE (Graph-RAG Anchored Code Engineering) workflow. 

This tool serves as the bridge between high-level LLM architectural planning (Gemini) and deterministic, agent-driven execution (GLM-5 / Kilo Code).

## Features
* **Architect (XML Forms):** Interactively generate and manage `RequirementsAnalysis.xml`, `Technology.xml`, and `DevelopmentPlan.xml`.
* **Context Builder:** Seamlessly parse project directories, filter files by extension or explicit ignore lists, and copy heavily structured context directly to your clipboard for LLM handoff.
* **LDD Monitor:** Instantly read `agent_error.log` to review your execution agent's Belief State and structured traces without running the code manually.

## Installation

Ensure you have Python 3.8+ installed. 

1. Clone this repository.
2. Navigate to the root directory containing `pyproject.toml`.
3. Install the package globally in editable mode:
   ```bash
   pip install -e .