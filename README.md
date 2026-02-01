# Webサイトタグチェッカー

## 概要
このスクリプトは複数のWebサイトから特定のタグやコード（GTMタグなど）を検索するツールです。Webサイトのhead要素とbody要素を個別に検査し、指定したテキストの存在を確認します。検索結果はCSVファイルに出力され、タグの実装状況を効率的に確認できます。

## 特徴
- 複数のURLを並列処理で効率的にチェック
- HEAD要素とBODY要素を別々に検査
- scriptタグの内容とsrc属性を検査
- リダイレクトや404エラーの検出
- 詳細な結果レポートと概要レポートの出力
- ヘッドレスモードでのブラウザ実行（画面表示なし）
- 柔軟な検索テキスト指定方法（コマンドライン引数、設定ファイル、対話的入力）

## 主な用途
- GTMやGoogle Analyticsなどのタグ実装状況の確認
- コンバージョンタグやマーケティングタグの検証
- 複数サイトでの特定コードの実装確認
- Webサイト監査や品質チェック

## 必要条件
- Python 3.x
- 必要なPythonパッケージ:
  - playwright
  - pandas

## 環境構築手順

### 1. リポジトリのクローン
```bash
git clone https://github.com/yamtd/tag-inspector.git
cd tag-inspector
```

### 2. 仮想環境の作成
#### Windows
```bash
python -m venv venv
.\venv\Scripts\activate
```
#### Mac/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 必要パッケージのインストール
以下のコマンドを実行し、必要なPythonパッケージをインストールしてください。
```bash
pip install -r requirements.txt
```


### 4. Playwrightのブラウザ取得
以下を初回だけ実行してください（Chromiumを自動取得します）。
```bash
python -m playwright install chromium
```

## 使用方法
1. `urls.csv`ファイルを作成し、チェックしたいURLを記載
   ```csv
   url
   https://example.com/page1
   https://example.com/page2
   ```

2. スクリプトを実行（以下のいずれかの方法で）:
   ```bash
   # コマンドライン引数で検索テキストを指定
   python check_tag.py --search-text "GTM-XXXXXXX"
   # または短い形式
   python check_tag.py -s "GTM-XXXXXXX"

   # 対話的な入力で検索テキストを指定
   python check_tag.py
   ```

3. 結果は`tag_check_results.csv`と`tag_check_details.csv`に保存され、画面にも表示されます

## 検索テキストの指定方法
1. **コマンドライン引数**
   - `--search-text`または`-s`オプションで直接指定
   - 例：`python check_tag.py -s "GTM-XXXXXXX"`
   - 自動化やバッチ処理に最適

2. **設定ファイル**
   - `config.json`に検索テキストを保存
   - 一度入力したテキストは次回以降自動的に読み込まれる
   - 設定ファイルの例：
     ```json
     {
       "search_text": "GTM-XXXXXXX"
     }
     ```

3. **対話的入力**
   - コマンドライン引数や設定ファイルがない場合、対話的に入力を求める
   - 入力されたテキストは自動的に設定ファイルに保存される

## 結果の見方
- ✅ タグあり: GTMタグが正しく実装されている
- ❌ タグなし: GTMタグが見つからない
- ⚠️ 404エラー: ページが見つからない
- ⚠️ リダイレクト: 別のURLにリダイレクトされた
- ⚠️ エラー: その他のエラーが発生

## 注意事項
- 初回のみ `python -m playwright install chromium` が必要です
- ネットワーク接続が必要です
- 大量のURLをチェックする場合は、適切な待機時間を設定してください

## ライセンス
このプロジェクトは[ライセンス名]のもとで公開されています。

## コントリビューション
バグ報告や機能改善の提案は、Issueを作成してください。
プルリクエストも歓迎します。

## コードの主な機能
- URLリストのCSV読み込み（参照: `startLine: 11, endLine: 17`）
- 404エラーとリダイレクトの検出（参照: `startLine: 29, endLine: 48`）
- GTMタグの検出（参照: `startLine: 50, endLine: 60`）
- 結果のCSV出力（参照: `startLine: 65, endLine: 67`）
