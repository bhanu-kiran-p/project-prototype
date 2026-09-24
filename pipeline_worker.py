import pandas as pd
import uuid
import re
from storage import get_conn, log_ai_activity
from drain3_parser import extract_template
from classifier import classify_template
from ai_synthesizer import synthesize_pattern
from registry import save_draft_pattern, approve_pattern, get_approved_patterns
from router import route_log
import json
import threading

# Global event to signal cancellation
_cancel_event = threading.Event()

def cancel_pipeline():
    _cancel_event.set()

def run_ai_recovery_pipeline():
    _cancel_event.clear()
    conn = get_conn()
    try:
        unk_df = pd.read_sql_query("SELECT * FROM unknown_dlq WHERE status='pending'", conn)
        
        for _, row in unk_df.iterrows():
            if _cancel_event.is_set():
                break
                
            raw_text = row['raw']
            source = row['source']
            log_id = row['uuid']
            
            # 1. Template Extraction
            template_res = extract_template(raw_text)
            template = template_res['template']
            
            # 2. Classification
            category, confidence = classify_template(template)
            
            log_ai_activity(conn, log_id, "is being processed.\nbert model identified the fields.")
            
            # 3. Pattern Synthesis
            ai_res = synthesize_pattern(raw_text, template, category)
            log_ai_activity(conn, log_id, f"ai generated a pattern.")
            regex_str = ai_res.get('regex')
            mapping = ai_res.get('mapping')
            
            if regex_str:
                pattern_id = str(uuid.uuid4())
                
                # Automatic Verification
                is_valid = False
                try:
                    compiled_regex = re.compile(regex_str)
                    match = compiled_regex.match(raw_text)
                    if match:
                        # Ensures the regex groups map correctly if we wanted strict checks,
                        # but a successful match means the pattern works for this log.
                        is_valid = True
                except Exception:
                    pass
                
                if is_valid:
                    log_ai_activity(conn, log_id, f"pattern validation passed.\npattern stored.\ningesting the dead letter queue again.")
                    # Save as approved immediately
                    save_draft_pattern(conn, pattern_id, source, regex_str, mapping, category, status="approved")
                    approve_pattern(conn, pattern_id) # This handles moving from draft to approved
                    
                    # Instead of calling route_log manually for all, we re-ingest all pending logs for this source
                    # But wait, route_log expects known_patterns map
                    known_patterns = get_approved_patterns(conn)
                    
                    pending_logs_for_source = pd.read_sql_query(
                        "SELECT * FROM unknown_dlq WHERE status='pending' AND source=?", 
                        conn, params=(source,)
                    )
                    
                    for _, plog in pending_logs_for_source.iterrows():
                        p_raw = plog['raw']
                        p_source = plog['source']
                        p_uuid = plog['uuid']
                        # Re-route
                        # We use the existing router to process the log.
                        new_uuid, routing_status = route_log(conn, p_raw, p_source, known_patterns)
                        
                        # If routing was successful as 'known', we delete the old entry from unknown_dlq
                        if routing_status == "known":
                            with conn:
                                conn.execute("DELETE FROM unknown_dlq WHERE uuid=?", (p_uuid,))
                        else:
                            # if for some reason it didn't match the new pattern
                            pass
                else:
                    log_ai_activity(conn, log_id, "pattern validation failed.\nredirected to draft for user response.")
                    # Validation failed, save as draft for manual review
                    save_draft_pattern(conn, pattern_id, source, regex_str, mapping, category)
                    with conn:
                        conn.execute("UPDATE unknown_dlq SET status='draft_created' WHERE uuid=?", (log_id,))
    finally:
        conn.close()
