# GuildBridgeBot

Guild Bridge Bot is a powerful tool that bridges communication between Hypixel's Minecraft guilds and Discord, 
enabling seamless interaction between guild members and Discord users. 
This bot ensures real-time relay of all guild messages, notifications, 
and events, facilitating better communication and management.

## Features

- **Two-Way Communication**: Relay messages between Hypixel guild chat and a designated Discord channel.
- **Officer Chat Support**: Separate channel for officer communications with togglable modes.
- **Guild Event Notifications**: Automatically notify Discord about guild events such as:
  - Members joining or leaving
  - Promotions and demotions
  - Kicks
  - Mutes and unmutes
- **Command Handling**: Execute Hypixel guild commands from Discord.
- **Auto-Accept Invites**: Optionally auto-accept guild invites.
- **Robust Error Handling**: Automatic reconnection and error reporting.
- **Customizable Appearance**: Use Discord webhooks for more control over bot messages.
- **Update Notifications**: Get notified in discord when theres a bridge update.

## Installation and Usage

### Initial Setup

Follow these instructions to start a new bridge bot instance:

1. **Install Docker:** [Instructions Here](https://docs.docker.com/engine/install/#installation-procedures-for-supported-platforms)

2. **Copy the Docker Compose File:**
    ```bash
    curl https://raw.githubusercontent.com/SkyKings-Network/GuildBridgeBot/refs/heads/main/compose.yml > compose.yml
    ```

3. **Update the settings for your compose file as needed:**
    ```bash
    nano compose.yml
    ```
   
4. **Start the Bot:**
    ```bash
    docker compose -f compose.yml up -d
    ```
   
If you are running the bot for the first time, you will need to log in with a Minecraft account.
To do this, check the logs of the bot container to get the link to log in:
```bash
docker compose logs -n 50
```

### Running multiple bridge bots
To run multiple bridge bots, you will need to add on to your docker compose file.
Each bot will need its own service definition.

1. **Open your compose file:**
    ```bash
    nano compose.yml
    ```
   
2. **Add a new service for each additional bot:**
    ```yaml
    bot2:
        image: skykingsnetwork/guildbridgebot:latest
        container_name: guildbridgebot2
        restart: unless-stopped
        environment:
          - BRIDGE_USE_ENV_CONFIG=true
          - BRIDGE_ACCOUNT_EMAIL=
          - BRIDGE_DISCORD_TOKEN=
          - BRIDGE_DISCORD_CHANNEL=
    ```
   
3. **Update the environment variables for each bot accordingly.**
4. **Save and exit the file.**
5. **Restart the docker compose setup:**
    ```bash
    docker compose -f compose.yml up -d
    ```

### Configuration

The bot can be configured using environment variables or a `config.json` file.
To use a file, mount it into the Docker container at `/Bot/config.json`. For example:
```yaml
volumes:
    - ./config.json:/Bot/config.json
```

### Updating the Bot
To update the bot to the latest version, run the following commands:
```bash
docker compose -f compose.yml pull
docker compose -f compose.yml up -d
```

## Commands

### Guild Management

| Command | Description |
|---------|-------------|
| `!invite <username>` | Invite a player to the guild |
| `!kick <username> [reason]` | Kick a player from the guild |
| `!promote <username>` | Promote a guild member |
| `!demote <username>` | Demote a guild member |
| `!setrank <username> <rank>` | Set a member's rank |
| `!mute <username> <duration>` | Mute a guild member |
| `!unmute <username>` | Unmute a guild member |

### Communication Control

| Command | Description |
|---------|-------------|
| `!notifications` | Toggle join/leave notifications |
| `!toggleaccept` | Toggle auto-accepting guild invites |

### Miscellaneous

| Command | Description |
|---------|-------------|
| `!help` | Display all available commands and bot information |
| `!online` | Check online guild members |
| `!list` | Show a list of all guild members |
| `!top` | Shows xperience ranking of members for the day |
| `!info` | Shows Guild Information |
| `!override <command>` | Force the bot to use a given command |

Note: Some commands may require appropriate permissions in both Discord and the Hypixel guild.

---

## Troubleshooting

If you need help troubleshooting, please open an ticket in our Discord server: https://discord.gg/skykings.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This bot is not affiliated with or endorsed by Hypixel. Use at your own risk and ensure compliance with Hypixel's rules and terms of service. The bot adheres to Hypixel's API rate limits to prevent any bans.

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.
