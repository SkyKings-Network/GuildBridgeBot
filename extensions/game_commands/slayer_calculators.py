import math

SLAYER_DATA = {
    "blaze": {
        "levels": [
            10,
            30,
            250,
            1500,
            5000,
            20000,
            100000,
            400000,
            1000000
        ],
        "xp_gain": [
            5,
            25,
            100,
            500
        ]
    },
    "enderman": {
        "levels": [
            10,
            30,
            250,
            1500,
            5000,
            20000,
            100000,
            400000,
            1000000
        ],
        "xp_gain": [
            5,
            25,
            100,
            500
        ]
    },
    "spider": {
        "levels": [
            5,
            25,
            200,
            1000,
            5000,
            20000,
            100000,
            400000,
            1000000
        ],
        "xp_gain": [
            5,
            25,
            100,
            500
        ]
    },
    "wolf": {
        "levels": [
            10,
            30,
            250,
            1500,
            5000,
            20000,
            100000,
            400000,
            1000000
        ],
        "xp_gain": [
            5,
            25,
            100,
            500
        ]
    },
    "vampire": {
        "levels": [
            20,
            75,
            240,
            840,
            2400
        ],
        "xp_gain": [
            10,
            25,
            60,
            120,
            150
        ]
    },
    "zombie": {
        "levels": [
            5,
            15,
            200,
            1000,
            5000,
            20000,
            100000,
            400000,
            1000000
        ],
        "xp_gain": [
            5,
            25,
            100,
            500,
            1500
        ]
    }
}

def calculate_slayer_level(boss, xp):
    if boss not in SLAYER_DATA:
        raise ValueError(f"Unknown slayer boss type: {boss}")
    levels = SLAYER_DATA[boss]["levels"]
    lvl = 0
    rexp = xp
    for level in levels:
        if rexp >= level:
            lvl += 1
        elif rexp < level:
            lvl += rexp / level
            break
    return lvl


def get_next_slayer_level(boss, current_xp):
    if boss not in SLAYER_DATA:
        raise ValueError(f"Unknown slayer boss type: {boss}")
    levels = SLAYER_DATA[boss]["levels"]
    for i, level in enumerate(levels):
        if current_xp < level:
            return level, level - current_xp
    return None, None


def get_kills_needed(boss, xp):
    if boss not in SLAYER_DATA:
        raise ValueError(f"Unknown slayer boss type: {boss}")
    xp_gain = SLAYER_DATA[boss]["xp_gain"]
    return [
        math.ceil(xp / gain) for gain in xp_gain if gain > 0
    ]