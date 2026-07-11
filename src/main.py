"""パイプラインのオーケストレーター

使い方:
  python -m src.main create          動画1本を生成(台本→音声→動画→記事)
  python -m src.main upload          生成済み(ready)の動画を1本投稿
  python -m src.main site            誘導先HPをビルド
  python -m src.main run             create → upload → site を一括実行(日次用)
  python -m src.main list            生成・投稿履歴を表示
  python -m src.main expand-topics   Claudeで新しいネタを20個追加
  python -m src.main demo            APIなしでサンプル動画を生成(動作確認用)
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from . import db
from .config import OUTPUT_DIR, load_config, load_topics, append_topics


def _pick_topic() -> str:
    used = db.used_topics()
    for t in load_topics():
        if t not in used:
            return t
    return ""


def cmd_create(cfg: dict, demo: bool = False) -> int | None:
    from . import tts, video_builder

    tts.check_engine(cfg)  # 先に確認し、API課金前に失敗させる

    if demo:
        topic = "(デモ) 年金の繰り下げ受給"
        script = {
            "title": "年金を75歳まで繰り下げると84%増える?【デモ】",
            "scenes": [
                {"caption": "年金、75歳まで待つと84%増?", "narration": "実は、年金の受け取りを遅らせるだけで、受給額が最大84%も増える制度があるのをご存知ですか?"},
                {"caption": "繰り下げ受給という制度", "narration": "これは繰り下げ受給という制度で、65歳からの受け取りを1か月遅らせるごとに、0.7%ずつ増えていきます。"},
                {"caption": "70歳なら42%増", "narration": "たとえば70歳まで待てば42%増、75歳まで待てば84%増になります。"},
                {"caption": "注意点もあります", "narration": "ただし、受け取り開始が遅いほど、長生きしないと総額で損になる場合もあります。ご自身の健康状態と相談が大切です。"},
                {"caption": "詳しくは概要欄へ", "narration": "詳しい損益分岐点の計算は、概要欄のリンクからご覧ください。"},
            ],
            "description": "年金の繰り下げ受給の仕組みを解説します。(これはデモ動画です)",
            "tags": ["年金", "繰り下げ受給"],
        }
    else:
        from . import script_gen

        topic = _pick_topic()
        if not topic:
            print("未使用のネタがありません。Claudeで新ネタを生成します...")
            append_topics(script_gen.generate_topics(db.used_topics(), cfg))
            topic = _pick_topic()
            if not topic:
                print("ネタの生成に失敗しました。config/topics.yaml に手動追加してください。")
                return None

        print(f"[1/4] 台本生成中: {topic}")
        script = script_gen.generate_script(topic, cfg)

    video_id = db.create_entry(topic)
    db.save_script(video_id, script["title"], script)
    print(f"  タイトル: {script['title']} ({len(script['scenes'])}シーン)")

    work_dir = OUTPUT_DIR / f"work_{video_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    scenes = script["scenes"]

    print(f"[2/4] 音声合成中 (VOICEVOX)")
    for i, scene in enumerate(scenes):
        tts.synthesize(scene["narration"], work_dir / f"scene_{i}.wav", cfg)

    print(f"[3/4] 動画生成中")
    from .video_builder import render_slide, build_video

    for i, scene in enumerate(scenes):
        render_slide(
            scene["caption"], i, len(scenes), cfg,
            work_dir / f"slide_{i}.png", is_last=(i == len(scenes) - 1),
        )
    out_path = OUTPUT_DIR / f"short_{video_id}.mp4"
    duration = build_video(work_dir, len(scenes), cfg, out_path)
    db.save_video_path(video_id, str(out_path))
    if demo:
        db.set_status(video_id, "demo")  # デモ動画は投稿対象にしない
    print(f"  完成: {out_path} ({duration:.1f}秒)")
    if duration > cfg["video"].get("max_seconds", 60):
        print(f"  ⚠ {cfg['video']['max_seconds']}秒を超えています。台本が長すぎる可能性があります。")

    if not demo:
        print(f"[4/4] ブログ記事生成中")
        from . import article_gen

        try:
            article = article_gen.generate_article(script["title"], script, cfg)
            html = article_gen.to_html(article["body_markdown"], cfg)
            db.save_article(
                video_id, article["slug"], article["title"],
                article["lead"], html, article["category"],
            )
            print(f"  記事: {article['title']}")
        except Exception as e:
            print(f"  ⚠ 記事生成に失敗(動画は生成済み): {e}")

    shutil.rmtree(work_dir, ignore_errors=True)
    return video_id


def cmd_upload(cfg: dict, video_id: int | None = None, privacy: str | None = None) -> None:
    from . import uploader

    if video_id is not None:
        row = db.get_video(video_id)
        if not row:
            print(f"ID {video_id} の動画が見つかりません。")
            return
        if not row["video_path"]:
            print(f"ID {video_id} は動画が未生成です。")
            return
    else:
        row = db.next_ready_video()
        if not row:
            print("投稿待ち(ready)の動画がありません。先に create を実行してください。")
            return

    if privacy:
        cfg["youtube"]["privacy_status"] = privacy

    script = json.loads(row["script_json"])
    site_url = cfg["site"]["base_url"].rstrip("/")
    if row["article_slug"]:
        site_url = f"{site_url}/articles/{row['article_slug']}.html"
    footer = cfg.get("description_footer", "").format(site_url=site_url)
    description = script.get("description", "") + "\n\n" + footer

    print(f"投稿中: {row['title']}")
    try:
        yt_id = uploader.upload_video(
            Path(row["video_path"]), row["title"], description,
            script.get("tags", []), cfg,
        )
    except Exception:
        db.mark_failed(row["id"])
        raise
    db.mark_uploaded(row["id"], yt_id)
    print(f"  投稿完了: https://www.youtube.com/shorts/{yt_id}")


def cmd_site(cfg: dict) -> None:
    from .build_site import build_site

    build_site(cfg)


def cmd_list() -> None:
    rows = db.list_videos()
    if not rows:
        print("履歴がありません。")
        return
    print(f"{'ID':>4}  {'状態':<10} {'タイトル':<40} YouTube")
    for r in rows:
        yt = f"https://youtube.com/shorts/{r['youtube_id']}" if r["youtube_id"] else "-"
        print(f"{r['id']:>4}  {r['status']:<10} {(r['title'] or r['topic'])[:38]:<40} {yt}")


def cmd_expand_topics(cfg: dict) -> None:
    from . import script_gen

    new = script_gen.generate_topics(db.used_topics() | set(load_topics()), cfg)
    append_topics(new)
    print(f"{len(new)} 個のネタを config/topics.yaml に追加しました:")
    for t in new:
        print(f"  - {t}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "command",
        choices=["create", "upload", "site", "run", "list", "expand-topics", "demo"],
    )
    parser.add_argument("--id", type=int, help="uploadで投稿する動画IDを指定(デモ動画のテスト投稿等)")
    parser.add_argument(
        "--privacy", choices=["public", "unlisted", "private"],
        help="uploadの公開設定を一時的に上書き(テストは unlisted 推奨)",
    )
    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
        return

    cfg = load_config()

    if args.command == "create":
        cmd_create(cfg)
    elif args.command == "demo":
        cmd_create(cfg, demo=True)
    elif args.command == "upload":
        cmd_upload(cfg, video_id=args.id, privacy=args.privacy)
    elif args.command == "site":
        cmd_site(cfg)
    elif args.command == "expand-topics":
        cmd_expand_topics(cfg)
    elif args.command == "run":
        video_id = cmd_create(cfg)
        if video_id is not None:
            cmd_upload(cfg)
            cmd_site(cfg)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code and not isinstance(e.code, int):
            print(e.code, file=sys.stderr)
            sys.exit(1)
        raise
