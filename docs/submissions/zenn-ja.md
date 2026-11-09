---
title: "依存ゼロ・アカウント不要で API の破壊的変更を CI で検知する"
emoji: "🛰️"
type: "tech"
topics: ["python", "api", "ci", "devops", "テスト"]
published: false
---

サードパーティ API は、何も告げずに変わる。フィールド名が変わり、型が
number から string に化け、配列から要素が消える。自分の連携コードは、
それが動かなくなるその瞬間まで、動き続ける——たいていは本番で、金曜日に。

SaaS の API 監視サービスに入らなくても、これを捕まえられる。正しいと分かっている
レスポンスを 1 つ保存し、CI でコマンドを 1 本書き、終了コードを見る。それだけでいい。
この記事では、標準ライブラリだけで書かれた約 200 行の `apidiff` を使って、
その最小構成を紹介する。以下の出力はすべて 2026-11-09 に実際に実行したもの。

## 考え方

1. ベースラインを保存する（正しいと分かっているレスポンス本文）。
2. 毎回、現在のレスポンスを取得してベースラインと diff する。
3. **破壊的**な変更（キーの削除、型の変更、配列長の変化）だけでビルドを落とす。
   無害な追加は無視する。

最後の点が重要だ。多くの「diff」ツールはノイズが多すぎる。ベンダーが新しい
フィールドを足したことは、誰かを呼び出す理由にはならない。あなたが gate
したいのは後退であって、バイト単位の差分ではない。

## インストール

pip もアカウントも不要。ファイルを 1 つコピーするだけ。

```bash
git clone https://github.com/akira7045/akira-devtools
cp akira-devtools/apidiff/apidiff.py .
```

Python 3.8 以上、標準ライブラリのみ。

## ベースラインを保存する

```bash
python3 apidiff.py save https://api.example.com/v1/status baseline.json
```

## 2 つのペイロードを diff する

以前はこう返っていたとする（自分が実装した時の形）。

```json
{"version":"1.2.0","user":{},"metadata":{}}
```

そして今日、ベンダーはこう返す。

```json
{"version":"1.3.0","user":{"email":"a@example.com"},"metadata":{"region":"eu-west-1"}}
```

フルの diff:

```bash
python3 apidiff.py diff old.json new.json
```

```
[added  ] metadata.region
    - "<missing>"
    + "eu-west-1"
[added  ] user.email
    - "<missing>"
    + "a@example.com"
[changed] version
    - "1.2.0"
    + "1.3.0"
```

3 つの変更。壊れうるのは `version` の変更だけで、それに固定している
コンシューマを壊しうる。新しいキー 2 つは追加的で安全だ。

## 破壊的変更だけで gate する

```bash
python3 apidiff.py diff old.json new.json --breaking-only
```

```
[changed] version
    - "1.2.0"
    + "1.3.0"
```

実際の変更が見つかったので終了コードは `1`。追加的なキーは抑制される。

## CI に入れる

```yaml
# .github/workflows/contract.yml
- name: Check API contract
  run: |
    python3 apidiff.py check "$API_URL" contract.json --breaking-only
```

`check` は `0`（一致 / 追加のみ）、`1`（破壊的変更）、`2`（リクエスト/パース
エラー）を返す。外部サービスも、API 自体以外の秘密情報も不要。

## 認証と POST エンドポイント

```bash
python3 apidiff.py save https://api.example.com/v1/query base.json \
  --data '{"q":"hello"}'            # POST を意味する

python3 apidiff.py check https://api.example.com/v1/me me.json \
  --header "Authorization: Bearer $TOKEN"
```

## 機械可読な出力

```bash
python3 apidiff.py check "$API_URL" contract.json --json
```

これを既存の PR コメンターや Slack 通知にパイプすればいい。

## ホステッドサービスではだめか？

ホステッドの契約監視は素晴らしい——予算があり、データが文句なしにネットワークの
外に出てよいなら。単一の内部依存なら、リポジトリ内のスナップショットファイルと
4 行の CI で十分で、コストゼロ、ペイロードは手元に残る。`apidiff` はその最小版だ。

48 個のテスト（ローカル HTTP サーバを使い、ネットワーク不要）を備え、
他の 5 つの単一ファイルツール（`secretscan`、`jsonl2csv`、`dupfind`、`envcheck`、
`logsum`）と一緒に配布している。

- **無料**: コードは GitHub 上で MIT ライセンス。使う、フォークする、出荷する、自由に。
- **有料（チーム向け）**: 30 日間のバグ修正窓口と名前の出たサポート窓口付きの
  商用ライセンス——企業の調達が MIT では得られないと求めるもの。

リポジトリ: https://github.com/akira7045/akira-devtools
