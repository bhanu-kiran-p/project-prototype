import streamlit as st
import os
import requests
import json

def synthesize_pattern(raw_log: str, template: str, ocsf_class: str) -> dict:
    """
    Synthesize Regex and Mapping via Cloud AI (Groq API).
    Returns a dictionary with 'regex' and 'mapping'.
    """
    api_key = st.secrets.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in .streamlit/secrets.toml")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
Given the following raw log, log template, and its OCSF class, generate a regular expression to parse the log and a mapping of the regex capture groups to standard OCSF schema fields.

Raw Log: {raw_log}
Template: {template}
OCSF Class: {ocsf_class}

Important instructions:
1. Ensure the regex is a valid Python regular expression with named capture groups (e.g., (?P<group_name>pattern)).
2. Map the new log's data to standard OCSF field names (like src_endpoint.ip, dst_endpoint.ip, dst_endpoint.port, action, etc.). This ensures that future logs of this type are parsed into the exact same common format as known logs.

Respond strictly in JSON format with the following structure:
{{
  "regex": "your_regex_pattern_here",
  "mapping": {{
    "group_name_1": "ocsf_field_1",
    "group_name_2": "ocsf_field_2"
  }}
}}
"""

    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "system", "content": "You are a helpful cybersecurity assistant that generates regex patterns and OCSF mappings from logs. You output only valid JSON without any markdown formatting."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        content = response.json()['choices'][0]['message']['content']
        return json.loads(content)

    except requests.exceptions.HTTPError as e:
        print(f"Error during AI synthesis: {e}")
        print(f"Response details: {e.response.text}")
        return {"regex": None, "mapping": {}}
    except Exception as e:
        print(f"Error during AI synthesis: {e}")
        # Return fallback/empty
        return {"regex": None, "mapping": {}}
