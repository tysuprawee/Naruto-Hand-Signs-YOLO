
# Official Jutsu Registry (Need to be hardcoded due to multiplayer aspect)
# This file defines the core techniques that CANNOT be modified by users via file editing.
# When packaged into an EXE, this code is frozen inside the executable.

OFFICIAL_JUTSUS = {
    "Shadow Clone + Chidori Combo": {
        "sequence": ["ram", "snake", "tiger", "ox", "hare", "monkey"],
        "display_text": "COMBO: SHADOW CLONE + CHIDORI!",
        "sound_path": None,
        "video_path": None,
        "effect": "lightning",
        "duration": 6.0,
        "min_level": 5,
        "combo_parts": [
            {
                "name": "Shadow Clone",
                "at_step": 3,
                "effect": "clone"
            },
            {
                "name": "Chidori",
                "at_step": 6,
                "effect": "lightning"
            }
        ]
    },
    "Shadow Clone + Rasengan Combo": {
        "sequence": ["ram", "snake", "tiger", "ram"],
        "display_text": "COMBO: SHADOW CLONE + RASENGAN!",
        "sound_path": None,
        "video_path": None,
        "effect": "rasengan",
        "duration": 8.0,
        "min_level": 5,
        "combo_parts": [
            {
                "name": "Shadow Clone",
                "at_step": 3,
                "effect": "clone"
            },
            {
                "name": "Rasengan",
                "at_step": 4,
                "effect": "rasengan"
            }
        ]
    },
    "Shadow Clone": {
        "sequence": ["ram", "snake", "tiger"],
        "display_text": "Kage Bunshin no Jutsu!",
        "sound_path": "src/sounds/clone.mp3",
        "video_path": None,
        "effect": "clone",
        "min_level": 0
    },
    "Rasengan": {
        "sequence": ["ram"],
        "display_text": "RASENGAN!",
        "sound_path": "src/sounds/rasengan.mp3",
        "video_path": "src/RasenShuriken/RasenShuriken.mp4",
        "effect": "rasengan",
        "duration": 8.0,
        "min_level": 1
    },
    "Fireball": {
        "sequence": ["horse", "snake", "ram", "monkey", "boar", "horse", "tiger"],
        "display_text": "KATON: GOUKAKYUU NO JUTSU!!",
        "sound_path": "src/sounds/fireball.mp3",
        "video_path": None,
        "effect": "fire",
        "min_level": 2
    },
    "Chidori": {
        "sequence": ["ox", "hare", "monkey"],
        "display_text": "CHIDORI: KAZUSA NO JUTSU!",
        "sound_path": "src/chidori/chidori.mp3",
        "video_path": "src/chidori/chidori.mp4",
        "effect": "lightning",
        "duration": 6.0,
        "min_level": 5
    },
    "Water Dragon": {
        "sequence": ["ox", "monkey", "hare", "rat", "boar", "bird", "ox", "horse", "bird"],
        "display_text": "Water Dragon Bullet!",
        "sound_path": None,
        "video_path": None,
        "effect": "water",
        "min_level": 8
    },
    "Phoenix Flower": {
        "sequence": ["rat", "tiger", "dog", "ox", "hare", "tiger"],
        "display_text": "Phoenix Sage Fire!",
        "sound_path": None,
        "video_path": None,
        "effect": "fire",
        "min_level": 3
    },
    "Sharingan": {
        "sequence": ["snake", "ram", "monkey", "boar", "horse", "tiger"],
        "display_text": "SHARINGAN!",
        "sound_path": None,
        "video_path": None,
        "effect": "eye",
        "min_level": 10
    }
}
