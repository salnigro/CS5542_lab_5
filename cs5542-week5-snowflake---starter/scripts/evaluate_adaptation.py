import sys
import os
import time

# Add parent directory to path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.chat_agent import get_agent

def run_evaluation():
    print("Starting Domain Adaptation Evaluation...\n")
    
    queries = [
        "Analyze the connection between recent user 'search' events and user sentiment.",
        "Assess the business outlook based on recent order metrics and external news.",
        "What is the impact of Team A's recent upload activity?",
        "Provide a summary of last week's system performance and user feedback.",
        "Calculate the sum of all 'upload' event values and tell me how that relates to revenue growth.",
        "Diagnose the cause of the high server latency this morning.",
        "Should we increase investment in the European market?",
        "Evaluate the success of the 'Free Trial' program.",
        "Are we ready for the upcoming compliance audit based on data tracking and policies?",
        "Determine the impact of last night's system maintenance."
    ]
    
    baseline_agent = get_agent(adapted=False)
    adapted_agent = get_agent(adapted=True)
    
    results = []
    
    for i, q in enumerate(queries):
        print(f"\n--- Query {i+1}/{len(queries)} ---")
        print(f"Q: {q}")
        
        # Baseline
        print("Running Baseline...")
        try:
            start = time.time()
            base_out = baseline_agent.invoke({"messages": [("user", q)]})
            raw_base = base_out["messages"][-1].content
            if isinstance(raw_base, list):
                base_response = "".join(part.get("text", "") for part in raw_base if isinstance(part, dict) and "text" in part)
            else:
                base_response = str(raw_base)
            base_time = time.time() - start
        except Exception as e:
            base_response = f"Error: {e}"
            base_time = 0
            
        # Adapted
        print("Running Adapted...")
        try:
            start = time.time()
            adapt_out = adapted_agent.invoke({"messages": [("user", q)]})
            raw_adapt = adapt_out["messages"][-1].content
            if isinstance(raw_adapt, list):
                adapt_response = "".join(part.get("text", "") for part in raw_adapt if isinstance(part, dict) and "text" in part)
            else:
                adapt_response = str(raw_adapt)
            adapt_time = time.time() - start
        except Exception as e:
            adapt_response = f"Error: {e}"
            adapt_time = 0
            
        results.append({
            "query": q,
            "baseline": base_response,
            "adapted": adapt_response,
            "baseline_time": base_time,
            "adapted_time": adapt_time
        })
        
    print("\n\n=== EVALUATION COMPLETE ===")
    
    # Write report
    with open("evaluation_results.md", "w", encoding="utf-8") as f:
        f.write("# Domain Adaptation Evaluation Results\n\n")
        f.write("| Query | Baseline Model | Adapted Model | Improv | \n")
        f.write("|---|---|---|---|\n")
        
        for i, res in enumerate(results):
            # truncate responses for table
            baseline_summ = res["baseline"].replace("\n", " ")[:150] + "..."
            adapted_summ = res["adapted"].replace("\n", " ")[:150] + "..."
            f.write(f"| {i+1}. {res['query']} | {baseline_summ} | {adapted_summ} | Pending |\n")

        f.write("\n## Detailed Responses\n\n")
        for i, res in enumerate(results):
            f.write(f"### Query {i+1}: {res['query']}\n")
            f.write(f"**Baseline (Generic Agent):**\n{res['baseline']}\n\n")
            f.write(f"**Adapted (Domain Expert):**\n{res['adapted']}\n\n")
            f.write("---\n")
            

if __name__ == "__main__":
    run_evaluation()
