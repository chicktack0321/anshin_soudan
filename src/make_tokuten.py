"""LINE登録特典PDF『50代からの個別お金防衛カルテ』の生成

使い方:
  python -m src.make_tokuten

出力:
  tokuten/            編集・確認用(わかりやすいファイル名)
  docs/tokuten/       LINE配布用(推測されにくいファイル名。サイトからリンクしない)

デザイン方針: A4 / BIZ UDゴシック / 大きめ文字 / 紺×金 / チェックリスト形式
※PDF内では絵文字はフォントに無いため使わない(■ ● ▶ □ などで代替)
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer,
    Table, TableStyle,
)

from .config import ROOT

# ---- ブランドカラー ----
NAVY = colors.HexColor("#152449")
NAVY2 = colors.HexColor("#1E3161")
GOLD = colors.HexColor("#C9A227")
GOLD_SOFT = colors.HexColor("#F0C452")
GOLD_PALE = colors.HexColor("#FFF8E4")
CREAM = colors.HexColor("#FAF6EC")
TEXT = colors.HexColor("#26282E")
TEXT_SUB = colors.HexColor("#5A5E68")
BORDER = colors.HexColor("#D8D2C0")

SITE_NAME = "50代からのお金の教科書"
SITE_URL = "https://chicktack0321.github.io/anshin_soudan/"
ASOF = "2026年7月時点"

# ---- フォント登録 (Windows標準のBIZ UDゴシック) ----
pdfmetrics.registerFont(TTFont("UD", "C:/Windows/Fonts/BIZ-UDGothicR.ttc", subfontIndex=0))
pdfmetrics.registerFont(TTFont("UDB", "C:/Windows/Fonts/BIZ-UDGothicB.ttc", subfontIndex=0))

# ---- スタイル ----
S = {
    "series": ParagraphStyle("series", fontName="UDB", fontSize=12, leading=18,
                             textColor=colors.HexColor("#8A6D10"), alignment=1),
    "cover_title": ParagraphStyle("cover_title", fontName="UDB", fontSize=27, leading=42,
                                  textColor=NAVY, alignment=1),
    "cover_sub": ParagraphStyle("cover_sub", fontName="UD", fontSize=13, leading=22,
                                textColor=TEXT_SUB, alignment=1),
    "cover_target": ParagraphStyle("cover_target", fontName="UDB", fontSize=13, leading=22,
                                   textColor=NAVY, alignment=1),
    "h2": ParagraphStyle("h2", fontName="UDB", fontSize=15, leading=24,
                         textColor=colors.white),
    "lead": ParagraphStyle("lead", fontName="UD", fontSize=11.5, leading=20, textColor=TEXT),
    "item_title": ParagraphStyle("item_title", fontName="UDB", fontSize=12.5, leading=20,
                                 textColor=NAVY),
    "item_detail": ParagraphStyle("item_detail", fontName="UD", fontSize=10.5, leading=17,
                                  textColor=TEXT_SUB),
    "box_title": ParagraphStyle("box_title", fontName="UDB", fontSize=13, leading=21,
                                textColor=NAVY),
    "box_body": ParagraphStyle("box_body", fontName="UD", fontSize=11, leading=19, textColor=TEXT),
    "note": ParagraphStyle("note", fontName="UD", fontSize=9, leading=15, textColor=TEXT_SUB),
    "checkbox": ParagraphStyle("checkbox", fontName="UD", fontSize=17, leading=20,
                               textColor=NAVY, alignment=1),
}


def _footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(GOLD_SOFT)
    canvas.setLineWidth(1)
    canvas.line(18 * mm, 16 * mm, w - 18 * mm, 16 * mm)
    canvas.setFont("UD", 8.5)
    canvas.setFillColor(TEXT_SUB)
    canvas.drawString(18 * mm, 11 * mm, f"{SITE_NAME}  {SITE_URL}")
    canvas.drawRightString(w - 18 * mm, 11 * mm, f"- {doc.page} -  無断転載禁止")
    # 上部の帯
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 8 * mm, w, 8 * mm, stroke=0, fill=1)
    canvas.setFillColor(GOLD_SOFT)
    canvas.rect(0, h - 9.2 * mm, w, 1.2 * mm, stroke=0, fill=1)
    canvas.setFont("UDB", 9)
    canvas.setFillColor(colors.white)
    canvas.drawCentredString(w / 2, h - 5.8 * mm, "50代からの個別お金防衛カルテ")
    canvas.restoreState()


def _heading(text: str) -> Table:
    """紺の帯見出し"""
    t = Table([[Paragraph(text, S["h2"])]], colWidths=[174 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 2.5, GOLD_SOFT),
    ]))
    return t


def _check_item(title: str, detail: str) -> Table:
    """□ + 項目名 + 解説 のチェック行"""
    body = Paragraph(
        f"{title}<br/><font size='10.5' color='#5A5E68'>{detail}</font>", S["item_title"]
    )
    t = Table([[Paragraph("□", S["checkbox"]), body]], colWidths=[12 * mm, 162 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.7, BORDER),
    ]))
    return t


def _info_box(title: str, body: str, bg=GOLD_PALE, border=GOLD_SOFT) -> Table:
    inner = [
        [Paragraph(title, S["box_title"])],
        [Paragraph(body, S["box_body"])],
    ]
    t = Table(inner, colWidths=[168 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1.5, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return t


def build_pdf(spec: dict, out_path: Path) -> None:
    doc = BaseDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=24 * mm,
        title=spec["title"].replace("<br/>", ""), author=SITE_NAME,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=_footer)])

    story = []

    # ---- 表紙 ----
    story.append(Spacer(1, 26 * mm))
    story.append(Paragraph(f"■ {spec['series']} ■", S["series"]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(spec["title"], S["cover_title"]))
    story.append(Spacer(1, 6 * mm))
    line = Table([[""]], colWidths=[46 * mm], rowHeights=[1.8 * mm])
    line.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOLD)]))
    story.append(line)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(spec["target"], S["cover_target"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "「安心お金の価値観・リスク診断」の結果にもとづく、あなた専用の実践シートです。<br/>"
        "上から順に、できたところに チェック□ を入れていくだけで使えます。",
        S["cover_sub"]))
    story.append(Spacer(1, 14 * mm))
    story.append(_info_box(
        "■ このカルテの使い方(3ステップ)",
        "1. 印刷するか、スマホでこのまま眺めながら進めます<br/>"
        "2. できている項目の □ にチェックを入れます(できていなくて当たり前です)<br/>"
        "3. チェックが入らなかった項目を、1週間に1つだけ進めてみてください",
    ))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        f"発行: {SITE_NAME}({ASOF})", S["cover_sub"]))
    story.append(PageBreak())

    # ---- 本文セクション ----
    for sec in spec["sections"]:
        story.append(_heading(sec["heading"]))
        story.append(Spacer(1, 4 * mm))
        if sec.get("lead"):
            story.append(Paragraph(sec["lead"], S["lead"]))
            story.append(Spacer(1, 3 * mm))
        for title, detail in sec["items"]:
            story.append(_check_item(title, detail))
        story.append(Spacer(1, 8 * mm))

    # ---- しめくくり(途中で改ページされないようにひとかたまりで) ----
    story.append(KeepTogether([
        _heading("■ 次の一歩"),
        Spacer(1, 4 * mm),
        _info_box(spec["next_title"], spec["next_body"]),
        Spacer(1, 6 * mm),
        _info_box(
            "■ 相談できる公式の窓口",
            spec["windows"],
            bg=CREAM, border=NAVY2,
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            f"【ご注意】本資料は{ASOF}の一般的な情報にもとづく情報提供を目的としたもので、"
            "個別の投資助言・保険募集・税務助言ではありません。制度の内容は法改正等により変更される"
            "場合があります。実際の手続きやご判断の際は、必ず公式の窓口や専門家にご確認ください。",
            S["note"]),
    ]))

    doc.build(story)


# ============================================================
# 3種類のカルテの中身
# ============================================================
PDFS = [
    {
        "slug": "01_nenkin_karte",
        "public_name": "karte-nenkin-x7k2m9.pdf",
        "series": "50代からの個別お金防衛カルテ 01",
        "title": "年金・生活費の<br/>安心チェックリスト",
        "target": "重点テーマ「年金・生活費」と診断されたあなたへ",
        "sections": [
            {
                "heading": "第1章 まず「現状」を知る - すべてはここから",
                "lead": "年金の不安のほとんどは「自分がいくらもらえるか知らない」ことから生まれます。最初の3つで現在地を確認しましょう。",
                "items": [
                    ("ねんきん定期便を確認した",
                     "毎年誕生月に届くハガキです。「老齢年金の種類と見込額」の欄を見るだけでOK。捨ててしまった場合も再発行できます。"),
                    ("「ねんきんネット」に登録した",
                     "日本年金機構の無料サービス。スマホでいつでも見込額を試算できます。マイナポータルからも連携できます。"),
                    ("毎月の生活費を書き出した",
                     "ざっくりで大丈夫。固定費(住居・光熱・通信・保険)と、食費などの変動費に分けて書くと「年金で足りるか」が見えてきます。"),
                ],
            },
            {
                "heading": "第2章 「受け取り方」の選択肢を知る",
                "lead": "同じ年金でも、受け取り方しだいで金額は大きく変わります。決める必要はまだありません。「知っておく」ことが大切です。",
                "items": [
                    ("繰下げ受給のしくみを知っている",
                     "受け取り開始を遅らせると1ヶ月ごとに0.7%増額。最大75歳まで遅らせると84%増になります。増額は一生続きます。"),
                    ("繰上げ受給の注意点を知っている",
                     "早く受け取ると1ヶ月ごとに減額され(生年月日により月0.4%等)、その減額も一生続きます。決める前に必ず試算を。"),
                    ("働きながら受け取る場合のルールを確認した",
                     "在職老齢年金といい、給与と年金の合計が基準額を超えると年金の一部が支給停止されます。基準額は年度により変わるため年金事務所で確認を。"),
                ],
            },
            {
                "heading": "第3章 「もらい忘れ・払いすぎ」を防ぐ",
                "lead": "年金まわりには「自分から手続きしないと受け取れないお金」がいくつもあります。",
                "items": [
                    ("加給年金の対象か確認した",
                     "厚生年金に20年以上加入した人に、年下の配偶者などがいる場合の\"家族手当\"。対象でも手続きしないと受け取れません。"),
                    ("国民年金の未納・免除期間を確認した",
                     "追納できる期間には期限があります(原則10年以内)。ねんきんネットで未納月をすぐ確認できます。"),
                    ("年金生活者支援給付金を知っている",
                     "住民税非課税など一定の条件を満たすと、年金に上乗せで受け取れる給付金です。請求手続きが必要です。"),
                    ("付加年金・任意加入を確認した(自営業・フリーの方)",
                     "月400円の付加保険料で、納めた月数×200円が毎年上乗せに。約2年の受給で元がとれる制度です。"),
                ],
            },
        ],
        "next_title": "■ チェックが3個以下だった方へ",
        "next_body": "焦らなくて大丈夫です。まずは第1章の「ねんきんネット登録」だけ、今週やってみてください。"
                     "現在地がわかるだけで、不安の半分は小さくなります。続きのくわしい解説は"
                     f"『{SITE_NAME}』の年金カテゴリの記事でお読みいただけます。",
        "windows": "・年金事務所(全国どこでも/予約制)<br/>"
                   "・ねんきんダイヤル 0570-05-1165<br/>"
                   "・街角の年金相談センター<br/>"
                   "・ねんきんネット(日本年金機構の公式サイトから)",
    },
    {
        "slug": "02_iryo_kaigo_karte",
        "public_name": "karte-iryo-p3v8n4.pdf",
        "series": "50代からの個別お金防衛カルテ 02",
        "title": "医療・介護の備え<br/>優先順位シート",
        "target": "重点テーマ「医療・介護の備え」と診断されたあなたへ",
        "sections": [
            {
                "heading": "STEP 1 「公的保障の実力」を先に知る",
                "lead": "民間保険を考えるのは、公的保障を知ってからが正しい順番です。日本の公的保障は意外なほど手厚いのです。",
                "items": [
                    ("高額療養費制度を知っている",
                     "医療費の自己負担には月ごとの上限があります。たとえば70歳未満・年収370〜770万円なら月9万円弱が目安(収入により異なります)。"),
                    ("限度額適用認定証(またはマイナ保険証)を知っている",
                     "事前の手続きで、窓口での支払い自体を上限額までにできます。マイナ保険証なら手続き不要になる場合もあります。"),
                    ("医療費控除を知っている",
                     "家族分を合算して年10万円(または所得の5%)を超えた分は、確定申告で税金が戻ります。レシートは捨てずに保管を。"),
                ],
            },
            {
                "heading": "STEP 2 「介護の入り口」を知っておく",
                "lead": "介護は突然始まります。いざという時に慌てないための3つです。",
                "items": [
                    ("地域包括支援センターの場所を調べた",
                     "介護の総合相談窓口です。「親のことで…」という漠然とした相談でもOK。お住まいの市区町村名+地域包括支援センターで検索できます。"),
                    ("介護保険の申請の流れを知っている",
                     "市区町村に申請 → 認定調査 → 要介護度の決定 → ケアプラン作成、という流れです。申請は家族が代行できます。"),
                    ("介護サービスの自己負担割合を知っている",
                     "原則1割負担(所得により2〜3割)。さらに高額介護サービス費という月額上限のしくみもあります。"),
                ],
            },
            {
                "heading": "STEP 3 いまの保険を「棚卸し」する",
                "lead": "新しく入る前に、いま入っている保険の整理から。ここで払いすぎが見つかる方がとても多いです。",
                "items": [
                    ("加入中の保険証券を1か所に集めた",
                     "生命保険・医療保険・がん保険・共済…。まず全部を1つの引き出しやファイルにまとめるだけで大きな前進です。"),
                    ("保障内容の重複をチェックした",
                     "入院日額の合計はいくらか。STEP1の公的保障と重なりすぎていないか。「なんとなく2つ入っている」は見直しどころです。"),
                    ("保険料の合計月額を書き出した",
                     "全部でいくら払っているかを1つの数字に。年間・10年間に直してみると、見直しの本気度が変わります。"),
                ],
            },
            {
                "heading": "STEP 4 足りない分「だけ」民間で備える",
                "lead": "順番の最後が民間保険です。「不安だから」ではなく「この金額が足りないから」で選ぶのがコツです。",
                "items": [
                    ("公的保障でカバーされない費用を確認した",
                     "差額ベッド代・先進医療・入院中の食事代・交通費などは高額療養費の対象外です。ここが民間保険の出番です。"),
                    ("家族に保険と医療情報の場所を伝えた",
                     "保険の一覧・かかりつけ医・お薬手帳の場所を家族と共有。いざという時、請求もれを防ぎます。"),
                ],
            },
        ],
        "next_title": "■ 最初の一歩はSTEP1から",
        "next_body": "今週は「高額療養費制度で自分の上限額を調べる」だけでOKです。ご自身の健康保険組合(または協会けんぽ・国保)の"
                     "サイトで確認できます。くわしい解説は"
                     f"『{SITE_NAME}』の保険・制度カテゴリの記事でお読みいただけます。",
        "windows": "・ご加入の健康保険組合/協会けんぽ/市区町村の国保窓口<br/>"
                   "・地域包括支援センター(介護の総合相談)<br/>"
                   "・市区町村の介護保険課<br/>"
                   "・国税庁(医療費控除/確定申告)",
    },
    {
        "slug": "03_souzoku_karte",
        "public_name": "karte-souzoku-w6t2r8.pdf",
        "series": "50代からの個別お金防衛カルテ 03",
        "title": "相続・終活<br/>はじめの一歩シート",
        "target": "重点テーマ「相続・終活」と診断されたあなたへ",
        "sections": [
            {
                "heading": "第1歩 「書き出す」 - 財産の見える化",
                "lead": "相続準備の9割は「リストを作ること」から始まります。金額まで書かなくても、まず「何があるか」だけで十分です。",
                "items": [
                    ("銀行口座の一覧を書き出した",
                     "ネット銀行・昔作った口座も忘れずに。放置口座は家族が見つけられず、そのままになりがちです。"),
                    ("保険・証券・不動産のリストを作った",
                     "保険会社名と証券番号、証券会社名、不動産の所在地。詳細より「存在がわかること」が大切です。"),
                    ("スマホとデジタル資産の引き継ぎを考えた",
                     "スマホのロック解除方法、ネット口座、サブスク契約、写真データ。今の時代の相続で一番もめやすい部分です。"),
                ],
            },
            {
                "heading": "第2歩 「話しておく」 - 家族との共有",
                "lead": "相続トラブルは資産の多い家庭より「話し合っていなかった家庭」で起こります。",
                "items": [
                    ("家族と「もしもの話」をするきっかけを作った",
                     "お盆やお正月など家族が集まる時がチャンス。「エンディングノートを書き始めたんだ」の一言が自然な入り口になります。"),
                    ("エンディングノートを用意した",
                     "市販のもので十分です(書店・100円ショップにもあります)。全部埋めなくてOK。書ける所から少しずつ。"),
                    ("葬儀・お墓の希望をメモした",
                     "形式・規模・呼んでほしい人。希望が書いてあるだけで、いざという時の家族の迷いと心の負担が大きく減ります。"),
                ],
            },
            {
                "heading": "第3歩 「調べておく」 - 制度の基本",
                "lead": "細かい計算は専門家に任せてOK。ただし「基本のものさし」だけは知っておくと安心です。",
                "items": [
                    ("相続税の基礎控除を知っている",
                     "3,000万円+600万円×法定相続人の数。例えば相続人が3人なら4,800万円までは相続税がかかりません。多くのご家庭は対象外です。"),
                    ("自筆証書遺言の法務局保管制度を知っている",
                     "自分で書いた遺言書を法務局が預かってくれる制度(2020年開始)。紛失・改ざんの心配がなく、家庭裁判所の検認も不要になります。"),
                    ("生前贈与の基本を知っている",
                     "年110万円までの贈与は原則非課税(暦年贈与)。ただし相続直前の贈与の扱いなどルールがあるため、実行前に確認を。"),
                ],
            },
            {
                "heading": "第4歩 「専門家に相談する」目安を知る",
                "lead": "次のどれかに当てはまるなら、早めの専門家相談が結果的に安上がりです。",
                "items": [
                    ("不動産が複数ある/分けにくい財産がある",
                     "不動産は物理的に分けられないため、もめごとの最大の火種。司法書士・税理士への相談が有効です。"),
                    ("相続人が多い・関係が複雑",
                     "再婚・養子・音信不通の相続人がいる場合など。行政書士・弁護士が力になります。"),
                    ("市区町村の無料相談会を調べた",
                     "多くの自治体で司法書士・税理士の無料相談会が定期開催されています。まずはここからで十分です。"),
                ],
            },
        ],
        "next_title": "■ 最初の一歩は「口座の一覧」から",
        "next_body": "今週は「銀行口座を紙に書き出す」だけでOKです。10分でできて、家族への一番のプレゼントになります。"
                     f"くわしい解説は『{SITE_NAME}』の相続・終活カテゴリの記事でお読みいただけます。",
        "windows": "・法務局(自筆証書遺言の保管制度)<br/>"
                   "・国税庁(相続税・贈与税)<br/>"
                   "・市区町村の無料法律相談・相続相談会<br/>"
                   "・司法書士会/税理士会の相談窓口",
    },
]


def main() -> None:
    src_dir = ROOT / "tokuten"
    pub_dir = ROOT / "docs" / "tokuten"
    src_dir.mkdir(exist_ok=True)
    pub_dir.mkdir(parents=True, exist_ok=True)

    for spec in PDFS:
        out = src_dir / f"{spec['slug']}.pdf"
        build_pdf(spec, out)
        # LINE配布用(推測されにくいファイル名)にもコピー
        pub = pub_dir / spec["public_name"]
        pub.write_bytes(out.read_bytes())
        print(f"生成: {out.name}  →  配布用URL: {SITE_URL}tokuten/{spec['public_name']}")


if __name__ == "__main__":
    main()
