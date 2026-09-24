from storage import archive_raw_text, log_event, log_ingestion_activity
import uuid
import re
from datetime import datetime

def route_log(conn, raw_text, source, known_patterns_map):
    log_uuid = str(uuid.uuid4())
    ts = datetime.now().isoformat()
    
    # checking if the log is empty
    if not raw_text or not raw_text.strip():
        with conn:
            conn.execute(
                "INSERT INTO failed_dlq (uuid, ts, source, raw, reason) VALUES (?, ?, ?, ?, ?)",
                (log_uuid, ts, source, raw_text, "empty or malformed log")
            )
        return log_uuid, "failed"

    # archive and log the event
    archive_path = archive_raw_text(raw_text, log_uuid)
    log_event(conn, log_uuid, source, "RECEIVED", f"Log received and archived to {archive_path}")
    log_ingestion_activity(conn, log_uuid, "pattern is known.\nsent to normalization.")

    # to reduce complexity we check only the patterns in certain source, ex: if the log is router log , check only the router log patterns
    '''
    the known_patterns_map looks like this
            KNOWN_PATTERNS_MAP = {
            "vpn-gw-01": [ 
                {
                    "ocsf_class": "Authentication",
                    "regex": re.compile(r"login OK user-(?P<username>\w+) src (?P<src_ip>\d+\.\d+\.\d+\.\d+)")
                }
            ]
        }
    
        # simply it looks like this
        {
        source1:[ {pattern1_info}, {pattern2_info}, {pattern3_info}, .... {pattern4_info} ],
        source2:[ {pattern1_info}, {pattern2_info}, {pattern3_info}, .... {pattern4_info} ]
        }
    '''
    source_rules = known_patterns_map.get(source, [])
    if source in known_patterns_map:
        source_rules = known_patterns_map[source]
    else:
        source_rules = []
    
    # matching the rules using regex
    for rule in source_rules:
        match = rule["regex"].match(raw_text)

        # if known pattern then the ture
        if match:
            extracted_fields = match.groupdict()
            ocsf_class = rule["ocsf_class"]
            
            conn.execute(
                "INSERT INTO normalized_logs (uuid, ts, source, raw, ocsf_class, fields) VALUES (?, ?, ?, ?, ?, ?)",
                (log_uuid, ts, source, raw_text, ocsf_class, str(extracted_fields))
            )
            conn.commit()
            log_ingestion_activity(conn, log_uuid, f"normalization success and converted to common format and stored in log storage.")
            return log_uuid, "known"
    
    # 6. Cold Path (Unknown DLQ): No patterns matched; route to AI[cite: 14]
    conn.execute(
        "INSERT INTO unknown_dlq (uuid, ts, source, raw, status) VALUES (?, ?, ?, ?, ?)",
        (log_uuid, ts, source, raw_text, "pending")
    )
    conn.commit()
    return log_uuid, "unknown"