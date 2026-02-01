#!/usr/bin/env python3
"""
Auxiliary script to update Claude usage.
Supports: manual (percentage), automatic (fetch with cookies), display (show).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def fetch_and_update():
    """Fetch usage from API with cookies and updates config."""
    config_dir = Path.home() / ".config" / "claude-usage"
    cookie_file = config_dir / "cookies.txt"
    config_file = config_dir / "config.json"

    if not cookie_file.exists():
        print("❌ No cookies configured.")
        print(f"   Save your cookies in: {cookie_file}")
        print("   See instructions in README.md")
        return False

    # Run get_usage.py as a subprocess using venv or system
    script_dir = Path(__file__).resolve().parent
    get_usage_script = script_dir / "get_usage.py"
    
    venv_python = config_dir / "venv" / "bin" / "python3"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable

    import subprocess
    try:
        result = subprocess.run(
            [python_exe, str(get_usage_script), "--quiet", "--raw"],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode != 0 or not result.stdout.strip():
            print("❌ Error fetching usage. Cookies may have expired.")
            print("   Export fresh cookies from claude.ai")
            return False
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ImportError):
        print("❌ Error executing get_usage.py")
        return False

    # Use five_hour (Pro) or seven_day as fallback
    usage_info = data.get("five_hour") or data.get("seven_day")
    if not usage_info:
        print("❌ Unexpected response from API")
        return False

    utilization = usage_info.get("utilization", 0)
    resets_at = usage_info.get("resets_at")

    config_dir.mkdir(parents=True, exist_ok=True)
    config = {}
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)

    config["usage_percentage"] = int(utilization)
    config["last_auto_update"] = datetime.now().isoformat()
    if resets_at:
        config["reset_at"] = resets_at

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Usage automatically updated: {int(utilization)}%")
    if resets_at:
        print(f"⏰ Next reset: {resets_at}")
    print(f"📁 Config: {config_file}")
    return True


def update_usage(percentage):
    """Updates the usage percentage in the configuration file"""
    config_file = os.path.expanduser("~/.config/claude-usage/config.json")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    
    # Read existing config or create new one
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        config = {
            "note": "Claude Usage Indicator configuration",
            "instructions": "Update usage_percentage manually or use the update_claude_usage.py script",
            "reset_hours": 5
        }
    
    # Update values
    config['usage_percentage'] = int(percentage)
    config['last_manual_update'] = datetime.now().isoformat()
    
    # Save
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Usage updated to {percentage}%")
    print(f"📁 File: {config_file}")
    print(f"⏰ Estimated next reset: in ~5 hours from now")

def show_current():
    """Shows the current usage"""
    config_file = Path.home() / ".config" / "claude-usage" / "config.json"

    if not config_file.exists():
        print("❌ No usage data saved yet")
        return

    with open(config_file) as f:
        config = json.load(f)

    percentage = config.get("usage_percentage", 0)
    last_update = config.get("last_auto_update") or config.get(
        "last_manual_update", "Never"
    )
    reset_at = config.get("reset_at", "")

    print(f"📊 Current usage: {percentage}%")
    print(f"🕐 Last update: {last_update}")
    if reset_at:
        print(f"⏰ Next reset: {reset_at}")
    print(f"📁 Configuration file: {config_file}")

def main():
    if len(sys.argv) < 2:
        print("Claude Usage Updater")
        print("=" * 50)
        print("\nUsage:")
        print(f"  {sys.argv[0]} fetch            - Automatically fetch usage (requires cookies)")
        print(f"  {sys.argv[0]} <percentage>     - Manually update usage (0-100)")
        print(f"  {sys.argv[0]} show             - Show current usage")
        print("\nExamples:")
        print(f"  {sys.argv[0]} fetch  # Get from API (with cookies)")
        print(f"  {sys.argv[0]} 45     # Manually update to 45%")
        print(f"  {sys.argv[0]} show   # View current usage")
        print("\n💡 For automatic fetch: save cookies to ~/.config/claude-usage/cookies.txt")
        sys.exit(1)

    if sys.argv[1].lower() == "fetch":
        sys.exit(0 if fetch_and_update() else 1)
    if sys.argv[1].lower() == "show":
        show_current()
    else:
        try:
            percentage = float(sys.argv[1])
            if 0 <= percentage <= 100:
                update_usage(percentage)
            else:
                print("❌ Error: Percentage must be between 0 and 100")
                sys.exit(1)
        except ValueError:
            print("❌ Error: You must provide a valid number")
            sys.exit(1)

if __name__ == "__main__":
    main()
