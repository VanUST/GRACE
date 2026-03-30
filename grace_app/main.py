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
        self.geometry("1100x800")
        
        # Load custom icon if it exists
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "assets", "icon.ico")
        try:
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass # Fail silently on OS that don't support .ico natively
        
        # Core State
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
        
        # UI Scaling Control
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
    # TAB 1: ARCHITECT (Interactive XML Forms)
    # ==========================================
    def _build_tab_architect(self):
        xml_tabs = ctk.CTkTabview(self.tab_arch, corner_radius=15)
        xml_tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        tab_req = xml_tabs.add("RequirementsAnalysis")
        tab_tech = xml_tabs.add("Technology")
        tab_plan = xml_tabs.add("DevelopmentPlan")

        self._build_form_requirements(tab_req)
        self._build_form_technology(tab_tech)
        self._build_form_plan(tab_plan)

        btn_frame = ctk.CTkFrame(self.tab_arch, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="Generate/Update XML Files", command=self.save_all_xmls, height=45, corner_radius=15, font=ctk.CTkFont(size=14, weight="bold")).pack(fill="x")

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
            # 1. Save Requirements
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

            # 2. Save Technology
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

            # 3. Save Development Plan
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

    # ==========================================
    # TAB 2: CONTEXT BUILDER (Filters & Selection)
    # ==========================================
    def _build_tab_context(self):
        filter_frame = ctk.CTkFrame(self.tab_ctx, corner_radius=15)
        filter_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(filter_frame, text="Allowed Extensions (comma sep):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_exts = ctk.CTkEntry(filter_frame, width=200, placeholder_text=".py, .js, .xml", corner_radius=15)
        self.entry_exts.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.entry_exts.insert(0, ".py, .xml, .md")

        ctk.CTkLabel(filter_frame, text="Ignored Dirs (comma sep):").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.entry_dirs = ctk.CTkEntry(filter_frame, width=200, placeholder_text=".git, node_modules", corner_radius=15)
        self.entry_dirs.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.entry_dirs.insert(0, ".git, __pycache__, venv, node_modules")

        ctk.CTkLabel(filter_frame, text="Ignored Files (comma sep):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_files = ctk.CTkEntry(filter_frame, width=200, placeholder_text="secrets.py, .env", corner_radius=15)
        self.entry_files.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        btn_apply = ctk.CTkButton(filter_frame, text="Apply Filters & Scan", command=self.refresh_file_list, corner_radius=15)
        btn_apply.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        body_frame = ctk.CTkFrame(self.tab_ctx, fg_color="transparent")
        body_frame.pack(fill="both", expand=True)

        self.scroll_files = ctk.CTkScrollableFrame(body_frame, label_text="Project Files", corner_radius=15)
        self.scroll_files.pack(side="left", fill="both", expand=True, padx=(0, 10))

        sidebar = ctk.CTkFrame(body_frame, width=250, corner_radius=15)
        sidebar.pack(side="right", fill="y")

        ctk.CTkButton(sidebar, text="Select All", command=self.select_all_files, corner_radius=15).pack(fill="x", padx=10, pady=(15, 5))
        ctk.CTkButton(sidebar, text="Deselect All", command=self.deselect_all_files, corner_radius=15).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(sidebar, text="Prompt Prefix:").pack(anchor="w", padx=10, pady=(20, 0))
        self.prompt_prefix = ctk.CTkTextbox(sidebar, height=100, corner_radius=15)
        self.prompt_prefix.pack(fill="x", padx=10, pady=5)
        self.prompt_prefix.insert("0.0", "Analyze the following GRACE blueprints and source code. I need to...")

        ctk.CTkButton(sidebar, text="Copy to Clipboard", command=self.copy_context, fg_color="#2b8a3e", hover_color="#216e31", corner_radius=15, height=40).pack(fill="x", padx=10, pady=20)
        
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
                if file in ["RequirementsAnalysis.xml", "Technology.xml", "DevelopmentPlan.xml"]:
                    var.set(True)

                self.file_vars[full_path] = (rel_path, var)
                
                cb = ctk.CTkCheckBox(self.scroll_files, text=rel_path, variable=var, corner_radius=5)
                cb.pack(anchor="w", padx=5, pady=4)

    def select_all_files(self):
        for _, (_, var) in self.file_vars.items(): var.set(True)

    def deselect_all_files(self):
        for _, (_, var) in self.file_vars.items(): var.set(False)

    def copy_context(self):
        context_string = self.prompt_prefix.get("0.0", "end").strip() + "\n\n"
        processed, failed = 0, 0

        for full_path, (rel_path, var) in self.file_vars.items():
            if var.get():
                try:
                    if os.path.getsize(full_path) > self.max_file_size_bytes:
                        context_string += f"--- File: {rel_path} ---\n[Omitted: Exceeds 1MB]\n\n"
                        failed += 1
                        continue

                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    lang = os.path.splitext(rel_path)[1].lower().replace('.', '')
                    if not lang: lang = 'text'
                    
                    context_string += f"--- File: {rel_path} ---\n```{lang}\n{content}\n```\n\n"
                    processed += 1
                except Exception as e:
                    context_string += f"--- File: {rel_path} ---\n[Omitted: Read error - {e}]\n\n"
                    failed += 1

        try:
            self.clipboard_clear()
            self.clipboard_append(context_string)
            self.ctx_status.configure(text=f"Copied! ({processed} ok, {failed} skipped)", text_color="#2b8a3e")
        except Exception as e:
            messagebox.showerror("Clipboard Error", str(e))

    # ==========================================
    # TAB 3: LDD MONITOR
    # ==========================================
    def _build_tab_ldd(self):
        top_bar = ctk.CTkFrame(self.tab_ldd, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(top_bar, text="Load agent_error.log", command=self.load_log, corner_radius=15).pack(side="left")
        
        self.log_viewer = ctk.CTkTextbox(self.tab_ldd, font=ctk.CTkFont(family="Courier", size=12), corner_radius=15)
        self.log_viewer.pack(fill="both", expand=True)

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