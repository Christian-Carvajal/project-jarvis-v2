---
name: local-ai-ollama-python
description: >-
  Expert guidance, architectural patterns, and code generation for offline Local AI LLMs in Python
  using Ollama, GGUF/llama.cpp, Modelfiles, ChatML templating, Chain-of-Thought (<think>) extraction,
  and structured Pydantic v2 JSON Schema output.
  Use when building or debugging local LLM inference pipelines, interacting with Ollama REST API,
  formatting Modelfiles, handling streaming inference, or enforcing zero-hallucination agentic planning.
license: Apache-2.0
metadata:
  version: v1
  publisher: antigravity-community
---

# Local AI & Ollama Python Integration Skill

This skill provides production-grade architectural patterns and procedures for building offline, low-latency, agentic AI applications with Python and local LLMs (Ollama, llama.cpp, GGUF).

---

## 1. Core Principles of Local LLM Systems

1. **Deterministic Structured JSON**:
   - Always enforce strict schema validation (via Pydantic v2) over raw model output.
   - Use `"format": "json"` in Ollama `/api/chat` requests to force valid JSON token constraints at inference time.

2. **Native Chain-of-Thought Reasoning Separation**:
   - Modern reasoning models (Qwen 2.5/3.5, DeepSeek-R1) generate reasoning inside `<think>...</think>` tags or Ollama `thinking` fields.
   - Separate `<think>` reasoning from the JSON output to maintain UI observability while keeping schemas pure.

3. **Telemetry & Ground-Truth Context Injection**:
   - Inject live physical state (e.g., smart home telemetry, active windows, CPU/RAM stats) into the `system` message so the local model possesses real-world grounding.

4. **Resilient Timeout & Streaming Handling**:
   - Local CPU/GPU inference can experience latency spikes during prompt evaluation. Set client HTTP timeouts to >= 120s.

---

## 2. Standard Ollama Python Client Architecture

### Synchronous Client with CoT Reasoning & Schema Validation

```python
import json
import requests
from typing import Optional, Tuple, List, Any
from pydantic import BaseModel, Field

class PlannedAction(BaseModel):
    domain: str = Field(description="Target domain: 'smart_home' or 'pc_automation'")
    device_or_target: str = Field(description="Target identifier")
    action: str = Field(description="Action name")
    value: Optional[Any] = Field(default=None, description="Optional parameter")

class ModelResponsePlan(BaseModel):
    spoken_response: str
    actions: List[PlannedAction] = Field(default_factory=list)
    reasoning: Optional[str] = None

class LocalAIEngine:
    SYSTEM_PROMPT = (
        "You are an autonomous AI assistant. "
        "Reason step-by-step inside <think></think> tags before formulating your output. "
        "Output your final response strictly as valid JSON matching the schema: "
        "{\"spoken_response\": \"<text>\", \"actions\": [{\"domain\": \"<str>\", \"device_or_target\": \"<str>\", \"action\": \"<str>\", \"value\": <val|null>}]}"
    )

    def __init__(self, model_name: str = "qwen2.5:3b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def _extract_reasoning_and_json(self, raw_content: str, thinking: str = "") -> Tuple[Optional[str], str]:
        reasoning = thinking.strip() if thinking else None
        text = raw_content.strip()

        if "<think>" in text:
            start_idx = text.find("<think>")
            end_idx = text.find("</think>")
            if end_idx != -1:
                think_block = text[start_idx + len("<think>"):end_idx].strip()
                if think_block:
                    reasoning = think_block
                text = (text[:start_idx] + text[end_idx + len("</think>"):]).strip()

        # Extract first complete JSON object
        start = text.find("{")
        end = text.rfind("}")
        json_str = text[start:end+1] if start != -1 and end != -1 and end > start else "{}"
        return reasoning, json_str

    def infer(self, user_prompt: str, telemetry_context: Optional[str] = None) -> ModelResponsePlan:
        sys_msg = self.SYSTEM_PROMPT
        if telemetry_context:
            sys_msg += f"\n[Live System Telemetry]: {telemetry_context}"

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "format": "json"
            },
            timeout=120.0
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")
        thinking = data.get("message", {}).get("thinking", "")

        reasoning, clean_json = self._extract_reasoning_and_json(content, thinking)
        parsed = json.loads(clean_json)
        if reasoning:
            parsed["reasoning"] = reasoning

        return ModelResponsePlan.model_validate(parsed)
```

---

## 3. Ollama Modelfile Best Practices

```dockerfile
FROM ./models/my-model-q4_k_m.gguf

PARAMETER temperature 0.2
PARAMETER top_p 0.95
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_predict 512
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
PARAMETER stop "###"

TEMPLATE """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{{ .System }}

### Input:
{{ .Prompt }}

### Response:
"""
```
