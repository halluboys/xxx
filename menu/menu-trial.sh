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
dateFromServer=$(curl -v --insecure --silent https://google.com/ 2>&1 | grep Date | sed -e 's/< Date: //')
biji=`date +"%Y-%m-%d" -d "$dateFromServer"`
#########################
red='\e[1;31m'
green='\e[1;32m'
NC='\e[0m'
green() { echo -e "\\033[32;1m${*}\\033[0m"; }
red() { echo -e "\\033[31;1m${*}\\033[0m"; }
x="ok"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m${NC}"
echo -e "\E[44;1;39m                    ⇱ TRIAL MENU GENERATOR ⇲                  \E[0m"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m${NC}"
echo -e "\033[1;37mNB: Trial account will not logged into create log user\033[0m
\033[1;32mTrial-Generator\033[0m :

[${GREEN}01${NC}] ${color1} •${color3}$bd Generate Trial SSH & OpenVPN
[${GREEN}02${NC}] ${color1} •${color3}$bd Generate Trial Wireguard
[${GREEN}03${NC}] ${color1} •${color3}$bd Generate Trial L2TP
[${GREEN}04${NC}] ${color1} •${color3}$bd Generate Trial PPTP
[${GREEN}05${NC}] ${color1} •${color3}$bd Generate Trial SSTP
[${GREEN}06${NC}] ${color1} •${color3}$bd Generate Trial Shadowsocks-R
[${GREEN}07${NC}] ${color1} •${color3}$bd Generate Trial Shadowsocks
[${GREEN}08${NC}] ${color1} •${color3}$bd Generate Trial Vmess
[${GREEN}09${NC}] ${color1} •${color3}$bd Generate Trial VLESS
[${GREEN}10${NC}] ${color1} •${color3}$bd Generate Trial Trojan-GFW
[${GREEN}11${NC}] ${color1} •${color3}$bd Generate Trial Trojan-GO

[00] • Back to Main Menu \033[1;32m<\033[1;33m<\033[1;31m<\033[1;31m"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m${NC}"
echo ""
echo -ne "Select menu : "; read x

case "$x" in 
   1 | 01)
   clear
   trialssh
   ;;
   2 | 02)
   clear
   trialwg
   ;;
   3 | 03)
   clear
   triall2tp
   ;;
   4 | 04)
   clear
   trialpptp
   ;;
   5 | 05)
   clear
   trialsstp
   ;;
   6 | 06)
   clear
   trialssr
   ;;
   7 | 07)
   clear
   trialss
   ;;
   8 | 08)
   clear
   trialv2ray
   ;;
   9 | 09)
   clear
   trialvless
   ;;
   10)
   clear
   trialtrojan
   ;;
   11)
   clear
   trialtrgo
   ;;
   0 | 00)
   clear
   menu
   ;;
   *)
   menu
esac

#fim

