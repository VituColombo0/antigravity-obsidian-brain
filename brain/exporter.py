"""
Exporter — Exporta dados parseados para o vault Obsidian.

Gerencia a estrutura do vault, escreve os arquivos Markdown,
mantém o índice (MOC) atualizado, e controla o estado de
sincronização para evitar reprocessamento.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path


logger = logging.getLogger("brain.exporter")


class ObsidianExporter:
    """
    Exporta dados do Antigravity para um vault Obsidian organizado.
    
    Estrutura:
        vault/
        ├── 00_Atlas/Index.md
        ├── 01_Projects/
        ├── 02_Knowledge/
        ├── 03_Context/
        ├── 04_Conversations/YYYY-MM/
        ├── 05_Artifacts/
        └── 99_Log/
    """

    def __init__(self, config: dict):
        self.vault_path = config["vault"]["path"]
        self.incremental = config["sync"].get("incremental", True)
        self.state_file = Path(config["antigravity"]["data_dir"]) / ".sync_state.json"
        self.synced_ids = self._load_sync_state()

    # ─── Estrutura do Vault ───────────────────────────────

    def initialize_vault(self):
        """Cria a estrutura de pastas do vault se não existir."""
        dirs = [
            self.vault_path,
            self.vault_path / "00_Atlas",
            self.vault_path / "01_Projects",
            self.vault_path / "02_Knowledge",
            self.vault_path / "03_Context",
            self.vault_path / "04_Conversations",
            self.vault_path / "05_Artifacts",
            self.vault_path / "99_Log",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Criar .obsidian config se não existir
        obsidian_dir = self.vault_path / ".obsidian"
        obsidian_dir.mkdir(exist_ok=True)

        app_json = obsidian_dir / "app.json"
        if not app_json.exists():
            app_json.write_text("{}", encoding="utf-8")

        appearance_json = obsidian_dir / "appearance.json"
        if not appearance_json.exists():
            appearance_json.write_text(
                json.dumps({"theme": "obsidian"}, indent=2),
                encoding="utf-8",
            )

        # Criar arquivos de contexto base se não existirem
        self._ensure_context_files()

        logger.info(f"Vault inicializado em {self.vault_path}")

    def _ensure_context_files(self):
        """Cria arquivos de contexto padrão se não existirem."""
        # Identidade do Antigravity
        identity_path = self.vault_path / "03_Context" / "Antigravity_Identity.md"
        if not identity_path.exists():
            identity_path.write_text(
                "# 🤖 Antigravity Identity\n\n"
                "Eu sou o **Antigravity**, seu assistente de codificação e IA.\n\n"
                "## 🎨 Estética e Filosofia\n"
                "- **Design Premium**: Interfaces vibrantes, modernas e com fator WOW.\n"
                "- **Abordagem Proativa**: Eu planejo, executo e verifico.\n"
                "- **Memória Persistente**: Com este Vault, aprendo cumulativamente.\n\n"
                "## 🤝 Relacionamento com o Usuário\n"
                "- Foco em **Pair Programming**.\n"
                "- Comunicações concisas e diretas.\n"
                "- Prioridade máxima à visão do usuário.\n",
                encoding="utf-8",
            )

        # Preferências do usuário
        prefs_path = self.vault_path / "03_Context" / "User_Preferences.md"
        if not prefs_path.exists():
            prefs_path.write_text(
                "# ⭐ Preferências do Usuário\n\n"
                "Gostos, hábitos e preferências detectados ao longo das conversas.\n\n"
                "---\n\n"
                "*(Este arquivo é atualizado automaticamente pelo Brain.)*\n",
                encoding="utf-8",
            )

        # Guidelines do Workspace
        guidelines_path = self.vault_path / "03_Context" / "Workspace_Guidelines.md"
        if not guidelines_path.exists():
            guidelines_path.write_text(
                "# 🏢 Workspace Guidelines\n\n"
                "## 📍 Localização Central\n"
                "Todos os projetos ativos residem em:\n"
                "`~/.gemini/antigravity/scratch/`\n\n"
                "## 🧠 Ciclo de Memória (Obsidian)\n"
                "Para cada novo projeto, o Antigravity deve:\n"
                "1. Criar uma nota em `01_Projects/`.\n"
                "2. Registrar o link do diretório de código.\n"
                "3. Manter status e decisões atualizados.\n",
                encoding="utf-8",
            )

    # ─── Exportação ───────────────────────────────────────

    def export_conversation(self, parsed_data: dict) -> Path | None:
        """
        Exporta uma conversa parseada para o vault.

        Args:
            parsed_data: Dict retornado por ConversationParser.parse_overview().

        Returns:
            Path do arquivo criado, ou None se falhar.
        """
        from brain.parser import ConversationParser

        conv_id = parsed_data["id"]

        # Checar se já foi sincronizado (modo incremental)
        if self.incremental and conv_id in self.synced_ids:
            logger.debug(f"Conversa {conv_id[:12]} já sincronizada, pulando.")
            return None

        # Determinar subpasta por mês
        if parsed_data["date"]:
            month_dir = parsed_data["date"].strftime("%Y-%m")
        else:
            month_dir = "sem-data"

        conv_dir = self.vault_path / "04_Conversations" / month_dir
        conv_dir.mkdir(parents=True, exist_ok=True)

        # Gerar nome de arquivo seguro
        safe_title = self._sanitize_filename(parsed_data["title"])
        file_name = f"{safe_title}_{conv_id[:8]}.md"
        file_path = conv_dir / file_name

        # Gerar e escrever Markdown
        parser = ConversationParser({"parser": {}, "tags": {}})
        markdown = parser.to_markdown(parsed_data)

        try:
            file_path.write_text(markdown, encoding="utf-8")
            self.synced_ids.add(conv_id)
            logger.info(f"  ✅ Conversa exportada: {file_path.name}")
            return file_path
        except Exception as e:
            logger.error(f"  ❌ Erro ao exportar conversa {conv_id[:12]}: {e}")
            return None

    def export_artifact(self, parsed_data: dict) -> Path | None:
        """
        Exporta um artefato parseado para o vault.

        Args:
            parsed_data: Dict retornado por ArtifactParser.parse_artifact().

        Returns:
            Path do arquivo criado, ou None se falhar.
        """
        from brain.parser import ArtifactParser

        # Gerar nome seguro
        safe_title = self._sanitize_filename(parsed_data["clean_title"])
        conv_short = parsed_data["conv_id"][:8]
        file_name = f"{safe_title}_{conv_short}.md"
        file_path = self.vault_path / "05_Artifacts" / file_name

        # Gerar Markdown
        parser = ArtifactParser({})
        markdown = parser.to_markdown(parsed_data)

        try:
            file_path.write_text(markdown, encoding="utf-8")
            logger.info(f"  ✅ Artefato exportado: {file_path.name}")
            return file_path
        except Exception as e:
            logger.error(f"  ❌ Erro ao exportar artefato: {e}")
            return None

    def export_knowledge_item(self, ki_data: dict) -> Path | None:
        """
        Exporta um Knowledge Item para o vault.

        Args:
            ki_data: Dict do scanner com metadata e artifacts.

        Returns:
            Path do arquivo criado.
        """
        metadata = ki_data.get("metadata", {})
        title = metadata.get("title", ki_data["id"])
        summary = metadata.get("summary", "")

        safe_title = self._sanitize_filename(title)
        file_path = self.vault_path / "02_Knowledge" / f"{safe_title}.md"

        parts = [
            f"---\n"
            f"title: \"{title}\"\n"
            f"type: knowledge\n"
            f"---\n\n"
            f"# 📚 {title}\n\n"
        ]

        if summary:
            parts.append(f"{summary}\n\n")

        # Incluir conteúdo dos artefatos do KI
        for art_path in ki_data.get("artifacts", []):
            if art_path.suffix == ".md":
                try:
                    content = art_path.read_text(encoding="utf-8")
                    parts.append(f"---\n\n{content}\n")
                except Exception:
                    pass

        try:
            file_path.write_text("".join(parts), encoding="utf-8")
            logger.info(f"  ✅ Knowledge exportado: {file_path.name}")
            return file_path
        except Exception as e:
            logger.error(f"  ❌ Erro ao exportar knowledge: {e}")
            return None

    # ─── Índice (MOC) ─────────────────────────────────────

    def rebuild_index(self):
        """
        Reconstrói o Index.md (Map of Content) com links para tudo.
        """
        parts = [
            "# 🗺️ Atlas: Antigravity Brain\n\n",
            f"*Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n\n",
            "## 📌 Navegação Rápida\n\n",
            "- [[03_Context/Antigravity_Identity|🤖 Quem sou eu]]\n",
            "- [[03_Context/User_Preferences|⭐ Preferências do Usuário]]\n",
            "- [[03_Context/Workspace_Guidelines|🏢 Regras do Workspace]]\n\n",
            "---\n\n",
        ]

        # Projetos
        projects_dir = self.vault_path / "01_Projects"
        project_files = sorted(projects_dir.glob("*.md"))
        if project_files:
            parts.append("## 🚀 Projetos\n\n")
            for pf in project_files:
                name = pf.stem.replace("_", " ")
                parts.append(f"- [[01_Projects/{pf.stem}|{name}]]\n")
            parts.append("\n")

        # Knowledge
        knowledge_dir = self.vault_path / "02_Knowledge"
        knowledge_files = sorted(knowledge_dir.glob("*.md"))
        if knowledge_files:
            parts.append("## 📚 Base de Conhecimento\n\n")
            for kf in knowledge_files:
                name = kf.stem.replace("_", " ")
                parts.append(f"- [[02_Knowledge/{kf.stem}|{name}]]\n")
            parts.append("\n")

        # Conversas recentes (últimas 20)
        conv_dir = self.vault_path / "04_Conversations"
        all_convs = sorted(conv_dir.rglob("*.md"), reverse=True)
        if all_convs:
            parts.append("## 💬 Conversas Recentes\n\n")
            for cf in all_convs[:20]:
                rel = cf.relative_to(self.vault_path)
                name = cf.stem.replace("_", " ")
                # Remover o hash do final
                if len(name) > 10:
                    name = re.sub(r"\s+[a-f0-9]{8}$", "", name)
                parts.append(f"- [[{rel.with_suffix('')}|{name}]]\n")

            if len(all_convs) > 20:
                parts.append(f"\n*...e mais {len(all_convs) - 20} conversas.*\n")
            parts.append("\n")

        # Artefatos recentes
        art_dir = self.vault_path / "05_Artifacts"
        all_arts = sorted(art_dir.glob("*.md"), reverse=True)
        if all_arts:
            parts.append("## 📦 Artefatos\n\n")
            for af in all_arts[:15]:
                name = af.stem.replace("_", " ")
                if len(name) > 10:
                    name = re.sub(r"\s+[a-f0-9]{8}$", "", name)
                parts.append(f"- [[05_Artifacts/{af.stem}|{name}]]\n")
            parts.append("\n")

        # Estatísticas
        parts.append("## 📊 Estatísticas\n\n")
        parts.append(f"| Métrica | Valor |\n")
        parts.append(f"|---------|-------|\n")
        parts.append(f"| Conversas | {len(all_convs)} |\n")
        parts.append(f"| Artefatos | {len(all_arts)} |\n")
        parts.append(f"| Projetos | {len(project_files)} |\n")
        parts.append(f"| Knowledge Items | {len(knowledge_files)} |\n")

        parts.append(
            "\n---\n"
            "> \"O conhecimento é a única ferramenta que se torna "
            "mais afiada quanto mais a usamos.\"\n"
        )

        index_path = self.vault_path / "00_Atlas" / "Index.md"
        index_path.write_text("".join(parts), encoding="utf-8")
        logger.info("📋 Índice (MOC) reconstruído.")

    # ─── Sync Log ─────────────────────────────────────────

    def log_sync(self, stats: dict):
        """Registra a sincronização no log do vault."""
        log_path = self.vault_path / "99_Log" / "Sync_History.md"

        if not log_path.exists():
            log_path.write_text(
                "# 🔄 Histórico de Sincronizações\n\n"
                "Registro automático de cada sync realizado.\n\n"
                "---\n\n",
                encoding="utf-8",
            )

        now = datetime.now()
        entry = (
            f"### {now.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            f"- Conversas sincronizadas: **{stats.get('conversations', 0)}**\n"
            f"- Artefatos sincronizados: **{stats.get('artifacts', 0)}**\n"
            f"- Knowledge items: **{stats.get('knowledge', 0)}**\n"
            f"- Modo: {'incremental' if self.incremental else 'completo'}\n\n"
            f"---\n\n"
        )

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

    # ─── Estado de Sync ───────────────────────────────────

    def _load_sync_state(self) -> set:
        """Carrega o estado de sincronização (IDs já processados)."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                return set(data.get("synced_ids", []))
            except (json.JSONDecodeError, Exception):
                pass
        return set()

    def save_sync_state(self):
        """Salva o estado de sincronização."""
        try:
            data = {
                "synced_ids": sorted(self.synced_ids),
                "last_sync": datetime.now().isoformat(),
                "total_synced": len(self.synced_ids),
            }
            self.state_file.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
            logger.debug(f"Estado de sync salvo: {len(self.synced_ids)} IDs")
        except Exception as e:
            logger.error(f"Erro ao salvar estado de sync: {e}")

    # ─── Utilitários ──────────────────────────────────────

    def _sanitize_filename(self, name: str) -> str:
        """Remove caracteres inválidos para nomes de arquivo."""
        # Remover emojis e caracteres especiais
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
        # Manter acentos mas remover outros unicode especiais
        safe = re.sub(r"[^\w\sàáâãéêíóôõúçÀÁÂÃÉÊÍÓÔÕÚÇ._-]", "", safe)
        safe = safe.strip(". ")
        # Substituir espaços por underscores
        safe = re.sub(r"\s+", "_", safe)
        # Limitar tamanho
        if len(safe) > 80:
            safe = safe[:80]
        return safe or "sem_titulo"
