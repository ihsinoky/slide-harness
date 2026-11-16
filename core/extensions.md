# 拡張（extensions）の仕組み

型とロールは、core を書き換えずに「拡張パッケージ」として追加できる。設計は AI-DLC v2 のプラグイン機構（manifest による宣言、厳密な加算、core 不変、無効化で素に戻る）を輸入したもの。

## 置き場と構成

拡張はリポジトリ直下の `extensions/<名前>/` に置く（core の外）。

```text
extensions/<name>/
  extension.json        # manifest（宣言）
  types/<slug>.md       # 型の定義＋型リード（1ファイルに統合）
  roles/<slug>.md       # ロールの定義
  designs/<slug>/       # デザイン（テンプレート一式）
    template.html
```

## manifest（extension.json）

```json
{
  "name": "record-archive",
  "version": "0.1.0",
  "description": "記録・参照型を追加する拡張",
  "provides": {
    "types": [{ "slug": "archive-record", "file": "types/archive-record.md", "status": "sample" }],
    "roles": []
  }
}
```

- `name` はディレクトリ名と一致させる。`core` と `aidlc` 系の名前は使わない
- `status` は `sample`（見本・未検証）／`trial`（試走中）／`verified`（試走で検証済み）のいずれか。`verified` への昇格は人間の承認による
- slug は型・ロールを通じた識別子。core の型 slug（recommendation / pitch / status / results / postmortem / explanation / framing）と衝突させない
- デザインは `provides.designs` に `{ "slug": "note", "file": "designs/note", "status": "sample" }` の形で宣言する

## デザイン（表現層）の契約

拡張が提供するデザインは、標準テンプレートと同じ契約を満たす `template.html` を含むこと（検証スクリプトが検査する）。

- CSS 変数のトークン一式（`--key`、`--ink`、`--ink-sub`、`--line`、`--paper`、`--reg`、`--font`）を `:root` で定義する。スライド本体の CSS と図の部品クラス（box／lbl／sub／arrow 等）はこのトークン経由で色と書体を受ける
- スライド寸法は 16:9（1280×720 基準）、印刷時は全スライド縦並び（`@media print` で操作 UI を消す）
- スライドショーと編集のビューア機能（標準テンプレートのスクリプトブロック）を含む
- デザインの切り替えで内容（タイトル・図・要点）は変えない。デザインは型・内容と直交する層である

デザインの解決順（`core/rendering.md`）：案件が指定した拡張デザイン → 案件固有テンプレート → リポジトリ共有 → 標準。案件がどのデザインを使ったか（拡張名と版を含む）を lint-report に記録する。

## デザインの取り込み（インポート）

既存の PowerPoint や参考 HTML スライドから、デザイントークンを取り込んで拡張デザインを生成できる。

```bash
python3 tools/import-design.py --from deck.pptx --name imported-corporate --slug corporate
python3 tools/import-design.py --from reference.html --name imported-web --slug web
```

- PowerPoint：テーマ（ppt/theme）の色スキーム（accent1 をキーカラー、dk1 を本文色、accent2 を規制色）と書体スキーム（見出し／本文）、スライド背景を抽出する
- HTML：`:root` の CSS 変数があればそのまま、無ければ色の出現頻度からキーカラーを推定する
- 生成物は標準テンプレートの骨格に抽出トークンを差し込んだ `template.html` と、出典・抽出値・限界を記録した `SOURCE.md`。manifest への登録まで自動で行い、status は `sample` で始まる
- **限界**：取り込むのは色・書体のトークンだけ。ロゴ、画像、図形の配置、スライドマスターの複雑なレイアウトは再現しない。書体は名前の取り込みのみでフォント自体は同梱しない。取り込んだデザインは人間が実物を見て確認してから status を上げる

## 型ファイルの必須部品

`types/<slug>.md` は次の見出しをすべて含むこと（検証スクリプトが検査する）。

- `## 定義`：読み手の仕事、典型構成、内容基準、特有の失敗（`core/deck-types.md` と同じ観点）
- `## ミッション`
- `## 観点`
- `## スコア基準`
- `## 典型構成と疑問チェーン`
- `## 型固有 lint`

新設の前提は主軸テストである：「この資料が成功したとき、読み手は具体的に何をした／何を持ち帰った状態になるか」が core の既存型と重ならないこと。重なる場合は新設ではなく、既存型の観点追加として扱う。

## ロールファイルの必須部品

`roles/<slug>.md` は次の見出しを含むこと。

- `## 担うフェーズ`
- `## 権限`
- `## 競合ルール`（既存ロールと意見が割れたときの扱い）

## 合成ルール

1. **厳密な加算のみ**。拡張は core の型・ロール・プロセスを上書きしない
2. **slug の衝突は合成エラー**。core または他の拡張と slug が衝突したら、黙って上書きせず停止して人間に上げる
3. **無効化はフォルダを外すだけ**。拡張を除けば、動作は素の core と一致する
4. **フェーズ0での扱い**：類型診断の候補は「core の型＋有効な拡張の型」。拡張の型を使った場合は、使用した拡張名・版・status を `type-diagnosis.md` に記録する。`sample`／`trial` の型を使うときは、その旨を G0 の提示に含める
5. **検証**：拡張を足したら `tools/validate-extensions.py` で構造を検査する（manifest の整合、必須部品の欠け、slug 衝突）。検査を通らない拡張は候補に入れない

## バインディング

- GitHub Copilot：拡張の型は `.github/agents/type-<slug>.agent.md` から参照できる（正は拡張側の型ファイル）。オーケストレータ（slide-flow）は開始時に `extensions/` を走査し、検証を通った拡張だけを候補に加える
- 他の実行環境でも同じ `extensions/` を読み、合成ルールは環境に依存しない
