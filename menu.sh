#!/bin/bash
# Color Validation
color1='\e[031;1m'
color2='\e[34;1m'
color3='\e[0m'
DF='\e[39m'
Bold='\e[1m'
Blink='\e[5m'
yell='\e[33m'
red='\e[1;31m'
green='\e[1;32m'
blue='\e[1;34m'
PURPLE='\e[1;95m'
CYAN='\e[1;36m'
Lred='\e[1;91m'
Lgreen='\e[92m'
Lyellow='\e[93m'
white='\e[1;37m'
NC='\e[0m'
MYIP=$(curl -sS ipv4.icanhazip.com)
#########################
# VPS Information
Checkstart1=$(ip route | grep default | cut -d ' ' -f 3 | head -n 1);
if [[ $Checkstart1 == "venet0" ]]; then
    clear
	  lan_net="venet0"
    typevps="OpenVZ"
else
    clear
		lan_net="eth0"
    typevps="KVM"
fi
clear
# DNS Patch
tipeos2=$(uname -m)
# OS Uptime
uptime="$(uptime -p | cut -d " " -f 2-10)"

source /etc/os-release
Versi_OS=$VERSION
ver=$VERSION_ID
Tipe=$NAME
URL_SUPPORT=$HOME_URL
basedong=$ID
ISP=$(curl -s ipinfo.io/org | cut -d " " -f 2-10 )
CITY=$(curl -s ipinfo.io/city )
WKT=$(curl -s ipinfo.io/timezone )
domain=$(cat /etc/xray/domain)
#Sver=$(cat /home/version)
DAY=$(date +%A)
DATE=$(date +%m/%d/%Y)
IPVPS=$(curl -s ipinfo.io/ip )
	freq=$( awk -F: ' /cpu MHz/ {freq=$2} END {print freq}' /proc/cpuinfo )
	tram=$( free -m | awk 'NR==2 {print $2}' )
	uram=$( free -m | awk 'NR==2 {print $3}' )
	fram=$( free -m | awk 'NR==2 {print $4}' )
	swap=$( free -m | awk 'NR==4 {print $2}' )
clear
echo -e ""
echo -e ""
echo -e "  $Lred                                            )     "
echo -e "  $Lred      )           (         )   .   ,    ( /(     "
echo -e "  $Lred     /( (     (   )\ )   ( /(    ) (    )\())     "
echo -e "  $Lred    (_)))\  _ )\ (()/(   )\())  /( )\  ((_)\      "
echo -e "  $CYAN ━━━$red(\e[93m_$red)\e[93m_$red(\e[93m_$red)(\e[93m_$red((\e[93m_$red)$CYAN━$red)(\e[93m_$red))$CYAN━$red((\e[93m_$red)\\e[93m__$red)(\e[93m_$red)((\e[93m_$red)(\e[93m__$red((\e[93m_$red)$CYAN━━━━━ "
echo -e "   \E[44;1;39m      ⇱ Premium Server Script By GEO ⇲           \E[0m"
echo -e "  $CYAN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ "
  echo -e "  $green Isp Name             :$white  $ISP"
  echo -e "  $green Domain               :$Lyellow  $domain"
  echo -e "  $green Ip Vps               :$Lyellow  $IPVPS"
  echo -e "  $green Operating System     :$white  "`hostnamectl | grep "Operating System" | cut -d ' ' -f5-`
  echo -e "  $green Total Amount Of RAM  : $white $tram MB"
  echo -e "  $green Used RAM             :$white  $uram MB"
  echo -e "  $green Free RAM             :$white  $fram MB"
  echo -e "  $green System Uptime        :$white  $uptime"
  echo -e "  $green City                 :$white  $CITY"
  echo -e "  $green Time                 :$white  $WKT"
  echo -e "  $green Day                  :$white  $DAY"
  echo -e "  $green Date                 :$white  $DATE"
  #echo -e "  $green Script Version    :$Lyellow  $Sver"
echo -e "  $CYAN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "   \E[44;1;39m                ⇱ Dashboard Menu ⇲               \E[0m"
echo -e "  $CYAN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e ""
echo -e "   [${green}01${NC}]${color1} •$white SSH & OpenVPN (${color2}menu-ssh${color3})$NC"
echo -e "   [${green}02${NC}]${color1} •$white SSTP - L2TP - PPTP - Wireguard (${color2}menu-vpn${color3})$NC"
echo -e "   [${green}03${NC}]${color1} •$white Shadowsocks & ShadowsocksR (${color2}menu-shadowsocks${color3})$NC"
echo -e "   [${green}04${NC}]${color1} •$white V2ray Vmess & Vless (${color2}menu-v2ray${color3})$NC"
echo -e "   [${green}05${NC}]${color1} •$white Trojan & TrojanGO (${color2}menu-trojan${color3})$NC"
echo -e "   [${green}05${NC}]${color1} •$white Backup (${color2}menu-backup${color3})$NC"
echo -e "   [${green}07${NC}]${color1} •$white Trial Account (${color2}menu-trial${color3})$NC"
echo -e "   [${green}08${NC}]${color1} •$white System Tools (${color2}menu-tools${color3}) $NC"
echo ""
echo -e "   [${green}00${NC}]${color1} •$white $bd Back to exit Menu \033[1;32m<\033[1;33m<\033[1;31m<\033[1;31m"
echo ""
echo -e "  $CYAN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $NC"
echo -e "   \E[44;1;39m                ⇱ GEOVPN PROJECT ⇲               \E[0m"
echo -e "  $CYAN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $NC"
echo -e "  $CYAN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $NC"
echo -e "  $green Client Name    ${color1}•$Lyellow $Name"
echo -e "  $green Script Expired ${color1}•$Lyellow $Exp2"
echo -e "  $CYAN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $NC"
echo -e "  $CYAN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ $NC"
echo -e  ""
 read -p "  Select menu :  " menu
echo -e   ""
case $menu in
1 | 01)
menu-ssh
;;
2 | 02)
menu-vpn
;;
3 | 03)
menu-shadowsocks
;;
4 | 04)
menu-v2ray
;;
5 | 05)
menu-trojan
;;
6 | 06)
menu-backup
;;
7 | 07)
menu-trial
;;
8 | 08)
menu-tools
;;
9 | 09)
installbot
;;
0 | 00)
exit
;;
*)
menu
;;
esac
