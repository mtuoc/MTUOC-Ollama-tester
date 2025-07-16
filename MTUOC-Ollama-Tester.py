#    MTUOC-Ollama-tester v2507
#    Copyright (C) 2025  Antoni Oliver
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import tkinter as tk
from tkinter import simpledialog, messagebox
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading
import time
import requests
import ollama
import re
import json

OLLAMA_URL = "http://localhost:11434"

def check_ollama_running():
    try:
        requests.get(f"{OLLAMA_URL}/tags", timeout=1)
        return True
    except requests.exceptions.RequestException:
        return False

def start_ollama_server():
    subprocess.Popen(["ollama", "serve"])
    for _ in range(10):
        if check_ollama_running():
            return True
        time.sleep(1)
    return False

def get_installed_models():
    try:
        models = ollama.list().models
        return [model.model for model in models]
    except Exception as e:
        messagebox.showerror("Error", f"No es poden obtenir els models: {e}")
        return []

class OllamaApp:
    def __init__(self, master):
        self.master = master

        # ──── Model selection ────
        model_frame = tk.Frame(master)
        model_frame.pack(pady=10, fill="x")

        tk.Label(model_frame, text="Model:").grid(row=0, column=0, sticky="w")
        self.model_var = tk.StringVar(master)
        self.model_menu = tk.OptionMenu(model_frame, self.model_var, "")
        self.model_menu.grid(row=0, column=1, padx=5)

        tk.Button(model_frame, text="Refresh", command=self.load_models).grid(row=0, column=2, padx=5)
        tk.Button(model_frame, text="Install new", command=self.install_model).grid(row=0, column=3, padx=5)

        # ──── Parameters ────
        param_frame = tk.LabelFrame(master, text="Parameters", padx=10, pady=5)
        param_frame.pack(pady=10, fill="x")

        self.params = {
            "temperature": tk.DoubleVar(value=0.9),
            "top_p": tk.DoubleVar(value=0.9),
            "top_k": tk.IntVar(value=40),
            "repeat_penalty": tk.DoubleVar(value=1.1),
            "seed": tk.StringVar(value=""),
            "num_predict": tk.IntVar(value=-1),
            "as_json": tk.BooleanVar(value=False)
        }

        param_keys = list(self.params.keys())
        param_layout = param_keys[:-1]  # exclude as_json

        for i in range(0, len(param_layout), 2):
            param1 = param_layout[i]
            var1 = self.params[param1]
            tk.Label(param_frame, text=param1).grid(row=i//2, column=0, sticky="w")
            tk.Entry(param_frame, textvariable=var1, width=10).grid(row=i//2, column=1, padx=5, pady=2, sticky="w")

            if i + 1 < len(param_layout):
                param2 = param_layout[i+1]
                var2 = self.params[param2]
                tk.Label(param_frame, text=param2).grid(row=i//2, column=2, sticky="w")
                tk.Entry(param_frame, textvariable=var2, width=10).grid(row=i//2, column=3, padx=5, pady=2, sticky="w")

        tk.Checkbutton(
            param_frame,
            text="Show full JSON response",
            variable=self.params["as_json"]
        ).grid(row=(len(param_layout)+1)//2, column=0, columnspan=4, sticky="w", pady=5)

        # ──── Chat messages ────
        chat_frame = tk.LabelFrame(master, text="Chat Messages", padx=10, pady=5)
        chat_frame.pack(padx=10, pady=10, fill="both", expand=True)

        tk.Label(chat_frame, text="role: system").pack(anchor="w")
        self.system_text = ScrolledText(chat_frame, height=4)
        self.system_text.pack(fill="both", padx=5, pady=2)

        tk.Label(chat_frame, text="role: user").pack(anchor="w")
        self.user_text = ScrolledText(chat_frame, height=4)
        self.user_text.pack(fill="both", padx=5, pady=2)

        tk.Label(chat_frame, text="role: assistant").pack(anchor="w")
        self.assistant_text = ScrolledText(chat_frame, height=4)
        self.assistant_text.pack(fill="both", padx=5, pady=2)

        tk.Label(chat_frame, text="Response").pack(anchor="w")
        self.response_text = ScrolledText(chat_frame, height=10)
        self.response_text.pack(fill="both", padx=5, pady=2)

        # ──── Botons just despres de Chat Messages ────
        button_frame = tk.Frame(master)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Send", command=self.send_prompt).pack(side="left", padx=10)
        tk.Button(button_frame, text="Clear", command=self.clear_all).pack(side="left", padx=10)

        # ──── Regular Expression ────
        regexp_frame = tk.LabelFrame(master, text="Regular Expression", padx=10, pady=5)
        regexp_frame.pack(padx=10, pady=10, fill="both", expand=False)

        tk.Label(regexp_frame, text="Regular expression").pack(anchor="w")
        self.regexp_entry = tk.Entry(regexp_frame)
        self.regexp_entry.pack(fill="x", padx=5, pady=2)

        tk.Label(regexp_frame, text="Result").pack(anchor="w")
        self.regexp_result = ScrolledText(regexp_frame, height=6)
        self.regexp_result.pack(fill="both", padx=5, pady=2)

        tk.Button(regexp_frame, text="Apply regexp", command=self.apply_regexp).pack(pady=5)

        self.load_models()

    def load_models(self):
        models = get_installed_models()
        models.append("Install new...")

        menu = self.model_menu["menu"]
        menu.delete(0, "end")

        for model in models:
            menu.add_command(label=model, command=lambda m=model: self.model_var.set(m))

        self.model_var.set(models[0] if models else "")

    def install_model(self):
        model_name = simpledialog.askstring("Install Model", "Enter model name (e.g., llama3, mistral):")
        if model_name:
            try:
                subprocess.run(["ollama", "pull", model_name], check=True)
                messagebox.showinfo("Success", f"Model '{model_name}' installed.")
                self.load_models()
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Error", f"Failed to install model: {e}")

    def send_prompt(self):
        model_name = self.model_var.get()
        if model_name == "Install new...":
            messagebox.showwarning("Warning", "Please select a valid model.")
            return

        messages = []
        if self.system_text.get("1.0", "end").strip():
            messages.append({"role": "system", "content": self.system_text.get("1.0", "end").strip()})
        if self.assistant_text.get("1.0", "end").strip():
            messages.append({"role": "assistant", "content": self.assistant_text.get("1.0", "end").strip()})
        if self.user_text.get("1.0", "end").strip():
            messages.append({"role": "user", "content": self.user_text.get("1.0", "end").strip()})
        else:
            messagebox.showwarning("Warning", "User prompt is required.")
            return

        options = {
            "model": model_name,
            "messages": messages,
            "options": {
                "temperature": self.params["temperature"].get(),
                "top_p": self.params["top_p"].get(),
                "top_k": self.params["top_k"].get(),
                "repeat_penalty": self.params["repeat_penalty"].get(),
                "num_predict": self.params["num_predict"].get()
            }
        }

        seed_value = self.params["seed"].get()
        if seed_value.strip().isdigit():
            options["options"]["seed"] = int(seed_value)

        try:
            response = ollama.chat(**options)
            self.response_text.delete("1.0", "end")

            if self.params["as_json"].get():
                if hasattr(response, "model_dump"):
                    data = response.model_dump()
                elif hasattr(response, "dict"):
                    data = response.dict()
                else:
                    data = dict(response)
                self.response_text.insert("end", json.dumps(data, indent=2))
            else:
                content = response['message']['content']
                self.response_text.insert("end", content)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get response: {e}")

    def clear_all(self):
        self.system_text.delete("1.0", "end")
        self.user_text.delete("1.0", "end")
        self.assistant_text.delete("1.0", "end")
        self.response_text.delete("1.0", "end")
        self.regexp_entry.delete(0, "end")
        self.regexp_result.delete("1.0", "end")

    def apply_regexp(self):
        pattern = self.regexp_entry.get().strip()
        text = self.response_text.get("1.0", "end").strip()
        self.regexp_result.delete("1.0", "end")

        if not pattern:
            self.regexp_result.insert("end", "[No regular expression provided]")
            return

        try:
            matches = re.findall(pattern, text, re.MULTILINE)
            if matches:
                if isinstance(matches[0], tuple):
                    output = "\n".join([" | ".join(m) for m in matches])
                else:
                    output = "\n".join(matches)
            else:
                output = "[No matches found]"
            self.regexp_result.insert("end", output)
        except re.error as e:
            self.regexp_result.insert("end", f"[Invalid regular expression]: {e}")

def launch_app():
    if not check_ollama_running():
        print("Starting Ollama server...")
        if not start_ollama_server():
            messagebox.showerror("Error", "Ollama server did not start.")
            return

    root = tk.Tk()
    root.title("MTUOC Ollama Tester")
    root.geometry("900x900")

    canvas = tk.Canvas(root)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    OllamaApp(scrollable_frame)

    root.mainloop()

if __name__ == "__main__":
    threading.Thread(target=launch_app).start()
