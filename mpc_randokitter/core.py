"""Core kit-building logic for MPC RandoKitter.

Shared by the CLI (mpc_random_kit.py) and the GUI (mpc_randokitter/gui.py).
Zero third-party dependencies — Python 3.6+ stdlib only.
"""

import datetime
import io
import os
import random
import re
import shutil
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, List, Optional

AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff"}

# Word pools for random kit names (Adjective_Noun combos)
_ADJECTIVES = (
    "Fuzzy", "Crispy", "Dusty", "Velvet", "Golden", "Cosmic", "Hazy", "Neon",
    "Rusty", "Silky", "Gritty", "Dreamy", "Burnt", "Frozen", "Liquid", "Atomic",
    "Lazy", "Electric", "Smoky", "Crystal", "Copper", "Mellow", "Savage",
    "Bitter", "Heavy", "Loose", "Warm", "Raw", "Deep", "Dark", "Bright",
    "Swift", "Wild", "Bold", "Strange", "Ancient", "Broken", "Hidden", "Hollow",
    "Faded", "Tangled", "Twisted", "Sunken", "Molten", "Woven", "Phantom",
    "Sonic", "Primal", "Bleached", "Sticky", "Wonky", "Murky", "Lush",
    "Polar", "Solar", "Lunar", "Gentle", "Fierce", "Sacred", "Wicked",
    "Mossy", "Peppered", "Charred", "Gilded", "Warped", "Grainy", "Oily",
    "Chunky", "Salty", "Smoked", "Brittle", "Cloudy", "Steamy", "Dense",
    "Wooly", "Spicy", "Muted", "Vivid", "Glassy", "Sandy", "Muddy",
    "Frayed", "Coiled", "Dented", "Crushed", "Soaked", "Bruised", "Peeled",
    "Scratched", "Rippled", "Layered", "Painted", "Waxed", "Frosted", "Salted",
    "Roasted", "Cracked", "Polished", "Rugged", "Jagged", "Smooth", "Coarse",
    "Dim", "Faint", "Thick", "Thin", "Flat", "Sharp", "Blunt",
    "Quiet", "Loud", "Slow", "Quick", "Tiny", "Grand", "Humble",
    "Crooked", "Slanted", "Curved", "Steep", "Narrow", "Vast", "Stray",
    "Hallow", "Ashen", "Brazen", "Sullen", "Serene", "Somber", "Lucid",
)

_NOUNS = (
    "Cream", "Thunder", "Pulse", "Groove", "Haze", "Bloom", "Vinyl", "Smoke",
    "Echo", "Ember", "Grain", "Tide", "Dust", "Honey", "Ghost", "Moss",
    "Rust", "Storm", "Dusk", "Flame", "Frost", "Amber", "Slate", "Silk",
    "Gravel", "Chrome", "Vapor", "Drift", "Bone", "Ash", "Coral", "Loom",
    "Spark", "Glow", "Shade", "Void", "Peak", "Root", "Sway", "Crunch",
    "Snap", "Thump", "Knock", "Buzz", "Rumble", "Drip", "Sizzle", "Howl",
    "Glitch", "Orbit", "Jungle", "Velour", "Concrete", "Marble", "Canvas",
    "Cipher", "Prism", "Horizon", "Mirage", "Oasis",
    "Plume", "Splinter", "Cobalt", "Tundra", "Anvil", "Furnace", "Lantern",
    "Thistle", "Bramble", "Fjord", "Canyon", "Ridge", "Crater", "Quarry",
    "Timber", "Flint", "Copper", "Pewter", "Burlap", "Linen", "Tweed",
    "Mortar", "Ratchet", "Piston", "Cinder", "Sulfur", "Magma", "Obsidian",
    "Quartz", "Basalt", "Granite", "Lichen", "Thorn", "Nettle", "Clover",
    "Birch", "Cedar", "Willow", "Sage", "Thyme", "Fennel", "Pepper",
    "Saffron", "Cacao", "Sesame", "Marrow", "Rind", "Husk", "Pith",
    "Sinew", "Gristle", "Tallow", "Resin", "Pitch", "Lacquer", "Patina",
    "Verge", "Brink", "Ledge", "Ravine", "Gorge", "Shoal", "Marsh",
    "Steppe", "Mesa", "Dune", "Bluff", "Cairn", "Spire", "Turret",
)

def generate_fun_name():
    """Pick a random Adjective_Noun combo for the kit."""
    return f"{random.choice(_ADJECTIVES)}_{random.choice(_NOUNS)}"

# Standard GM-ish pad → MIDI note layout for 128 pads.
# Pads 1-16 follow a typical MPC bank A drum layout, rest fill upward.
def default_pad_notes(count=128):
    base = [
        37, 36, 42, 82,   # pad 1-4:  side stick, kick, closed HH, ???
        40, 38, 46, 44,   # pad 5-8:  snare, snare2, open HH, pedal HH
        48, 47, 45, 43,   # pad 9-12: hi tom, mid tom, low tom, floor tom
        49, 55, 51, 53,   # pad 13-16: crash, ride bell, ride, ride2
    ]
    notes = []
    for i in range(count):
        if i < len(base):
            notes.append(base[i])
        else:
            # Fill remaining pads chromatically from note 60 upward
            notes.append(60 + (i - len(base)))
    return notes
