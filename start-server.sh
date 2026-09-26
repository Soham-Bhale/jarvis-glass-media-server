#!/data/data/com.termux/files/usr/bin/bash

# ==========================================================
# JARVIS Glass Media Server - 1-Click Termux Launch Script
# ==========================================================

echo "=========================================================="
echo " Starting JARVIS Glass Media Server & Cloud Storage..."
echo "=========================================================="

# 1. Acquire CPU Wake-Lock so Android doesn't sleep the server
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    echo "[+] CPU wake-lock acquired (runs 24/7 in background)."
fi

# 2. Start SSH Daemon if not already running
if ! pgrep -x "sshd" >/dev/null; then
    sshd
    echo "[+] OpenSSH server started on port 8022."
else
    echo "[+] OpenSSH server is already active on port 8022."
fi

# 3. Detect Phone's Local IP Address
WLAN_IP=$(ip -4 addr show wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
if [ -z "$WLAN_IP" ]; then
    WLAN_IP=$(ifconfig 2>/dev/null | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -n 1)
fi

CURRENT_USER=$(whoami 2>/dev/null || echo "user")

echo "----------------------------------------------------------"
echo " [*] Termux SSH User : $CURRENT_USER"
echo " [*] Termux SSH Port : 8022"
if [ -n "$WLAN_IP" ]; then
    echo " [*] Connect via SSH : ssh $CURRENT_USER@$WLAN_IP -p 8022"
    echo " [*] Media Server URL: http://$WLAN_IP:8000"
else
    echo " [*] Connect via SSH : ssh $CURRENT_USER@<phone_ip> -p 8022"
    echo " [*] Media Server URL: http://localhost:8000"
fi
echo "=========================================================="

# 4. Launch FastAPI Server
python app.py
