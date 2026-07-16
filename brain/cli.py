"""
CLI — Interface de linha de comando do Antigravity Obsidian Brain.

Comandos:
    python -m brain sync          Sincronização completa
    python -m brain sync --incremental   Apenas novos
    python -m brain watch         Modo daemon (auto-sync)
    python -m brain status        Status do vault
    python -m brain reindex       Reconstruir índice
    python -m brain export <id>   Exportar conversa específica
"""

import argparse
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from brain.config import load_config, setup_logging
from brain.scanner import AntigravityScanner
from brain.parser import ConversationParser, ArtifactParser
from brain.exporter import ObsidianExporter
from brain.watcher import BrainWatcher


console = Console()


def cmd_sync(config: dict, incremental: bool = True):
    """Executa sincronização completa ou incremental."""
    logger = setup_logging(config)

    console.print(
        Panel(
            "[bold bright_cyan]🧠 Antigravity Obsidian Brain[/]\n\n"
            f"  Modo: [bold]{'Incremental' if incremental else 'Completo'}[/]\n"
            f"  Vault: [dim]{config['vault']['path']}[/]\n"
            f"  Dados: [dim]{config['antigravity']['data_dir']}[/]",
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )

    # Inicializar
    scanner = AntigravityScanner(config)
    conv_parser = ConversationParser(config)
    art_parser = ArtifactParser(config)

    # Forçar modo completo se solicitado
    if not incremental:
        config["sync"]["incremental"] = False

    exporter = ObsidianExporter(config)
    exporter.initialize_vault()

    # Escanear
    console.print("\n[bold]🔍 Escaneando dados do Antigravity...[/]\n")
    scan_result = scanner.scan_all()

    conversations = scan_result["conversations"]
    artifacts = scan_result["artifacts"]
    knowledge = scan_result["knowledge_items"]

    stats = {"conversations": 0, "artifacts": 0, "knowledge": 0}

    # Sincronizar conversas
    if conversations:
        console.print(f"[bold]💬 Sincronizando {len(conversations)} conversas...[/]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Conversas", total=len(conversations))

            for conv in conversations:
                parsed = conv_parser.parse_overview(conv["overview_path"])
                if parsed:
                    result = exporter.export_conversation(parsed)
                    if result:
                        stats["conversations"] += 1

                progress.advance(task)

    # Sincronizar artefatos
    if artifacts:
        console.print(f"\n[bold]📦 Sincronizando {len(artifacts)} artefatos...[/]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Artefatos", total=len(artifacts))

            for art in artifacts:
                parsed = art_parser.parse_artifact(art["path"], art["conv_id"])
                if parsed:
                    result = exporter.export_artifact(parsed)
                    if result:
                        stats["artifacts"] += 1

                progress.advance(task)

    # Sincronizar knowledge
    if knowledge:
        console.print(f"\n[bold]📚 Sincronizando {len(knowledge)} knowledge items...[/]\n")

        for ki in knowledge:
            result = exporter.export_knowledge_item(ki)
            if result:
                stats["knowledge"] += 1

    # Reconstruir índice
    console.print("\n[bold]📋 Reconstruindo índice...[/]")
    exporter.rebuild_index()

    # Salvar estado e log
    exporter.save_sync_state()
    exporter.log_sync(stats)

    # Resultado final
    total = stats["conversations"] + stats["artifacts"] + stats["knowledge"]
    console.print(
        Panel(
            f"[bold bright_green]✅ Sincronização concluída![/]\n\n"
            f"  💬 Conversas: [bold]{stats['conversations']}[/] novas\n"
            f"  📦 Artefatos: [bold]{stats['artifacts']}[/] novos\n"
            f"  📚 Knowledge: [bold]{stats['knowledge']}[/] itens\n"
            f"  📊 Total: [bold]{total}[/] itens sincronizados\n\n"
            f"  📂 Vault: [dim]{config['vault']['path']}[/]\n\n"
            f"  [dim]Abra o Obsidian e aponte para a pasta acima![/]",
            border_style="bright_green",
            padding=(1, 2),
        )
    )


def cmd_watch(config: dict):
    """Inicia o modo daemon (auto-sync)."""
    logger = setup_logging(config)

    console.print(
        Panel(
            "[bold bright_magenta]👁️  Modo Watch[/]\n\n"
            "Monitorando mudanças em tempo real.\n"
            "Pressione [bold]Ctrl+C[/] para parar.",
            border_style="bright_magenta",
            padding=(1, 2),
        )
    )

    # Fazer sync inicial
    cmd_sync(config, incremental=True)

    # Iniciar watcher
    watcher = BrainWatcher(config)
    watcher.run_forever()


def cmd_status(config: dict):
    """Mostra o status do vault e dados."""
    scanner = AntigravityScanner(config)
    exporter = ObsidianExporter(config)

    vault_path = config["vault"]["path"]
    vault_exists = vault_path.exists()

    console.print(
        Panel(
            "[bold bright_cyan]🧠 Antigravity Obsidian Brain — Status[/]",
            border_style="bright_cyan",
        )
    )

    # Tabela de diretórios
    table = Table(title="📂 Diretórios", border_style="cyan")
    table.add_column("Item", style="bold")
    table.add_column("Caminho", style="dim")
    table.add_column("Status")

    ag_dir = config["antigravity"]["data_dir"]
    table.add_row(
        "Antigravity",
        str(ag_dir),
        "[green]✅ Encontrado[/]" if ag_dir.exists() else "[red]❌ Não encontrado[/]",
    )
    table.add_row(
        "Vault Obsidian",
        str(vault_path),
        "[green]✅ Ativo[/]" if vault_exists else "[yellow]⚠️ Não inicializado[/]",
    )

    console.print(table)

    # Tabela de dados
    scan = scanner.scan_all()

    table2 = Table(title="📊 Dados Disponíveis", border_style="cyan")
    table2.add_column("Tipo", style="bold")
    table2.add_column("Quantidade", justify="right")
    table2.add_column("Sincronizados", justify="right")

    synced = len(exporter.synced_ids)

    table2.add_row(
        "💬 Conversas",
        str(len(scan["conversations"])),
        str(synced),
    )
    table2.add_row(
        "📦 Artefatos",
        str(len(scan["artifacts"])),
        "—",
    )
    table2.add_row(
        "📚 Knowledge Items",
        str(len(scan["knowledge_items"])),
        "—",
    )

    console.print(table2)

    # Vault stats
    if vault_exists:
        conv_count = len(list((vault_path / "04_Conversations").rglob("*.md")))
        art_count = len(list((vault_path / "05_Artifacts").glob("*.md")))
        proj_count = len(list((vault_path / "01_Projects").glob("*.md")))
        know_count = len(list((vault_path / "02_Knowledge").glob("*.md")))

        table3 = Table(title="🗃️ Conteúdo do Vault", border_style="cyan")
        table3.add_column("Seção", style="bold")
        table3.add_column("Arquivos", justify="right")

        table3.add_row("04_Conversations/", str(conv_count))
        table3.add_row("05_Artifacts/", str(art_count))
        table3.add_row("01_Projects/", str(proj_count))
        table3.add_row("02_Knowledge/", str(know_count))

        console.print(table3)


def cmd_reindex(config: dict):
    """Reconstrói o índice do vault."""
    setup_logging(config)
    exporter = ObsidianExporter(config)
    exporter.rebuild_index()
    console.print("[bold green]✅ Índice reconstruído com sucesso![/]")


def cmd_export(config: dict, conv_id: str):
    """Exporta uma conversa específica."""
    logger = setup_logging(config)

    brain_dir = config["antigravity"]["brain_dir"]

    # Procurar pelo ID (parcial ou completo)
    target = None
    for d in brain_dir.iterdir():
        if d.is_dir() and d.name.startswith(conv_id):
            target = d
            break

    if not target:
        console.print(f"[red]❌ Conversa não encontrada: {conv_id}[/]")
        return

    overview = target / ".system_generated" / "logs" / "overview.txt"
    if not overview.exists():
        console.print(f"[red]❌ overview.txt não encontrado para {conv_id}[/]")
        return

    parser = ConversationParser(config)
    exporter = ObsidianExporter(config)
    exporter.initialize_vault()

    parsed = parser.parse_overview(overview)
    if parsed:
        # Forçar exportação (ignorar incremental)
        exporter.synced_ids.discard(parsed["id"])
        result = exporter.export_conversation(parsed)
        if result:
            console.print(f"[green]✅ Exportado: {result}[/]")
        else:
            console.print("[red]❌ Falha na exportação.[/]")
    else:
        console.print("[red]❌ Não foi possível parsear a conversa.[/]")


def main():
    parser = argparse.ArgumentParser(
        prog="brain",
        description="🧠 Antigravity Obsidian Brain — Memória infinita para o Antigravity AI",
    )
    parser.add_argument(
        "--config", "-c",
        help="Caminho para config.yaml",
        default=None,
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Sincronizar dados para o Obsidian")
    sync_parser.add_argument(
        "--incremental", "-i",
        action="store_true",
        default=True,
        help="Sincronizar apenas novos (padrão)",
    )
    sync_parser.add_argument(
        "--full", "-f",
        action="store_true",
        help="Sincronização completa (reprocessar tudo)",
    )

    # watch
    subparsers.add_parser("watch", help="Modo daemon: sincronizar automaticamente")

    # status
    subparsers.add_parser("status", help="Status do vault e dados")

    # reindex
    subparsers.add_parser("reindex", help="Reconstruir índice do vault")

    # export
    export_parser = subparsers.add_parser("export", help="Exportar conversa específica")
    export_parser.add_argument("conversation_id", help="ID da conversa (parcial ou completo)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config(args.config)

    if args.command == "sync":
        incremental = not getattr(args, "full", False)
        cmd_sync(config, incremental=incremental)
    elif args.command == "watch":
        cmd_watch(config)
    elif args.command == "status":
        cmd_status(config)
    elif args.command == "reindex":
        cmd_reindex(config)
    elif args.command == "export":
        cmd_export(config, args.conversation_id)


if __name__ == "__main__":
    main()
