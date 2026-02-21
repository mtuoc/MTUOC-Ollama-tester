import ollama
import json
import re
import yaml
import subprocess
import time
import requests

class OllamaModelEngine:
    def __init__(self, config_path="config.yaml"):
        self.config = self.load_config(config_path)
        self.client = None

    def load_config(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error carregant YAML: {e}")
            return None

    def initialize_client(self, status_callback=None):
        if not self.config: return False
        o_cfg = self.config.get('ollama_settings', {})
        host = o_cfg.get('host', o_cfg.get('url', "http://localhost:11434"))
        timeout = o_cfg.get('timeout', 5)

        if status_callback: status_callback("Comprovant servidor Ollama...")
        
        try:
            requests.get(host, timeout=timeout)
        except:
            if status_callback: status_callback("Intentant aixecar el servidor...")
            try:
                subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(4) 
            except Exception:
                if status_callback: status_callback("ERROR: Comanda 'ollama' no trobada.")
                return False

        try:
            self.client = ollama.Client(host=host)
            self.client.list()
            if status_callback: status_callback("Servidor connectat.")
            return True
        except Exception:
            if status_callback: status_callback("ERROR de connexió")
            return False

    def ensure_model_exists(self, status_callback=None):
        o_cfg = self.config.get('ollama_settings', {})
        model_name = o_cfg.get('model')
        
        if not model_name:
            if status_callback: status_callback("ERROR: Model no definit.")
            return False
            
        try:
            if status_callback: status_callback(f"Verificant model: '{model_name}'...")
            
            # Fem el pull i capturem el progrés
            for chunk in self.client.pull(model=model_name, stream=True):
                status = chunk.get("status", "")
                completed = chunk.get("completed") # Pot ser None
                total = chunk.get("total")         # Pot ser None
                
                # Verifiquem que ambdós valors existeixin i siguin números abans de calcular
                if isinstance(completed, int) and isinstance(total, int) and total > 0:
                    percent = int((completed / total) * 100)
                    if status_callback: status_callback(f"DOWNLOADING: {percent}%")
                elif status:
                    # Si no hi ha números, mostrem el text de l'estat (ex: "verifying sha256")
                    if status_callback: status_callback(status.upper())
            
            if status_callback: status_callback("READY")
            return True
        except Exception as e:
            error_msg = str(e)
            print(f"DEBUG: Error real d'Ollama: {error_msg}")
            if status_callback: status_callback(f"ERROR: {error_msg[:20]}")
            return False

    def generate(self, prompt, system_prompt="", assistant_context="", override_regex=None):
        if not self.client: return "Error: Client no connectat.", ""
        
        o_cfg = self.config.get('ollama_settings', {})
        g_cfg = self.config.get('generation_params', o_cfg)
        
        # Filtrem claus no vàlides per a les opcions de xat
        forbidden = ['model', 'url', 'host', 'timeout']
        options = {k: v for k, v in g_cfg.items() if k not in forbidden and v is not None}
        
        messages = []
        if system_prompt: messages.append({'role': 'system', 'content': system_prompt})
        if assistant_context: messages.append({'role': 'assistant', 'content': assistant_context})
        messages.append({'role': 'user', 'content': prompt})

        try:
            response = self.client.chat(model=o_cfg.get('model'), messages=messages, options=options)
            raw_text = response['message']['content'].strip()
            return raw_text, self.post_process(raw_text, override_regex)
        except Exception as e:
            return f"ERROR GENERACIÓ: {str(e)}", ""

    def post_process(self, text, override_regex=None):
        processed = text
        p_cfg = self.config.get('prompt_settings', {})
        regex_pattern = override_regex if override_regex else p_cfg.get('regex_pattern', "None")
        if regex_pattern and regex_pattern != "None":
            try:
                match = re.search(regex_pattern, processed, re.MULTILINE | re.DOTALL)
                if match:
                    processed = match.group(1).strip() if match.groups() else match.group(0).strip()
            except: pass
        return processed
