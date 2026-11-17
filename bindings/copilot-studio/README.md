# Copilot Studio への組み込み手順

slide-harness の構成を、Microsoft Copilot Studio のエージェントとして組み込む手順。
定義の正は GitHub 側の `core/` に置いたままにし、Studio 側はその写しとして運用する（別々に作らない）。

前提の調査は 2026-11-17、Microsoft Learn と Microsoft の Copilot Studio ブログで確認した。
Copilot Studio には3つのハーネスがあり、エージェント作成時に選び、後から変更できない。

## 方針：GitHub Copilot ハーネスで作る

Copilot Studio の **GitHub Copilot ハーネス**（旧称のまま呼ばれることがある。Copilot Studio の機能であり、GitHub Copilot サービスとは別物）を選ぶ。理由は対応の直接さである。

- **Skills** がネイティブに使える。core の部品をスキル（再利用できる指示のまとまり、Markdown で書き出せる）として、そのままの形で持ち込める
- **Hooks** がある。セッション開始時やツール実行前などのライフサイクル時点でワークフローを差し込め、ツール呼び出しを deny できる。GitHub 側の pre-commit フックに相当する強制の置き場になる
- ファイルの作成・編集がネイティブで、完成形 HTML の生成と保存が会話の中で完結する
- トピックは無く、自然言語の指示とスキルとツールで構成する。slide-flow エージェント定義の考え方と一致する

標準ハーネスでは agentic なスキルは使えず（Microsoft Learn 明記）、トピックとエージェントフローへの分解が必要になる。分解表は末尾に置くが、推奨はしない。

注意（2026-11-17 時点）：
- Hooks はパブリックプレビュー（`copilotstudio.preview.microsoft.com` で有効化）。現在のランタイムは **fail-open**（フックがエラーやタイムアウトになると、既定の動作で続行する）。つまりフック単独では G2 の強制はベストエフォートであり、手順9の二重化が要る
- 課金は Copilot Credits の従量で、作成・テスト・評価も消費する。M365 Copilot ライセンスではカバーされない
- オーケストレーションは設定できない。ゲートの厳密さは、指示とフックとツールの設計で担保する

## 対応表（slide-harness → Copilot Studio）

| slide-harness の部品 | Studio での置き場 | 備考 |
|---|---|---|
| `core/process.md`（大原則・ゲート） | エージェントの Instructions（要約）＋スキル `slide-process`（全文） | 指示には要約だけを入れ、全文はスキル側に置く |
| 型リード7本（`core/type-leads/`） | スキル ×7（`slide-type-recommendation` など） | 1型＝1スキル。ミッション／観点／スコア基準／疑問チェーン／型固有 lint をそのまま写す |
| `core/deck-types.md` | スキル `slide-process` 内の型一覧、または Knowledge | 型の診断はフェーズ0のスキル実行として行う |
| `core/anti-slop-checklist.md` | スキル `slide-lint` | フェーズ2で明示的に呼ばせる |
| `core/review-feedback.md`（指摘ナレッジ） | スキル `slide-lint` に含める＋Knowledge | 蓄積の更新は GitHub 側で行い、写しを同期する（手順10） |
| `core/rendering.md`＋標準テンプレート | スキル `slide-render`＋Knowledge（テンプレート HTML） | 完成形はエージェントのファイル作成で出力する |
| `core/conventions.md`・`core/extensions.md` | Instructions の要約＋Knowledge | 規約の追加は拡張だけ、の規則は指示に明記する |
| 拡張（`extensions/`） | スキルの追加＋Knowledge のファイル追加 | 検証は手順8のチェックを通してから登録する |
| ゲート G0／G1／G3（人間の承認） | 会話での提示と承認＋ワークフロー（承認の記録） | 提示は全体を出す。承認なしに次へ進まないことを指示に明記 |
| 機械 lint（`tools/lint-slides.py`） | MCP ツール `lint_slides`（手順7） | 終了コードと出力を返し、パスなしでは G2 を成立させない |
| pre-commit フック | Hook（ツール実行前に lint 結果を確認し、未実施なら保存を deny） | プレビューかつ fail-open のため、手順9の二重化とセット |
| 案件フォルダ（`works/<案件>/`） | SharePoint ライブラリのフォルダ | intent／outline／slides／lint-report を同じ構成で残す |
| 型診断・優先順位マップ等の成果物 | エージェントがファイルとして作成し、案件フォルダへ保存 | 会話の中だけで完結させない |

## 手順

### 0. 前提を確認する
- Copilot Studio の環境と、Copilot Credits の残量・課金先を確認する（作成とテストでも消費する）
- Hooks を使うため、プレビュー環境（`copilotstudio.preview.microsoft.com`）で対象環境にフックが提供されているか確認する
- 案件フォルダ用の SharePoint サイト（ライブラリ）を用意する

### 1. エージェントを作成する（ハーネス選択）
- Copilot Studio で新規エージェントを作成し、ハーネスに **GitHub Copilot ハーネス** を選ぶ（後から変更できない。ここが実質のスコープ決定）
- 名前は `slide-harness`、説明には「AI のスライド生成を、構造化された・検証可能な資料づくりのワークフローで進めるエージェント」と書く

### 2. Instructions に要約を入れる
エージェントの指示には、`core/process.md` の要約だけを入れる。全文はスキルに置き、指示からは「フェーズに入る前に該当スキルを読む」形にする。開始文の案：

```
あなたは slide-harness のオーケストレータです。スライド資料の作成を、意図（フェーズ0）→構成（フェーズ1）→生成（フェーズ2）→検証（フェーズ3）の順に進めます。
・型（主型1つ＋副型最大1つ）はフェーズ0で推定し、スキル slide-process の手順で人間に確認して確定します。型の名前を人間に判断させません
・承認ゲートは G0（意図・型・優先順位マップ）、G1（タイトル目次）、G3（最終）です。提示は差分ではなく全体を出し、承認なしに次のフェーズへ進みません。G2 は lint の全層パスが条件です
・生成と検査は分けます。作った内容を自分で採点しません。フェーズ2の終わりにスキル slide-lint を実行し、機械 lint ツール lint_slides の結果（終了コード）を記録します。機械 lint が不合格の間は G2 をパスとして扱いません
・1スライド＝1メッセージで、タイトルは主張文にします。図の形を先に選び、文章は図ごとの要点1行にします
・成果物（intent、type-diagnosis、priority-map、outline、slides、lint-report、検証メモ）は案件フォルダにファイルとして残します
・人間の指摘を受けたら、個別修正に加えて、パターン化して台帳への追加案を提示します
```

### 3. スキルを作成する
Build 画面からスキルを追加し、`core/` の部品を次の単位で写す。スキルは Markdown で書き出せるため、GitHub 側のファイルを正として生成・更新する運用にする。

| スキル名 | 元にする core | 役割 |
|---|---|---|
| `slide-process` | `process.md`＋`deck-types.md` | フェーズとゲート、型診断の手順 |
| `slide-type-<slug>` ×7 | `type-leads/01〜07` | 型ごとの観点・構成・型固有 lint |
| `slide-lint` | `anti-slop-checklist.md`＋`review-feedback.md` | 内容の検査と、指摘パターンの先回り確認 |
| `slide-render` | `rendering.md`＋`figure-forms.md` | 完成形 HTML の生成と視覚の確認 |

### 4. Knowledge を登録する
- `templates/standard/template.html` と、採用する拡張のファイルを Knowledge に登録する（アップロード、または SharePoint／OneDrive の同期フォルダ）
- Knowledge は事実と素材の置き場であり、指示の置き場ではない。指示系は必ず Instructions とスキルに置く

### 5. 案件フォルダを SharePoint に作る
- ライブラリに `works/` 相当のフォルダを作り、案件ごとにサブフォルダを切る運用を指示に含める
- エージェントのファイル作成で、成果物をそこへ保存させる

### 6. ゲートを会話とワークフローで実装する
- G0／G1／G3 は、エージェントが全体を提示し、人間が承認して初めて進む。これは指示（手順2）で担保する
- 承認の記録を残すため、承認時にワークフロー（エージェントフロー）で案件フォルダの記録ファイルへ追記させる。Teams で使う場合は、承認カード（アダプティブカード）で承認を受ける形も選べる

### 7. 機械 lint を MCP ツールにする
`tools/lint-slides.py` は Studio の中では直接動かないため、ツールとして外に出す。

1. lint を HTTP で呼べる形にする。`lint-slides.py` をラップする小さな MCP サーバー（入力：案件の slides.html と slides.md と outline.md、出力：終了コードと指摘の一覧）を、Azure Functions などにホストする
2. Copilot Studio で「ツール追加 → Model Context Protocol」でそのサーバーを接続し、ツール名を `lint_slides` とする
3. 指示とスキル `slide-lint` に、フェーズ2の終わりに必ず `lint_slides` を呼び、結果を lint-report に記録することを書く

代替：フックやツールから CLI（bash）が使える環境では、リポジトリを置いて `python3 tools/lint-slides.py` を直接実行してもよい。運用の安定性では MCP を推奨する。

### 8. 拡張の登録手順を決める
- 拡張を足すときは、GitHub 側で `tools/validate-extensions.py` の検査を通してから、対応するスキル／Knowledge を Studio に追加する
- 型の status（sample／trial／verified）の昇格は人間の承認が要る、という規則は指示に明記する

### 9. フックで G2 を二重化する（プレビュー機能）
- セッション開始フック：案件フォルダと現在のフェーズ、未承認のゲートがあればその旨をコンテキストに足すワークフローを差し込む
- ツール実行前フック：完成形ファイルの保存ツールの前に、案件の lint-report に機械 lint のパス記録があるかを確認し、無ければ deny するワークフローを差し込む
- fail-open のため、フックが落ちても止まらない。指示側の担保（手順2・7）と併せて二重化として扱い、フックだけに依存しない

### 10. テストし、同期の運用を決める
- Evaluate で、試走の再現ケース（例：試走2号の題材で G0 から G1 まで進める。ゲートで止まること、lint を呼ぶこと）を作り、公開前に測る
- 公開先は Teams／Microsoft 365 Copilot を選ぶ
- 同期の運用：正は GitHub の `core/`。core を更新したら、対応するスキルと Knowledge を写し直し、版を案件外の記録（このフォルダの `SYNC.md`）に残す。Studio 側で直接直した場合は、その場で GitHub 側へ戻す

## 標準ハーネスで作る場合の差分（参考）

- スキルは使えない。core の部品は、トピック（フェーズごとの会話パス）とエージェントフローへの分解が要る
- ゲートはトピック内の確認ノードと承認フローで実装する。分解の粒度を決める作業が増える
- 機械 lint は、エージェントフローから HTTP で呼ぶ（MCP もツールとして追加できる）
- オーケストレーションは設定できる反面、型診断のような推論の柔軟さは指示とトピック設計に依存する

## 出典（2026-11-17 確認）
- Microsoft Learn「Add tools to custom agents」：ツールの仕組み（コネクタ／エージェントフロー／MCP／Computer use）と、標準ハーネスのスキルに関する注記
- Microsoft Learn「Add knowledge to an agent」：Knowledge の種類と上限（アップロード500ファイル等）
- Microsoft Copilot Studio ブログ「Hooks in Copilot Studio」：フックの位置づけ、実装（ワークフロー）、fail-open、プレビューの入手方法
- Microsoft Learn「Write effective instructions for declarative agents」：指示を Knowledge に逃がさない原則（宣言型エージェント向けだが、指示と知識の分離は本手順でも同じに扱う）
