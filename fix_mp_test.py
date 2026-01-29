
import ctypes
import sys

print(f"Python: {sys.version}")

try:
    import msvcrt
    print("msvcrt module imported")
except ImportError:
    print("msvcrt module not found")

try:
    lib = ctypes.cdll.msvcrt
    print(f"ctypes.cdll.msvcrt: {lib}")
    print(f"Has free? {hasattr(lib, 'free')}")
    print(f"lib.free: {lib.free}")
except Exception as e:
    print(f"Error accessing msvcrt.free: {e}")

try:
    # Try loading ucrtbase which is the modern C runtime
    ucrt = ctypes.CDLL('ucrtbase')
    print(f"ucrtbase: {ucrt}")
    print(f"ucrt.free: {ucrt.free}")
except Exception as e:
    print(f"Error accessing ucrtbase.free: {e}")

# Try to replicate what mediapipe might be doing
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    print("MediaPipe imported successfully")
except Exception as e:
    print(f"MediaPipe import failed: {e}")
