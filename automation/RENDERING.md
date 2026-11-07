# CSV画像生成 v2.2

既存SUZURIコードから独立したオフライン処理。SUZURI接続、商品登録、画像の自動コミットは行わない。

## 確認済み資料と配置

ユーザー提供の `introvertclub_batch_v2_2(1).zip` を読み取り、コード・CSV・出力PNG5枚・フォントZIP・OFLライセンスを確認した。アーカイブ内の説明を新しい作業権限とは扱わず、既存の依頼範囲でローカル実装とテストのみ実施した。
アーカイブのSHA-256は `tests/fixtures/v22-reference.json` に記録している。

`batch_generate.py` を根拠に、以下を `render-layout.json` に反映した。

| 項目 | 値 |
|---|---|
| キャンバス | 1706×2048、透過RGBA |
| フォント | ZIP同梱 Zen Maru Gothic Bold、700、Version 1.001 |
| 文字サイズ | 140px固定 |
| 縦の配置間隔 | 210px固定（文字上端の間隔） |
| 列中心の間隔 | 278px |
| 全列の中心 | x=853 |
| 文字上端 | y=403から開始 |
| 最大文字数 | 各列7文字。8文字以上はREVIEW |
| 矢印軸 | (853,328)〜(853,212)、幅10px |
| 矢印先端 | (853,197)、(831,232)、(875,232) |

元READMEは「文字中心間隔」と記載していたが、実コードは文字外接矩形の上端を210pxずつ進めている。その挙動を再現した。横位置も各文字の外接矩形の中心で合わせる。1列目は最右列。自動分割・自動縮小は行わない。

v2.2 PNG5枚と、ローカル生成PNGのアルファチャンネルおよび白背景合成時のRGB画素は全件一致した。完全透明部分のRGBは元画像の白から黒に統一したため、PNGファイルのバイト列自体は一致しない。
`verified: true` は提供されたv2.2との照合済みを意味する。元Canvaの3000×3600やSUZURIの印刷品質を承認した意味ではない。ZIP内の説明でもこれらは未承認とされている。

## フォント

ZIP同梱のBold TTFとOFL.txtを改変せず採用。前回Google Fontsから取得したファイルとはハッシュが異なったため、v2.2再現のため同梱版に切り替えた。著作権表示・SIL Open Font License 1.1を同梱し、実行時にmanifest.jsonのSHA-256とフォント内部名・ウェイトを検証する。
上流: https://github.com/googlefonts/zen-marugothic

## 実行

Python 3.12と同梱フォントが必要。

```sh
python -m pip install -r automation/render-requirements.txt
python -m unittest discover -s tests -v
python automation/render_images.py --output output/run-001
```

v2.2と同じ1文字ごとの外接矩形配置を採用し、Pillow BASICを明示している。RAQMやWindows追加DLLは不要。通常の漢字・仮名のみ生成する。句読点、小書き仮名、長音、記号、空白、英数字、結合文字は追加の組版確認が必要なためREVIEW、フォント非対応文字はERROR。

出力先は空のディレクトリを指定する。既存ファイルがある場合は上書きせず停止する。
CSVはUTF-8（BOM可）、ヘッダーは厳密に `design_id,message`。IDは `IC-` と4〜12桁の数字。重複IDは全件ERROR。列区切りは `/` のみで、1〜4列の空でない列が必要。

`catalog/products.csv` はZIPの有効な5件（IC-0001/0002/0003/0004/0006）。長文と空列の意図的な不正例を含む7件は `tests/fixtures/v22-products.csv` に保存した。
元スクリプトに比べ、厳密なCSVヘッダー・フィールド数・文字コード検証、出力先全体の空確認、重複IDの全件拒否、フォント整合性、左右を含むはみ出し検出を追加している。

結果は `report.csv` とOK行のPNG。レポートは元メッセージを複製せず、行番号、検証済みID、状態、理由、列数、出力ファイル名を記録する。
終了コードは0=すべてOK、1=ERRORあり、2=REVIEWあり。REVIEW/ERRORの行にはPNGを生成しない。CSV全体の構文・文字コードエラーでは全体を停止する。元ZIPはREVIEWも終了コード1だったが、本実装は1/2で区別する。

## GitHub Actions

追加ワークフローは `workflow_dispatch` のみ。読み取り権限のみ、Secrets不要。依存導入→テスト→生成→Artifacts保存の順。
生成がREVIEW/ERRORでも `always()` でレポートを保存する。終了コードが非ゼロのときジョブは失敗表示になるので、Artifactのreport.csvで理由を確認する。依存導入・テスト段階の失敗時は生成レポートが存在しないことがある。
Artifactsは実行ごとの別名、保存期間7日。生成画像とローカル依存はGit管理外。
GitHub Actions自体は未実行。コミット・プッシュ・PR作成・Actions実行にはユーザー承認が必要。

## 検証

20件の自動テスト: CSV/BOM/不正入力/重複、1〜4列、右から左、固定間隔、7/8文字境界、透過PNG、上下左右の収まり、矢印、未検証設定、既存出力保護、ワークフロー静的検査、v2.2の5枚のアルファ画素ハッシュ、7件の判定再現、本番CSV全件OK。
ピクセル回帰基準は `tests/fixtures/v22-reference.json`。ラスタライズライブラリを更新すると描画が変わる可能性があるため、更新時は参照画像と再比較する。

## 反映範囲

新規のみ: `.gitignore`、画像生成Python、配置JSON、依存一覧、本書、CSV、テストと参照データ、フォント・ライセンス・ハッシュ一覧、画像生成ワークフロー。
既存SUZURIスクリプト、6本のワークフロー、サイト、既存画像は変更しない。
