# SQL AI Database Solutions: Talking to Databases with Artificial Intelligence


This repository includes a runnable public example:

- `seed_database.py`: creates a sample SQLite database.
- `text_to_sql.py`: reads the schema, builds prompts, validates SQL, and runs safe read-only queries.
- `app.py`: provides a small Streamlit interface for the demo.

Run it locally:

```bash
pip install -r requirements.txt
python seed_database.py
streamlit run app.py
```

## Abstract

**SQL AI Database Solutions** allow users to ask questions in natural language and receive answers from a database without manually writing SQL. The idea sounds simple: the user asks a question, an AI model generates a SQL query, and the application executes it. In a real-world system, however, generating SQL is not enough. The application must understand the database schema, validate the generated query, restrict permissions, and return reliable results. This article explains a practical Text-to-SQL architecture using Python, SQLite, Streamlit-style examples, and a realistic sales and customer support scenario.

## 1. Why Text-to-SQL Matters

Many organizations store valuable information in relational databases: sales, customers, products, payments, inventory, attendance, support tickets, or academic records. The challenge is that not every user knows SQL. A manager, for example, may want to ask:

> Which customers have unpaid invoices greater than 500?

A data analyst could solve that with `JOIN`, `GROUP BY`, and filters. A SQL AI solution tries to convert that business question into a correct SQL query and run it against the database.

The freeCodeCamp reference presents this idea as an AI-powered data extractor: a user writes a question, and the system uses AI to query a database. Hugging Face also highlights an important warning: Text-to-SQL should not be treated as a simple translation task, because a generated query can be wrong and still return results that look valid. That is why real applications need validation, restrictions, and sometimes an agent that can inspect and improve the output.

## 2. General Architecture

A real SQL AI application can be organized like this:

```text
User
  -> Web interface or chat
  -> Database schema reader
  -> Prompt for the AI model
  -> Generated SQL
  -> Security validator
  -> Read-only database connection
  -> Table result or natural-language summary
```

The most important rule is that the model should not invent tables or columns. It needs database context: table names, column names, data types, and relationships.

## 3. Real-World Scenario: Sales and Customer Support

Imagine an online store that stores customers, orders, and payment information. The support team wants to answer questions such as:

- Which customers still owe money?
- Which products sold the most this month?
- Which orders were partially paid?
- Which customers purchased more than three times?

A minimal database schema could look like this:

```sql
CREATE TABLE customers (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  country TEXT NOT NULL
);

CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL,
  order_date TEXT NOT NULL,
  total REAL NOT NULL,
  paid REAL NOT NULL,
  status TEXT NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);
```

With that data, a natural-language question like this:

```text
Which customers have unpaid invoices greater than 500?
```

can be converted into SQL:

```sql
SELECT
  c.name,
  c.email,
  SUM(o.total - o.paid) AS pending_amount
FROM customers c
JOIN orders o ON o.customer_id = c.id
WHERE o.status IN ('pending', 'partial')
GROUP BY c.id, c.name, c.email
HAVING pending_amount > 500
ORDER BY pending_amount DESC;
```

This is where Text-to-SQL becomes useful: the user understands the business question, but may not know the SQL syntax required to answer it.

## 4. Creating a Test Database with Python

The following example creates a SQLite database with customers and orders. It is small, but it represents a realistic sales case.

```python
import sqlite3

DB_PATH = "sales_demo.db"

schema = """
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  country TEXT NOT NULL
);

CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER NOT NULL,
  order_date TEXT NOT NULL,
  total REAL NOT NULL,
  paid REAL NOT NULL,
  status TEXT NOT NULL,
  FOREIGN KEY (customer_id) REFERENCES customers(id)
);
"""

customers = [
    (1, "Ana Torres", "ana@example.com", "Peru"),
    (2, "Luis Ramos", "luis@example.com", "Chile"),
    (3, "Marta Diaz", "marta@example.com", "Colombia"),
]

orders = [
    (1, 1, "2026-06-01", 900.00, 300.00, "partial"),
    (2, 1, "2026-06-15", 150.00, 150.00, "paid"),
    (3, 2, "2026-06-20", 780.00, 0.00, "pending"),
    (4, 3, "2026-06-22", 120.00, 120.00, "paid"),
]

with sqlite3.connect(DB_PATH) as conn:
    conn.executescript(schema)
    conn.executemany(
        "INSERT INTO customers (id, name, email, country) VALUES (?, ?, ?, ?)",
        customers,
    )
    conn.executemany(
        """
        INSERT INTO orders (id, customer_id, order_date, total, paid, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        orders,
    )

print("Database ready:", DB_PATH)
```

## 5. Reading the Database Schema Automatically

Before asking a model to generate SQL, we should provide the real schema. In SQLite, we can read it like this:

```python
import sqlite3

def get_schema(db_path: str) -> str:
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

        schema_lines = []
        for (table_name,) in tables:
            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            schema_lines.append(f"Table: {table_name}")
            for column in columns:
                _, name, data_type, not_null, _, pk = column
                required = "NOT NULL" if not_null else "NULL"
                primary_key = "PRIMARY KEY" if pk else ""
                schema_lines.append(f"  - {name}: {data_type} {required} {primary_key}")

        return "\n".join(schema_lines)

print(get_schema("sales_demo.db"))
```

Expected output:

```text
Table: customers
  - id: INTEGER NULL PRIMARY KEY
  - name: TEXT NOT NULL
  - email: TEXT NOT NULL
  - country: TEXT NOT NULL
Table: orders
  - id: INTEGER NULL PRIMARY KEY
  - customer_id: INTEGER NOT NULL
  - order_date: TEXT NOT NULL
  - total: REAL NOT NULL
  - paid: REAL NOT NULL
  - status: TEXT NOT NULL
```

This context reduces errors because the model knows that `customers.email` exists, but it should not invent a column such as `customer_phone` if it is not in the schema.

## 6. Prompting the Model to Generate SQL

The prompt should be direct and include clear rules:

```python
def build_prompt(schema: str, question: str) -> str:
    return f"""
You are a Text-to-SQL assistant.
Generate one SQLite SELECT query for the user's question.
Use only the tables and columns listed in the schema.
Do not generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, PRAGMA, or ATTACH.
Return only SQL, without markdown.

Schema:
{schema}

Question:
{question}
"""
```

In a real application, the model call can use Hugging Face, OpenAI, Groq, Gemini, Claude, or another provider. The important part is to separate responsibilities:

```python
schema = get_schema("sales_demo.db")
question = "Which customers have unpaid invoices greater than 500?"
prompt = build_prompt(schema, question)

sql_query = llm.generate(prompt)  # Replace this with your selected AI provider
print(sql_query)
```

## 7. Validating Before Execution

AI-generated SQL should never be executed without controls. For a demo, we can use a basic validator:

```python
def is_safe_select(sql: str) -> bool:
    normalized = " ".join(sql.strip().lower().split())
    forbidden = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "replace",
        "truncate",
        "pragma",
        "attach",
        "detach",
    ]

    if not normalized.startswith("select "):
        return False

    return not any(word in normalized for word in forbidden)
```

For production, this should be improved with a SQL parser such as `sqlglot`, allowlisted tables, a read-only database user, row limits, and query auditing.

## 8. Executing with Read-Only Permissions

The following example opens SQLite in read-only mode and adds `LIMIT 50` if the model did not include one:

```python
import sqlite3

def run_safe_query(db_path: str, sql: str) -> list[tuple]:
    if not is_safe_select(sql):
        raise ValueError("Unsafe SQL generated by model")

    safe_sql = sql.strip().rstrip(";")
    if " limit " not in f" {safe_sql.lower()} ":
        safe_sql += " LIMIT 50"

    readonly_uri = f"file:{db_path}?mode=ro"
    with sqlite3.connect(readonly_uri, uri=True) as conn:
        return conn.execute(safe_sql).fetchall()
```

Usage:

```python
sql_query = """
SELECT
  c.name,
  c.email,
  SUM(o.total - o.paid) AS pending_amount
FROM customers c
JOIN orders o ON o.customer_id = c.id
WHERE o.status IN ('pending', 'partial')
GROUP BY c.id, c.name, c.email
HAVING pending_amount > 500
ORDER BY pending_amount DESC
"""

rows = run_safe_query("sales_demo.db", sql_query)
print(rows)
```

Possible output:

```text
[('Luis Ramos', 'luis@example.com', 780.0), ('Ana Torres', 'ana@example.com', 600.0)]
```

## 9. Mini Interface with Streamlit

A simple interface can display the user question, generated SQL, and database results:

```python
import streamlit as st

DB_PATH = "sales_demo.db"

st.title("Text-to-SQL AI Demo")
question = st.text_input("Ask a question about sales")

if st.button("Generate SQL") and question:
    schema = get_schema(DB_PATH)
    prompt = build_prompt(schema, question)

    sql_query = llm.generate(prompt)
    st.code(sql_query, language="sql")

    try:
        rows = run_safe_query(DB_PATH, sql_query)
        st.write(rows)
    except Exception as error:
        st.error(f"Could not execute the query: {error}")
```

This flow matches the idea from the Medium reference: a lightweight Streamlit app, a SQLite database, and a model call. The key improvement here is that we add validation and dynamic schema reading instead of depending only on a fixed prompt.

## 10. Agent-Based Approach

Hugging Face shows another useful improvement: using an agent with a SQL tool. The tool contains the table description, and the agent can iterate if it needs to correct the query.

A conceptual example with `smolagents` looks like this:

```python
from sqlalchemy import create_engine, inspect, text
from smolagents import CodeAgent, InferenceClientModel, tool

engine = create_engine("sqlite:///sales_demo.db")

def describe_tables() -> str:
    inspector = inspect(engine)
    description = []
    for table in inspector.get_table_names():
        columns = inspector.get_columns(table)
        description.append(f"Table {table}:")
        for column in columns:
            description.append(f"  - {column['name']}: {column['type']}")
    return "\n".join(description)

@tool
def sql_engine(query: str) -> str:
    """
    Execute a read-only SQL query over the sales database.

    Args:
        query: A safe SQLite SELECT query.
    """
    if not is_safe_select(query):
        return "Rejected: only safe SELECT queries are allowed."

    with engine.connect() as connection:
        rows = connection.execute(text(query)).fetchall()
    return "\n".join(str(row) for row in rows)

sql_engine.description = f"""
Use this tool to answer business questions with SQL.
Available schema:
{describe_tables()}
"""

agent = CodeAgent(
    tools=[sql_engine],
    model=InferenceClientModel(model_id="meta-llama/Llama-3.1-8B-Instruct"),
)

agent.run("Which customers have pending debt greater than 500?")
```

This approach is useful when the database has multiple tables and the model needs to reason about joins. Even then, the agent should use a safe tool, not a full-permission database connection.

## 11. Best Practices for Real Projects

1. Use a read-only database user.
2. Send only the required schema to the model, not sensitive data.
3. Validate generated SQL with a parser, not only with string checks.
4. Block dangerous statements such as `DROP`, `DELETE`, `UPDATE`, or `ALTER`.
5. Add a default `LIMIT` to avoid large accidental queries.
6. Log the user question, generated SQL, execution time, and errors.
7. Show the generated SQL to the user for transparency.
8. Require human confirmation in sensitive domains such as health, finance, or personal data.
9. Evaluate the system with real business questions.
10. Measure accuracy: a query that runs successfully is not always correct.

## 12. Important Observation

The hardest part of a SQL AI solution is not connecting the model. The hardest part is building trust. A model can generate a query that runs without errors but answers the wrong question. For example, it may forget a date filter, use the wrong column, or create a `JOIN` that duplicates totals. This is why the architecture should include validation, tests with known questions, and human review for critical reports.

## Conclusion

SQL AI Database Solutions make databases more accessible. They allow non-technical users to ask business questions in natural language and receive answers from real data. However, the solution must be designed carefully: schema context, validation, read-only permissions, limits, and monitoring are required. AI does not replace the judgment of a developer or analyst; it amplifies it when integrated with good engineering practices.

In short: Text-to-SQL is powerful, but it should be treated as an assisted query tool, not as an unrestricted door into the database.


## References

- freeCodeCamp: [How to Talk to Any Database Using AI - Build Your Own SQL Query Data Extractor](https://www.freecodecamp.org/news/talk-to-databases-using-ai-build-a-sql-query-data-extractor)
- Hugging Face: [Text-to-SQL with smolagents](https://huggingface.co/docs/smolagents/examples/text_to_sql)
- Medium: [Building a Text-to-SQL Query Generator with Streamlit and Hugging Face](https://medium.com/@kuhelidey878/building-a-text-to-sql-query-generator-with-streamlit-and-hugging-face-turn-natural-language-into-3e81eee198fb)
