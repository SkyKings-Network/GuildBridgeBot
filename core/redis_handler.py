import asyncio
import json
import traceback
import uuid
import redis.asyncio as redis
from core.config import redis as config


class RedisManager:
    def __init__(self, bot, mineflayer_bot):
        self.read_task: asyncio.Task = None  # type: ignore
        self.bot = bot
        self.mineflayer_bot = mineflayer_bot
        self.config = config
        self.client_name = config.clientName
        self.recieve_channel = config.recieveChannel
        self.send_channel = config.sendChannel
        self._response_waiters: dict[str, asyncio.Future] = {}
        self.redis: redis.Redis = None
        self._restart: bool = True

    @property
    def running(self):
        if self.read_task is None:
            return False
        return not self.read_task.done()

    async def start(self):
        if self.running:
            raise RuntimeError("Already running")
        self.read_task = asyncio.create_task(self.reader())

    async def process_request(self, message_data):
        if self.mineflayer_bot is None:
            return {"success": False, "error": "bot not connected"}
        if message_data["endpoint"] == "alive":
            await self.mineflayer_bot.chat("/ping")
            try:
                await self.bot.wait_for("minecraft_pong", timeout=10)
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            return {"success": True}
        elif message_data["endpoint"] == "kick":
            await self.mineflayer_bot.chat("/g kick " + message_data["data"]["username"] + " " + message_data["data"]["reason"])
            try:
                await self.bot.wait_for(
                    "hypixel_guild_member_kick", timeout=10,
                    check=lambda x: x.lower() == message_data["data"]["username"].lower() if x is not None else False,
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            return {"success": True}
        elif message_data["endpoint"] == "mute":
            await self.mineflayer_bot.chat("/g mute " + message_data["data"]["username"])
            # TODO: write a success check for this
            return {"success": True}
        elif message_data["endpoint"] == "unmute":
            await self.mineflayer_bot.chat("/g unmute " + message_data["data"]["username"])
            # TODO: write a success check for this
            return {"success": True}
        elif message_data["endpoint"] == "setrank":
            await self.mineflayer_bot.chat(
                "/g setrank " + message_data["data"]["username"] + " " + message_data["data"]["rank"]
                )
            # wait for either hypixel_guild_member_promote or hypixel_guild_member_demote
            # return on first completed event
            chk = lambda p, f, t: ((p.lower() == message_data["data"]["username"].lower() and
                                   t.lower() == message_data["data"]["rank"].lower()) if (p is not None and t is not None) else False)
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
            await self.mineflayer_bot.chat("/g promote " + message_data["data"]["username"])
            try:
                await self.bot.wait_for(
                    "hypixel_guild_member_promote", timeout=10,
                    check=lambda p, f, t: p.lower() == message_data["data"]["username"].lower() if p is not None else False,
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            return {"success": True}
        elif message_data["endpoint"] == "demote":
            await self.mineflayer_bot.chat("/g demote " + message_data["data"]["username"])
            try:
                await self.bot.wait_for(
                    "hypixel_guild_member_demote", timeout=10,
                    check=lambda p, f, t: p.lower() == message_data["data"]["username"].lower() if p is not None else False,
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            return {"success": True}
        elif message_data["endpoint"] == "override":
            await self.mineflayer_bot.chat(message_data["data"]["command"])
            # can't really write a check for this
            return {"success": True}
        elif message_data["endpoint"] == "invite":
            try:
                returned = await asyncio.wait_for(
                    asyncio.create_task(
                        self.bot.send_invite(message_data["data"]["username"])
                    ),
                    timeout=10,
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
            if returned[0]:
                return {"success": True}
            return {"success": False, "error": returned[1]}

        return {"success": False, "error": "invalid endpoint"}

    async def reader(self):
        try:
            self.redis = redis.Redis(host=self.config["host"], password=self.config["password"], port=self.config["port"])
            async with self.redis.pubsub() as pubsub:
                channel = self.recieve_channel + ":" + self.client_name
                await pubsub.subscribe(channel)
                print(f"Redis > Subscribed to {channel}")
                while (not self.bot.is_closed()) and self.running:
                    try:
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10)
                    except asyncio.TimeoutError:
                        continue
                    if message is None:
                        continue
                    try:
                        message_data = json.loads(message["data"])
                    except json.JSONDecodeError as e:  # pylint: disable=broad-exception-caught
                        print("Redis > Invalid payload received: " + str(e))
                        continue
                    if message_data.get("type") not in ("request", "response"):
                        print(
                            "Redis > Invalid payload received (missing or invalid `type`)"
                        )
                        continue
                    if message_data["type"] == "response":
                        future = self._response_waiters.get(message_data["uuid"])
                        if future is not None:
                            future.set_result(message_data["data"])
                        continue
                    if message_data.get("source") == self.client_name:
                        continue
                    if "source" not in message_data:
                        print(
                            "Redis > Invalid payload received (missing source)"
                        )
                        continue
                    print(f"Redis > Handling message from {message_data.get('source')}")
                    try:
                        response = await self.process_request(message_data)
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        await self.send_message(
                            type="response",
                            uuid=message_data["uuid"],
                            data={"error": str(e)},
                        )
                        print("Redis > Error processing request\n" + str(e))
                        traceback.print_exc()
                        print("Payload: " + str(message_data))
                        continue
                    await self.send_message(
                        type="response",
                        uuid=message_data["uuid"],
                        data=response,
                    )
        except asyncio.CancelledError:
            print("Redis > Task Cancelled")
        except redis.ConnectionError:
            print("Redis > Redis connection closed")
        except Exception as e:  # pylint: disable=broad-exception-caught
            print("Redis > Critical error occurred\n" + str(e))
            traceback.print_exc()
            content = f"Critical error occurred in RedisManager: {e}"
            content += "\n```\n" + traceback.format_exc() + "\n```"
            if len(content) > 2000:
                # remove end codeblock, send first chunk, then send rest w/ block
                content = content[:-4]
                for i in range(0, len(content), 2000):
                    if i == 0:
                        await self.bot.send_debug_message(content[i:i + 1996] + "\n```")
                    else:
                        await self.bot.send_debug_message("```\n" + content[i:i + 1992] + "\n```")
            else:
                await self.bot.send_debug_message(content)
        finally:
            if self.redis is not None:
                await self.close(restart=self._restart)
        print("Redis > Connection closed")
        if self._restart:
            await asyncio.sleep(5)
            print("Redis > Restarting...")
            await self.start()

    async def send_message(self, **data) -> str:
        if self.redis is None:
            raise RuntimeError("Redis not connected")
        if "uuid" not in data:
            data["uuid"] = str(uuid.uuid4().hex)
        if "type" not in data:
            data["type"] = "request"
        data["source"] = self.client_name
        await self.redis.publish(self.send_channel, json.dumps(data))
        return data["uuid"]

    async def request(self, endpoint: str, **data):
        if self.redis is None:
            raise RuntimeError("Redis not connected")
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

    async def close(self, *, restart: bool = False):
        self._restart = restart
        await self.redis.close()
        self.read_task.cancel()

    @classmethod
    async def create(cls, discord_bot, mineflayer_bot):
        self = cls(discord_bot, mineflayer_bot)
        await self.start()
        return self