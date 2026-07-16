"""
Config — Gerenciamento de configuração do Brain.

Carrega config.yaml, detecta diretórios do Antigravity automaticamente,
e fornece defaults sensatos para tudo.
"""

import os
import logging
from pathlib import Path

import yaml


# Defaults globais
DEFAULTS = {
    "vault": {
        "path": "~/.gemini/antigravity/brain_vault",
    },
    "antigravity": {
        "data_dir": "~/.gemini/antigravity",
    },
    "sync": {
        "auto": True,
        "interval_minutes": 5,
        "watch_mode": True,
        "incremental": True,
    },
    "parser": {
        "summary_max_length": 500,
        "include_tool_calls": True,
        "include_metadata": True,
    },
    "tags": {
        "detect_languages": True,
        "detect_actions": True,
        "custom": {},
    },
    "logging": {
        "level": "INFO",
        "file": "brain_sync.log",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge recursivo de dicts. Override tem prioridade."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _expand_path(path_str: str) -> Path:
    """Expande ~ e variáveis de ambiente em caminhos."""
    return Path(os.path.expanduser(os.path.expandvars(path_str))).resolve()


def load_config(config_path: str | Path | None = None) -> dict:
    """
    Carrega a configuração do Brain.

    Ordem de prioridade:
    1. config.yaml fornecido
    2. config.yaml no diretório atual
    3. Defaults embutidos

    Args:
        config_path: Caminho para o config.yaml (opcional).

    Returns:
        Dict com a configuração completa e caminhos resolvidos.
    """
    config = DEFAULTS.copy()

    # Tentar carregar config.yaml
    if config_path:
        cfg_file = Path(config_path)
    else:
        # Procurar em locais padrão
        candidates = [
            Path.cwd() / "config.yaml",
            Path(__file__).parent.parent / "config.yaml",
            _expand_path("~/.config/antigravity-brain/config.yaml"),
        ]
        cfg_file = None
        for candidate in candidates:
            if candidate.exists():
                cfg_file = candidate
                break

    if cfg_file and cfg_file.exists():
        with open(cfg_file, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        config = _deep_merge(DEFAULTS, user_config)

    # Resolver caminhos
    config["vault"]["path"] = _expand_path(config["vault"]["path"])
    config["antigravity"]["data_dir"] = _expand_path(
        config["antigravity"].get("data_dir", "~/.gemini/antigravity")
    )

    # Derivar caminhos internos do Antigravity
    ag_dir = config["antigravity"]["data_dir"]
    config["antigravity"]["brain_dir"] = ag_dir / "brain"
    config["antigravity"]["conversations_dir"] = ag_dir / "conversations"
    config["antigravity"]["knowledge_dir"] = ag_dir / "knowledge"

    # Validar que o diretório do Antigravity existe
    if not ag_dir.exists():
        logging.warning(
            f"Diretório do Antigravity não encontrado em {ag_dir}. "
            f"Certifique-se de que o Antigravity está instalado."
        )

    return config


def setup_logging(config: dict) -> logging.Logger:
    """Configura o logger do Brain."""
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)

    logger = logging.getLogger("brain")
    logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_fmt = logging.Formatter(
        "%(asctime)s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # File handler (opcional)
    log_file = log_config.get("file")
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger
