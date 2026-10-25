# AIチャットアプリ — 大瓜生山祭2026

京都芸術大学・プログラミング演習の学生作品を紹介する静的サイトです。GitHub Pagesで公開できます。ページのビルドやAPIキーは不要です。

## データの流れ・置き場所

```text
input/*.xlsx（またはルートのExcel。Git対象外）
    ↓ python3 scripts/import_works.py
data/works.json（公開用：イニシャル・作品名・説明・URL・画像パス）
    ↓ script.js が fetch で読む
index.html の作品一覧・詳細画面

data/works.json のURL
    ↓ python3 scripts/capture_works.py
.local/captures/*.png（確認用画像。Git対象外）
    ↓ 目視確認後 --approve で掲載
assets/screenshots/*.png（公開するキャプチャ）
```

| ファイル | 用途 | Gitに含める |
| --- | --- | --- |
| `input/*.xlsx` / ルートの `*.xlsx` | フォーム回答の元データ | いいえ |
| `scripts/import_works.py` | Excel抽出・重複整理 | はい |
| `scripts/capture_works.py` | キャプチャ・確認後の掲載 | はい |
| `data/works.json` | ページが読む生成データ | はい |
| `assets/screenshots/` | 掲載する画像 | はい |
| `.local/import-report.json` | 採用行・重複行・入力の注意点 | いいえ |
| `.local/capture-report.json` | 取得結果・確認待ち・表示内容 | いいえ |
| `.local/capture-report.md` | キャプチャ状況の見やすい一覧 | いいえ |
| `.local/captures/` | 掲載前の画像 | いいえ |
| `index.html` / `script.js` | 本文・描画・詳細ダイアログ | はい |
| `theme.css` / `styles.css` | デザイン変数・レイアウト | はい |

## Excelを更新する

Python 3 の標準ライブラリだけで取り込めます。Excelの最新エクスポートを `input/` に置き、以前のファイルと差し替えます。現在のようにルートに置いても構いません。Excelの一時ファイル `~$*.xlsx` は無視します。

```sh
python3 scripts/import_works.py --check
python3 scripts/import_works.py
```

`--check` は確認のみで、公開データを更新しません。Excelが複数ある場合はファイルを明示してください。

```sh
python3 scripts/import_works.py "input/回答.xlsx"
python3 scripts/import_works.py "input/回答.xlsx" --sheet "フォームの回答 1"
```

列の順番は自由です。次の見出しで始まる列を読みます。見出しの全角・半角コロン、余分な空白は正規化します。

- `タイムスタンプ`
- `氏名：ローマ字` → 入力順で各単語の頭文字を連結（架空例：`Example Person` → `E.P.`）
- `作品名`
- `作品の説明文`
- `作品のURL`

漢字氏名・ローマ字氏名の全文・学年は公開JSONに書き出しません。キーワードからカテゴリや説明を創作することもしません。説明文は原文・改行を維持し、一覧は2行に収め、詳細画面で全文を表示します。

**重複ルールは「1人1作品・最新回答を採用」です。** ローマ字氏名の大文字小文字、全角半角、連続空白を正規化して同じ人を判定します。イニシャルだけでは判定しません。作品名やURLを直して再送信した回答もまとめます。タイムスタンプが同じなら、後のシート・後の行を優先します。過去のURLや説明で空欄を補完せず、最新回答の内容に揃えます。採用・除外行と変更された項目は `.local/import-report.json` で確認できます。

同姓同名、氏名の綴り・順番の変更、1人が複数作品を出す運用になった場合は、この判定ルールの変更が必要です。作品IDは正規化したローマ字氏名のSHA-256ハッシュから生成し、氏名の文字列自体は保存しません。行の追加・並べ替え・タイトル・URL修正では変わりません。氏名の表記を変えるとIDも変わります。

URL未入力の作品も表示し、外部リンクは隠します。HTTPや不正なURL、必須項目不足、読めないタイムスタンプがある場合は取り込みを中止し、既存の公開JSONを維持します。フォームの文字数目安を超えた作品は、レポートに注意を出して全文を残します。

`ai.studio/apps/…` と `aistudio.google.com/apps/…` は、取り込み時に `https://aistudio.google.com/apps/…?showAssistant=true&showPreview=true&fullscreenApplet=true` の形式に揃えます。ほかのクエリとフラグメントは維持します。公開済みの `*.ai.studio` アプリのURLには追加しません。

## キャプチャを更新する

キャプチャ時のみ `playwright-cli` とChromeが必要です。ページを見るだけなら不要です。未導入の場合は次を実行してください。

```sh
npm install -g @playwright/cli
```

```sh
python3 scripts/capture_works.py
```

1280×900で各URLの初期画面を取得します。ログインやフォーム送信などの操作はしません。結果は `.local/capture-report.json`、画像は `.local/captures/` に保存します。取得済みの確認待ち画像と掲載済み画像はスキップします。

**画像を開いて、アプリが表示されていること、氏名・アカウント情報が写っていないことを確認してから掲載します。** ログイン画面、エラー画面、読み込み途中は掲載せず、あとで手動で対応してください。

```sh
# IDは data/works.json / .local/capture-report.json で確認
python3 scripts/capture_works.py --approve work-xxxxxxxxxxxx

# 1作品だけ再撮影（--id は複数指定可）
python3 scripts/capture_works.py --id work-xxxxxxxxxxxx --force
```

掲載すると `assets/screenshots/` に画像をコピーし、`data/works.json` の画像パスも更新します。ファイル名には作品IDとURLのハッシュを使うため、URL修正後に以前の画面を誤表示しません。新しいURLで再撮影してください。同じURLでアプリの見た目が変わった場合は `--force` で撮り直して再掲載します。

手動で取得した画像を使う場合は、`scripts/import_works.py` の `screenshot_path(work)` と同じファイル名で `assets/screenshots/` に保存し、Excel取り込みを再実行すると反映されます。画像がない作品には仮のイラストを表示します。

## ローカルで確認する

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

<http://127.0.0.1:8000> を開きます。JSONを読むため、HTMLの直接ダブルクリックではなくHTTPサーバーを使います。Pythonの簡易サーバーは元Excelや `.local/` も配信できるので、ローカル確認専用とし、そのまま外部へ公開しないでください。

- iPad `1024×768`、`768×1024` で4列、スマートフォン幅 `390`、`320` で2列・横スクロールなし。
- 全作品数、イニシャル、説明全文、外部リンクを確認。
- 詳細ダイアログの開閉、Escape、元のカードへのフォーカス復帰を確認。

```sh
node --check script.js
python3 -m unittest discover -s tests
git diff --check
git ls-files '*.xlsx' '.local/*'  # 何も表示されないこと
```

## デザインと公開

作品の初期表示はJSONの登録順です。一覧の先頭が画面内にあり、1分間操作がなければ、先頭の1行（iPadは4作品・スマートフォンは2作品）を最後尾へ送ります。残りのカードは約0.6秒で上へ移動し、最後尾に回ったカードはその場でフェード表示します。作品番号は登録順の固定番号です。

タッチ・クリック・マウス移動・キー操作・スクロール後は、再び1分待ちます。詳細表示中、指を置いている間、カードにキーボードフォーカスがある間、一覧の先頭が画面外の場合、ページが非表示の場合は移動しません。詳細を閉じてからも1分待ちます。端末の「視差効果を減らす」が有効な場合は、アニメーションを省略して順番だけ更新します。既読情報や並び順は保存せず、再読み込みで登録順に戻ります。

色・書体・余白などは `theme.css`、配置は `styles.css`、ページ本文は `index.html` で変更します。`data/works.json` は生成物なので、作品情報の修正はExcelで行って再取り込みしてください。

GitHub Pagesの **Settings → Pages → Deploy from a branch → main / (root)** で公開します。`main` の更新は自動公開されます。`.nojekyll` と相対パスを維持してください。元Excelと `.local/` は `.gitignore` で除外し、公開用JSONと確認済み画像だけを含めます。`.gitignore` は既に追跡済みのファイルには効かないため、公開前に上記の `git ls-files` でも確認してください。

日程（2026年10月31日・11月1日）は[学園祭公式サイト](https://www.kyoto-art.ac.jp/kuafes/2026/)を参照しています。
