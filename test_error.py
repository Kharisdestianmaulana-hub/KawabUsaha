import sqlite3
conn = sqlite3.connect('kawanusaha.db')
cursor = conn.cursor()
date_filter = "DATE(sales.created_at, 'localtime') = DATE('now', 'localtime')"
try:
    query_top = f"""
        SELECT p.name, SUM(si.quantity) as qty
        FROM sale_items si
        JOIN sales s ON si.sale_id = s.id
        JOIN products p ON si.product_id = p.id
        WHERE s.business_id = 1 AND {date_filter}
        GROUP BY p.id
        ORDER BY qty DESC
        LIMIT 3
    """
    cursor.execute(query_top)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
