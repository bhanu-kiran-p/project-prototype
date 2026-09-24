import streamlit as st
import pandas as pd
from storage import get_conn

st.set_page_config(layout="wide")

conn = get_conn()

st.write("### Common Format Logs")
norm_df = pd.read_sql_query("SELECT * FROM normalized_logs ORDER BY ts DESC", conn)
if not norm_df.empty:
    st.dataframe(norm_df, hide_index=True, use_container_width=True)
else:
    st.write("No common format logs available.")

st.write("### Raw Logs")
# Union raw logs from normalized, unknown, and failed queues
raw_df = pd.read_sql_query('''
    SELECT ts, raw, source FROM normalized_logs
    UNION ALL
    SELECT ts, raw, source FROM unknown_dlq
    UNION ALL
    SELECT ts, raw, source FROM failed_dlq
    ORDER BY ts DESC
''', conn)
if not raw_df.empty:
    st.dataframe(raw_df, hide_index=True, use_container_width=True)
else:
    st.write("No raw logs available.")
