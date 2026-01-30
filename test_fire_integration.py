import sys
from pathlib import Path
import cv2
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.fire_effect import FireEffect

def test_fire_effect():
    print("[*] Testing FireEffect...")
    try:
        effect = FireEffect(fire_size=400)
        effect.update()
        rgba = effect.render()
        
        assert rgba.shape == (400, 400, 4)
        print("[+] FireEffect instantiated, updated, and rendered successfully.")
    except Exception as e:
        print(f"[-] FireEffect failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fire_effect()
    print("[*] Done.")
