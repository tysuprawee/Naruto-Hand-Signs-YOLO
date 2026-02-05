
# Official Jutsu Registry (Need to be hardcoded due to multiplayer aspect)
# This file defines the core techniques that CANNOT be modified by users via file editing.
# When packaged into an EXE, this code is frozen inside the executable.

OFFICIAL_JUTSUS = {
    "Fireball": {
        "sequence": ["horse", "snake", "ram", "monkey", "boar", "horse", "tiger"],
        "display_text": "KATON: GOUKAKYUU NO JUTSU!!",
        "sound_path": "src/sounds/fireball.mp3",
        "video_path": None,
        "effect": "fire"
    },
    "Chidori": {
        "sequence": ["ox", "hare", "monkey"],
        "display_text": "CHIDORI: KAZUSA NO JUTSU!",
        "sound_path": "src/chidori/chidori.mp3",
        "video_path": "src/chidori/chidori.mp4",
        "effect": "lightning"
    },
    "Water Dragon": {
        "sequence": ["ox", "monkey", "hare", "rat", "boar", "bird", "ox", "horse", "bird"],
        "display_text": "Water Dragon Bullet!",
        "sound_path": None,
        "video_path": None,
        "effect": "water"
    },
    "Shadow Clone": {
        "sequence": ["ram", "snake", "tiger"],
        "display_text": "Kage Bunshin no Jutsu!",
        "sound_path": None,
        "video_path": None,
        "effect": "clone"
    },
    "Phoenix Flower": {
        "sequence": ["rat", "tiger", "dog", "ox", "hare", "tiger"],
        "display_text": "Phoenix Sage Fire!",
        "sound_path": None,
        "video_path": None,
        "effect": "fire"
    },
    
    "Sharingan": {
        "sequence": ["snake", "ram", "monkey", "boar", "horse", "tiger"],
        "display_text": "SHARINGAN!",
        "sound_path": None,
        "video_path": None,
        "effect": "eye"
    },
    "Rasengan": {
        "sequence": ["ram"],
        "display_text": "RASENGAN!",
        "sound_path": "src/sounds/rasengan.mp3",
        "video_path": "src/RasenShuriken/RasenShuriken.mp4",
        "effect": "rasengan"
    }
}
