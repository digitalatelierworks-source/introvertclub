# SUZURI 自動登録（試作）

既存のTシャツ（商品ID `19942047`）を参照し、新しい**非公開**の両面プリント商品を作成するPythonスクリプトです。

## 安全上の仕様
- 初期状態はドライラン。**SUZURIには何も書き込みません**。
- `--create` を明示したときだけ、新しい非公開素材・商品を作成します。
- 既存商品の変更・削除はしません。
- APIキーをソースコードやGitHubリポジトリに保存しないでください。
- **実APIでの動作・左胸への正確な配置・プリント解像度は未検証**です。作成後はSUZURI画面で必ず確認してください。
- APIの `texture` にはPNGのdata URIを渡します。画像が大きすぎる場合はAPIの制限にかかる可能性があります。

## 実行前に用意するもの
- Python 3
- SUZURI APIトークン（環境変数 `SUZURI_API_TOKEN` に設定）
- 前面ロゴPNG（`assets/images/logo.png`）
- 背面デザインの透過PNG（ローカルに保存。**Web公開ディレクトリへAPIキーを置かないこと**）

### ローカルで試す

```bash
export SUZURI_API_TOKEN='（手元で発行したトークン）'
python3 automation/suzuri_create.py \
  --front assets/images/logo.png \
  --back /path/to/introvertclub_friends_back_transparent.png
```

上記は**読み取り・確認のみ**です。内容を確認したあと、同じコマンドの末尾に `--create` を追加すると、非公開の商品作成リクエストを送ります。

## 現段階での注意点
- SUZURI APIの `sub_materials` を背面に指定していますが、前面の印刷位置が「左胸」になるとは限りません。位置指定の追加検証が必要です。
- 商品タイプはAPIのスタンダードTシャツ（item ID 1）を想定し、異なる場合は停止します。
- 利益設定は既存素材の `price` を参照します。両面印刷による原価・販売価格の差を公開前に確認してください。
- 次段階：画像サイズ確認、商品プレビュー検証、GitHub Actionsの手動実行ワークフロー、CSVからの複数デザイン生成。
