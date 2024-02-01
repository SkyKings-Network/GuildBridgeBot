import asyncio
import json
import uuid
import redis.asyncio as redis


class RedisManager:
    def __init__(self, bot, mineflayer_bot, config):
        self.read_task: asyncio.Task = None  # type: ignore
        self.bot = bot
        self.mineflayer_bot = mineflayer_bot
        self.config = config
        self.client_name = config["clientName"]
        self.recieve_channel = config["recieveChannel"]
        self.send_channel = config["sendChannel"]
        self._response_waiters: dict[str, asyncio.Future] = {}
        self.redis = None

    async def start(self):
        self.read_task = asyncio.create_task(self.reader())

    async def process_request(self, message_data):
        if self.mineflayer_bot is None:
            return {"success": False, "error": "bot not connected"}
        if message_data["endpoint"] == "alive":
            self.mineflayer_bot.chat("/ping")
            try:
                await self.bot.wait_for("minecraft_pong", timeout=10)
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            return {"success": True}
        elif message_data["endpoint"] == "kick":
            self.mineflayer_bot.chat("/g kick " + message_data["data"]["username"] + " " + message_data["data"]["reason"])
            try:
                await self.bot.wait_for(
                    "hypixel_guild_member_kick", timeout=10,
                    check=lambda x: x.lower() == message_data["data"]["username"].lower(),
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            return {"success": True}
        elif message_data["endpoint"] == "mute":
            self.mineflayer_bot.chat("/g mute " + message_data["data"]["username"])
            # TODO: write a success check for this
            return {"success": True}
        elif message_data["endpoint"] == "unmute":
            self.mineflayer_bot.chat("/g unmute " + message_data["data"]["username"])
            # TODO: write a success check for this
            return {"success": True}
        elif message_data["endpoint"] == "setrank":
            self.mineflayer_bot.chat(
                "/g setrank " + message_data["data"]["username"] + " " + message_data["data"]["rank"]
                )
            # wait for either hypixel_guild_member_promote or hypixel_guild_member_demote
            # return on first completed event
            chk = lambda x, f, t: (x.lower() == message_data["data"]["username"].lower() and
                                   t.lower() == message_data["data"]["rank"].lower())
            try:
                await asyncio.wait(
                    [
                        self.bot.wait_for(
                            "hypixel_guild_member_promote", timeout=10,
                            check=chk,
                        ),
                        self.bot.wait_for(
                            "hypixel_guild_member_demote", timeout=10,
                            check=chk,
                        )
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=10,
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            return {"success": True}
        elif message_data["endpoint"] == "promote":
            self.mineflayer_bot.chat("/g promote " + message_data["data"]["username"])
            try:
                await self.bot.wait_for(
                    "hypixel_guild_member_promote", timeout=10,
                    check=lambda x: x.lower() == message_data["data"]["username"].lower(),
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            return {"success": True}
        elif message_data["endpoint"] == "demote":
            self.mineflayer_bot.chat("/g demote " + message_data["data"]["username"])
            try:
                await self.bot.wait_for(
                    "hypixel_guild_member_demote", timeout=10,
                    check=lambda x: x.lower() == message_data["data"]["username"].lower(),
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            return {"success": True}
        elif message_data["endpoint"] == "override":
            self.mineflayer_bot.chat(message_data["data"]["command"])
            # can't really write a check for this
            return {"success": True}
        elif message_data["endpoint"] == "invite":
            self.mineflayer_bot.chat("/g invite " + message_data["data"]["username"])
            # wait for hypixel_guild_member_invite_failed or hypixel_guild_member_invite
            # return on first completed event
            chk = lambda x: x.lower() == message_data["data"]["username"].lower()
            returned = await asyncio.wait(
                [
                    asyncio.Task(self.bot.wait_for(
                        "hypixel_guild_member_invite_failed", timeout=10,
                        check=chk,
                    ), name="invite_failed"),
                    asyncio.Task(self.bot.wait_for(
                        "hypixel_guild_member_invite", timeout=10,
                        check=chk,
                    ), name="invite_success")
                ],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=10,
            )
            if len(returned[0]) == 0:
                return {"success": False, "error": "timeout"}
            if returned[0].pop().get_name() == "invite_success":
                return {"success": True}
            return {"success": False, "error": "invite failed"}

        return {"success": False, "error": "invalid endpoint"}

    async def reader(self):
        self.redis = redis.Redis(host=self.config["host"], password=self.config["password"], port=self.config["port"])
        async with self.redis.pubsub() as pubsub:
            channel = self.recieve_channel + ":" + self.client_name
            await pubsub.subscribe(channel)
            print(f"Subscribed to {channel}")
            while not self.bot.is_closed():
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message is not None:
                        try:
                            message_data = json.loads(message["data"])
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            print(e)
                            continue
                        if message_data.get("type") not in ("request", "response"):
                            print(
                                "WARN: Invalid payload (missing or invalid `type`)\n"
                                "```\n" + str(message_data) + "\n"
                                                              "```"
                            )
                            continue
                        if message_data["type"] == "response":
                            print(
                                "DEBUG: Response recieved\n"
                                "```\n" + str(message_data) + "\n"
                                                              "```"
                            )
                            future = self._response_waiters.get(message_data["uuid"])
                            if future is not None:
                                future.set_result(message_data["data"])
                            continue
                        if message_data.get("source") == self.client_name:
                            continue
                        if "source" not in message_data:
                            print(
                                "WARN: Invalid payload (missing source)\n"
                                "```\n" + str(message_data) + "\n"
                                                              "```"
                            )
                            continue
                        try:
                            response = await self.process_request(message_data)
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            print(e)
                            await self.send_message(
                                type="response",
                                uuid=message_data["uuid"],
                                data={"error": str(e)},
                            )
                            continue
                        await self.send_message(
                            type="response",
                            uuid=message_data["uuid"],
                            data=response,
                        )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    print(e)
                    continue
        print("IPC server closed")

    async def send_message(self, **data) -> str:
        if "uuid" not in data:
            data["uuid"] = str(uuid.uuid4().hex)
        if "type" not in data:
            data["type"] = "request"
        data["source"] = self.client_name
        await self.redis.publish(self.send_channel, json.dumps(data))
        return data["uuid"]

    async def request(self, endpoint: str, **data):
        payload = {
            "source": self.client_name,
            "type": "request",
            "endpoint": endpoint,
            "data": data,
            "uuid": str(uuid.uuid4().hex),
        }
        future = asyncio.Future()
        self._response_waiters[payload["uuid"]] = future
        await self.send_message(**payload)
        try:
            response = await asyncio.wait_for(future, timeout=10)
        except asyncio.TimeoutError:
            response = None
        del self._response_waiters[payload["uuid"]]
        return response

    @classmethod
    async def create(cls, bot: "Bot"):
        self = cls(bot)
        await self.start()
        return self
