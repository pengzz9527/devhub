"""
DevTools Hub — 自动化数据采集与更新脚本
========================================
功能：
1. 从 GitHub API 采集各工具 Stars/Forks/Release
2. 更新中英文对比文章中的最新数据
3. Git 提交并推送到 GitHub (触发 Vercel 自动部署)

用法：
  python ~/.hermes/scripts/devtoolshub_auto_update.py
  python ~/.hermes/scripts/devtoolshub_auto_update.py --check-only   # 只看变化不推送
  python ~/.hermes/scripts/devtoolshub_auto_update.py --force        # 强制更新全部

配置：
  首次运行会在 ~/.hermes/scripts/ 下创建 devtoolshub_config.yaml
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────────
SITE_DIR = Path("/root/devtoolshub")
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = SCRIPT_DIR / "devtoolshub_config.yaml"

# ── 工具数据库（名称 → GitHub repo + 分类） ────────────────────
TOOLS = {
    "GitHub Copilot": {
        "repo": None,  # 闭源，无公开 GitHub
        "stars": None,
        "website": "https://github.com/features/copilot/plans",
    },
    "Cursor": {
        "repo": "getcursor/cursor",
        "stars": None,
        "website": "https://cursor.com/pricing",
    },
    "Codeium": {
        "repo": "Exafunction/codeium",
        "stars": None,
        "website": "https://codeium.com/pricing",
    },
    "Windsurf": {
        "repo": None,  # 闭源产品
        "stars": None,
        "website": "https://codeium.com/windsurf",
    },
    "Amazon Q Developer": {
        "repo": None,  # 闭源产品
        "stars": None,
        "website": "https://aws.amazon.com/q/developer/pricing",
    },
    "VS Code": {
        "repo": "microsoft/vscode",
        "stars": None,
        "website": "https://code.visualstudio.com",
    },
    "Zed": {
        "repo": "zed-industries/zed",
        "stars": None,
        "website": "https://zed.dev",
    },
    "JetBrains": {
        "repo": "JetBrains/intellij-community",
        "stars": None,
        "website": "https://jetbrains.com",
    },
    "DuckDB": {
        "repo": "duckdb/duckdb",
        "stars": None,
        "website": "https://duckdb.org",
    },
    "SQLite": {
        "repo": "sqlite/sqlite",
        "stars": None,
        "website": "https://sqlite.org",
    },
    "PostgreSQL": {
        "repo": "postgres/postgres",
        "stars": None,
        "website": "https://postgresql.org",
    },
}

# ── 文章文件映射（中英文） ──────────────────────────────────────
ARTICLES = {
    "ai-code-assistant-comparison": {
        "title": {"en": "AI Coding Assistant", "zh": "AI 编程助手"},
        "files": {
            "en": SITE_DIR / "content/en/post/ai-code-assistant-comparison/index.md",
            "zh": SITE_DIR / "content/zh/post/ai-code-assistant-comparison/index.md",
        },
        # 文章头部的工具列表（按表格顺序）
        "tools": ["GitHub Copilot", "Cursor", "Codeium", "Windsurf", "Amazon Q Developer"],
    },
    "ide-comparison": {
        "title": {"en": "IDE Comparison", "zh": "编辑器对比"},
        "files": {
            "en": SITE_DIR / "content/en/post/ide-comparison/index.md",
            "zh": SITE_DIR / "content/zh/post/ide-comparison/index.md",
        },
        "tools": ["VS Code", "Cursor", "Zed", "JetBrains"],
    },
    "database-comparison": {
        "title": {"en": "Database Comparison", "zh": "数据库对比"},
        "files": {
            "en": SITE_DIR / "content/en/post/database-comparison/index.md",
            "zh": SITE_DIR / "content/zh/post/database-comparison/index.md",
        },
        "tools": ["DuckDB", "SQLite", "PostgreSQL"],
    },
}


# ── GitHub API ──────────────────────────────────────────────────
def fetch_github_data(repo: str) -> dict | None:
    """获取 GitHub 仓库的 Stars 和最新 Release 版本"""
    if not repo:
        return None
    api_url = f"https://api.github.com/repos/{repo}"
    headers = {
        "User-Agent": "DevToolsHub-AutoUpdate/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        # 获取仓库信息
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        stars = data.get("stargazers_count", 0)
        forks = data.get("forks_count", 0)
        open_issues = data.get("open_issues_count", 0)
        description = (data.get("description") or "")[:120]

        # 获取最新 Release
        release_url = api_url + "/releases/latest"
        release_tag = None
        release_date = None
        try:
            req2 = urllib.request.Request(release_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                release_data = json.loads(resp2.read().decode())
            release_tag = release_data.get("tag_name")
            release_date = release_data.get("published_at", "")[:10]
        except (urllib.error.HTTPError, json.JSONDecodeError):
            pass  # 有些库没有 release

        return {
            "stars": _fmt_stars(stars),
            "stars_raw": stars,
            "forks": forks,
            "open_issues": open_issues,
            "description": description,
            "release_tag": release_tag,
            "release_date": release_date,
        }
    except Exception as e:
        print(f"  ⚠️  {repo}: {e}")
        return None


def _fmt_stars(n: int) -> str:
    """格式化 Star 数，如 123456 → '123K'"""
    if n >= 1000:
        return f"{n / 1000:.0f}K+"
    return str(n)


# ── Markdown 更新器 ────────────────────────────────────────────
def update_github_stars_in_md(content: str, tool_name: str, stars: str) -> str:
    """更新文章中的 GitHub Stars 数据（匹配 'XXK+ Stars' 或 'N Stars' 或 '🌟 XX' 模式）"""
    patterns = [
        # "GitHub Stars: XXK+" (table row or inline)
        (rf"(?<={re.escape(tool_name)}.*?)(\d+\.?\d*K?\s*\+?\s*Stars?)(?![^|]*\|)", stars + " Stars"),
        # "XXK+" (in star rating columns)
        (rf"(?<=[\|]\s*){re.escape(stars[:-1])}\s*K\s*\+?(?=\s*[\|])", stars),
    ]
    for old_pat, new_val in patterns:
        content = re.sub(old_pat, new_val, content, flags=re.DOTALL)
    return content


def update_stars_table(content: str, stars_dict: dict) -> str:
    """通用的 stars 更新"""
    updated = False
    for tool_name in sorted(stars_dict.keys(), key=len, reverse=True):
        data = stars_dict[tool_name]
        if data and data.get("stars_raw"):
            # Match patterns like "28K+" or "35K+" in the content
            old_stars = str(data["stars"])
            # Find all existing star-like patterns near the tool name
            pattern = rf"(?<={re.escape(tool_name)})(.*?)(\d+\.?\d*K?\+?)(?=\s)"
            # Be more specific — look between pipe characters (table cells)
            for m in re.finditer(re.escape(tool_name), content):
                pos = m.start()
                # Look around for table data
                line_start = content.rfind("\n", 0, pos)
                line_end = content.find("\n", pos)
                if line_start >= 0 and line_end > 0:
                    line = content[line_start:line_end]
                    if "|" in line and tool_name in line:
                        # This line is a table row — replace star-like patterns
                        star_match = re.search(r"(\d+)K", line)
                        if star_match:
                            old_val = star_match.group(0)
                            new_val = f"{data['stars_raw']//1000}K+"
                            if old_val != new_val:
                                line_new = line.replace(old_val, new_val, 1)
                                content = content[:line_start] + line_new + content[line_end:]
                                print(f"  ✅ 更新 {tool_name}: {old_val} → {new_val}")
                                updated = True
    if not updated:
        print("  ℹ️  无变化")
    return content, updated


def update_pricing_table(content: str, lang: str) -> tuple[str, bool]:
    """更新文章底部最后更新时间"""
    today = datetime.utcnow()
    date_str = today.strftime("%B %d, %Y")
    date_str_zh = today.strftime("%Y 年 %m 月 %d 日")

    new_date = date_str_zh if lang == "zh" else date_str
    old_date_pattern = r"Last updated: .*?(\d{4}|[A-Z])"

    match = re.search(old_date_pattern, content)
    if match:
        old_str = match.group(0)
        if lang == "zh":
            new_str = f"最后更新：{new_date}"
        else:
            new_str = f"Last updated: {new_date}"
        content = content.replace(old_str, new_str)
        print(f"  ✅ 更新日期: {new_str}")
        return content, True
    return content, False


# ── 主流程 ──────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  🛠  DevTools Hub — 自动化数据更新")
    print(f"  📅  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)

    check_only = "--check-only" in sys.argv
    force = "--force" in sys.argv

    if check_only:
        print("\n🔍 检查模式（不推送）\n")
    elif force:
        print("\n⚡ 强制更新模式\n")
    else:
        print()

    # ── 第 1 步：采集 GitHub 数据 ──
    print("📡 采集 GitHub 数据...")
    all_data = {}
    for tool_name, tool_info in TOOLS.items():
        repo = tool_info["repo"]
        if repo is None:
            print(f"  ⏭️  {tool_name}: 闭源项目，跳过")
            all_data[tool_name] = None
            continue
        print(f"  🔄  {tool_name} ({repo})...", end=" ")
        data = fetch_github_data(repo)
        if data:
            print(f"⭐ {data['stars']}  🏷️  {data['release_tag'] or 'N/A'}")
        else:
            print("❌ 失败")
        all_data[tool_name] = data
        time.sleep(0.3)  # 避免 GitHub API 限流

    # ── 第 2 步：更新文章 ──
    print("\n📝 更新文章...")
    any_change = False
    for article_key, article_info in ARTICLES.items():
        print(f"\n  📄 {article_info['title']['en']} / {article_info['title']['zh']}")

        for lang, file_path in article_info["files"].items():
            if not file_path.exists():
                print(f"    ⏭️  {lang}: 文件不存在，跳过")
                continue

            content = file_path.read_text(encoding="utf-8")
            changed = False

            # 更新 Stars 数据
            stars_dict = {t: all_data.get(t) for t in article_info["tools"]}
            content, stars_updated = update_stars_table(content, stars_dict)
            if stars_updated:
                changed = True

            # 更新日期
            content, date_updated = update_pricing_table(content, lang)
            if date_updated:
                changed = True

            if changed:
                file_path.write_text(content, encoding="utf-8")
                any_change = True
                print(f"    ✅ {lang}: 已更新")
            else:
                print(f"    ℹ️  {lang}: 无变化")

    # ── 第 3 步：Git 提交并推送 ──
    if any_change and not check_only:
        print("\n📤 Git 提交...")
        os.chdir(str(SITE_DIR))
        os.system("git add -A")
        msg = f"auto: update tool data {datetime.utcnow().strftime('%Y-%m-%d')}"
        ret = os.system(f'git commit -m "{msg}"')
        if ret == 0:
            ret2 = os.system("git push origin main")
            if ret2 == 0:
                print("✅ 已推送至 GitHub，Vercel 自动部署中...")
            else:
                print("⚠️  git push 失败")
        else:
            print("ℹ️  无新提交")
    elif any_change and check_only:
        print("\n🔍 检测到变更（check-only 模式，未推送）")
    else:
        print("\n✅ 所有数据已是最新")

    # ── 输出摘要 ──
    print("\n" + "=" * 55)
    print("  📊 数据摘要")
    print("=" * 55)
    for tool_name, data in all_data.items():
        if data:
            print(f"  ⭐ {data['stars']:>6s}  {data['release_tag'] or '':>12s}  {tool_name}")
        else:
            print(f"  {'❌':>6s}  {'N/A':>12s}  {tool_name}")

    print("\n✅ 完成")


if __name__ == "__main__":
    main()
