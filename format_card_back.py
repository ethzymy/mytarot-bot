from PIL import Image

def resize_and_crop(image_path, output_path, target_size=(800, 1360)):
    # Open the image
    img = Image.open(image_path)
    
    # Calculate aspect ratios
    target_ratio = target_size[0] / target_size[1]
    img_ratio = img.width / img.height
    
    if img_ratio > target_ratio:
        # Image is wider than needed, resize based on height
        new_height = target_size[1]
        new_width = int(new_height * img_ratio)
    else:
        # Image is taller than needed, resize based on width
        new_width = target_size[0]
        new_height = int(new_width / img_ratio)
        
    # Resize image
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Calculate coordinates for center crop
    left = (new_width - target_size[0]) / 2
    top = (new_height - target_size[1]) / 2
    right = (new_width + target_size[0]) / 2
    bottom = (new_height + target_size[1]) / 2
    
    # Crop image
    img = img.crop((left, top, right, bottom))
    
    # Save image
    img.save(output_path, quality=95)
    print(f"Saved: {output_path} with size {img.size}")

if __name__ == "__main__":
    # Use the original source image, NOT the side-by-side comparison report.
    input_file = r"C:\Users\bossx\.gemini\antigravity\brain\8bedc24d-035e-4baa-8800-7695de21050a\card_back_master_final.png"
    output_file = r"c:\Users\bossx\.gemini\antigravity\scratch\mytarot-bot\assets\card_back_whatsapp.jpg"
    
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    resize_and_crop(input_file, output_file)

