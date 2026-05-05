# Configuration

## Server
| Key           | Type | Description                         | Default          |
|---------------|------|-------------------------------------|------------------|
| `SERVER_HOST` | str  | The host to connect to.             | `mc.hypixel.net` |
| `SERVER_PORT` | int  | The port to connect to on the host. | `25565`          |

## Account
| Key             | Type | Description                                                                         | Default |
|-----------------|------|-------------------------------------------------------------------------------------|---------|
| `ACCOUNT_EMAIL` | str  | Not actually useful, serves as an internal identifier for the account you're using. |         |

## Discord
| Key                              | Type      | Description                                                                                                                            | Default |
|----------------------------------|-----------|----------------------------------------------------------------------------------------------------------------------------------------|---------|
| `DISCORD_TOKEN`                  | str       | Discord bot token.                                                                                                                     |         |
| `DISCORD_CHANNEL`                | int       | Channel ID for your bridge messages.                                                                                                   |         |
| `DISCORD_ALLOWCROSSCHAT`         | list[int] | Channel IDs for which to allow "Cross Chat", which sends messages from other bridge bots to your guild. Formatted like so: `ID,ID,...` |         |
| `DISCORD_OFFICERCHANNEL`         | int       | Channel ID for your officer chat messages.                                                                                             |         |
| `DISCORD_ALLOWOFFICERCROSSCHAT`  | list[int] | Same as `DISCORD_ALLOWCROSSCHAT`, but for officer chat.                                                                                |         |
| `DISCORD_COMMANDROLE`            | int       | Your "Guild Staff" role, allows members with the role to take staff actions with the bot (invite, kick, mute, etc.)                    |         |
| `DISCORD_OVERRIDEROLE`           | int       | Your admin role, allows members with the role to use administrative commands such as `!override`.                                      |         |
| `DISCORD_OWNERID`                | int       | Functionally the same as `DISCORD_OVERRIDEROLE`, but for one user instead.                                                             |         |
| `DISCORD_PREFIX`                 | str       | The prefix for the bot.                                                                                                                | `!`     |
| `DISCORD_WEBHOOKURL`             | str       | If set, the bot will send webhook messages that appear to be from the Minecraft users, instead of embeds from the bot.                 |         |
| `DISCORD_DEBUGWEBHOOKURL`        | str       | Outputs some of the bot's logs to this webhook. Not useful unless you know what you're doing.                                          |         |
| `DISCORD_SERVERNAME`             | str       | When using `DISCORD_WEBHOOKURL`, messages from the bridge bot will use this name as the webhook's name.                                |         |
| `DISCORD_IGNORECROSSCHATWARNING` | bool      | Silences the warning in the terminal when crosschat is enabled.                                                                        | `false` 

## Settings
| Key                           | Type      | Description                                                                                                                  | Default |
|-------------------------------|-----------|------------------------------------------------------------------------------------------------------------------------------|---------|
| `SETTINGS_AUTOACCEPT`         | bool      | Autoaccept guild invites.                                                                                                    | `false` |
| `SETTINGS_DATELIMIT`          | int       | Date range limit for the `!top` command. Limited by Hypixel, so changing this value to something bigger will have no effect. | `30`    |
| `SETTINGS_EXTENSIONS`         | list[str] | List of `discord.py` extensions to load. There are two built-in: `.game_commands` and `.mute_sync`.                          |         |
| `SETTINGS_PRINTCHAT`          | bool      | If enabled, prints all chat messages to the terminal.                                                                        | `false` |
| `SETTINGS_HIDEINVITEMESSAGES` | bool      | Hides invite messages from being sent to bridge chat.                                                                        | `false` |

## Redis
Optional and not useful unless you know what you're doing.
| Key                    | Type | Description                                       | Default |
|------------------------|------|---------------------------------------------------|---------|
| `REDIS_HOST`           | str  | Hostname for the redis server.                    |         |
| `REDIS_PORT`           | int  | Port for the redis server.                        |         |
| `REDIS_PASSWORD`       | str  | Redis server password, if requirepass is enabled. |         |
| `REDIS_CLIENTNAME`     | str  | Client name to use for pub/sub.                   |         |
| `REDIS_RECEIVECHANNEL` | str  | Pub/sub channel to receive messages on.           |         |
| `REDIS_SENDCHANNEL`    | str  | Pub/sub channel to send messages on.              |         |

## Extensions
### `.mute_sync`
| Key                          | Type | Description                        | Default |
|------------------------------|------|------------------------------------|---------|
| `MUTE_SYNC_MUTE_ROLE`        | int  | The role to apply for guild mutes. |         |
| `MUTE_SYNC_HYPIXEL_API_KEY`  | str  | Hypixel API key.                   |         |
| `MUTE_SYNC_SKYKINGS_API_KEY` | str  | SkyKings API key.                  |         |

### `.game_commands`
Uses `DISCORD_PREFIX` (see above) as the prefix for commands.
| Key                             | Type      | Description                                                                                                      | Default |
|---------------------------------|-----------|------------------------------------------------------------------------------------------------------------------|---------|
| `GAME_COMMANDS_HYPIXEL_API_KEY` | str       | Hypixel API key.                                                                                                 |         |
| `ENABLED_COMMANDS`              | list[str] | Commands to enable. Defaults to all if left empty.                                                               |         |
| `USE_ANTISPAM`                  | bool      | Adds a random string of characters to the end of each message to try and evade spam filters. Usually not needed. | `false` |
| `COMMAND_COOLDOWN`              | float     | Cooldown between commands, in seconds.                                                                           | `5.0`   |

