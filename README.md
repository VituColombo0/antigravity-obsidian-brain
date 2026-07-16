# 🧠 Antigravity Obsidian Brain

> **Memória infinita para o Antigravity AI — toda conversa, projeto e decisão salva e sincronizada no Obsidian.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Obsidian](https://img.shields.io/badge/Obsidian-Compatible-purple.svg)](https://obsidian.md)

---

## 📖 O que é?

O **Antigravity Obsidian Brain** é uma ponte entre o [Antigravity AI](https://github.com/google-deepmind/antigravity) (assistente de codificação com IA) e o [Obsidian](https://obsidian.md) (app de notas em Markdown).

Ele transforma o Obsidian no **cérebro permanente** do Antigravity:

- 🔄 **Sincroniza automaticamente** todas as conversas, artefatos e projetos para o seu vault do Obsidian
- 🧠 **Dá memória infinita** ao Antigravity — ele lê suas notas do Obsidian antes de cada resposta
- 📝 **Bidirecional** — edite notas no Obsidian e o Antigravity aprende com elas
- 🔍 **Indexa tudo** — busca por palavra-chave, tags, links entre notas
- 🤖 **Zero configuração** — detecta automaticamente os diretórios do Antigravity

### Antes vs Depois

| Sem o Brain | Com o Brain |
|---|---|
| Antigravity esquece conversas passadas | Lembra de tudo que vocês já fizeram |
| Contexto perdido entre sessões | Contexto acumulado permanente |
| Sem forma de revisar decisões | Tudo navegável e pesquisável no Obsidian |
| Conhecimento isolado por conversa | Grafo de conhecimento interconectado |

---

## 🚀 Instalação Rápida

### Pré-requisitos
- Python 3.10+
- [Obsidian](https://obsidian.md) instalado
- Antigravity AI configurado (`~/.gemini/antigravity/`)

### 1. Clone o repositório

```bash
git clone https://github.com/SEU_USUARIO/antigravity-obsidian-brain.git
cd antigravity-obsidian-brain
```

### 2. Instale

```bash
# Linux / macOS
chmod +x install.sh && ./install.sh

# Windows
install.bat
```

### 3. Configure (opcional)

Edite `config.yaml` para ajustar caminhos e preferências:

```yaml
vault:
  path: "~/ObsidianVault/AntigravityBrain"  # Onde criar/usar o vault
  
sync:
  auto: true              # Sincronizar automaticamente
  interval_minutes: 5     # Intervalo entre syncs
  watch_mode: true        # Monitorar mudanças em tempo real
```

### 4. Primeira sincronização

```bash
python -m brain sync
```

### 5. Abra no Obsidian

Abra o Obsidian → "Open folder as vault" → Selecione a pasta do vault configurada.

---

## 📂 Estrutura do Vault

O Brain organiza seu vault assim:

```
AntigravityBrain/
├── 00_Atlas/
│   └── Index.md                    # 🗺️ Mapa de todo o vault
├── 01_Projects/
│   ├── Current_Projects.md         # 📋 Lista de projetos ativos
│   └── <nome_do_projeto>.md        # 📁 Uma nota por projeto
├── 02_Knowledge/
│   └── <topico>.md                 # 📚 Base de conhecimento técnico
├── 03_Context/
│   ├── Antigravity_Identity.md     # 🤖 Personalidade e regras
│   ├── User_Preferences.md         # ⭐ Preferências do usuário
│   └── Workspace_Guidelines.md     # 🏢 Regras do workspace
├── 04_Conversations/
│   ├── 2026-07/
│   │   ├── Refactoring_Luna.md     # 💬 Conversa parseada
│   │   └── ...
│   └── ...
├── 05_Artifacts/
│   └── <artefato>.md               # 📦 Documentos e análises criados
└── 99_Log/
    ├── Session_Logs.md             # 📅 Log de sessões
    └── Sync_History.md             # 🔄 Histórico de sincronizações
```

---

## 🛠️ Comandos

```bash
# Primeira sincronização completa
python -m brain sync

# Sincronização rápida (apenas novos)
python -m brain sync --incremental

# Modo daemon (roda em background, sincroniza automaticamente)
python -m brain watch

# Status do vault
python -m brain status

# Recriar índices
python -m brain reindex

# Exportar conversa específica
python -m brain export <conversation-id>
```

---

## 🔧 Como funciona

### Fluxo de Sincronização

```
┌─────────────────────┐         ┌──────────────────────┐
│   Antigravity AI    │         │    Obsidian Vault     │
│                     │         │                       │
│ brain/              │ ──sync──▶ 04_Conversations/    │
│   <id>/logs/        │         │   2026-07/chat.md     │
│   <id>/artifacts/   │ ──sync──▶ 05_Artifacts/        │
│                     │         │   analysis.md         │
│ conversations/      │         │                       │
│   <id>.pb           │         │ 00_Atlas/Index.md     │
│                     │         │ (auto-atualizado)     │
│ knowledge/          │ ──sync──▶ 02_Knowledge/        │
│   <ki>/artifacts/   │         │   topic.md            │
└─────────────────────┘         └──────────────────────┘
```

### Parsing Inteligente

O Brain não faz um dump cru dos dados. Ele:

1. **Parseia** os logs brutos (JSON) em Markdown limpo e legível
2. **Extrai** metadados (data, assunto, arquivos tocados, comandos rodados)
3. **Gera tags** automáticas (`#project/luna`, `#language/python`, `#action/git`)
4. **Cria wikilinks** entre notas relacionadas (`[[01_Projects/Luna]]`)
5. **Resume** conversas longas em resumos executivos

---

## 🤝 Contribuindo

1. Fork o repositório
2. Crie sua branch (`git checkout -b feature/minha-feature`)
3. Commit suas mudanças (`git commit -m 'feat: minha feature'`)
4. Push para a branch (`git push origin feature/minha-feature`)
5. Abra um Pull Request

---

## 📄 Licença

MIT — use como quiser. Veja [LICENSE](LICENSE) para detalhes.

---

## 💡 Inspiração

Este projeto nasceu da necessidade de dar **memória permanente** ao Antigravity. Sem ele, cada conversa é um universo isolado. Com ele, o Antigravity evolui a cada sessão, lembrando de seus projetos, preferências, erros passados e decisões de design.

> *"A memória é a mãe de toda sabedoria."* — Ésquilo
