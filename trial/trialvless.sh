#!/bin/bash
red='\e[1;31m'
green='\e[0;32m'
NC='\e[0m'
MYIP=$(curl -sS ipinfo.io/ip)
echo "Checking VPS"
clear
source /var/lib/geovpnstore/ipvps.conf
if [[ "$IP" = "" ]]; then
domain=$(cat /etc/xray/domain)
else
domain=$IP
fi
tls="$(cat ~/log-install.txt | grep -w "Vless TLS" | cut -d: -f2|sed 's/ //g')"
none="$(cat ~/log-install.txt | grep -w "Vless None TLS" | cut -d: -f2|sed 's/ //g')"
# Create Expried 
masaaktif="1"
exp=$(date -d "$masaaktif days" +"%Y-%m-%d")

# Make Random Username 
user=Trial`</dev/urandom tr -dc X-Z0-9 | head -c4`
uuid=$(cat /proc/sys/kernel/random/uuid)

sed -i '/#tls$/a\### '"$user $exp"'\
},{"id": "'""$uuid""'","email": "'""$user""'"' /etc/v2ray/vless.json
sed -i '/#none$/a\### '"$user $exp"'\
},{"id": "'""$uuid""'","email": "'""$user""'"' /etc/v2ray/vnone.json
vlesslink1="vless://${uuid}@${domain}:$tls?path=nur&security=tls&encryption=none&type=ws#${user}"
vlesslink2="vless://${uuid}@${domain}:$none?path=nur&encryption=none&type=ws#${user}"
systemctl restart xray@vless
systemctl restart xray@vnone
clear
echo -e ""
echo -e "=================================" | lolcat
echo -e "          TRIAL XRAY / VLESS  "
echo -e "=================================" | lolcat
echo -e "Remarks        : ${user}"
echo -e "Domain         : ${domain}"
echo -e "port TLS       : $tls"
echo -e "port none TLS  : $none"
echo -e "id             : ${uuid}"
echo -e "Encryption     : none"
echo -e "network        : ws"
echo -e "path           : geo"
echo -e "=================================" | lolcat
echo -e "Link TLS       : ${vlesslink1}"
echo -e "=================================" | lolcat
echo -e "Link None TLS  : ${vlesslink2}"
echo -e "=================================" | lolcat
echo -e " ${green}Aktif Selama   : $masaaktif Hari"
echo -e "=================================" | lolcat
echo -e "Script Installer By : Geo•NTB" | lolcat
echo -e "=================================" | lolcat
