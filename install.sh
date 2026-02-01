#!/bin/bash
# Installation script for Claude Usage Indicator

set -e

echo "================================================"
echo "Claude Usage Indicator Installer"
echo "================================================"
echo ""

# Check dependencies
echo "📦 Checking dependencies..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python 3: sudo apt install python3"
    exit 1
fi

# Install system dependencies first
echo "📦 Checking system packages..."
pkgs=("python3-gi" "gir1.2-appindicator3-0.1" "gir1.2-gtk-3.0" "python3-venv" "python3-pip")
missing_pkgs=()

for pkg in "${pkgs[@]}"; do
    if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "ok installed"; then
        missing_pkgs+=("$pkg")
    fi
done

if [ ${#missing_pkgs[@]} -gt 0 ]; then
    echo "   Installing missing packages: ${missing_pkgs[*]}"
    sudo apt update
    sudo apt install -y "${missing_pkgs[@]}"
else
    echo "   ✅ All system dependencies are already installed"
fi

# Install Playwright for automatic fetch (optional)
echo "📦 Checking Playwright (for automatic updates)..."
VENV_PATH="$HOME/.config/claude-usage/venv"
mkdir -p "$(dirname "$VENV_PATH")"

if [ -f "$VENV_PATH/bin/python3" ] && "$VENV_PATH/bin/pip" show playwright &>/dev/null; then
    echo "   Playwright already installed in venv"
else
    echo "   Install Playwright for automatic updates? (y/n)"
    echo "   (A virtual environment will be created at $VENV_PATH)"
    read -r pw_response
    if [[ "$pw_response" =~ ^[Yy]$ ]]; then
        python3 -m venv "$VENV_PATH"
        "$VENV_PATH/bin/pip" install --upgrade pip
        "$VENV_PATH/bin/pip" install playwright
        "$VENV_PATH/bin/python3" -m playwright install chromium
        echo "   ✅ Playwright installed in virtual environment"
    else
        echo "   ⚠️  Without Playwright: you must update usage manually"
    fi
fi

# Copy files
echo "📋 Copying files..."

# Create directories if they don't exist
sudo mkdir -p /usr/local/bin
mkdir -p ~/.config/autostart

# Copy icon
echo "🖼️  Copying icon..."
sudo cp claude-usage.png /usr/share/pixmaps/claude-usage.png

# Copy main script
sudo cp claude_usage_indicator.py /usr/local/bin/
sudo chmod +x /usr/local/bin/claude_usage_indicator.py

# Copy update script
sudo cp update_claude_usage.py /usr/local/bin/
sudo chmod +x /usr/local/bin/update_claude_usage.py

# Copy automatic fetch script
sudo cp get_usage.py /usr/local/bin/
sudo chmod +x /usr/local/bin/get_usage.py

# Copy .desktop file for autostart
cp claude-usage-indicator.desktop ~/.config/autostart/

echo ""
echo "✅ Installation completed!"
echo ""
echo "================================================"
echo "How to use:"
echo "================================================"
echo ""
echo "1. Start the indicator manually:"
echo "   python3 /usr/local/bin/claude_usage_indicator.py"
echo ""
echo "   Or simply log out and log back in"
echo "   (it will start automatically)"
echo ""
echo "2. Update your usage:"
echo "   a) Automatic (with cookies/login):"
echo "      - Use 'Renew Session (Login)' in the indicator menu"
echo "      - Or save cookies to ~/.config/claude-usage/cookies.txt"
echo ""
echo "   b) Manual:"
echo "      - Go to https://claude.ai/settings/usage"
echo "      - update_claude_usage.py <percentage>"
echo ""
echo "3. View current usage:"
echo "   update_claude_usage.py show"
echo ""
echo "The indicator updates every 5 minutes."
echo "With configured cookies, fetch is automatic."
echo ""
echo "Do you want to start the indicator now? (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "🚀 Starting Claude Usage Indicator..."
    nohup python3 /usr/local/bin/claude_usage_indicator.py > /dev/null 2>&1 &
    echo "✅ Indicator started. You should see it in your taskbar."
else
    echo "👍 You can start it later by logging out and back in,"
    echo "   or by running: python3 /usr/local/bin/claude_usage_indicator.py"
fi

echo ""
echo "Enjoy your Claude indicator! 🎉"
