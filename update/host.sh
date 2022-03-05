#!/bin/bash

grey='\x1b[90m'
red='\x1b[91m'
green='\x1b[92m'
yellow='\x1b[93m'
blue='\x1b[94m'
purple='\x1b[95m'
cyan='\x1b[96m'
white='\x1b[37m'
bold='\033[1m'
off='\x1b[m'
flag='\x1b[47;41m'
clear
sys=$(cat /etc/xray/domain)
Geogabut=paoandest@gmail.com
Geo=1d158d0efc4eef787222cefff0b6d20981462
DM1=apa-itu.website
DM2=bothervpn.tk
DM3=vpsku.space
DM4=gassfull.tech
DM5=geo-gabut.me
DM6=geoganteng.my.id
DM7=geoganteng.tech
DM8=gua-mau.online
DM9=vip-server.xyz
echo -e ""
echo -e "${cyan}=================================${off}"
echo -e " DNS Record For Custom Subdomain" | lolcat
echo -e "${red}---------------------------------${off}"
echo -e "      SILAHKAN PILIH DOMAIN " | lolcat
echo -e "${cyan}=================================${off}"
echo -e "${green}"
echo -e "    1 ⸩  $DM1"
echo -e "    2 ⸩  $DM2"
echo -e "    3 ⸩  $DM3"
echo -e "    4 ⸩  $DM4"
echo -e "    5 ⸩  $DM5"
echo -e "    6 ⸩  $DM6"
echo -e "    7 ⸩  $DM7"
echo -e "    8 ⸩  $DM8"
echo -e "    9 ⸩  $DM9"
echo -e "${off}"
echo -e "---------------------------------" | lolcat
echo -e "    ${green}0 ⸩  Custom Domain ${off}"
echo -e "    ${green}x ⸩  Keluar ${off}"
echo -e "${cyan}=================================${off}"
echo ""
read -p "   [☆]  Masukkan Nomor :  " nom
if [[ $nom == '1' ]]; then
DOMAIN=$DM1
CF_ID=$Geogabut
CF_KEY=$Geo
elif [[ $nom == '2' ]]; then
DOMAIN=$DM2
CF_ID=$Geogabut
CF_KEY=$Geo
elif [[ $nom == '3' ]]; then
DOMAIN=$DM3
CF_ID=$Geogabut
CF_KEY=$Geo
elif [[ $nom == '4' ]]; then
DOMAIN=$DM4
CF_ID=$Geogabut
CF_KEY=$Geo
elif [[ $nom == '5' ]]; then
DOMAIN=$DM5
CF_ID=$Geogabut
CF_KEY=$Geo
elif [[ $nom == '6' ]]; then
DOMAIN=$DM6
CF_ID=$Geogabut
CF_KEY=$Geo
elif [[ $nom == '7' ]]; then
DOMAIN=$DM7
CF_ID=$Geogabut
CF_KEY=$Geo
elif [[ $nom == '8' ]]; then
DOMAIN=$DM8
CF_ID=$Geogabut
CF_KEY=$Geo
elif [[ $nom == '9' ]]; then
DOMAIN=$DM9
CF_ID=$Geogabut
CF_KEY=$Geo
elif [[ $nom == '0' ]]; then
echo -e "${green}Anda Harus Mempunyai Email Akun Cloudflare Dan Domain Aktif!${off}"
echo -e "${green}Untuk Api Key Bisa Anda Dapat Di Profil Akun Cloudflare Anda.${off}"
sleep 1
echo ""
read -rp "Masukkan Domain Anda : " -e DOMAIN
if [[ $DOMAIN == $DM1 ]] || [[ $DOMAIN == $DM2 ]] || [[ $DOMAIN == $DM3 ]] || [[ $DOMAIN == $DM4 ]] || [[ $DOMAIN == $DM5 ]] || [[ $DOMAIN == $DM6 ]] || [[ $DOMAIN == $DM7 ]] || [[ $DOMAIN == $DM8 ]] || [[ $DOMAIN == $DM9 ]] ; then
sleep 1
echo -e "${red}Masukkan Domain Mu Sendiri! Bukan Domain System!!!${off}"
sleep 1
echo ""
exit 0
fi
sleep 0.5
echo ""
read -rp "Masukkan Email Cloudflare : " -e CF_ID
sleep 0.5
echo ""
read -rp "Masukkan Api Key Cloudflare : " -e CF_KEY
clear
elif [[ $nom == 'x' ]]; then
clear
menu
else
echo -e "${red}Masukkan Nomor Yang Benar!${off}"
sleep 1
clear
hostnya
fi
sleep 1
if [[ $nom == '0' ]]; then
echo -e "${cyan}Domain Anda :${off}${green} ${DOMAIN} ${off}"
else
echo -e "${cyan}Domain Dipilih :${off}${green} ${DOMAIN} ${off}"
fi
echo -e ""
read -rp "Masukkan Subdomain: " -e sub
echo -e "${green}Menganalisis Subomain...${off}"
sleep 0.5
clear

SUB_DOMAIN=${sub}.${DOMAIN}
set -euo pipefail
IP=$(wget -qO- ipinfo.io/ip);
echo -e "${cyan}Pointing DNS Untuk Domain${off} ${green}${SUB_DOMAIN}...${off}"
sleep 1
clear
ZONE=$(curl -sLX GET "https://api.cloudflare.com/client/v4/zones?name=${DOMAIN}&status=active" \
-H "X-Auth-Email: ${CF_ID}" \
-H "X-Auth-Key: ${CF_KEY}" \
-H "Content-Type: application/json" | jq -r .result[0].id)
if [[ $ZONE == 'null' ]] || [[ $ZONE == "" ]]; then
echo -e "${red}ERROR!${off} ${green}Result Gagal, Kemungkinan Api Key Tidak Valid!${off}"
sleep 1
exit 0
fi
RECORD=$(curl -sLX GET "https://api.cloudflare.com/client/v4/zones/${ZONE}/dns_records?name=${SUB_DOMAIN}" \
-H "X-Auth-Email: ${CF_ID}" \
-H "X-Auth-Key: ${CF_KEY}" \
-H "Content-Type: application/json" | jq -r .result[0].id)
if [[ "${#RECORD}" -le 10 ]]; then
RECORD=$(curl -sLX POST "https://api.cloudflare.com/client/v4/zones/${ZONE}/dns_records" \
-H "X-Auth-Email: ${CF_ID}" \
-H "X-Auth-Key: ${CF_KEY}" \
-H "Content-Type: application/json" \
--data '{"type":"A","name":"'${SUB_DOMAIN}'","content":"'${IP}'","ttl":120,"proxied":false}' | jq -r .result.id)
fi
RESULT=$(curl -sLX PUT "https://api.cloudflare.com/client/v4/zones/${ZONE}/dns_records/${RECORD}" \
-H "X-Auth-Email: ${CF_ID}" \
-H "X-Auth-Key: ${CF_KEY}" \
-H "Content-Type: application/json" \
--data '{"type":"A","name":"'${SUB_DOMAIN}'","content":"'${IP}'","ttl":120,"proxied":false}')

echo "IP=$SUB_DOMAIN" >> /var/lib/akbarstorevpn/ipvps.conf

sleep 0.5
echo -e "${cyan}=================================${off}"
echo -e "     ${red}DOMAIN BERHASIL DISIMPAN${off}"
echo -e "${cyan}=================================${off}"
echo -e ""
echo -e "${green}Domain Anda Sekarang :${off} ${cyan}$SUB_DOMAIN${off}"
echo -e ""
echo -e "${cyan}=================================${off}"
echo -e "${red}NOTE :${off}"
echo -e "${green}Domain Ini Tidak Support Wildcard Atau Multi Subdomain!"
echo -e "Untuk VPN L2TP, SSTP, PPTP, Dan WIREGUARD,"
echo -e "Anda Harus Menggunakan Domain System${off} ${cyan}$sys $off}"
echo ""
