"""スライド画像の生成と ffmpeg による動画組み立て"""
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 配色 (紺ベース + 金アクセント: シニア向けに高コントラスト)
BG_TOP = (13, 22, 54)
BG_BOTTOM = (28, 44, 96)
GOLD = (240, 196, 82)
WHITE = (255, 255, 255)
STROKE = (8, 12, 30)


def _gradient_bg(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / h
        color = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = color
    return img


NO_LINE_START = "、。!?%」』)ゃゅょっぁぃぅぇぉー"
NO_LINE_END = "「『("


def _wrap(text: str, chars_per_line: int) -> list[str]:
    """日本語向け折り返し。行間で文字数を均等に配分し、禁則処理を行う"""
    import math

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


def _fit_text(text: str, max_width: int, font_path: str) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """テキストが収まる最大フォントサイズと折り返し行を決める"""
    for size in range(120, 56, -8):
        chars = max(4, max_width // size)
        lines = _wrap(text, chars)
        if len(lines) <= 6:
            return ImageFont.truetype(font_path, size), lines
    return ImageFont.truetype(font_path, 56), _wrap(text, max(4, max_width // 56))


def render_slide(
    caption: str,
    index: int,
    total: int,
    cfg: dict,
    out_path: Path,
    is_last: bool = False,
) -> Path:
    vc = cfg["video"]
    w, h = vc["width"], vc["height"]
    font_path = vc["font"]

    img = _gradient_bg(w, h)
    draw = ImageDraw.Draw(img)

    # 上部: チャンネルラベル (金色の帯)
    label = vc.get("channel_label", "")
    if label:
        label_font = ImageFont.truetype(font_path, 44)
        bbox = draw.textbbox((0, 0), label, font=label_font)
        lw = bbox[2] - bbox[0]
        pad = 28
        bx0 = (w - lw) / 2 - pad
        by0 = 180
        draw.rounded_rectangle(
            [bx0, by0, bx0 + lw + pad * 2, by0 + 44 + pad * 1.4], radius=18, fill=GOLD
        )
        draw.text(((w - lw) / 2, by0 + pad * 0.7), label, font=label_font, fill=STROKE)

    # 中央: メインキャプション (自動サイズ・折り返し・縁取り)
    font, lines = _fit_text(caption, w - 160, font_path)
    line_h = int(font.size * 1.45)
    total_h = line_h * len(lines)
    y = (h - total_h) / 2 - 60
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        draw.text(
            ((w - lw) / 2, y),
            line,
            font=font,
            fill=GOLD if is_last else WHITE,
            stroke_width=8,
            stroke_fill=STROKE,
        )
        y += line_h

    # 下部: 進行ドット
    dot_r = 14
    gap = 52
    start_x = (w - gap * (total - 1)) / 2
    dy = h - 320
    for i in range(total):
        cx = start_x + gap * i
        color = GOLD if i <= index else (70, 82, 130)
        draw.ellipse([cx - dot_r, dy - dot_r, cx + dot_r, dy + dot_r], fill=color)

    # 最終スライド: 誘導文
    if is_last:
        cta_font = ImageFont.truetype(font_path, 52)
        cta = "▼ 概要欄にリンクがあります ▼"
        bbox = draw.textbbox((0, 0), cta, font=cta_font)
        draw.text(
            ((w - (bbox[2] - bbox[0])) / 2, dy - 200),
            cta,
            font=cta_font,
            fill=WHITE,
            stroke_width=6,
            stroke_fill=STROKE,
        )

    img.save(out_path)
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
    fps = cfg["video"]["fps"]
    segments = []
    total_dur = 0.0

    for i in range(scene_count):
        slide = work_dir / f"slide_{i}.png"
        audio = work_dir / f"scene_{i}.wav"
        seg = work_dir / f"seg_{i}.mp4"
        dur = _wav_duration(audio) + 0.35  # シーン間の間
        total_dur += dur
        fade_out = max(dur - 0.25, 0)
        _run_ffmpeg(
            [
                "-loop", "1", "-framerate", str(fps), "-i", str(slide),
                "-i", str(audio),
                "-t", f"{dur:.3f}",
                "-vf", f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.3f}:d=0.25,format=yuv420p",
                "-af", "apad",
                "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage",
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
