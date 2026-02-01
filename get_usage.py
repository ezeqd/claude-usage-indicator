#!/usr/bin/env python3
"""
Fetch Claude.ai usage metrics using session cookies.

Uses Playwright to bypass Cloudflare and make authenticated requests to the
usage API. Requires cookies from an active claude.ai session.

Export cookies: DevTools > Network > click usage request > Headers > Cookie
Save to: ~/.config/claude-usage/cookies.txt

Security: cookies.txt contains sensitive session data. Add to .gitignore.
"""

import json
import sys
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Default cookie file location
DEFAULT_COOKIE_FILE = Path.home() / ".config" / "claude-usage" / "cookies.txt"


def parse_cookies(cookie_str: str, domain: str = "claude.ai") -> list[dict]:
    """Parse Cookie header string into Playwright cookie format."""
    cookies = []
    for part in cookie_str.split("; "):
        part = part.strip()
        if not part:
            continue
        idx = part.find("=")
        if idx == -1:
            continue
        name = part[:idx].strip()
        value = part[idx + 1 :].strip()
        if not name:
            continue
        cookies.append(
            {
                "name": name,
                "value": value,
                "domain": domain,
                "path": "/",
            }
        )
    return cookies


def get_usage(
    cookie_file: Path | None = None,
    org_id: str | None = None,
    headless: bool = True,
    quiet: bool = False,
) -> dict | None:
    """
    Fetch usage data from claude.ai API using session cookies.

    Args:
        cookie_file: Path to file containing Cookie header string
        org_id: Organization UUID (extracted from lastActiveOrg if not provided)
        headless: Run browser in headless mode
        quiet: Suppress stderr output (for use from indicator)

    Returns:
        Usage data dict or None on failure
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        if not quiet:
            print(
                "Error: Playwright required. Run: pip install playwright && playwright install chromium",
                file=sys.stderr,
            )
        return None

    cookie_file = cookie_file or DEFAULT_COOKIE_FILE
    if not cookie_file.exists():
        if not quiet:
            print(f"Error: Cookie file not found: {cookie_file}", file=sys.stderr)
        return None

    cookie_str = cookie_file.read_text().strip()
    if not cookie_str:
        if not quiet:
            print("Error: Cookie file is empty", file=sys.stderr)
        return None

    # Extract org_id from lastActiveOrg cookie if not provided
    if not org_id:
        for part in cookie_str.split("; "):
            if part.strip().startswith("lastActiveOrg="):
                org_id = part.split("=", 1)[1].strip()
                break
        if not org_id:
            org_id = "32321586-22bf-4e89-9007-8b6469448821"

    url = f"https://claude.ai/api/organizations/{org_id}/usage"
    cookies = parse_cookies(cookie_str)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1920, "height": 1080},
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        context.add_cookies(cookies)

        page = context.new_page()
        response_data = None

        def handle_response(response):
            nonlocal response_data
            if response.url == url and response.status == 200:
                try:
                    response_data = response.json()
                except Exception:
                    pass

        page.on("response", handle_response)
        error_msg = None

        try:
            response = page.goto(url, timeout=60000, wait_until="networkidle")
            if response:
                if response.status == 401:
                    error_msg = "Cookie expired (401 Unauthorized)"
                elif response.status == 403:
                    error_msg = "Access denied (403 Forbidden). Try renewing org_id or cookies."
                elif response.status != 200:
                    error_msg = f"API Error: {response.status}"
            elif not response_data:
                error_msg = "No response received from API"
        except PlaywrightTimeout:
            error_msg = "Timeout connecting to Claude"
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "playwright install" in str(e):
                error_msg = "Playwright browsers not installed. Run: playwright install chromium"
            else:
                error_msg = f"Error: {str(e)}"
        finally:
            browser.close()

    if error_msg and not response_data:
        return {"error": error_msg}
    return response_data


def interactive_login(cookie_file: Path | None = None) -> bool:
    """
    Launch a headed browser for the user to log in manually and capture cookies.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: Playwright required for login automation.", file=sys.stderr)
        return False

    cookie_file = cookie_file or DEFAULT_COOKIE_FILE
    print("\n" + "="*60)
    print("CLAUDE.AI LOGIN")
    print("="*60)
    print("1. A browser window will open.")
    print("2. Log in normally (Google, Email, etc.).")
    print("3. Once you see your chats, the script will capture the cookies.")
    print("4. The browser will close automatically.")
    print("="*60 + "\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        
        page.goto("https://claude.ai/login")
        
        try:
            # Wait for user to reach the main chat page
            # No timeout to give user enough time
            print("Waiting for you to complete login...")
            # Match both /chats and /chat/
            page.wait_for_url(lambda url: "/chat" in url, timeout=0)
            
            print("Session detected! Capturing cookies...")
            cookies = context.cookies()
            
            # Format cookies as header string
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            
            cookie_file.parent.mkdir(parents=True, exist_ok=True)
            cookie_file.write_text(cookie_str)
            
            print(f"\n✅ Cookies saved successfully to:\n   {cookie_file}\n")
            return True
        except Exception as e:
            print(f"\n❌ Error during login: {e}")
            return False
        finally:
            browser.close()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch Claude.ai usage metrics using session cookies"
    )
    parser.add_argument(
        "cookie_file",
        nargs="?",
        type=Path,
        default=DEFAULT_COOKIE_FILE,
        help=f"Path to cookie file (default: {DEFAULT_COOKIE_FILE})",
    )
    parser.add_argument(
        "--org-id",
        help="Organization UUID (default: from lastActiveOrg cookie)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window (useful for debugging)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress stderr (for use from indicator)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw JSON without pretty-printing",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open a browser to log in and capture cookies automatically",
    )

    args = parser.parse_args()

    if args.login:
        return 0 if interactive_login(args.cookie_file) else 1

    if not args.cookie_file.exists():
        if not args.quiet:
            print(f"Error: Cookie file not found: {args.cookie_file}", file=sys.stderr)
            print("Tip: Run with --login to capture cookies automatically.", file=sys.stderr)
        return 1

    if not args.quiet:
        print("Fetching usage (this may take a moment)...", file=sys.stderr)

    data = get_usage(
        args.cookie_file,
        org_id=args.org_id,
        headless=not args.no_headless,
        quiet=args.quiet,
    )

    if data is None:
        if not args.quiet:
            print(
                "Error: Failed to fetch usage. Cookies may have expired.",
                file=sys.stderr,
            )
        return 1

    if args.raw:
        print(json.dumps(data))
    else:
        print(json.dumps(data, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
