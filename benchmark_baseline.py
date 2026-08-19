"""
=============================================================================
Project JARVIS — Qwen 3.5 (2B) Baseline Benchmark & Evaluation Suite
=============================================================================
Automated evaluation harness to benchmark baseline 'qwen3.5:2b' performance
across Direct IoT, Ambiguous Contextual Commands, PC Automation, and Chit-Chat.
Saves comprehensive metrics to 'benchmarks/baseline_qwen3.5_2b_results.json'.
=============================================================================
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ai_engine import AIEngine, AssistantIntentResponse, DeviceAction


# -----------------------------------------------------------------------------
# 15 Standardized Evaluation Test Cases
# -----------------------------------------------------------------------------
BENCHMARK_TEST_SUITE = [
    # 1. Direct IoT Controls (4 Test Cases)
    {
        "id": "IOT-01",
        "category": "Direct IoT Controls",
        "prompt": "Turn on living room light",
        "expected_domain": "smart_home",
        "expected_target": "living_room_light",
        "expected_action": "turn_on",
        "is_chitchat": False,
        "description": "Explicit lighting activation command"
    },
    {
        "id": "IOT-02",
        "category": "Direct IoT Controls",
        "prompt": "Set temperature to 20",
        "expected_domain": "smart_home",
        "expected_target": "thermostat",
        "expected_action": "set_temperature",
        "expected_value": 20,
        "is_chitchat": False,
        "description": "Explicit climate thermostat temperature set point"
    },
    {
        "id": "IOT-03",
        "category": "Direct IoT Controls",
        "prompt": "Lock the front door",
        "expected_domain": "smart_home",
        "expected_target": "front_door_lock",
        "expected_action": "lock",
        "is_chitchat": False,
        "description": "Explicit perimeter smart lock actuation"
    },
    {
        "id": "IOT-04",
        "category": "Direct IoT Controls",
        "prompt": "Turn off kitchen light",
        "expected_domain": "smart_home",
        "expected_target": "kitchen_light",
        "expected_action": "turn_off",
        "is_chitchat": False,
        "description": "Explicit secondary room lighting deactivation"
    },

    # 2. Contextual / Ambiguous Commands (4 Test Cases)
    {
        "id": "CTX-01",
        "category": "Contextual / Ambiguous Commands",
        "prompt": "It's freezing and dark in here",
        "expected_domain": "smart_home",
        "expected_target": "thermostat",
        "expected_action": "set_temperature",
        "is_chitchat": False,
        "description": "Ambiguous multi-device comfort reasoning (thermostat + lights)"
    },
    {
        "id": "CTX-02",
        "category": "Contextual / Ambiguous Commands",
        "prompt": "I'm heading to sleep",
        "expected_domain": "smart_home",
        "expected_target": "living_room_light",
        "expected_action": "turn_off",
        "is_chitchat": False,
        "description": "Night routine intent reasoning (lights off / lock door)"
    },
    {
        "id": "CTX-03",
        "category": "Contextual / Ambiguous Commands",
        "prompt": "Movie night mode",
        "expected_domain": "smart_home",
        "expected_target": "living_room_light",
        "expected_action": "turn_on",
        "is_chitchat": False,
        "description": "Ambiance scene reasoning (entertainment / lighting)"
    },
    {
        "id": "CTX-04",
        "category": "Contextual / Ambiguous Commands",
        "prompt": "I am leaving the house",
        "expected_domain": "smart_home",
        "expected_target": "front_door_lock",
        "expected_action": "lock",
        "is_chitchat": False,
        "description": "Departure routine intent reasoning (secure lock / pc lock)"
    },

    # 3. PC Automation (4 Test Cases)
    {
        "id": "PC-01",
        "category": "PC Automation",
        "prompt": "Launch Notepad",
        "expected_domain": "pc_automation",
        "expected_target": "notepad",
        "expected_action": "open_app",
        "is_chitchat": False,
        "description": "Native OS desktop application launch"
    },
    {
        "id": "PC-02",
        "category": "PC Automation",
        "prompt": "Open YouTube and search for classical music",
        "expected_domain": "pc_automation",
        "expected_target": "youtube",
        "expected_action": "open_website",
        "expected_value": "classical music",
        "is_chitchat": False,
        "description": "Browser web navigation with search parameter extraction"
    },
    {
        "id": "PC-03",
        "category": "PC Automation",
        "prompt": "Open Spotify",
        "expected_domain": "pc_automation",
        "expected_target": "spotify",
        "expected_action": "open_app",
        "is_chitchat": False,
        "description": "Desktop media player launch"
    },
    {
        "id": "PC-04",
        "category": "PC Automation",
        "prompt": "Lock my computer",
        "expected_domain": "pc_automation",
        "expected_target": "lock_pc",
        "expected_action": "lock_pc",
        "is_chitchat": False,
        "description": "Operating system workstation security lock"
    },

    # 4. Conversational Standby / Chit-Chat (3 Test Cases)
    {
        "id": "CHAT-01",
        "category": "Conversational Standby / Chit-Chat",
        "prompt": "Hello Jarvis, how are you today?",
        "is_chitchat": True,
        "description": "Conversational greeting expecting zero false device activations"
    },
    {
        "id": "CHAT-02",
        "category": "Conversational Standby / Chit-Chat",
        "prompt": "Thank you for your help",
        "is_chitchat": True,
        "description": "Polite conversational closing with null action plan"
    },
    {
        "id": "CHAT-03",
        "category": "Conversational Standby / Chit-Chat",
        "prompt": "Who created you?",
        "is_chitchat": True,
        "description": "Identity inquiry with null action plan"
    }
]


def run_benchmark(model_name: str = "qwen3.5:2b") -> Dict[str, Any]:
    """
    Executes the 15-case evaluation benchmark against the baseline LLM.
    Collects JSON validity, schema compliance, chit-chat null actions, latency, and throughput.
    """
    ai_engine = AIEngine(model_name=model_name)
    resolved_model = ai_engine.model_name

    print("=" * 80, flush=True)
    print(f"  [BENCHMARK] PROJECT JARVIS -- BASELINE EVALUATION SUITE", flush=True)
    print(f"  [TARGET]    Target Model: {resolved_model} (Ollama Endpoint)", flush=True)
    print(f"  [DATE]      Timestamp:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"  [CASES]     Test Cases:   {len(BENCHMARK_TEST_SUITE)} Standardized Scenarios", flush=True)
    print("=" * 80, flush=True)

    results_data = []
    
    valid_json_count = 0
    schema_accurate_count = 0
    chitchat_null_accurate_count = 0
    total_chitchat_count = 0
    total_actionable_count = 0

    latencies = []
    tokens_per_second_list = []
    total_tokens_evaluated = 0

    for idx, test in enumerate(BENCHMARK_TEST_SUITE, 1):
        test_id = test["id"]
        category = test["category"]
        prompt = test["prompt"]
        is_chitchat = test["is_chitchat"]

        if is_chitchat:
            total_chitchat_count += 1
        else:
            total_actionable_count += 1

        print(f"\n[{idx:02d}/15] [{test_id}] Category: {category}", flush=True)
        print(f"      Prompt: \"{prompt}\"", flush=True)

        start_time = time.time()
        plan: AssistantIntentResponse = ai_engine.parse_command(prompt)
        elapsed_sec = time.time() - start_time
        latency_ms = elapsed_sec * 1000
        latencies.append(latency_ms)

        # Token execution metrics
        eval_count = plan.eval_count or 0
        eval_duration_ms = plan.eval_duration_ms or latency_ms
        tps = (eval_count / (eval_duration_ms / 1000.0)) if (eval_count and eval_duration_ms > 0) else 0.0
        if tps > 0:
            tokens_per_second_list.append(tps)
        total_tokens_evaluated += eval_count

        # 1. JSON Validity Evaluation
        is_valid_json = isinstance(plan, AssistantIntentResponse) and plan.interpreted_intent != "offline_fallback"
        if is_valid_json:
            valid_json_count += 1

        # 2. Schema Compliance & Intent Accuracy
        is_schema_accurate = False
        if is_valid_json:
            if is_chitchat:
                # Chit-Chat should produce empty actions
                if len(plan.actions) == 0:
                    is_schema_accurate = True
                    chitchat_null_accurate_count += 1
            else:
                # Actionable commands should produce at least one matching action
                if len(plan.actions) > 0:
                    exp_domain = test.get("expected_domain")
                    exp_target = test.get("expected_target")
                    exp_action = test.get("expected_action")

                    for act in plan.actions:
                        act_domain = act.domain
                        act_target = act.device_or_target
                        act_action = act.action

                        # Verification of domain and key entity
                        if exp_domain and act_domain == exp_domain:
                            if exp_target in act_target or act_target in exp_target:
                                is_schema_accurate = True
                                break
                            elif exp_action and exp_action in act_action:
                                is_schema_accurate = True
                                break
                        elif not exp_domain and len(plan.actions) > 0:
                            is_schema_accurate = True
                            break

        if is_schema_accurate and not is_chitchat:
            schema_accurate_count += 1

        status_str = "PASS" if is_schema_accurate else "FAIL"
        action_summary = [f"[{a.domain}] {a.device_or_target}.{a.action}" for a in plan.actions] if plan.actions else ["(none)"]

        print(f"      Result:   [{status_str}] Latency: {latency_ms:.1f} ms | TPS: {tps:.1f} tok/s", flush=True)
        print(f"      Actions:  {action_summary}", flush=True)
        print(f"      Spoken:   \"{plan.spoken_response}\"", flush=True)

        results_data.append({
            "test_id": test_id,
            "category": category,
            "prompt": prompt,
            "description": test["description"],
            "is_chitchat": is_chitchat,
            "json_valid": is_valid_json,
            "schema_accurate": is_schema_accurate,
            "latency_ms": round(latency_ms, 2),
            "tokens_evaluated": eval_count,
            "tokens_per_second": round(tps, 2),
            "spoken_response": plan.spoken_response,
            "actions_generated": [a.model_dump() for a in plan.actions],
            "interpreted_intent": plan.interpreted_intent
        })

    # -------------------------------------------------------------------------
    # Aggregate Metrics Computation
    # -------------------------------------------------------------------------
    total_tests = len(BENCHMARK_TEST_SUITE)
    json_validity_rate = (valid_json_count / total_tests) * 100.0
    action_accuracy_rate = (schema_accurate_count / total_actionable_count) * 100.0 if total_actionable_count else 0.0
    chitchat_accuracy_rate = (chitchat_null_accurate_count / total_chitchat_count) * 100.0 if total_chitchat_count else 0.0
    overall_accuracy_rate = ((schema_accurate_count + chitchat_null_accurate_count) / total_tests) * 100.0

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    avg_tps = sum(tokens_per_second_list) / len(tokens_per_second_list) if tokens_per_second_list else 0.0

    summary = {
        "benchmark_metadata": {
            "model_evaluated": resolved_model,
            "benchmark_name": "Project JARVIS Baseline Evaluation",
            "timestamp": datetime.now().isoformat(),
            "total_test_cases": total_tests,
            "actionable_cases": total_actionable_count,
            "chitchat_cases": total_chitchat_count
        },
        "metrics": {
            "json_validity_rate_pct": round(json_validity_rate, 2),
            "action_schema_accuracy_pct": round(action_accuracy_rate, 2),
            "chitchat_null_action_accuracy_pct": round(chitchat_accuracy_rate, 2),
            "overall_accuracy_pct": round(overall_accuracy_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_tokens_per_sec": round(avg_tps, 2),
            "total_tokens_evaluated": total_tokens_evaluated
        },
        "detailed_results": results_data
    }

    # -------------------------------------------------------------------------
    # Console Summary Table
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80, flush=True)
    print("  [REPORT] BASELINE BENCHMARK SUMMARY REPORT", flush=True)
    print("=" * 80, flush=True)
    print(f"  Model Tested:                     {resolved_model}", flush=True)
    print(f"  Total Scenarios Evaluated:        {total_tests}", flush=True)
    print(f"  JSON Validity Rate:               {json_validity_rate:.1f}% ({valid_json_count}/{total_tests})", flush=True)
    print(f"  Action Schema Accuracy:           {action_accuracy_rate:.1f}% ({schema_accurate_count}/{total_actionable_count})", flush=True)
    print(f"  Chit-Chat Null-Action Accuracy:   {chitchat_accuracy_rate:.1f}% ({chitchat_null_accurate_count}/{total_chitchat_count})", flush=True)
    print(f"  Overall Benchmark Score:          {overall_accuracy_rate:.1f}% ({schema_accurate_count + chitchat_null_accurate_count}/{total_tests})", flush=True)
    print(f"  Average Inference Latency:        {avg_latency:.1f} ms ({avg_latency/1000.0:.2f} s)", flush=True)
    print(f"  Average Generation Throughput:    {avg_tps:.1f} tokens/sec", flush=True)
    print("=" * 80, flush=True)

    # -------------------------------------------------------------------------
    # Save Results to JSON File
    # -------------------------------------------------------------------------
    benchmarks_dir = os.path.join(PROJECT_ROOT, "benchmarks")
    os.makedirs(benchmarks_dir, exist_ok=True)
    out_file = os.path.join(benchmarks_dir, "baseline_qwen3.5_2b_results.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[+] Detailed benchmark results persisted to:\n    {out_file}\n", flush=True)
    return summary


if __name__ == "__main__":
    target_model = sys.argv[1] if len(sys.argv) > 1 else "qwen3.5:2b"
    run_benchmark(model_name=target_model)
