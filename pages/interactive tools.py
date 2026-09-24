import streamlit as st
import json
import time
import re
import pandas as pd
from storage import get_conn
from router import route_log

st.set_page_config(page_title="Interactive Tools", layout="wide")

conn = get_conn()

KNOWN_PATTERNS = {
    "demo-source": [
        {
            "ocsf_class": "Authentication",
            "regex": re.compile(r"login OK user-(?P<username>\w+) src (?P<src_ip>\d+\.\d+\.\d+\.\d+)")
        }
    ]
}

st.write("# Interactive ULPF Tools")
st.divider()

# ==========================================
# ROW 1: Real-time Normalization
# ==========================================
st.write("### Real-time Log Normalization")
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    with st.container(border=True):
        st.write("#### Enter the Code")
        raw_input = st.text_area(
            "Paste raw log snippet here:", 
            value="login OK user-bhanu src 192.168.1.50",
            height=150
        )
        normalize_btn = st.button("Normalize Log", type="primary")

with row1_col2:
    with st.container(border=True):
        st.write("#### Common Format")
        if normalize_btn:
            log_uuid, status = route_log(conn, raw_input, "demo-source", KNOWN_PATTERNS)
            if status == "known":
                st.success("Successfully routed through Fast Path.")
                # Fetch it from DB to show it
                row = pd.read_sql_query(f"SELECT * FROM normalized_logs WHERE uuid='{log_uuid}'", conn).iloc[0]
                try:
                    fields = eval(row['fields'])
                except:
                    fields = row['fields']
                st.json({
                    "uuid": row['uuid'],
                    "class_name": row['ocsf_class'],
                    "fields": fields
                })
            elif status == "unknown":
                st.error("Validation Failed: Routing to Unknown DLQ.")
            else:
                st.error("Validation Failed: Routing to Failed DLQ.")
        else:
            st.info("Click 'Normalize Log' to see the JSON output.")

st.divider()

# ==========================================
# ROW 2: High-Volume Ingestion
# ==========================================
st.write("### High-Volume Log Ingestion")
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    with st.container(border=True):
        st.write("#### Batch Processing")
        uploaded_file = st.file_uploader("Upload raw log dump (.txt, .csv)", type=["txt", "csv"])
        process_btn = st.button("Process Batch")

with row2_col2:
    with st.container(border=True):
        st.write("#### Download File")
        if uploaded_file and process_btn:
            # Simulate backend processing time
            with st.spinner("Processing records..."):
                content = uploaded_file.getvalue().decode('utf-8').splitlines()
                processed_count = 0
                for line in content:
                    if line.strip():
                        route_log(conn, line, "demo-source", KNOWN_PATTERNS)
                        processed_count += 1
            
            st.success(f"Successfully processed {processed_count} logs from {uploaded_file.name}!")
            
            df = pd.read_sql_query(f"SELECT * FROM normalized_logs ORDER BY id DESC LIMIT {processed_count}", conn)
            
            output_list = []
            for _, row in df.iterrows():
                try:
                    f = eval(row['fields'])
                except:
                    f = row['fields']
                output_list.append({
                    "uuid": row['uuid'],
                    "class": row['ocsf_class'],
                    "fields": f
                })
            
            mock_output = json.dumps(output_list, indent=2)
            
            st.download_button(
                label="⬇️ Download OCSF Dataset",
                data=mock_output,
                file_name=f"normalized_{uploaded_file.name}.json",
                mime="application/json"
            )
        else:
            st.info("Upload a file and process it to enable downloads.")