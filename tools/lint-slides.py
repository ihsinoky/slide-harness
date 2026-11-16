#!/usr/bin/env python3
"""slide-harness 機械 lint（G2 の前提条件）。

使い方: python3 tools/lint-slides.py works/<案件>

判定できるものを機械で判定する層。エージェントの自己申告に依存しない。
検査内容:
  構造: slides.md と slides.html のスライド数・タイトルの一致、
        各スライドのキッカー／タイトル／要点の有無（このスクリプトで判定）
  幾何: SVG 内テキストの実寸（ヘッドレス Chrome で getBBox を実測）が、
        収まるべき四角（中心を含む最小の rect）と viewBox の内側にあるか。
        中心を含まない別の四角とテキストが重なっていないか
        （バッジ等の下に本文が潜る事故の検出）
Chrome の探索順: 環境変数 SLIDE_LINT_CHROME → PATH 上の
chrome-headless-shell / chromium / google-chrome → ローカルの既知パス。
終了コード: 0 = パス、1 = 不合格あり、2 = 実行環境の不備。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AUDIT_JS = """
window.addEventListener('load', () => {
  // スライドショーの表示制御（非表示スライド）で getBBox が 0 になるため、全枚を表示状態にしてから測る
  document.querySelectorAll('section.slide').forEach(s => {
    s.style.display = 'block'; s.style.position = 'static'; s.style.transform = 'none';
  });
  void document.body.offsetHeight;
  const out = [];
  document.querySelectorAll('section.slide').forEach((sec, si) => {
    const svg = sec.querySelector('svg'); if (!svg) return;
    const rects = [...svg.querySelectorAll('rect')].map(r => r.getBBox());
    svg.querySelectorAll('text').forEach(t => {
      const bb = t.getBBox(); const content = t.textContent.trim(); if (!content) return;
      const cx = bb.x + bb.width / 2, cy = bb.y + bb.height / 2;
      const containing = rects.filter(r => cx >= r.x - 1 && cx <= r.x + r.width + 1 && cy >= r.y - 2 && cy <= r.y + r.height + 2);
      if (containing.length) {
        const box = containing.reduce((a, b) => a.width * a.height <= b.width * b.height ? a : b);
        if (bb.x < box.x + 3 || bb.x + bb.width > box.x + box.width - 3)
          out.push(`${si + 1}枚目「${content.slice(0, 18)}」: テキストが四角をはみ出しています`);
      }
      for (const r of rects) {
        if (containing.includes(r)) continue;
        const ix = Math.min(bb.x + bb.width, r.x + r.width) - Math.max(bb.x, r.x);
        const iy = Math.min(bb.y + bb.height, r.y + r.height) - Math.max(bb.y, r.y);
        if (ix > 2 && iy > 2) { out.push(`${si + 1}枚目「${content.slice(0, 18)}」: テキストが別の四角と重なっています`); break; }
      }
      const vb = svg.viewBox.baseVal;
      if (bb.x < 0 || bb.x + bb.width > vb.width || bb.y < 0 || bb.y + bb.height > vb.height)
        out.push(`${si + 1}枚目「${content.slice(0, 18)}」: テキストが図の範囲（viewBox）をはみ出しています`);
    });
  });
  const pre = document.createElement('pre'); pre.id = '__lint_result';
  pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
});
"""


def find_chrome() -> str | None:
    env = os.environ.get("SLIDE_LINT_CHROME")
    if env and Path(env).is_file():
        return env
    for name in ("chrome-headless-shell", "chromium", "google-chrome", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    local = Path.home() / "workspace/tools/chrome/chrome-headless-shell-linux64/chrome-headless-shell"
    return str(local) if local.is_file() else None


def geometry_errors(html: str, chrome: str) -> list:
    audit = html.replace("</body>", f"<script>{AUDIT_JS}</script></body>")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(audit)
        tmp = f.name
    try:
        dom = subprocess.run(
            [chrome, "--no-sandbox", "--disable-gpu", "--virtual-time-budget=5000",
             "--dump-dom", f"file://{tmp}"],
            capture_output=True, text=True, timeout=120).stdout
    finally:
        Path(tmp).unlink(missing_ok=True)
    m = re.search(r'<pre id="__lint_result">(.*?)</pre>', dom, re.S)
    if not m:
        raise RuntimeError("監査スクリプトの結果が取得できませんでした")
    return json.loads(m.group(1).replace("&quot;", '"'))


def main() -> int:
    if len(sys.argv) != 2:
        print("使い方: python3 tools/lint-slides.py works/<案件>")
        return 2
    work = Path(sys.argv[1])
    html_path, md_path = work / "slides.html", work / "slides.md"
    for p in (html_path, md_path):
        if not p.is_file():
            print(f"機械 lint エラー: {p} がありません")
            return 1
    html = html_path.read_text(encoding="utf-8")
    md = md_path.read_text(encoding="utf-8")
    errors = []
    sections = re.findall(r'<section class="slide">(.*?)</section>', html, re.S)
    md_titles = re.findall(r"^## \d+\.\s*(.+)$", md, re.M)
    if len(sections) != len(md_titles):
        errors.append(f"構造: スライド数が一致しません（html {len(sections)} / md {len(md_titles)}）")
    for i, sec in enumerate(sections, 1):
        h1 = re.search(r"<h1>(.*?)</h1>", sec, re.S)
        title = re.sub(r"\s+", " ", h1.group(1)).strip() if h1 else ""
        if i <= len(md_titles) and title != md_titles[i - 1].strip():
            errors.append(f"構造: {i}枚目のタイトルが slides.md と一致しません")
        if 'class="kicker"' not in sec:
            errors.append(f"構造: {i}枚目にキッカーがありません")
        if 'class="takeaway"' not in sec:
            errors.append(f"構造: {i}枚目に要点（takeaway）がありません")
    chrome = find_chrome()
    if not chrome:
        print("機械 lint エラー: ヘッドレス Chrome が見つかりません"
              "（SLIDE_LINT_CHROME でパスを指定できます）。幾何検査なしに G2 はパスできません")
        return 2
    try:
        errors += geometry_errors(html, chrome)
    except Exception as e:
        print(f"機械 lint エラー: 幾何検査に失敗しました（{e}）")
        return 2
    if errors:
        print(f"機械 lint 不合格（{work}）:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"機械 lint パス（{work}）: {len(sections)}枚、構造と幾何に問題なし")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
