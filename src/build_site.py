"""誘導先HP(静的サイト)のビルド"""
import shutil
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from . import db
from .config import ROOT


def build_site(cfg: dict) -> Path:
    site_cfg = cfg["site"]
    out_dir = ROOT / site_cfg.get("output_dir", "docs")
    templates_dir = ROOT / "site" / "templates"
    static_dir = ROOT / "site" / "static"

    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
    ctx_base = {
        "site": site_cfg,
        "disclosure": cfg.get("affiliate", {}).get("disclosure", ""),
        "year": date.today().year,
    }

    articles = []
    for row in db.published_articles():
        articles.append(
            {
                "slug": row["article_slug"],
                "title": row["article_title"],
                "lead": row["article_lead"] or "",
                "html": row["article_html"],
                "date": (row["created_at"] or "")[:10],
                "youtube_id": row["youtube_id"],
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "articles").mkdir(exist_ok=True)

    index_tpl = env.get_template("index.html")
    (out_dir / "index.html").write_text(
        index_tpl.render(articles=articles, **ctx_base), encoding="utf-8"
    )

    article_tpl = env.get_template("article.html")
    for a in articles:
        (out_dir / "articles" / f"{a['slug']}.html").write_text(
            article_tpl.render(article=a, **ctx_base), encoding="utf-8"
        )

    if static_dir.exists():
        for f in static_dir.iterdir():
            shutil.copy2(f, out_dir / f.name)

    print(f"サイトを {out_dir} に出力しました(記事 {len(articles)} 件)")
    return out_dir
