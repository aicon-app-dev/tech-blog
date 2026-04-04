---
title: "ハーネスエンジニアリングを極めたら、IssueからAIエージェントが動き、人間の役割は要件定義だけになった"
emoji: "🤖"
type: "tech"
topics: ["harness-engineering", "github-actions", "claude", "ai", "startup","ハーネス","ハーネスエンジニアリング","AIエージェント","エージェント"]
published: true
---


2ヶ月で21体のAIエージェントによる自律開発パイプラインを構築した。GitHub Issueに要求を書いて寝れば、朝にはマージレディのPRが上がっている。本記事では、2026年2〜3月に何を作り、何が動き、何がまだ動いていないのかを記す。

出発点は、2月時点で既に **57万行** に膨れていたモノレポだった。モバイルアプリ＋管理画面＋バックエンドが詰まったこのコードベースを、AIエージェントに正しく理解させ、自律的に開発させる——それがこの2ヶ月の挑戦だった。

![マージPR数の推移（半月単位）](/images/blog_metrics_biweekly.png)

*2025年12月〜2026年3月のマージPR数推移。2月後半のハーネス整備期を経て、3月後半には681件/半月まで急増。なお、この数値にはドキュメント更新等のPRも含まれるため、あくまで参考値である。*

:::message
**4/9（木）20:00〜** この記事の裏側を話すオンラインイベントを開催します → **[詳細・参加申し込み](https://connpass.com/event/389901/)**
:::

## 1. 我々について — 2ヶ月前の課題

専任のエンジニアはいない。代表と私が要件を決め、それを学生エンジニア数名とフリーランスに依頼して、開発していた。
開発フローは、一般的なスタートアップのそれだった。

- 代表と私で仕様をまとめ、エンジニアに長々と説明する
- コンテキストを伝えきれず、何度も往復が発生する
- CIは最低限のリント・テストのみ。しかもバックエンドなど一部プロジェクトにしか入っていなかった
- 要件の認識合わせ、設計の確認、実装の分担——すべてが人間同士のコミュニケーションに依存していた

開発プロセスが未熟な上、やりたいことに対して圧倒的に手が足りていなかった。

---

## 2. 2026年2〜3月にやった取り組み

まず前提として、この2ヶ月間の運用方針を説明する。**2月は機能開発を完全に止めた。** プロダクトのコードには一切手を入れず、ハーネスエンジニアリング——CI/CD、エージェントパイプライン、開発プロセスの整備——だけに集中した月だ。そして **3月は、開発する日とハーネスする日を1日おきに交互に回した。** 奇数日はプロダクト開発、偶数日はパイプラインの改善・拡張、というリズムだ。こうすることで、ハーネスの仕組みが実際の開発で機能するかを短いサイクルで検証し続けられた。

この2ヶ月で構築した仕組みの全体像を先に示す。

- **開発プロセスの分解** — 要求→要件定義→基本設計→詳細設計→タスク分割→実装→レビュー→マージの各ステップを定義
- **GitHub Projects + Issue駆動の自動化** — 1つの要求Issueからサブタスクが自動生成され、全コンテキストがIssueツリーに集約
- **ラベル駆動の自律エージェント（21体）** — ラベル付与をトリガーにエージェントがバトンリレーし、マージレディのPRまで全自動で流れる
- **CI/CDのモノレポ全体展開** — DBスキーマの破壊的変更チェック、全プロジェクトへのリント・テスト展開
- **PRごとのプレビュー環境自動構築** — Terraformで構築・破棄を自動化。QRコードでモバイル動作確認
- **定期スコアリング＆自動リファクタ** — AIがコードベースの健全性を6観点でスコアリングし、改善Issueを自動起票

自律開発パイプラインを支える主要な技術スタックは以下の通り。

![全体アーキテクチャ図](/images/02_overall_architecture.png)

| 技術 | 役割 |
|---|---|
| **GitHub Actions** | 全自動化の基盤。エージェントの起動・CI/CD・Issue管理すべてここで動く |
| **Claude API** | 各AIエージェントの頭脳。APIキー経由で呼び出し |
| **Claude Code** | ローカル〜CI上でのコード生成・修正に使用 |
| **Bug Bot（Cursor）** | PRに対する自動バグ検出。静的解析の指摘をコメントで残す |
| **Terraform** | プレビュー環境の構築・破棄をコードで管理 |
| **Expo** | React Nativeモバイルアプリのビルド・配信 |
| **Lefthook** | 人間がローカルでコーディングする際のpre-commitフック。CIと同じリントをローカルでも強制実行 |
| **Sentry** | フロントエンドのエラー監視（本格活用はこれから） |

設計の原則は一つ。 **開発のすべてをGitHub上で完結させる** こと。ローカル開発に依存すると、AIエージェントの動作が見えなくなる。GitHub上でIssue → PR → マージまですべてが可視化されていれば、人間のエンジニアが複数人いても「今誰が（どのエージェントが）何をしているか」が一目瞭然になる。

以下、各取り組みの詳細を述べる。

### 2-1. 開発プロセスの分解

最も重要な意思決定は、 **開発プロセスを細かく分解したこと** だ。

我々は以下のステップに分解している。

```
要求定義 → 要件定義 → 基本設計 → 詳細設計 → 実装 → 設計分割 → サブタスク化 → featureブランチ → devマージ
```

![具体例: Issueからdevマージまでの流れ](/images/03b_concrete_example.png)

従来は「Issueを立てて、誰かが実装してPR出す」という粒度だった。これをここまで分解した理由は、 **AIエージェントが一つひとつのステップを確実にこなせるようにするため** だ。一気に全部やらせると品質がブレる。ステップを分ければ、各ステップでの検証が可能になる。

これが我々の自律開発の起点であり、これが全てと言ってもいい。

### 2-2. Issue駆動の自動化

![要件定義Issueでの壁打ち例 — AIが要求を分析し質問を投げ、人間が回答する](/images/requirements_issue_example.png)

*要件定義エージェントがIssue上で壁打ちしている実例。AIが現状の実装を分析した上で質問を投げ、人間が回答することで要件が詰まっていく。*

**やったこと：**

- Issueに対してPRが自動で紐付く仕組みを構築
- 1つのIssue（要求）から、設計・実装などのサブIssueが自動生成される
- 各Issueのステータスが、プロセスの進行に応じて自動的に左から右へ遷移する
- すべてのコンテキスト（要件、設計、議論、PR）が1つのIssueツリーに集約される

Issueは以下のような親子構造で管理されている。

```
要求Issue（人間が作成）
├── [要件定義] サブIssue
├── [詳細設計] サブIssue
├── [実装] PR1: feature-A
├── [実装] PR2: feature-B
└── [実装] PR3: feature-C
```

`claude-requirements.yml` のトリガー部分。`要件定義作成` ラベルが付与されると要件定義エージェントが起動し、Issue上で壁打ちが始まる。

```yaml
on:
  issues:
    types: [labeled]
  issue_comment:
    types: [created]

jobs:
  requirements:
    if: |
      github.event_name == 'issues' &&
      github.event.label.name == '要件定義作成'
    runs-on: ubuntu-latest
    timeout-minutes: 30
    concurrency:
      group: claude-requirements-${{ github.event.issue.number }}
      cancel-in-progress: false
```

**何が変わったか：**

これが回るようになって、人間同士のコミュニケーションコストが劇的に減った。「あれどうなってる？」がなくなった。Projectボードを見れば、全タスクの進捗が一目瞭然。だから各自が自分の作業に安心して没頭できるようになった。

代表も横からフィードバックを入れやすくなったし、「これやっといて」で本当に完了するようになった。AIが自律的に動いて途中で詰まっても、Issueにすべてのコンテキストが載っているから人間が救済しやすい。

この仕組みの構築に最初の2週間を費やした。ここが一番苦戦した。だが、 **ここが回り始めてから、開発速度が一気に跳ね上がった。** 我々にとっては最大の転換点だった。

### 2-3. ラベル駆動の自律エージェント

GitHub Projects上でプロセスが可視化されたあと、次にやったのが **ラベルによるエージェント自動起動** だ。これが我々のパイプラインの心臓部にあたる。

**仕組み：**

1. Issueやプロジェクトの状態に応じて、適切なラベルが自動付与される
2. ラベルをトリガーにGitHub Actionsが発火し、対応するClaude APIエージェントが起動する
3. エージェントが作業を完了すると、次のステップに対応するラベルを自動で付与する
4. 次のエージェントが起動する

つまり、 **人間がラベルを1つ付ければ（あるいはIssueを立てれば）、あとはエージェント同士がバトンを渡し合って、最終的にマージレディのPRが上がってくる。**

一定以上の判断が必要なポイントでは、人間にレビュー依頼が飛ぶ。完全放任ではなく、人間がハンドオフポイントで介入できる設計にしている。

![ラベル駆動フローの全体図](/images/04_label_driven_flow.png)

`claude-implement-from-issue.yml` — ラベル付与でエージェントが起動し、ブランチ作成→実装→PR作成まで全自動で走る。MCP サーバー（Browser、Figma、DB）も接続される。

```yaml
on:
  issues:
    types: [labeled]

jobs:
  implement:
    if: github.event.label.name == 'IssueからClaudeが自動実装'
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Setup MCP servers
        uses: ./.github/actions/setup-mcp-servers
        with:
          enable-browser: "true"
          enable-figma: "true"
          enable-db: "true"
```

`auto-label-on-unblock.yml` — バトンリレーの実装。ブロッカーIssueがクローズされると、後続Issueの全ブロッカー解消を確認してから自動でラベルを付与し、実装エージェントを再起動する。

```yaml
- name: Add label to unblocked dependent issues
  run: |
    DEPENDENT_ISSUES=$(gh api repos/$REPO/issues/$ISSUE_NUMBER/dependencies/blocking \
      --paginate --jq '.[].number')

    for DEP_ISSUE in $DEPENDENT_ISSUES; do
      REMAINING=$(gh api "repos/$REPO/issues/$DEP_ISSUE/dependencies/blocked_by" \
        --jq '[.[] | select(.state != "closed")] | length')
      if [ "$REMAINING" -eq "0" ]; then
        gh issue edit $DEP_ISSUE --add-label "IssueからClaudeが自動実装" --repo $REPO
      fi
    done
```

### 2-4. AIエージェント一覧と各役割

現在稼働しているAIエージェントの一覧を示す。各エージェントにはそれぞれ固有のシステムプロンプト（人格・スキル定義）が設定されている。

| # | ファイル名 | 役割 | 使い方のコツ |
|---|-----------|------|------------|
| 1 | `claude-requirements.yml` | 要求Issueから[要件定義]サブイシューを作成し、質問→回答の壁打ちで要件を詰める。「要件確定」で[詳細設計]サブイシューを自動作成 | Issueのbodyに背景・ゴール・制約を詳しく書くほど壁打ちの質が上がる。`AIが自動的に回答`ラベルと併用すると完全自動化。「要件確定」は正確なキーワード一致が必要 |
| 2 | `claude-auto-answer.yml` | 要件定義・設計フェーズのClaude質問にAIが自動回答。「基本設計確定」「詳細設計確定」も自動判断 | 自動回答できるのはコードパターン・慣習・CLAUDE.md記載事項のみ。ビジネス判断はエスカレーションされるので人間が回答する。壁打ちが止まったら人間がコメントすれば再開 |
| 3 | `claude-detailed-design.yml` | 基本設計→詳細設計の2フェーズを担当。Entスキーマ・GraphQL定義・テスト戦略・PR分割計画を策定し、設計PRを作成 | **設計書末尾のPR分割計画が最重要** — タスク分割エージェントの入力になる。壁打ち上限15ラウンドで停止するので、AI自動回答でテンポよく進めるのが効率的 |
| 4 | `claude-task-split.yml` | 設計PRマージ後、設計書のPR分割計画を読み取り[実装]サブイシュー群を作成。依存関係を`blocked_by`で設定 | PR分割計画が曖昧だと不適切な分割になる。手動dispatchでPR番号指定の再実行可能。依存関係が間違うとタスクが永遠に開始されないので注意 |
| 5 | `claude-implement-from-issue.yml` | Issue本文の指示に従いブランチ作成→コード実装→テスト→PR作成を全自動実行。依存Issueがある場合はブロック解除後に着手 | Issue本文に実装指示を具体的に書くほど品質が上がる（ファイルパス・関数名・テストケース等）。`make ent`/`make ggen`等のコード生成も自動実行。タイムアウト60分 |
| 6 | `auto-label-on-unblock.yml` | ブロッカーIssueクローズ時、後続Issueに`IssueからClaudeが自動実装`ラベルを付与して実装を再起動 | 手動でIssueをクローズしても後続が自動起動する。ブロッカーが複数ある場合は全クローズまで起動しない |
| 7 | `create-feature-pr.yml` | 全[実装]サブイシュー完了時にfeat→developのPRを自動作成。Projectステータスを「人間レビュー待ち」に更新 | Feature PRは人間レビュー必須。部分完了では作成されない。develop向けPR作成時に影響分析が自動実行される |
| 8 | `claude-full-auto-pipeline.yml` | Bugbot修正→CI修正→Claudeレビュー→レビュー修正→マージをステートマシンで全自動実行 | `（自動マージ）`付きラベルなら自動マージ、なしなら人間レビュー待ち。上限: Bugbot10回/CI3回/レビュー5サイクル。上限到達で`人間の対応が必要`ラベルが付く |
| 9 | `claude-auto-review-pipeline.yml` | CI→レビュー→修正→マージを自動化。フルオートとの違いはBugbotフェーズがない点 | Bugbot不要なPR（小規模修正・ドキュメント変更等）に適している。レビュー上限10サイクル/CI修正上限3回 |
| 10 | `claude-auto-review.yml` | PRのコードレビューを4カテゴリ（アーキテクチャ/リスク/保守性/設計適合性）で実施。修正は行わない | `Claude自動パイプライン`ラベル付きPRは除外。同一commit SHAへの重複レビューはスキップ。設計ドキュメントがあれば設計適合性チェックも実行 |
| 11 | `claude-auto-review-fix.yml` | Claudeレビューの指摘を自動修正。Critical/High→無条件修正、Medium→ルール確認後修正、Low→スキップ | スコープゲートあり（PR変更ファイルのみ修正可能）。上限5サイクル。フルオートパイプラインの一部として組み込まれることが多い |
| 12 | `claude-bugbot.yml` | cursor[bot]のレビュー指摘をFix/False positive/Won't fix/Questionの4種に仕分けて対応 | False positive判定が重要（Bugbotは誤検知も多い）。人間が質問に回答後に再ラベル付与で再処理可能。上限6回 |
| 13 | `claude-fix-ci.yml` | CI失敗ログを分析し、Lint→型→テスト→コード生成→一時的障害に応じて自動修正 | 一時的障害はファイル編集せず`gh run rerun`のみ。修正後はローカル検証してからpush。上限3回 |
| 14 | `claude-auto-merge.yml` | 全CI通過確認後にPRを自動マージ。フィーチャーブランチマージ時はIssueを明示的にクローズ | GitHubの`closes #`はデフォルトブランチマージ時のみ動作するため、フィーチャーブランチ向けでは明示クローズが必要 |
| 15 | `claude-impact-analysis.yml` | PR変更内容を分析し、影響を受ける機能・テスト項目をPR descriptionに自動追記 | develop向けPR作成時に自動実行されるので手動ラベル不要。既存のdescriptionは保持される |
| 16 | `claude-fix-conflict.yml` | マージコンフリクトを自動解消 | 両方の変更を理解した上で適切にマージする（片方を一方的に捨てない）。`merge-conflict-rule.mdc`に準拠 |
| 17 | `claude-bug-investigation.yml` | バグIssueのコードベースを調査し原因特定。修正は行わず原因分析と修正方針の提示に特化 | 2フェーズ構成: `ongoing`（初期調査）→`confirmed`（結果まとめ）。Browser MCPで画面操作再現も可能。完了後に`IssueからClaudeが自動実装`ラベルで自動修正に接続可能 |
| 18 | `pipeline-stuck-monitor.yml` | 5分間隔でパイプライン停滞を検知。壁打ち停止/PR停止/実装遷移停止/feat PR未作成が対象。自動回復を最大2回試行 | 回復アクションはラベル再付与やワークフロー再実行等の安全な操作のみ。`人間の対応が必要`ラベル付きはスキップ。失敗時はIssue起票+Slack通知でエスカレーション |
| 19 | `sync-develop-to-feature.yml` | `.github/workflows/`等のdevelop push時に全オープンPRへ自動sync。`ブランチ最新化`ラベルでfeatureブランチにdevelopをマージ | 壊れたワークフローをdevelopにマージすると全PRに影響するので注意。`ブランチ最新化`ラベルは手動付与・自動除去 |
| 20 | `update-workflow-readme.yml` | `claude*.yml`変更時に`.github/README.md`を自動更新しPR作成 | ワークフロー追加・変更時にドキュメントが自動追従する仕組み |
| 21 | `detect-unused-code.yml` | 毎週月曜にcustomer-mobileの不要コードを検知して報告 | v1→v2移行に伴いv1側で使われなくなったコードの検出に有用。週次スケジュール実行 |

エージェントがうまく動作する鍵は、 **各エージェントに正しいスキル（システムプロンプト）を与えること** に尽きる。プロンプトの精度がそのまま出力の精度になる。

![自動レビューエージェントの出力例 — 指摘を重要度別に分類し、approve/request changesを判断する](/images/auto_review_example.png)

*10番の自動レビューエージェントの出力例。指摘をHigh/Medium/Lowに分類し、既存の防護策（GraphQLバリデーション等）を考慮した上でapprove判定を下している。*

`claude-auto-review.yml` — レビューエージェントの起動部分。Claudeが自身の修正pushをレビューしないようスキップ判定し、同一コミットへの重複レビューも防止する。

```yaml
on:
  pull_request:
    types: [opened, reopened, ready_for_review, labeled]

jobs:
  claude-auto-review:
    if: >-
      github.event.pull_request.draft == false &&
      (github.event.action != 'labeled' ||
       github.event.label.name == 'ClaudeがPRにレビュー') &&
      !contains(github.event.pull_request.labels.*.name, 'Claude自動パイプライン')
    steps:
      - name: Check if push is from Claude (skip self-review)
        run: |
          if [[ "${{ github.actor }}" == "claude[bot]" ]]; then
            echo "skip=true" >> $GITHUB_OUTPUT
          fi
      - name: Check for duplicate review on this commit
        run: |
          HEAD_SHA="${{ github.event.pull_request.head.sha }}"
          EXISTING=$(gh api repos/${{ github.repository }}/pulls/${{ github.event.pull_request.number }}/reviews \
            --jq "[.[] | select(.commit_id == \"$HEAD_SHA\")] | length")
```

### 2-5. CI/CDの拡充

自律開発でAIが大量のコード変更を生成するようになると、CIの重要度が跳ね上がる。人間がすべてのPRを精読するのは物理的に不可能だから、機械的に品質を担保する仕組みが必要になる。

**この期間で追加・拡張したCIチェック：**

**DBスキーマの破壊的変更チェック**
AIがDBマイグレーションを生成した際に、既存データとの互換性を自動検証する。これがないとAIが意図せず破壊的変更を入れてしまうリスクがあり、安心してリリースできなかった。このチェックが入ったことで、物量を増やしても破壊的変更が混入しないことが担保され、ガンガン新機能を作れるようになった。

`check-migration-drop-column.yml` — マイグレーションファイルに `DROP COLUMN` が含まれていないかを自動検出し、PRにコメントで警告する。

```yaml
on:
  pull_request:
    paths:
      - "backend/ent/migrate/migrations/**"

jobs:
  check-drop-column:
    steps:
      - name: Check for DROP COLUMN in new migration files
        run: |
          BASE_SHA="${{ github.event.pull_request.base.sha }}"
          HEAD_SHA="${{ github.event.pull_request.head.sha }}"
          MIGRATION_FILES=$(git diff --name-only --diff-filter=A \
            "${BASE_SHA}" "${HEAD_SHA}" -- "backend/ent/migrate/migrations/*.sql")

          while IFS= read -r file; do
            if grep -qi "DROP COLUMN" "$file"; then
              WARNING_COUNT=$((WARNING_COUNT + 1))
            fi
          done <<< "$MIGRATION_FILES"
```

**リント・テストのモノレポ全体展開**
以前はバックエンドにしかリント・テストのCIが入っていなかった。これをモノレポ内の全プロジェクト（カスタマーモバイル、オペレーターフロントエンド含む）に展開した。

**ドキュメント同期チェック**
コード変更に対してドキュメントが追従しているかを自動検証する。

**テストの着手**
単体テストの記述を開始している。まだまだ不十分な段階で、カバレッジとしては発展途上。ただし、テストが書ける基盤は整った。

Lefthookによるpre-commitフックと合わせて、ローカルでもCI上でも同じリントが走る二重チェック体制になっている。

### 2-6. プレビュー環境

![PRにpreviewラベルを付けるとQRコード付きのプレビュービルドが自動生成される](/images/preview_qr_comment.jpg)

*`preview` ラベルを付けると、GitHub ActionsがExpoビルドを実行しQRコードをPRにコメント。スマホでスキャンするだけでその場で動作確認できる。*

PRごとにプレビュー環境が自動で立ち上がる仕組みをTerraformで構築した。

**仕組み：**

- PRが作成されると、GitHub Actionsが発火しTerraformでプレビュー環境を自動構築
- PRがマージまたはクローズされると、同じくTerraformで環境を自動破棄
- QRコードが生成され、モバイルアプリの動作確認がその場で可能

`preview-deploy.yml` — PR に `preview` ラベルを付けると、その PR 用の独立したプレビュー環境を Terraform で自動構築する。

```yaml
name: Preview Deploy

on:
  pull_request:
    types: [labeled, synchronize]

jobs:
  check-label:
    steps:
      - name: Check preview label
        run: |
          HAS_PREVIEW=$(jq -r '.pull_request.labels[].name' "$GITHUB_EVENT_PATH" | grep -x "preview")
          if [ -n "$HAS_PREVIEW" ]; then
            echo "run=true" >> $GITHUB_OUTPUT
          fi
```

`terraform/itemforward/preview/main.tf` — PR 番号で環境を分離。S3 バックエンドの key を `preview/pr-{N}/terraform.tfstate` で動的に切り替える。

```hcl
terraform {
  backend "s3" {
    bucket  = "itemforward-terraform-state-bucket"
    key     = "preview/placeholder/terraform.tfstate"
    # 上書き: -backend-config="key=preview/pr-{N}/terraform.tfstate"
    region  = "ap-northeast-1"
    encrypt = true
  }
}
```

PRごとに `pr-{N}.operator.itemforward.com`、`pr-{N}.api.operator.itemforward.com` 等のDNSが自動で作成され、S3上にPR単位でTerraformのstateファイルが管理される。PRがクローズされると `preview-cleanup.yml` が発火し、環境が自動で破棄される。

### 2-7. 定期スコアリング＆自動リファクタ

コードベースの健全性を維持するために、AIによる定期スコアリングの仕組みを導入している。

**スコアリング観点：**

1. アーキテクチャ
2. コード品質
3. テスト
4. セキュリティ
5. パフォーマンス
6. 運用性

モノレポ内の各プロジェクトに対して、これら6つの観点でAIがスコアを算出する。スコアが低い箇所については、自動でIssueが起票され、リファクタ用のPRが生成される。

![スコアリングレポート — customer-mobileの例](/images/scoring-report-customer-mobile.png)

*customer-mobileプロジェクトのスコアリング結果。総合60点（Cランク）。アーキテクチャ 4.8、コード品質 6.5、テスト 5.0、セキュリティ 7.5、パフォーマンス 5.4、運用性 6.5 — テストやアーキテクチャが低いといったリアルな数字がそのまま改善Issueの起点になる。*

上記のプロジェクト品質スコアリングとは別に、**自動化パイプライン自体の健全性**を測るスコアリングも運用している。各ワークフローの「複雑度」と「安定性」を定量評価し、改善優先度の高いものからIssueを起票する仕組みだ。

```python
def score_complexity(target, static):
    loc_score = min(static["loc"], 500) / 500 * 15
    branch_score = min(static["branch_points"], 25) / 25 * 20
    integration_score = min(static["external_calls"], 40) / 40 * 20
    mutation_score = min(static["write_operations"], 20) / 20 * 10
    # ... 重み付け合算で 0-100 の複雑度スコアを算出
    return round(min(total, 100.0), 1)

def score_stability(target, runtime, static):
    success_score = runtime["success_rate"] * 45      # 成功率（配点45）
    rerun_score = (1 - runtime["rerun_rate"]) * 20    # 再実行率（配点20）
    # ... 実行時間健全性、マーカー密度等を加算
    return round(max(min(total, 100), 0), 1)

def priority_score(complexity, stability):
    return round(complexity * (100 - stability) / 100, 1)
```

複雑度は静的解析（LOC、分岐数、外部API呼び出し数、状態変更操作数等）から、安定性はGitHub Actionsの実行履歴（成功率、再実行率、実行時間中央値）から算出している。優先度スコアは `複雑度 × (100 - 安定性) / 100` で、複雑なのに安定していないワークフローほど上位にランクされる。

現状はまだスコアリングに基づく優先度付けを精査している段階で、完全自動化には至っていない。今後はスコアリングのタイミングでIssueを自動起票し、そのIssueを起点にリファクタエージェントが自律的に修正PRを上げるフローを確立する。

---

:::message
**4/9（木）20:00〜** コスト感や組織設計など、この記事の裏側をオンラインで話します → **[参加申し込み](https://connpass.com/event/389901/)**
:::

## 3. まだできていないこと・これからやること

### 3-1. カスタムリントの作成

現在、AIエージェントはシステムプロンプト内で「この規約に従って実装すること」と指示している。しかしこれでは、エージェントがプロンプトの規約を読み解く処理に認知リソースを消費し、肝心のビジネスロジック実装に集中できない場面がある。

カスタムリントを整備すれば、コード規約の遵守はリンターに任せられる。エージェントの認知負荷を下げ、よりポン出しで正しいコードが書けるようにする。

現時点では、カスタムリンターの代わりに **「黄金原則（Golden Principles）」** をルールファイルとしてリポジトリに配置し、エージェントが参照する形で運用している。

`golden-principles.mdc` の抜粋:

```markdown
## 原則 1: 共有ユーティリティ優先（重複排除）
- 新しいヘルパー関数を作る前に `backend/utils/` の既存関数を確認する
- ポインタ変換は必ず `backend/utils/ptr.go` を使う。新規作成禁止
- 複数サービスで使うロジックは `domain/service` 層に集約してDRYにする

## 原則 5: レイヤー境界の厳守
- サービス層から `ent` パッケージを直接importしない
- 同一レイヤー内のパブリックメソッド呼び出し禁止（service→service、repo→repo）
- インフラストラクチャ層は必ずリポジトリで抽象化する

## 原則 7: 不要なコードを書かない
- 使わないメソッドを定義しない
- 取得系メソッドをWhere句ごとに増やさない。引数を拡張して対応する
```

`backend-architecture-rule.mdc` の抜粋:

```markdown
## サービス層（Service Layer）
- **使わないメソッドを定義しないでください**
- 同パッケージ内でパブリックメソッドを呼び出し合わないでください
- サービス層がインフラストラクチャに依存しないように（ent import 禁止）

## リゾルバ（Resolver）の責務
- 認証情報取得、サービス呼び出し、型変換（convert/ 経由）のみ
- バリデーションやビジネスロジックを書かない
```

これらを今後、静的解析で機械的に強制するカスタムリンターに昇格させていく。OpenAI の記事にある「リントがカスタムであるため、エラーメッセージを書き込んでエージェントコンテキストに修復手順を注入する」をまさに実現したい。

### 3-2. E2Eテスト（Maestro + Playwright）

Maestro（モバイル）とPlaywright（Web）を組み合わせたE2Eテスト基盤を構築する。

目指しているのは、要件定義の段階で動作シナリオを自動生成し、実装完了後にそのシナリオでE2Eテストが自動実行される世界だ。ユーザー入力→管理画面でのオペレーター操作→結果確認までの一気通貫のテストを自動化する。

実はこの部分、既にかなり動いている。バックエンドE2Eテスト、Preview環境でのE2E、そして Claude Code スキルによるモバイル×管理画面の一気通貫テストまで構築済みだ。

`preview-e2e-test.yml` — Preview環境でEASビルドを取得→Simulatorにインストール→E2Eテスト実行:

```yaml
name: Preview E2E Test

on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: "PR number"
        required: true
      build_id:
        description: "EAS Simulator Build ID"
        required: true

jobs:
  e2e-test:
    timeout-minutes: 60
    steps:
      - name: Wait for EAS build and download artifact
        run: |
          BUILD_ID="${{ inputs.build_id }}"
          while [ $COUNT -lt $MAX_WAIT ]; do
            STATUS=$(eas build:view "$BUILD_ID" --json | jq -r '.status')
            if [ "$STATUS" = "FINISHED" ]; then
              ARTIFACT_URL=$(eas build:view "$BUILD_ID" --json | jq -r '.artifacts.buildUrl')
              curl -L -o build.tar.gz "$ARTIFACT_URL"
              break
            fi
          done
```

一番やりたかったのが `howmatch-e2e` Claude Code スキル。モバイル（iOS Simulator）と管理画面（Playwright）を MCP で操作し、アイテム登録→査定→金額反映の一気通貫フローを自動検証する:

```
Test Flow:
  Step 1: [Mobile] ホーム画面の初期状態を記録（総資産額）
  Step 2: [Mobile] アイテム登録 → カメラ → フォトライブラリから画像選択
  Step 3: [Mobile] AI解析結果確認 → 必須項目入力 → 登録
  Step 4: [Operator] 査定入力ページで新規アイテムを検索
  Step 5: [Operator] 金額リンク → 査定金額入力 → 保存
  Step 6: [Mobile] ホーム画面リフレッシュ → 金額反映確認
  Step 7: レポート生成
```

「まだできていないこと」に入れているのは、これらを **CIパイプラインに完全に組み込んで全PR自動実行する** 段階がまだだからだ。仕組みはあるが、安定稼働するところまでは至っていない。

### 3-3. 本番バグ自動検知 → 自動修正

Sentryでフロントエンドのエラーを、バックエンドのログでサーバー側の異常を検知する。検知したバグに対して、AIエージェントが原因を特定し、修正PRを自動で上げる仕組みを作る。

Sentry の導入自体は完了しており、`customer-mobile-v2` に組み込み済みだ。バグ調査エージェント（`claude-bug-investigation.yml`）も既に稼働しており、バグIssueに対してコードベースを調査→原因特定→修正方針の提示まで自動で行う。Browser MCP で画面操作の再現も可能だ。

まだ繋がっていないのは **Sentry のアラート → 自動でバグ Issue 起票 → 調査エージェント起動** の部分。ここが繋がれば、夜中にバグが発生→朝には修正PRが上がっている、という世界が完成する。

### 3-4. ログ・メトリクス・BigQuery → UI/UX改善

バックエンドのメトリクス・ログ、DBの読み書きパフォーマンス、BigQueryに蓄積されたユーザー行動データ。これらを統合的に分析し、UI/UXの改善提案をAIエージェントに行わせることを計画している。

### 3-5. Claude Code → Figma → React Native パイプライン

デザインワークフローの自動化を目指している。

```
要求（こういうデザインにしたい）
  → Claude Codeがデザイントークンを読み込み、Figmaファイルを自動生成
  → 人間がFigma上でレビュー・修正・追加プロンプト投入
  → Reactコードを自動生成
  → React Nativeに合流
```

デザイントークンをベースにすることで、ブランド一貫性を保ちながらデザイン→実装のサイクルを高速化する。

![デザイン→実装パイプラインの全体図](/images/08_design_to_code_pipeline.png)

### 3-6. エージェント自己改善

過去に実装されたPRを分析し、繰り返し発生しているミスや非効率なパターンを検出する。根本原因がエージェントのプロンプトやワークフロー設計にある場合、エージェント自身がそれを修正する仕組みを構築したい。

また、日常的な会話やフィードバックのログをどのようにエージェントのコンテキストに反映させるか——意思決定レイヤーへの情報伝達の仕組みも今後の課題だ。

![エージェント自己改善のフィードバックループ図](/images/09_agent_self_improvement.png)

### 3-7. アプリ内チャットの自前実装

現在、アプリ内のユーザー⇔オペレーター間チャットにはSaaSを組み込んで使っている。これを全て自前で書き直す計画がある。

きっかけはOpenAIのハーネスエンジニアリング記事にあった「複雑なオープンソースやサードパーティの仕様に振り回されるより、自分たちで実装した方が結局は品質が安定する」という指摘だ。実際、外部サービスのAPI仕様の複雑さやUIの制約に合わせる工数が無視できなくなってきている。

---

## 4. 振り返り — OpenAIの原則と我々の実践

ここまで書いてきた我々の取り組みは、OpenAI のハーネスエンジニアリング記事を参考に設計したものだ。彼らの記事でチームは、 **手書きコードを1行も使わずに、5ヶ月で約100万行・1,500件のPRを3人のエンジニアで出荷した** 実験について述べている。到達した結論は明快だった。

> エンジニアリングチームの主な業務は、コードを書くことではなく、 **環境を設計し、意図を明確にし、エージェントが信頼性の高い作業を行うためのフィードバックループを構築すること** になる。

我々はこの記事を読んで「組織規模やサービス規模が小さい今だからこそ当てはまる」と確信し、原則を HOW MUCH の開発に全面的に適用した。以下に、彼らの原則に対して我々が何をやったかの対応表を示す。

| 達成度 | OpenAI の原則 | 彼らの実践 | 我々の実践 |
|:---:|---|---|---|
| ○ | **AGENTS.md は百科事典ではなくマップ** | 約100行の AGENTS.md + 構造化された `docs/` ディレクトリを記録システムに | CLAUDE.md を短く保ち、`docs/` に設計ドキュメントをバージョン管理。ただしディレクトリごとの説明が不十分な箇所がまだ残っている |
| ○ | **エージェントの認識可能性が目標** | リポジトリ内でバージョン管理されたものだけがエージェントの「世界」 | アプリの要件やビジネスロジックに関する事柄は、リポジトリの `docs/` にマークダウン化。「リポジトリに入ってない業務プロセスを根絶する」が合言葉 |
| △ | **アーキテクチャ制約をカスタムリンターで機械的に適用** | レイヤー構造の依存方向を静的に強制。リントのエラーメッセージに修復手順を注入 | 現状は「黄金原則」ルールファイルでプロンプト経由の運用。カスタムリンターによる機械的な強制はこれから |
| ○ | **ラベル駆動の自律パイプライン** | エージェントが PR をオープンし、レビューし、フィードバックに対応し、マージまで自律実行 | GitHub ラベルでエージェント間のバトンリレーを実装。要件定義からマージまで全自動で流れるが、テスト自動化が未整備でCI通過率にまだ課題あり |
| ○ | **エントロピーとガベージコレクション** | 定期的なクリーンアップ Codex タスクで技術的負債を「少しずつ返済」 | 週次の定期スコアリング + 不要コード検知は稼働中。スコアリング→自動リファクタIssue起票の完全自動化はまだ |
| ○ | **スループットがマージの考え方を変える** | ブロックを最小限にしたマージゲート。修正は安価、待機は高コスト | 自動マージの仕組みは構築済み。ただし実際にはエージェントが詰まって人間がローカルで救済するケースがまだ多く、スループットは理想に届いていない |
| △ | **アプリケーションの可読性向上** | Chrome DevTools Protocol をエージェントに組み込み、UI 操作・検証を自動化 | Browser MCP を組み込んだが、画面操作できる範囲はまだ限定的。E2Eテストの CI パイプライン組み込みもこれから |
| ◎ | **計画は第一級の成果物** | 実行プランを `docs/exec-plans/` にバージョン管理 | 設計書末尾のPR分割計画がタスク分割エージェントの入力。設計→実装の接続点として機能 |

Martin Fowler 氏はハーネスエンジニアリングを **Context Engineering（コンテキスト供給）・Architectural Constraints（アーキテクチャ制約）・Garbage Collection（技術的負債の回収）** の3つの柱で整理している。振り返ると、我々の2ヶ月はまさにこの3つを同時に立ち上げる作業だった。

OpenAI の記事にある「初期の進捗は予想より遅れたが、それは Codex に能力がなかったからではなく、環境が十分に定義されていなかったため」という一文は、我々の経験とも重なる。最初の2週間は Issue 駆動の仕組み構築に費やした。何も動かない2週間だった。だが、そこが回り始めてから爆発的に速度が上がった。

2ヶ月で構築した仕組みの核は、突き詰めると3点に集約される。**開発プロセスを細かく分解したこと。** **すべてをGitHub上で可視化したこと。** **ラベル駆動でエージェントが自律的にバトンを渡す仕組みを作ったこと。**

まだまだ未完成な部分は多い。だが、この基盤が回り始めてからの開発速度は、以前とは比較にならない。本記事の設定やワークフローが、同じような課題を抱えるチームの参考になれば幸いだ。

**筆者**: 加藤 — 株式会社Aicon PM。元SES企業でフルスタックエンジニアとして勤務後、2025年5月にAiconに入社。PMとして開発プロセス設計・AIエージェントパイプラインの構築を担当。

---

### 4/9（木）この記事の裏側を話すイベントやります

この記事の内容をもう少し深掘りして、**記事には書けなかったコスト感・組織設計・技術の裏話**を30分でサクッとお話しするオンラインイベントを開催します。

👉 **[connpassでイベント詳細を見る](https://connpass.com/event/389901/)**

[![イベントサムネイル](https://media.connpass.com/thumbs/30/74/3074d89756936f13ee81fa1729ecf2f9.png)](https://connpass.com/event/389901/)

- **日時**: 2026/4/9（木）20:00〜20:30
- **形式**: オンライン（Google Meet）・無料
- **内容**: Claude API × GitHub Actionsのリアルな請求額、副業エンジニアとの情報共有設計、CI/CD・クリーンアーキテクチャの技術ディープダイブなど

気軽にご参加ください → **[参加申し込みはこちら](https://connpass.com/event/389901/)**

---
