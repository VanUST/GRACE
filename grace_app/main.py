import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Set modern aesthetic defaults
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class GraceWorkflowApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GRACE Workflow Manager")
        self.geometry("1100x850")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path_ico = os.path.join(current_dir, "assets", "icon.ico")
        icon_path_png = os.path.join(current_dir, "assets", "icon.png")
        
        try:
            if os.name == 'nt' and os.path.exists(icon_path_ico):
                # Windows handles .ico natively
                self.iconbitmap(icon_path_ico)
            elif os.path.exists(icon_path_png):
                # Linux/macOS requires safe scaling to prevent X11 BadLength crashes
                from PIL import Image, ImageTk
                
                # Open and resize to a safe Window Manager size (64x64)
                img = Image.open(icon_path_png)
                img = img.resize((64, 64), Image.Resampling.LANCZOS)
                
                # Convert and apply
                photo = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, photo)
        except Exception as e:
            print(f"Notice: Could not load custom icon. Reverting to default. ({e})")
        
        self.selected_directory = os.getcwd()
        self.file_vars = {}
        self.max_file_size_bytes = 1024 * 1024  # 1 MB limit
        
        self._build_ui()

    def _build_ui(self):
        # --- Top Header / Controls ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(side="top", fill="x", padx=15, pady=(15, 0))
        
        self.dir_label = ctk.CTkLabel(top_frame, text=f"Active Project: {self.selected_directory}", font=ctk.CTkFont(size=14, weight="bold"))
        self.dir_label.pack(side="left")
        
        btn_select = ctk.CTkButton(top_frame, text="Change Project", command=self.load_directory, width=120, corner_radius=15)
        btn_select.pack(side="left", padx=15)
        
        scale_label = ctk.CTkLabel(top_frame, text="UI Scale:")
        scale_label.pack(side="right", padx=(10, 0))
        
        self.scale_var = ctk.StringVar(value="100%")
        scale_menu = ctk.CTkOptionMenu(top_frame, values=["80%", "90%", "100%", "110%", "125%", "150%"], 
                                       variable=self.scale_var, command=self.change_scaling, width=80, corner_radius=15)
        scale_menu.pack(side="right")

        # --- Main Tabview ---
        self.tabview = ctk.CTkTabview(self, corner_radius=15)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.tab_arch = self.tabview.add("1. Architect (XML Forms)")
        self.tab_ctx = self.tabview.add("2. Context Builder")
        self.tab_ldd = self.tabview.add("3. LDD Monitor")
        
        self._build_tab_architect()
        self._build_tab_context()
        self._build_tab_ldd()

    def change_scaling(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)

    # ==========================================
    # HELPER: FILE/TEMPLATE LOADERS
    # ==========================================
    def _get_file_content(self, filename):
        filepath = os.path.join(self.selected_directory, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"[Omitted: Read error for {filename} - {str(e)}]"
        return f"[{filename} not found in project directory.]"

    def _load_template(self, filename):
        # Look in the selected project dir, script dir, or an assets folder
        paths_to_try = [
            os.path.join(self.selected_directory, filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", filename)
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    return f"[Error reading template {filename}: {str(e)}]"
        
        return f"[Template {filename} not found. Please ensure it exists in the project or script directory.]\n\nUser Instruction:\n{{user_inst}}"

    def _get_selected_files_context(self):
        context_string = ""
        for full_path, (rel_path, var) in self.file_vars.items():
            if var.get():
                # Skip XMLs here since they are injected explicitly in the prompts
                if os.path.basename(full_path) in ["RequirementsAnalysis.xml", "Technology.xml", "DevelopmentPlan.xml"]:
                    continue
                try:
                    if os.path.getsize(full_path) > self.max_file_size_bytes:
                        context_string += f"--- File: {rel_path} ---\n[Omitted: Exceeds 1MB]\n\n"
                        continue

                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    lang = os.path.splitext(rel_path)[1].lower().replace('.', '')
                    if not lang: lang = 'text'
                    
                    context_string += f"--- File: {rel_path} ---\n```{lang}\n{content}\n```\n\n"
                except Exception as e:
                    context_string += f"--- File: {rel_path} ---\n[Omitted: Read error - {e}]\n\n"
        return context_string

    def _copy_to_clipboard(self, text, status_label=None):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            if status_label:
                status_label.configure(text="Prompt Copied to Clipboard!", text_color="#2b8a3e")
        except Exception as e:
            messagebox.showerror("Clipboard Error", str(e))

    # ==========================================
    # TAB 1: ARCHITECT
    # ==========================================
    def _build_tab_architect(self):
        # NEW: Phase 0 Auto-Generator Frame
        auto_frame = ctk.CTkFrame(self.tab_arch, corner_radius=15, fg_color="#1a2b3c")
        auto_frame.pack(fill="x", padx=5, pady=(5, 10))
        
        ctk.CTkLabel(auto_frame, text="Phase 0: Auto-Generate Blueprints from Idea", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 0))
        
        self.high_level_idea = ctk.CTkTextbox(auto_frame, height=80, corner_radius=15)
        self.high_level_idea.pack(fill="x", padx=10, pady=5)
        self.high_level_idea.insert("0.0", "Describe your project, feature, or goal here in plain English...")
        
        btn_auto_prompt = ctk.CTkButton(auto_frame, text="Compile & Copy Initialization Prompt", command=self.copy_init_prompt, fg_color="#005b96", hover_color="#003f6b", height=40, corner_radius=15)
        btn_auto_prompt.pack(side="right", padx=10, pady=(0, 10))
        
        self.init_status = ctk.CTkLabel(auto_frame, text="", text_color="gray")
        self.init_status.pack(side="right", padx=10, pady=(0, 10))

        # --- The Manual Forms (Kept for tweaking Gemini's output later) ---
        xml_tabs = ctk.CTkTabview(self.tab_arch, corner_radius=15)
        xml_tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        tab_req = xml_tabs.add("RequirementsAnalysis")
        tab_tech = xml_tabs.add("Technology")
        tab_plan = xml_tabs.add("DevelopmentPlan")

        self._build_form_requirements(tab_req)
        self._build_form_technology(tab_tech)
        self._build_form_plan(tab_plan)

        # Bottom Action Area
        action_frame = ctk.CTkFrame(self.tab_arch, fg_color="transparent")
        action_frame.pack(fill="x", pady=10)
        
        btn_save = ctk.CTkButton(action_frame, text="Save Manual Form Edits to XML", command=self.save_all_xmls, height=45, corner_radius=15)
        btn_save.pack(side="left", fill="x", expand=True, padx=(0, 5))

        prompt_frame = ctk.CTkFrame(self.tab_arch, corner_radius=15)
        prompt_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(prompt_frame, text="Phase 1: Update Existing Blueprints (Architect Prompt):").pack(anchor="w", padx=10, pady=(10, 0))
        self.arch_instruction = ctk.CTkTextbox(prompt_frame, height=60, corner_radius=15)
        self.arch_instruction.pack(fill="x", padx=10, pady=5)
        self.arch_instruction.insert("0.0", "Update the existing architecture to include...")

        self.arch_status = ctk.CTkLabel(prompt_frame, text="", text_color="gray")
        self.arch_status.pack(side="right", padx=10)

        btn_copy_prompt = ctk.CTkButton(prompt_frame, text="Compile & Copy Architect Prompt", command=self.copy_architect_prompt, fg_color="#8a2b8a", hover_color="#6e216e", height=40, corner_radius=15)
        btn_copy_prompt.pack(side="right", padx=10, pady=10)

    # NEW: Function to handle the Initialization Prompt
    def copy_init_prompt(self):
        user_idea = self.high_level_idea.get("0.0", "end").strip()
        template = self._load_template("init_prompt.txt")
        prompt = template.replace("{user_idea}", user_idea)
        
        self._copy_to_clipboard(prompt, self.init_status)

    def _build_form_requirements(self, parent):
        ctk.CTkLabel(parent, text="Project Goal:", anchor="w").pack(fill="x", pady=(5, 0))
        self.req_goal = ctk.CTkEntry(parent, placeholder_text="Enter high-level objective...", corner_radius=15)
        self.req_goal.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(parent, text="Actors (One per line. Format: id | Description):", anchor="w").pack(fill="x")
        self.req_actors = ctk.CTkTextbox(parent, height=80, corner_radius=15)
        self.req_actors.pack(fill="x", pady=(0, 10))
        self.req_actors.insert("0.0", "user | End User\nsystem | Backend Agent")

        ctk.CTkLabel(parent, text="Use Cases (One per line. Format: id | actor_id | Action | Goal | Constraints):", anchor="w").pack(fill="x")
        self.req_usecases = ctk.CTkTextbox(parent, height=120, corner_radius=15)
        self.req_usecases.pack(fill="both", expand=True, pady=(0, 5))
        self.req_usecases.insert("0.0", "uc_01 | user | Uploads raw data | System ingests data | Latency < 2s")

    def _build_form_technology(self, parent):
        ctk.CTkLabel(parent, text="Language & Framework:", anchor="w").pack(fill="x", pady=(5, 0))
        self.tech_lang = ctk.CTkEntry(parent, placeholder_text="e.g., Python 3.10+, FastAPI", corner_radius=15)
        self.tech_lang.pack(fill="x", pady=(0, 10))
        self.tech_lang.insert(0, "Python 3.10+")

        ctk.CTkLabel(parent, text="Dependencies (One per line. Format: name | version | reason):", anchor="w").pack(fill="x")
        self.tech_deps = ctk.CTkTextbox(parent, height=120, corner_radius=15)
        self.tech_deps.pack(fill="x", pady=(0, 10))
        self.tech_deps.insert("0.0", "numpy | >=1.24.0 | Required for array matrix operations")

        ctk.CTkLabel(parent, text="Environment Guidelines:", anchor="w").pack(fill="x")
        self.tech_env = ctk.CTkTextbox(parent, height=80, corner_radius=15)
        self.tech_env.pack(fill="both", expand=True, pady=(0, 5))
        self.tech_env.insert("0.0", "Strictly adhere to virtual environment isolation.")

    def _build_form_plan(self, parent):
        ctk.CTkLabel(parent, text="Architectural Pattern:", anchor="w").pack(fill="x", pady=(5, 0))
        self.plan_arch = ctk.CTkEntry(parent, corner_radius=15)
        self.plan_arch.pack(fill="x", pady=(0, 10))
        self.plan_arch.insert(0, "Intent-Driven Component Architecture")

        ctk.CTkLabel(parent, text="Modules (One per module block. Separate modules by empty line):\nFormat:\n[Module ID]\nInput: ...\nOutput: ...\nBehavior: ...\nTest: ...", anchor="w").pack(fill="x")
        self.plan_modules = ctk.CTkTextbox(parent, corner_radius=15)
        self.plan_modules.pack(fill="both", expand=True, pady=(0, 5))
        self.plan_modules.insert("0.0", "[data_ingestion]\nInput: Raw byte stream\nOutput: Normalized vectors\nBehavior: Fails gracefully on malformed bytes\nTest: If stream is null, explicitly log error.")

    def save_all_xmls(self):
        try:
            req_root = ET.Element("RequirementsAnalysis")
            ET.SubElement(req_root, "ProjectGoal").text = self.req_goal.get()
            actors_el = ET.SubElement(req_root, "Actors")
            for line in self.req_actors.get("0.0", "end").strip().split('\n'):
                if '|' in line:
                    a_id, a_desc = map(str.strip, line.split('|', 1))
                    act = ET.SubElement(actors_el, "Actor", id=a_id)
                    act.text = a_desc
            uc_el = ET.SubElement(req_root, "UseCases")
            for line in self.req_usecases.get("0.0", "end").strip().split('\n'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    uc = ET.SubElement(uc_el, "UseCase", id=parts[0])
                    aag = ET.SubElement(uc, "AAG")
                    ET.SubElement(aag, "ActorRef").text = parts[1]
                    ET.SubElement(aag, "Action").text = parts[2]
                    ET.SubElement(aag, "Goal").text = parts[3]
                    if len(parts) >= 5:
                        ET.SubElement(uc, "Constraints").text = parts[4]
            self._write_xml("RequirementsAnalysis.xml", req_root)

            tech_root = ET.Element("Technology")
            stack = ET.SubElement(tech_root, "Stack")
            ET.SubElement(stack, "Language").text = self.tech_lang.get()
            deps = ET.SubElement(tech_root, "Dependencies")
            for line in self.tech_deps.get("0.0", "end").strip().split('\n'):
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        ET.SubElement(deps, "Package", name=parts[0], version=parts[1], reason=parts[2])
            env = ET.SubElement(tech_root, "Environment")
            ET.SubElement(env, "Guideline").text = self.tech_env.get("0.0", "end").strip()
            self._write_xml("Technology.xml", tech_root)

            plan_root = ET.Element("DevelopmentPlan")
            arch = ET.SubElement(plan_root, "Architecture")
            ET.SubElement(arch, "Pattern").text = self.plan_arch.get()
            mods_el = ET.SubElement(plan_root, "Modules")
            mod_blocks = self.plan_modules.get("0.0", "end").strip().split('\n\n')
            for block in mod_blocks:
                lines = block.strip().split('\n')
                if not lines or not lines[0].startswith('['): continue
                mod_id = lines[0].strip('[]')
                mod = ET.SubElement(mods_el, "Module", id=mod_id)
                contract = ET.SubElement(mod, "MODULE_CONTRACT")
                tests = ET.SubElement(mod, "MentalTests")
                for line in lines[1:]:
                    if line.startswith("Input:"): ET.SubElement(contract, "Input").text = line.split(':', 1)[1].strip()
                    elif line.startswith("Output:"): ET.SubElement(contract, "Output").text = line.split(':', 1)[1].strip()
                    elif line.startswith("Behavior:"): ET.SubElement(contract, "Behavior").text = line.split(':', 1)[1].strip()
                    elif line.startswith("Test:"): ET.SubElement(tests, "Test").text = line.split(':', 1)[1].strip()
            self._write_xml("DevelopmentPlan.xml", plan_root)
            
            messagebox.showinfo("Success", "All GRACE XML Blueprints generated successfully!")
            self.refresh_file_list() 
        except Exception as e:
            messagebox.showerror("XML Generation Error", f"Failed to generate XML:\n{str(e)}")

    def _write_xml(self, filename, element):
        xml_string = ET.tostring(element, encoding='utf-8')
        parsed = minidom.parseString(xml_string)
        pretty_xml = parsed.toprettyxml(indent="    ")
        filepath = os.path.join(self.selected_directory, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

    def copy_architect_prompt(self):
        req_xml = self._get_file_content("RequirementsAnalysis.xml")
        tech_xml = self._get_file_content("Technology.xml")
        user_inst = self.arch_instruction.get("0.0", "end").strip()

        # Using explicit string replacement to avoid KeyErrors from curly braces in user code/XML
        template = self._load_template("architect_prompt.txt")
        prompt = template.replace("{req_xml}", req_xml)
        prompt = prompt.replace("{tech_xml}", tech_xml)
        prompt = prompt.replace("{user_inst}", user_inst)
        
        self._copy_to_clipboard(prompt, self.arch_status)

    # ==========================================
    # TAB 2: CONTEXT BUILDER
    # ==========================================
    def _build_tab_context(self):
        filter_frame = ctk.CTkFrame(self.tab_ctx, corner_radius=15)
        filter_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(filter_frame, text="Allowed Extensions:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_exts = ctk.CTkEntry(filter_frame, width=200, placeholder_text=".py, .js, .xml", corner_radius=15)
        self.entry_exts.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.entry_exts.insert(0, ".py, .xml, .md")

        ctk.CTkLabel(filter_frame, text="Ignored Dirs:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.entry_dirs = ctk.CTkEntry(filter_frame, width=200, placeholder_text=".git, node_modules", corner_radius=15)
        self.entry_dirs.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.entry_dirs.insert(0, ".git, __pycache__, venv, node_modules")

        ctk.CTkLabel(filter_frame, text="Ignored Files:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_files = ctk.CTkEntry(filter_frame, width=200, placeholder_text="secrets.py, .env", corner_radius=15)
        self.entry_files.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        btn_apply = ctk.CTkButton(filter_frame, text="Apply Filters & Scan", command=self.refresh_file_list, corner_radius=15)
        btn_apply.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        body_frame = ctk.CTkFrame(self.tab_ctx, fg_color="transparent")
        body_frame.pack(fill="both", expand=True)

        self.scroll_files = ctk.CTkScrollableFrame(body_frame, label_text="Project Files", corner_radius=15)
        self.scroll_files.pack(side="left", fill="both", expand=True, padx=(0, 10))

        sidebar = ctk.CTkFrame(body_frame, width=300, corner_radius=15)
        sidebar.pack(side="right", fill="y")

        ctk.CTkButton(sidebar, text="Select All", command=self.select_all_files, corner_radius=15).pack(fill="x", padx=10, pady=(15, 5))
        ctk.CTkButton(sidebar, text="Deselect All", command=self.deselect_all_files, corner_radius=15).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(sidebar, text="User Instruction (Taskmaster Prompt):").pack(anchor="w", padx=10, pady=(20, 0))
        self.prompt_prefix = ctk.CTkTextbox(sidebar, height=100, corner_radius=15)
        self.prompt_prefix.pack(fill="x", padx=10, pady=5)
        self.prompt_prefix.insert("0.0", "Review the appended files. Based on the DevelopmentPlan, write a strict, copy-pasteable prompt that I can feed to GLM-5 so it implements...")

        btn_copy = ctk.CTkButton(sidebar, text="Compile & Copy Taskmaster Prompt", command=self.copy_taskmaster_prompt, fg_color="#2b8a3e", hover_color="#216e31", corner_radius=15, height=45)
        btn_copy.pack(fill="x", padx=10, pady=20)
        
        self.ctx_status = ctk.CTkLabel(sidebar, text="", text_color="gray")
        self.ctx_status.pack(fill="x", padx=10)

    def refresh_file_list(self):
        for widget in self.scroll_files.winfo_children():
            widget.destroy()
        self.file_vars.clear()

        exts = [e.strip().lower() for e in self.entry_exts.get().split(',') if e.strip()]
        ig_dirs = [d.strip() for d in self.entry_dirs.get().split(',') if d.strip()]
        ig_files = [f.strip() for f in self.entry_files.get().split(',') if f.strip()]

        for root, dirs, files in os.walk(self.selected_directory):
            dirs[:] = [d for d in dirs if d not in ig_dirs]

            for file in files:
                if file in ig_files: continue
                ext = os.path.splitext(file)[1].lower()
                if exts and ext not in exts: continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.selected_directory)
                
                var = ctk.BooleanVar(value=False)
                self.file_vars[full_path] = (rel_path, var)
                
                cb = ctk.CTkCheckBox(self.scroll_files, text=rel_path, variable=var, corner_radius=5)
                cb.pack(anchor="w", padx=5, pady=4)

    def select_all_files(self):
        for _, (_, var) in self.file_vars.items(): var.set(True)

    def deselect_all_files(self):
        for _, (_, var) in self.file_vars.items(): var.set(False)

    def copy_taskmaster_prompt(self):
        req_xml = self._get_file_content("RequirementsAnalysis.xml")
        tech_xml = self._get_file_content("Technology.xml")
        plan_xml = self._get_file_content("DevelopmentPlan.xml")
        selected_code = self._get_selected_files_context()
        user_inst = self.prompt_prefix.get("0.0", "end").strip()

        template = self._load_template("taskmaster_prompt.txt")
        prompt = template.replace("{req_xml}", req_xml)
        prompt = prompt.replace("{tech_xml}", tech_xml)
        prompt = prompt.replace("{plan_xml}", plan_xml)
        prompt = prompt.replace("{selected_code}", selected_code)
        prompt = prompt.replace("{user_inst}", user_inst)

        self._copy_to_clipboard(prompt, self.ctx_status)

    # ==========================================
    # TAB 3: LDD MONITOR
    # ==========================================
    def _build_tab_ldd(self):
        top_bar = ctk.CTkFrame(self.tab_ldd, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(top_bar, text="Load agent_error.log", command=self.load_log, corner_radius=15).pack(side="left")
        
        self.log_viewer = ctk.CTkTextbox(self.tab_ldd, font=ctk.CTkFont(family="Courier", size=12), corner_radius=15)
        self.log_viewer.pack(fill="both", expand=True)

        # Prompt Compiler Section
        prompt_frame = ctk.CTkFrame(self.tab_ldd, corner_radius=15)
        prompt_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(prompt_frame, text="User Instruction for Debugger (What do you need patched?):").pack(anchor="w", padx=10, pady=(10, 0))
        self.dbg_instruction = ctk.CTkTextbox(prompt_frame, height=60, corner_radius=15)
        self.dbg_instruction.pack(fill="x", padx=10, pady=5)
        self.dbg_instruction.insert("0.0", "Identify the failure in the belief state log above. Provide the strict code patch to fix this bug while maintaining GRACE markup constraints.")

        self.dbg_status = ctk.CTkLabel(prompt_frame, text="", text_color="gray")
        self.dbg_status.pack(side="right", padx=10)

        btn_copy_prompt = ctk.CTkButton(prompt_frame, text="Compile & Copy Debugger Prompt", command=self.copy_debugger_prompt, fg_color="#b22222", hover_color="#8b0000", height=40, corner_radius=15)
        btn_copy_prompt.pack(side="right", padx=10, pady=10)

    def load_log(self):
        self.log_viewer.delete("0.0", "end")
        log_path = os.path.join(self.selected_directory, "agent_error.log")
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    self.log_viewer.insert("0.0", f.read())
            except Exception as e:
                self.log_viewer.insert("0.0", f"Error reading log: {e}")
        else:
            self.log_viewer.insert("0.0", f"No agent_error.log found in {self.selected_directory}.")

    def copy_debugger_prompt(self):
        req_xml = self._get_file_content("RequirementsAnalysis.xml")
        tech_xml = self._get_file_content("Technology.xml")
        plan_xml = self._get_file_content("DevelopmentPlan.xml")
        agent_log = self._get_file_content("agent_error.log")
        selected_code = self._get_selected_files_context()
        user_inst = self.dbg_instruction.get("0.0", "end").strip()

        template = self._load_template("debugger_prompt.txt")
        prompt = template.replace("{req_xml}", req_xml)
        prompt = prompt.replace("{tech_xml}", tech_xml)
        prompt = prompt.replace("{plan_xml}", plan_xml)
        prompt = prompt.replace("{agent_log}", agent_log)
        prompt = prompt.replace("{selected_code}", selected_code)
        prompt = prompt.replace("{user_inst}", user_inst)

        self._copy_to_clipboard(prompt, self.dbg_status)

    # ==========================================
    # UTILS
    # ==========================================
    def load_directory(self):
        dir_path = filedialog.askdirectory(initialdir=self.selected_directory)
        if dir_path:
            self.selected_directory = dir_path
            self.dir_label.configure(text=f"Active Project: {self.selected_directory}")
            self.refresh_file_list()

def main():
    app = GraceWorkflowApp()
    app.mainloop()

if __name__ == "__main__":
    main()