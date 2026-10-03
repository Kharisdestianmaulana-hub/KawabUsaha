from app.database.connection import get_db_connection

def get_user_access(telegram_id: int):
    """
    Mengecek hak akses user.
    Mengembalikan dict: {'business_id': int, 'role': str} atau None jika tidak terdaftar.
    Role: 'owner' atau 'kasir'
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Cek apakah dia bos (owner)
        cursor.execute("SELECT id FROM businesses WHERE user_id = ?", (telegram_id,))
        biz = cursor.fetchone()
        
        if biz:
            return {'business_id': biz['id'], 'role': 'owner'}
            
        # 2. Cek apakah dia pegawai (staff)
        cursor.execute("SELECT business_id, role FROM staff WHERE telegram_user_id = ?", (telegram_id,))
        staff = cursor.fetchone()
        
        if staff:
            return {'business_id': staff['business_id'], 'role': staff['role']}
            
    return None
