import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import threading
import requests
import ollama
import re
import json

class OllamaApp:
    def __init__(self, master):
        self.master = master
        
        # Variables de control corregides
        self.ollama_url = tk.StringVar(value="http://localhost:11434")
        self.model_name = tk.StringVar()
        self.as_json = tk.BooleanVar(value=False)

        # Configuració d'estils
        self.style = ttk.Style()
        self.master.option_add('*TCombobox*Listbox.font', ('Segoe UI', 10))
        
        self.setup_ui()
        self.load_models()

    def setup_ui(self):
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(4, weight=1) 

        # 1. Secció Superior
        top_frame = tk.LabelFrame(self.master, text="Model & Connection", padx=15, pady=5)
        top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=2)
        top_frame.columnconfigure(1, weight=1)

        tk.Label(top_frame, text="Model:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, padx=5, sticky="w")
        self.model_combo = ttk.Combobox(top_frame, textvariable=self.model_name, font=('Segoe UI', 10))
        self.model_combo.grid(row=0, column=1, padx=5, sticky="ew")
        
        btn_top_frame = tk.Frame(top_frame)
        btn_top_frame.grid(row=0, column=2, padx=5)
        tk.Button(btn_top_frame, text="🔄 Refresh", command=self.load_models, font=('Segoe UI', 8)).pack(side="left", padx=2)
        tk.Button(btn_top_frame, text="🌐 Set URL", command=self.set_url, font=('Segoe UI', 8), bg="#e1e1e1").pack(side="left", padx=2)

        # 2. Paràmetres
        param_frame = tk.LabelFrame(self.master, text="Parameters", padx=15, pady=5)
        param_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=2)
        self.params = {
            "temp": ("temperature", tk.DoubleVar(value=0.9)),
            "p": ("top_p", tk.DoubleVar(value=0.9)),
            "k": ("top_k", tk.IntVar(value=40)),
            "pen": ("repeat_penalty", tk.DoubleVar(value=1.1)),
            "pred": ("num_predict", tk.IntVar(value=-1)),
            "seed": ("seed", tk.StringVar(value=""))
        }
        for i, (short, (long_name, var)) in enumerate(self.params.items()):
            tk.Label(param_frame, text=f"{long_name}:", font=('Segoe UI', 8)).grid(row=0, column=i*2, padx=(5, 2), sticky="w")
            tk.Entry(param_frame, textvariable=var, width=6, font=('Segoe UI', 9)).grid(row=0, column=i*2+1, sticky="w")
        tk.Checkbutton(param_frame, text="JSON", variable=self.as_json, font=('Segoe UI', 8, 'bold')).grid(row=0, column=12, padx=15)

        # 3. Rols (System/Assistant)
        role_frame = tk.Frame(self.master)
        role_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=2)
        role_frame.columnconfigure(0, weight=1); role_frame.columnconfigure(1, weight=1)
        
        sys_f = tk.LabelFrame(role_frame, text="System Role", padx=5, pady=2)
        sys_f.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        self.system_text = ScrolledText(sys_f, height=3, font=('Consolas', 9))
        self.system_text.pack(fill="both")

        ast_f = tk.LabelFrame(role_frame, text="Assistant Context", padx=5, pady=2)
        ast_f.grid(row=0, column=1, sticky="nsew", padx=(2, 0))
        self.assistant_text = ScrolledText(ast_f, height=3, font=('Consolas', 9))
        self.assistant_text.pack(fill="both")

        # 4. User Prompt (Ocupant tot l'ample)
        usr_f = tk.LabelFrame(self.master, text="User Prompt", padx=15, pady=5)
        usr_f.grid(row=3, column=0, sticky="ew", padx=15, pady=2)
        usr_f.columnconfigure(0, weight=1)
        self.user_text = ScrolledText(usr_f, height=4, font=('Consolas', 10))
        self.user_text.grid(row=0, column=0, sticky="ew")

        # 5. Response
        response_frame = tk.LabelFrame(self.master, text="Response", padx=15, pady=5)
        response_frame.grid(row=4, column=0, sticky="nsew", padx=15, pady=2)
        response_frame.columnconfigure(0, weight=1); response_frame.rowconfigure(0, weight=1)
        self.response_text = ScrolledText(response_frame, font=('Consolas', 10), bg="#fcfcfc")
        self.response_text.grid(row=0, column=0, sticky="nsew")

        # 6. Botons d'Acció (Botó de generació guardat en una variable per poder-lo desactivar)
        action_btn_frame = tk.Frame(self.master)
        action_btn_frame.grid(row=5, column=0, pady=5)
        self.gen_button = tk.Button(action_btn_frame, text="GENERATE TEXT", command=self.send_prompt, 
                                    bg="#4CAF50", fg="white", font=('Segoe UI', 10, 'bold'), padx=30, pady=8)
        self.gen_button.pack(side="left", padx=10)
        tk.Button(action_btn_frame, text="Clear Everything", command=self.clear_all, font=('Segoe UI', 9), padx=15).pack(side="left", padx=10)

        # 7. Regex
        regex_f = tk.LabelFrame(self.master, text="Post-processing (Regex)", padx=15, pady=5)
        regex_f.grid(row=6, column=0, sticky="ew", padx=15, pady=5)
        regex_f.columnconfigure(1, weight=1)
        tk.Label(regex_f, text="Pattern:", font=('Segoe UI', 8, 'bold')).grid(row=0, column=0)
        self.regexp_entry = tk.Entry(regex_f, font=('Consolas', 9))
        self.regexp_entry.grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(regex_f, text="Apply Filter", command=self.apply_regexp, font=('Segoe UI', 8)).grid(row=0, column=2)
        self.regexp_result = ScrolledText(regex_f, height=3, bg="#f3f3f3", font=('Consolas', 9))
        self.regexp_result.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)

    def set_url(self):
        new_url = simpledialog.askstring("Ollama URL", "URL del servidor:", initialvalue=self.ollama_url.get())
        if new_url:
            self.ollama_url.set(new_url)
            self.load_models()

    def get_client(self):
        return ollama.Client(host=self.ollama_url.get())

    def load_models(self):
        try:
            models = [m.model for m in self.get_client().list().models]
            self.model_combo['values'] = models
            if models: self.model_name.set(models[0])
        except Exception: pass

    def send_prompt(self):
        model = self.model_name.get()
        if not model: return
        
        # Desactivem el botó i canviem el text
        self.gen_button.config(state="disabled", text="GENERATING...", bg="#9e9e9e")
        
        messages = []
        if self.system_text.get("1.0", "end").strip():
            messages.append({"role": "system", "content": self.system_text.get("1.0", "end").strip()})
        if self.assistant_text.get("1.0", "end").strip():
            messages.append({"role": "assistant", "content": self.assistant_text.get("1.0", "end").strip()})
        
        u_content = self.user_text.get("1.0", "end").strip()
        if not u_content: 
            self.gen_button.config(state="normal", text="GENERATE TEXT", bg="#4CAF50")
            return
        messages.append({"role": "user", "content": u_content})

        opts = {k: v[1].get() for k, v in self.params.items() if k != 'seed'}
        s_v = self.params['seed'][1].get()
        if s_v.strip().isdigit(): opts['seed'] = int(s_v)

        def _gen():
            try:
                resp = self.get_client().chat(model=model, messages=messages, options=opts)
                self.response_text.delete("1.0", "end")
                if self.as_json.get():
                    data = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)
                    self.response_text.insert("end", json.dumps(data, indent=2))
                else:
                    self.response_text.insert("end", resp['message']['content'])
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                # Re-activem el botó quan acaba la tasca (sigui èxit o error)
                self.gen_button.config(state="normal", text="GENERATE TEXT", bg="#4CAF50")

        threading.Thread(target=_gen, daemon=True).start()

    def clear_all(self):
        for w in [self.system_text, self.user_text, self.assistant_text, self.response_text, self.regexp_result]:
            w.delete("1.0", "end")
        self.regexp_entry.delete(0, "end")

    def apply_regexp(self):
        pat = self.regexp_entry.get().strip()
        txt = self.response_text.get("1.0", "end").strip()
        self.regexp_result.delete("1.0", "end")
        if not pat: return
        try:
            matches = re.findall(pat, txt, re.MULTILINE)
            out = "\n".join([" | ".join(map(str, m)) if isinstance(m, tuple) else str(m) for m in matches])
            self.regexp_result.insert("end", out or "[Sense coincidències]")
        except Exception as e: self.regexp_result.insert("end", f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("MTUOC Ollama Tester Pro")
    root.geometry("1700x1200")
    OllamaApp(root)
    root.mainloop()
