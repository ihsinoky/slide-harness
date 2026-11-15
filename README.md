# slide-harness

GitHub Copilot でスライド資料を作るためのハーネス。
スライド作成を、AI-DLC のようにフェーズ・ゲート・成果物で組み立てたプロセスとして定義し、
anti-slop 対策をプロセス側で担保する。

## 考え方

- **圧縮は意図合わせの後**：要約やタイトル付けは、言いたいことの優先順位が人間と一致してから。
- **ゲートで止まる**：G0（優先順位マップ）、G1（タイトルだけのアウトライン）、G3（最終）の承認なしに進まない。
- **生成と検査は別パス**：anti-slop リントは生成とは独立に、チェックリストで実行する。
- **1スライド＝1メッセージ**：タイトルは名詞題ではなく主張文。図が先、文章は要点1行。

## 構成

```
core/
  process.md              フェーズ・ゲート・成果物・役割（プロセスの正）
  anti-slop-checklist.md  リント項目
  figure-forms.md         図の形の分類（figure-docs の要約）
.github/
  agents/slide-flow.agent.md   カスタムエージェント定義
  copilot-instructions.md      リポジトリ全体への指示
works/                    案件ごとの作業フォルダ（成果物をここに残す）
```

## 使い方

1. Copilot で `slide-flow` エージェントを選ぶ（またはこのリポジトリで普通に依頼する）。
2. 案件ごとに `works/<案件名>/` を作り、成果物（intent / priority-map / outline / lint-report）を残す。
3. フェーズとゲートは `core/process.md` のとおりに進む。

## 備考

- プロセスの正は `core/`。エージェント定義はその要約で、矛盾したら core が優先。
- M365 Copilot Studio へは、core をナレッジと指示文に写して移植する想定（対応表は別途管理）。
