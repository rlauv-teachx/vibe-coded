import os
import random
from PIL import Image, ImageDraw, ImageFont
import uuid
from datetime import datetime

def generate_receipt_image(items, total, filename, uploads_folder):
    """
    Generates a receipt image imitating SampleStore (Walmart format).
    """
    width = 400
    # Estimate height based on items
    line_height = 24
    header_lines = 8
    footer_lines = 10
    num_items = len(items)
    height = (header_lines + num_items + footer_lines) * line_height + 50
    
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
        font = ImageFont.truetype(font_path, 16)
        bold_font = ImageFont.truetype(font_path, 16) # DejaVuSansMono is already bold-ish, or use Bold variant
    except:
        font = ImageFont.load_default()
        bold_font = font

    y = 20
    
    # Header
    draw.text((width//2, y), "SampleStore", font=bold_font, fill='black', anchor="ms")
    y += line_height
    draw.text((width//2, y), "Save Money. Live Better.", font=font, fill='black', anchor="ms")
    y += line_height * 1.5
    
    draw.text((width//2, y), "123 Sample St", font=font, fill='black', anchor="ms")
    y += line_height
    draw.text((width//2, y), "Codeville, CA 90210", font=font, fill='black', anchor="ms")
    y += line_height
    draw.text((width//2, y), "ST# 01234 OP# 000001 TE# 01 TR# 09876", font=font, fill='black', anchor="ms")
    y += line_height * 1.5
    
    # Items
    for item_name, price in items:
        # Format: UPC Description Price
        # Mock UPC
        upc = "".join([str(random.randint(0,9)) for _ in range(12)])
        
        draw.text((20, y), f"{upc} {item_name}", font=font, fill='black', anchor="ls")
        price_str = f"{price:.2f}"
        draw.text((width - 20, y), price_str, font=font, fill='black', anchor="rs")
        y += line_height

    y += line_height * 0.5
    draw.line((20, y, width - 20, y), fill='black')
    y += line_height
    
    # Totals
    subtotal = sum(price for _, price in items)
    tax = subtotal * 0.08
    total_val = subtotal + tax
    
    draw.text((150, y), "SUBTOTAL", font=font, fill='black', anchor="rs")
    draw.text((width - 20, y), f"{subtotal:.2f}", font=font, fill='black', anchor="rs")
    y += line_height
    
    draw.text((150, y), "TAX 8.000%", font=font, fill='black', anchor="rs")
    draw.text((width - 20, y), f"{tax:.2f}", font=font, fill='black', anchor="rs")
    y += line_height * 1.5
    
    draw.text((150, y), "TOTAL", font=bold_font, fill='black', anchor="rs")
    draw.text((width - 20, y), f"{total_val:.2f}", font=bold_font, fill='black', anchor="rs")
    y += line_height * 1.5
    
    # Payment
    draw.text((20, y), "VISA TEND", font=font, fill='black', anchor="ls")
    draw.text((width - 20, y), f"{total_val:.2f}", font=font, fill='black', anchor="rs")
    y += line_height
    
    # Footer
    draw.text((width//2, y + 20), datetime.now().strftime("%m/%d/%y %H:%M:%S"), font=font, fill='black', anchor="ms")
    y += line_height * 2
    
    draw.text((width//2, y), "THANK YOU FOR SHOPPING", font=font, fill='black', anchor="ms")
    y += line_height
    draw.text((width//2, y), "WITH SAMPLESTORE", font=font, fill='black', anchor="ms")
    
    # Save
    file_path = os.path.join(uploads_folder, filename)
    image.save(file_path)

    # Return data structure
    data = {
        "store": "SampleStore",
        "date": datetime.now().strftime("%m/%d/%y %H:%M:%S"),
        "items": [{"description": i[0], "price": i[1]} for i in items],
        "subtotal": subtotal,
        "tax": tax,
        "total": total_val
    }
    return filename, data

def create_sample_receipts(uploads_folder):
    samples = []
    
    # Sample 1: Groceries
    items1 = [("MILK 1GAL", 3.49), ("EGGS 1DOZ", 4.99), ("BREAD WHEAT", 2.29), ("BANANAS", 1.45)]
    f1, d1 = generate_receipt_image(items1, 0, "sample_receipt_1.png", uploads_folder)
    samples.append((f1, d1))
    
    # Sample 2: Electronics
    items2 = [("USB CABLE", 12.99), ("AA BATTERIES", 8.49)]
    f2, d2 = generate_receipt_image(items2, 0, "sample_receipt_2.png", uploads_folder)
    samples.append((f2, d2))
    
    # Sample 3: Clothing
    items3 = [("T-SHIRT L", 15.00), ("JEANS M", 35.50), ("SOCKS 3PK", 9.99)]
    f3, d3 = generate_receipt_image(items3, 0, "sample_receipt_3.png", uploads_folder)
    samples.append((f3, d3))
    
    return samples

