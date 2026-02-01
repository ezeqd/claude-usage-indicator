#!/usr/bin/env python3
"""
Claude Usage Indicator for Ubuntu MATE
Displays Claude usage (shared between claude.ai and Claude Code) in the taskbar
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

class ClaudeUsageIndicator:
    def __init__(self):
        # Define icon (system or local)
        icon_path = "/usr/share/pixmaps/claude-usage.png"
        if not os.path.exists(icon_path):
            # Fallback to local for development
            icon_path = os.path.join(os.path.dirname(__file__), "claude-usage.png")
            if not os.path.exists(icon_path):
                icon_path = "dialog-information"

        self.indicator = AppIndicator3.Indicator.new(
            "claude-usage-indicator",
            icon_path,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Initialize usage data
        self.usage_data = {
            'five_hour': {'usage': 0, 'reset': None},
            'weekly': {'usage': 0, 'reset': None},
            'last_update': None
        }
        
        # Create menu
        self.menu = self.create_menu()
        self.indicator.set_menu(self.menu)
        
        # Update initial label
        self.update_label()
        
        # Start automatic update every 5 minutes
        GLib.timeout_add_seconds(300, self.auto_update)
        
        # First update
        threading.Thread(target=self.fetch_usage, daemon=True).start()
    
    def create_menu(self):
        menu = Gtk.Menu()
        
        # Short Term Status Item (5h)
        self.five_hour_item = Gtk.MenuItem(label="Loading usage (5h)...")
        self.five_hour_item.set_sensitive(False)
        menu.append(self.five_hour_item)
        
        # Long Term Status Item (Weekly)
        self.weekly_item = Gtk.MenuItem(label="Loading weekly usage...")
        self.weekly_item.set_sensitive(False)
        menu.append(self.weekly_item)
        
        # Separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # Reset Item (time until next 5h reset)
        self.reset_item = Gtk.MenuItem(label="Next reset: calculating...")
        self.reset_item.set_sensitive(False)
        menu.append(self.reset_item)
        
        # Separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # Manual refresh
        refresh_item = Gtk.MenuItem(label="🔄 Update now")
        refresh_item.connect("activate", self.manual_refresh)
        menu.append(refresh_item)
        
        # Open Claude settings
        settings_item = Gtk.MenuItem(label="⚙️ Open Claude Settings")
        settings_item.connect("activate", self.open_claude_settings)
        menu.append(settings_item)
        
        # Renew session (Automatic Login)
        login_item = Gtk.MenuItem(label="🔑 Renew Session (Login)")
        login_item.connect("activate", self.run_login)
        menu.append(login_item)
        
        # Separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # About
        about_item = Gtk.MenuItem(label="ℹ️ About")
        about_item.connect("activate", self.show_about)
        menu.append(about_item)
        
        # Quit
        quit_item = Gtk.MenuItem(label="❌ Quit")
        quit_item.connect("activate", self.quit)
        menu.append(quit_item)
        
        menu.show_all()
        return menu
    
    def update_label(self):
        """Updates the indicator text on the taskbar"""
        # We use 5h usage for the main icon as it is the most restrictive
        usage_pct = self.usage_data['five_hour']['usage']
        
        # Change icon color based on usage level
        if usage_pct >= 90:
            icon = "🔴"
        elif usage_pct >= 70:
            icon = "🟡"
        else:
            icon = "🟢"
        
        # Label shows the most critical or 5h usage by default
        label = f"Claude: {usage_pct}%"
        self.indicator.set_label(label, "100%")
        
        # Update menu items
        self.five_hour_item.set_label(f"{icon} Usage (5h): {usage_pct}%")
        
        w_usage = self.usage_data['weekly']['usage']
        w_icon = "🔴" if w_usage >= 90 else "🟡" if w_usage >= 70 else "🟢"
        self.weekly_item.set_label(f"{w_icon} Weekly Usage: {w_usage}%")
    
    def _fetch_usage_from_api(self) -> dict | None:
        """Fetch usage from claude.ai API using cookies. Returns data or None."""
        config_dir = Path.home() / ".config" / "claude-usage"
        cookie_file = config_dir / "cookies.txt"
        script_dir = Path(__file__).resolve().parent
        get_usage_script = script_dir / "get_usage.py"

        if not cookie_file.exists() or not get_usage_script.exists():
            return None

        # Determine which Python executable to use (venv or system)
        venv_python = config_dir / "venv" / "bin" / "python3"
        python_exe = str(venv_python) if venv_python.exists() else sys.executable

        try:
            result = subprocess.run(
                [python_exe, str(get_usage_script), "--quiet", "--raw"],
                capture_output=True,
                text=True,
                timeout=90,
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"error": "Error parsing API JSON"}
            else:
                stderr_msg = result.stderr.strip() if result.stderr else "Unknown error"
                # If the script returned a formatted JSON error, pass it
                if stderr_msg.startswith('{') and 'error' in stderr_msg:
                    try: return json.loads(stderr_msg)
                    except: pass
                return {"error": f"System error: {stderr_msg[:50]}..."}
        except subprocess.TimeoutExpired:
            return {"error": "Timeout connecting to Claude"}
        except Exception as e:
            return {"error": str(e)}

    def _parse_api_usage(self, data: dict) -> None:
        """Parse API response and update usage_data."""
        # Parse Five Hour Usage
        fh = data.get("five_hour")
        if fh:
            self.usage_data['five_hour']['usage'] = int(fh.get("utilization", 0))
            resets_at = fh.get("resets_at")
            if resets_at:
                try:
                    self.usage_data['five_hour']['reset'] = datetime.fromisoformat(
                        resets_at.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError): pass

        # Parse Weekly Usage
        wk = data.get("seven_day")
        if wk:
            self.usage_data['weekly']['usage'] = int(wk.get("utilization", 0))
            resets_at = wk.get("resets_at")
            if resets_at:
                try:
                    self.usage_data['weekly']['reset'] = datetime.fromisoformat(
                        resets_at.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError): pass

    def fetch_usage(self):
        """
        Fetches current Claude usage.
        Attempts automatic fetch with cookies; if fails, uses manual config.
        """
        try:
            config_file = Path.home() / ".config" / "claude-usage" / "config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Try automatic fetch with cookies
            api_data = self._fetch_usage_from_api()
            
            if api_data and "error" not in api_data:
                # CASE 1: Full Success
                self._parse_api_usage(api_data)
                # Persist in config for fallback
                config = {
                    "five_hour_usage": self.usage_data["five_hour"]["usage"],
                    "weekly_usage": self.usage_data["weekly"]["usage"],
                    "last_auto_update": datetime.now().isoformat(),
                }
                if self.usage_data["five_hour"]["reset"]:
                    config["five_hour_reset"] = self.usage_data["five_hour"]["reset"].isoformat()
                if self.usage_data["weekly"]["reset"]:
                    config["weekly_reset"] = self.usage_data["weekly"]["reset"].isoformat()
                
                with open(config_file, "w") as f:
                    json.dump(config, f, indent=2)
                
            elif config_file.exists():
                # CASE 2: API Error but we have stale data
                if api_data and "error" in api_data:
                    GLib.idle_add(self.show_error, api_data["error"])
                
                with open(config_file) as f:
                    config = json.load(f)

                self.usage_data["five_hour"]["usage"] = config.get("five_hour_usage", config.get("usage_percentage", 0))
                self.usage_data["weekly"]["usage"] = config.get("weekly_usage", 0)

                if config.get("five_hour_reset"):
                    try:
                        self.usage_data["five_hour"]["reset"] = datetime.fromisoformat(
                            config["five_hour_reset"].replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError): pass
                
                if config.get("weekly_reset"):
                    try:
                        self.usage_data["weekly"]["reset"] = datetime.fromisoformat(
                            config["weekly_reset"].replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError): pass
                
                # Mark in UI that these are stale data
                GLib.idle_add(lambda: self.five_hour_item.set_label(f"⚠️ Usage (5h): {self.usage_data['five_hour']['usage']}% (Offline)"))
            
            else:
                # CASE 3: API Error and nothing saved (First time)
                example_config = {
                    "note": "Configure cookies.txt for automatic updates",
                    "usage_percentage": 0,
                    "reset_hours": 5,
                }
                with open(config_file, "w") as f:
                    json.dump(example_config, f, indent=2)
                self.usage_data["five_hour"]["usage"] = 0
                self.usage_data["weekly"]["usage"] = 0

            GLib.idle_add(self.update_ui)

        except Exception as e:
            print(f"Error fetching usage: {e}")
            GLib.idle_add(self.show_error, str(e))
    
    def update_ui(self):
        """Updates the interface with fetched data"""
        self.update_label()
 
        # Update reset info for the nearest limit (usually 5h)
        reset_time = self.usage_data['five_hour']['reset']
        if reset_time:
            from datetime import timezone
            now = datetime.now(timezone.utc) if reset_time.tzinfo else datetime.now()
 
            if reset_time > now:
                diff = reset_time - now
                total_seconds = int(diff.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                self.reset_item.set_label(f"⏰ Reset (5h) in: {hours}h {minutes}m")
            else:
                self.reset_item.set_label("⏰ 5h Limit Reset")
        return False
        
    def show_error(self, message):
        """Displays an error in the menu"""
        self.five_hour_item.set_label(f"❌ Error: {message}")
        return False
    
    def auto_update(self):
        """Automatic update callback"""
        threading.Thread(target=self.fetch_usage, daemon=True).start()
        return True  # Continue calling this function
    
    def manual_refresh(self, widget):
        """Manual update by user"""
        self.five_hour_item.set_label("🔄 Updating...")
        threading.Thread(target=self.fetch_usage, daemon=True).start()
    
    def open_claude_settings(self, widget):
        """Opens Claude settings page"""
        subprocess.Popen(['xdg-open', 'https://claude.ai/settings/usage'])

    def run_login(self, widget):
        """Executes interactive login process"""
        def _login_thread():
            config_dir = Path.home() / ".config" / "claude-usage"
            get_usage_script = Path(__file__).resolve().parent / "get_usage.py"
            venv_python = config_dir / "venv" / "bin" / "python3"
            python_exe = str(venv_python) if venv_python.exists() else sys.executable

            GLib.idle_add(self.five_hour_item.set_label, "🔑 Starting login...")
            
            try:
                subprocess.run([python_exe, str(get_usage_script), "--login"], check=True)
                GLib.idle_add(self.five_hour_item.set_label, "✅ Login completed")
                # Update data immediately after login
                self.fetch_usage()
            except subprocess.CalledProcessError:
                GLib.idle_add(self.show_error, "Login failed or cancelled")

        threading.Thread(target=_login_thread, daemon=True).start()
    
    def show_about(self, widget):
        """Displays About window"""
        dialog = Gtk.MessageDialog(
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Claude Usage Indicator"
        )
        dialog.format_secondary_text(
            "Claude Usage Monitor for Ubuntu MATE\n\n"
            "Shows shared usage between claude.ai and Claude Code\n"
            "Limits reset approximately every 5 hours (Claude Pro)\n\n"
            "Configuration file:\n"
            "~/.config/claude-usage/config.json"
        )
        dialog.run()
        dialog.destroy()
    
    def quit(self, widget):
        """Exits the application"""
        Gtk.main_quit()

def main():
    indicator = ClaudeUsageIndicator()
    Gtk.main()

if __name__ == "__main__":
    main()
