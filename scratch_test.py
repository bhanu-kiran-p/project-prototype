import sqlite3
import pandas as pd
from drain3_parser import extract_template
from classifier import classify_template
from ai_synthesizer import synthesize_pattern
import re

conn = sqlite3.connect('storage.db')
unk_df = pd.read_sql_query("SELECT * FROM unknown_dlq WHERE raw LIKE '%unknown action%' AND status='draft_created' LIMIT 1", conn)
if unk_df.empty:
    print('No unknown action logs found.')
else:
    row = unk_df.iloc[0]
    raw_text = row['raw']
    template_res = extract_template(raw_text)
    template = template_res['template']
    category, confidence = classify_template(template)
    ai_res = synthesize_pattern(raw_text, template, category)
    regex_str = ai_res.get('regex')
    print('Raw:', raw_text)
    print('Regex:', regex_str)
    try:
        c = re.compile(regex_str)
        m = c.match(raw_text)
        print('Match:', m)
    except Exception as e:
        print('Error:', e)
