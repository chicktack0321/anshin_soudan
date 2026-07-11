# 50代以上向け YouTubeショート × アフィリエイト 自動化システム

「お金・年金・節約」ジャンルのショート動画を自動生成・投稿し、
アフィリエイト記事付きの誘導先HPに集客するパイプラインです。

## 全体の流れ

```
ネタリスト (config/topics.yaml)
   │
   ▼ Claude API ──── 台本生成(コンプライアンス配慮込み)
   │
   ▼ VOICEVOX ────── ナレーション音声合成(無料)
   │
   ▼ Pillow+ffmpeg ─ 大文字字幕スライド動画 (1080x1920)
   │
   ▼ YouTube API ─── ショート自動投稿(概要欄に記事リンク)
   │
   ▼ Claude API ──── 動画と連動したブログ記事生成
   │
   ▼ 静的サイト ───── docs/ に出力 → GitHub Pages等で公開
                      記事内にアフィリエイトボタン ← ここで収益化
```

## 1. 初回セットアップ

### 1-1. 依存ライブラリ

```powershell
pip install -r requirements.txt
```

ffmpeg が必要です(インストール済みなら不要): `winget install Gyan.FFmpeg`

### 1-2. VOICEVOX(無料の音声合成)

https://voicevox.hiroshiba.jp/ からダウンロードしてインストール。
**動画生成時はVOICEVOXアプリを起動しておく**こと(`run_daily.ps1` は自動起動を試みます)。

話者は `config.yaml` の `voicevox.speaker` で変更可能。
デフォルトは 13(青山龍星: 落ち着いた男性声。シニア向けに聞き取りやすい)。

> VOICEVOXの利用規約上、動画の概要欄等にクレジット表記(例: `VOICEVOX:青山龍星`)が必要です。
> `config.yaml` の `description_footer` に追記してください。

### 1-3. 設定ファイル

```powershell
copy config\config.example.yaml config\config.yaml
```

`config/config.yaml` を開いて設定:
- `anthropic.api_key` — https://console.anthropic.com/ で取得(環境変数 `ANTHROPIC_API_KEY` でも可)
- `site.base_url` — HP公開後のURL
- `affiliate.links` — ASPで取得したアフィリエイトリンク(後述)

### 1-4. YouTube API(自動投稿用)

#### プロジェクト作成とAPI有効化

1. https://console.cloud.google.com/ で新規プロジェクト作成
2. 「APIとサービス」→「ライブラリ」で「YouTube Data API v3」を検索して有効化

#### OAuth同意画面の設定

3. 「APIとサービス」→「OAuth同意画面」(新UIでは「Google Auth Platform」)を開く
   - User Type: **外部**
   - アプリ名・サポートメール・デベロッパー連絡先を入力(すべて自分のメールでOK)
   - スコープの追加画面は何もせずスキップ(実行時にアプリ側が要求する)
   - **テストユーザーに投稿に使うGoogleアカウントを追加**(未追加だと認証がブロックされる)

#### OAuthクライアントIDの作成

4. 「APIとサービス」→「認証情報」→ 上部の「+ 認証情報を作成」→「OAuthクライアントID」
5. アプリケーションの種類: **デスクトップアプリ**(ウェブアプリではない。リダイレクトURI等の設定は不要)
6. 名前は任意(例: short-uploader)→「作成」
7. 作成直後のダイアログで「JSONをダウンロード」
   (閉じた場合は認証情報一覧の右端のダウンロードアイコンから取得可能)
8. ダウンロードした `client_secret_xxx.json` を `config\client_secrets.json` に配置:
   ```powershell
   Copy-Item "$env:USERPROFILE\Downloads\client_secret_*.json" config\client_secrets.json
   ```

#### 初回認証

9. `python -m src.main upload` の初回実行時にブラウザが開く
10. 投稿先チャンネルのアカウントを選択(ブランドアカウント運用ならチャンネル選択も出る)
11. 「このアプリは Google で確認されていません」の警告は正常。
    「詳細」→「(アプリ名)に移動」で進み、アップロード権限を「許可」
12. トークンは `data/youtube_token.json` に保存され、以降はブラウザ認証不要

#### ⚠ 重要: 本番環境への公開(7日でトークンが切れる問題の対策)

公開ステータスが「テスト」のままだと **リフレッシュトークンが7日で失効し、毎週再認証が必要**になる。
動作確認が済んだら「OAuth同意画面」で **「本番環境に公開」(PUBLISH APP)** に変更すること。
審査に出さなくても自分のアカウントでの利用は継続でき、トークンの7日失効がなくなる
(認証時に未確認アプリの警告が出続けるだけで実害なし)。

> APIのデフォルトクォータでは動画投稿は **1日約6本まで**(10,000ユニット/日、投稿1本=1,600ユニット)。日次運用なら十分です。

### 1-5. ASP(アフィリエイト)登録

このジャンルと相性が良いASP:
- **A8.net** — 保険相談・家計簿アプリ・格安SIMなど案件豊富
- **もしもアフィリエイト** — Amazon・楽天の物販も扱える
- **アクセストレード** — 金融系案件が強い

審査にはHPが必要な場合が多いので、先にサイトを数記事公開してから申請するとスムーズです。
取得したリンクを `config.yaml` の `affiliate.links` に登録すると、
記事生成時にClaudeが文脈に合う箇所へ自動でボタンを挿入します。

## 2. 使い方

```powershell
python -m src.main demo           # 動作確認(Claude API不要、VOICEVOXは必要)
python -m src.main create         # 動画1本生成(台本→音声→動画→記事)
python -m src.main upload         # 生成済み動画を1本YouTubeに投稿
python -m src.main site           # 誘導先HPを docs/ にビルド
python -m src.main run            # 上記3つを一括実行(日次用)
python -m src.main list           # 履歴一覧
python -m src.main expand-topics  # Claudeで新ネタを20個追加
```

## 3. 毎日の自動実行(タスクスケジューラ)

管理者PowerShellで一度だけ実行(毎朝7時の例):

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\System_Dev\Short_afiliate\run_daily.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00
Register-ScheduledTask -TaskName "ShortAffiliateDaily" -Action $action -Trigger $trigger
```

ログは `data/logs/` に保存されます。

## 4. HPの公開(GitHub Pages・無料)

1. GitHubにリポジトリを作成し、このプロジェクトをpush(`.gitignore` で秘密情報は除外済み。
   ただし `docs/` も除外されているので、公開時は `.gitignore` から `docs/` の行を削除)
2. リポジトリの Settings → Pages → Source を `main` ブランチの `/docs` に設定
3. 公開URLを `config.yaml` の `site.base_url` に設定 → 以後の動画概要欄に記事リンクが入る

## 5. 運用上の注意(重要)

- **YouTubeのポリシー**: 機械的な量産・繰り返しコンテンツはチャンネル収益化(YPP)審査で
  弾かれることがあります。本システムはアフィリエイト収益が主軸なのでYPP必須ではありませんが、
  台本の質を保つこと・同じ構成の乱発を避けることがチャンネル継続の鍵です。
  1日1〜2本ペースから始めて反応を見るのを推奨します。
- **ステマ規制(景表法)**: サイトに「アフィリエイト広告を利用しています」の表記が必須。
  テンプレートに組み込み済みですが、消さないこと。
- **金融コンテンツ**: 個別の投資助言(金商法)にならないよう、台本生成プロンプトで
  「制度の一般的な解説に徹する」よう制約済み。ただし公開前に内容の事実確認を推奨します。
  制度改正(年金額・NISA等)で古い情報になっていないか定期的に確認してください。
- **VOICEVOXクレジット表記**: 概要欄への表記を忘れずに。

## 6. コスト目安

| 項目 | 月額(1日1本 = 月30本) |
|---|---|
| Claude API (claude-sonnet-5, 台本+記事) | 数十〜数百円 |
| VOICEVOX / ffmpeg / Pillow | 無料 |
| YouTube API | 無料 |
| GitHub Pages | 無料 |
| **合計** | **500円以内が目安** |

## ファイル構成

```
config/config.yaml      設定(APIキー・アフィリリンク等) ※git管理外
config/topics.yaml      ネタリスト
src/main.py             CLI(create/upload/site/run...)
src/script_gen.py       Claude台本生成
src/tts.py              VOICEVOX音声合成
src/video_builder.py    スライド画像+ffmpeg動画生成
src/uploader.py         YouTube投稿
src/article_gen.py      ブログ記事生成
src/build_site.py       静的サイトビルド
site/templates/         HPテンプレート(シニア向け大文字デザイン)
output/                 生成された動画
data/pipeline.db        生成・投稿履歴(SQLite)
docs/                   ビルドされたHP(公開用)
run_daily.ps1           日次自動実行スクリプト
```
