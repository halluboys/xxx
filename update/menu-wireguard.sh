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
x="ok"
Green_font_prefix="\033[32m" && Red_font_prefix="\033[31m" && Green_background_prefix="\033[42;37m" && Red_background_prefix="\033[41;37m" && Font_color_suffix="\033[0m"
chck_pid(){
	PID=`ps -ef |grep -v grep | grep wg0 |awk '{print $2}'`
	if [[ ! -z "${PID}" ]]; then
			echo -e "Current status: ${Green_font_prefix} Installed${Font_color_suffix} & ${Green_font_prefix}Running${Font_color_suffix}"
		else
			echo -e "Current status: ${Green_font_prefix} Installed${Font_color_suffix} but ${Red_font_prefix}Not Running${Font_color_suffix}"
		fi
}

while true $x != "ok"
do
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m${NC}"
echo -e "\E[44;1;39m                      ⇱ WIREGUARD MENU ⇲                      \E[0m"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m${NC}"
chck_pid
echo -e "
[${GREEN}01${NC}] ${color1} •${color3}$bd Create Wireguard Account
[${GREEN}02${NC}] ${color1} •${color3}$bd Deleting Wireguard Account
[${GREEN}03${NC}] ${color1} •${color3}$bd Cek User Login Wireguard
[${GREEN}04${NC}] ${color1} •${color3}$bd Extending Wireguard Account Active Life
[${GREEN}05${NC}] ${color1} •${color3}$bd Check Wireguard User Interface

[00] • Back to Main Menu \033[1;32m<\033[1;33m<\033[1;31m<\033[1;31m"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m${NC}"
echo ""
echo -ne "Select menu : "; read x

case "$x" in 
   1 | 01)
   clear
   addwg
   break
   ;;
   2 | 02)
   clear
   delwg
   break
   ;;
   3 | 03)
   clear
   cekwg
   break
   ;;
   4 | 04)
   clear
   renewwg
   break
   ;;
   5 | 05)
   clear
   wg show
   read -n 1 -s -r -p "Press any key to back on menu"
   menu-wireguard
   break
   ;;
   0 | 00)
   clear
   menu-vpn
   break
   ;;
   *)
   clear
esac
done
#fim
