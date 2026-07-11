"""スライド画像の生成と ffmpeg による動画組み立て

デザイン方針(50代以上向け):
- 紺×金の高コントラスト。数字は金色でハイライトして目を引く
- 文字はソフトシャドウ+縁取りで、小さい画面でもくっきり
- ゆっくりしたズーム(Ken Burns)で静止画でも動きを出す
- スライドは1.25倍で描画し、ズームしてもシャープさを保つ
"""
import math
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---- 配色 ----
BG_TOP = (11, 21, 51)
BG_BOTTOM = (30, 49, 97)
GLOW = (52, 78, 140)
GOLD = (240, 196, 82)
GOLD_DEEP = (201, 162, 39)
WHITE = (255, 255, 255)
STROKE = (8, 12, 26)
MUTED = (150, 165, 205)
TRACK = (44, 58, 100)

SUPERSAMPLE = 1.25  # 描画倍率(ズーム時の劣化防止)
ZOOM_MAX = 1.08     # 1シーンでのズーム到達倍率

NO_LINE_START = "、。!?%」』)ゃゅょっぁぃぅぇぉー"
NO_LINE_END = "「『("

# 金色にする文字: 数字と、数字に続く単位
UNIT_CHARS = "%%円万歳倍割秒分年月日人回つ台"


def _wrap(text: str, chars_per_line: int) -> list[str]:
    """日本語向け折り返し。行間で文字数を均等に配分し、禁則処理を行う"""
    text = text.strip()
    if len(text) <= chars_per_line:
        return [text]

    n_lines = math.ceil(len(text) / chars_per_line)
    target = math.ceil(len(text) / n_lines)

    lines = []
    rest = text
    while rest:
        if len(rest) <= target + 1:
            lines.append(rest)
            break
        cut = target
        # 読点・句点の直後で切れるならそこを優先(前後2文字以内で探す)
        for offset in (0, -1, 1, -2, 2):
            p = cut + offset
            if 1 <= p < len(rest) and rest[p - 1] in "、。":
                cut = p
                break
        else:
            # 英数字の連続(84%等)の途中で切らない
            while 1 < cut < len(rest) and rest[cut - 1].isascii() and rest[cut].isascii():
                cut -= 1
            # 禁則: 次の行頭に来てはいけない文字は前の行に含める
            while cut < len(rest) and rest[cut] in NO_LINE_START:
                cut += 1
            # 禁則: 行末に開き括弧を残さない
            while cut > 1 and rest[cut - 1] in NO_LINE_END:
                cut -= 1
        lines.append(rest[:cut])
        rest = rest[cut:]
    return [l for l in lines if l]


def _fit_text(
    text: str, max_width: int, font_path: str, size_max: int, size_min: int
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """テキストが収まる最大フォントサイズと折り返し行を決める"""
    step = max(4, (size_max - size_min) // 8)
    for size in range(size_max, size_min, -step):
        chars = max(4, max_width // size)
        lines = _wrap(text, chars)
        if len(lines) <= 5:
            return ImageFont.truetype(font_path, size), lines
    return ImageFont.truetype(font_path, size_min), _wrap(text, max(4, max_width // size_min))


def _char_colors(line: str, base_color: tuple) -> list[tuple]:
    """数字とそれに続く単位を金色にする"""
    colors = []
    prev_digit = False
    for ch in line:
        if ch.isdigit() or ch in ".,":
            colors.append(GOLD)
            prev_digit = ch.isdigit()
        elif prev_digit and ch in UNIT_CHARS:
            colors.append(GOLD)
            prev_digit = False
        else:
            colors.append(base_color)
            prev_digit = False
    return colors


def _radial_glow(size: int, peak_alpha: int) -> Image.Image:
    """中心が明るい円形グラデーションのアルファマスク"""
    small = 128
    mask = Image.new("L", (small, small), 0)
    px = mask.load()
    c = small / 2
    for y in range(small):
        for x in range(small):
            d = math.hypot(x - c, y - c) / c
            px[x, y] = int(peak_alpha * max(0.0, 1.0 - d) ** 1.6)
    return mask.resize((size, size), Image.BILINEAR)


def render_slide(
    caption: str,
    index: int,
    total: int,
    cfg: dict,
    out_path: Path,
    is_last: bool = False,
) -> Path:
    vc = cfg["video"]
    S = SUPERSAMPLE
    px = lambda v: int(v * S)
    w, h = px(vc["width"]), px(vc["height"])
    font_path = vc["font"]

    # ---- 背景: 縦グラデーション ----
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line(
            [(0, y), (w, y)],
            fill=tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)),
        )

    # ---- 中央の光彩(文字周りを少し明るく)----
    glow_size = px(1500)
    glow = Image.new("RGB", (glow_size, glow_size), GLOW)
    img.paste(glow, (int(w / 2 - glow_size / 2), int(h * 0.42 - glow_size / 2)),
              _radial_glow(glow_size, 110))

    # ---- 装飾(輪・円)と飾り枠 ----
    deco = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    # 右上の金の輪
    cx, cy, r = px(1010), px(190), px(240)
    dd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*GOLD, 42), width=px(3))
    r2 = px(165)
    dd.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=(*GOLD, 26), width=px(2))
    # 左下の淡い円
    cx, cy, r = px(45), px(1680), px(330)
    dd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*GOLD, 14))
    # 飾り枠(角丸の細い金線)
    m = px(34)
    dd.rounded_rectangle([m, m, w - m, h - m], radius=px(30),
                         outline=(*GOLD_DEEP, 130), width=px(2))
    img = Image.alpha_composite(img.convert("RGBA"), deco)
    draw = ImageDraw.Draw(img)

    # ---- 上部: チャンネルラベルのピル ----
    label = vc.get("channel_label", "")
    if label:
        f_label = ImageFont.truetype(font_path, px(42))
        lw = draw.textlength(label, font=f_label)
        pad_x, pad_y = px(30), px(16)
        bx = (w - lw) / 2 - pad_x
        by = px(140)
        bh = px(42) + pad_y * 2
        draw.rounded_rectangle(
            [bx, by, bx + lw + pad_x * 2, by + bh], radius=bh / 2, fill=GOLD
        )
        draw.text(((w - lw) / 2, by + pad_y - px(3)), label, font=f_label, fill=STROKE)

    # ---- 右上: シーン番号 ----
    f_counter = ImageFont.truetype(font_path, px(34))
    counter = f"{index + 1}/{total}"
    tw = draw.textlength(counter, font=f_counter)
    draw.text((w - m - px(28) - tw, m + px(20)), counter, font=f_counter, fill=MUTED)

    # ---- 中央: キャプション ----
    base_color = GOLD if is_last else WHITE
    font, lines = _fit_text(caption, w - px(190), font_path, px(108), px(58))
    line_h = int(font.size * 1.5)
    block_h = line_h * len(lines)
    y0 = (h - block_h) / 2 - px(70)

    # 金の飾りライン(キャプションの上)
    lw_deco = px(110)
    draw.rounded_rectangle(
        [(w - lw_deco) / 2, y0 - px(64), (w + lw_deco) / 2, y0 - px(56)],
        radius=px(4), fill=GOLD_DEEP,
    )

    # ソフトシャドウ(ぼかした黒文字を下に敷く)
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    y = y0
    for line in lines:
        lw = draw.textlength(line, font=font)
        sd.text(((w - lw) / 2 + px(4), y + px(10)), line, font=font, fill=(0, 0, 0, 160))
        y += line_h
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(px(9))))
    draw = ImageDraw.Draw(img)

    # 本文字(1文字ずつ描いて数字を金色に)
    y = y0
    for line in lines:
        lw = draw.textlength(line, font=font)
        x = (w - lw) / 2
        for ch, color in zip(line, _char_colors(line, base_color)):
            draw.text((x, y), ch, font=font, fill=color,
                      stroke_width=px(5), stroke_fill=STROKE)
            x += draw.textlength(ch, font=font)
        y += line_h

    # ---- 最終スライド: CTAパネル ----
    if is_last:
        cta = "▼ 概要欄にリンクがあります"
        f_cta = ImageFont.truetype(font_path, px(46))
        tw = draw.textlength(cta, font=f_cta)
        pw, ph = tw + px(90), px(120)
        bx, by = (w - pw) / 2, h - px(560)
        draw.rounded_rectangle([bx, by, bx + pw, by + ph], radius=px(24),
                               fill=(16, 26, 58), outline=GOLD, width=px(3))
        draw.text(((w - tw) / 2, by + (ph - px(46)) / 2 - px(4)), cta,
                  font=f_cta, fill=WHITE)

    # ---- 下部: 進行バー ----
    bar_w, bar_h = px(560), px(10)
    bx, by = (w - bar_w) / 2, h - px(300)
    draw.rounded_rectangle([bx, by, bx + bar_w, by + bar_h], radius=bar_h / 2, fill=TRACK)
    fill_w = bar_w * (index + 1) / total
    draw.rounded_rectangle([bx, by, bx + max(fill_w, bar_h), by + bar_h],
                           radius=bar_h / 2, fill=GOLD)

    img.convert("RGB").save(out_path)
    return out_path


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error"] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg エラー:\n{result.stderr}")


def build_video(work_dir: Path, scene_count: int, cfg: dict, out_path: Path) -> float:
    """work_dir 内の slide_N.png / scene_N.wav から縦動画を組み立てる。総尺(秒)を返す"""
    vc = cfg["video"]
    fps = vc["fps"]
    width, height = vc["width"], vc["height"]
    segments = []
    total_dur = 0.0

    for i in range(scene_count):
        slide = work_dir / f"slide_{i}.png"
        audio = work_dir / f"scene_{i}.wav"
        seg = work_dir / f"seg_{i}.mp4"
        dur = _wav_duration(audio) + 0.35  # シーン間の間
        total_dur += dur
        frames = max(int(round(dur * fps)), 1)
        zoom_inc = (ZOOM_MAX - 1.0) / frames
        fade_out = max(dur - 0.25, 0)
        vf = (
            f"zoompan=z='min(zoom+{zoom_inc:.6f},{ZOOM_MAX})'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={width}x{height}:fps={fps},"
            f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.3f}:d=0.25,"
            f"format=yuv420p"
        )
        _run_ffmpeg(
            [
                "-loop", "1", "-i", str(slide),
                "-i", str(audio),
                "-t", f"{dur:.3f}",
                "-vf", vf,
                "-af", "apad",
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                str(seg),
            ]
        )
        segments.append(seg)

    concat_list = work_dir / "concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{s.as_posix()}'" for s in segments), encoding="utf-8"
    )
    _run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(out_path)]
    )
    return total_dur
