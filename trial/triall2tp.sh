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

ISP=$(curl -s ipinfo.io/org | cut -d " " -f 2-10 )
CITY=$(curl -s ipinfo.io/city )
COUNTRY=$(curl -s ipinfo.io/country )

MYIP=$(curl -sS ipinfo.io/ip)
clear
source /var/lib/geovpnstore/ipvps.conf
if [[ "$IP" = "" ]]; then
PUBLIC_IP=$(cat /etc/xray/domain);
else
PUBLIC_IP=$IP
fi

# Create Expried 
masaaktif="1"
exp=$(date -d "$masaaktif days" +"%Y-%m-%d")

# Make Random Username 
VPN_USER=Trial`</dev/urandom tr -dc X-Z0-9 | head -c4`
VPN_PASSWORD=123

# Add or update VPN user
cat >> /etc/ppp/chap-secrets <<EOF
"$VPN_USER" l2tpd "$VPN_PASSWORD" *
EOF

VPN_PASSWORD_ENC=$(openssl passwd -1 "$VPN_PASSWORD")
cat >> /etc/ipsec.d/passwd <<EOF
$VPN_USER:$VPN_PASSWORD_ENC:xauth-psk
EOF

# Update file attributes
chmod 600 /etc/ppp/chap-secrets* /etc/ipsec.d/passwd*
echo -e "### $VPN_USER $exp">>"/var/lib/geovpnstore/data-user-l2tp"

echo -e ""
echo -e "${red}================================${off}"
echo -e "         TRIAL L2TP/IPSEC${off}"
echo -e "${red}================================${off}"
echo -e " ${white}ISP   : $ISP"
echo -e " CITY          : $CITY"
echo -e " COUNTRY       : $COUNTRY"
echo -e " Server IP     : $MYIP"
echo -e " Server Host   : $PUBLIC_IP"
echo -e " IPSec PSK     : myvpn"
echo -e " Username      : $VPN_USER"
echo -e " Password      : $VPN_PASSWORD${off}"
echo -e "${red}================================${off}"
echo -e " ${white}Aktif Selama : $masaaktif Hari"
echo -e "${red}=================================${off}"
echo -e ""
