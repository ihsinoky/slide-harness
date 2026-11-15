# 標準テンプレート

テンプレートが案件に指定されていない場合に使う標準テンプレート。仕様は `core/rendering.md`。

- 基づくデザインシステム：デジタル庁デザインシステム（DADS）のデザイントークン（キーカラー Blue-900 `#0017C1`、淡色 Blue-50/100、Noto Sans JP、行間170%）
- 形式：単一 HTML ファイル。16:9（1280×720 基準）、矢印キー／ボタンで移動、印刷時は全スライド縦並び
- 使い方：`template.html` を案件の `slides.html` の土台としてコピーし、`{{...}}` を置き換え、`.fig` 内の SVG に outline 指定の図を実際に描く
- 図の部品クラス（box／box-tint／box-gray／box-warn、lbl／sub、arrow／arrow-key）を SVG 内で使い回す
