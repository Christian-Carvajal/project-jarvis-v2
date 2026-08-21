# Project JARVIS — Performance Benchmarks & Evaluation Suite

This directory contains standardized benchmark scripts, evaluation datasets, and recorded evaluation results for comparing baseline pre-trained models against fine-tuned LoRA weights.

---

## 📁 Directory Structure

```
benchmarks/
├── baseline_qwen3.5_2b_results.json    # Full raw evaluation results for baseline qwen3.5:2b
└── README.md                           # Benchmark documentation and comparative summary
```

---

## 📊 Summary of Benchmark Results

### Baseline vs. Fine-Tuned Comparison Matrix

| Evaluation Dimension | Baseline `qwen3.5:2b` (Pre-Trained) | Fine-Tuned Model (`jarvis-custom`) | Improvement ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **JSON Validity Rate** | **100.0%** (15/15) | *Pending Evaluation* | — |
| **Action Schema Accuracy** | **100.0%** (12/12) | *Pending Evaluation* | — |
| **Chit-Chat Null Accuracy** | **66.7%** (2/3) | *Target: 100.0%* | — |
| **Overall Score** | **93.3%** (14/15) | *Target: 100.0%* | — |
| **Avg Inference Latency** | **10.11 s** | *Pending Evaluation* | — |
| **Avg Generation Speed** | **47.7 tok/s** | *Pending Evaluation* | — |

---

## 🚀 Running the Benchmarks

### 1. Run Baseline Benchmark
To benchmark any model running in local Ollama:
```powershell
python benchmark_baseline.py qwen3.5:2b
```

### 2. Run Fine-Tuned Model Benchmark
```powershell
python benchmark_baseline.py jarvis-custom
```

### 3. Detailed Results Documentation
See [`docs/baseline_benchmark_results.md`](../docs/baseline_benchmark_results.md) for full trace logs and qualitative evaluation details.
