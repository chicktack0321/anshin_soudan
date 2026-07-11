"""設定ファイルの読み込み"""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "config.yaml"
TOPICS_PATH = ROOT / "config" / "topics.yaml"
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(
            "config/config.yaml がありません。\n"
            "  copy config\\config.example.yaml config\\config.yaml\n"
            "を実行して設定してください。"
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if not cfg.get("anthropic", {}).get("api_key"):
        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        cfg.setdefault("anthropic", {})["api_key"] = env_key

    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    return cfg


def load_topics() -> list[str]:
    with open(TOPICS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("topics", [])


def append_topics(new_topics: list[str]) -> None:
    topics = load_topics()
    topics.extend(t for t in new_topics if t not in topics)
    with open(TOPICS_PATH, "w", encoding="utf-8") as f:
        f.write("# ネタ(トピック)リスト\n")
        yaml.safe_dump({"topics": topics}, f, allow_unicode=True, default_flow_style=False)
