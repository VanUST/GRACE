import os
import argparse
import requests
import tempfile
import logging
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- DOCLING API SETUP ---
HAS_DOCLING = False
DOC_CONVERTER = None

try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.datamodel.base_models import InputFormat
    
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pipeline_options.do_formula_enrichment = True
    
    DOC_CONVERTER = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    HAS_DOCLING = True
except ImportError:
    pass

# --- PROMPT TEMPLATES ---

BASE_PROMPTS = {
    "RESEARCH": """
    <meta_instructions role="RESEARCHER">
      <goal>Distill information into a strict scientific specification (O-M-I).</goal>
      <output_format>Markdown file named 'specs/KNOWLEDGE.md'</output_format>
      <rules>
        1. PRIORITIZE <user_logic> (Manual Rules) over external sources. These are the axioms.
        2. Ignore marketing fluff. Focus on algorithms, math, and physics.
        3. STRUCTURE: For each phenomenon, use the O-M-I pattern:
           - Observation: The real-world phenomenon.
           - Model: The mathematical formula (LaTeX preferred) or logic rule.
           - Implementation: How to represent this in code (variables, constraints).
      </rules>
    </meta_instructions>
    """,
    "ARCHITECT": """
    <meta_instructions role="ARCHITECT">
      <goal>Design the software architecture based on MISSION and KNOWLEDGE.</goal>
      <output_format>Markdown file named 'specs/ARCHITECTURE.md'</output_format>
      <rules>
        1. Analyze the <mission> and <research_specs>.
        2. Create a high-level dependency graph.
        3. DEFINE CONTRACTS: For every major module, write the interface.
        4. Use 'SKELETON' mode: Describe functions but do not implement logic.
      </rules>
    </meta_instructions>
    """,
    "DEVELOPER": """
    <meta_instructions role="DEVELOPER">
      <goal>Implement the code based on ARCHITECTURE and CONTRACTS.</goal>
      <methodology>GRACE Framework + AAG (Actor-Action-Goal)</methodology>
      <rules>
        1. STRICTLY follow the signatures defined in <architecture_context>.
        2. BEFORE every function, write an AAG comment.
        3. Do NOT hallucinate new features. Stick to the plan.
      </rules>
    </meta_instructions>
    """
}

# --- LEGACY WORKFLOW INJECTIONS ---
LEGACY_INSTRUCTIONS = {
    "ARCHITECT": """
      <legacy_mode_active>TRUE</legacy_mode_active>
      <legacy_rules>
        1. AUDIT: The <current_codebase> is LEGACY (Non-AAG compliant).
        2. STRATEGY: Do not just overwrite. Design a "Refactoring Plan" or "Adapter Layer".
        3. Identify "God Classes" to break down into Actors.
        4. Output a migration path in ARCHITECTURE.md: "Current State -> Refactoring Steps -> Target AAG State".
      </legacy_rules>
    """,
    "DEVELOPER": """
      <legacy_mode_active>TRUE</legacy_mode_active>
      <legacy_rules>
        1. REFACTORING: You are converting legacy code to AAG.
        2. PRESERVE LOGIC: Ensure the original business logic from <source_code> is kept, but wrapped in AAG structures.
        3. If a file is too large, split it.
      </legacy_rules>
    """
}

# --- UTILITY FUNCTIONS ---

def parse_pdf_docling(file_path):
    if not HAS_DOCLING or DOC_CONVERTER is None:
        return "[ERROR] 'docling' missing. Run: pip install docling"
    try:
        conv_result = DOC_CONVERTER.convert(file_path)
        return conv_result.document.export_to_markdown()
    except Exception as e:
        return f"[ERROR] Docling parsing failed: {e}"

def fetch_source(source):
    print(f"🔍 [DEBUG] Processing: {source}")
    is_pdf = source.lower().endswith('.pdf')
    is_url = source.startswith(('http://', 'https://'))
    local_path = source
    temp_file = None
    
    if is_url and not is_pdf:
        try:
            head = requests.head(source, timeout=5)
            if 'application/pdf' in head.headers.get('Content-Type', ''): is_pdf = True
        except: pass

    try:
        if is_url:
            headers = {'User-Agent': 'Scientific-Crawler/1.0'}
            resp = requests.get(source, headers=headers, timeout=30)
            resp.raise_for_status()
            if is_pdf:
                fd, temp_file_path = tempfile.mkstemp(suffix=".pdf")
                os.write(fd, resp.content)
                os.close(fd)
                local_path = temp_file_path
                temp_file = temp_file_path
            else:
                raw_text = resp.text
        
        if is_pdf:
            content = parse_pdf_docling(local_path)
            if temp_file: os.remove(temp_file)
            return content
        else:
            if not is_url:
                if not os.path.exists(source): return f"Error: File not found {source}"
                with open(source, 'r', encoding='utf-8') as f: raw_text = f.read()
            soup = BeautifulSoup(raw_text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'iframe']): tag.decompose()
            return md(str(soup.body) if soup.body else str(soup))
    except Exception as e:
        if temp_file: os.remove(temp_file)
        return f"Error processing {source}: {e}"

def get_file_content(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return f.read()
    return ""

def generate_multi_tree(start_paths, exclude_dirs):
    """Generates a combined tree for multiple source directories."""
    tree_str = ""
    for start_path in start_paths:
        if not os.path.exists(start_path):
            tree_str += f"[MISSING DIRECTORY: {start_path}]\n"
            continue
            
        tree_str += f"ROOT: {start_path}/\n"
        for root, dirs, files in os.walk(start_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            level = root.replace(start_path, '').count(os.sep)
            indent = '    ' * (level + 1)
            tree_str += f"{indent}|-- {os.path.basename(root)}/\n"
            for f in files:
                tree_str += f"{indent}    |-- {f}\n"
        tree_str += "\n"
    return tree_str

def extract_skeleton(content):
    lines = content.split('\n')
    skeleton = [l for l in lines if l.strip().startswith(('def ', 'class ', 'import ', 'from ', '@', 'async ')) or '"""' in l]
    return "\n".join(skeleton)

# --- MAIN BUILDER LOGIC ---

def build_context(mode, source_dirs, is_legacy=False):
    output_xml = f"context_{mode.lower()}.xml"
    exclude = [".git", "__pycache__", "venv", "node_modules", "specs", ".idea", ".vscode"]
    
    print(f"🚀 Building Context for: {mode}")
    print(f"📂 Sources: {source_dirs}")
    if is_legacy: print("⚠️ LEGACY MODE ACTIVE: Injecting Refactoring Prompts")

    with open(output_xml, 'w', encoding='utf-8') as f:
        f.write(f'<grace_context mode="{mode}">\n')
        
        # 1. INJECT PROMPTS (With Legacy Override)
        prompt_content = BASE_PROMPTS.get(mode, "")
        if is_legacy and mode in LEGACY_INSTRUCTIONS:
            prompt_content += f"\n{LEGACY_INSTRUCTIONS[mode]}"
        f.write(prompt_content)
        
        # 2. INJECT MISSION
        mission = get_file_content("TASK.md")
        if mission: f.write(f'\n  <mission><![CDATA[\n{mission}\n]]></mission>\n')

        # --- MODE 1: RESEARCH ---
        if mode == "RESEARCH":
            # A. Manual Rules (High Priority)
            manual_rules = get_file_content("specs/MANUAL_RULES.md")
            if manual_rules:
                f.write(f'\n  <user_logic type="axiom"><![CDATA[\n{manual_rules}\n]]></user_logic>\n')
            
            # B. External Sources
            f.write('\n  <raw_sources>\n')
            if os.path.exists("SOURCES.txt"):
                with open("SOURCES.txt", 'r') as s:
                    lines = [line.strip() for line in s if line.strip() and not line.startswith('#')]
                    for source_path in lines:
                        content = fetch_source(source_path)
                        safe_content = content.replace("]]>", "]]]]><![CDATA[>")
                        f.write(f'    <article source="{source_path}"><![CDATA[\n{safe_content}\n]]></article>\n')
            f.write('  </raw_sources>\n')

        # --- MODE 2: ARCHITECT ---
        elif mode == "ARCHITECT":
            specs = get_file_content("specs/KNOWLEDGE.md")
            if specs: f.write(f'\n  <research_specs><![CDATA[\n{specs}\n]]></research_specs>\n')
            
            f.write(f'\n  <current_codebase type="{"legacy_full" if is_legacy else "skeleton"}">\n')
            f.write(f'    <tree><![CDATA[\n{generate_multi_tree(source_dirs, exclude)}\n]]></tree>\n')
            
            for src_dir in source_dirs:
                if not os.path.exists(src_dir): continue
                for r, d, files in os.walk(src_dir):
                    d[:] = [x for x in d if x not in exclude]
                    for file in files:
                        path = os.path.join(r, file)
                        content = get_file_content(path)
                        # If legacy, Architect might need full code to understand the mess. 
                        # If standard, skeleton is enough.
                        final_content = content if is_legacy else extract_skeleton(content)
                        f.write(f'    <file path="{path}"><![CDATA[\n{final_content}\n]]></file>\n')
            f.write('  </current_codebase>\n')

        # --- MODE 3: DEVELOPER ---
        elif mode == "DEVELOPER":
            arch = get_file_content("specs/ARCHITECTURE.md")
            if arch: f.write(f'\n  <architecture_context><![CDATA[\n{arch}\n]]></architecture_context>\n')
            
            f.write(f'\n  <source_code>\n    <tree><![CDATA[\n{generate_multi_tree(source_dirs, exclude)}\n]]></tree>\n')
            for src_dir in source_dirs:
                if not os.path.exists(src_dir): continue
                for r, d, files in os.walk(src_dir):
                    d[:] = [x for x in d if x not in exclude]
                    for file in files:
                        path = os.path.join(r, file)
                        content = get_file_content(path).replace("]]>", "]]]]><![CDATA[>")
                        f.write(f'    <file path="{path}"><![CDATA[\n{content}\n]]></file>\n')
            f.write('  </source_code>\n')

        f.write('</grace_context>\n')
    print(f"✅ Generated: {output_xml}")

def main_entry_point():
    parser = argparse.ArgumentParser(description="GRACE Context Generator")
    parser.add_argument("mode", choices=["RESEARCH", "ARCHITECT", "DEVELOPER"])
    parser.add_argument("--src", nargs='+', default=["src"])
    parser.add_argument("--legacy", action="store_true")
    
    args = parser.parse_args()
    
    # Defaults to current working directory if not absolute path
    build_context(args.mode, args.src, args.legacy)

if __name__ == "__main__":
    main_entry_point()