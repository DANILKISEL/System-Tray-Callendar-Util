#!/usr/bin/env python3
"""
macOS Calendar Monitor - Menu Bar Edition

Handles JSON output from calctl (both calendars and events).
"""

import json
import shutil
import subprocess
import threading
import time
import webbrowser
import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path

import rumps

try:
    import tomllib
except ImportError:
    import tomli as tomllib


# ================================================
# Resource Path Handling (for py2app bundle)
# ================================================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def find_calctl_path():
    if getattr(sys, 'frozen', False):
        path = os.path.join(os.path.dirname(sys.executable), '..', 'Resources', 'calctl')
        if os.path.exists(path):
            return path
        raise FileNotFoundError(f"Bundled calctl not found at {path}")
    else:
        path = shutil.which('calctl')
        if path:
            return path
        home = Path.home()
        common = [
            home / '.local' / 'bin' / 'calctl',
            Path('/opt/homebrew/bin/calctl'),
            Path('/usr/local/bin/calctl'),
        ]
        for p in common:
            if p.exists():
                return str(p)
        raise FileNotFoundError("calctl not found. Install with 'pipx install calctl'")


def get_generate_link_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), '..', 'Resources', 'generate_link.py')
    else:
        return './generate_link.py'


CALCTL_PATH = find_calctl_path()
GENERATE_LINK_PATH = get_generate_link_path()

if not os.access(CALCTL_PATH, os.X_OK):
    os.chmod(CALCTL_PATH, 0o755)

print(f"Using calctl at: {CALCTL_PATH}")
print(f"Using generate_link at: {GENERATE_LINK_PATH}")


# ================================================
# Configuration
# ================================================
def load_config(config_path="conf.toml"):
    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        config.setdefault("calendar", {})
        config.setdefault("event", {})
        config["calendar"].setdefault("poll_interval", 30)
        config["event"].setdefault("soon_threshold_minutes", 5)
        return config
    except FileNotFoundError:
        rumps.alert(title="Config Error", message=f"'{config_path}' not found.")
        raise SystemExit
    except Exception as e:
        rumps.alert(title="Config Error", message=str(e))
        raise SystemExit


# ================================================
# Calendar Interaction
# ================================================
def parse_calctl_list_plain(text):
    """
    Fallback parser for plain text output from 'calctl list'.
    Example lines:
        2026-04-18 20:00–21:00  Event Title  [Calendar Name]  🔁 RRULE:...
    """
    events = []
    lines = text.strip().splitlines()

    pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2})\s+'
        r'(?:(\d{2}:\d{2})–(\d{2}:\d{2})|\(all day\))\s+'
        r'(.+?)\s+'
        r'\[(.+?)\]'
        r'(?:\s+🔁\s+.*)?$'
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if not match:
            continue

        date_str = match.group(1)
        start_time_str = match.group(2)
        end_time_str = match.group(3)
        title = match.group(4).strip()
        calendar = match.group(5).strip()

        if start_time_str and end_time_str:
            start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()
        else:
            start_dt = datetime.strptime(date_str, "%Y-%m-%d")
            end_dt = start_dt + timedelta(days=1)
            start_iso = start_dt.date().isoformat()
            end_iso = end_dt.date().isoformat()

        event_id = f"{title}-{date_str}-{calendar}".replace(" ", "_")

        events.append({
            'id': event_id,
            'title': title,
            'startDate': start_iso,
            'endDate': end_iso,
            'calendar': calendar,
            'location': '',
            'notes': '',
            'url': '',
        })

    return events


def get_upcoming_events():
    """Fetch upcoming events from the next 7 days using calctl."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        result = subprocess.run(
            [CALCTL_PATH, "list", "--from", today, "--to", next_week],
            capture_output=True,
            encoding='utf-8',
            check=True,
            timeout=10
        )
        output = result.stdout.strip()
        if not output:
            return []
        # Try JSON first (bundled calctl outputs JSON automatically when stdout is captured)
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return parse_calctl_list_plain(output)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching events: {e.stderr}")
        return []
    except Exception as e:
        print(f"Unexpected error in get_upcoming_events: {e}")
        return []


def update_event_video_link(event_id, video_link):
    """Update an event's location with the video link."""
    try:
        subprocess.run(
            [CALCTL_PATH, "edit", event_id, "--location", video_link],
            check=True,
            capture_output=True,
            encoding='utf-8',
            timeout=10
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error updating event {event_id}: {e.stderr}")
        return False


def extract_video_link_from_event(event):
    """Look for a video conferencing link in event details."""
    video_domains = ["zoom.us", "meet.google.com", "teams.microsoft.com", "webex.com"]
    fields = [event.get("location", ""), event.get("notes", ""), event.get("url", "")]
    for field in fields:
        if not field:
            continue
        for domain in video_domains:
            if domain in field.lower():
                words = field.split()
                for word in words:
                    if domain in word:
                        if word.startswith(("http://", "https://")):
                            return word
                        return f"https://{word}"
    return None


# ================================================
# Menu Bar App
# ================================================
class CalendarMonitorApp(rumps.App):
    def __init__(self):
        super(CalendarMonitorApp, self).__init__(
            name="📅 Calendar Monitor",
            title="📅",
            quit_button="Quit"
        )
        self.config = load_config()
        self.poll_interval = self.config["calendar"]["poll_interval"]
        self.processed_event_ids = set()
        self.running = True
        self.writable_calendars_cache = None

        self.status_item = rumps.MenuItem(title="Status: Running")
        self.menu.add(self.status_item)
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Check Now", callback=self.manual_check))
        self.menu.add(rumps.separator)

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        rumps.notification(
            title="Calendar Monitor Started",
            subtitle="",
            message=f"Polling every {self.poll_interval} seconds.",
            sound=False
        )

    def update_status(self, message):
        self.status_item.title = f"Status: {message}"

    @rumps.clicked("Check Now")
    def manual_check(self, _):
        self.update_status("Manual check...")
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        events = get_upcoming_events()
        if events:
            for event in events:
                event_id = event.get("id")
                if event_id and event_id not in self.processed_event_ids:
                    self.processed_event_ids.add(event_id)
                    self.process_event_for_video_link(event)
            self.check_for_soon_events(events)
        else:
            print("No events or error.")

    def _get_writable_calendar_names(self):
        """Fetch a set of calendar names that are likely writable.
        Parses JSON output from 'calctl calendars'."""
        if self.writable_calendars_cache is not None:
            return self.writable_calendars_cache

        writable = set()
        try:
            result = subprocess.run(
                [CALCTL_PATH, "calendars"],
                capture_output=True,
                encoding='utf-8',
                timeout=5
            )
            output = result.stdout.strip()
            if not output:
                return writable

            # Try JSON first (calctl outputs JSON when stdout is captured)
            try:
                calendars = json.loads(output)
                for cal in calendars:
                    cal_type = cal.get("type", "").lower()
                    cal_name = cal.get("title") or cal.get("name", "")
                    # Skip subscription and birthday calendars
                    if "subscription" in cal_type or "birthday" in cal_type:
                        continue
                    if any(kw in cal_name.lower() for kw in ["holidays", "birthdays"]):
                        continue
                    if cal_name:
                        writable.add(cal_name)
            except json.JSONDecodeError:
                # Fallback: plain text (unlikely for calctl calendars)
                lines = output.splitlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    lower = line.lower()
                    if any(kw in lower for kw in ["holidays", "birthdays", "subscription"]):
                        continue
                    writable.add(line)
        except Exception as e:
            print(f"Error fetching calendars: {e}")

        self.writable_calendars_cache = writable
        print(f"Writable calendars: {writable}")
        return writable

    def process_event_for_video_link(self, event):
        event_id = event.get("id")
        event_title = event.get("title", "Untitled")
        calendar_name = event.get("calendar", "")

        # Skip if calendar is known to be read‑only
        writable_calendars = self._get_writable_calendar_names()
        if calendar_name and calendar_name not in writable_calendars:
            print(f"Skipping read‑only calendar event: {event_title} (calendar: {calendar_name})")
            self.update_status(f"Skipped: {event_title[:20]}")
            return

        # Check for existing video link
        existing_link = extract_video_link_from_event(event)
        if existing_link:
            return

        print(f"No video link found for event: {event_title}")
        self.update_status(f"Generating link for: {event_title[:20]}...")

        event_json = json.dumps(event)
        try:
            result = subprocess.run(
                [sys.executable, GENERATE_LINK_PATH, event_json],
                capture_output=True,
                encoding='utf-8',
                check=True,
                timeout=30
            )
            video_link = result.stdout.strip()

            if video_link:
                print(f"Generated video link: {video_link}")
                if update_event_video_link(event_id, video_link):
                    print(f"Successfully updated event '{event_title}'")
                    self.update_status(f"Link added: {event_title[:20]}")
                else:
                    print(f"Failed to update event '{event_title}'.")
                    self.update_status("Update failed")
            else:
                print("generate_link.py returned no output.")
                self.update_status("No link generated")

        except subprocess.CalledProcessError as e:
            print(f"Error running generate_link.py: {e.stderr}")
            self.update_status("generate_link error")
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.update_status("Error")

    def check_for_soon_events(self, events):
        soon_threshold = self.config["event"]["soon_threshold_minutes"]
        now = datetime.now()

        for event in events:
            # Support both JSON (start) and plain fallback (startDate)
            start_str = event.get("start") or event.get("startDate")
            if not start_str:
                continue
            try:
                if 'T' in start_str:
                    start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                else:
                    start_time = datetime.strptime(start_str, "%Y-%m-%d")
            except ValueError:
                continue

            time_until = (start_time - now).total_seconds() / 60
            if 0 <= time_until <= soon_threshold:
                video_link = extract_video_link_from_event(event)
                if video_link:
                    title = event.get("title", "Event")
                    rumps.notification(
                        title="Meeting Starting Soon",
                        subtitle=title,
                        message=f"Opening {video_link.split('/')[2]}...",
                        sound=True
                    )
                    webbrowser.open(video_link)
                    self.update_status(f"Opened link for {title[:20]}")
                    return True
        return False

    def monitor_loop(self):
        while self.running:
            self._do_check()
            for _ in range(self.poll_interval):
                if not self.running:
                    break
                time.sleep(1)
        print("Monitor loop stopped.")

    def quit_application(self):
        self.running = False
        rumps.quit_application()


if __name__ == "__main__":
    CalendarMonitorApp().run()