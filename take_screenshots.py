"""GitHubスクショ自動取得スクリプト

gh auth tokenでGitHub APIからセッションを取得し、Playwrightでスクショを撮る。
"""
import subprocess
import os
from playwright.sync_api import sync_playwright

REPO = "aicon-app-dev/itemforword"
BASE_URL = f"https://github.com/{REPO}"
SAVE_DIR = "/Users/ohkawa/Documents/aicon/tech-blog/screenshots"


def get_gh_token() -> str:
    """gh auth tokenを取得する"""
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    return result.stdout.strip()


def take_screenshots() -> None:
    """各種スクショを撮影する"""
    token = get_gh_token()
    os.makedirs(SAVE_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
        )

        page = context.new_page()

        # GitHubにOAuthトークンでログイン
        # gh CLIトークンをcookieではなくBasic Auth的に使う
        # GitHub Sessions APIでセッションcookieを取得
        page.set_extra_http_headers({
            "Authorization": f"token {token}"
        })

        # まずGitHubのトップにアクセスしてログイン状態を確認
        page.goto("https://github.com")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # Authorizationヘッダーだと通常のWeb UIは動かないので
        # device flowで取得したトークンでgithub sessionを作る
        # → gh auth login --with-tokenで取得したトークンをgist APIで検証
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True
        )
        print(f"ログインユーザー: {result.stdout.strip()}")

        # Playwrightで直接ログインフォームを使う
        page2 = context.new_page()
        page2.goto("https://github.com/login")
        page2.wait_for_load_state("networkidle")

        # ログイン済みかチェック
        if "login" in page2.url:
            print("ブラウザ未ログイン。GitHub CLIトークンでAPIスクショに切り替えます。")
            browser.close()

            # APIベースでデータ取得→HTMLレンダリングの代わりに
            # Playwrightで既存ブラウザセッションを利用
            _take_with_chrome_profile(p)
            return

        print("ブラウザログイン済み")
        _take_pages(page2)
        browser.close()


def _take_with_chrome_profile(playwright) -> None:
    """Chromeの既存プロファイルを使ってスクショを撮る"""
    # macOSのChromeプロファイルパスを特定
    chrome_profiles = [
        os.path.expanduser("~/Library/Application Support/Google/Chrome"),
        os.path.expanduser("~/Library/Application Support/Google/Chrome/Profile 1"),
    ]

    user_data_dir = None
    for p in chrome_profiles:
        if os.path.exists(p):
            user_data_dir = p
            break

    if not user_data_dir:
        print("Chromeプロファイルが見つかりません")
        return

    print(f"Chromeプロファイル使用: {user_data_dir}")

    # 既存Chromeが起動中だとロックされるので、一時コピーを使う
    import shutil
    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="chrome_profile_")
    print(f"一時プロファイル: {tmp_dir}")

    # cookieとLocalStateだけコピー
    for item in ["Default", "Local State"]:
        src = os.path.join(user_data_dir, item)
        dst = os.path.join(tmp_dir, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif os.path.isfile(src):
            shutil.copy2(src, dst)

    try:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=tmp_dir,
            headless=True,
            viewport={"width": 1920, "height": 1080},
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(f"{BASE_URL}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # ログイン確認
        if "login" in page.url:
            print("Chromeプロファイルでもログインできませんでした")
            context.close()
            return

        print("GitHubログイン成功！スクショ撮影開始...")
        _take_pages(page)
        context.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _take_pages(page) -> None:
    """各ページのスクショを撮影する"""
    targets = [
        # GitHub Actions一覧（複数ワークフロー同時稼働）
        (f"{BASE_URL}/actions", "01_actions_overview.png", None),
        # Issues一覧
        (f"{BASE_URL}/issues?q=is%3Aissue+is%3Aopen+sort%3Aupdated-desc", "02_issues_open.png", None),
        # Pull Requests一覧
        (f"{BASE_URL}/pulls?q=is%3Apr+sort%3Aupdated-desc", "03_pulls_list.png", None),
        # GitHub Projects（あれば）
        (f"https://github.com/orgs/aicon-app-dev/projects", "04_projects_board.png", None),
        # Actions ワークフロー一覧
        (f"{BASE_URL}/actions?query=workflow%3Aclaude", "05_claude_workflows.png", None),
    ]

    for url, filename, selector in targets:
        print(f"撮影中: {filename}")
        try:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            if selector:
                element = page.query_selector(selector)
                if element:
                    element.screenshot(path=f"{SAVE_DIR}/{filename}")
                else:
                    page.screenshot(path=f"{SAVE_DIR}/{filename}", full_page=False)
            else:
                page.screenshot(path=f"{SAVE_DIR}/{filename}", full_page=False)
            print(f"  保存: {SAVE_DIR}/{filename}")
        except Exception as e:
            print(f"  エラー: {e}")

    # 最新のPRを1つ開いてChecksタブを撮る
    print("最新PRのChecksタブを撮影中...")
    try:
        page.goto(f"{BASE_URL}/pulls?q=is%3Apr+sort%3Aupdated-desc")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        # 最初のPRリンクをクリック
        first_pr = page.query_selector('[data-testid="listview-item-title-link"]')
        if not first_pr:
            first_pr = page.query_selector(".js-navigation-open.Link--primary")
        if first_pr:
            first_pr.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            page.screenshot(path=f"{SAVE_DIR}/06_pr_detail.png", full_page=False)

            # Checksタブ
            checks_tab = page.query_selector('a[href*="checks"]')
            if checks_tab:
                checks_tab.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                page.screenshot(path=f"{SAVE_DIR}/07_pr_checks.png", full_page=False)

            # Files changedタブ（diff画面）
            files_tab = page.query_selector('a[href*="files"]')
            if files_tab:
                files_tab.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                page.screenshot(path=f"{SAVE_DIR}/08_pr_diff.png", full_page=False)
    except Exception as e:
        print(f"  PR詳細エラー: {e}")

    # 最新のIssueを1つ開いてタイムライン（ラベル自動遷移）を撮る
    print("最新Issueのタイムラインを撮影中...")
    try:
        page.goto(f"{BASE_URL}/issues?q=is%3Aissue+sort%3Aupdated-desc")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        first_issue = page.query_selector('[data-testid="listview-item-title-link"]')
        if not first_issue:
            first_issue = page.query_selector(".js-navigation-open.Link--primary")
        if first_issue:
            first_issue.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            page.screenshot(
                path=f"{SAVE_DIR}/09_issue_timeline.png", full_page=True
            )
    except Exception as e:
        print(f"  Issue詳細エラー: {e}")

    print(f"\n撮影完了！保存先: {SAVE_DIR}/")


if __name__ == "__main__":
    take_screenshots()
