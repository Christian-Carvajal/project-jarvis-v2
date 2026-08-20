---
name: local-llm-fine-tuning-lora
description: >-
  Procedures, dataset curation recipes, and conversion pipelines for fine-tuning local LLMs
  (Qwen, Llama, Mistral) using LoRA/QLoRA, Unsloth, HuggingFace PEFT, and exporting to quantized GGUF
  for deployment with Ollama and llama.cpp.
  Use when generating training datasets, creating JSONL/Alpaca formats, training adapters,
  quantizing models to GGUF (Q4_K_M, Q8_0), or diagnosing fine-tuning degradation.
license: Apache-2.0
metadata:
  version: v1
  publisher: antigravity-community
---

# Local LLM Fine-Tuning & GGUF Deployment Skill

This skill provides step-by-step procedures for creating high-quality synthetic datasets, fine-tuning local open-weights LLMs with LoRA/QLoRA, quantizing merged checkpoints to GGUF, and deploying to Ollama.

---

## 1. High-Precision Dataset Engineering

### Key Principles
1. **Multi-Action Diversity**: Include 1-action, 2-action, and multi-domain complex action samples.
2. **Ambiguous Environmental Grounding**: Train the model on descriptive statements (e.g., "It's dark and chilly") mapping to multiple home/PC actions.
3. **Conversational Standby & Safety Refusals**: Include zero-action samples to prevent hallucinated commands during regular chit-chat.
4. **CoT Reasoning Inclusion**: Pre-populate `<think>...</think>` tokens in training outputs for native reasoning capability.

### Dataset JSONL Format (Alpaca / Instruction Style)

```json
{"instruction": "You are JARVIS, an autonomous AI smart home assistant. Reason inside <think></think> and output JSON.", "input": "Turn on the living room light and open YouTube", "output": "<think>User wants dual-domain actions: living room light and YouTube.</think>{\"spoken_response\": \"Living room light illuminated and YouTube opened.\", \"actions\": [{\"domain\": \"smart_home\", \"device_or_target\": \"living_room_light\", \"action\": \"turn_on\", \"value\": null}, {\"domain\": \"pc_automation\", \"device_or_target\": \"youtube\", \"action\": \"open_website\", \"value\": null}]}"}
```

---

## 2. LoRA Fine-Tuning with Unsloth / Hugging Face

```python
from unsloth import FastLanguageModel
import torch
from trl import SFTTrainer
from transformers import TrainingArguments

# 1. Load 4-bit Base Model
max_seq_length = 2048
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-3B-Instruct",
    max_seq_length=max_seq_length,
    load_in_4bit=True,
)

# 2. Add LoRA Adapters
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
)

# 3. Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        max_steps=120,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=1,
        output_dir="outputs",
    ),
)
trainer.train()

# 4. Save GGUF
model.save_pretrained_gguf("jarvis_model_q4", tokenizer, quantization_method="q4_k_m")
```

---

## 3. Quantization & Ollama Deployment

1. **Export to GGUF**:
   Convert merged 16-bit float model to GGUF format using `llama.cpp/convert_hf_to_gguf.py` or Unsloth direct export.
2. **Quantize**:
   ```bash
   ./llama.cpp/llama-quantize ./models/jarvis_f16.gguf ./models/jarvis_q4_k_m.gguf Q4_K_M
   ```
3. **Register with Ollama**:
   ```bash
   ollama create jarvis-trained-model -f Modelfile
   ```
