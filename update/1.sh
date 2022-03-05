#!/bin/bash
# My Telegram : https://t.me/sampiiiiu
# ==========================================
# Color
bd='\e[1m'
RED='\033[0;31m'
NC='\033[0m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
LIGHT='\033[0;37m'
# ==========================================
# Getting
MYIP=$(wget -qO- ipinfo.io/ip);
# ===============================
cd /usr/bin
wget -O menu-ssh "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-ssh.sh"
wget -O menu-l2tp "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-l2tp.sh"
wget -O menu-pptp "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-pptp.sh"
wget -O menu-sstp "https://raw.githubusercontent.com/shalluboys/xxx/main/update/menu-sstp.sh"
wget -O menu-wireguad "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-wireguad.sh"
wget -O menu-shadowsocks "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-shadowsocks.sh"
#wget -O ssrmenu "https://raw.githubusercontent.com/halluboys/xxx/main/update/ssrmenu.sh"
wget -O menu-v2ray "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-v2ray.sh"
#wget -O menu-vless "https://raw.githubusercontent.com/halluboys/xxx/main/update/vlessmenu.sh"
wget -O menu-trojan "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-trojan.sh"
wget -O menu-vpn "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-vpn.sh"
wget -O menu-tools "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-tools.sh"
wget -O menu-trial "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-trial.sh"
wget -O menu-domain "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-domain.sh"
wget -O menu-backup "https://raw.githubusercontent.com/halluboys/xxx/main/update/menu-backup.sh"


chmod +x menu-ssh
chmod +x menu-l2tp
chmod +x menu-pptp
chmod +x menu-sstp
chmod +x menu-wireguad
chmod +x menu-shadowsocks
chmod +x menu-v2ray
chmod +x menu-vpn
chmod +x menu-tools
chmod +x menu-trial
chmod +x menu-backup
chmod +x menu-domain
chmod +x menu-trojan
