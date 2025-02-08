from barcode import EAN13
from barcode.writer import ImageWriter
import os
from PIL import Image, ImageDraw, ImageFont
import textwrap

def create_barcode_label(name, price, barcode_number, output_path):
    # Create barcode
    ean = EAN13(barcode_number, writer=ImageWriter())
    
    # Create a new image with white background
    img = Image.new('RGB', (400, 200), 'white')
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to load a font (use default if not available)
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Add item details
    draw.text((10, 10), f"{name}", fill='black', font=font)
    draw.text((10, 40), f"${price:.2f}", fill='black', font=font)
    draw.text((10, 70), f"{barcode_number}", fill='black', font=font)
    
    # Generate and paste barcode
    barcode_img = ean.render()
    barcode_img = barcode_img.resize((380, 100))
    img.paste(barcode_img, (10, 90))
    
    # Save the final image
    img.save(output_path)

def generate_sample_barcodes():
    # Create output directory if it doesn't exist
    if not os.path.exists('barcodes'):
        os.makedirs('barcodes')
    
    # Configure the barcode writer
    writer_options = {
        'module_height': 15.0,  # Increase height for better scanning
        'module_width': 0.2,    # Adjust width
        'quiet_zone': 6.5,      # Add quiet zone (white space) around barcode
        'font_size': 2,         # Smaller text
        'text_distance': 5,     # Distance of text from bars
        'write_text': True      # Include the number below barcode
    }
    
    # Sample items with their barcodes from the database
    items = [
        {
            'name': 'Milk',
            'barcode': '2967882314534'
        },
        {
            'name': 'Bread',
            'barcode': '1204341716081'
        },
        {
            'name': 'Eggs',
            'barcode': '8781567199506'
        }
    ]
    
    # Generate barcodes
    for item in items:
        # Generate the barcode with custom options
        ean = EAN13(item['barcode'], writer=ImageWriter())
        ean.writer_options = writer_options
        
        # Save with just the barcode number as filename
        filename = f"barcodes/{item['barcode']}"
        ean.save(filename)
        print(f"Generated barcode for {item['name']} ({item['barcode']}): {filename}.png")

if __name__ == "__main__":
    generate_sample_barcodes() 