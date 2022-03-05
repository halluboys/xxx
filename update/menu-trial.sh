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

BURIQ () {
    curl -sS https://raw.githubusercontent.com/halluboys/perizinan/main/main/allow > /root/tmp
    data=( `cat /root/tmp | grep -E "^### " | awk '{print $2}'` )
    for user in "${data[@]}"
    do
    exp=( `grep -E "^### $user" "/root/tmp" | awk '{print $3}'` )
    d1=(`date -d "$exp" +%s`)
    d2=(`date -d "$biji" +%s`)
    exp2=$(( (d1 - d2) / 86400 ))
    if [[ "$exp2" -le "0" ]]; then
    echo $user > /etc/.$user.ini
    else
    rm -f /etc/.$user.ini > /dev/null 2>&1
    fi
    done
    rm -f /root/tmp
}

MYIP=$(curl -sS ipinfo.io/ip)
Name=$(curl -sS https://raw.githubusercontent.com/halluboys/perizinan/main/main/allow | grep $MYIP | awk '{print $2}')
echo $Name > /usr/local/etc/.$Name.ini
CekOne=$(cat /usr/local/etc/.$Name.ini)

Bloman () {
if [ -f "/etc/.$Name.ini" ]; then
CekTwo=$(cat /etc/.$Name.ini)
    if [ "$CekOne" = "$CekTwo" ]; then
        res="Expired"
    fi
else
res="Permission Accepted..."
fi
}

PERMISSION () {
    MYIP=$(curl -sS ipinfo.io/ip)
    IZIN=$(curl -sS https://raw.githubusercontent.com/halluboys/perizinan/main/main/allow | awk '{print $4}' | grep $MYIP)
    if [ "$MYIP" = "$IZIN" ]; then
    Bloman
    else
    res="Permission Denied!"
    fi
    BURIQ
}
red='\e[1;31m'
green='\e[1;32m'
NC='\e[0m'
green() { echo -e "\\033[32;1m${*}\\033[0m"; }
red() { echo -e "\\033[31;1m${*}\\033[0m"; }
PERMISSION

if [ -f /home/needupdate ]; then
red "Your script need to update first !"
exit 0
elif [ "$res" = "Permission Accepted..." ]; then
echo -ne
else
red "Permission Denied!"
exit 0
fi
clear
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

