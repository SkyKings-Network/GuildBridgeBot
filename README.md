# GuildBridgeBot

Guild Bridge Bot is a powerful tool that bridges communication between Hypixel's Minecraft guilds and Discord, 
enabling seamless interaction between guild members and Discord users. 
This bot ensures real-time relay of all guild messages, notifications, 
and events, facilitating better communication and management.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation and Usage](#installation-and-usage)
- [Commands](#commands)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)
- [Support](#support)
- [To-Do List](#to-do-list)

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

## Requirements

- Python 3.10+
    - discord.py
    - javascript
- node.js 
    - mineflayer
- Redis (optional, for additional features)

---

## Installation and Usage

### Initial Setup

Follow these instructions to copy the repository to a new server.

1. **Install Node.js:**
    ```bash
    cd ~
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
    source ~/.bashrc
    nvm install 19.7.0
    ```

2. **Install PM2 (Process Manager):**
    ```bash
    npm install -g pm2
    ```

3. **Install Python3 and Virtual Environment:**
    ```bash
    sudo apt-get update
    sudo apt install python3-pip
    sudo apt install python3.12-venv
    ```

4. **Clone the Project Repository:**
    ```bash
    git clone https://github.com/Jacktheguys/GuildBridgeBot
    ```

5. **Set Up Configuration Files:**
    ```bash
    mkdir bridges
    mv GuildBridgeBot/example.config.json GuildBridgeBot/config.json
    ```

### Creating a New Bridge Bot

1. **Copy Project Files:**
    ```bash
    cd ~
    mkdir bridges/<NAME_OF_GUILD>
    cp -r GuildBridgeBot/* bridges/<NAME_OF_GUILD>/
    cd bridges/<NAME_OF_GUILD>
    ```

2. **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install Dependencies:**
    ```bash
    python3 -m pip install -U -r requirements.txt
    ```

4. **Configuration**:  
    Update the `config.json` file with your guild's settings:
    ```bash
    nano config.json
    ```

5. **Start the Bot Using PM2:**
    ```bash
    pm2 start main.py --name <NAME_OF_GUILD>-BridgeBot --interpreter ./venv/bin/python --restart-delay=3000
    ```

---

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
| `!officerchat` | Toggle officer chat mode |
| `!guildchat` | Toggle regular guild chat mode |
| `!notifications` | Toggle join/leave notifications |
| `!toggleaccept` | Toggle auto-accepting guild invites |

### Miscellaneous

| Command | Description |
|---------|-------------|
| `!help` | Display all available commands and bot information |
| `!online` | Check online guild members |
| `!list` | Show a list of all guild members |
| `!override <command>` | Force the bot to use a given command |

Note: Some commands may require appropriate permissions in both Discord and the Hypixel guild.

---

## Troubleshooting

1. **Bot Not Starting:** 
   - Ensure the virtual environment is activated before running the bot. 
   - Verify that `pm2` is installed globally and the path to the Python interpreter is correct.

2. **Configuration Errors:** 
   - Double-check the `config.json` file for any misconfigurations or missing values.

3. **Slow Sync Issues:** 
   - For message sync delays, review the server and network speed.
   - Consider enabling Redis for better synchronization.

4. **Bot Disconnecting Frequently:**
   - Check the `config.json` file and ensure auto-reconnection settings are enabled.
   - Use Redis to prevent disconnections.

If you need further assistance, please open an issue on the GitHub repository.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This bot is not affiliated with or endorsed by Hypixel. Use at your own risk and ensure compliance with Hypixel's rules and terms of service. The bot adheres to Hypixel's API rate limits to prevent any bans.

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.

## To-Do List

- [ ] **Improve Minecraft-to-Discord sync speed**: Consider using a queue instead of dispatching events.
- [ ] **Add auto-accept requirements** for guild invites.
- [ ] **Make logs easier to read** by reducing the number of print statements and improving log formatting.

---
