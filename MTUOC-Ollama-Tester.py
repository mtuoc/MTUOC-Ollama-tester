import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import threading
from ollama_engine import OllamaModelEngine

class OllamaAppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MTUOC Ollama Tester Pro")
        self.root.geometry("1500x1200") # Mida inicial suggerida
        
        self.engine = OllamaModelEngine("config.yaml")
        
        self.setup_scrollable_ui()
        threading.Thread(target=self.startup_sequence, daemon=True).start()

    def setup_scrollable_ui(self):
        """Crea una base amb scrollbar on anirà tota la GUI."""
        # 1. Contenidor principal i Canvas
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.main_container, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview)
        
        # 2. El frame que realment contindrà els ginys
        self.scrollable_frame = tk.Frame(self.canvas, padx=20, pady=10)

        # Configuració del scroll
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Ajustar l'amplada del frame intern a la del canvas
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # 3. Empaquetar el sistema de scroll
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # 4. Ara cridem a la creació dels components dins de scrollable_frame
        self.build_widgets(self.scrollable_frame)

    def on_canvas_configure(self, event):
        """Assegura que el contingut s'estiri horitzontalment per ocupar el canvas."""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def build_widgets(self, parent):
        """Aquí va tota la teva interfície anterior, però penjant de 'parent'."""
        # Secció Rols
        role_frame = tk.Frame(parent)
        role_frame.pack(fill="x", pady=5)
        role_frame.columnconfigure(0, weight=1); role_frame.columnconfigure(1, weight=1)

        sys_f = tk.LabelFrame(role_frame, text=" System Role ", padx=5, pady=5)
        sys_f.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.system_txt = scrolledtext.ScrolledText(sys_f, height=5, font=("Consolas", 10))
        self.system_txt.pack(fill="both")

        ast_f = tk.LabelFrame(role_frame, text=" Assistant Context ", padx=5, pady=5)
        ast_f.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.assistant_txt = scrolledtext.ScrolledText(ast_f, height=5, font=("Consolas", 10))
        self.assistant_txt.pack(fill="both")

        # User Prompt
        tk.Label(parent, text="USER PROMPT", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.prompt_in = scrolledtext.ScrolledText(parent, height=10, font=("Consolas", 11))
        self.prompt_in.pack(fill="both", pady=5)

        # Botó
        self.btn_gen = tk.Button(parent, text="CONNECTING...", bg="#9E9E9E", fg="white", 
                                 state="disabled", font=("Arial", 11, "bold"), pady=12, command=self.on_generate)
        self.btn_gen.pack(fill="x", pady=10)

        # Respostes
        tk.Label(parent, text="RAW RESPONSE").pack(anchor="w")
        self.raw_out = scrolledtext.ScrolledText(parent, height=10, bg="#F5F5F5", font=("Consolas", 10))
        self.raw_out.pack(fill="both", pady=5)

        reg_frame = tk.LabelFrame(parent, text=" Regex Filter ", padx=10, pady=10)
        reg_frame.pack(fill="x", pady=10)
        self.reg_entry = tk.Entry(reg_frame, font=("Consolas", 11))
        self.reg_entry.pack(fill="x")
        
        if self.engine.config:
            initial_regex = self.engine.config.get('prompt_settings', {}).get('regex_pattern', "")
            self.reg_entry.insert(0, initial_regex)

        tk.Label(parent, text="FINAL RESULT", fg="#2E7D32", font=("Arial", 10, "bold")).pack(anchor="w")
        self.final_out = scrolledtext.ScrolledText(parent, height=8, bg="#F1F8E9", font=("Consolas", 12, "bold"))
        self.final_out.pack(fill="both", pady=5)

    # --- La resta de mètodes es mantenen igual ---
    def startup_sequence(self):
        if self.engine.initialize_client(self.update_button_status):
            self.engine.ensure_model_exists(self.update_button_status)

    def update_button_status(self, status):
        self.root.after(0, self._update_ui, status)

    def _update_ui(self, status):
        if status == "READY":
            m = self.engine.config['ollama_settings'].get('model', 'model')
            self.btn_gen.config(state="normal", text=f"GENERATE WITH {m.upper()}", bg="#4CAF50")
        elif any(x in status for x in ["DOWNLOADING", "CONNECTANT", "REVISANT"]):
            self.btn_gen.config(state="disabled", text=status, bg="#2196F3")
        elif "ERROR" in status:
            self.btn_gen.config(state="disabled", text=status, bg="#F44336")
        else:
            self.btn_gen.config(state="disabled", text=status, bg="#9E9E9E")

    def on_generate(self):
        p = self.prompt_in.get("1.0", "end").strip()
        s = self.system_txt.get("1.0", "end").strip()
        a = self.assistant_txt.get("1.0", "end").strip()
        r = self.reg_entry.get().strip()
        if not p: return

        def run():
            self.btn_gen.config(state="disabled", text="GENERATING...", bg="#FF9800")
            raw, final = self.engine.generate(p, s, a, override_regex=r)
            self.raw_out.delete("1.0", "end"); self.raw_out.insert("end", raw)
            self.final_out.delete("1.0", "end"); self.final_out.insert("end", final)
            self.update_button_status("READY")

        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk(); app = OllamaAppGUI(root); root.mainloop()
