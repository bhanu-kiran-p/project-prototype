# test_ai_pipeline.py
from ai_synthesizer import synthesize_pattern
from classifier import classify_template
from drain3_parser import extract_template


def run_ai_pipeline(raw_log: str) -> dict:
  # Step 1: Extract Template
  drain_res = extract_template(raw_log)
  template = drain_res["template"]
  cluster_id = drain_res["cluster_id"]

  # Step 2: Classify OCSF Category
  ocsf_class = classify_template(template)

  # Step 3: Synthesize Regex and Mapping via Cloud AI
  ai_rules = synthesize_pattern(raw_log, template, ocsf_class)

  return {
      "raw_log": raw_log,
      "cluster_id": cluster_id,
      "template": template,
      "ocsf_class": ocsf_class,
      "generated_regex": ai_rules.get("regex"),
      "ocsf_mapping": ai_rules.get("mapping"),
  }


# Local Test
if __name__ == "__main__":
  # Feed two similar logs to Drain3 and confirm they return the same cluster ID
  log1 = "2026-09-20T14:32:10Z firewall01 DROP TCP 192.168.1.105:443 -> 10.0.0.1:80"
  log2 = "2026-09-20T14:35:12Z firewall01 DROP TCP 192.168.1.110:443 -> 10.0.0.2:80"
  
  res1 = extract_template(log1)
  res2 = extract_template(log2)
  
  print(f"Log 1 Cluster ID: {res1['cluster_id']} | Template: {res1['template']}")
  print(f"Log 2 Cluster ID: {res2['cluster_id']} | Template: {res2['template']}")
  
  if res1['cluster_id'] == res2['cluster_id']:
      print("[SUCCESS] Drain3 Testing: Both similar logs returned the same cluster ID.")
  else:
      print("[FAILED] Drain3 Testing: Cluster IDs did not match.")
      
  # Test the AI synthesis by confirming the response is a valid JSON dictionary
  print("\nRunning AI Pipeline for log1...")
  result = run_ai_pipeline(log1)
  
  print("\nAI Synthesis Results:")
  import json
  print(json.dumps(result, indent=2))
  
  # Check if response is a valid JSON dictionary mapping (we already parse it into a dict)
  if isinstance(result.get("generated_regex"), str) and isinstance(result.get("ocsf_mapping"), dict):
      print("\n[SUCCESS] AI Synthesis Testing: Response contains valid regex and mapping dictionary.")
  else:
      print("\n[FAILED] AI Synthesis Testing: Invalid response structure.")