# 受注サンプル納品見本 — logsum による「アクセスログ集計」案件

このフォルダは、受託案件で「依頼 → 納品」をどう進めるかの実例です。
架空の依頼を想定し、実際に動くサンプルデータ・実行コマンド・期待出力を同梱しています。
お客様はこの通りに動かせば、納品物の挙動を5分で検証できます。

---

## 依頼（想定）

> Webサーバのアクセスログ（Apache/nginx 形式）を、
> ステータスコード別・URL別に集計したい。
> 追加のライブラリは入れたくない。手元のPythonだけで動かしたい。

## 納品物

- `logsum.py`（単一ファイルCLI・標準ライブラリのみ・読み取り専用）
- 本サンプル一式（`sample_access.log` / `expected_status.json` / 本README）
- 使い方は `products/logsum/README.md` を参照。

## 検収手順（コピペで実行）

```bash
# 1) ステータスコード別に集計
python3 logsum/logsum.py samples/logsum-case/sample_access.log --format access --by status
```

期待出力:

```
total lines : 10
matched     : 10
grouped by  : status
  200  5
  500  2
  201  1
  401  1
  404  1
```

```bash
# 2) URL別の上位5件
python3 logsum/logsum.py samples/logsum-case/sample_access.log --format auto --by path --top 5
```

期待出力:

```
total lines : 10
matched     : 10
grouped by  : path
  /api/orders    3
  /api/login     2
  /api/users     2
  /api/orders/9  1
  /api/users/12  1
```

```bash
# 3) JSONで機械可読出力（想定: CI等に渡す）
python3 logsum/logsum.py samples/logsum-case/sample_access.log --format auto --by status --json
```

期待出力は `expected_status.json` と一致します。

```bash
# 4) 自動検証（期待JSONと突き合わせ）
diff <(python3 logsum/logsum.py samples/logsum-case/sample_access.log \
        --format auto --by status --json) samples/logsum-case/expected_status.json \
  && echo "OK: 期待出力と一致"
```

## 納品の約束

- 標準ライブラリのみ / pip不要 / Python 3.8+。
- 読み取り専用。対象ログを書き換え・削除しない。
- 追加要件は別見積（15,000円〜）。検収期間は納品後7日。

## 価格（この案件相当）

| 内容 | 価格 |
|------|-----:|
| logsum 単体（MITライセンス・納品物込） | 1,500円 |
| セットアップ支援（お客様環境で動作確認） | 5,000円 |
| カスタム改修（集計軸の追加など1要件） | 15,000円〜 |

詳細は `products/SALES.md`。
