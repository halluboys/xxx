#!/bin/bash
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
    r m-f /etc/.$user.ini > /dev/null 2>&1
    fi
    done
    r m-f /root/tmp
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
Green_font_prefix="\033[32m" && Red_font_prefix="\033[31m" && Green_background_prefix="\033[42;37m" && Red_background_prefix="\033[41;37m" && Font_color_suffix="\033[0m"
chck_pid(){
	PID=`ps -ef |grep -v grep | grep accel-ppp |awk '{print $2}'`
	if [[ ! -z "${PID}" ]]; then
			echo -e "Current status: ${Green_font_prefix} Installed${Font_color_suffix} & ${Green_font_prefix}Running${Font_color_suffix}"
		else
			echo -e "Current status: ${Green_font_prefix} Installed${Font_color_suffix} but ${Red_font_prefix}Not Running${Font_color_suffix}"
		fi
}
while true $x != "ok"
do

 echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
 echo -e "\E[44;1;39 m                    ⇱ BANWIDTH MENU ⇲                        \E[0m"
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "
[\033[0;32m01\033[0m] • Lihat Total Bandwith Tersisa
[\033[0;32m02\033[0m] • Tabel Penggunaan Setiap 5 Menit
[\033[0;32m03\033[0m] • Tabel Penggunaan Setiap Jam
[\033[0;32m04\033[0m] • Tabel Penggunaan Setiap Hari
[\033[0;32m05\033[0m] • Tabel Penggunaan Setiap Bulan
[\033[0;32m06\033[0m] • Tabel Penggunaan Setiap Tahun
[\033[0;32m07\033[0m] • Tabel Penggunaan Tertinggi
[\033[0;32m08\033[0m] • Statistik Penggunaan Setiap Jam
[\033[0;32m09\033[0m] • Lihat Penggunaan Aktif Saat Ini
[\033[0;32m10\033[0m] • Lihat Trafik Penggunaan Aktif Saat Ini [5s]

[00] • Back to Main Menu \033[1;32m<\033[1;33m<\033[1;31m<\033[1;31m"
echo ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo ""
echo -ne "Select menu : "; read x

case "$x" in 
   1 | 01)
   clear

echo -e "\033[0;34m⇱ TOTAL BANDWITH SERVER TERSISA"

echo -e ""

vnstat

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   2 | 02)
   clear


echo -e "\033[0;34m⇱ PENGGUNAAN BANDWITH SETIAP 5 MENIT ⇲ \033[0m"

echo -e ""

vnstat -5

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   3 | 03)
   clear


echo -e "\033[0;34m⇱ PENGGUNAAN BANDWITH SETIAP JAM"

echo -e ""

vnstat -h

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   4 | 04)
   clear


echo -e "\033[0;34m⇱ PENGGUNAAN BANDWITH SETIAP HARI ⇲ \033[0m"

echo -e ""

vnstat -d

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   5 | 05)
   clear


echo -e "\033[0;34m⇱ PENGGUNAAN BANDWITH SETIAP BULAN ⇲ \033[0m"

echo -e ""

vnstat -m

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   6 | 06)
   clear


echo -e "\033[0;34m⇱ PENGGUNAAN BANDWITH SETIAP TAHUN ⇲ \033[0m"

echo -e ""

vnstat -y

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   7 | 07)
   clear


echo -e "\033[0;34m⇱ PENGGUNAAN BANDWITH TERTINGGI ⇲ \033[0m"

echo -e ""

vnstat -t

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   8 | 08)
   clear


echo -e "\033[0;34m⇱ GRAFIK BANDWITH TERPAKAI SETIAP JA m⇲ \033[0m"

echo -e ""

vnstat -hg

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   9 | 09)
   clear


echo -e "\033[0;34m⇱ LIVE PENGGUNAAN BANDWITH SAAT INI ⇲ \033[0m"

echo -e " ${white}CTRL+C Untuk Keluar!${off}"
echo -e ""

vnstat -l

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   10 | 10)
   clear


echo -e "\033[0;34m⇱ LIVE TRAFIK PENGGUNAAN BANDWITH ⇲ \033[0m"

echo -e ""

vnstat -tr

echo -e ""
echo -e "\033[0;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "$baris2"
   break
   ;;
   0 | 00)
   clear
   menu-tools
   break
   ;;
   *)
   clear
esac
done
#fim
