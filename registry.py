from datetime import datetime
import json
import re

def save_draft_pattern(conn, pattern_id, source, regex, mapping, ocsf_class, status="pending"):
    """
    Saves a pattern draft to the database.
    """
    ts = datetime.now().isoformat()
    mapping_str = json.dumps(mapping) if isinstance(mapping, dict) else mapping
    
    with conn:
        conn.execute(
            "INSERT INTO draft_patterns (pattern_id, source, regex, mapping, ocsf_class, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pattern_id, source, regex, mapping_str, ocsf_class, status, ts)
        )

def approve_pattern(conn, pattern_id):
    """
    Approves a pattern by moving it from draft_patterns to approved_patterns.
    """
    cursor = conn.cursor()
    # Get the draft pattern
    cursor.execute("SELECT source, regex, mapping, ocsf_class FROM draft_patterns WHERE pattern_id = ?", (pattern_id,))
    row = cursor.fetchone()
    
    if not row:
        return False
        
    source, regex, mapping, ocsf_class = row
    ts = datetime.now().isoformat()
    
    with conn:
        # Insert into approved_patterns
        conn.execute(
            "INSERT INTO approved_patterns (pattern_id, source, regex, mapping, ocsf_class, approved_at) VALUES (?, ?, ?, ?, ?, ?)",
            (pattern_id, source, regex, mapping, ocsf_class, ts)
        )
        # Update draft pattern status
        conn.execute(
            "UPDATE draft_patterns SET status = 'approved' WHERE pattern_id = ?",
            (pattern_id,)
        )
    return True

def get_approved_patterns(conn):
    """
    Returns a dictionary structure of approved patterns similar to known_patterns_map
    expected by the router.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT source, regex, mapping, ocsf_class FROM approved_patterns")
    rows = cursor.fetchall()
    
    patterns = {}
    for source, regex, mapping, ocsf_class in rows:
        if source not in patterns:
            patterns[source] = []
        
        # safely compile regex
        try:
            compiled = re.compile(regex)
        except Exception:
            continue
            
        patterns[source].append({
            "ocsf_class": ocsf_class,
            "regex": compiled,
            "mapping": json.loads(mapping) if isinstance(mapping, str) else mapping
        })
    return patterns
