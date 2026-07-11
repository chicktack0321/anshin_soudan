"""Claude API による台本生成"""
import json
import re

import anthropic

SCRIPT_SYSTEM = """あなたは50代・60代向けYouTubeショート動画の放送作家です。
お金・年金・節約をテーマに、シニアが「知らなかった、得した」と感じる台本を作ります。

必ず守るルール:
- 断定的な利益保証をしない(「必ず儲かる」「絶対得する」は禁止)
- 特定の金融商品の購入を勧誘しない(制度や仕組みの一般的な解説に徹する)
- 誇張やあおりではなく、正確で具体的な数字を使う(不確かな数字は「〜の場合」と条件を付ける)
- 専門用語はかみ砕く。中学生でもわかる言葉で
- ナレーションは丁寧語。落ち着いた語り口
- 最後のシーンは必ず「詳しくは概要欄のリンクから」という誘導で締める

出力はJSONのみ。前後に説明文を書かない。"""

SCRIPT_PROMPT = """テーマ: {topic}

このテーマで40〜50秒のYouTubeショート動画の台本を作ってください。

構成:
- シーン1: 強いフック(「え、そうなの?」と思わせる問いかけや意外な事実)
- シーン2〜5: 本題(具体的な数字・手順・条件)
- 最終シーン: まとめ+「詳しくは概要欄のリンクから」

以下のJSON形式で出力:
{{
  "title": "動画タイトル(30字以内、数字を入れて興味を引く。数字や事実は本文と完全に一致させること。本文と矛盾する誇張は禁止)",
  "scenes": [
    {{
      "caption": "画面に大きく表示する短文(20字以内、体言止めや問いかけ)",
      "narration": "読み上げる文章(1シーン40〜70字程度)"
    }}
  ],
  "description": "YouTube概要欄の説明文(100字程度)",
  "tags": ["タグ1", "タグ2"]
}}

シーン数は5〜6個。narrationの合計は220〜280字に必ず収めること
(1秒あたり約6字で読み上げるため、280字を超えると60秒に収まらない)。"""

TOPICS_PROMPT = """50代・60代の日本人向けYouTubeショート動画のネタを20個考えてください。
テーマは「お金・年金・節約・制度・詐欺対策」。
「知らないと損する」「意外と知られていない」切り口で、具体的なもの。

以下は使用済みなので避けてください:
{used}

JSONの文字列配列のみで出力: ["ネタ1", "ネタ2", ...]"""


def _client(cfg: dict) -> anthropic.Anthropic:
    key = cfg["anthropic"]["api_key"]
    if not key:
        raise SystemExit(
            "Claude APIキーが未設定です。config.yaml の anthropic.api_key か"
            "環境変数 ANTHROPIC_API_KEY を設定してください。"
        )
    return anthropic.Anthropic(api_key=key)


def _response_text(resp) -> str:
    """応答からテキストブロックのみを結合して返す(思考ブロック等を除外)"""
    if resp.stop_reason == "max_tokens":
        raise ValueError("応答が max_tokens で打ち切られました。max_tokens を増やしてください")
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    if not text:
        raise ValueError("応答にテキストが含まれていません")
    return text


def _extract_json(text: str):
    """コードフェンス等を除去してJSONを取り出す"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=0)
    return json.loads(text[start:])


def generate_script(topic: str, cfg: dict) -> dict:
    client = _client(cfg)
    resp = client.messages.create(
        model=cfg["anthropic"]["model"],
        max_tokens=8000,  # thinking がデフォルト有効なモデルは思考分も消費する
        system=SCRIPT_SYSTEM,
        messages=[{"role": "user", "content": SCRIPT_PROMPT.format(topic=topic)}],
    )
    script = _extract_json(_response_text(resp))

    if not script.get("title") or not script.get("scenes"):
        raise ValueError(f"台本のJSON形式が不正です: {script}")
    if not 3 <= len(script["scenes"]) <= 10:
        raise ValueError(f"シーン数が不正です: {len(script['scenes'])}個")
    for s in script["scenes"]:
        if not s.get("caption") or not s.get("narration"):
            raise ValueError(f"シーンに caption/narration がありません: {s}")
    return script


def generate_topics(used: set[str], cfg: dict) -> list[str]:
    client = _client(cfg)
    used_text = "\n".join(f"- {t}" for t in sorted(used)) or "(なし)"
    resp = client.messages.create(
        model=cfg["anthropic"]["model"],
        max_tokens=8000,
        messages=[{"role": "user", "content": TOPICS_PROMPT.format(used=used_text)}],
    )
    topics = _extract_json(_response_text(resp))
    return [t for t in topics if isinstance(t, str) and t.strip()]
