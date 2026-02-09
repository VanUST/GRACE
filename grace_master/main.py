import os
import argparse
import requests
import tempfile
import logging
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
GRACE_DIR = ".grace"

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
    "RESEARCH": f"""
    <meta_instructions role="RESEARCHER">
      <goal>Distill information into a strict scientific specification (O-M-I).</goal>
      <output_format>Markdown file named '{GRACE_DIR}/KNOWLEDGE.md'</output_format>
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
    "ARCHITECT": f"""
    <meta_instructions role="ARCHITECT">
      <goal>Design or extend software architecture based on MISSION and KNOWLEDGE.</goal>
      <output_format>Markdown file named '{GRACE_DIR}/ARCHITECTURE.md'</output_format>
      <rules>
        1. Analyze the <mission> and existing <current_codebase_structure>.
        2. MAINTENANCE MODE: If <current_codebase_structure> exists, respect its patterns unless explicitly told to change them.
        3. DEFINE CONTRACTS: For every major module, write the interface.
        4. Use 'SKELETON' mode: Describe functions but do not implement logic.
        5. OUTPUT: A high-level dependency graph and interface definitions.
      </rules>
    </meta_instructions>
    """,
    "REFACTOR": f"""
    <meta_instructions role="LEAD_ARCHITECT">
      <goal>Analyze existing codebase and Design a NEW Architecture from scratch.</goal>
      <output_format>Markdown file named '{GRACE_DIR}/ARCHITECTURE.md'</output_format>
      <rules>
        1. IGNORE existing architectural flaws. You are designing the IDEAL state.
        2. Analyze <source_code_raw> to understand the business logic required.
        3. Create a dependency graph that solves the <mission>.
        4. DEFINE MIGRATION: Briefly outline how to move from current state to new state.
      </rules>
    </meta_instructions>
    """,
    "DEVELOPER": """
    <meta_instructions role="DEVELOPER">
      <goal>Implement code based on ARCHITECTURE and CONTRACTS.</goal>
      <methodology>Hybrid: GRACE (New Code) + Preservation (Old Code)</methodology>
      <rules>
        1. OLD CODE IS SACRED: If it works, do not break it. Do not refactor stylistic issues unless necessary for the Mission.
        2. NEW CODE IS GRACE: All new logic must follow the AAG (Actor-Action-Goal) pattern.
        3. STRICTLY follow the signatures defined in <architecture_context>.
        4. BEFORE every new function, write an AAG comment.
      </rules>
    </meta_instructions>
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

def get_grace_content(filename):
    """Helper to get content specifically from the hidden .grace directory"""
    return get_file_content(os.path.join(GRACE_DIR, filename))

def generate_multi_tree(start_paths, exclude_dirs):
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

def build_context(mode, source_dirs, mission_text):
    if not os.path.exists(GRACE_DIR):
        os.makedirs(GRACE_DIR)
        print(f"📁 Created centralized context folder: {GRACE_DIR}/")
        
    output_xml = os.path.join(GRACE_DIR, f"context_{mode.lower()}.xml")
    
    # Common exclude list
    exclude = [".git", "__pycache__", "venv", "node_modules", "specs", ".idea", ".vscode", ".grace", "dist", "build"]
    
    print(f"🚀 Building Context for: {mode}")
    print(f"🎯 Mission: {mission_text[:50]}...")
    print(f"📂 Sources: {source_dirs}")

    with open(output_xml, 'w', encoding='utf-8') as f:
        f.write(f'<grace_context mode="{mode}">\n')
        
        # 1. INJECT PROMPT
        prompt_content = BASE_PROMPTS.get(mode, "")
        f.write(prompt_content)
        
        # 2. INJECT MISSION (Required for all modes, from CLI arg)
        f.write(f'\n  <mission><![CDATA[\n{mission_text}\n]]></mission>\n')

        # --- MODE 1: RESEARCH ---
        if mode == "RESEARCH":
            manual_rules = get_grace_content("MANUAL_RULES.md")
            if manual_rules:
                f.write(f'\n  <user_logic type="axiom"><![CDATA[\n{manual_rules}\n]]></user_logic>\n')
            
            f.write('\n  <raw_sources>\n')
            if os.path.exists("SOURCES.txt"):
                with open("SOURCES.txt", 'r') as s:
                    lines = [line.strip() for line in s if line.strip() and not line.startswith('#')]
                    for source_path in lines:
                        content = fetch_source(source_path)
                        safe_content = content.replace("]]>", "]]]]><![CDATA[>")
                        f.write(f'    <article source="{source_path}"><![CDATA[\n{safe_content}\n]]></article>\n')
            f.write('  </raw_sources>\n')

        # --- MODE 2: ARCHITECT (Maintenance/Extension) ---
        elif mode == "ARCHITECT":
            specs = get_grace_content("KNOWLEDGE.md")
            if specs: f.write(f'\n  <research_specs><![CDATA[\n{specs}\n]]></research_specs>\n')
            
            f.write(f'\n  <current_codebase_structure>\n')
            f.write(f'    <tree><![CDATA[\n{generate_multi_tree(source_dirs, exclude)}\n]]></tree>\n')
            
            for src_dir in source_dirs:
                if not os.path.exists(src_dir): continue
                for r, d, files in os.walk(src_dir):
                    d[:] = [x for x in d if x not in exclude]
                    for file in files:
                        if file.endswith(('.pyc', '.png', '.jpg', '.exe')): continue
                        path = os.path.join(r, file)
                        content = get_file_content(path)
                        skeleton = extract_skeleton(content)
                        f.write(f'    <file path="{path}" type="skeleton"><![CDATA[\n{skeleton}\n]]></file>\n')
            f.write('  </current_codebase_structure>\n')

        # --- MODE 3: REFACTOR (New Architecture from Old Code) ---
        elif mode == "REFACTOR":
            specs = get_grace_content("KNOWLEDGE.md")
            if specs: f.write(f'\n  <research_specs><![CDATA[\n{specs}\n]]></research_specs>\n')
            
            f.write(f'\n  <source_code_raw>\n')
            f.write(f'    <tree><![CDATA[\n{generate_multi_tree(source_dirs, exclude)}\n]]></tree>\n')
            
            for src_dir in source_dirs:
                if not os.path.exists(src_dir): continue
                for r, d, files in os.walk(src_dir):
                    d[:] = [x for x in d if x not in exclude]
                    for file in files:
                        if file.endswith(('.pyc', '.png', '.jpg', '.exe')): continue
                        path = os.path.join(r, file)
                        content = get_file_content(path).replace("]]>", "]]]]><![CDATA[>")
                        f.write(f'    <file path="{path}"><![CDATA[\n{content}\n]]></file>\n')
            f.write('  </source_code_raw>\n')

        # --- MODE 4: DEVELOPER (Implementation) ---
        elif mode == "DEVELOPER":
            # Note: Architecture now lives in .grace/ARCHITECTURE.md
            arch = get_grace_content("ARCHITECTURE.md")
            if arch: f.write(f'\n  <architecture_context><![CDATA[\n{arch}\n]]></architecture_context>\n')
            
            f.write(f'\n  <source_code>\n    <tree><![CDATA[\n{generate_multi_tree(source_dirs, exclude)}\n]]></tree>\n')
            for src_dir in source_dirs:
                if not os.path.exists(src_dir): continue
                for r, d, files in os.walk(src_dir):
                    d[:] = [x for x in d if x not in exclude]
                    for file in files:
                        if file.endswith(('.pyc', '.png', '.jpg', '.exe')): continue
                        path = os.path.join(r, file)
                        content = get_file_content(path).replace("]]>", "]]]]><![CDATA[>")
                        f.write(f'    <file path="{path}"><![CDATA[\n{content}\n]]></file>\n')
            f.write('  </source_code>\n')

        f.write('</grace_context>\n')
    print(f"✅ Generated: {output_xml}")

def main_entry_point():
    parser = argparse.ArgumentParser(description="GRACE Context Generator")
    parser.add_argument("mode", choices=["RESEARCH", "ARCHITECT", "DEVELOPER", "REFACTOR"])
    parser.add_argument("-m", "--mission", required=True, help="The specific task or mission description for this run")
    parser.add_argument("--src", nargs='+', default=["src"], help="Source directories to scan")
    
    args = parser.parse_args()
    build_context(args.mode, args.src, args.mission)

if __name__ == "__main__":
    main_entry_point()