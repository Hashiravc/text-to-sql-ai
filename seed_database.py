import sqlite3

DB_PATH = "sales_demo.db"

SCHEMA = """
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

CUSTOMERS = [
    (1, "Ana Torres", "ana@example.com", "Peru"),
    (2, "Luis Ramos", "luis@example.com", "Chile"),
    (3, "Marta Diaz", "marta@example.com", "Colombia"),
    (4, "Carla Vega", "carla@example.com", "Peru"),
]

ORDERS = [
    (1, 1, "2026-06-01", 900.00, 300.00, "partial"),
    (2, 1, "2026-06-15", 150.00, 150.00, "paid"),
    (3, 2, "2026-06-20", 780.00, 0.00, "pending"),
    (4, 3, "2026-06-22", 120.00, 120.00, "paid"),
    (5, 4, "2026-06-25", 240.00, 100.00, "partial"),
]


def seed_database(db_path: str = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO customers (id, name, email, country) VALUES (?, ?, ?, ?)",
            CUSTOMERS,
        )
        conn.executemany(
            """
            INSERT INTO orders (id, customer_id, order_date, total, paid, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ORDERS,
        )


if __name__ == "__main__":
    seed_database()
    print(f"Database ready: {DB_PATH}")
