from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import pandas as pd
import concurrent.futures
import os

def check_tag_presence(url, search_text):
    """単一URLに対するタグ検索処理を実行する関数"""
    # Chrome オプションの設定
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # ChromeDriver のパスを設定
    driver_path = os.environ.get("CHROMEDRIVER_PATH", "C:/chromedriver.exe")
    service = Service(driver_path)
    
    result = {
        "url": url,
        "status": "未チェック",
        "in_head": False,
        "in_body": False,
        "in_html": False,
        "details": []
    }
    
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(10)
        
        try:
            # ページ読み込み
            driver.get(url)
            time.sleep(1.5)
            driver.execute_script("window.stop();")
            
            # リダイレクトの確認
            final_url = driver.current_url
            if final_url != url:
                result["status"] = "⚠️ リダイレクト"
                result["details"].append(f"リダイレクト先: {final_url}")
            
            # ステータスコードの確認
            try:
                status_code = driver.execute_script("""
                    var xhr = new XMLHttpRequest();
                    xhr.open('HEAD', window.location.href, false);
                    xhr.send(null);
                    return xhr.status;
                """)
                
                if status_code == 404:
                    result["status"] = "⚠️ 404エラー"
                    return result
            except Exception:
                pass
            
            # HEAD内での検索
            try:
                head_element = driver.find_element(By.TAG_NAME, "head")
                head_html = head_element.get_attribute("innerHTML")
                
                if search_text in head_html:
                    result["in_head"] = True
                    result["details"].append("✅ HEADタグ内に検索テキストが存在します")
                    
                    # script タグでの検索
                    script_tags = head_element.find_elements(By.TAG_NAME, "script")
                    for i, script in enumerate(script_tags):
                        try:
                            script_content = script.get_attribute("innerHTML") or ""
                            script_src = script.get_attribute("src") or ""
                            
                            if search_text in script_content:
                                result["details"].append(f"  - script[{i}]の内容に存在します")
                            elif search_text in script_src:
                                result["details"].append(f"  - script[{i}]のsrc属性に存在します")
                        except Exception:
                            continue
            except Exception as e:
                result["details"].append(f"⚠️ HEAD要素の検索中にエラー: {str(e)}")
            
            # BODY内での検索
            try:
                body_element = driver.find_element(By.TAG_NAME, "body")
                body_html = body_element.get_attribute("innerHTML")
                
                if search_text in body_html:
                    result["in_body"] = True
                    result["details"].append("✅ BODYタグ内に検索テキストが存在します")
                    
                    # body内のscriptタグでの検索
                    script_tags = body_element.find_elements(By.TAG_NAME, "script")
                    for i, script in enumerate(script_tags):
                        try:
                            script_content = script.get_attribute("innerHTML") or ""
                            script_src = script.get_attribute("src") or ""
                            
                            if search_text in script_content:
                                result["details"].append(f"  - body内script[{i}]の内容に存在します")
                            elif search_text in script_src:
                                result["details"].append(f"  - body内script[{i}]のsrc属性に存在します")
                        except Exception:
                            continue
            except Exception as e:
                result["details"].append(f"⚠️ BODY要素の検索中にエラー: {str(e)}")
            
            # HTML全体での検索（念のため）
            page_source = driver.page_source
            if search_text in page_source:
                result["in_html"] = True
            
            # 総合判定
            if result["in_head"] or result["in_body"]:
                locations = []
                if result["in_head"]: locations.append("HEAD")
                if result["in_body"]: locations.append("BODY")
                result["status"] = f"✅ テキストが見つかりました ({', '.join(locations)})"
            elif result["in_html"]:
                result["status"] = "✅ テキストが見つかりました (その他の場所)"
            else:
                result["status"] = "❌ テキストが見つかりません"
                
        except TimeoutException:
            result["status"] = "⚠️ タイムアウトエラー"
        except Exception as e:
            result["status"] = f"⚠️ エラー: {str(e)}"
        finally:
            driver.quit()
    except Exception as e:
        result["status"] = f"⚠️ ドライバー初期化エラー: {str(e)}"
    
    return result

def main():
    # 検索するテキストを設定
    SEARCH_TEXT = "GTM-1234ABCD"  # 任意のテキストに変更（GTMのIDなど）
    
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
        "BODY内": ["あり" if r["in_body"] else "なし" for r in results]
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