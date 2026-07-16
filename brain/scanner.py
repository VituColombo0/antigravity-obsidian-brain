"""
Scanner — Descobre e inventaria dados do Antigravity.

Varre os diretórios do Antigravity (brain/, conversations/, knowledge/)
e cataloga o que está disponível para sincronizar.
"""

import json
import logging
from datetime import datetime
from pathlib import Path


logger = logging.getLogger("brain.scanner")


class AntigravityScanner:
    """
    Escaneia os diretórios internos do Antigravity e retorna
    um inventário de tudo que pode ser sincronizado.
    """

    def __init__(self, config: dict):
        self.ag_dir = config["antigravity"]["data_dir"]
        self.brain_dir = config["antigravity"]["brain_dir"]
        self.conversations_dir = config["antigravity"]["conversations_dir"]
        self.knowledge_dir = config["antigravity"]["knowledge_dir"]

    def scan_all(self) -> dict:
        """
        Escaneia todos os dados do Antigravity.

        Returns:
            Dict com listas de conversas, artefatos e knowledge items.
        """
        logger.info(f"Escaneando dados do Antigravity em {self.ag_dir}...")

        result = {
            "conversations": self.scan_conversations(),
            "artifacts": self.scan_artifacts(),
            "knowledge_items": self.scan_knowledge(),
            "scan_time": datetime.now().isoformat(),
        }

        total = (
            len(result["conversations"])
            + len(result["artifacts"])
            + len(result["knowledge_items"])
        )
        logger.info(
            f"Scan completo: {len(result['conversations'])} conversas, "
            f"{len(result['artifacts'])} artefatos, "
            f"{len(result['knowledge_items'])} knowledge items "
            f"({total} itens total)"
        )

        return result

    def scan_conversations(self) -> list[dict]:
        """
        Encontra todas as conversas com overview.txt.

        Returns:
            Lista de dicts com id, overview_path, date, etc.
        """
        conversations = []

        if not self.brain_dir.exists():
            logger.warning(f"Diretório brain/ não encontrado: {self.brain_dir}")
            return conversations

        for conv_dir in sorted(self.brain_dir.iterdir()):
            if not conv_dir.is_dir():
                continue

            # Ignorar diretórios especiais
            if conv_dir.name in ("tempmediaStorage",):
                continue

            overview_path = conv_dir / ".system_generated" / "logs" / "overview.txt"
            if not overview_path.exists():
                continue

            # Extrair data da primeira entrada do overview
            date = self._extract_date(overview_path)

            conversations.append({
                "id": conv_dir.name,
                "overview_path": overview_path,
                "date": date,
                "size_bytes": overview_path.stat().st_size,
            })

        logger.debug(f"Encontradas {len(conversations)} conversas com overview.txt")
        return conversations

    def scan_artifacts(self) -> list[dict]:
        """
        Encontra todos os artefatos .md nas pastas de conversas.

        Returns:
            Lista de dicts com path, conv_id, name, etc.
        """
        artifacts = []

        if not self.brain_dir.exists():
            return artifacts

        for conv_dir in sorted(self.brain_dir.iterdir()):
            if not conv_dir.is_dir():
                continue

            artifacts_dir = conv_dir / "artifacts"
            if not artifacts_dir.exists():
                continue

            for art_file in sorted(artifacts_dir.iterdir()):
                # Apenas arquivos .md (ignorar metadata.json e .resolved)
                if not art_file.is_file() or art_file.suffix != ".md":
                    continue

                artifacts.append({
                    "path": art_file,
                    "conv_id": conv_dir.name,
                    "name": art_file.stem,
                    "size_bytes": art_file.stat().st_size,
                    "modified": datetime.fromtimestamp(art_file.stat().st_mtime),
                })

        logger.debug(f"Encontrados {len(artifacts)} artefatos")
        return artifacts

    def scan_knowledge(self) -> list[dict]:
        """
        Encontra Knowledge Items (KIs) do Antigravity.

        Returns:
            Lista de dicts com path, metadata, etc.
        """
        items = []

        if not self.knowledge_dir.exists():
            return items

        for ki_dir in sorted(self.knowledge_dir.iterdir()):
            if not ki_dir.is_dir():
                continue

            meta_path = ki_dir / "metadata.json"
            if not meta_path.exists():
                continue

            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                continue

            # Encontrar artefatos do KI
            ki_artifacts = []
            ki_art_dir = ki_dir / "artifacts"
            if ki_art_dir.exists():
                for art in ki_art_dir.iterdir():
                    if art.is_file():
                        ki_artifacts.append(art)

            items.append({
                "id": ki_dir.name,
                "path": ki_dir,
                "metadata": metadata,
                "artifacts": ki_artifacts,
            })

        logger.debug(f"Encontrados {len(items)} knowledge items")
        return items

    def _extract_date(self, overview_path: Path) -> datetime | None:
        """Extrai a data da primeira linha do overview.txt."""
        try:
            with open(overview_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()

            if not first_line:
                return None

            entry = json.loads(first_line)
            date_str = entry.get("created_at", "")
            if date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        except (json.JSONDecodeError, Exception):
            pass

        return None

    def get_conversation_summary_list(self) -> list[dict]:
        """
        Retorna uma lista resumida de conversas para exibição rápida.
        Lê apenas a primeira linha de cada overview para ser eficiente.
        """
        summaries = []

        for conv in self.scan_conversations():
            # Ler primeira mensagem do usuário para gerar título
            try:
                with open(conv["overview_path"], "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()

                entry = json.loads(first_line)
                content = entry.get("content", "")

                # Extrair USER_REQUEST
                import re
                match = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", content, re.DOTALL)
                title = "Conversa"
                if match:
                    title = match.group(1).strip().split("\n")[0][:60]

                summaries.append({
                    "id": conv["id"][:12],
                    "title": title,
                    "date": conv["date"].strftime("%Y-%m-%d %H:%M") if conv["date"] else "?",
                    "size": f"{conv['size_bytes'] / 1024:.0f}KB",
                })

            except Exception:
                continue

        return summaries
