import asyncio
import re
import os
import subprocess
import requests
from typing import AsyncGenerator, Optional, List, Dict
import ollama

class LLMManager:
    """Dynamic Ollama LLM Manager supporting asynchronous streaming, model switching, auto-pulling missing GGUF models, and offline fallback handling."""

    AVAILABLE_MODELS = {
        "ultra-fast": "qwen3.5:2b",  # Default ultra-low latency model
        "fast": "qwen3.5:4b",        # Balanced conversational model
        "task": "qwen3.5:9b",        # Structured task execution
        "reasoning": "deepseek-r1:8b" # Deep reasoning engine
    }

    SYSTEM_PROMPT = (
        "You are JARVIS, an advanced, highly intelligent local AI assistant modeled after "
        "Stark Industries technology. You possess system control, application launcher, and smart home capabilities. "
        "Respond concisely, authoritatively, and professionally. Keep conversational voice responses short and direct."
    )

    def __init__(self, model_name: str = "qwen3.5:2b", default_model_key: Optional[str] = None, base_url: str = "http://localhost:11434"):
        target = default_model_key or model_name
        self.base_url = base_url
        self.active_model = self.AVAILABLE_MODELS.get(target, target)
        self.client = ollama.AsyncClient(host=base_url)
        self.is_online = False
        self.check_and_provision_model()

    @property
    def model_name(self) -> str:
        return self.active_model

    @model_name.setter
    def model_name(self, value: str):
        self.set_model(value)

    def check_and_provision_model(self):
        """Checks if Ollama service is reachable and auto-pulls the default model if missing."""
        try:
            resp = requests.get(f"{self.base_url.rstrip('/')}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                self.is_online = True
                models_data = resp.json().get("models", [])
                installed_names = [m.get("name", "").split(":")[0] for m in models_data]
                full_installed = [m.get("name", "") for m in models_data]

                base_active = self.active_model.split(":")[0]
                if self.active_model not in full_installed and base_active not in installed_names:
                    print(f"[SYSTEM]: Model '{self.active_model}' not found locally. Auto-downloading via Ollama in background...")
                    subprocess.Popen(["ollama", "pull", self.active_model], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    print(f"[LLM Manager]: Model '{self.active_model}' verified active on Ollama.")
            else:
                self.is_online = False
        except Exception as e:
            self.is_online = False
            print(f"[LLM Manager Notice]: Ollama service unreachable at {self.base_url} ({e}). Local action pipeline active.")

    def set_model(self, model_key: str) -> str:
        """Switch active Ollama model dynamically at runtime."""
        if model_key in self.AVAILABLE_MODELS:
            self.active_model = self.AVAILABLE_MODELS[model_key]
        elif model_key in self.AVAILABLE_MODELS.values():
            self.active_model = model_key
        else:
            self.active_model = model_key

        self.check_and_provision_model()
        return self.active_model

    def _format_messages(self, prompt: str, system_override: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": system_override or self.SYSTEM_PROMPT}]
        if history:
            for turn in history:
                role = turn.get("role", "user")
                if role not in ["user", "assistant", "system"]:
                    role = "user"
                content = turn.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})
        return messages

    def generate_response(self, prompt: str, system_override: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None) -> str:
        """Synchronous generation fallback returning full response text with conversational history context."""
        if not self.is_online:
            return "Ollama AI service is offline. Local application controls, Spotify, YouTube, and system commands remain fully functional."

        messages = self._format_messages(prompt, system_override=system_override, history=history)
        try:
            resp = ollama.chat(
                model=self.active_model,
                messages=messages,
                keep_alive="1h",
                options={"num_gpu": 99, "num_thread": 8, "temperature": 0.6}
            )
            content = resp.get("message", {}).get("content", "")
            return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        except Exception as e:
            self.is_online = False
            return f"Ollama query notice ({e}). Fast-path commands are active."

    async def generate_response_async(self, prompt: str, system_override: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None, **kwargs) -> str:
        """Asynchronous wrapper offloading synchronous LLM inference to a background worker thread with history."""
        return await asyncio.to_thread(self.generate_response, prompt, system_override=system_override, history=history, **kwargs)

    async def generate_response_stream(
        self, prompt: str, system_override: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens asynchronously with multi-turn history context."""
        if not self.is_online:
            yield "Ollama service offline. Local application controls are active."
            return

        messages = self._format_messages(prompt, system_override=system_override, history=history)

        in_think_block = False
        try:
            response = await self.client.chat(
                model=self.active_model,
                messages=messages,
                stream=True,
                keep_alive="1h",  # Prevents cold-start reloads
                options={
                    "num_gpu": 99,         # Force 100% GPU layer offloading onto VRAM
                    "num_thread": 8,       # Core Ultra thread allocation
                    "temperature": 0.6,    # Low entropy for fast sampling
                    "top_k": 20,
                    "top_p": 0.8
                }
            )

            async for chunk in response:
                if hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                    content = chunk.message.content or ""
                elif isinstance(chunk, dict):
                    content = chunk.get("message", {}).get("content", "")
                else:
                    content = ""

                if not content:
                    continue

                # Strip <think> tags from Qwen 3.5 / DeepSeek-R1
                if "<think>" in content:
                    in_think_block = True
                    content = re.sub(r'<think>.*', '', content)
                if "</think>" in content:
                    in_think_block = False
                    content = re.sub(r'.*?</think>', '', content)

                if not in_think_block and content.strip():
                    yield content
        except Exception as e:
            self.is_online = False
            yield f"\n[JARVIS Core Notice: Ollama query failed ({e}). Local action engine active.]"
