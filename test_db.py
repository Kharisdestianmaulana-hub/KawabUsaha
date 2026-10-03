from app.database.connection import get_db_connection
try:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        time_modifier = "DATE(created_at) = DATE('now', 'localtime')"
        b_id = 1
        
        q = f'''
            SELECT p.name, SUM(si.quantity) as qty_sold 
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON si.product_id = p.id
            WHERE s.business_id = ? AND s.{time_modifier}
            GROUP BY p.id
            ORDER BY qty_sold DESC
        '''
        print(q)
        cursor.execute(q, (b_id,))
except Exception as e:
    print(f"ERROR: {e}")
