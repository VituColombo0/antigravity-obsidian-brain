"""
Parser — Converte dados brutos do Antigravity em Markdown limpo.

Parseia os overview.txt (JSON line-by-line) de cada conversa
e gera notas Markdown formatadas, com:
- Resumo executivo
- Diálogos limpos (sem XML/JSON)
- Tags automáticas
- Wikilinks para projetos e arquivos
- Metadados YAML frontmatter
"""

import json
import re
import logging
from datetime import datetime
from pathlib import Path


logger = logging.getLogger("brain.parser")


# Padrões de linguagens para auto-tagging
LANGUAGE_PATTERNS = {
    "python": [r"\.py\b", r"\bpython\b", r"\bpip\b", r"\bvenv\b"],
    "javascript": [r"\.js\b", r"\bjavascript\b", r"\bnpm\b", r"\bnode\b"],
    "typescript": [r"\.ts\b", r"\btypescript\b", r"\btsx\b"],
    "html": [r"\.html\b", r"\bhtml\b"],
    "css": [r"\.css\b", r"\bcss\b", r"\btailwind\b"],
    "rust": [r"\.rs\b", r"\brust\b", r"\bcargo\b"],
    "go": [r"\.go\b", r"\bgolang\b"],
    "shell": [r"\.sh\b", r"\bbash\b", r"\bshell\b"],
    "yaml": [r"\.yaml\b", r"\.yml\b"],
    "sql": [r"\.sql\b", r"\bsql\b", r"\bdatabase\b"],
}

# Padrões de ações para auto-tagging
ACTION_PATTERNS = {
    "git": [r"\bgit\b", r"\bcommit\b", r"\bmerge\b", r"\bbranch\b", r"\bpush\b"],
    "install": [r"\binstall\b", r"\bsetup\b", r"\bnpm install\b", r"\bpip install\b"],
    "debug": [r"\bdebug\b", r"\berro\b", r"\berror\b", r"\bfix\b", r"\bbug\b"],
    "refactor": [r"\brefactor\b", r"\brename\b", r"\breorganiz\b"],
    "deploy": [r"\bdeploy\b", r"\bbuild\b", r"\bproduc\b"],
    "design": [r"\bdesign\b", r"\bui\b", r"\bux\b", r"\blayout\b", r"\bestilo\b"],
    "test": [r"\btest\b", r"\bteste\b", r"\bspec\b"],
}


class ConversationParser:
    """
    Parseia o overview.txt de uma conversa do Antigravity
    e gera Markdown limpo para o Obsidian.
    """

    def __init__(self, config: dict):
        self.config = config.get("parser", {})
        self.tag_config = config.get("tags", {})
        self.summary_max = self.config.get("summary_max_length", 500)
        self.include_tools = self.config.get("include_tool_calls", True)
        self.include_meta = self.config.get("include_metadata", True)

    def parse_overview(self, overview_path: Path) -> dict | None:
        """
        Parseia um overview.txt e retorna dados estruturados.

        Args:
            overview_path: Caminho para o overview.txt.

        Returns:
            Dict com title, date, messages, tags, summary, files_touched, etc.
            Ou None se falhar.
        """
        try:
            content = overview_path.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
        except Exception as e:
            logger.error(f"Erro ao ler {overview_path}: {e}")
            return None

        if not lines:
            return None

        messages = []
        first_user_msg = None
        first_date = None
        all_tool_calls = []
        files_touched = set()

        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            source = entry.get("source", "")
            entry_type = entry.get("type", "")
            content_text = entry.get("content", "")
            created_at = entry.get("created_at", "")
            tool_calls = entry.get("tool_calls", [])

            # Capturar data da primeira entrada
            if created_at and not first_date:
                try:
                    first_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            # Extrair mensagens do usuário
            if source == "USER_EXPLICIT" and entry_type == "USER_INPUT":
                user_msg = self._extract_user_message(content_text)
                if user_msg:
                    messages.append({"role": "user", "content": user_msg, "time": created_at})
                    if not first_user_msg:
                        first_user_msg = user_msg

            # Extrair respostas do modelo
            elif source == "MODEL" and entry_type == "PLANNER_RESPONSE":
                if content_text:
                    # Limpar o texto de escape sequences
                    clean = content_text.replace("\\n", "\n").strip()
                    if clean:
                        messages.append({"role": "assistant", "content": clean, "time": created_at})

                # Coletar tool calls
                if tool_calls and self.include_tools:
                    for tc in tool_calls:
                        tool_name = tc.get("name", "")
                        tool_args = tc.get("args", {})
                        all_tool_calls.append({"name": tool_name, "args": tool_args})

                        # Extrair arquivos tocados
                        for arg_key in ["TargetFile", "AbsolutePath", "SearchPath"]:
                            val = tool_args.get(arg_key, "")
                            if val:
                                clean_val = val.strip('"')
                                if clean_val and "/" in clean_val:
                                    files_touched.add(clean_val)

        if not messages:
            return None

        # Gerar título
        title = self._generate_title(first_user_msg or "Conversa sem título")

        # Gerar tags
        all_text = " ".join(m["content"] for m in messages)
        tags = self._detect_tags(all_text)

        # Gerar resumo
        summary = self._generate_summary(messages)

        # ID da conversa (nome do diretório pai)
        conv_id = overview_path.parent.parent.parent.name

        return {
            "id": conv_id,
            "title": title,
            "date": first_date,
            "messages": messages,
            "tool_calls": all_tool_calls,
            "files_touched": sorted(files_touched),
            "tags": tags,
            "summary": summary,
        }

    def to_markdown(self, data: dict) -> str:
        """
        Converte dados parseados em Markdown formatado para Obsidian.

        Args:
            data: Dict retornado por parse_overview().

        Returns:
            String com o conteúdo Markdown completo.
        """
        parts = []

        # --- YAML Frontmatter ---
        if self.include_meta:
            date_str = data["date"].strftime("%Y-%m-%d %H:%M") if data["date"] else "desconhecida"
            tags_str = "\n".join(f"  - {t}" for t in data["tags"])
            frontmatter = (
                f"---\n"
                f"title: \"{data['title']}\"\n"
                f"date: {date_str}\n"
                f"conversation_id: \"{data['id']}\"\n"
                f"type: conversation\n"
                f"tags:\n{tags_str}\n"
                f"---\n"
            )
            parts.append(frontmatter)

        # --- Título ---
        parts.append(f"# 💬 {data['title']}\n")

        # --- Metadados ---
        if self.include_meta:
            date_display = data["date"].strftime("%d/%m/%Y às %H:%M") if data["date"] else "?"
            parts.append(f"📅 **Data:** {date_display}")
            parts.append(f"🔑 **ID:** `{data['id'][:12]}...`\n")

        # --- Resumo ---
        if data["summary"]:
            parts.append(f"## 📋 Resumo\n\n{data['summary']}\n")

        # --- Arquivos Tocados ---
        if data["files_touched"]:
            parts.append("## 📁 Arquivos Modificados\n")
            for f in data["files_touched"][:20]:  # Limitar a 20
                basename = Path(f).name
                parts.append(f"- `{basename}` — `{f}`")
            parts.append("")

        # --- Conversa ---
        parts.append("## 💬 Conversa\n")

        for msg in data["messages"]:
            if msg["role"] == "user":
                parts.append(f"### 👤 Usuário\n\n{msg['content']}\n")
            elif msg["role"] == "assistant":
                content = msg["content"]
                # Truncar respostas muito longas
                if len(content) > 2000:
                    content = content[:2000] + "\n\n*(...resposta truncada)*"
                parts.append(f"### 🤖 Antigravity\n\n{content}\n")

        # --- Tool Calls (resumido) ---
        if data["tool_calls"] and self.include_tools:
            parts.append("## ⚡ Ações Executadas\n")
            seen = set()
            for tc in data["tool_calls"]:
                name = tc["name"]
                summary = tc["args"].get("toolSummary", tc["args"].get("toolAction", ""))
                if summary:
                    summary = summary.strip('"')
                key = f"{name}:{summary}"
                if key not in seen:
                    seen.add(key)
                    parts.append(f"- **{name}** — {summary}")
            parts.append("")

        # --- Tags ---
        if data["tags"]:
            tag_str = " ".join(f"#{t}" for t in data["tags"])
            parts.append(f"\n---\n{tag_str}\n")

        return "\n".join(parts)

    # ─── Métodos internos ──────────────────────────────────

    def _extract_user_message(self, raw: str) -> str | None:
        """Extrai a mensagem do usuário de dentro de tags XML."""
        # Buscar <USER_REQUEST>...</USER_REQUEST>
        match = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", raw, re.DOTALL)
        if match:
            msg = match.group(1).strip()
            # Remover linhas vazias extras
            msg = re.sub(r"\n{3,}", "\n\n", msg)
            return msg if msg else None

        # Fallback: se não tiver as tags, usar o texto inteiro (limpo)
        clean = re.sub(r"<[^>]+>.*?</[^>]+>", "", raw, flags=re.DOTALL).strip()
        clean = re.sub(r"<[^>]+>", "", clean).strip()
        return clean if clean else None

    def _generate_title(self, first_message: str) -> str:
        """Gera um título curto a partir da primeira mensagem do usuário."""
        # Pegar a primeira linha significativa
        lines = [l.strip() for l in first_message.split("\n") if l.strip()]
        if not lines:
            return "Conversa sem título"

        title = lines[0]

        # Limpar e truncar
        title = re.sub(r"[^\w\sàáâãéêíóôõúçÀÁÂÃÉÊÍÓÔÕÚÇ,.:!?-]", "", title)
        title = title.strip()

        if len(title) > 60:
            title = title[:57] + "..."

        return title or "Conversa sem título"

    def _generate_summary(self, messages: list[dict]) -> str:
        """Gera um resumo executivo da conversa."""
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        assistant_msgs = [m["content"] for m in messages if m["role"] == "assistant"]

        summary_parts = []

        if user_msgs:
            summary_parts.append(f"**Pedidos do usuário:** {len(user_msgs)} mensagens")
            # Listar os primeiros pedidos
            for i, msg in enumerate(user_msgs[:3]):
                short = msg[:120].replace("\n", " ")
                summary_parts.append(f"{i + 1}. {short}")

        if assistant_msgs:
            summary_parts.append(f"\n**Respostas:** {len(assistant_msgs)} respostas do Antigravity")

        summary = "\n".join(summary_parts)

        if len(summary) > self.summary_max:
            summary = summary[: self.summary_max] + "..."

        return summary

    def _detect_tags(self, text: str) -> list[str]:
        """Detecta tags automáticas baseadas no conteúdo."""
        tags = set()
        text_lower = text.lower()

        # Detectar linguagens
        if self.tag_config.get("detect_languages", True):
            for lang, patterns in LANGUAGE_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, text_lower):
                        tags.add(f"lang/{lang}")
                        break

        # Detectar ações
        if self.tag_config.get("detect_actions", True):
            for action, patterns in ACTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, text_lower):
                        tags.add(f"action/{action}")
                        break

        # Tags customizadas
        custom = self.tag_config.get("custom", {})
        for pattern, tag in custom.items():
            if re.search(pattern, text, re.IGNORECASE):
                tags.add(tag)

        return sorted(tags)


class ArtifactParser:
    """
    Parseia artefatos do Antigravity (arquivos .md em artifacts/).

    Artefatos já são Markdown, então o parsing é mais simples:
    apenas adiciona frontmatter e links.
    """

    def __init__(self, config: dict):
        self.config = config

    def parse_artifact(self, artifact_path: Path, conv_id: str) -> dict | None:
        """
        Parseia um artefato e retorna dados estruturados.

        Args:
            artifact_path: Caminho do arquivo .md
            conv_id: ID da conversa que gerou o artefato.

        Returns:
            Dict com title, content, metadata, etc.
        """
        try:
            content = artifact_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Erro ao ler artefato {artifact_path}: {e}")
            return None

        if not content.strip():
            return None

        # Extrair título do primeiro heading
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else artifact_path.stem

        # Limpar emojis do título para nome de arquivo
        clean_title = re.sub(r"[^\w\sàáâãéêíóôõúçÀÁÂÃÉÊÍÓÔÕÚÇ-]", "", title).strip()

        # Tentar ler metadata.json se existir
        meta_path = artifact_path.with_suffix(".md.metadata.json")
        metadata = {}
        if meta_path.exists():
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                pass

        # Data de modificação do arquivo
        mod_time = datetime.fromtimestamp(artifact_path.stat().st_mtime)

        return {
            "title": title,
            "clean_title": clean_title or artifact_path.stem,
            "content": content,
            "metadata": metadata,
            "conv_id": conv_id,
            "date": mod_time,
            "original_path": str(artifact_path),
        }

    def to_markdown(self, data: dict) -> str:
        """Converte artefato parseado em Markdown com frontmatter."""
        parts = []

        # Frontmatter
        date_str = data["date"].strftime("%Y-%m-%d %H:%M")
        artifact_type = data["metadata"].get("ArtifactType", "other")
        summary = data["metadata"].get("Summary", "")

        frontmatter = (
            f"---\n"
            f"title: \"{data['title']}\"\n"
            f"date: {date_str}\n"
            f"type: artifact\n"
            f"artifact_type: {artifact_type}\n"
            f"conversation_id: \"{data['conv_id']}\"\n"
            f"---\n"
        )
        parts.append(frontmatter)

        # Link para a conversa original
        parts.append(
            f"> 📎 Gerado na conversa `{data['conv_id'][:12]}...`\n"
        )

        # Conteúdo original
        parts.append(data["content"])

        return "\n".join(parts)
