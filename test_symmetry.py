import sys
from PIL import Image, ImageDraw, ImageFont

def process_card_back(img_path, output_path):
    print(f"Loading {img_path}")
    img = Image.open(img_path)
    w, h = img.size
    
    # Standard tarot is 2.75 x 4.75 inches -> aspect ratio ~ 0.5789
    target_ratio = 2.75 / 4.75
    
    # We want max height, crop width from center
    target_h = h
    target_w = int(h * target_ratio)
    
    left = (w - target_w) / 2
    top = 0
    right = (w + target_w) / 2
    bottom = h
    
    # 1. Crop to Tarot Aspect Ratio
    cropped = img.crop((left, top, right, bottom))
    
    # 2. Duplicate and Rotate 180 degrees
    flipped = cropped.rotate(180)
    
    # 3. Stitch them side-by-side with a border
    border = 20
    out_w = (target_w * 2) + (border * 3)
    out_h = target_h + (border * 2)
    
    output_img = Image.new('RGB', (out_w, out_h), (20, 20, 20))
    
    output_img.paste(cropped, (border, border))
    output_img.paste(flipped, (border * 2 + target_w, border))
    
    # Save the result
    output_img.save(output_path)
    print(f"Saved symmetry check to {output_path}")

if __name__ == "__main__":
    src = r"C:\Users\bossx\.gemini\antigravity\brain\8bedc24d-035e-4baa-8800-7695de21050a\card_back_eye_perfect_sym_1775491924771.png"
    dest = r"C:\Users\bossx\.gemini\antigravity\scratch\mytarot-bot\card_back_symmetry_test.jpg"
    process_card_back(src, dest)
