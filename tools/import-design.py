#!/usr/bin/env python3
"""参考スライド（PowerPoint / HTML）からデザイントークンを取り込み、
拡張のデザインパッケージ（extensions/<name>/designs/<slug>/）を生成する。

使い方:
  python3 tools/import-design.py --from deck.pptx --name imported-corporate --slug corporate
  python3 tools/import-design.py --from reference.html --name imported-web --slug web

取り込むのはデザインのトークン（キーカラー、本文色、背景、補助色、罫線、書体）だけ。
ロゴ・画像・複雑なレイアウトは再現しない（SOURCE.md に取り込み内容と限界を記録する）。
生成後は tools/validate-extensions.py で検証すること。
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}


def blend(hexcolor: str, other: str, ratio: float) -> str:
    def rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    a, b = rgb(hexcolor), rgb(other)
    out = tuple(round(a[i] * (1 - ratio) + b[i] * ratio) for i in range(3))
    return "#{:02X}{:02X}{:02X}".format(*out)


def extract_pptx(path: Path) -> dict:
    tokens, notes = {}, []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        theme_name = next((n for n in names if n.startswith("ppt/theme/theme")), None)
        if not theme_name:
            raise SystemExit("テーマ（ppt/theme/*.xml）が見つかりません")
        theme = ET.fromstring(z.read(theme_name))
        scheme = theme.find(".//a:clrScheme", NS)
        colors = {}
        if scheme is not None:
            for child in scheme:
                tag = child.tag.split("}")[-1]
                srgb = child.find("a:srgbClr", NS)
                sysclr = child.find("a:sysClr", NS)
                if srgb is not None:
                    colors[tag] = "#" + srgb.get("val")
                elif sysclr is not None and sysclr.get("lastClr"):
                    colors[tag] = "#" + sysclr.get("lastClr")
        fonts = theme.find(".//a:fontScheme", NS)
        major = minor = ""
        if fonts is not None:
            for part, key in (("majorFont", "major"), ("minorFont", "minor")):
                node = fonts.find(f"a:{part}", NS)
                if node is not None:
                    latin = node.find("a:latin", NS)
                    ea = node.find("a:ea", NS)
                    name = (ea.get("typeface") if ea is not None and ea.get("typeface")
                            else latin.get("typeface") if latin is not None else "")
                    if key == "major":
                        major = name
                    else:
                        minor = name
        bg = None
        for cand in ("ppt/slides/slide1.xml",):
            if cand in names:
                slide = ET.fromstring(z.read(cand))
                bgclr = slide.find(".//p:bg//a:srgbClr", NS)
                if bgclr is not None:
                    bg = "#" + bgclr.get("val")
    key = colors.get("accent1", "#0F62FE")
    ink = colors.get("dk1", "#161616")
    paper = bg or colors.get("lt1", "#FFFFFF")
    tokens = {
        "--key": key,
        "--key-dark": blend(key, "#000000", 0.25),
        "--tint": blend(key, "#FFFFFF", 0.92),
        "--tint2": blend(key, "#FFFFFF", 0.82),
        "--ink": ink,
        "--ink-sub": colors.get("dk2", blend(ink, "#FFFFFF", 0.45)),
        "--line": blend(ink, "#FFFFFF", 0.65),
        "--paper": paper,
        "--warn": "#B3261E",
        "--focus": "#FFD43D",
        "--reg": colors.get("accent2", "#6929C4"),
        "--font": f'"{major or minor or "Noto Sans JP"}","{minor or "Noto Sans JP"}","Noto Sans JP",sans-serif',
    }
    notes.append(f"テーマ色: {colors}")
    notes.append(f"見出し書体: {major or '（なし）'} / 本文書体: {minor or '（なし）'}")
    return tokens, notes


def extract_html(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    tokens, notes = {}, []
    root = re.search(r":root\s*\{(.*?)\}", text, re.S)
    if root:
        for var in ("--key", "--key-dark", "--tint", "--tint2", "--ink",
                    "--ink-sub", "--line", "--paper", "--warn", "--focus", "--reg", "--font"):
            m = re.search(re.escape(var) + r"\s*:\s*([^;]+);", root.group(1))
            if m:
                tokens[var] = m.group(1).strip()
        notes.append(":root の CSS 変数をそのまま取り込んだ")
    if "--key" not in tokens:
        hexes = re.findall(r"#[0-9A-Fa-f]{6}\b", text)
        freq = {}
        for h in hexes:
            freq[h.upper()] = freq.get(h.upper(), 0) + 1
        ranked = sorted(freq.items(), key=lambda kv: -kv[1])
        notes.append(f"CSS 変数が無いため色の出現頻度から推定した: {ranked[:6]}")
        if ranked:
            key = ranked[0][0]
            tokens.update({
                "--key": key, "--key-dark": blend(key, "#000000", 0.25),
                "--tint": blend(key, "#FFFFFF", 0.92), "--tint2": blend(key, "#FFFFFF", 0.82),
                "--ink": "#161616", "--ink-sub": "#525252", "--line": "#8D8D8D",
                "--paper": "#FFFFFF", "--warn": "#B3261E", "--focus": "#FFD43D",
                "--reg": "#6929C4", "--font": '"Noto Sans JP",sans-serif',
            })
        fm = re.search(r"font-family\s*:\s*([^;]+);", text)
        if fm:
            tokens["--font"] = fm.group(1).strip()
    return tokens, notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--name", required=True, help="拡張名（extensions/<name>）")
    ap.add_argument("--slug", required=True, help="デザインの slug")
    ap.add_argument("--base", default="templates/standard/template.html")
    ap.add_argument("--root", default="extensions")
    args = ap.parse_args()

    src = Path(args.src)
    if src.suffix.lower() == ".pptx":
        tokens, notes = extract_pptx(src)
    elif src.suffix.lower() in (".html", ".htm"):
        tokens, notes = extract_html(src)
    else:
        raise SystemExit("対応形式は .pptx / .html です")

    base = Path(args.base).read_text(encoding="utf-8")
    out = base
    for var, val in tokens.items():
        out = re.sub(re.escape(var) + r"\s*:[^;]+;", f"{var}:{val};", out, count=1)
    header = (f"/* 取り込みデザイン: {args.name}/{args.slug}\n"
              f"   出典: {src.name}（tools/import-design.py でトークンを抽出）\n"
              f"   ロゴ・画像・レイアウトは再現していない。詳細は SOURCE.md */\n")
    out = out.replace("<style>\n", "<style>\n" + header, 1)

    ext_dir = Path(args.root) / args.name
    design_dir = ext_dir / "designs" / args.slug
    design_dir.mkdir(parents=True, exist_ok=True)
    (design_dir / "template.html").write_text(out, encoding="utf-8")
    (design_dir / "SOURCE.md").write_text(
        f"# 取り込み記録 — {args.name}/{args.slug}\n\n"
        f"- 出典ファイル: `{src}`\n"
        f"- 取り込んだトークン:\n" +
        "".join(f"  - `{k}`: {v}\n" for k, v in sorted(tokens.items())) +
        f"- 抽出メモ:\n" + "".join(f"  - {n}\n" for n in notes) +
        "\n## 限界\n"
        "- 取り込むのは色・書体のトークンだけ。ロゴ、画像、図形の配置、スライドマスターの複雑なレイアウトは再現しない\n"
        "- 書体は名前の取り込みのみで、フォント自体は同梱しない（読み手の環境に無い書体はフォールバックする）\n"
        "- status は sample から始める。人間が実物を見て確認してから trial / verified に上げる\n",
        encoding="utf-8")

    manifest_path = ext_dir / "extension.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"name": args.name, "version": "0.1.0",
                    "description": f"{src.name} から取り込んだデザインを含む拡張",
                    "provides": {"types": [], "roles": [], "designs": []}}
    designs = manifest.setdefault("provides", {}).setdefault("designs", [])
    if not any(d.get("slug") == args.slug for d in designs):
        designs.append({"slug": args.slug, "file": f"designs/{args.slug}", "status": "sample"})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"生成: {design_dir}/template.html")
    print("トークン:")
    for k, v in sorted(tokens.items()):
        print(f"  {k}: {v}")
    print("次に: python3 tools/validate-extensions.py extensions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
