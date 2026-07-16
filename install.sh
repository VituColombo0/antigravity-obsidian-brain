#!/usr/bin/env bash
# ============================================================
#  Antigravity Obsidian Brain — Instalação (Linux / macOS)
# ============================================================
set -e

echo ""
echo "  🧠 Antigravity Obsidian Brain — Instalador"
echo "  ============================================"
echo ""

# 1. Verificar Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 não encontrado. Instale: https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  ✅ Python $PYTHON_VERSION encontrado"

# 2. Criar virtualenv
if [ ! -d "venv" ]; then
    echo "  📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "  ✅ Ambiente virtual ativado"

# 3. Instalar dependências
echo "  📥 Instalando dependências..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 4. Copiar config se não existir
if [ ! -f "config.yaml" ]; then
    cp config.example.yaml config.yaml
    echo "  📋 config.yaml criado (edite se necessário)"
fi

# 5. Verificar Antigravity
AG_DIR="$HOME/.gemini/antigravity"
if [ -d "$AG_DIR" ]; then
    CONV_COUNT=$(find "$AG_DIR/brain" -name "overview.txt" 2>/dev/null | wc -l)
    echo "  ✅ Antigravity encontrado — $CONV_COUNT conversas disponíveis"
else
    echo "  ⚠️  Antigravity não encontrado em $AG_DIR"
    echo "     O Brain funcionará quando o Antigravity for instalado."
fi

echo ""
echo "  ✅ Instalação concluída!"
echo ""
echo "  Próximos passos:"
echo "    1. Edite config.yaml com o caminho do seu vault"
echo "    2. Execute: source venv/bin/activate"
echo "    3. Execute: python -m brain sync"
echo "    4. Abra o Obsidian e aponte para o vault criado"
echo ""
