import os
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from app.database.connection import get_db_connection

def generate_invoice_pdf(sale_id: int) -> str:
    """Mengenerate file PDF invoice dan mereturn path filenya."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Ambil data penjualan
        cursor.execute("SELECT * FROM sales WHERE id = ?", (sale_id,))
        sale = cursor.fetchone()
        if not sale:
            raise ValueError("Data penjualan tidak ditemukan.")
            
        # 2. Ambil nama usaha
        cursor.execute("SELECT name FROM businesses WHERE id = ?", (sale['business_id'],))
        business = cursor.fetchone()
        business_name = business['name'] if business else "Toko KawanUsaha"
        
        # 3. Ambil data pelanggan (jika ada)
        customer_name = "Pelanggan Umum"
        if sale['customer_id']:
            cursor.execute("SELECT name FROM customers WHERE id = ?", (sale['customer_id'],))
            cust = cursor.fetchone()
            if cust:
                customer_name = cust['name']
                
        # 4. Ambil detail barang
        cursor.execute("""
            SELECT p.name, si.quantity, si.price_at_sale 
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.sale_id = ?
        """, (sale_id,))
        items = cursor.fetchall()
        
    # Buat direktori temp jika belum ada
    os.makedirs("temp", exist_ok=True)
    file_path = f"temp/INV-{sale_id}.pdf"
    
    # Setup ukuran kertas A5
    c = canvas.Canvas(file_path, pagesize=A5)
    width, height = A5
    
    # ============ HEADER ============
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, business_name)
    
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 70, "INVOICE / STRUK PEMBELIAN")
    
    date_str = sale['created_at'][:10]
    inv_number = f"INV-{date_str.replace('-', '')}-{sale_id}"
    staff_name = sale.get('staff_name') or "Owner"
    
    c.setFont("Helvetica", 9)
    c.drawString(40, height - 100, f"No. Invoice : {inv_number}")
    c.drawString(40, height - 115, f"Tanggal     : {date_str}")
    c.drawString(40, height - 130, f"Pelanggan   : {customer_name}")
    c.drawString(40, height - 145, f"Kasir       : {staff_name}")
    
    # ============ TABLE HEADER ============
    y = height - 185
    c.line(40, y + 15, width - 40, y + 15)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y, "Item")
    c.drawString(200, y, "Qty")
    c.drawString(240, y, "Harga")
    c.drawString(320, y, "Total")
    c.line(40, y - 10, width - 40, y - 10)
    
    # ============ TABLE CONTENT ============
    y -= 25
    c.setFont("Helvetica", 9)
    for item in items:
        subtotal = item['quantity'] * item['price_at_sale']
        # Potong string panjang
        nama_item = item['name'][:22] + "..." if len(item['name']) > 22 else item['name']
        
        c.drawString(40, y, nama_item)
        c.drawString(200, y, str(item['quantity']))
        c.drawString(240, y, f"Rp{int(item['price_at_sale']):,}".replace(',', '.'))
        c.drawString(320, y, f"Rp{int(subtotal):,}".replace(',', '.'))
        y -= 20
        
        # Jika halaman penuh, skip untuk MVP
        if y < 100:
            c.drawString(40, y, "... (Item lainnya disembunyikan)")
            y -= 20
            break
            
    # ============ FOOTER / TOTAL ============
    c.line(40, y + 10, width - 40, y + 10)
    
    # Check if discount exists
    discount = 0
    if 'discount' in sale.keys() and sale['discount']:
        discount = sale['discount']
        
    payment_method = sale.get('payment_method') or "Tunai"
    
    if discount > 0:
        c.setFont("Helvetica", 9)
        c.drawString(200, y - 10, "Subtotal:")
        c.drawString(290, y - 10, f"Rp{int(sale['total_amount'] + discount):,}".replace(',', '.'))
        c.drawString(200, y - 25, "Diskon:")
        c.drawString(290, y - 25, f"-Rp{int(discount):,}".replace(',', '.'))
        y -= 30
        
    c.setFont("Helvetica-Bold", 11)
    c.drawString(200, y - 10, "TOTAL BAYAR:")
    c.drawString(290, y - 10, f"Rp{int(sale['total_amount']):,}".replace(',', '.'))
    
    c.setFont("Helvetica", 9)
    c.drawString(200, y - 25, "Metode:")
    c.drawString(290, y - 25, str(payment_method))
    
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, 40, f"Terima kasih telah berbelanja di {business_name}!")
    
    c.save()
    return file_path
