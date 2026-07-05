#!/usr/bin/env python3.14
# import python 3.14
# files = off
"""
DeepSeekCraftR1 - Minecraft Infdev
Classic Infdev-style sandbox: infinite terrain, caves, ores, mobs, survival.
Python 3.14+ compatible | 60 FPS target | no external asset files
"""

import pygame
import pygame.font
from pygame.locals import *
import array
import math
import random
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    HAS_OPENGL = True
except ImportError:
    HAS_OPENGL = False


def _surface_rgba_bytes(surface):
    """Return top-left RGBA bytes for OpenGL uploads."""
    if hasattr(pygame.image, "tobytes"):
        return pygame.image.tobytes(surface, "RGBA", True)
    return pygame.image.tostring(surface, "RGBA", True)


def _gl_float_buffer(data):
    """Wrap float mesh data for PyOpenGL (Python 3.14 needs memoryview, not array.array)."""
    if isinstance(data, memoryview):
        return data
    return memoryview(data)

# ─── Configuration ───────────────────────────────────────────────────────────

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600
FOV = 75
NEAR_PLANE = 0.1
FAR_PLANE = 200.0
MOUSE_SENSITIVITY = 0.15
GRAVITY = -20.0
JUMP_SPEED = 8.0
MOVE_SPEED = 5.0
REACH_DISTANCE = 6.0
TARGET_FPS = 60
CHUNK_SIZE = 16
RENDER_DISTANCE = 4
BOOT_RENDER_DISTANCE = 2
MESH_BUILD_BUDGET = 3
WORLD_HEIGHT = 64
SEA_LEVEL = 32
MAX_HEALTH = 20
FALL_DAMAGE_THRESHOLD = 4.0
MOB_SPAWN_COUNT = 12

LEVEL_THEMES = ("Normal", "Hell", "Sky", "Paradise", "Woods")
LEVEL_TYPES = ("Island", "Floating", "Flat")
BLOCK_NAMES = {}

# Color palette (classic Infdev)
COLORS = {
    "grass": (0.30, 0.55, 0.15),
    "grass_top": (0.35, 0.65, 0.20),
    "dirt": (0.50, 0.35, 0.20),
    "stone": (0.50, 0.50, 0.50),
    "cobblestone": (0.45, 0.45, 0.45),
    "gravel": (0.55, 0.55, 0.55),
    "wood": (0.40, 0.25, 0.10),
    "leaves": (0.15, 0.40, 0.10),
    "water": (0.10, 0.30, 0.60),
    "lava": (0.90, 0.35, 0.05),
    "sand": (0.75, 0.70, 0.50),
    "planks": (0.60, 0.45, 0.20),
    "bedrock": (0.20, 0.20, 0.20),
    "sky_day": (0.53, 0.78, 0.92),
    "sky_night": (0.05, 0.05, 0.15),
    "brick": (0.60, 0.20, 0.10),
    "glass": (0.75, 0.85, 0.95),
    "cloth": (0.85, 0.85, 0.85),
    "coal_ore": (0.25, 0.25, 0.25),
    "iron_ore": (0.55, 0.50, 0.45),
    "gold_ore": (0.70, 0.60, 0.20),
    "diamond_ore": (0.35, 0.70, 0.75),
    "obsidian": (0.12, 0.08, 0.18),
    "gold_block": (0.90, 0.78, 0.15),
    "iron_block": (0.78, 0.78, 0.78),
    "mossy_stone": (0.35, 0.45, 0.30),
    "bookshelf": (0.55, 0.40, 0.20),
    "tnt": (0.85, 0.20, 0.20),
    "hell_stone": (0.35, 0.10, 0.10),
    "hell_sand": (0.45, 0.15, 0.05),
    "cloud": (1.0, 1.0, 1.0),
    "pig": (0.90, 0.65, 0.65),
    "zombie": (0.35, 0.55, 0.30),
    "skeleton": (0.80, 0.80, 0.75),
}


class BlockType(Enum):
    AIR = 0
    GRASS = 1
    DIRT = 2
    STONE = 3
    WOOD = 4
    LEAVES = 5
    WATER = 6
    SAND = 7
    PLANKS = 8
    BEDROCK = 9
    BRICK = 10
    COBBLESTONE = 11
    GRAVEL = 12
    GLASS = 13
    CLOTH = 14
    COAL_ORE = 15
    IRON_ORE = 16
    GOLD_ORE = 17
    DIAMOND_ORE = 18
    LAVA = 19
    OBSIDIAN = 20
    GOLD_BLOCK = 21
    IRON_BLOCK = 22
    MOSSY_STONE = 23
    BOOKSHELF = 24
    TNT = 25
    HELL_STONE = 26
    HELL_SAND = 27


BLOCK_PROPERTIES = {
    BlockType.AIR: {"solid": False, "transparent": True, "color": None, "fluid": False, "name": "Air"},
    BlockType.GRASS: {"solid": True, "transparent": False, "color": "grass", "fluid": False, "name": "Grass"},
    BlockType.DIRT: {"solid": True, "transparent": False, "color": "dirt", "fluid": False, "name": "Dirt"},
    BlockType.STONE: {"solid": True, "transparent": False, "color": "stone", "fluid": False, "name": "Stone"},
    BlockType.WOOD: {"solid": True, "transparent": False, "color": "wood", "fluid": False, "name": "Wood"},
    BlockType.LEAVES: {"solid": True, "transparent": True, "color": "leaves", "fluid": False, "name": "Leaves"},
    BlockType.WATER: {"solid": False, "transparent": True, "color": "water", "fluid": True, "name": "Water"},
    BlockType.SAND: {"solid": True, "transparent": False, "color": "sand", "fluid": False, "name": "Sand"},
    BlockType.PLANKS: {"solid": True, "transparent": False, "color": "planks", "fluid": False, "name": "Planks"},
    BlockType.BEDROCK: {"solid": True, "transparent": False, "color": "bedrock", "fluid": False, "name": "Bedrock"},
    BlockType.BRICK: {"solid": True, "transparent": False, "color": "brick", "fluid": False, "name": "Brick"},
    BlockType.COBBLESTONE: {"solid": True, "transparent": False, "color": "cobblestone", "fluid": False, "name": "Cobblestone"},
    BlockType.GRAVEL: {"solid": True, "transparent": False, "color": "gravel", "fluid": False, "name": "Gravel"},
    BlockType.GLASS: {"solid": True, "transparent": True, "color": "glass", "fluid": False, "name": "Glass"},
    BlockType.CLOTH: {"solid": True, "transparent": False, "color": "cloth", "fluid": False, "name": "Cloth"},
    BlockType.COAL_ORE: {"solid": True, "transparent": False, "color": "coal_ore", "fluid": False, "name": "Coal Ore"},
    BlockType.IRON_ORE: {"solid": True, "transparent": False, "color": "iron_ore", "fluid": False, "name": "Iron Ore"},
    BlockType.GOLD_ORE: {"solid": True, "transparent": False, "color": "gold_ore", "fluid": False, "name": "Gold Ore"},
    BlockType.DIAMOND_ORE: {"solid": True, "transparent": False, "color": "diamond_ore", "fluid": False, "name": "Diamond Ore"},
    BlockType.LAVA: {"solid": False, "transparent": True, "color": "lava", "fluid": True, "name": "Lava"},
    BlockType.OBSIDIAN: {"solid": True, "transparent": False, "color": "obsidian", "fluid": False, "name": "Obsidian"},
    BlockType.GOLD_BLOCK: {"solid": True, "transparent": False, "color": "gold_block", "fluid": False, "name": "Gold Block"},
    BlockType.IRON_BLOCK: {"solid": True, "transparent": False, "color": "iron_block", "fluid": False, "name": "Iron Block"},
    BlockType.MOSSY_STONE: {"solid": True, "transparent": False, "color": "mossy_stone", "fluid": False, "name": "Mossy Stone"},
    BlockType.BOOKSHELF: {"solid": True, "transparent": False, "color": "bookshelf", "fluid": False, "name": "Bookshelf"},
    BlockType.TNT: {"solid": True, "transparent": False, "color": "tnt", "fluid": False, "name": "TNT"},
    BlockType.HELL_STONE: {"solid": True, "transparent": False, "color": "hell_stone", "fluid": False, "name": "Hell Rock"},
    BlockType.HELL_SAND: {"solid": True, "transparent": False, "color": "hell_sand", "fluid": False, "name": "Hell Sand"},
}

HOTBAR_BLOCKS = [
    BlockType.DIRT, BlockType.STONE, BlockType.COBBLESTONE, BlockType.PLANKS,
    BlockType.WOOD, BlockType.BRICK, BlockType.GLASS, BlockType.SAND,
    BlockType.GRAVEL, BlockType.CLOTH, BlockType.TNT, BlockType.BOOKSHELF,
]

for _bt in BlockType:
    BLOCK_NAMES[_bt] = BLOCK_PROPERTIES[_bt]["name"]

# ─── AI Chat ─────────────────────────────────────────────────────────────────

AI_RESPONSES = {
    "hello": ["Hello, builder!", "Hi! Ready to craft?", "Hey! The world is yours to shape."],
    "hi": ["Hello, builder!", "Hi! Ready to craft?", "Hey! The world is yours to shape."],
    "how are you": ["I am doing great and ready to help you build.", "Feeling blocky today. How about you?"],
    "help": [
        "WASD move | Space jump | Mouse break/place | Scroll wheel hotbar",
        "E inventory | T chat | ESC pause | F fullscreen",
        "Survive the night. Mine ores. Build shelter.",
    ],
    "build": ["Let's build something amazing!", "Great idea! What should we make?", "I love building with you."],
    "mine": ["Dig deep and look for rare ores.", "Be careful near cliffs.", "Mining is the heart of survival."],
    "craft": ["Collect resources and combine them.", "Crafting opens up endless possibilities.", "Every block starts with a plan."],
    "creeper": ["Sssss... boom! Watch your distance.", "Creepers are explosive troublemakers.", "A creeper once blew up my house."],
    "diamond": ["Diamonds are rare. Look deep underground.", "Found diamonds? Nice work.", "Diamonds are a builder's best friend."],
    "night": ["It is getting dark. Build a shelter.", "Nights are dangerous. Stay safe.", "Monsters come out after sunset."],
    "water": ["Water is useful for farming and travel.", "Watch out for drowning.", "Water flows and can be collected."],
    "tree": ["Trees provide wood for building.", "Punch a tree to get started.", "Remember to replant when you can."],
    "default": [
        "I am your AI assistant in this blocky world.",
        "That is interesting. Tell me more.",
        "In Minecraft Infdev, the possibilities are endless.",
        "Have you explored the world yet?",
        "Every block tells a story.",
        "The world is generated procedurally. Go explore!",
        "Try building a house or digging a mine.",
    ],
}


class AIChat:
    def __init__(self):
        self.messages = [
            {"role": "assistant", "content": "Welcome to Minecraft Infdev. Type help for controls. Survive, mine, and build."}
        ]
        self.input_buffer = ""
        self.active = False
        self.scroll_offset = 0

    def get_response(self, message: str) -> str:
        msg = message.lower().strip()
        for key in AI_RESPONSES:
            if key in msg:
                return random.choice(AI_RESPONSES[key])
        return random.choice(AI_RESPONSES["default"])

    def send_message(self, message: str):
        if not message.strip():
            return
        self.messages.append({"role": "user", "content": message.strip()})
        response = self.get_response(message)
        self.messages.append({"role": "assistant", "content": response})
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]

    def toggle(self):
        self.active = not self.active
        if self.active:
            self.input_buffer = ""


# ─── 3D Utilities ────────────────────────────────────────────────────────────

@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Vec3):
            return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
        return NotImplemented

    def __mul__(self, scalar):
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __neg__(self):
        return Vec3(-self.x, -self.y, -self.z)

    def __getitem__(self, idx):
        return (self.x, self.y, self.z)[idx]

    def __setitem__(self, idx, val):
        if idx == 0:
            self.x = val
        elif idx == 1:
            self.y = val
        elif idx == 2:
            self.z = val
        else:
            raise IndexError(idx)

    def __len__(self):
        return 3

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def normalize(self):
        l = self.length()
        if l == 0:
            return Vec3()
        return Vec3(self.x / l, self.y / l, self.z / l)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def to_tuple(self):
        return (self.x, self.y, self.z)

    def to_int_tuple(self):
        return (int(self.x), int(self.y), int(self.z))

    @staticmethod
    def from_tuple(t):
        return Vec3(t[0], t[1], t[2])


def normalize_angle(angle):
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle


class Inventory:
    """Infdev survival inventory (files=off, in-memory only)."""

    def __init__(self, creative=False):
        self.creative = creative
        self.counts = defaultdict(int)
        if not creative:
            self.counts[BlockType.DIRT] = 64
            self.counts[BlockType.STONE] = 64
            self.counts[BlockType.PLANKS] = 32
            self.counts[BlockType.WOOD] = 16

    def add(self, block_type, amount=1):
        if block_type == BlockType.AIR:
            return
        self.counts[block_type] += amount

    def can_place(self, block_type):
        return self.creative or self.counts.get(block_type, 0) > 0

    def use(self, block_type):
        if self.creative:
            return True
        if self.counts.get(block_type, 0) <= 0:
            return False
        self.counts[block_type] -= 1
        return True

    def count(self, block_type):
        return 999 if self.creative else self.counts.get(block_type, 0)


@dataclass
class Mob:
    kind: str
    pos: Vec3
    velocity: Vec3 = field(default_factory=Vec3)
    health: float = 10.0
    alive: bool = True
    cooldown: float = 0.0

    def color_name(self):
        return "pig" if self.kind == "pig" else ("zombie" if self.kind == "zombie" else "skeleton")

    def hostile(self):
        return self.kind in ("zombie", "skeleton")


def _value_noise(x, y, z, seed):
    n = math.sin(x * 12.9898 + y * 78.233 + z * 37.719 + seed * 0.017) * 43758.5453
    return n - math.floor(n)


def _smooth_noise(x, y, z, seed):
    xf, yf, zf = math.floor(x), math.floor(y), math.floor(z)
    tx, ty, tz = x - xf, y - yf, z - zf
    c000 = _value_noise(xf, yf, zf, seed)
    c100 = _value_noise(xf + 1, yf, zf, seed)
    c010 = _value_noise(xf, yf + 1, zf, seed)
    c110 = _value_noise(xf + 1, yf + 1, zf, seed)
    c001 = _value_noise(xf, yf, zf + 1, seed)
    c101 = _value_noise(xf + 1, yf, zf + 1, seed)
    c011 = _value_noise(xf, yf + 1, zf + 1, seed)
    c111 = _value_noise(xf + 1, yf + 1, zf + 1, seed)
    x00 = c000 * (1 - tx) + c100 * tx
    x10 = c010 * (1 - tx) + c110 * tx
    x01 = c001 * (1 - tx) + c101 * tx
    x11 = c011 * (1 - tx) + c111 * tx
    y0 = x00 * (1 - ty) + x10 * ty
    y1 = x01 * (1 - ty) + x11 * ty
    return y0 * (1 - tz) + y1 * tz


# ─── World Generation (Infdev-style) ─────────────────────────────────────────

class World:
    def __init__(self, seed=None, theme="Normal", level_type="Island"):
        self.blocks = {}
        self.chunk_blocks = defaultdict(dict)
        self.generated_chunks = set()
        self.dirty_chunks = set()
        self.seed = seed if seed is not None else random.randint(0, 2 ** 31 - 1)
        self.theme = theme if theme in LEVEL_THEMES else "Normal"
        self.level_type = level_type if level_type in LEVEL_TYPES else "Island"
        print(f"Generating Infdev world | type={self.level_type} theme={self.theme} seed={self.seed}")

    def ensure_chunks_around(self, px, pz, radius=RENDER_DISTANCE):
        cx0 = int(px // CHUNK_SIZE)
        cz0 = int(pz // CHUNK_SIZE)
        for cx in range(cx0 - radius, cx0 + radius + 1):
            for cz in range(cz0 - radius, cz0 + radius + 1):
                if (cx, cz) not in self.generated_chunks:
                    self._generate_chunk(cx, cz)

    def _generate_chunk(self, cx, cz):
        self.generated_chunks.add((cx, cz))
        rng = random.Random(self.seed ^ (cx * 92837111) ^ (cz * 689287499))
        cx_min = cx * CHUNK_SIZE
        cz_min = cz * CHUNK_SIZE
        tree_positions = []
        height_map = {}

        for x in range(cx_min, cx_min + CHUNK_SIZE):
            for z in range(cz_min, cz_min + CHUNK_SIZE):
                height_map[(x, z)] = self._terrain_height(x, z)

        for x in range(cx_min, cx_min + CHUNK_SIZE):
            for z in range(cz_min, cz_min + CHUNK_SIZE):
                h = height_map[(x, z)]
                self._fill_column(x, z, h, rng)
                if self.theme == "Woods" and rng.random() < 0.22 and h >= SEA_LEVEL - 2:
                    tree_positions.append((x, h + 1, z))
                elif self.theme == "Normal" and x % 5 == 0 and z % 5 == 0 and rng.random() < 0.12 and h >= SEA_LEVEL:
                    tree_positions.append((x, h + 1, z))

        self._carve_caves(cx_min, cz_min, rng)
        self._place_ores(cx_min, cz_min, rng)
        for tx, ty, tz in tree_positions:
            self._place_tree(tx, ty, tz, rng)

    def _fill_column(self, x, z, h, rng):
        if self.theme == "Hell":
            surface = BlockType.HELL_SAND if h < SEA_LEVEL + 2 else BlockType.HELL_STONE
            for y in range(max(1, h + 1)):
                if y == 0:
                    bt = BlockType.BEDROCK
                elif y == h:
                    bt = surface
                elif y > h - 3:
                    bt = BlockType.HELL_STONE
                else:
                    bt = BlockType.STONE
                self._set_block_raw(x, y, z, bt)
            if rng.random() < 0.02 and h < 20:
                self._set_block_raw(x, h + 1, z, BlockType.LAVA)
            return

        if self.theme == "Sky":
            if h < SEA_LEVEL - 8:
                return
            for y in range(h + 1):
                if y == 0:
                    bt = BlockType.BEDROCK
                elif y == h:
                    bt = BlockType.GRASS
                elif y > h - 3:
                    bt = BlockType.DIRT
                else:
                    bt = BlockType.STONE
                self._set_block_raw(x, y, z, bt)
            return

        if self.theme == "Paradise":
            h = max(h, SEA_LEVEL)
            for y in range(h + 1):
                if y == 0:
                    bt = BlockType.BEDROCK
                elif y == h:
                    bt = BlockType.GRASS
                elif y > h - 2:
                    bt = BlockType.DIRT
                else:
                    bt = BlockType.STONE
                self._set_block_raw(x, y, z, bt)
            return

        # Normal / Woods
        for y in range(h + 1):
            if y == 0:
                bt = BlockType.BEDROCK
            elif y == h:
                bt = BlockType.GRASS if h >= SEA_LEVEL else BlockType.SAND
            elif y > h - 4:
                bt = BlockType.DIRT
            else:
                bt = BlockType.STONE
            self._set_block_raw(x, y, z, bt)
        if h < SEA_LEVEL:
            for y in range(h + 1, SEA_LEVEL + 1):
                self._set_block_raw(x, y, z, BlockType.WATER)

    def _terrain_height(self, x, z):
        if self.level_type == "Flat":
            return SEA_LEVEL + 1
        if self.level_type == "Island":
            dist = math.sqrt(x * x + z * z)
            if dist > 96:
                return max(1, SEA_LEVEL - 18)
            falloff = max(0.0, 1.0 - dist / 96.0)
            n = _smooth_noise(x * 0.05, 0, z * 0.05, self.seed)
            return max(2, int(SEA_LEVEL + (n - 0.35) * 22 * falloff))
        if self.level_type == "Floating":
            plate = _smooth_noise(x * 0.02, 0, z * 0.02, self.seed + 31)
            if plate < 0.42:
                return 0
            n = _smooth_noise(x * 0.06, 0, z * 0.06, self.seed + 77)
            return max(8, int(SEA_LEVEL + 10 + n * 14))
        if self.theme == "Sky":
            island = _smooth_noise(x * 0.04, 0, z * 0.04, self.seed)
            return max(8, int(SEA_LEVEL + 8 + island * 18))
        if self.theme == "Paradise":
            return SEA_LEVEL + 1
        if self.theme == "Hell":
            base = SEA_LEVEL - 6
            n = _smooth_noise(x * 0.05, 0, z * 0.05, self.seed + 99)
            return max(4, int(base + n * 10))
        n1 = _smooth_noise(x * 0.03, 0, z * 0.03, self.seed)
        n2 = _smooth_noise(x * 0.08, 0, z * 0.08, self.seed + 17) * 0.5
        return max(2, int(SEA_LEVEL + (n1 + n2 - 0.8) * 18))

    def _carve_caves(self, cx_min, cz_min, rng):
        for x in range(cx_min, cx_min + CHUNK_SIZE):
            for z in range(cz_min, cz_min + CHUNK_SIZE):
                for y in range(1, SEA_LEVEL + 18):
                    bt = self.get_block(x, y, z)
                    if bt not in (BlockType.STONE, BlockType.DIRT, BlockType.GRAVEL):
                        continue
                    cave = _smooth_noise(x * 0.09, y * 0.09, z * 0.09, self.seed + 500)
                    worm = _smooth_noise(x * 0.15 + 20, y * 0.12, z * 0.15, self.seed + 900)
                    if cave > 0.62 and worm > 0.55:
                        self._set_block_raw(x, y, z, BlockType.AIR)

    def _place_ores(self, cx_min, cz_min, rng):
        ore_rules = [
            (BlockType.COAL_ORE, 6, 48, 0.018),
            (BlockType.IRON_ORE, 4, 42, 0.010),
            (BlockType.GOLD_ORE, 4, 28, 0.004),
            (BlockType.DIAMOND_ORE, 3, 16, 0.002),
            (BlockType.GRAVEL, 2, 55, 0.008),
        ]
        for x in range(cx_min, cx_min + CHUNK_SIZE):
            for z in range(cz_min, cz_min + CHUNK_SIZE):
                for y in range(1, 50):
                    if self.get_block(x, y, z) != BlockType.STONE:
                        continue
                    r = rng.random()
                    for ore, min_y, max_y, chance in ore_rules:
                        if min_y <= y <= max_y and r < chance:
                            self._set_block_raw(x, y, z, ore)
                            break

    def _place_tree(self, x, y, z, rng):
        trunk = 4 + rng.randint(0, 2)
        for dy in range(trunk):
            self.set_block(x, y + dy, z, BlockType.WOOD)
        radius = 2
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                for dy in range(-1, 2):
                    if abs(dx) + abs(dz) + abs(dy) > radius + 1:
                        continue
                    if dx == 0 and dz == 0 and dy < 2:
                        continue
                    lx, ly, lz = x + dx, y + trunk + dy, z + dz
                    if self.get_block(lx, ly, lz) in (BlockType.AIR, BlockType.LEAVES):
                        self.set_block(lx, ly, lz, BlockType.LEAVES)

    def _set_block_raw(self, x, y, z, block_type):
        key = (int(x), int(y), int(z))
        chunk_key = (key[0] // CHUNK_SIZE, key[2] // CHUNK_SIZE)
        if block_type == BlockType.AIR:
            self.blocks.pop(key, None)
            self.chunk_blocks[chunk_key].pop(key, None)
        else:
            self.blocks[key] = block_type
            self.chunk_blocks[chunk_key][key] = block_type

    def get_block(self, x, y, z):
        return self.blocks.get((int(x), int(y), int(z)), BlockType.AIR)

    def get_ground_y(self, x, z):
        """Return standing Y above solid ground at x,z."""
        ix, iz = int(x), int(z)
        self.ensure_chunks_around(ix, iz, 1)
        for y in range(WORLD_HEIGHT - 1, 0, -1):
            below = self.get_block(ix, y, iz)
            if BLOCK_PROPERTIES[below]["solid"]:
                return float(y + 1)
        return float(SEA_LEVEL + 6)

    def set_block(self, x, y, z, block_type):
        x, y, z = int(x), int(y), int(z)
        self._set_block_raw(x, y, z, block_type)
        cx, cz = x // CHUNK_SIZE, z // CHUNK_SIZE
        self.dirty_chunks.add((cx, cz))
        if x % CHUNK_SIZE == 0:
            self.dirty_chunks.add((cx - 1, cz))
        if x % CHUNK_SIZE == CHUNK_SIZE - 1:
            self.dirty_chunks.add((cx + 1, cz))
        if z % CHUNK_SIZE == 0:
            self.dirty_chunks.add((cx, cz - 1))
        if z % CHUNK_SIZE == CHUNK_SIZE - 1:
            self.dirty_chunks.add((cx, cz + 1))

    def get_chunk_blocks(self, cx, cz):
        return self.chunk_blocks.get((cx, cz), {})

    def find_spawn(self, px=0, pz=0):
        self.ensure_chunks_around(px, pz, 2)
        for y in range(WORLD_HEIGHT - 1, 0, -1):
            below = self.get_block(int(px), y, int(pz))
            feet = self.get_block(int(px), y + 1, int(pz))
            head = self.get_block(int(px), y + 2, int(pz))
            if BLOCK_PROPERTIES[below]["solid"] and feet == BlockType.AIR and head == BlockType.AIR:
                return Vec3(px, y + 1.0, pz)
        return Vec3(px, SEA_LEVEL + 6, pz)

    def hit_test(self, origin, direction, max_dist=REACH_DISTANCE):
        pos = Vec3.from_tuple(origin)
        dir = direction.normalize()
        distance = 0.0
        while distance < max_dist:
            block_pos = (int(pos.x), int(pos.y), int(pos.z))
            block = self.get_block(*block_pos)
            if block != BlockType.AIR and BLOCK_PROPERTIES[block]["solid"]:
                return block_pos, block
            pos = pos + dir * 0.1
            distance += 0.1
        return None, None

    def get_block_face(self, origin, direction, hit_pos):
        entry = Vec3.from_tuple(origin)
        t_min = float("inf")
        best_axis = -1
        best_sign = 0
        eps = 1e-6
        for i, axis in enumerate(("x", "y", "z")):
            if abs(direction[i]) < eps:
                continue
            if direction[i] > 0:
                t = (hit_pos[i] + 0.5 - entry[i]) / direction[i]
            else:
                t = (hit_pos[i] - 0.5 - entry[i]) / direction[i]
            if 0 <= t < t_min:
                t_min = t
                best_axis = i
                best_sign = 1 if direction[i] > 0 else -1
        face = Vec3(0, 0, 0)
        if best_axis >= 0:
            setattr(face, ("x", "y", "z")[best_axis], best_sign)
        return face

    def is_fluid_at(self, x, y, z):
        bt = self.get_block(int(x), int(y), int(z))
        return BLOCK_PROPERTIES[bt]["fluid"]


# ─── Mesh Builder ────────────────────────────────────────────────────────────

# Face definitions: vertices, normals
FACE_DATA = {
    "front": {  # +Z
        "verts": [
            (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5),
            (-0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
        ],
        "normal": (0, 0, 1),
    },
    "back": {  # -Z
        "verts": [
            (0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5),
            (0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5),
        ],
        "normal": (0, 0, -1),
    },
    "right": {  # +X
        "verts": [
            (0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5),
            (0.5, -0.5, 0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5),
        ],
        "normal": (1, 0, 0),
    },
    "left": {  # -X
        "verts": [
            (-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5),
            (-0.5, -0.5, -0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5),
        ],
        "normal": (-1, 0, 0),
    },
    "top": {  # +Y
        "verts": [
            (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5),
            (-0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
        ],
        "normal": (0, 1, 0),
    },
    "bottom": {  # -Y
        "verts": [
            (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, -0.5, -0.5),
            (-0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (-0.5, -0.5, -0.5),
        ],
        "normal": (0, -1, 0),
    },
}

OPPOSITE_FACE = {
    "front": "back",
    "back": "front",
    "right": "left",
    "left": "right",
    "top": "bottom",
    "bottom": "top",
}


def get_face_name_from_normal(normal):
    xn, yn, zn = normal
    if xn > 0:
        return "right"
    if xn < 0:
        return "left"
    if yn > 0:
        return "top"
    if yn < 0:
        return "bottom"
    if zn > 0:
        return "front"
    if zn < 0:
        return "back"
    return "top"


def build_chunk_mesh(world, cx, cz):
    """Build CPU-side mesh arrays for OpenGL 2.1 client-state rendering."""
    vertices = []
    normals = []
    colors = []

    chunk_blocks = world.get_chunk_blocks(cx, cz)
    if not chunk_blocks:
        return None

    for (bx, by, bz), block_type in chunk_blocks.items():
        if block_type == BlockType.AIR:
            continue
        props = BLOCK_PROPERTIES[block_type]
        color_name = props["color"]
        base_color = COLORS.get(color_name, (1, 1, 1))
        alpha = 0.55 if props["fluid"] else 1.0

        for face_name, face in FACE_DATA.items():
            nx, ny, nz = bx, by, bz
            if face_name == "front":
                nz += 1
            elif face_name == "back":
                nz -= 1
            elif face_name == "right":
                nx += 1
            elif face_name == "left":
                nx -= 1
            elif face_name == "top":
                ny += 1
            elif face_name == "bottom":
                ny -= 1

            neighbor = world.get_block(nx, ny, nz)
            neighbor_props = BLOCK_PROPERTIES.get(neighbor, BLOCK_PROPERTIES[BlockType.AIR])
            if neighbor == block_type and props["fluid"]:
                continue
            if neighbor_props["transparent"] or neighbor == BlockType.AIR:
                for vert in face["verts"]:
                    vx = bx + vert[0]
                    vy = by + vert[1]
                    vz = bz + vert[2]
                    vertices.extend([vx, vy, vz])
                    normals.extend(face["normal"])
                    shade = 0.8 if face_name == "bottom" else 1.0
                    if face_name == "top" and block_type == BlockType.GRASS:
                        c = COLORS["grass_top"]
                    else:
                        c = base_color
                    colors.extend([c[0] * shade * alpha, c[1] * shade * alpha, c[2] * shade * alpha])

    if not vertices:
        return None

    verts = array.array("f", vertices)
    norms = array.array("f", normals)
    cols = array.array("f", colors)
    return {
        "vertices": _gl_float_buffer(verts),
        "normals": _gl_float_buffer(norms),
        "colors": _gl_float_buffer(cols),
        "count": len(vertices) // 3,
    }


def draw_chunk_mesh(mesh):
    """Draw a chunk mesh with legacy OpenGL 2.1 client arrays."""
    if not mesh or mesh["count"] <= 0:
        return
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_NORMAL_ARRAY)
    glEnableClientState(GL_COLOR_ARRAY)
    glVertexPointer(3, GL_FLOAT, 0, _gl_float_buffer(mesh["vertices"]))
    glNormalPointer(GL_FLOAT, 0, _gl_float_buffer(mesh["normals"]))
    glColorPointer(3, GL_FLOAT, 0, _gl_float_buffer(mesh["colors"]))
    glDrawArrays(GL_TRIANGLES, 0, mesh["count"])
    glDisableClientState(GL_COLOR_ARRAY)
    glDisableClientState(GL_NORMAL_ARRAY)
    glDisableClientState(GL_VERTEX_ARRAY)


def draw_colored_cube(center, size, color):
    """Draw a simple mob/entity cube."""
    cx, cy, cz = center
    hs = size * 0.5
    glDisable(GL_LIGHTING)
    glColor3f(*color)
    glBegin(GL_QUADS)
    for face in (
        ((cx - hs, cy - hs, cz + hs), (cx + hs, cy - hs, cz + hs), (cx + hs, cy + hs, cz + hs), (cx - hs, cy + hs, cz + hs)),
        ((cx + hs, cy - hs, cz - hs), (cx - hs, cy - hs, cz - hs), (cx - hs, cy + hs, cz - hs), (cx + hs, cy + hs, cz - hs)),
        ((cx - hs, cy + hs, cz - hs), (cx - hs, cy + hs, cz + hs), (cx + hs, cy + hs, cz + hs), (cx + hs, cy + hs, cz - hs)),
        ((cx - hs, cy - hs, cz + hs), (cx - hs, cy - hs, cz - hs), (cx + hs, cy - hs, cz - hs), (cx + hs, cy - hs, cz + hs)),
        ((cx + hs, cy - hs, cz + hs), (cx + hs, cy - hs, cz - hs), (cx + hs, cy + hs, cz - hs), (cx + hs, cy + hs, cz + hs)),
        ((cx - hs, cy - hs, cz - hs), (cx - hs, cy - hs, cz + hs), (cx - hs, cy + hs, cz + hs), (cx - hs, cy + hs, cz - hs)),
    ):
        for vx, vy, vz in face:
            glVertex3f(vx, vy, vz)
    glEnd()
    glEnable(GL_LIGHTING)


def draw_cloud_layer(player_pos, time_of_day, seed):
    """Infdev-style drifting clouds."""
    glDisable(GL_LIGHTING)
    glColor4f(1.0, 1.0, 1.0, 0.85)
    glEnable(GL_BLEND)
    y = SEA_LEVEL + 24 + math.sin(time_of_day * math.pi) * 2
    for i in range(10):
        ox = ((i * 37 + int(player_pos.x)) % 140) - 70
        oz = ((i * 53 + int(player_pos.z)) % 140) - 70
        w = 10 + (i % 4) * 3
        glBegin(GL_QUADS)
        glVertex3f(player_pos.x + ox, y, player_pos.z + oz)
        glVertex3f(player_pos.x + ox + w, y, player_pos.z + oz)
        glVertex3f(player_pos.x + ox + w, y, player_pos.z + oz + w * 0.6)
        glVertex3f(player_pos.x + ox, y, player_pos.z + oz + w * 0.6)
        glEnd()
    glDisable(GL_BLEND)
    glEnable(GL_LIGHTING)


# ─── Game State ──────────────────────────────────────────────────────────────

class GameState(Enum):
    MENU = 1
    LEVEL_GEN = 2
    PLAYING = 3
    PAUSED = 4
    OPTIONS = 5


# ─── Main Application ────────────────────────────────────────────────────────

class DeepSeekCraftR1:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.mouse.set_visible(True)
        pygame.display.set_caption("DeepSeekCraftR1 - Minecraft Infdev")
        self.icon = pygame.Surface((32, 32))
        self.icon.fill((50, 50, 50))
        pygame.display.set_icon(self.icon)

        # Handle fullscreen toggle
        self.fullscreen = False
        self.sw = SCREEN_WIDTH
        self.sh = SCREEN_HEIGHT
        # Menus use plain pygame (reliable mouse clicks); gameplay uses OpenGL.
        self.gl_mode = False
        self.screen = pygame.display.set_mode((self.sw, self.sh), DOUBLEBUF)
        self.sw, self.sh = self.screen.get_size()
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MENU
        self.dt = 0.0
        self.fps = 0
        self.frame_time = 0
        self.last_time = time.time()

        # OpenGL setup (enabled when entering gameplay)
        if not HAS_OPENGL:
            print("WARNING: PyOpenGL not found. Running in fallback mode.")

        # Game objects
        self.world = None
        self.inventory = Inventory(creative=False)
        self.player_pos = Vec3(0, 40, 0)
        self.velocity = Vec3(0, 0, 0)
        self.on_ground = False
        self.yaw = 0
        self.pitch = 0
        self.selected_block_idx = 0
        self.show_chat = False
        self.show_inventory = False
        self.health = MAX_HEALTH
        self.mobs = []
        self.fall_distance = 0.0
        self.hurt_timer = 0.0
        self.mouse_locked = False

        # Level generation settings (Infdev menu)
        self.level_theme_idx = 0
        self.level_type_idx = 0
        self.level_seed = random.randint(0, 999999)
        self.level_gen_selection = 0

        # Chat
        self.chat = AIChat()

        # Menu items
        self.menu_buttons = []
        self.menu_selection = 0
        self.menu_anim_time = 0

        # Sky
        self.sky_rotation = 0
        self.time_of_day = 0.5  # 0-1, 0.5 = noon
        self.day_length = 120.0  # seconds for full day

        # Build initial menu
        self._build_menu()

        # Font
        try:
            self.font = pygame.font.Font(None, 28)
            self.font_small = pygame.font.Font(None, 20)
            self.font_title = pygame.font.Font(None, 72)
            self.font_chat = pygame.font.Font(None, 22)
        except Exception:
            self.font = pygame.font.SysFont("Arial", 28)
            self.font_small = pygame.font.SysFont("Arial", 20)
            self.font_title = pygame.font.SysFont("Arial", 72)
            self.font_chat = pygame.font.SysFont("Arial", 22)

        # World initialized when game starts
        self.chunk_meshes = {}
        self.mesh_queue = []
        self._set_menu_display_mode()

    def _setup_opengl(self):
        glClearColor(0.53, 0.78, 0.92, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def _build_menu(self):
        self.menu_buttons = [
            {"text": "Singleplayer", "action": "singleplayer"},
            {"text": "Options", "action": "options"},
            {"text": "Quit Game", "action": "quit"},
        ]
        self.menu_selection = 0
        self.level_gen_buttons = [
            {"text": "Generate Level", "action": "generate"},
            {"text": "Back", "action": "back"},
        ]

    def start_game(self, seed=None, theme=None, level_type=None, show_progress=True):
        self._free_chunk_meshes()
        theme = theme or LEVEL_THEMES[self.level_theme_idx]
        level_type = level_type or LEVEL_TYPES[self.level_type_idx]
        seed = self.level_seed if seed is None else seed

        if show_progress:
            self._render_loading_message("Preparing world...")
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                    return
        self.world = World(seed=seed, theme=theme, level_type=level_type)
        self.inventory = Inventory(creative=False)
        self.health = MAX_HEALTH
        self.mobs = []
        self.player_pos = Vec3(0, 40, 0)
        self.velocity = Vec3(0, 0, 0)
        self.yaw = 0
        self.pitch = 0
        self.selected_block_idx = 0
        self.show_inventory = False
        self.show_chat = False
        self.fall_distance = 0.0

        boot_radius = BOOT_RENDER_DISTANCE
        coords = []
        for cx in range(-boot_radius, boot_radius + 1):
            for cz in range(-boot_radius, boot_radius + 1):
                coords.append((cx, cz))
        total = len(coords)
        for i, (cx, cz) in enumerate(coords):
            if (cx, cz) not in self.world.generated_chunks:
                self.world._generate_chunk(cx, cz)
            if show_progress and (i % 2 == 0 or i == total - 1):
                pct = int(100 * (i + 1) / total)
                self._render_loading_message(f"Generating level... {pct}%")

        self.player_pos = self.world.find_spawn(0, 0)

        needed = sorted(self._ensure_chunks_around_player(mesh_radius=BOOT_RENDER_DISTANCE, build_meshes=False))
        total_meshes = len(needed)
        for i, (cx, cz) in enumerate(needed):
            if (cx, cz) not in self.chunk_meshes:
                mesh = build_chunk_mesh(self.world, cx, cz)
                if mesh:
                    self.chunk_meshes[(cx, cz)] = mesh
            if show_progress and (i % 2 == 0 or i == total_meshes - 1):
                pct = int(100 * (i + 1) / total_meshes)
                self._render_loading_message(f"Building terrain... {pct}%")

        self._set_game_display_mode()
        self.state = GameState.PLAYING
        self.mouse_locked = True
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        self.mesh_queue = []
        self._queue_chunk_meshes(mesh_radius=RENDER_DISTANCE)
        self._spawn_mobs()
        print("Level ready. Survive the night.")

    def _set_menu_display_mode(self):
        """Use software pygame for menus so mouse clicks always work."""
        if not HAS_OPENGL:
            self._prepare_menu_mouse()
            return
        if self.gl_mode:
            self._free_gpu_resources()
            w, h = self.screen.get_size()
            self.screen = pygame.display.set_mode((w, h), DOUBLEBUF)
            self.sw, self.sh = self.screen.get_size()
            self.gl_mode = False
        self._prepare_menu_mouse()

    def _set_game_display_mode(self):
        """Switch to OpenGL for 3D gameplay."""
        if not HAS_OPENGL:
            return
        if not self.gl_mode:
            w, h = self.screen.get_size()
            self.screen = pygame.display.set_mode((w, h), DOUBLEBUF | OPENGL)
            self.sw, self.sh = self.screen.get_size()
            self.gl_mode = True
            self._setup_opengl()
            self._overlay_tex = None
            self._overlay_tex_w = 0
            self._overlay_tex_h = 0

    def _present_menu_overlay(self, overlay):
        if self.gl_mode and HAS_OPENGL:
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self._render_menu_background()
            self._draw_surface_2d(overlay, (0, 0))
        else:
            self._render_menu_background()
            self.screen.blit(overlay, (0, 0))
        pygame.display.flip()

    def _player_chunk_coords(self):
        return int(self.player_pos.x // CHUNK_SIZE), int(self.player_pos.z // CHUNK_SIZE)

    def _queue_chunk_meshes(self, mesh_radius=None):
        if not self.world:
            return set()
        radius = RENDER_DISTANCE if mesh_radius is None else mesh_radius
        self.world.ensure_chunks_around(self.player_pos.x, self.player_pos.z, radius)
        pcx, pcz = self._player_chunk_coords()
        needed = set()
        for cx in range(pcx - radius, pcx + radius + 1):
            for cz in range(pcz - radius, pcz + radius + 1):
                needed.add((cx, cz))
        for key in list(self.chunk_meshes.keys()):
            if key not in needed:
                self.chunk_meshes.pop(key, None)
        queued = set(self.mesh_queue)
        for cx, cz in needed:
            if (cx, cz) not in self.chunk_meshes and (cx, cz) not in queued:
                self.mesh_queue.append((cx, cz))
                queued.add((cx, cz))
        self.mesh_queue.sort(
            key=lambda k: (k[0] - pcx) ** 2 + (k[1] - pcz) ** 2
        )
        return needed

    def _process_mesh_queue(self):
        if not self.world:
            return
        budget = MESH_BUILD_BUDGET
        while self.mesh_queue and budget > 0:
            cx, cz = self.mesh_queue.pop(0)
            if (cx, cz) in self.chunk_meshes:
                continue
            mesh = build_chunk_mesh(self.world, cx, cz)
            if mesh:
                self.chunk_meshes[(cx, cz)] = mesh
            budget -= 1

    def _ensure_chunks_around_player(self, mesh_radius=None, build_meshes=True):
        needed = self._queue_chunk_meshes(mesh_radius=mesh_radius)
        if build_meshes:
            self._process_mesh_queue()
        return needed

    def _spawn_mobs(self):
        rng = random.Random(self.world.seed + 404)
        kinds = ["pig", "pig", "zombie", "skeleton"]
        for i in range(MOB_SPAWN_COUNT):
            angle = rng.random() * math.pi * 2
            dist = 8 + rng.random() * 24
            x = self.player_pos.x + math.cos(angle) * dist
            z = self.player_pos.z + math.sin(angle) * dist
            self.world.ensure_chunks_around(x, z, 1)
            y = self.world.get_ground_y(x, z)
            kind = rng.choice(kinds)
            self.mobs.append(Mob(kind=kind, pos=Vec3(x, y, z), health=8 if kind == "pig" else 12))

    def rebuild_dirty_chunks(self):
        if not self.world or not self.world.dirty_chunks:
            return
        dirty = list(self.world.dirty_chunks)[:MESH_BUILD_BUDGET]
        for key in dirty:
            self.world.dirty_chunks.discard(key)
        pcx, pcz = self._player_chunk_coords()
        for cx, cz in dirty:
            if abs(cx - pcx) > RENDER_DISTANCE + 1 or abs(cz - pcz) > RENDER_DISTANCE + 1:
                continue
            self.chunk_meshes.pop((cx, cz), None)
            mesh = build_chunk_mesh(self.world, cx, cz)
            if mesh:
                self.chunk_meshes[(cx, cz)] = mesh

    def _refresh_screen_size(self):
        self.sw, self.sh = self.screen.get_size()

    def _prepare_menu_mouse(self):
        """Menu screens need a free visible cursor (not grabbed)."""
        if self.mouse_locked or pygame.event.get_grab():
            self.mouse_locked = False
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)

    def _ui_mouse_pos(self, event=None):
        if event is not None and hasattr(event, "pos"):
            mx, my = event.pos
        elif event is not None and isinstance(event, (tuple, list)) and len(event) >= 2:
            mx, my = int(event[0]), int(event[1])
        else:
            mx, my = pygame.mouse.get_pos()
        try:
            ww, wh = pygame.display.get_window_size()
        except Exception:
            ww, wh = self.sw, self.sh
        if ww > 0 and wh > 0 and (ww != self.sw or wh != self.sh):
            mx = int(mx * self.sw / ww)
            my = int(my * self.sh / wh)
        return mx, my

    def _menu_button_rect(self, index):
        y = 280 + index * 60
        return pygame.Rect(self.sw // 2 - 120, y - 18, 240, 40)

    def _level_gen_button_rect(self, index):
        y = 420 + index * 60
        return pygame.Rect(self.sw // 2 - 130, y - 18, 260, 40)

    def _level_gen_theme_rect(self):
        return pygame.Rect(self.sw // 2 - 180, 180, 360, 40)

    def _level_gen_type_rect(self):
        return pygame.Rect(self.sw // 2 - 180, 230, 360, 40)

    def _options_back_rect(self):
        return pygame.Rect(self.sw // 2 - 120, self.sh - 120, 240, 40)

    def _ui_button_at(self, pos, rects):
        mx, my = self._ui_mouse_pos(pos)
        for idx, rect in enumerate(rects):
            if rect.collidepoint(mx, my):
                return idx
        return None

    def _render_loading_message(self, message):
        self._refresh_screen_size()
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        title = self.font_title.render("GENERATING LEVEL", True, (255, 255, 255))
        overlay.blit(title, title.get_rect(center=(self.sw // 2, self.sh // 2 - 40)))
        txt = self.font.render(message, True, (220, 220, 220))
        overlay.blit(txt, txt.get_rect(center=(self.sw // 2, self.sh // 2 + 20)))
        bar_w = 360
        bar = pygame.Rect(self.sw // 2 - bar_w // 2, self.sh // 2 + 60, bar_w, 16)
        pygame.draw.rect(overlay, (40, 40, 40, 220), bar)
        if "%" in message:
            try:
                pct = int(message.rsplit(" ", 1)[-1].rstrip("%"))
                fill = bar.copy()
                fill.width = max(4, int(bar_w * pct / 100))
                pygame.draw.rect(overlay, (90, 160, 255, 230), fill)
            except ValueError:
                pass
        self._present_menu_overlay(overlay)
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
                break
        pygame.event.pump()

    def run(self):
        while self.running:
            elapsed_ms = self.clock.tick(TARGET_FPS)
            self.dt = elapsed_ms / 1000.0 if elapsed_ms > 0 else 1.0 / TARGET_FPS
            if self.dt > 0.1:
                self.dt = 0.1

            self.fps = int(self.clock.get_fps()) if self.clock.get_fps() > 0 else TARGET_FPS
            self.frame_time += self.dt

            if self.state == GameState.MENU:
                self._handle_menu_events()
                self._update_menu()
                self._render_menu()
            elif self.state == GameState.LEVEL_GEN:
                self._handle_level_gen_events()
                self._update_menu()
                self._render_level_gen()
            elif self.state == GameState.OPTIONS:
                self._handle_options_events()
                self._render_options()
            elif self.state == GameState.PLAYING:
                self._handle_game_events()
                self._update_game()
                self._render_game()
            elif self.state == GameState.PAUSED:
                self._handle_pause_events()
                self._render_game()

            # tick() already called at loop start

        self._cleanup()

    def _handle_menu_events(self):
        self._refresh_screen_size()
        self._prepare_menu_mouse()
        menu_rects = [self._menu_button_rect(i) for i in range(len(self.menu_buttons))]
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_UP or event.key == K_w:
                    self.menu_selection = (self.menu_selection - 1) % len(self.menu_buttons)
                elif event.key == K_DOWN or event.key == K_s:
                    self.menu_selection = (self.menu_selection + 1) % len(self.menu_buttons)
                elif event.key == K_RETURN or event.key == K_SPACE:
                    self._activate_menu_item(self.menu_buttons[self.menu_selection])
                elif event.key == K_ESCAPE:
                    self.running = False
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                idx = self._ui_button_at(event, menu_rects)
                if idx is not None:
                    self.menu_selection = idx
                    self._activate_menu_item(self.menu_buttons[idx])

    def _activate_menu_item(self, item):
        action = item["action"]
        if action == "singleplayer":
            self._set_menu_display_mode()
            self.state = GameState.LEVEL_GEN
            self.level_gen_selection = 0
        elif action == "options":
            self._set_menu_display_mode()
            self.state = GameState.OPTIONS
        elif action == "quit":
            self.running = False

    def _handle_level_gen_events(self):
        self._refresh_screen_size()
        self._prepare_menu_mouse()
        btn_rects = [self._level_gen_button_rect(i) for i in range(len(self.level_gen_buttons))]
        theme_rect = self._level_gen_theme_rect()
        type_rect = self._level_gen_type_rect()
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key in (K_LEFT, K_a):
                    self.level_theme_idx = (self.level_theme_idx - 1) % len(LEVEL_THEMES)
                elif event.key in (K_RIGHT, K_d):
                    self.level_theme_idx = (self.level_theme_idx + 1) % len(LEVEL_THEMES)
                elif event.key in (K_q,):
                    self.level_type_idx = (self.level_type_idx - 1) % len(LEVEL_TYPES)
                elif event.key in (K_e,):
                    self.level_type_idx = (self.level_type_idx + 1) % len(LEVEL_TYPES)
                elif event.key == K_r:
                    self.level_seed = random.randint(0, 999999)
                elif event.key == K_UP or event.key == K_w:
                    self.level_gen_selection = (self.level_gen_selection - 1) % len(self.level_gen_buttons)
                elif event.key == K_DOWN or event.key == K_s:
                    self.level_gen_selection = (self.level_gen_selection + 1) % len(self.level_gen_buttons)
                elif event.key == K_RETURN or event.key == K_SPACE:
                    self._activate_level_gen_item(self.level_gen_buttons[self.level_gen_selection])
                elif event.key == K_ESCAPE:
                    self.state = GameState.MENU
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                mx, my = self._ui_mouse_pos(event)
                if theme_rect.collidepoint(mx, my):
                    self.level_theme_idx = (self.level_theme_idx + 1) % len(LEVEL_THEMES)
                    continue
                if type_rect.collidepoint(mx, my):
                    self.level_type_idx = (self.level_type_idx + 1) % len(LEVEL_TYPES)
                    continue
                idx = self._ui_button_at(event, btn_rects)
                if idx is not None:
                    self.level_gen_selection = idx
                    self._activate_level_gen_item(self.level_gen_buttons[idx])

    def _activate_level_gen_item(self, item):
        if item["action"] == "generate":
            self.start_game(
                seed=self.level_seed,
                theme=LEVEL_THEMES[self.level_theme_idx],
                level_type=LEVEL_TYPES[self.level_type_idx],
            )
        elif item["action"] == "back":
            self.state = GameState.MENU
            self._set_menu_display_mode()

    def _render_level_gen(self):
        self._refresh_screen_size()
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        title = self.font_title.render("GENERATE LEVEL", True, (255, 255, 255))
        overlay.blit(title, title.get_rect(center=(self.sw // 2, 90)))
        theme = self.font.render(f"Theme: {LEVEL_THEMES[self.level_theme_idx]}", True, (220, 220, 220))
        overlay.blit(theme, theme.get_rect(center=(self.sw // 2, 200)))
        level_type = self.font.render(f"Type: {LEVEL_TYPES[self.level_type_idx]}", True, (220, 220, 220))
        overlay.blit(level_type, level_type.get_rect(center=(self.sw // 2, 250)))
        hint = self.font_small.render(
            "Click Theme/Type to change | Q/E change type | Left/Right change theme | R new seed",
            True,
            (170, 170, 170),
        )
        overlay.blit(hint, hint.get_rect(center=(self.sw // 2, 290)))
        seed_txt = self.font.render(f"Seed: {self.level_seed}", True, (220, 220, 220))
        overlay.blit(seed_txt, seed_txt.get_rect(center=(self.sw // 2, 340)))
        for i, btn in enumerate(self.level_gen_buttons):
            y = 420 + i * 60
            selected = i == self.level_gen_selection
            btn_surf = pygame.Surface((260, 40), pygame.SRCALPHA)
            btn_surf.fill((60, 60, 60, 180 if selected else 100))
            if selected:
                pygame.draw.rect(btn_surf, (120, 180, 255, 220), btn_surf.get_rect(), 2)
            overlay.blit(btn_surf, (self.sw // 2 - 130, y - 18))
            color = (255, 255, 255) if selected else (180, 180, 180)
            label = self.font.render(btn["text"], True, color)
            overlay.blit(label, label.get_rect(center=(self.sw // 2, y)))
        self._present_menu_overlay(overlay)

    def _handle_options_events(self):
        self._refresh_screen_size()
        self._prepare_menu_mouse()
        back_rect = self._options_back_rect()
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key in (K_ESCAPE, K_RETURN, K_BACKSPACE):
                    self.state = GameState.MENU
                    self._set_menu_display_mode()
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                mx, my = self._ui_mouse_pos(event)
                if back_rect.collidepoint(mx, my):
                    self.state = GameState.MENU
                    self._set_menu_display_mode()

    def _update_menu(self):
        self.menu_anim_time += self.dt
        self.time_of_day = (self.time_of_day + self.dt * 0.02) % 1.0

    def _render_menu(self):
        self._refresh_screen_size()
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)

        # Title
        bounce = math.sin(self.menu_anim_time * 2) * 5
        title = self.font_title.render("DEEPSEEKCRAFTR1", True, (255, 255, 255))
        title_shadow = self.font_title.render("DEEPSEEKCRAFTR1", True, (30, 30, 30))
        overlay.blit(title_shadow, title_shadow.get_rect(center=(self.sw // 2 + 2, 122 + int(bounce))))
        overlay.blit(title, title.get_rect(center=(self.sw // 2, 120 + int(bounce))))

        # Subtitle
        sub = self.font_small.render("Minecraft Infdev - files off", True, (200, 200, 200))
        overlay.blit(sub, sub.get_rect(center=(self.sw // 2, 170)))

        # Buttons
        for i, btn in enumerate(self.menu_buttons):
            y = 280 + i * 60
            selected = i == self.menu_selection
            alpha = 180 if selected else 100
            pulse = math.sin(self.menu_anim_time * 3 + i) * 4 if selected else 0
            btn_surf = pygame.Surface((240, 40), pygame.SRCALPHA)
            btn_surf.fill((60, 60, 60, alpha))
            if selected:
                pygame.draw.rect(btn_surf, (120, 180, 255, 220), btn_surf.get_rect(), 2)
            overlay.blit(btn_surf, (self.sw // 2 - 120, y - 18))

            color = (255, 255, 255) if selected else (180, 180, 180)
            text = self.font.render(btn["text"], True, color)
            overlay.blit(text, text.get_rect(center=(self.sw // 2, y + int(pulse))))

        # Footer
        footer = self.font_small.render(
            "Click a button | Arrow keys or W/S | Enter to select | ESC to quit",
            True,
            (150, 150, 150),
        )
        overlay.blit(footer, footer.get_rect(center=(self.sw // 2, self.sh - 40)))

        self._present_menu_overlay(overlay)

    def _render_options(self):
        self._refresh_screen_size()
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        title = self.font_title.render("OPTIONS", True, (255, 255, 255))
        overlay.blit(title, title.get_rect(center=(self.sw // 2, 120)))

        lines = [
            f"Resolution: {self.sw} x {self.sh}",
            f"Target FPS: {TARGET_FPS}",
            f"Render distance: {RENDER_DISTANCE} chunks",
            f"Mouse sensitivity: {MOUSE_SENSITIVITY}",
            "Fullscreen: press F in game",
            "Click Back or press ESC to return",
        ]
        for i, line in enumerate(lines):
            txt = self.font.render(line, True, (220, 220, 220))
            overlay.blit(txt, txt.get_rect(center=(self.sw // 2, 220 + i * 34)))

        back_rect = self._options_back_rect()
        btn_surf = pygame.Surface((240, 40), pygame.SRCALPHA)
        btn_surf.fill((60, 60, 60, 180))
        pygame.draw.rect(btn_surf, (120, 180, 255, 220), btn_surf.get_rect(), 2)
        overlay.blit(btn_surf, back_rect.topleft)
        back_txt = self.font.render("Back to Menu", True, (255, 255, 255))
        overlay.blit(back_txt, back_txt.get_rect(center=back_rect.center))

        self._present_menu_overlay(overlay)

    def _render_menu_background(self):
        if self.gl_mode and HAS_OPENGL:
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glOrtho(0, self.sw, self.sh, 0, -1, 1)
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_CULL_FACE)

            t = self.time_of_day
            sky_color = (
                0.05 + 0.48 * abs(math.sin(t * math.pi)),
                0.05 + 0.73 * abs(math.sin(t * math.pi)),
                0.15 + 0.77 * abs(math.sin(t * math.pi)),
            )
            glClearColor(*sky_color, 1.0)
            glClear(GL_COLOR_BUFFER_BIT)

            # Draw ground plane
            glBegin(GL_QUADS)
            ground_color = (0.2, 0.35, 0.15)
            glColor3f(*ground_color)
            glVertex2f(0, self.sh * 0.7)
            glVertex2f(self.sw, self.sh * 0.7)
            glColor3f(0.15, 0.25, 0.10)
            glVertex2f(self.sw, self.sh)
            glVertex2f(0, self.sh)
            glEnd()

            # Draw some block silhouettes
            glColor3f(0.15, 0.25, 0.12)
            for i in range(20):
                bx = (i * 73 + int(self.menu_anim_time * 10)) % self.sw
                bh = 20 + int(math.sin(i * 1.5 + self.menu_anim_time) * 15)
                by = self.sh * 0.7 - bh
                bw = 25 + int(math.sin(i * 2.3) * 10)
                glBegin(GL_QUADS)
                glVertex2f(bx, by)
                glVertex2f(bx + bw, by)
                glVertex2f(bx + bw, by + bh)
                glVertex2f(bx, by + bh)
                glEnd()

            glEnable(GL_DEPTH_TEST)
            glEnable(GL_CULL_FACE)
        else:
            t = self.time_of_day
            sky = (
                int((0.05 + 0.48 * abs(math.sin(t * math.pi))) * 255),
                int((0.05 + 0.73 * abs(math.sin(t * math.pi))) * 255),
                int((0.15 + 0.77 * abs(math.sin(t * math.pi))) * 255),
            )
            self.screen.fill(sky)
            ground_rect = pygame.Rect(0, self.sh * 0.7, self.sw, self.sh * 0.3)
            pygame.draw.rect(self.screen, (50, 90, 40), ground_rect)
            for i in range(20):
                bx = (i * 73 + int(self.menu_anim_time * 10)) % self.sw
                bh = 20 + int(math.sin(i * 1.5 + self.menu_anim_time) * 15)
                by = int(self.sh * 0.7 - bh)
                bw = 25 + int(math.sin(i * 2.3) * 10)
                pygame.draw.rect(self.screen, (40, 65, 35), (bx, by, bw, bh))

    def _draw_text_2d(self, text_surface, pos):
        """Draw text onto the OpenGL screen or pygame screen."""
        if HAS_OPENGL:
            text_data = _surface_rgba_bytes(text_surface)
            w, h = text_surface.get_size()

            # Save state
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, self.sw, self.sh, 0, -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_CULL_FACE)

            # Create texture for this frame
            tex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, tex)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

            # Enable blending for text
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            # Draw textured quad
            glEnable(GL_TEXTURE_2D)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0)
            glVertex2f(pos[0] - w // 2, pos[1] - h // 2)
            glTexCoord2f(1, 0)
            glVertex2f(pos[0] + w // 2, pos[1] - h // 2)
            glTexCoord2f(1, 1)
            glVertex2f(pos[0] + w // 2, pos[1] + h // 2)
            glTexCoord2f(0, 1)
            glVertex2f(pos[0] - w // 2, pos[1] + h // 2)
            glEnd()
            glDisable(GL_TEXTURE_2D)
            glDisable(GL_BLEND)

            glDeleteTextures([tex])

            glEnable(GL_DEPTH_TEST)
            glEnable(GL_CULL_FACE)
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
        else:
            self.screen.blit(text_surface, text_surface.get_rect(center=pos))

    def _draw_surface_2d(self, surface, pos):
        """Draw a pygame surface onto the OpenGL screen with texture caching."""
        if HAS_OPENGL:
            data = _surface_rgba_bytes(surface)
            w, h = surface.get_size()

            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, self.sw, self.sh, 0, -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_CULL_FACE)

            # Reuse cached texture if size matches, otherwise recreate
            if not hasattr(self, '_overlay_tex') or self._overlay_tex is None or self._overlay_tex_w != w or self._overlay_tex_h != h:
                if hasattr(self, '_overlay_tex') and self._overlay_tex is not None:
                    glDeleteTextures([self._overlay_tex])
                self._overlay_tex = glGenTextures(1)
                self._overlay_tex_w = w
                self._overlay_tex_h = h
                glBindTexture(GL_TEXTURE_2D, self._overlay_tex)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            else:
                glBindTexture(GL_TEXTURE_2D, self._overlay_tex)
                glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)

            glEnable(GL_BLEND)
            glEnable(GL_TEXTURE_2D)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0)
            glVertex2f(pos[0], pos[1])
            glTexCoord2f(1, 0)
            glVertex2f(pos[0] + w, pos[1])
            glTexCoord2f(1, 1)
            glVertex2f(pos[0] + w, pos[1] + h)
            glTexCoord2f(0, 1)
            glVertex2f(pos[0], pos[1] + h)
            glEnd()
            glDisable(GL_TEXTURE_2D)
            glDisable(GL_BLEND)

            glEnable(GL_DEPTH_TEST)
            glEnable(GL_CULL_FACE)
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
        else:
            self.screen.blit(surface, pos)

    def _free_chunk_meshes(self):
        """Drop cached chunk mesh data."""
        self.chunk_meshes.clear()
        self.mesh_queue = []
        if hasattr(self, '_overlay_tex') and self._overlay_tex is not None:
            try:
                glDeleteTextures([self._overlay_tex])
            except Exception:
                pass
            self._overlay_tex = None
            self._overlay_tex_w = 0
            self._overlay_tex_h = 0

    def _free_gpu_resources(self):
        """Free overlay textures before GL context loss."""
        if not HAS_OPENGL:
            return
        self._free_chunk_meshes()

    def _rebuild_gpu_state(self):
        """Rebuild GL state after display mode changes."""
        if not HAS_OPENGL:
            return
        self._setup_opengl()
        self._overlay_tex = None
        self._overlay_tex_w = 0
        self._overlay_tex_h = 0
        if self.world:
            self._ensure_chunks_around_player()

    def _handle_fullscreen_toggle(self):
        self.fullscreen = not self.fullscreen
        self._free_gpu_resources()
        flags = DOUBLEBUF | OPENGL if self.gl_mode else DOUBLEBUF
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), FULLSCREEN | flags)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        self.sw, self.sh = self.screen.get_size()
        if self.gl_mode:
            self._rebuild_gpu_state()

    def _handle_game_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.state = GameState.PAUSED
                    self.mouse_locked = False
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)
                elif event.key == K_t:
                    self.show_chat = not self.show_chat
                    if self.show_chat:
                        self.chat.active = True
                        self.chat.input_buffer = ""
                        self.mouse_locked = False
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                    else:
                        self.chat.active = False
                        self.mouse_locked = True
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                elif event.key == K_RETURN:
                    if self.show_chat and self.chat.active:
                        self.chat.send_message(self.chat.input_buffer)
                        self.chat.input_buffer = ""
                        self.show_chat = False
                        self.chat.active = False
                        self.mouse_locked = True
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                elif event.key == K_BACKSPACE:
                    if self.show_chat and len(self.chat.input_buffer) > 0:
                        self.chat.input_buffer = self.chat.input_buffer[:-1]
                elif event.key == K_e:
                    self.show_inventory = not self.show_inventory
                elif event.key == K_f:
                    self._handle_fullscreen_toggle()
                elif event.key >= K_1 and event.key <= K_9:
                    idx = event.key - K_1
                    if idx < len(HOTBAR_BLOCKS):
                        self.selected_block_idx = idx
            elif event.type == KEYUP:
                pass
            elif event.type == MOUSEBUTTONDOWN:
                if self.show_chat or self.show_inventory:
                    continue
                if event.button == 1:
                    self._break_block()
                elif event.button == 3:
                    self._place_block()
                elif event.button == 4:
                    self.selected_block_idx = (self.selected_block_idx - 1) % len(HOTBAR_BLOCKS)
                elif event.button == 5:
                    self.selected_block_idx = (self.selected_block_idx + 1) % len(HOTBAR_BLOCKS)
            elif event.type == TEXTINPUT:
                if self.show_chat and self.chat.active and len(self.chat.input_buffer) < 120:
                    self.chat.input_buffer += event.text
            elif event.type == MOUSEMOTION:
                if self.mouse_locked:
                    dx, dy = event.rel
                    self.yaw = normalize_angle(self.yaw + dx * MOUSE_SENSITIVITY)
                    self.pitch += -dy * MOUSE_SENSITIVITY
                    self.pitch = max(-89, min(89, self.pitch))

    def _handle_pause_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.state = GameState.PLAYING
                    self.mouse_locked = True
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                elif event.key == K_q:
                    self._set_menu_display_mode()
                    self.state = GameState.MENU
                    self.mouse_locked = False
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)
                    self.world = None
                    self.mobs = []
                    self._free_chunk_meshes()

    def _break_block(self):
        if not self.world:
            return
        origin = self.player_pos.to_tuple()
        direction = self._get_look_direction()
        hit_pos, block = self.world.hit_test(origin, direction)
        if hit_pos and block not in (BlockType.AIR, BlockType.BEDROCK):
            self.world.set_block(*hit_pos, BlockType.AIR)
            drop = block
            if block == BlockType.GRASS:
                drop = BlockType.DIRT
            self.inventory.add(drop, 1)

    def _place_block(self):
        if not self.world:
            return
        block_type = HOTBAR_BLOCKS[self.selected_block_idx]
        if not self.inventory.can_place(block_type):
            return
        origin = self.player_pos.to_tuple()
        direction = self._get_look_direction()
        hit_pos, block = self.world.hit_test(origin, direction)
        if hit_pos:
            face = self.world.get_block_face(origin, direction, hit_pos)
            new_pos = (
                hit_pos[0] + int(face.x),
                hit_pos[1] + int(face.y),
                hit_pos[2] + int(face.z),
            )
            px, py, pz = int(self.player_pos.x), int(self.player_pos.y), int(self.player_pos.z)
            if new_pos in ((px, py, pz), (px, py + 1, pz)):
                return
            existing = self.world.get_block(*new_pos)
            if existing in (BlockType.AIR, BlockType.WATER):
                if self.inventory.use(block_type):
                    self.world.set_block(*new_pos, block_type)

    def _get_look_direction(self):
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)
        return Vec3(
            -math.sin(yaw_rad) * math.cos(pitch_rad),
            -math.sin(pitch_rad),
            -math.cos(yaw_rad) * math.cos(pitch_rad),
        ).normalize()

    def _update_game(self):
        if not self.world:
            return

        # Day/night cycle
        self.time_of_day = (self.time_of_day + self.dt / self.day_length) % 1.0

        # Player movement (frozen while chat/inventory open)
        if not self.show_chat and not self.show_inventory:
            keys = pygame.key.get_pressed()
            forward = Vec3(
                -math.sin(math.radians(self.yaw)),
                0,
                -math.cos(math.radians(self.yaw)),
            ).normalize()
            right = forward.cross(Vec3(0, 1, 0)).normalize()

            move = Vec3(0, 0, 0)
            if keys[K_w] or keys[K_UP]:
                move = move + forward
            if keys[K_s] or keys[K_DOWN]:
                move = move - forward
            if keys[K_a]:
                move = move - right
            if keys[K_d]:
                move = move + right

            if move.length() > 0:
                move = move.normalize() * MOVE_SPEED
                self.velocity.x = move.x
                self.velocity.z = move.z
            else:
                self.velocity.x *= 0.8
                self.velocity.z *= 0.8

            if keys[K_SPACE] and self.on_ground:
                self.velocity.y = JUMP_SPEED
                self.on_ground = False
                self.fall_distance = 0.0

        # Gravity
        self.velocity.y += GRAVITY * self.dt

        # Collision detection (simple AABB)
        new_pos = self.player_pos + self.velocity * self.dt

        player_width = 0.3
        player_height = 1.7
        self.on_ground = False

        test_pos = Vec3(new_pos.x, self.player_pos.y, self.player_pos.z)
        if not self._check_collision(test_pos, player_width, player_height):
            self.player_pos.x = new_pos.x
        else:
            self.velocity.x = 0

        test_pos = Vec3(self.player_pos.x, new_pos.y, self.player_pos.z)
        if not self._check_collision(test_pos, player_width, player_height):
            if self.velocity.y < 0:
                self.fall_distance += self.player_pos.y - new_pos.y
            self.player_pos.y = new_pos.y
        else:
            if self.velocity.y < 0:
                self.on_ground = True
                if self.fall_distance > FALL_DAMAGE_THRESHOLD:
                    self._hurt(int(self.fall_distance - FALL_DAMAGE_THRESHOLD))
                self.fall_distance = 0.0
            self.velocity.y = 0

        test_pos = Vec3(self.player_pos.x, self.player_pos.y, new_pos.z)
        if not self._check_collision(test_pos, player_width, player_height):
            self.player_pos.z = new_pos.z
        else:
            self.velocity.z = 0

        self.player_pos.y = max(self.player_pos.y, -10)

        if self.world.is_fluid_at(self.player_pos.x, self.player_pos.y, self.player_pos.z):
            bt = self.world.get_block(int(self.player_pos.x), int(self.player_pos.y), int(self.player_pos.z))
            if bt == BlockType.LAVA:
                self._hurt(4)

        self.hurt_timer = max(0.0, self.hurt_timer - self.dt)
        self._update_mobs()
        self._queue_chunk_meshes()
        self._process_mesh_queue()
        self.rebuild_dirty_chunks()
        self._cull_distant_chunks()

        if self.health <= 0:
            self.start_game(
                seed=self.world.seed,
                theme=self.world.theme,
                level_type=self.world.level_type,
                show_progress=False,
            )

    def _hurt(self, amount):
        self.health = max(0, self.health - amount)
        self.hurt_timer = 0.35

    def _update_mobs(self):
        if not self.world:
            return
        night = self.time_of_day < 0.22 or self.time_of_day > 0.78
        for mob in self.mobs:
            if not mob.alive:
                continue
            mob.cooldown = max(0.0, mob.cooldown - self.dt)
            if mob.hostile() and night:
                to_player = (self.player_pos - mob.pos)
                if to_player.length() < 24:
                    step = to_player.normalize() * 2.2 * self.dt
                    mob.pos = mob.pos + step
                    if to_player.length() < 1.4 and mob.cooldown <= 0:
                        self._hurt(3 if mob.kind == "zombie" else 2)
                        mob.cooldown = 1.0
            else:
                mob.pos.x += math.sin(self.frame_time + (id(mob) % 7)) * 0.6 * self.dt
                mob.pos.z += math.cos(self.frame_time * 0.8 + (id(mob) % 5)) * 0.6 * self.dt
            mob.pos.y = self.world.get_ground_y(mob.pos.x, mob.pos.z)

    def _check_collision(self, pos, width, height):
        """Check AABB collision with world blocks."""
        min_x = int(pos.x - width)
        max_x = int(pos.x + width)
        min_y = int(pos.y)
        max_y = int(pos.y + height)
        min_z = int(pos.z - width)
        max_z = int(pos.z + width)

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                for z in range(min_z, max_z + 1):
                    block = self.world.get_block(x, y, z) if self.world else BlockType.AIR
                    if block and BLOCK_PROPERTIES.get(block, {}).get("solid", False):
                        return True
        return False

    def _cull_distant_chunks(self):
        pcx, pcz = self._player_chunk_coords()
        to_remove = []
        for (cx, cz) in self.chunk_meshes:
            if abs(cx - pcx) > RENDER_DISTANCE + 1 or abs(cz - pcz) > RENDER_DISTANCE + 1:
                to_remove.append((cx, cz))
        for key in to_remove:
            self.chunk_meshes.pop(key, None)
        if self.mesh_queue:
            self.mesh_queue = [
                key for key in self.mesh_queue
                if abs(key[0] - pcx) <= RENDER_DISTANCE + 1 and abs(key[1] - pcz) <= RENDER_DISTANCE + 1
            ]

    def _render_game(self):
        if not HAS_OPENGL or not self.gl_mode:
            self.screen.fill((100, 100, 255))
            # Fallback 2D view
            text = self.font.render("OpenGL required for 3D view", True, (255, 255, 255))
            self.screen.blit(text, (20, 20))
            text2 = self.font_small.render("Install: pip install PyOpenGL PyOpenGL_accelerate", True, (200, 200, 200))
            self.screen.blit(text2, (20, 60))
            pygame.display.flip()
            return

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)

        # Sky color based on time of day
        t = self.time_of_day
        sky_r = 0.05 + 0.48 * abs(math.sin(t * math.pi))
        sky_g = 0.05 + 0.73 * abs(math.sin(t * math.pi))
        sky_b = 0.15 + 0.77 * abs(math.sin(t * math.pi))
        glClearColor(sky_r, sky_g, sky_b, 1.0)

        # Set up projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = self.sw / self.sh
        gluPerspective(FOV, aspect, NEAR_PLANE, FAR_PLANE)

        # Set up view
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Camera look direction
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)
        look_x = -math.sin(yaw_rad) * math.cos(pitch_rad)
        look_y = -math.sin(pitch_rad)
        look_z = -math.cos(yaw_rad) * math.cos(pitch_rad)
        gluLookAt(
            self.player_pos.x, self.player_pos.y + 1.5, self.player_pos.z,
            self.player_pos.x + look_x, self.player_pos.y + 1.5 + look_y, self.player_pos.z + look_z,
            0, 1, 0,
        )

        # Light direction
        light_angle = t * 2 * math.pi
        light_dir = (math.sin(light_angle), 0.5, math.cos(light_angle))
        light_strength = 0.3 + 0.7 * max(0, math.sin(light_angle + 0.5))
        ambient = (0.2 * light_strength, 0.2 * light_strength, 0.3 * light_strength)

        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (*ambient, 1.0))
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, (*light_dir, 0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (light_strength, light_strength, light_strength, 1))
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        draw_cloud_layer(self.player_pos, self.time_of_day, self.world.seed if self.world else 0)

        for mesh in self.chunk_meshes.values():
            draw_chunk_mesh(mesh)

        for mob in self.mobs:
            if mob.alive:
                c = COLORS.get(mob.color_name(), (1, 1, 1))
                size = 0.9 if mob.kind == "pig" else 1.1
                draw_colored_cube((mob.pos.x, mob.pos.y + size * 0.5, mob.pos.z), size, c)

        glDisable(GL_COLOR_MATERIAL)
        glDisable(GL_LIGHTING)

        # Render HUD (overlay)
        self._render_hud()

        pygame.display.flip()

    def _render_hud(self):
        """Render 2D HUD overlay (crosshair, hotbar, chat, info)."""
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.sw, self.sh, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)

        # ── Crosshair ──
        ch_size = 12
        ch_color = (255, 255, 255, 200)
        cx, cy = self.sw // 2, self.sh // 2

        # Reuse HUD surface to avoid allocation every frame
        if not hasattr(self, '_hud_surface') or self._hud_surface.get_size() != (self.sw, self.sh):
            self._hud_surface = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        s = self._hud_surface
        s.fill((0, 0, 0, 0))
        # Crosshair lines
        pygame.draw.line(s, ch_color, (cx - ch_size, cy), (cx + ch_size, cy), 2)
        pygame.draw.line(s, ch_color, (cx, cy - ch_size), (cx, cy + ch_size), 2)
        # Dot in center
        pygame.draw.circle(s, (255, 255, 255, 255), (cx, cy), 2)

        # ── Hotbar ──
        slot_size = 40
        margin = 4
        visible_slots = min(9, len(HOTBAR_BLOCKS))
        total_width = visible_slots * (slot_size + margin) - margin
        start_x = (self.sw - total_width) // 2
        hotbar_y = self.sh - slot_size - 10

        pygame.draw.rect(
            s, (30, 30, 30, 180),
            (start_x - 4, hotbar_y - 4, total_width + 8, slot_size + 8),
            border_radius=4,
        )

        for i in range(visible_slots):
            bt = HOTBAR_BLOCKS[i]
            bx = start_x + i * (slot_size + margin)
            selected = i == self.selected_block_idx
            color_name = BLOCK_PROPERTIES[bt]["color"]
            block_color = COLORS.get(color_name, (100, 100, 100))
            rc = tuple(int(c * 255) for c in block_color)
            slot_rect = pygame.Rect(bx, hotbar_y, slot_size, slot_size)
            if selected:
                pygame.draw.rect(s, (200, 200, 200, 220), slot_rect, border_radius=3)
                pygame.draw.rect(s, (255, 255, 255, 255), slot_rect, 3, border_radius=3)
            else:
                pygame.draw.rect(s, (60, 60, 60, 180), slot_rect, border_radius=3)
                pygame.draw.rect(s, (100, 100, 100, 200), slot_rect, 1, border_radius=3)
            pygame.draw.rect(s, rc, (bx + 6, hotbar_y + 6, slot_size - 12, slot_size - 12), border_radius=2)
            count = self.inventory.count(bt)
            if count < 999:
                ctxt = self.font_small.render(str(count), True, (255, 255, 255, 230))
                s.blit(ctxt, (bx + slot_size - ctxt.get_width() - 4, hotbar_y + slot_size - 16))

        # ── Hearts ──
        hearts = max(0, int(math.ceil(self.health / 2)))
        for i in range(10):
            hx = 12 + i * 18
            hy = 10
            color = (220, 40, 40, 230) if i < hearts else (80, 30, 30, 180)
            if self.hurt_timer > 0 and i < hearts and int(self.frame_time * 10) % 2 == 0:
                color = (255, 120, 120, 230)
            pygame.draw.rect(s, color, (hx, hy, 14, 14), border_radius=3)

        # ── Info text ──
        info_lines = [
            f"FPS: {self.fps}",
            f"Pos: {int(self.player_pos.x)}, {int(self.player_pos.y)}, {int(self.player_pos.z)}",
            f"Time: {int(self.time_of_day * 24):02d}:{int((self.time_of_day * 24 * 60) % 60):02d}",
            f"Theme: {self.world.theme if self.world else '-'}",
            f"Type: {self.world.level_type if self.world else '-'}",
        ]
        for i, line in enumerate(info_lines):
            txt = self.font_small.render(line, True, (255, 255, 255, 200))
            s.blit(txt, (10, 34 + i * 20))

        # ── Inventory panel ──
        if self.show_inventory:
            panel = pygame.Rect(self.sw // 2 - 180, self.sh // 2 - 160, 360, 320)
            pygame.draw.rect(s, (0, 0, 0, 200), panel, border_radius=6)
            pygame.draw.rect(s, (180, 180, 180, 220), panel, 2, border_radius=6)
            title = self.font.render("Inventory", True, (255, 255, 255))
            s.blit(title, (panel.x + 12, panel.y + 10))
            y = panel.y + 44
            for bt in sorted(self.inventory.counts.keys(), key=lambda b: b.value):
                if self.inventory.count(bt) <= 0:
                    continue
                line = f"{BLOCK_NAMES[bt]}: {self.inventory.count(bt)}"
                s.blit(self.font_small.render(line, True, (230, 230, 230)), (panel.x + 14, y))
                y += 20

        # ── Chat (if active) ──
        if self.show_chat or (self.chat.messages and self.state == GameState.PLAYING):
            chat_x = 20
            chat_y = self.sh - 300
            chat_w = 400
            chat_h = 260

            # Chat background
            pygame.draw.rect(s, (0, 0, 0, 160), (chat_x - 5, chat_y - 5, chat_w + 10, chat_h + 60), border_radius=4)

            # Messages (show last 8)
            display_msgs = self.chat.messages[-8:]
            for i, msg in enumerate(display_msgs):
                color = (120, 200, 255) if msg["role"] == "user" else (200, 255, 200)
                prefix = "You: " if msg["role"] == "user" else "AI: "
                txt = self.font_chat.render(f"{prefix}{msg['content'][:50]}", True, color)
                s.blit(txt, (chat_x + 5, chat_y + 5 + i * 28))

            # Input box
            if self.chat.active:
                input_rect = pygame.Rect(chat_x, chat_y + chat_h + 5, chat_w, 30)
                pygame.draw.rect(s, (50, 50, 50, 220), input_rect, border_radius=3)
                pygame.draw.rect(s, (200, 200, 200, 200), input_rect, 1, border_radius=3)
                input_txt = f"> {self.chat.input_buffer}"
                if len(self.chat.input_buffer) == 0:
                    input_txt = "> Type a message, then press Enter"
                    c = self.font_chat.render(input_txt, True, (150, 150, 150))
                else:
                    c = self.font_chat.render(input_txt, True, (255, 255, 255))
                s.blit(c, (chat_x + 5, chat_y + chat_h + 9))

        # ── Pause overlay ──
        if self.state == GameState.PAUSED:
            if not hasattr(self, '_pause_overlay') or self._pause_overlay.get_size() != (self.sw, self.sh):
                self._pause_overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
                self._pause_overlay.fill((0, 0, 0, 180))
            s.blit(self._pause_overlay, (0, 0))
            pause_text = self.font_title.render("PAUSED", True, (255, 255, 255))
            s.blit(pause_text, pause_text.get_rect(center=(self.sw // 2, self.sh // 2 - 40)))
            resume_text = self.font.render("Press ESC to resume | Q to quit to menu", True, (200, 200, 200))
            s.blit(resume_text, resume_text.get_rect(center=(self.sw // 2, self.sh // 2 + 30)))

        # Draw the HUD surface
        self._draw_surface_2d(s, (0, 0))

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def _cleanup(self):
        self._free_gpu_resources()
        pygame.quit()
        sys.exit()


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("DeepSeekCraftR1 - Minecraft Infdev")
    print(f"Python {sys.version.split()[0]}")
    print(f"Target: {TARGET_FPS} FPS")
    print("files = off (no external asset files required)")
    print("Level types: Island, Floating, Flat")
    print("Themes: Normal, Hell, Sky, Paradise, Woods")
    print()

    if not HAS_OPENGL:
        print("Installing PyOpenGL...")
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "PyOpenGL", "PyOpenGL_accelerate"]
        )
        print("Please restart the program.")
        sys.exit(0)

    game = DeepSeekCraftR1()
    game.run()
