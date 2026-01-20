# FyShare

**FyShare** is a lightweight, dependency-free Python tool that lets you quickly host a temporary file-sharing server on your local network (LAN) with a clean web interface.

Perfect for sharing files offline over your trusted local area network — no internet required.

Designed for simplicity and usability.

Minimum required version: **Python 3.9+**

---

## Features

- **Zero Dependencies:** Runs entirely on the Python standard library.
- **Secure by Design:**
  - Randomly selected ports (1500-9500).
  - Per-session OTPs with limited validity and periodic rotation.
  - Rate limiting and brute-force protection (tracks failed attempts per IP, applies cooldowns and temporary blocks).
  - Uses security headers (CSP, X-Frame-Options, etc.).
  - Automatically stops the server after an idle timeout (from `config.json`).
  - Restricts concurrent users (maximum set in `config.json`).
  
- **Offline LAN Sharing:** Works without internet; share files directly over your local network.  
- **Session Cookies:** Keeps users logged in until the session expires or they log out manually.
- **Styled Web UI:** Clean web (HTML/CSS/JS) interface for browsing and downloading files.
- **Cross-Platform:** Runs on Windows, macOS, Linux, and Android via any Python interpreter.
- **Easy Customization:** Modify the design in `templates/` and `static/` for a personalized look.

---

## Requirements

- Host and receiver connected to the same LAN.
- A browser on the receiver's device (e.g., Chrome).
- **Python 3.9** or higher on the host's device.

Check your version:
```bash
python --version
# or
py --version
```

---

## Installation

**Get the files:**
- **Clone the repository**
   ```bash
   git clone https://github.com/chetan0121/Fyshare.git
   cd Fyshare
   ```

   **OR**

- **Download as ZIP:**
   Download the source code, extract it, and open a terminal in the extracted folder.

---

## Usage

### Desktop (Windows / Mac / Linux)

1. **Start the server:**
   ```bash
   python FyShare.py
   ```

2. **Select a directory:**
   The application will ask which directory you want to share. You can choose the default path, enter a custom path, or use a temporary path. (e.g., `%USERPROFILE%\Downloads`)

3. **Connect:**
   - The terminal will display a **URL** (e.g., `http://192.168.1.5:4521`) and an **OTP**.
   - Open the URL on the browser of any device connected to the same LAN.
   - Enter the OTP to log in.

4. **Stop the server:**
   Press `Ctrl+C` in the terminal to stop the server manually after use, or wait for automatic idle shutdown.


### Android (via Termux)
Steps to host a file-sharing server from an Android device using Termux.

**Note:** You can use any other app that can run Python 3.9+.

1. **Install Termux:**  
    Download Termux from Play Store or F-Droid.  

2. **Install Python:**
    ```bash
    pkg update && pkg upgrade
    pkg install python
    ```

3. **Allow storage access:**  
    ```bash
    termux-setup-storage
    ```
    Allow storage permission to Termux when prompted.  

4. **Download FyShare:**
    Do the same as the Installation section.

5. **Run the server:**  
   - Copy the path to `FyShare.py` from the extracted folder.
   - Go to Termux and run this command:
   ```bash
   python "copied_path"
   ```
   - Example command: `python "/storage/emulated/0/Download/Fyshare-main/FyShare.py"`

6. **After Running:**
   Follow steps 2–4 from the Desktop section above.

---

## Configuration

This will help you modify `config.json`:

| Key                    | Description                                          |
| :---                   | :---                                                 |
| `root_directory`       | The default path to share/serve                      |
| `max_users`            | Maximum concurrent users allowed.                    |
| `idle_timeout_minutes` | Server auto-shutdown time if no users are logged in. |
| `refresh_time_seconds` | Server state refresh interval.                       |
| `max_attempts_per_ip`  | Failed login attempts before cooldown.               |
| `cooldown_seconds`     | Duration of cooldown after failed attempts.          |
| `block_time_minutes`   | Duration an IP is blocked after excessive failures.  |

---   

## Limitations

- **HTTP Only:** FyShare uses plain HTTP. It is intended for use on trusted local networks (Home/Office Wi-Fi). **Do not expose this directly to the public internet.**
