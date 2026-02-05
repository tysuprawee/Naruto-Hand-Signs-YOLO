import sys
print(f"Python: {sys.version}")
try:
    import mediapipe as mp
    print(f"MediaPipe file: {mp.__file__}")
    if hasattr(mp, 'solutions'):
        print("SUCCESS: mp.solutions found!")
        print(f"mp.solutions.hands: {mp.solutions.hands}")
    else:
        print("FAILURE: mp.solutions NOT found.")
        print(f"Dir(mp): {dir(mp)}")
except Exception as e:
    print(f"Import Error: {e}")
