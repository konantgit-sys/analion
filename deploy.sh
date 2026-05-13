#!/bin/bash
# Deploy Analion to GitHub
# Usage: GITHUB_TOKEN=ghp_xxx ./deploy.sh [commit_message]

set -e

TOKEN="${GITHUB_TOKEN:-}"
MSG="${1:-Auto-deploy: Analion v3.0 — Multi-Provider + Billing}"

if [ -z "$TOKEN" ]; then
    echo "❌ Нет GITHUB_TOKEN. Укажи токен:"
    echo "   GITHUB_TOKEN=ghp_xxx ./deploy.sh"
    exit 1
fi

REPO="https://konantgit-sys:${TOKEN}@github.com/konantgit-sys/analion.git"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

echo "📦 Клонирую репозиторий..."
git clone --depth=1 "$REPO" "$TMPDIR/repo" 2>/dev/null

echo "📋 Копирую файлы проекта..."
# Основные файлы
cp -f README.md README_EN.md CHANGELOG.md ROADMAP.md ARCHITECTURE.md requirements.txt start.sh port.txt "$TMPDIR/repo/" 2>/dev/null || true
cp -f .env.example "$TMPDIR/repo/" 2>/dev/null || true

# Директории
for dir in engine runner selector builder data docs; do
    [ -d "$dir" ] && rsync -a --delete "$dir/" "$TMPDIR/repo/$dir/" --exclude='__pycache__' --exclude='*.db'
done

# Создаём .gitkeep в docs если пусто
[ ! -f "$TMPDIR/repo/docs/.gitkeep" ] && touch "$TMPDIR/repo/docs/.gitkeep"

cd "$TMPDIR/repo"

# .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.db
.env
backend.log
server.log
*.log
EOF

git add -A
git commit -m "$MSG" 2>/dev/null || echo "⚠️  Нет изменений для коммита"
git push origin main 2>/dev/null || git push origin master 2>/dev/null

echo ""
echo "✅ Деплой завершён!"
echo "   https://github.com/konantgit-sys/analion"
