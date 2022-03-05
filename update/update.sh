#!/bin/bash
RED='\e[1;31m'
GREEN='\e[0;32m'
BLUE='\e[0;34m'
NC='\e[0m'
MYIP=$(wget -qO- icanhazip.com);
echo -e  "${RED}Checking VPS${NC}"
sleep 2
IZIN=$( curl https://raw.githubusercontent.com/halluboys/perizinan/main/ip | grep $MYIP )
if [ $MYIP = $IZIN ]; then
echo -e "${GREEN}Permission Accepted...${NC}"
sleep 2 
else
clear
echo -e ""
echo -e "======================================="
echo -e ""
echo -e "${RED}PERMINTAAN DITOLAK...!!! ${NC}"
echo -e "IP VPS ANDA BELUM TERDAFTAR"
echo -e "Contact WA https//wa.me/+6282339191527"
echo -e "For Registration IP VPS"
echo -e ""
echo -e "======================================="
echo -e ""
exit 0
fi
if [ "${EUID}" -ne 0 ]; then
		echo "You need to run this script as root"
		exit 1
fi
if [ "$(systemd-detect-virt)" == "openvz" ]; then
		echo "OpenVZ is not supported"
		exit 1
fi
clear
echo "Untuk Melakukan Tindakan Ini, Anda Harus Laporan Terlebih Dahulu Kepada Pihak Admin."
echo "Agar Diberikan Akses Pembaruan Pada Script VPS Anda!"
read -p "Sudah Laporan? [Y/N]:" arg
if [[ $arg == 'Y' ]]; then
  echo "Tindakan Diteruskan!"
  figlet -f slant Memperbarui... | lolcat
elif [[ $arg == 'y' ]]; then
  echo "Tindakan Diteruskan!"
  figlet -f slant Memperbarui... | lolcat
elif [[ $arg == 'N' ]]; then
  echo "Tindakan Dihentikan!"
  sleep 1
  clear
  neofetch
  exit 0
elif [[ $arg == 'n' ]]; then
  echo "Tindakan Dihentikan!"
  sleep 1
  clear
  neofetch
  exit 0
else
  echo "Argumen Tidak Diketahui!"
  sleep 1
  clear
  neofetch
  exit 0
fi
sleep 1

if [ ! -e /home/vps/public_html/TCP.ovpn ]; then
cp /etc/openvpn/client-tcp-1194.ovpn /home/vps/public_html/tcp.ovpn
cp /etc/openvpn/client-udp-2200.ovpn /home/vps/public_html/udp.ovpn
cp /etc/openvpn/client-tcp-ssl.ovpn /home/vps/public_html/ssl.ovpn

mkdir /root/OpenVPN
cp -r /etc/openvpn/client-tcp-ssl.ovpn OpenVPN/ssl.ovpn
cp -r /etc/openvpn/client-udp-2200.ovpn OpenVPN/udp.ovpn
cp -r /etc/openvpn/client-tcp-1194.ovpn OpenVPN/tcp.ovpn
cd /root
zip -r openvpn.zip OpenVPN > /dev/null 2>&1
cp -r /root/openvpn.zip /home/vps/public_html/geo.zip
rm -rf /root/OpenVPN
rm -f /root/openvpn.zip
fi
# text gambar
apt-get install boxes

# color text
cd
# banner /etc/issue.net
wget -O /etc/issue.net "https://vpnkuy.site/file/banner.conf"
echo "Banner /etc/issue.net" >>/etc/ssh/sshd_config
sed -i 's@DROPBEAR_BANNER=""@DROPBEAR_BANNER="/etc/issue.net"@g' /etc/default/dropbear

cd /usr/bin
wget -O /usr/bin/system https://github.com/halluboys/scriptvps/raw/main/menu/system.sh && chmod +x /usr/bin/system && cd /usr/bin && apt install -y dos2unix && dos2unix system

echo "0 0 * * * root clear-log && xp" >> /etc/crontab
echo "*/10 * * * * root xp-ws" >> /etc/crontab
cd
rm -f /root/key.pem
rm -f /root/cert.pem
rm -f /root/ssh-vpn.sh
rm -f /root/websocket.sh
rm -f /root/master.zip
rm -f /root/badvpn-master

apt install dnsutils jq -y
apt-get install net-tools -y
apt-get install tcpdump -y
apt-get install dsniff -y
apt install grepcidr -y

cd
systemctl restart cron
echo "1.0.1" > /home/ver
clear
figlet -f slant sukses | lolcat
rm -f update.sh
sleep 2
clear
neofetch
