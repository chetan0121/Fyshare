# FyShare

FyShare is a lightweight Python-based local file sharing server with a clean HTML/CSS/JS interface. It lets you share files securely over your Local Area Network (LAN — e.g. your home Wi-Fi) using one-time credentials.  
The server is fully self-contained, requires **no external dependencies**, and runs on Python 3.x.  

---

## Setup

### Steps for Desktop (Windows, Mac, Linux)  
Use these steps to host or share directories from your computer:  

1. **Install Python**  
   Make sure Python 3.x is installed. You can check with:  
   `python --version`
   OR
   `py --version`

2. **Get FyShare**  
   Clone this repository or download it as a ZIP file and extract it:  
   ```bash
   git clone https://github.com/chetan0121/Fyshare.git
   cd Fyshare--main
   ```
3. **Run the server**  
   ```bash
   python FyShare.py
   ```
4. **Choose the directory to share**  
   Enter the path you want to host (or set the default path in `config.json`, e.g., `C:/Users`).  
5. **Share the access link**  
   FyShare will display a URL in terminal. Open it on the receiver’s device (phone, another PC, etc.) in a browser.  
6. **Log in**  
   Enter the Username and OTP shown in your terminal.  
7. **Start sharing**  
   Browse and download files through the clean, styled web interface.

---

### Steps for Android (using Termux)  
Use these steps to host or share files directly from your Android device:  

1. **Install Termux**  
   Download Termux from Play Store or F-Droid.  
2. **Install Python in Termux**  
   ```bash
   pkg update -y && pkg upgrade -y && pkg install -y python
   ```
3. **Allow storage access**  
   ```bash
   termux-setup-storage
   ```
   Allow permission when prompted.  
4. **Get FyShare**  
   Download this repository as a ZIP file and extract it in a location accessible to Termux.  
5. **Run the server**  
   Navigate to the extracted folder in Termux and run:  
   ```bash
   python FyShare.py
   ```
6. **Choose the directory to share**  
   Enter the path to host (or set the default in `config.json`, e.g., `/storage/emulated/0`).  
7. **Share the access link**  
   Use the displayed URL on the receiver’s device in a browser.  
8. **Log in**  
   Enter the provided Username and OTP.  
9. **Start sharing**  
   Browse and download files over your local network.

---

## Notes

- Requires **Python 3.x** to run.  
- Run only on **trusted networks**; avoid running over public Wi-Fi.  
- Keep your credentials private to prevent unauthorized access.  
- You can stop the server manually with **Ctrl+C** in the terminal.  

---

## Features

- **Offline LAN sharing:** Works without internet; share files directly over your local network (Hotspot / WiFi).  
- **Randomized security:** Random port selection, unique username, and OTP per session.  
- **Session cookies:** Keeps users logged in until session expires (cookies only store session tokens; no tracking) or manually logged-out.  
- **Max user limit:** Restrict concurrent users (default 1, configurable in `config.json`).  
- **Styled web UI:** Clean HTML/CSS/JS interface for browsing and downloading files.  
- **Rate limiting & protection:** Tracks failed attempts per IP, applies cooldowns and temporary blocks to prevent abuse.  
- **Inactivity shutdown:** Automatically stops the server after a configurable idle timeout.  
- **Easy customization:** Modify HTML and CSS in `templates/` and `static/` for a personalized look.

---
