# Calendar Monitor

A macOS menu bar application that automatically adds Google Meet links to calendar events and opens them when meetings are about to start.

![Menu Bar Icon](https://img.shields.io/badge/macOS-Ventura%2013%2B-blue)

## Features

- 🔄 **Automatic Link Generation** – Creates Google Meet links for events without video conferencing links
- ⏰ **Smart Notifications** – Opens meeting links when events are about to start (configurable threshold)
- 🚫 **Read‑Only Calendar Detection** – Skips holidays, birthdays, and subscription calendars to avoid errors
- 📅 **Menu Bar Integration** – Runs discreetly in the macOS menu bar with status updates
- 🔧 **Fully Configurable** – Adjust polling interval and "soon" threshold via `conf.toml`

## Requirements

- macOS Ventura 13 or later
- Python 3.11+ (for bundled app, Python is included)
- [calctl](https://github.com/yourusername/calctl) – macOS Calendar CLI tool
- Google Cloud Project with Calendar API enabled (for Google Meet generation)

## Installation

### Option 1: Run from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/calendar-monitor.git
   cd calendar-monitor
   ```

2. Install dependencies:
   ```bash
   pip install rumps google-api-python-client google-auth-oauthlib google-auth-httplib2 pyobjc tomli
   ```

3. Install `calctl`:
   ```bash
   pipx install calctl
   ```

4. Create `conf.toml` (see Configuration section).

5. Place your Google OAuth `credentials.json` in the project directory.

6. Run the monitor:
   ```bash
   python main.py
   ```

### Option 2: Use Pre‑built `.app` Bundle

1. Download `Calendar Monitor.app` from [Releases](https://github.com/yourusername/calendar-monitor/releases).
2. Move it to your `/Applications` folder.
3. **Grant Calendar permissions** when prompted (System Settings → Privacy & Security → Calendars).
4. Place `credentials.json` and `conf.toml` in `~/Library/Application Support/CalendarMonitor/` (or next to the `.app`).

## Configuration

Create a `conf.toml` file with the following content:

```toml
[calendar]
# Seconds between calendar checks
poll_interval = 30

[event]
# Minutes before event start to consider it "soon"
soon_threshold_minutes = 5
```

## Google Calendar API Setup

To generate Google Meet links, you need OAuth 2.0 credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select existing).
3. Enable the **Google Calendar API**.
4. Under **APIs & Services → Credentials**, create an **OAuth 2.0 Client ID**.
   - Application type: **Desktop app**.
5. Download the JSON file and rename it to `credentials.json`.
6. Place it in the same directory as the script or `.app`.

On first run, a browser window will open for you to authorize access. A `token.pickle` file will be created for future automatic authentication.

## Usage

### Running from Source

```bash
python main.py
```

The 📅 icon will appear in your menu bar. Click it to:

- View current status
- Trigger a manual calendar check
- Quit the application

### Building a Standalone `.app` with py2app

1. Ensure `py2app` is installed:
   ```bash
   pip install py2app
   ```

2. Run the build script:
   ```bash
   python setup.py py2app
   ```

3. The app will be created in `dist/Calendar Monitor.app`.

**Note:** Update the `CALCTL_PATH` variable in `setup.py` to point to your actual `calctl` binary location.

## How It Works

1. **Polling Loop** – Every `poll_interval` seconds, the app fetches upcoming events for the next 7 days using `calctl`.
2. **New Event Detection** – If an event hasn't been processed before, it checks for an existing video link.
3. **Link Generation** – If no link is found and the calendar is writable, it calls `generate_link.py` (which uses Google Calendar API) to create a Meet link.
4. **Event Update** – The link is saved back to the macOS Calendar event's location field.
5. **Soon Event Check** – For events starting within `soon_threshold_minutes`, the video link is opened automatically in your default browser.

## Permissions

The app requires access to your calendars. When first launched (or after a permissions reset), macOS will prompt:

> "Calendar Monitor" would like to access your calendars.

You must click **OK** for the app to function. You can manage this later in **System Settings → Privacy & Security → Calendars**.

## Troubleshooting

### "calctl: command not found"

Ensure `calctl` is installed and in your `PATH`. If using the bundled app, verify the path in `setup.py` is correct.

### "Calendar access denied"

- Reset permissions: `sudo tccutil reset Calendar`
- Manually add the app in **System Settings → Privacy & Security → Calendars**.

### "No video link found" but no link generated

- Check that `generate_link.py` is executable and has proper Google credentials.
- Run `python generate_link.py '{"title":"Test"}'` to test standalone.

### Events in local calendars are skipped

The app treats calendars containing "holidays", "birthdays", or "subscription" (case‑insensitive) as read‑only. If your local calendar has such a keyword in its name, rename it in the Calendar app.

## Project Structure

```
calendar-monitor/
├── main.py                 # Menu bar application
├── generate_link.py        # Google Meet link generator
├── setup.py                # py2app build configuration
├── conf.toml               # User configuration
├── credentials.json        # Google OAuth credentials 
└── README.md               # This file
```

## License

MIT License – see [LICENSE](LICENSE) file for details.

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## Acknowledgments

- [rumps](https://github.com/jaredks/rumps) – Ridiculously Uncomplicated macOS Python Statusbar apps
- [calctl](https://github.com/yourusername/calctl) – Command-line tool for macOS Calendar
- [py2app](https://py2app.readthedocs.io/) – Create standalone Mac applications from Python