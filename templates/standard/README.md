# 標準テンプレート（IBM Carbon）

標準テンプレートは IBM Carbon Design System のデザイントークンに基づく（2026-11-16 に6標準の比較レンダリングを経て採用。前標準の DADS 版は `templates/dads/` に案件用として残置）。

- キーカラー：Blue 60 `#0F62FE`、淡色 Blue 10 `#EDF5FF`、本文 Gray 100 `#161616`、補助 Gray 70 `#525252`、罫線 Gray 50 `#8D8D8D`
- 書体：IBM Plex Sans JP（フォールバック付き）。角は Carbon の流儀で基本直角（要点バー等）
- 形式：単一 HTML ファイル。16:9（1280×720 基準）、矢印キー／ボタンで移動、印刷時は全スライド縦並び
- 使い方：`template.html` を案件の `slides.html` の土台としてコピーし、`{{...}}` を置き換え、`.fig` 内の SVG に outline 指定の図を実際に描く
