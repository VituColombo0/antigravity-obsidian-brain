# Antigravity Obsidian Brain

Ponte de sincronização bidirecional entre o ambiente do assistente Antigravity AI e vaults locais do Obsidian, viabilizando persistência estruturada de conversas, artefatos técnicos, histórico de decisões e grafos de conhecimento.

[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Target: Obsidian](https://img.shields.io/badge/Target-Obsidian%20Vault-purple.svg)](https://obsidian.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform: Linux / macOS / Windows](https://img.shields.io/badge/Platform-Cross--Platform-lightgrey.svg)](https://github.com/VituColombo0/antigravity-obsidian-brain)

---

## Visão Geral

O **Antigravity Obsidian Brain** atua como uma camada persistente de memória para o Antigravity AI. Em sessões padrão de desenvolvimento com agentes de IA, históricos de decisões e análises complexas de código podem se dispersar entre conversas encerradas. Esta ferramenta estrutura esses dados continuamente no formato nativo do Obsidian, gerando retroalimentação contextual para novas interações.

### Capacidades Centrais

- **Sincronização Contínua e Incremental:** Monitora logs de conversas (`transcript.jsonl`) e artefatos gerados pelo agente, espelhando alterações no vault em tempo real.
- **Parsing Estruturado com Frontmatter:** Converte saídas brutas em notas Markdown limpas, enriquecidas com metadados YAML (data, modelo, tags de projeto, linguagens e símbolos modificados).
- **Indexação por Wikilinks e Tags:** Estabelece links automáticos entre tarefas relacionadas (`[[01_Projects/MeuProjeto]]`), gerando um grafo navegável de conhecimento acumulado.
- **Detecção Automática de Diretórios:** Localiza dinamicamente as instalações locais do Antigravity AI tanto em sistemas baseados em Unix (`~/.gemini/antigravity-ide`) quanto em Windows.

---

## Arquitetura de Sincronização

```
┌─────────────────────────────────┐               ┌─────────────────────────────────┐
│         Antigravity AI          │               │         Obsidian Vault          │
│                                 │               │                                 │
│  brain/<conv-id>/logs/          │ ───(Sync)───▶ │  04_Conversations/<ano-mes>/    │
│    transcript.jsonl             │               │    chat_resumo.md               │
│                                 │               │                                 │
│  brain/<conv-id>/artifacts/     │ ───(Sync)───▶ │  05_Artifacts/                  │
│    analysis.md, report.md       │               │    documentos_e_planos.md       │
│                                 │               │                                 │
│  knowledge/<ki-id>/             │ ───(Sync)───▶ │  02_Knowledge/                  │
│    metadata.json & artifacts    │               │    base_tecnica.md              │
│                                 │               │                                 │
│                                 │ ──(Reindex)─▶ │  00_Atlas/Index.md              │
│                                 │               │    MOC (Map of Content)         │
└─────────────────────────────────┘               └─────────────────────────────────┘
```

---

## Estrutura do Vault Gerado

O vault é particionado segundo a metodologia PARA/Zettelkasten adaptada para desenvolvimento de software:

```text
AntigravityBrain/
├── 00_Atlas/
│   └── Index.md                  # Mapa central de conteúdo (MOC) e índices gerais
├── 01_Projects/
│   ├── Current_Projects.md       # Relação de repositórios e iniciativas ativas
│   └── <nome_do_projeto>.md      # Registro individual por projeto
├── 02_Knowledge/
│   └── <topico>.md               # Itens de conhecimento técnico e padrões reutilizáveis
├── 03_Context/
│   ├── Antigravity_Identity.md   # Definições de persona, regras e diretrizes de prompt
│   ├── User_Preferences.md       # Diretrizes de estilo do usuário e convenções de código
│   └── Workspace_Guidelines.md   # Políticas e restrições de ambiente local
├── 04_Conversations/
│   └── YYYY-MM/
│       └── <topico_da_sessao>.md # Transcrição sintética das conversas e prompts
├── 05_Artifacts/
│   └── <arquivo_de_saida>.md     # Planos de implementação, relatórios e diagramas
└── 99_Log/
    ├── Session_Logs.md           # Linha do tempo das interações
    └── Sync_History.md           # Registro de auditoria do daemon de sincronização
```

---

## Instalação e Configuração

### Pré-requisitos
- Python 3.10 ou superior
- [Obsidian](https://obsidian.md) instalado
- Antigravity AI configurado

### 1. Clonagem e Configuração do Ambiente

```bash
git clone https://github.com/VituColombo0/antigravity-obsidian-brain.git
cd antigravity-obsidian-brain
```

### 2. Instalação Automática

**Linux / macOS:**
```bash
chmod +x install.sh
./install.sh
```

**Windows:**
```cmd
install.bat
```

### 3. Configuração de Parâmetros (`config.yaml`)

Se necessário, ajuste os diretórios e políticas de sincronização:

```yaml
vault:
  path: "~/ObsidianVault/AntigravityBrain"  # Caminho de destino do vault
  create_if_missing: true

antigravity:
  app_data_dir: "~/.gemini/antigravity-ide" # Diretório base de telemetria

sync:
  auto: true
  interval_minutes: 5
  incremental_only: true
  watch_mode: true
```

---

## Linha de Comando (CLI)

O módulo oferece interface CLI para execução manual, diagnósticos e automações:

```bash
# Executa a sincronização completa inicial
python -m brain sync

# Executa sincronização incremental (apenas sessões novas ou alteradas)
python -m brain sync --incremental

# Inicia o daemon contínuo com monitoramento de filesystem (watch mode)
python -m brain watch

# Exibe o status da conexão, quantidade de notas e integridade do vault
python -m brain status

# Reconstrói os índices gerais e mapas de conteúdo (00_Atlas/Index.md)
python -m brain reindex

# Exporta uma conversa específica a partir de seu Conversation ID
python -m brain export <conversation-id>
```

---

## Operação em Segundo Plano (Systemd no Linux)

Para manter o serviço em execução contínua no Linux como serviço de usuário:

```ini
# ~/.config/systemd/user/antigravity-brain.service
[Unit]
Description=Antigravity Obsidian Brain Sync Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/antigravity-obsidian-brain
ExecStart=/usr/bin/python3 -m brain watch
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

Ativação do serviço:
```bash
systemctl --user daemon-reload
systemctl --user enable --now antigravity-brain.service
```

---

## Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE) para mais informações.
