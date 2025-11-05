"""Gestión del archivo de configuración de la interfaz."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from .constants import CategoriaTipo, PersonaTipo


CONFIG_PATH = Path.home() / ".gobant_rx_tools_gui.json"


@dataclass
class TemplateConfig:
    natural_cat1: str = ""
    natural_cat2: str = ""
    juridica_cat1: str = ""
    juridica_cat2: str = ""

    def resolve_path(self, persona: PersonaTipo, categoria: CategoriaTipo) -> str:
        if persona == PersonaTipo.NATURAL:
            return self.natural_cat1 if categoria == CategoriaTipo.CAT_1 else self.natural_cat2
        return self.juridica_cat1 if categoria == CategoriaTipo.CAT_1 else self.juridica_cat2


@dataclass
class GuiConfig:
    templates: TemplateConfig = field(default_factory=TemplateConfig)
    last_open_dir: str = ""
    last_save_dir: str = ""


DEFAULT_CONFIG = GuiConfig()


def load_config(path: Path = CONFIG_PATH) -> GuiConfig:
    if not path.exists():
        return DEFAULT_CONFIG
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    templates = TemplateConfig(**data.get("templates", {}))
    return GuiConfig(
        templates=templates,
        last_open_dir=data.get("last_open_dir", ""),
        last_save_dir=data.get("last_save_dir", ""),
    )


def save_config(config: GuiConfig, path: Path = CONFIG_PATH) -> None:
    serializable = asdict(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(serializable, fh, ensure_ascii=False, indent=2)
