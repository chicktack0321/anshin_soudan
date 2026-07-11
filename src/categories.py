"""サイトのカテゴリ定義

記事生成AIはこの中から1つを選んで記事に付与する。
サイトのナビゲーション・カテゴリページもここから生成される。
"""

CATEGORIES = {
    "nenkin": {
        "name": "年金",
        "emoji": "🏦",
        "description": "受け取り方・手続き・増やし方。年金を1円でも多く、確実に受け取るための知識。",
    },
    "setsuyaku": {
        "name": "節約・家計",
        "emoji": "💰",
        "description": "毎日の出費を無理なく減らすコツ。固定費の見直しから買い物術まで。",
    },
    "seido": {
        "name": "制度・給付金",
        "emoji": "📋",
        "description": "知らないと損する公的制度や給付金。申請すればもらえるお金の情報。",
    },
    "hoken": {
        "name": "保険・住まい",
        "emoji": "🏠",
        "description": "保険の見直しと住まいの備え。払いすぎを防ぎ、これからに備える。",
    },
    "sagi": {
        "name": "詐欺対策",
        "emoji": "🛡️",
        "description": "還付金詐欺・電話詐欺の最新手口と対策。大切なお金を守るために。",
    },
    "souzoku": {
        "name": "相続・終活",
        "emoji": "📖",
        "description": "家族がもめないための相続準備とエンディングノート。今からできる備え。",
    },
}

DEFAULT_CATEGORY = "seido"


def category_list() -> list[dict]:
    """テンプレート用: slugを含む辞書のリスト"""
    return [{"slug": slug, **info} for slug, info in CATEGORIES.items()]
