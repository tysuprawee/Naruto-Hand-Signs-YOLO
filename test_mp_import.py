
try:
    import mediapipe as mp
    print("Imported mediapipe as mp")
    try:
        print(f"mp.solutions: {mp.solutions}")
    except AttributeError:
        print("mp.solutions NOT found")

    try:
        from mediapipe import solutions
        print(f"from mediapipe import solutions: {solutions}")
    except ImportError:
        print("from mediapipe import solutions FAILED")

    try:
        import mediapipe.python.solutions.hands as mp_hands
        print(f"import mediapipe.python.solutions.hands: {mp_hands}")
    except ImportError:
        print("import mediapipe.python.solutions.hands FAILED")

except ImportError as e:
    print(f"Import mediapipe failed: {e}")
