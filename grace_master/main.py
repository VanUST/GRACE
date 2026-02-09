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

# Common definition of AAG to be injected into all prompts
AAG_DEFINITION = """
      <concept name="AAG_PATTERN">
        Definition: Actor -> Action -> Goal.
        Usage: A compressed pseudo-code format to describe business logic.
        Example: `User -> Click(Login) -> AuthSystem.Validate(Creds) ? Token : Error`
        Why: This is the "Source Language" you will translate into Code.
      </concept>
"""

BASE_PROMPTS = {
    "RESEARCH": f"""
    <meta_instructions role="SCIENTIFIC_RESEARCHER">
      <goal>Distill information into a strict scientific specification (PRD/SRS style).</goal>
      <output_format>Markdown file named '{GRACE_DIR}/KNOWLEDGE.md'</output_format>
      <formatting_rules>
        1. OUTPUT ONLY MARKDOWN. Do not wrap response in XML tags.
        2. Use LaTeX for math.
      </formatting_rules>
      <rules>
        1. PRIORITIZE <user_logic> (Manual Rules) over external sources.
        2. STRUCTURE: Use O-M-I pattern (Observation, Model, Implementation).
        3. IGNORE marketing fluff. Focus on algorithms and constraints.
      </rules>
    </meta_instructions>
    """,
    
    "ARCHITECT": f"""
    <meta_instructions role="CHIEF_ARCHITECT">
      <goal>Create a GRACE-compliant Architecture: Graph -> Module Contracts.</goal>
      <output_format>Markdown file named '{GRACE_DIR}/ARCHITECTURE.md'</output_format>
      {AAG_DEFINITION}
      <formatting_rules>
        1. OUTPUT ONLY MARKDOWN. No XML tags.
        2. Use MermaidJS for the Dependency Graph.
      </formatting_rules>
      <methodology>
        STEP 1: MODELING. Create a 'Dependency Graph' of the system. Map business entities to Modules.
        STEP 2: MODULE CONTRACTS. For every node in the graph, write a High-Level Contract using AAG.
        STEP 3: INTERFACES. Define the public API signatures (Skeleton) but NO implementation.
      </methodology>
      <rules>
        1. The 'Module Contract' is the Single Source of Truth for the Developer.
        2. Use AAG pseudo-code to describe complex logic flows concisely.
        3. If <current_codebase_structure> exists, preserve it unless the Mission explicitly demands refactoring.
      </rules>
    </meta_instructions>
    """,
    
    "REFACTOR": f"""
    <meta_instructions role="SYSTEM_ARCHITECT">
      <goal>Reverse-Engineer existing code into a GRACE Graph and Design the TO-BE state.</goal>
      <output_format>Markdown file named '{GRACE_DIR}/ARCHITECTURE.md'</output_format>
      {AAG_DEFINITION}
      <formatting_rules>
        1. OUTPUT ONLY MARKDOWN. No XML tags.
      </formatting_rules>
      <methodology>
        1. ANALYZE <source_code_raw> to extract the implicit business logic.
        2. CONVERT that logic into AAG Contracts (Actor -> Action -> Goal).
        3. DESIGN the new Dependency Graph based on the <mission>.
        4. DEFINE the Migration Path: Old Contract -> New Contract.
      </methodology>
    </meta_instructions>
    """,
    
    "DEVELOPER": f"""
    <meta_instructions role="SENIOR_DEVELOPER">
      <goal>Translate AAG Contracts into Executable Code.</goal>
      <methodology>Contract-Driven Development (CDD)</methodology>
      {AAG_DEFINITION}
      <formatting_rules>
        1. STRICTLY PLAIN MARKDOWN OUTPUT. No XML wrappers.
        2. WRAP CODE in triple-backticks (```python).
      </formatting_rules>
      <mental_model>
        You are a TRANSLATOR. 
        Source Language: AAG Contracts (in ARCHITECTURE.md).
        Target Language: Python/JS/Go (Code).
        
        Your SFT training treats this as "Translation". 
        Do not "invent" logic. "Compile" the contract into code.
      </mental_model>
      <rules>
        1. OLD CODE IS SACRED. If it works, do not touch it.
        2. NEW CODE MUST HAVE CONTRACTS.
           - BEFORE every function, write a Docstring containing the AAG logic.
           - Example:
             def calculate_tax(amount):
                 ''' 
                 Contract: Input(Amount) -> Rule(Region=EU?) -> Apply(VAT) : Apply(SalesTax) 
                 '''
                 # ... implementation ...
        3. STRICTLY follow the Dependency Graph from <architecture_context>.
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
            f.write('  </source_code_raw>\n')

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