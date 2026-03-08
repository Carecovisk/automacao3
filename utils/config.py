"""Application configuration management.

Loads and saves settings from/to ``config.json`` at the project root.
Default values live here so ``config.json`` does not need to be committed.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

OUTPUT_PATH = Path.home() / ".automacao3" / "output"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
_CONFIG_PATH = OUTPUT_PATH / "config.json"

_DEFAULTS: dict = {
    "use_llm": False,
    "gemini_api_key": "",
    "use_llm_abbreviation_expansion": False,
    "use_llm_judge": False,
    "high_confidence_threshold": 0.9,
}


@dataclass
class AppConfig:
    use_llm: bool = False
    gemini_api_key: str = ""
    use_llm_abbreviation_expansion: bool = False
    use_llm_judge: bool = False
    high_confidence_threshold: float = 0.9


def load_config() -> AppConfig:
    """Read ``config.json``; creates it with defaults if absent."""
    if not _CONFIG_PATH.exists():
        cfg = AppConfig()
        save_config(cfg)
        return cfg

    with _CONFIG_PATH.open("r", encoding="utf-8") as f:
        data: dict = json.load(f)

    # Merge with defaults so new fields added in the future don't break old files
    merged = {**_DEFAULTS, **data}
    return AppConfig(
        use_llm=bool(merged["use_llm"]),
        gemini_api_key=str(merged["gemini_api_key"]),
        use_llm_abbreviation_expansion=bool(merged["use_llm_abbreviation_expansion"]),
        use_llm_judge=bool(merged["use_llm_judge"]),
        high_confidence_threshold=float(merged["high_confidence_threshold"]),
    )


def save_config(config: AppConfig) -> None:
    """Write *config* atomically to ``config.json``."""
    data = asdict(config)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=_CONFIG_PATH.parent, suffix=".tmp", prefix="config_"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, _CONFIG_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
