#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  اجرای برنامه - Enterprise Organization Management Portal
# ═══════════════════════════════════════════════════════════

VENV_DIR=".venv"
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     راه‌اندازی پورتال سازمانی                        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check virtualenv
if [ ! -d "$VENV_DIR" ]; then
    echo "[خطا] محیط مجازی یافت نشد. ابتدا ./install.sh را اجرا کنید."
    exit 1
fi

# Activate
source "$VENV_DIR/bin/activate"

# Check db
if [ ! -f "db.sqlite3" ]; then
    echo "[!] پایگاه داده وجود ندارد. اجرای migrate..."
    python manage.py migrate --quiet
    python manage.py seed_data
fi

# Open browser after 2 seconds (optional)
URL="http://${HOST}:${PORT}/org/"
if command -v xdg-open &>/dev/null; then
    (sleep 2 && xdg-open "$URL") &
elif command -v open &>/dev/null; then
    (sleep 2 && open "$URL") &
fi

echo " آدرس برنامه:    $URL"
echo " پنل ادمین:      http://${HOST}:${PORT}/admin/"
echo " برای توقف:      Ctrl + C"
echo "──────────────────────────────────────────────────────"
echo ""

# Run server
exec python manage.py runserver "${HOST}:${PORT}"
