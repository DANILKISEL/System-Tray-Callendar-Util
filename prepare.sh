#!/bin/bash

set -e  # Exit on error

echo "=============================================="
echo " Calendar Monitor – Dependency Installer"
echo "=============================================="
echo ""

# ----------------------------------------
# 1. Install Python 3.10 (if not present)
# ----------------------------------------
echo "🔍 Checking Python 3.10..."
if command -v python3.10 &> /dev/null; then
    echo "✅ Python 3.10 is already installed: $(python3.10 --version)"
else
    echo "📥 Downloading Python 3.10 from python.org..."
    PYTHON_PKG_URL="https://www.python.org/ftp/python/3.10.11/python-3.10.11-macos11.pkg"
    PYTHON_PKG="/tmp/python-3.10.11.pkg"
    curl -L -o "$PYTHON_PKG" "$PYTHON_PKG_URL"

    echo "📦 Installing Python 3.10 (requires administrator password)..."
    sudo installer -pkg "$PYTHON_PKG" -target /
    rm -f "$PYTHON_PKG"
    echo "✅ Python 3.10 installed."
fi

# ----------------------------------------
# 2. Ensure pip is available for Python 3.10
# ----------------------------------------
echo ""
echo "🔍 Checking pip for Python 3.10..."
if ! python3.10 -m pip --version &> /dev/null; then
    echo "📥 Installing pip..."
    python3.10 -m ensurepip --upgrade
fi
echo "✅ pip ready: $(python3.10 -m pip --version)"

# ----------------------------------------
# 3. Install pipx using Python 3.10
# ----------------------------------------
echo ""
echo "📦 Installing pipx..."
python3.10 -m pip install --user pipx
# Add pipx to PATH for this session
export PATH="$HOME/.local/bin:$PATH"
# Ensure pipx path is in shell config for future sessions
if ! grep -q '\.local/bin' ~/.zshrc 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
fi
echo "✅ pipx installed."

# ----------------------------------------
# 4. Install calctl using pipx
# ----------------------------------------
echo ""
echo "📦 Installing calctl via pipx..."
pipx install calctl
echo "✅ calctl installed: $(which calctl)"

# ----------------------------------------
# 5. Install Python packages for the project
# ----------------------------------------
echo ""
echo "📦 Installing required Python packages..."
python3.10 -m pip install --user \
    rumps \
    google-api-python-client \
    google-auth-oauthlib \
    google-auth-httplib2 \
    pyobjc \
    tomli

echo "✅ All Python packages installed."

# ----------------------------------------
# 6. Verify Google credentials reminder
# ----------------------------------------
echo ""
echo "=============================================="
echo " ✅ All dependencies installed successfully!"
echo "=============================================="
echo ""
echo "📋 Installed versions:"
echo "   Python:  $(python3.10 --version)"
echo "   pip:     $(python3.10 -m pip --version)"
echo "   pipx:    $(pipx --version)"
echo "   calctl:  $(calctl --version 2>/dev/null || echo 'installed')"
echo ""
echo "📌 Next steps:"
echo "   1. Ensure 'credentials.json' (Google OAuth) is present in the project folder."
echo "   2. Create 'conf.toml' with your desired settings."
echo "   3. Run the monitor: python3.10 main.py"
echo ""
echo "🔐 IMPORTANT: On first run, grant Calendar access when prompted."
echo ""