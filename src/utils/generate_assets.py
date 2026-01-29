
import cv2
import numpy as np
from pathlib import Path

def create_text_icon(text, filename, color=(255, 255, 255), bg_color=(50, 50, 50)):
    # Create a 100x100 image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:] = bg_color
    
    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1
    
    # Get text size
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Center text
    text_x = (100 - text_width) // 2
    text_y = (100 + text_height) // 2
    
    cv2.putText(img, text, (text_x, text_y), font, font_scale, color, thickness)
    
    # Save
    save_path = Path("src/pics") / filename
    cv2.imwrite(str(save_path), img)
    print(f"Created {save_path}")

def create_fire_asset():
    # Create a transparent fire asset (4 channels)
    # 300x300 for the effect
    img = np.zeros((300, 300, 4), dtype=np.uint8)
    
    # Draw a gradient circle (Red/Orange)
    center = (150, 150)
    
    # Multiple circles to simulate a fireball
    cv2.circle(img, center, 80, (0, 0, 255, 200), -1)   # Red
    cv2.circle(img, center, 60, (0, 100, 255, 230), -1) # Orange
    cv2.circle(img, center, 30, (0, 255, 255, 255), -1) # Yellow
    
    # Save as PNG
    save_path = Path("src/pics/fire.png")
    cv2.imwrite(str(save_path), img)
    print(f"Created {save_path}")

def main():
    Path("src/pics").mkdir(parents=True, exist_ok=True)
    
    signs = [
        "horse", "snake", "ram", "monkey", "boar", "tiger",
        "dragon", "dog", "rat", "ox", "hare", "bird"
    ]
    
    for sign in signs:
        create_text_icon(sign.upper(), f"{sign}.png")
        
    create_fire_asset()
    print("Assets generated.")

if __name__ == "__main__":
    main()
