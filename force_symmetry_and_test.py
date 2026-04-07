from PIL import Image

def force_symmetry_and_test(img_path, master_out, test_out):
    print(f"Loading {img_path}")
    img = Image.open(img_path).convert('RGB')
    w, h = img.size
    
    # 1. Force absolute 180-degree mathematical symmetry
    # We take the top half, duplicate, rotate 180, and paste to the bottom.
    top_half = img.crop((0, 0, w, h // 2))
    bottom_half_sym = top_half.rotate(180)
    
    master_sym = Image.new('RGB', (w, h))
    master_sym.paste(top_half, (0, 0))
    master_sym.paste(bottom_half_sym, (0, h // 2))
    
    # Save the new flawless master image
    master_sym.save(master_out)
    print(f"Saved flawless symmetrical master to {master_out}")
    
    # 2. Crop to Tarot Ratio (2.75 x 4.75 -> 0.5789)
    target_ratio = 2.75 / 4.75
    target_h = h
    target_w = int(h * target_ratio)
    
    left = (w - target_w) // 2
    top = 0
    right = left + target_w
    bottom = h
    
    cropped = master_sym.crop((left, top, right, bottom))
    
    # 3. Stitch original cropped vs 180-flip cropped for testing
    flipped = cropped.rotate(180)
    
    border = 20
    out_w = (target_w * 2) + (border * 3)
    out_h = target_h + (border * 2)
    
    output_img = Image.new('RGB', (out_w, out_h), (20, 20, 20))
    output_img.paste(cropped, (border, border))
    output_img.paste(flipped, (border * 2 + target_w, border))
    
    output_img.save(test_out)
    print(f"Saved symmetry check to {test_out}")

if __name__ == "__main__":
    src = r"C:\Users\bossx\.gemini\antigravity\brain\8bedc24d-035e-4baa-8800-7695de21050a\card_back_mytarot_1775490094032.png"
    master = r"C:\Users\bossx\.gemini\antigravity\brain\8bedc24d-035e-4baa-8800-7695de21050a\card_back_master_final.png"
    test = r"C:\Users\bossx\.gemini\antigravity\scratch\mytarot-bot\card_back_symmetry_test.jpg"
    force_symmetry_and_test(src, master, test)
