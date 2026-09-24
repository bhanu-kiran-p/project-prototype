import streamlit as st
import pandas as pd
import re
from storage import get_conn
from router import route_log
import demo_data
from drain3_parser import extract_template
from classifier import classify_template
from ai_synthesizer import synthesize_pattern
from registry import save_draft_pattern, approve_pattern, get_approved_patterns
import uuid
import os
import concurrent.futures
from pipeline_worker import run_ai_recovery_pipeline, cancel_pipeline
import time

@st.cache_resource
def get_executor():
    return concurrent.futures.ThreadPoolExecutor(max_workers=2)

executor = get_executor()

st.set_page_config(layout="wide")

conn = get_conn()

# Dummy patterns for testing ingestion
KNOWN_PATTERNS = {
    "demo-source": [
        {
            "ocsf_class": "Authentication",
            "regex": re.compile(r"login OK user-(?P<username>\w+) src (?P<src_ip>\d+\.\d+\.\d+\.\d+)")
        }
    ]
}

# Merge with DB approved patterns
approved = get_approved_patterns(conn)
for src, patterns in approved.items():
    if src not in KNOWN_PATTERNS:
        KNOWN_PATTERNS[src] = []
    KNOWN_PATTERNS[src].extend(patterns)

def ingest_demo_batch():
    logs = demo_data.get_demo_logs(10)
    for raw_text, source in logs:
        route_log(conn, raw_text, source, KNOWN_PATTERNS)
    
    # Trigger background AI recovery pipeline automatically
    executor.submit(run_ai_recovery_pipeline)
    
    st.rerun()

def ingest_malformed():
    route_log(conn, "", "demo-source", KNOWN_PATTERNS)
    st.rerun()

def reset_db():
    cancel_pipeline()
    
    # Wait briefly for any active background thread to cleanly exit its current loop
    time.sleep(1.5)
    
    # Safely delete all records rather than trying to delete the SQLite file on Windows
    tables = [
        "log_events", "normalized_logs", "unknown_dlq", "failed_dlq", 
        "draft_patterns", "approved_patterns", "ingestion_activity", "ai_activity"
    ]
    
    try:
        with conn:
            for t in tables:
                conn.execute(f"DELETE FROM {t}")
    except Exception as e:
        st.error(f"Failed to clear data: {e}")
        return

    st.rerun()

with st.sidebar:
    st.write("### Controls")
    if st.button("Ingest Demo Batch"):
        ingest_demo_batch()
    if st.button("Ingest malformed logs"):
        ingest_malformed()
    if st.button("Reset prototype"):
        reset_db()


st.write("# UPLF Dashboard")

# Fetch metrics
norm_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM normalized_logs", conn).iloc[0]['cnt']
unk_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM unknown_dlq", conn).iloc[0]['cnt']
fail_count = pd.read_sql_query("SELECT COUNT(*) as cnt FROM failed_dlq", conn).iloc[0]['cnt']
ingested_count = norm_count + unk_count + fail_count

col1, col2, col3, col4 = st.columns(4)
with col1:
    with st.container(border=True):
        st.metric(label="Ingested Logs", value=ingested_count)
        
with col2:
    with st.container(border=True):
        st.metric(label="Normalized Logs", value=norm_count)
        
with col3:
    with st.container(border=True):
        st.metric(label="Unknown DLQ", value=unk_count)
        
with col4:
    with st.container(border=True):
        st.metric(label="Failed DLQ", value=fail_count)

st.divider()

graph_col1, graph_col2 = st.columns(2)

with graph_col1:
    st.write("### Log Processing Status")
    status_data = pd.DataFrame({
        "Status": ["Ingested", "Normalized", "Unknown DLQ", "Failed DLQ"],
        "Count": [ingested_count, norm_count, unk_count, fail_count]
    })
    st.bar_chart(status_data, x="Status", y="Count", color="#4CAF50")

with graph_col2:
    st.write("#### Volume Over Time")
    time_df = pd.read_sql_query('''
        SELECT ts FROM normalized_logs
        UNION ALL
        SELECT ts FROM unknown_dlq
        UNION ALL
        SELECT ts FROM failed_dlq
    ''', conn)
    
    if not time_df.empty:
        time_df['ts'] = pd.to_datetime(time_df['ts'])
        time_data = time_df.set_index('ts').resample('s').size().reset_index(name='Log Count')
        st.line_chart(time_data, x="ts", y="Log Count")
    else:
        st.write("No time data available yet. Ingest logs to see volume.")

st.divider()
st.write("### Live System Activity")
act_col1, act_col2 = st.columns(2)

with act_col1:
    st.write("#### Ingestion Pipeline")
    try:
        ingest_act = pd.read_sql_query("SELECT message, log_uuid, ts FROM ingestion_activity ORDER BY ts DESC LIMIT 50", conn)
        with st.container(height=300):
            if ingest_act.empty:
                st.write("No activity yet.")
            else:
                for _, row in ingest_act.iterrows():
                    st.markdown(f"```text\n{row['message']}\nUUID: {row['log_uuid']}\n```")
    except Exception as e:
        st.write("Waiting for initialization...")

with act_col2:
    st.write("#### AI Pipeline")
    try:
        ai_act = pd.read_sql_query("SELECT message, log_uuid, ts FROM ai_activity ORDER BY ts DESC LIMIT 50", conn)
        with st.container(height=300):
            if ai_act.empty:
                st.write("No activity yet.")
            else:
                for _, row in ai_act.iterrows():
                    st.markdown(f"```text\n{row['message']}\nUUID: {row['log_uuid']}\n```")
    except Exception as e:
        st.write("Waiting for initialization...")

st.write("### Normalized Logs")
norm_df = pd.read_sql_query("SELECT * FROM normalized_logs ORDER BY ts DESC LIMIT 100", conn)
st.dataframe(norm_df, hide_index=True, use_container_width=True)

st.write("### Unknown Dead Letter Queue")
unk_df = pd.read_sql_query("SELECT * FROM unknown_dlq ORDER BY ts DESC LIMIT 100", conn)
st.dataframe(unk_df, hide_index=True, use_container_width=True)

st.write("### Failed Dead Letter Queue")
fail_df = pd.read_sql_query("SELECT * FROM failed_dlq ORDER BY ts DESC LIMIT 100", conn)
st.dataframe(fail_df, hide_index=True, use_container_width=True)

st.divider()

st.write("## AI Recovery Pipeline")
if st.button("Process Unknown DLQ (Manual AI Pipeline Trigger)"):
    unk_df = pd.read_sql_query("SELECT * FROM unknown_dlq WHERE status='pending'", conn)
    processed = 0
    for _, row in unk_df.iterrows():
        raw_text = row['raw']
        source = row['source']
        log_id = row['uuid']
        
        # 1. Template Extraction
        template_res = extract_template(raw_text)
        template = template_res['template']
        
        # 2. Classification
        category, confidence = classify_template(template)
        
        # 3. Pattern Synthesis
        ai_res = synthesize_pattern(raw_text, template, category)
        regex = ai_res.get('regex')
        mapping = ai_res.get('mapping')
        
        if regex:
            # 4. Save Draft
            pattern_id = str(uuid.uuid4())
            save_draft_pattern(conn, pattern_id, source, regex, mapping, category)
            with conn:
                conn.execute("UPDATE unknown_dlq SET status='draft_created' WHERE uuid=?", (log_id,))
            processed += 1
            
    st.success(f"Processed {processed} Unknown DLQ logs!")
    st.rerun()

st.write("### Draft Patterns")
draft_df = pd.read_sql_query("SELECT * FROM draft_patterns WHERE status='pending'", conn)
if not draft_df.empty:
    st.dataframe(draft_df, hide_index=True, use_container_width=True)
    draft_id_to_approve = st.selectbox("Select Pattern ID to Approve", draft_df['pattern_id'].tolist())
    if st.button("Approve Pattern"):
        approve_pattern(conn, draft_id_to_approve)
        st.success(f"Pattern {draft_id_to_approve} approved!")
        st.rerun()
else:
    st.info("No draft patterns pending approval.")