#!/usr/bin/env python3
"""slide-harness 拡張の構造検証。

使い方: python3 tools/validate-extensions.py [extensions-dir]
検査内容: manifest の整合（name とディレクトリ名、file の実在）、
型ファイルの必須見出し、ロールファイルの必須見出し、slug の衝突
（core の型 slug、および拡張同士）。
"""
import json
import sys
from pathlib import Path

CORE_TYPE_SLUGS = {
    "recommendation", "pitch", "status", "results",
    "postmortem", "explanation", "framing",
}
TYPE_HEADINGS = ["## 定義", "## ミッション", "## 観点", "## スコア基準",
                 "## 典型構成と疑問チェーン", "## 型固有 lint"]
ROLE_HEADINGS = ["## 担うフェーズ", "## 権限", "## 競合ルール"]
STATUSES = {"sample", "trial", "verified"}


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("extensions")
    if not root.is_dir():
        print(f"拡張ディレクトリがありません: {root}")
        return 1
    errors = []
    seen_slugs = {}
    ext_dirs = sorted(p for p in root.iterdir() if p.is_dir())
    if not ext_dirs:
        print("拡張はまだありません（検証対象なし）")
        return 0
    for ext in ext_dirs:
        manifest_path = ext / "extension.json"
        if not manifest_path.is_file():
            errors.append(f"{ext.name}: extension.json がありません")
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{ext.name}: extension.json が不正な JSON です（{e}）")
            continue
        if manifest.get("name") != ext.name:
            errors.append(f"{ext.name}: manifest の name がディレクトリ名と一致しません")
        provides = manifest.get("provides", {})
        for item in provides.get("designs", []):
            slug = item.get("slug", "")
            rel = item.get("file", "")
            target = ext / rel / "template.html"
            where = f"{ext.name}/{rel}"
            if slug in seen_slugs:
                errors.append(f"{where}: slug '{slug}' が {seen_slugs[slug]} と重複しています")
            seen_slugs[slug] = where
            if item.get("status") not in STATUSES:
                errors.append(f"{where}: status は sample / trial / verified のいずれかです")
            if not target.is_file():
                errors.append(f"{where}: template.html がありません")
                continue
            text = target.read_text(encoding="utf-8")
            for marker in ("--key:", "--ink:", "--paper:", "--font:",
                           "@media print", "tb-edit", ".slide"):
                if marker not in text:
                    errors.append(f"{where}: デザイン契約の要素 '{marker}' がありません")
        for kind, headings in (("types", TYPE_HEADINGS), ("roles", ROLE_HEADINGS)):
            for item in provides.get(kind, []):
                slug = item.get("slug", "")
                rel = item.get("file", "")
                target = ext / rel
                where = f"{ext.name}/{rel}"
                if slug in CORE_TYPE_SLUGS:
                    errors.append(f"{where}: slug '{slug}' が core の型と衝突しています")
                if slug in seen_slugs:
                    errors.append(f"{where}: slug '{slug}' が {seen_slugs[slug]} と重複しています")
                seen_slugs[slug] = where
                if kind == "types" and item.get("status") not in STATUSES:
                    errors.append(f"{where}: status は sample / trial / verified のいずれかです")
                if not target.is_file():
                    errors.append(f"{where}: ファイルがありません")
                    continue
                text = target.read_text(encoding="utf-8")
                for h in headings:
                    if h not in text:
                        errors.append(f"{where}: 必須見出し '{h}' がありません")
        print(f"検査: {ext.name} v{manifest.get('version', '?')} "
              f"(型 {len(provides.get('types', []))} / ロール {len(provides.get('roles', []))} "
              f"/ デザイン {len(provides.get('designs', []))})")
    if errors:
        print("\n合成エラー:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\n検証 OK：すべての拡張が合成可能です")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
