from pathlib import Path

import streamlit as st

from seed_database import DB_PATH, seed_database
from text_to_sql import build_prompt, demo_generate_sql, get_schema, run_safe_query


if not Path(DB_PATH).exists():
    seed_database(DB_PATH)

st.set_page_config(page_title="Text-to-SQL AI Demo", page_icon="SQL")
st.title("Text-to-SQL AI Demo")

question = st.text_input(
    "Ask a question about sales",
    value="Which customers have unpaid invoices greater than 500?",
)

schema = get_schema(DB_PATH)

with st.expander("Database schema"):
    st.code(schema, language="text")

if st.button("Generate SQL and Run"):
    prompt = build_prompt(schema, question)
    sql_query = demo_generate_sql(question)

    st.subheader("Prompt sent to the model")
    st.code(prompt, language="text")

    st.subheader("Generated SQL")
    st.code(sql_query, language="sql")

    try:
        rows = run_safe_query(DB_PATH, sql_query)
        st.subheader("Query result")
        st.dataframe(rows, use_container_width=True)
    except Exception as error:
        st.error(f"Could not execute the query: {error}")
