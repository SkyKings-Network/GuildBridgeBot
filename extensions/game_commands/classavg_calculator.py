import aiohttp

async def calculate_classavg(player, profile=None, global_boost=0.0, mayor_boost=0.0, config = None):

    RAW_BASE_CLASS_XP = 300000
    LVL50_XP = 569809640

    headers = {"API-Key": config.hypixel_api_key}

    async with aiohttp.ClientSession() as session:

        async with session.get(
            f"https://api.minecraftservices.com/minecraft/profile/lookup/name/{player}"
        ) as resp:
            if resp.status != 200:
                return {"error": "player_not_found"}
            uuid = (await resp.json())["id"]

        url = f"https://api.hypixel.net/v2/skyblock/profiles?uuid={uuid}"

        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            profiles = data.get("profiles", [])

            if not profiles:
                return {"error": "no_profiles"}

            if profile:
                best_profile = next(
                    (p for p in profiles if p.get("cute_name").lower() == profile.lower()),
                    None
                )
                if not best_profile:
                    return {"error": "profile_not_found"}
            else:
                best_profile = next(
                    (p for p in profiles if p.get("selected")),
                    profiles[0]
                )

            member_data = best_profile["members"][uuid]
            dungeons = member_data.get("dungeons", {}).get("player_classes", {})
            perks = member_data.get("player_data", {}).get("perks", {})
            attributes = member_data.get("attributes", {})

            SHARD_TABLE = {
                0: 0, 1: 1, 2: 2, 3: 3, 4: 5,
                5: 7, 6: 9, 7: 12, 8: 15, 9: 19, 10: 24
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
            total_event_multiplier = 1.0 + global_boost + mayor_boost

            xp = {
                cls: int(dungeons.get(cls, {}).get("experience", 0) or 0)
                for cls in class_levels
            }

            runs = {cls: 0 for cls in class_levels}

            while any(x < LVL50_XP for x in xp.values()):

                active = min(xp, key=xp.get)
                runs[active] += 1

                for cls in xp:
                    gain = (
                        RAW_BASE_CLASS_XP
                        * base_gear_multiplier
                        * total_event_multiplier
                        + RAW_BASE_CLASS_XP * class_perks[cls]
                    )

                    xp[cls] += gain if cls == active else gain * 0.25

            return {
                "player": player,
                "profile": best_profile["cute_name"],
                "runs": runs,
                "total_runs": sum(runs.values())
            }