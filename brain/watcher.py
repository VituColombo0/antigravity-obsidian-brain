"""
Watcher — Monitora mudanças e sincroniza automaticamente.

Usa watchdog para detectar novas conversas e artefatos no
diretório do Antigravity e sincronizar em tempo real.
"""

import logging
import time
import threading
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

from brain.scanner import AntigravityScanner
from brain.parser import ConversationParser, ArtifactParser
from brain.exporter import ObsidianExporter


logger = logging.getLogger("brain.watcher")


class BrainEventHandler(FileSystemEventHandler):
    """
    Handler de eventos do filesystem.
    Detecta novos overview.txt e artefatos.
    """

    def __init__(self, config: dict, exporter: ObsidianExporter):
        super().__init__()
        self.config = config
        self.exporter = exporter
        self.conv_parser = ConversationParser(config)
        self.art_parser = ArtifactParser(config)
        self._debounce_lock = threading.Lock()
        self._pending = set()
        self._debounce_timer = None

    def on_created(self, event):
        self._handle_event(event)

    def on_modified(self, event):
        self._handle_event(event)

    def _handle_event(self, event):
        """Processa eventos de criação/modificação."""
        if event.is_directory:
            return

        path = Path(event.src_path)

        # overview.txt criado/modificado -> nova conversa
        if path.name == "overview.txt" and ".system_generated" in str(path):
            self._schedule_sync(path, "conversation")

        # Artefato .md criado em artifacts/
        elif path.suffix == ".md" and path.parent.name == "artifacts":
            self._schedule_sync(path, "artifact")

    def _schedule_sync(self, path: Path, sync_type: str):
        """
        Agenda uma sincronização com debounce.
        Espera 3 segundos após a última mudança antes de sincronizar.
        """
        with self._debounce_lock:
            self._pending.add((str(path), sync_type))

            if self._debounce_timer:
                self._debounce_timer.cancel()

            self._debounce_timer = threading.Timer(3.0, self._process_pending)
            self._debounce_timer.start()

    def _process_pending(self):
        """Processa itens pendentes de sincronização."""
        with self._debounce_lock:
            items = list(self._pending)
            self._pending.clear()

        for path_str, sync_type in items:
            path = Path(path_str)

            try:
                if sync_type == "conversation":
                    data = self.conv_parser.parse_overview(path)
                    if data:
                        self.exporter.export_conversation(data)
                        logger.info(f"🔄 Nova conversa sincronizada: {data['title'][:40]}")

                elif sync_type == "artifact":
                    # Extrair conv_id do caminho
                    conv_id = path.parent.parent.name
                    data = self.art_parser.parse_artifact(path, conv_id)
                    if data:
                        self.exporter.export_artifact(data)
                        logger.info(f"🔄 Novo artefato sincronizado: {path.name}")

            except Exception as e:
                logger.error(f"Erro ao sincronizar {path}: {e}")

        # Reconstruir índice e salvar estado
        try:
            self.exporter.rebuild_index()
            self.exporter.save_sync_state()
        except Exception as e:
            logger.error(f"Erro ao atualizar índice: {e}")


class BrainWatcher:
    """
    Observador que monitora o diretório do Antigravity
    e sincroniza mudanças para o Obsidian em tempo real.
    """

    def __init__(self, config: dict):
        self.config = config
        self.brain_dir = config["antigravity"]["brain_dir"]
        self.interval = config["sync"].get("interval_minutes", 5) * 60
        self._observer = None
        self._running = False

    def start(self):
        """Inicia o watcher em background."""
        if not WATCHDOG_AVAILABLE:
            logger.error(
                "watchdog não está instalado. "
                "Instale com: pip install watchdog"
            )
            return False

        if not self.brain_dir.exists():
            logger.error(f"Diretório do Antigravity não encontrado: {self.brain_dir}")
            return False

        exporter = ObsidianExporter(self.config)
        exporter.initialize_vault()

        handler = BrainEventHandler(self.config, exporter)

        self._observer = Observer()
        self._observer.schedule(handler, str(self.brain_dir), recursive=True)
        self._observer.start()
        self._running = True

        logger.info(
            f"👁️  Watcher iniciado — monitorando {self.brain_dir}\n"
            f"   Sincronizando para {self.config['vault']['path']}"
        )

        return True

    def run_forever(self):
        """Roda o watcher em loop até Ctrl+C."""
        if not self.start():
            return

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⏹️  Watcher encerrado pelo usuário.")
        finally:
            self.stop()

    def stop(self):
        """Para o watcher."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        logger.info("Watcher parado.")
