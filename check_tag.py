from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd
import concurrent.futures
import os
import argparse
import json
import urllib.request

def get_search_text():
    """検索テキストを取得する関数"""
    # 1. コマンドライン引数から取得を試みる
    parser = argparse.ArgumentParser(description='タグチェックツール')
    parser.add_argument('--search-text', '-s', help='検索するテキスト')
    args = parser.parse_args()
    
    if args.search_text:
        return args.search_text
    
    # 2. 設定ファイルから取得を試みる
    config_path = 'config.json'
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'search_text' in config:
                    return config['search_text']
        except Exception:
            pass
    
    # 3. 対話的な入力
    while True:
        search_text = input("検索するテキストを入力してください（例：GTM-MBWPPD2）: ").strip()
        if search_text:
            # 設定ファイルに保存
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump({'search_text': search_text}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return search_text
        print("テキストを入力してください。")

def find_line_numbers(text, search_text):
    """テキスト内で検索文字列が出現する行番号を返す（1始まり）"""
    line_numbers = []
    for index, line in enumerate(text.splitlines(), start=1):
        if search_text in line:
            line_numbers.append(index)
    return line_numbers

def find_line_matches(text, search_text, max_matches=5):
    """検索文字列が含まれる行の行番号と行内容を返す（最大件数あり）"""
    matches = []
    for index, line in enumerate(text.splitlines(), start=1):
        if search_text in line:
            matches.append((index, line.strip()))
            if len(matches) >= max_matches:
                break
    return matches

def fetch_view_source(url, timeout_seconds=10):
    """view-source相当のHTMLを取得する（失敗時はNone）"""
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; tag-check/1.0)"}
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_bytes = response.read()
        return raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        return None

def check_tag_presence(url, search_text):
    """単一URLに対するタグ検索処理を実行する関数"""
    result = {
        "url": url,
        "status": "未チェック",
        "in_head": False,
        "in_body": False,
        "in_html": False,
        "line_numbers": [],
        "line_numbers_view_source": [],
        "details": []
    }
    
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(1500)

                # リダイレクトの確認
                final_url = page.url
                if final_url != url:
                    result["status"] = "⚠️ リダイレクト"
                    result["details"].append(f"リダイレクト先: {final_url}")

                # ステータスコードの確認
                status_code = response.status if response else None
                if status_code == 404:
                    result["status"] = "⚠️ 404エラー"
                else:
                    # HEAD内での検索
                    head_element = page.query_selector("head")
                    if head_element:
                        head_html = head_element.inner_html()
                        if search_text in head_html:
                            result["in_head"] = True
                            result["details"].append("✅ HEADタグ内に検索テキストが存在します")
                            head_matches = find_line_matches(head_html, search_text)
                            if head_matches:
                                for line_no, line_text in head_matches:
                                    result["details"].append(f"  - HEAD一致行 {line_no}: {line_text}")
                                if len(head_matches) >= 5:
                                    result["details"].append("  - HEAD一致行は一部のみ表示しています")

                        # script タグでの検索
                        script_tags = head_element.query_selector_all("script")
                        for i, script in enumerate(script_tags):
                            script_content = script.inner_html() or ""
                            script_src = script.get_attribute("src") or ""
                            if search_text in script_content:
                                result["details"].append(f"  - script[{i}]の内容に存在します")
                            elif search_text in script_src:
                                result["details"].append(f"  - script[{i}]のsrc属性に存在します")

                    # BODY内での検索
                    body_element = page.query_selector("body")
                    if body_element:
                        body_html = body_element.inner_html()
                        if search_text in body_html:
                            result["in_body"] = True
                            result["details"].append("✅ BODYタグ内に検索テキストが存在します")
                            body_matches = find_line_matches(body_html, search_text)
                            if body_matches:
                                for line_no, line_text in body_matches:
                                    result["details"].append(f"  - BODY一致行 {line_no}: {line_text}")
                                if len(body_matches) >= 5:
                                    result["details"].append("  - BODY一致行は一部のみ表示しています")

                        # body内のscriptタグでの検索
                        script_tags = body_element.query_selector_all("script")
                        for i, script in enumerate(script_tags):
                            script_content = script.inner_html() or ""
                            script_src = script.get_attribute("src") or ""
                            if search_text in script_content:
                                result["details"].append(f"  - body内script[{i}]の内容に存在します")
                            elif search_text in script_src:
                                result["details"].append(f"  - body内script[{i}]のsrc属性に存在します")

                    # HTML全体での検索（念のため）
                    page_source = page.content()
                    if search_text in page_source:
                        result["in_html"] = True
                        result["line_numbers"] = find_line_numbers(page_source, search_text)
                        if result["line_numbers"]:
                            joined_lines = ", ".join(map(str, result["line_numbers"]))
                            result["details"].append(f"一致行番号: {joined_lines}")
                        else:
                            html_matches = find_line_matches(page_source, search_text)
                            if html_matches:
                                for line_no, line_text in html_matches:
                                    result["details"].append(f"  - HTML一致行 {line_no}: {line_text}")

                    # view-source相当のHTMLでも行番号を取得（ブラウザ表示の行に近づける）
                    view_source_html = fetch_view_source(url)
                    if view_source_html:
                        if search_text in view_source_html:
                            result["line_numbers_view_source"] = find_line_numbers(view_source_html, search_text)
                            if result["line_numbers_view_source"]:
                                joined_lines = ", ".join(map(str, result["line_numbers_view_source"]))
                                result["details"].append(f"view-source一致行番号: {joined_lines}")
                    else:
                        result["details"].append("⚠️ view-source取得に失敗しました")

                    # 総合判定
                    if result["in_head"] or result["in_body"]:
                        locations = []
                        if result["in_head"]:
                            locations.append("HEAD")
                        if result["in_body"]:
                            locations.append("BODY")
                        result["status"] = f"✅ テキストが見つかりました ({', '.join(locations)})"
                    elif result["in_html"]:
                        result["status"] = "✅ テキストが見つかりました (その他の場所)"
                    else:
                        result["status"] = "❌ テキストが見つかりません"
            except PlaywrightTimeoutError:
                result["status"] = "⚠️ タイムアウトエラー"
            except Exception as e:
                result["status"] = f"⚠️ エラー: {str(e)}"
            finally:
                page.close()
                context.close()
                browser.close()
    except Exception as e:
        result["status"] = f"⚠️ ブラウザ初期化エラー: {str(e)}"

    return result

def main():
    # 検索するテキストを取得
    SEARCH_TEXT = get_search_text()
    
    # URLリストをCSVから読み込む
    try:
        df_urls = pd.read_csv('urls.csv')
        df_urls['url'] = df_urls['url'].str.strip()
        urls = df_urls['url'].tolist()
    except Exception as e:
        print(f"CSVファイルの読み込みエラー: {str(e)}")
        urls = []
    
    if not urls:
        print("チェックするURLがありません。")
        return
    
    print(f"{len(urls)}件のURLをチェックします...")
    results = []
    
    # 並列処理で複数URLを同時にチェック
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(check_tag_presence, url, SEARCH_TEXT): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            result = future.result()
            results.append(result)
            print(f"処理中: {len(results)}/{len(urls)} - {result['url']}: {result['status']}")
    
    # 結果DataFrame
    df_results = pd.DataFrame({
        "URL": [r["url"] for r in results],
        "Status": [r["status"] for r in results],
        "HEAD内": ["あり" if r["in_head"] else "なし" for r in results],
        "BODY内": ["あり" if r["in_body"] else "なし" for r in results],
        "一致行番号": [", ".join(map(str, r["line_numbers"])) if r["line_numbers"] else "" for r in results],
        "一致行番号(view-source)": [", ".join(map(str, r["line_numbers_view_source"])) if r["line_numbers_view_source"] else "" for r in results]
    })
    
    # 詳細情報DataFrameも作成
    df_details = pd.DataFrame(results)
    df_details["details"] = df_details["details"].apply(lambda x: "\n".join(x) if x else "")
    
    # 結果をCSVに保存
    df_results.to_csv("tag_check_results.csv", index=False, encoding="utf-8-sig")
    df_details.to_csv("tag_check_details.csv", index=False, encoding="utf-8-sig")
    
    print(f"チェック完了。結果は tag_check_results.csv に保存されました。")
    
    # 結果を表示（ace_toolsが利用可能な場合）
    try:
        import ace_tools as tools
        tools.display_dataframe_to_user(name="タグチェック結果", dataframe=df_results)
    except ImportError:
        # 標準出力で結果概要を表示
        print("\n結果概要:")
        print(f"合計: {len(results)}件")
        print(f"テキスト検出: {df_results['Status'].str.contains('✅').sum()}件")
        print(f"テキストなし: {df_results['Status'].str.contains('❌').sum()}件")
        print(f"エラー: {df_results['Status'].str.contains('⚠️').sum()}件")
        
        print("\nHEAD/BODY別の検出状況:")
        print(f"HEAD内のみ: {sum([1 for r in results if r['in_head'] and not r['in_body']])}件")
        print(f"BODY内のみ: {sum([1 for r in results if not r['in_head'] and r['in_body']])}件")
        print(f"両方に存在: {sum([1 for r in results if r['in_head'] and r['in_body']])}件")

if __name__ == "__main__":
    main()