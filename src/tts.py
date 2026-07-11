"""VOICEVOX による音声合成"""
from pathlib import Path

import requests


def check_engine(cfg: dict) -> None:
    url = cfg["voicevox"]["url"]
    try:
        requests.get(f"{url}/version", timeout=3)
    except requests.ConnectionError:
        raise SystemExit(
            f"VOICEVOXエンジンに接続できません ({url})。\n"
            "VOICEVOXアプリを起動してから再実行してください。\n"
            "未インストールの場合: https://voicevox.hiroshiba.jp/"
        )


def synthesize(text: str, out_path: Path, cfg: dict) -> Path:
    """テキストをWAVに変換して保存"""
    base = cfg["voicevox"]["url"]
    speaker = cfg["voicevox"]["speaker"]

    r = requests.post(
        f"{base}/audio_query", params={"text": text, "speaker": speaker}, timeout=30
    )
    r.raise_for_status()
    query = r.json()
    query["speedScale"] = cfg["voicevox"].get("speed", 1.0)
    query["postPhonemeLength"] = 0.3  # 語尾の余韻

    r = requests.post(
        f"{base}/synthesis", params={"speaker": speaker}, json=query, timeout=120
    )
    r.raise_for_status()
    out_path.write_bytes(r.content)
    return out_path
