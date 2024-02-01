# GuildBridgeBot

# To Do

[-] Make IPC server not turn on if disabled in config
[-] Make seperate files for everything
[-] Make !update fully update it and restart
[-] Add api for bots to connect
[-] Make documentation on how to setup
[-] Make sure its optimized as close as the javascript one 

[-] Add requirements to autoaccept
[-] Make logs easier to read (less print statements)
[-] Remake the doc to setup servers


# How To Setup Server

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash

source ~/.bashrc

nvm install 19.7.0

npm install -g pm2

git clone https://github.com/Jacktheguys/GuildBridgeBot

mkdir bridges

mkdir bridges/bridgebots

cd GuildBridgeBot/

mv example.config.json config.json

npm install -g yarn

apt-get update

sudo apt install python3-pip

yarn


# Creating A New Bridge Bot

cd ~

mkdir bridges/bridgebots/<NAME_OF_GUILD>-Bridgebot

cp -r GuildBridgeBot/ bridges/bridgebots/<NAME_OF_GUILD>-Bridgebot/

nano config.json

pip install -r requirements.txt

pm2 start main.py --name index

# Setting Up IPC Server
(For jack only)

Set client name to correct name