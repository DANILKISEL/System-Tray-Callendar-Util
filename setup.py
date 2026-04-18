# setup.py
from setuptools import setup
import os

# Path to calctl binary
CALCTL_PATH = '/Users/dkisel/.local/bin/calctl'  # Update if needed

APP = ['main.py']
DATA_FILES = [
    ('', ['conf.toml']),
    ('', ['generate_link.py']),
    ('', [CALCTL_PATH]),   # Copy calctl into Resources root
]
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'rumps',
        'googleapiclient',
        'google_auth_oauthlib',
        'google_auth_httplib2',
        'objc',
        'tomllib',
    ],
    'plist': {
        'LSUIElement': True,
        'CFBundleName': 'Calendar Monitor',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleIdentifier': 'com.dkisel.calendarmonitor',
        'NSAppleEventsUsageDescription': 'Calendar Monitor needs access to your calendars.',
        'NSCalendarsUsageDescription': 'Calendar Monitor needs access to your calendars.',
    },
    'includes': [
        'Foundation',
        'EventKit',
        'objc',
        'Cocoa',  # instead of pyobjc_framework_Cocoa
        'EventKit',
        'colorsys',
        'argparse',
        'textwrap',
        'shlex'
    ],
}

setup(
    name='CalendarMonitor',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)