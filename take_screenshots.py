"""GitHubスクショ自動取得 — Chromeデバッグポート経由"""
import os
from playwright.sync_api import sync_playwright

REPO = "aicon-app-dev/itemforword"
BASE_URL = f"https://github.com/{REPO}"
SAVE_DIR = "/Users/ohkawa/Documents/aicon/tech-blog/screenshots"


def _goto(page, url: str) -> None:
    """ページ遷移してロード完了を待つ"""
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)


def _shot(page, filename: str, full_page: bool = False) -> None:
    """スクショ保存"""
    path = f"{SAVE_DIR}/{filename}"
    page.screenshot(path=path, full_page=full_page)
    print(f"  保存: {filename}")


def take_screenshots() -> None:
    os.makedirs(SAVE_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})

        # ログイン確認
        _goto(page, BASE_URL)
        if "login" in page.url:
            print("未ログイン。")
            browser.close()
            return

        print("GitHubログイン成功！撮影開始...\n")

        # 1. Actions一覧
        _goto(page, f"{BASE_URL}/actions")
        _shot(page, "01_actions_overview.png")

        # 2. Issues一覧
        _goto(page, f"{BASE_URL}/issues?q=is%3Aissue+sort%3Aupdated-desc")
        _shot(page, "02_issues_list.png")

        # 3. PR一覧
        _goto(page, f"{BASE_URL}/pulls?q=is%3Apr+sort%3Aupdated-desc")
        _shot(page, "03_pulls_list.png")

        # 4. Projects
        _goto(page, "https://github.com/orgs/aicon-app-dev/projects?query=")
        _shot(page, "04_projects.png")

        # 5. Claude系ワークフロー
        _goto(page, f"{BASE_URL}/actions?query=workflow%3Aclaude")
        _shot(page, "05_claude_workflows.png")

        # 6-8. 最新PR詳細
        _goto(page, f"{BASE_URL}/pulls?q=is%3Apr+sort%3Aupdated-desc")
        pr_links = page.query_selector_all('a[id^="issue_"]')
        if pr_links:
            href = pr_links[0].get_attribute("href")
            if href and not href.startswith("http"):
                href = f"https://github.com{href}"

            _goto(page, href)
            _shot(page, "06_pr_detail.png")
            _shot(page, "06b_pr_full.png", full_page=True)

            _goto(page, f"{href}/checks")
            _shot(page, "07_pr_checks.png")

            _goto(page, f"{href}/files")
            _shot(page, "08_pr_diff.png")

        # 9. 最新Issue詳細
        _goto(page, f"{BASE_URL}/issues?q=is%3Aissue+sort%3Aupdated-desc")
        issue_links = page.query_selector_all('a[id^="issue_"]')
        if issue_links:
            href = issue_links[0].get_attribute("href")
            if href and not href.startswith("http"):
                href = f"https://github.com{href}"
            _goto(page, href)
            _shot(page, "09_issue_detail.png")
            _shot(page, "09b_issue_full.png", full_page=True)

        # 10. ラベル一覧
        _goto(page, f"{BASE_URL}/labels")
        _shot(page, "10_labels.png")
        _shot(page, "10b_labels_full.png", full_page=True)

        # 11-12. Actions成功/進行中
        _goto(page, f"{BASE_URL}/actions?query=is%3Asuccess")
        _shot(page, "11_actions_success.png")

        _goto(page, f"{BASE_URL}/actions?query=is%3Ain_progress")
        _shot(page, "12_actions_in_progress.png")

        print(f"\n撮影完了！ {SAVE_DIR}")
        page.close()
        browser.close()


if __name__ == "__main__":
    take_screenshots()
