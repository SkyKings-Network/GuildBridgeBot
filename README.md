# GuildBridgeBot

## To Do

- [ ] Improve minecraft -> discord speed
  - Possible use a queue instead of dispatching events
- [ ] Add requirements to autoaccept
- [ ] Make logs easier to read (less print statements)


## Initial Setup

Instructions are for Linux/Ubuntu machines

```shell
# Ensure we are in the home directory
cd ~

# Install nvm & node

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
source ~/.bashrc
nvm install 19.7.0

# Install pm2 for process management
npm install -g pm2

# Install python3
sudo apt-get update
sudo apt install python3-pip
apt install python3.12-venv

# Clone the project
git clone https://github.com/Jacktheguys/GuildBridgeBot

# Create directories for bridge bots
mkdir bridges

# Create config file
mv GuildBridgeBot/example.config.json GuildBridgeBot/config.json
```


## Creating A New Bridge Bot

```shell
# Ensure we are in the home directory
cd ~

# Copy files for a new bridge bot
mkdir bridges/<NAME_OF_GUILD>
cp -r GuildBridgeBot/* bridges/<NAME_OF_GUILD>/
cd bridges/<NAME_OF_GUILD>

# Create a virtal environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
python3 -m pip install -U -r requirements.txt

# Update the config
nano config.json

# Then run the bot with pm2
pm2 start main.py --name <NAME_OF_GUILD>-BridgeBot --interpreter ./venv/bin/python --restart-delay=3000
```

## More Information

For more information on the bot, please refer to the [documentation](https://docs.skykings.net/bridge).