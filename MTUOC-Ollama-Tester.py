import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
from ollama_engine import OllamaModelEngine

class OllamaAppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MTUOC Ollama Tester")
        self.root.geometry("1100x1200")
        
        # Carreguem el motor amb el fitxer de configuració unificat
        self.engine = OllamaModelEngine("config.yaml")
        self.setup_ui()
        
        # Iniciem la connexió i verificació de model en segon pla
        threading.Thread(target=self.startup_sequence, daemon=True).start()

    def startup_sequence(self):
        # El motor ara gestiona si el servidor està running i el pull del model
        if self.engine.initialize_client(self.update_button_status):
            self.engine.ensure_model_exists(self.update_button_status)

    def setup_ui(self):
        main_frame = tk.Frame(self.root, padx=20, pady=10)
        main_frame.pack(fill="both", expand=True)

        # Secció de Rols (System i Assistant)
        role_frame = tk.Frame(main_frame)
        role_frame.pack(fill="x", pady=5)
        role_frame.columnconfigure(0, weight=1); role_frame.columnconfigure(1, weight=1)

        sys_f = tk.LabelFrame(role_frame, text=" System Role ", padx=5, pady=5)
        sys_f.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.system_txt = scrolledtext.ScrolledText(sys_f, height=4, font=("Consolas", 9))
        self.system_txt.pack(fill="both")

        ast_f = tk.LabelFrame(role_frame, text=" Assistant Context ", padx=5, pady=5)
        ast_f.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.assistant_txt = scrolledtext.ScrolledText(ast_f, height=4, font=("Consolas", 9))
        self.assistant_txt.pack(fill="both")

        # User Prompt
        tk.Label(main_frame, text="USER PROMPT", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.prompt_in = scrolledtext.ScrolledText(main_frame, height=8, font=("Consolas", 11))
        self.prompt_in.pack(fill="both", pady=5)

        # Botó dinàmic d'estat
        self.btn_gen = tk.Button(main_frame, text="CONNECTING...", bg="#9E9E9E", fg="white", 
                                 state="disabled", font=("Arial", 11, "bold"), pady=12, command=self.on_generate)
        self.btn_gen.pack(fill="x", pady=10)

        # Resposta Bruta i Regex
        tk.Label(main_frame, text="RAW RESPONSE").pack(anchor="w")
        self.raw_out = scrolledtext.ScrolledText(main_frame, height=8, bg="#F5F5F5", font=("Consolas", 10))
        self.raw_out.pack(fill="both", pady=5)

        reg_frame = tk.LabelFrame(main_frame, text=" Regex Filter ", padx=10, pady=10)
        reg_frame.pack(fill="x", pady=10)
        self.reg_entry = tk.Entry(reg_frame, font=("Consolas", 11))
        self.reg_entry.pack(fill="x")
        # Obtenim el regex del nou bloc prompt_settings
        self.reg_entry.insert(0, self.engine.config.get('prompt_settings', {}).get('regex_pattern', ""))

        tk.Label(main_frame, text="FINAL RESULT", fg="#2E7D32", font=("Arial", 10, "bold")).pack(anchor="w")
        self.final_out = scrolledtext.ScrolledText(main_frame, height=6, bg="#F1F8E9", font=("Consolas", 12, "bold"))
        self.final_out.pack(fill="both", expand=True, pady=5)

    def update_button_status(self, status):
        self.root.after(0, self._update_ui, status)

    def _update_ui(self, status):
        if status == "READY":
            model = self.engine.config['ollama_settings'].get('model', 'model')
            self.btn_gen.config(state="normal", text=f"GENERATE WITH {model.upper()}", bg="#4CAF50")
        elif "DOWNLOADING" in status or "PULLING" in status or "CONNECTANT" in status:
            self.btn_gen.config(state="disabled", text=status, bg="#2196F3")
        elif "ERROR" in status:
            self.btn_gen.config(state="disabled", text=status, bg="#F44336")
        else:
            self.btn_gen.config(state="disabled", text=status, bg="#9E9E9E")

    def on_generate(self):
        prompt = self.prompt_in.get("1.0", "end").strip()
        system = self.system_txt.get("1.0", "end").strip()
        assistant = self.assistant_txt.get("1.0", "end").strip()
        regex = self.reg_entry.get().strip()
        
        if not prompt: return

        def run():
            self.btn_gen.config(state="disabled", text="GENERATING...", bg="#FF9800")
            # El mètode generate ara rep els rols i el regex opcional
            raw, final = self.engine.generate(prompt, system, assistant, override_regex=regex)
            
            self.raw_out.delete("1.0", "end"); self.raw_out.insert("end", raw)
            self.final_out.delete("1.0", "end"); self.final_out.insert("end", final)
            self.update_button_status("READY")

        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk(); app = OllamaAppGUI(root); root.mainloop()
