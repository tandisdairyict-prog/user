#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  نصب پیش‌نیازها - Enterprise Organization Management Portal
# ═══════════════════════════════════════════════════════════

set -e

PYTHON=${PYTHON:-python3}
VENV_DIR=".venv"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     نصب پورتال سازمانی - Enterprise Portal          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v $PYTHON &>/dev/null; then
    echo "[خطا] Python3 یافت نشد. لطفاً Python 3.10+ نصب کنید."
    exit 1
fi

PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[✓] Python $PY_VER یافت شد"

# Create virtualenv
if [ ! -d "$VENV_DIR" ]; then
    echo "[...] ایجاد محیط مجازی Python در $VENV_DIR ..."
    $PYTHON -m venv "$VENV_DIR"
    echo "[✓] محیط مجازی ایجاد شد"
else
    echo "[✓] محیط مجازی موجود است"
fi

# Activate
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "[...] به‌روزرسانی pip ..."
pip install --upgrade pip --quiet

# Install requirements
echo "[...] نصب پکیج‌های Python ..."
pip install Django "Pillow>=10.0" --quiet
echo "[✓] پکیج‌ها نصب شدند"

# Create .env if not exists
if [ ! -f ".env" ]; then
    cat > .env <<'EOF'
DEBUG=True
SECRET_KEY=django-insecure-change-this-in-production
ALLOWED_HOSTS=*
DATABASE_URL=sqlite:///db.sqlite3
EOF
    echo "[✓] فایل .env ایجاد شد"
fi

# Run migrations
echo "[...] اجرای migration های پایگاه داده ..."
python manage.py migrate --run-syncdb 2>&1 | grep -E "OK|error|Error" || true
echo "[✓] پایگاه داده آماده شد"

# Seed demo data
if python manage.py shell -c "from org_chart.models import Company; exit(0 if Company.objects.exists() else 1)" 2>/dev/null; then
    echo "[✓] داده‌های نمونه قبلاً بارگذاری شده‌اند"
else
    echo "[...] بارگذاری داده‌های نمونه ..."
    python manage.py seed_data
fi

# Create superuser if not exists
echo ""
echo "──────────────────────────────────────────────────────"
echo " ایجاد حساب مدیر سیستم (اختیاری)"
echo "──────────────────────────────────────────────────────"
if python manage.py shell -c "from django.contrib.auth.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null; then
    echo "[✓] حساب مدیر از قبل موجود است"
else
    echo " برای ایجاد حساب مدیر پنل ادمین، اطلاعات زیر را وارد کنید:"
    echo " (برای رد کردن این مرحله Ctrl+C بزنید)"
    python manage.py createsuperuser --noinput \
        --username admin \
        --email admin@portal.local 2>/dev/null && \
        python manage.py shell -c "
from django.contrib.auth.models import User
u = User.objects.get(username='admin')
u.set_password('admin1234')
u.save()
print('[✓] حساب مدیر ایجاد شد: admin / admin1234')
" || echo "[✓] ادامه بدون ایجاد مدیر"
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ نصب با موفقیت انجام شد!                         ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  برای اجرای برنامه:  ./run.sh                       ║"
echo "║  آدرس:               http://127.0.0.1:8000/org/     ║"
echo "║  پنل ادمین:          http://127.0.0.1:8000/admin/   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
