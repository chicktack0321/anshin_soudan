# LINE公式アカウント 設定メモ

## 特典PDFの配布URL(サイトからはリンクされていない非公開URL)

| テーマ | 配布URL |
|---|---|
| 年金・生活費 | https://chicktack0321.github.io/anshin_soudan/tokuten/karte-nenkin-x7k2m9.pdf |
| 医療・介護の備え | https://chicktack0321.github.io/anshin_soudan/tokuten/karte-iryo-p3v8n4.pdf |
| 相続・終活 | https://chicktack0321.github.io/anshin_soudan/tokuten/karte-souzoku-w6t2r8.pdf |

※ファイル名を変えたい場合は `src/make_tokuten.py` の `public_name` を変更して
`python -m src.make_tokuten` → `git push`(変更前のURLは無効になるので配信済みメッセージに注意)

## あいさつメッセージ(友だち追加時の自動送信)の文面案

```
ご登録ありがとうございます😊
『50代からのお金の教科書』です。

お約束の【50代からの個別お金防衛カルテ(PDF)】をお届けします。

診断で出たあなたの「重点テーマ」のカルテをお受け取りください👇

🏦 年金・生活費タイプの方
https://chicktack0321.github.io/anshin_soudan/tokuten/karte-nenkin-x7k2m9.pdf

🏥 医療・介護の備えタイプの方
https://chicktack0321.github.io/anshin_soudan/tokuten/karte-iryo-p3v8n4.pdf

📖 相続・終活タイプの方
https://chicktack0321.github.io/anshin_soudan/tokuten/karte-souzoku-w6t2r8.pdf

もちろん、3つすべて受け取っていただいてもOKです✨

これから週1回ほど、50代からのお金の
「知らないと損する話」をお届けしていきます。
不要になったらいつでもブロックで解除できます。
```

## 応答メッセージ(キーワード自動応答)の設定案

| 受信キーワード | 返信 |
|---|---|
| 年金 | 年金・生活費カルテのURLを返信 |
| 医療 / 介護 / 保険 | 医療・介護カルテのURLを返信 |
| 相続 / 終活 | 相続・終活カルテのURLを返信 |
| カルテ | 3つ全部のURLを返信(あいさつメッセージと同文) |

## 開設後にやること

1. LINE Official Account Manager で友だち追加URL(https://lin.ee/xxxx)を取得
2. `config/config.yaml` の `line.url` に設定
3. `python -m src.main site` → `git add docs && git commit && git push`
   → 診断ページのボタンが「準備中」から本物のLINE誘導に切り替わる
