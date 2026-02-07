#!/usr/bin/env python3
"""
Jutsu Academy - Full Pygame Edition
====================================
A complete Pygame-based launcher and game for the Jutsu Trainer with:
- Modern menu system
- Settings with volume sliders
- Camera selection
- Practice mode (Free Play, Challenge)
- Particle effects and visual polish
- Sound system

Usage:
    python src/jutsu_academy/main_pygame.py
"""

import sys
from pathlib import Path

# Keep script execution behavior compatible with the original entrypoint
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.jutsu_academy.main_pygame_shared import *  # noqa: F401,F403
from src.jutsu_academy.main_pygame_app import JutsuAcademy, main


if __name__ == "__main__":
    main()
