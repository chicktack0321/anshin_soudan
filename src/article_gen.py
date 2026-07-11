"""動画台本からHP用アフィリエイト記事を生成"""
import json
import re

import markdown as md

from .categories import CATEGORIES, DEFAULT_CATEGORY
from .script_gen import _client, _extract_json, _response_text

ARTICLE_SYSTEM = """あなたは50代・60代向けのお金情報サイトの編集者です。
YouTubeショート動画の台本を元に、より詳しく解説するブログ記事を書きます。

必ず守るルール:
- 断定的な利益保証をしない。「必ず」「絶対」は使わない
- 制度の説明は一般論に徹し、個別の投資助言をしない
- 見出しを使って読みやすく。1段落は3〜4文まで
- 文字は大きく表示される前提。簡潔で具体的に
- 記事の自然な流れの中で、指定されたアフィリエイト案件に言及できる箇所があれば
  {{AFF:キー名}} という行を挿入する(無理に入れない。関連する案件のみ、最大2箇所)

出力はJSONのみ。"""

ARTICLE_PROMPT = """以下のショート動画の台本を元に、1200〜1800字のブログ記事を書いてください。

動画タイトル: {title}
台本:
{script_text}

利用可能なアフィリエイト案件(関連するものだけ {{{{AFF:キー名}}}} で挿入):
{aff_list}

カテゴリ(最も近いスラッグを1つ選ぶ):
{category_list}

以下のJSON形式で出力:
{{
  "slug": "URLスラッグ(英小文字とハイフンのみ、例: nenkin-kurisage)",
  "title": "記事タイトル(検索されやすいキーワードを含む)",
  "lead": "記事の導入文(80字程度)",
  "category": "カテゴリのスラッグ",
  "body_markdown": "記事本文(Markdown形式。##見出しを使う)"
}}"""

AFF_BUTTON_HTML = """
<div class="aff-box">
  <p class="aff-note">PR</p>
  <a class="aff-button" href="{url}" target="_blank" rel="nofollow sponsored noopener">{label}</a>
</div>
"""


def generate_article(title: str, script: dict, cfg: dict) -> dict:
    client = _client(cfg)
    script_text = "\n".join(
        f"- {s['caption']}: {s['narration']}" for s in script["scenes"]
    )
    links = cfg.get("affiliate", {}).get("links", {}) or {}
    aff_list = "\n".join(
        f"- キー名: {key} / 内容: {v.get('description', v.get('label', ''))}"
        for key, v in links.items()
    ) or "(なし)"

    category_list = "\n".join(
        f"- {slug}: {info['name']}({info['description']})"
        for slug, info in CATEGORIES.items()
    )

    resp = client.messages.create(
        model=cfg["anthropic"]["model"],
        max_tokens=12000,  # thinking がデフォルト有効なモデルは思考分も消費する
        system=ARTICLE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": ARTICLE_PROMPT.format(
                    title=title, script_text=script_text,
                    aff_list=aff_list, category_list=category_list,
                ),
            }
        ],
    )
    article = _extract_json(_response_text(resp))
    for key in ("slug", "title", "lead", "body_markdown"):
        if not article.get(key):
            raise ValueError(f"記事JSONに {key} がありません")
    article["slug"] = re.sub(r"[^a-z0-9-]", "-", article["slug"].lower()).strip("-")
    if article.get("category") not in CATEGORIES:
        article["category"] = DEFAULT_CATEGORY
    return article


def to_html(body_markdown: str, cfg: dict) -> str:
    """Markdown→HTML変換 + アフィリエイトボタン差し込み"""
    links = cfg.get("affiliate", {}).get("links", {}) or {}

    def replace_aff(m: re.Match) -> str:
        key = m.group(1).strip()
        link = links.get(key)
        if not link:
            return ""
        return AFF_BUTTON_HTML.format(url=link["url"], label=link["label"])

    html = md.markdown(body_markdown, extensions=["tables", "nl2br"])
    html = re.sub(r"(?:<p>)?\{\{AFF:([\w-]+)\}\}(?:</p>)?", replace_aff, html)
    return html
