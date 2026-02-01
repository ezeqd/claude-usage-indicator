# Claude Usage Indicator for Ubuntu MATE

A professional taskbar indicator that shows your Claude usage (shared between claude.ai and Claude Code). Specifically designed for Claude Pro users who need to monitor their 5-hour and weekly limits.

## 🎯 Features

- **Dual Usage Monitor**: Displays both **short-term (5h)** and **weekly** usage separately.
- **Automatic Updates**: Fetches real usage from the official Claude API.
- **Simplified Session Renewal**: Log in directly from the indicator to capture cookies automatically without manual code copying.
- **Official Iconography**: Uses the official Claude "C" icon for perfect system integration.
- **Visual Indicators**: Smart color coding (🟢, 🟡, 🔴) based on the most critical limit.
- **Reset Information**: Precise countdown for your next 5-hour reset.
- **Offline Detection**: Alerts you if the displayed data is stale (cache) or if there was a connection error.
- **Auto-start**: Configures itself to start with your system.

## 📋 Requirements

- Ubuntu MATE 24.04 LTS (or AppIndicator compatible)
- Python 3
- Claude Pro subscription (recommended to see both limits)
- Internet connection

## 🚀 Installation

The installer is smart and detects your current dependencies to avoid unnecessary system updates.

```bash
chmod +x install.sh
./install.sh
```

During installation, you will be asked if you want to install **Playwright**. Say **yes (`s`)** to enable automatic updates and integrated login. A secure virtual environment will be created in `~/.config/claude-usage/venv` to avoid interfering with your system.

## 📖 How to Use

### 1. Start the Indicator
The indicator starts automatically when you log in. If you need to launch it manually:
```bash
python3 /usr/local/bin/claude_usage_indicator.py &
```

### 2. Account Configuration (Login)
No more copying cookies from DevTools:
1. Click the Claude icon on your taskbar.
2. Select **🔑 Renew Session (Login)**.
3. A browser window will open; log in normally.
4. Once you enter your chats, the window will close automatically and your stats will appear in seconds.

### 3. Understanding Limits
- **Usage (5h)**: The dynamic quota that resets several times a day. Most common for intensive users.
- **Weekly Usage**: The total message limit for your Pro subscription per week.
- **Reset (5h)**: Indicates exactly how much time is left for your short-term message quota to recover.

### 4. Manual Update (Optional)
If you prefer not to use automatic mode, you can update the value manually:
```bash
update_claude_usage.py 45  # Sets usage to 45%
```

## 🔧 Configuration
Everything is saved in:
- `~/.config/claude-usage/config.json`: Cached usage data.
- `~/.config/claude-usage/cookies.txt`: Current session (protect this file).
- `~/.config/claude-usage/venv/`: Virtual environment for Playwright.

## 🛠️ Troubleshooting

### Indicator shows 0% or "Offline"
- Check your internet connection.
- Your session might have expired. Use the **Renew Session (Login)** option from the menu.
- Check for specific errors by clicking the menu (they will appear in red if the API fails).

### I don't see the official icon
- Make sure you ran `install.sh` recently. The icon is installed at `/usr/share/pixmaps/claude-usage.png`.

## 📝 Technical Notes
- **Security**: The automatic login process uses Playwright in "headed" mode only for you to enter your credentials; the script never sees or saves your password, it only captures the final session cookie.
- **Multi-Account**: If you change accounts in the login browser, the indicator will update with the new account.

---
**Security Note**: The `cookies.txt` file contains credentials. Do not share it. This project is intended for personal and local use.
