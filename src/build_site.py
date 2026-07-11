"""誘導先HP(静的サイト)のビルド

出力構成:
  docs/
    index.html            トップ(カテゴリ一覧+新着記事)
    category/<slug>.html  カテゴリ別記事一覧
    articles/<slug>.html  記事ページ(関連記事付き)
    about.html ほか       固定ページ (site/pages/*.md)
    sitemap.xml           検索エンジン向け
"""
import shutil
from datetime import date
from pathlib import Path

import markdown as md
from jinja2 import Environment, FileSystemLoader

from . import db
from .categories import CATEGORIES, DEFAULT_CATEGORY, category_list
from .config import ROOT


def _load_articles() -> list[dict]:
    articles = []
    for row in db.published_articles():
        cat = row["category"] if row["category"] in CATEGORIES else DEFAULT_CATEGORY
        articles.append(
            {
                "slug": row["article_slug"],
                "title": row["article_title"],
                "lead": row["article_lead"] or "",
                "html": row["article_html"],
                "date": (row["created_at"] or "")[:10],
                "youtube_id": row["youtube_id"],
                "category": cat,
                "category_name": CATEGORIES[cat]["name"],
                "category_emoji": CATEGORIES[cat]["emoji"],
            }
        )
    return articles


def _load_pages() -> list[dict]:
    """site/pages/*.md を固定ページとして読み込む(先頭の # 見出しをタイトルに使う)"""
    pages = []
    pages_dir = ROOT / "site" / "pages"
    if not pages_dir.exists():
        return pages
    for f in sorted(pages_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        title = f.stem
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        pages.append({"slug": f.stem, "title": title, "html": md.markdown(text, extensions=["tables"])})
    return pages


def build_site(cfg: dict) -> Path:
    site_cfg = cfg["site"]
    out_dir = ROOT / site_cfg.get("output_dir", "docs")
    templates_dir = ROOT / "site" / "templates"
    static_dir = ROOT / "site" / "static"

    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=False)
    categories = category_list()
    ctx_base = {
        "site": site_cfg,
        "disclosure": cfg.get("affiliate", {}).get("disclosure", ""),
        "year": date.today().year,
        "categories": categories,
    }

    articles = _load_articles()
    counts: dict[str, int] = {}
    for a in articles:
        counts[a["category"]] = counts.get(a["category"], 0) + 1

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "articles").mkdir(exist_ok=True)
    (out_dir / "category").mkdir(exist_ok=True)
    (out_dir / ".nojekyll").touch()  # GitHub PagesにJekyll処理をさせない

    # トップページ
    index_tpl = env.get_template("index.html")
    (out_dir / "index.html").write_text(
        index_tpl.render(articles=articles, counts=counts, root="", **ctx_base),
        encoding="utf-8",
    )

    # カテゴリページ
    cat_tpl = env.get_template("category.html")
    for c in categories:
        cat_articles = [a for a in articles if a["category"] == c["slug"]]
        (out_dir / "category" / f"{c['slug']}.html").write_text(
            cat_tpl.render(
                category=c, articles=cat_articles, root="../",
                current_category=c["slug"], **ctx_base,
            ),
            encoding="utf-8",
        )

    # 記事ページ(同カテゴリの他記事を「あわせて読みたい」に最大3件)
    article_tpl = env.get_template("article.html")
    for a in articles:
        related = [
            x for x in articles if x["category"] == a["category"] and x["slug"] != a["slug"]
        ][:3]
        (out_dir / "articles" / f"{a['slug']}.html").write_text(
            article_tpl.render(
                article=a, related=related, root="../",
                current_category=a["category"], **ctx_base,
            ),
            encoding="utf-8",
        )

    # 固定ページ (運営者情報・プライバシーポリシー・免責事項)
    page_tpl = env.get_template("page.html")
    pages = _load_pages()
    for p in pages:
        (out_dir / f"{p['slug']}.html").write_text(
            page_tpl.render(page=p, root="", **ctx_base), encoding="utf-8"
        )

    # sitemap.xml
    base = site_cfg["base_url"].rstrip("/")
    urls = [f"{base}/"]
    urls += [f"{base}/category/{c['slug']}.html" for c in categories]
    urls += [f"{base}/articles/{a['slug']}.html" for a in articles]
    urls += [f"{base}/{p['slug']}.html" for p in pages]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{u}</loc></url>" for u in urls]
    sitemap.append("</urlset>")
    (out_dir / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    (out_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8"
    )

    if static_dir.exists():
        for f in static_dir.iterdir():
            shutil.copy2(f, out_dir / f.name)

    print(
        f"サイトを {out_dir} に出力しました"
        f"(記事 {len(articles)} 件 / カテゴリ {len(categories)} 件 / 固定ページ {len(pages)} 件)"
    )
    return out_dir
