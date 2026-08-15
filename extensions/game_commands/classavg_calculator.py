async def calculate_classavg(member_data, global_boost=0.0, mayor_boost=0.0):
    RAW_BASE_CLASS_XP = 300000
    LVL50_XP = 569809640

    dungeons = member_data.get("dungeons", {}).get("player_classes", {})
    perks = member_data.get("player_data", {}).get("perks", {})
    attributes = member_data.get("attributes", {})

    SHARD_TABLE = {
        0: 0, 1: 1, 2: 2, 3: 4, 4: 6,
        5: 9, 6: 12, 7: 16, 8: 20, 9: 25, 10: 32
    }

    catagrad_level = min(max(attributes.get("catacombs_graduate", 0), 0), 10)
    shards = SHARD_TABLE.get(catagrad_level, 0)
    catagrad_bonus = shards * 0.02

    class_levels = {
        "mage": perks.get("cold_efficiency", 0),
        "archer": perks.get("toxophilite", 0),
        "berserk": perks.get("unbridled_rage", 0),
        "healer": perks.get("heart_of_gold", 0),
        "tank": perks.get("diamond_in_the_rough", 0),
    }

    class_perks = {k: v * 0.02 for k, v in class_levels.items()}

    base_gear_multiplier = 1.0 + 0.06 + 0.04 + 0.20 + catagrad_bonus

    xp = {
        cls: int(dungeons.get(cls, {}).get("experience", 0) or 0)
        for cls in class_levels
    }

    runs = {cls: 0 for cls in class_levels}

    while any(x < LVL50_XP for x in xp.values()):
        active = min(xp, key=xp.get)
        runs[active] += 1

        for cls in xp:
            additive_multiplier = base_gear_multiplier + class_perks[cls] + global_boost
            
            actual_multiplier = additive_multiplier * (1.0 + mayor_boost)
            
            gain = RAW_BASE_CLASS_XP * actual_multiplier

            xp[cls] += gain if cls == active else gain * 0.25

    return {
        "runs": runs,
        "total_runs": sum(runs.values())
    }