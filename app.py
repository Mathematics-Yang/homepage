import json
import os
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import jinja2
import markdown
import requests
from flask import Flask, abort, jsonify, render_template, send_from_directory


# 读取配置文件
def load_config():
    global config
    config_path = os.path.join(BASE_DIR, "config.json")
    default_config_path = os.path.join(BASE_DIR, "default", "default_config.json")

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        if os.path.exists(default_config_path):
            print("config.json不存在，从默认配置读取")
            with open(default_config_path, encoding="utf-8") as f:
                config = json.load(f)
            # Vercel 文件系统只读，不尝试复制
            try:
                shutil.copy2(default_config_path, config_path)
            except OSError as error:
                app.logger.info("无法写入默认配置: %s", error)
        else:
            print("使用内置默认配置")
            config = {
                "github_url": "https://github.com/Mathematics-Yang",
                "dark_mode": "auto",
                "name": "Jianan Yang",
                "bio": "Graduate Student @ XJTU",
                "introduction_file": "Introduction.md",
                "github_token": "",
                "theme": {
                    "primary_color": "#6a11cb",
                    "secondary_color": "#2575fc",
                    "dark_primary_color": "#a855f7",
                    "dark_secondary_color": "#60a5fa",
                },
                "background": {
                    "image": "background.webp",
                    "blur": 8,
                    "overlay_opacity": 0.6,
                    "overlay_color": "#121212",
                    "dark_overlay_color": "#000000",
                },
                "contact": {},
                "academic_profile": {
                    "affiliation_zh": "西安交通大学",
                    "affiliation_en": "Xi'an Jiaotong University",
                    "position_zh": "硕士研究生",
                    "position_en": "Graduate Student",
                    "location_zh": "中国 · 西安",
                    "location_en": "Xi'an, China",
                    "status_zh": "欢迎交流与合作",
                    "status_en": "Open to Ideas & Collaboration",
                },
                "current_focus": [],
                "education": [],
                "experience": [],
                "selected_articles": [],
            }

    # 确保所有必要字段存在，防止模板报错
    if "theme" not in config:
        config["theme"] = {}
    theme_defaults = {
        "primary_color": "#6a11cb",
        "secondary_color": "#2575fc",
        "dark_primary_color": "#a855f7",
        "dark_secondary_color": "#60a5fa",
    }
    for key, value in theme_defaults.items():
        if key not in config["theme"]:
            config["theme"][key] = value

    if "background" not in config:
        config["background"] = {}
    bg_defaults = {
        "image": "background.webp",
        "blur": 8,
        "overlay_opacity": 0.6,
        "overlay_color": "#121212",
        "dark_overlay_color": "#000000",
    }
    for key, value in bg_defaults.items():
        if key not in config["background"]:
            config["background"][key] = value

    if "contact" not in config:
        config["contact"] = {}
    if "academic_profile" not in config:
        config["academic_profile"] = {}
    if "current_focus" not in config:
        config["current_focus"] = []
    if "education" not in config:
        config["education"] = []
    if "experience" not in config:
        config["experience"] = []
    if "selected_articles" not in config:
        config["selected_articles"] = []


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
load_config()

# 全局缓存
_cache = {"github_info": None, "cache_time": 0}
CACHE_TTL = 3600
STATS_CACHE_PATH = os.path.join(BASE_DIR, "data", "github_stats.json")
STATS_CACHE_TTL = 21600
GITHUB_REQUEST_TIMEOUT = 8
MAX_REPOSITORY_WORKERS = 6
_stats_cache = {"username": None, "data": None, "cache_time": 0}
_thread_state = threading.local()
REPOSITORY_DESCRIPTIONS = {
    "cs231n-documents-2025": {
        "zh": "斯坦福 CS231n 2025 课程资料，包括课件、讨论内容及中英文作业。",
        "en": "Course materials for Stanford CS231n 2025, including slides, discussions, and assignments in English and Chinese.",
    },
    "deep-learning-from-Scratch": {
        "zh": "《深度学习入门：基于 Python 的理论与实现》学习笔记与实践。",
        "en": "Notes and implementations for Deep Learning from Scratch, covering neural-network theory and practice in Python.",
    },
    "Toy-MiniMind": {
        "zh": "基于 MiniMind 的重构实践，通过交互式笔记本从零拆解大模型核心代码。",
        "en": "A refactored MiniMind learning project that explains core LLM code step by step through interactive notebooks.",
    },
    "PINN-from-Scratch": {
        "zh": "从零实现物理信息神经网络，以一维热传导方程为示例。",
        "en": "A physics-informed neural network implemented from scratch for the one-dimensional heat equation.",
    },
    "Hsuan-Tien-Lin-s-Machine-Learning-Notes": {
        "zh": "台湾大学林轩田老师《机器学习基石》与《机器学习技法》课程笔记。",
        "en": "Study notes for Hsuan-Tien Lin's Machine Learning Foundations and Machine Learning Techniques courses.",
    },
    "Deep-Learning-Advanced-Natural-Language-Processing": {
        "zh": "《深度学习进阶：自然语言处理》中文学习笔记与 Jupyter Notebook 实践。",
        "en": "Chinese study notes and Jupyter Notebook exercises for Deep Learning 2: Natural Language Processing.",
    },
}
LANGUAGE_COLORS = {
    "C": "#555555",
    "C++": "#f34b7d",
    "Cython": "#fedf5b",
    "Dockerfile": "#384d54",
    "HTML": "#e34c26",
    "JavaScript": "#f1e05a",
    "Jupyter Notebook": "#da5b0b",
    "Python": "#3572a5",
    "Shell": "#89e051",
    "TypeScript": "#3178c6",
}
MARKDOWN_EXTENSIONS = ["extra", "codehilite", "toc", "tables", "md_in_html"]
MARKDOWN_EXTENSION_CONFIGS = {
    "codehilite": {"css_class": "highlight", "linenums": False}
}
CENTERED_DIV_PATTERN = re.compile(
    r"<div(?P<attributes>[^>]*\balign\s*=\s*['\"]center['\"][^>]*)>",
    re.IGNORECASE,
)


def render_markdown(markdown_text):
    """Render Markdown, including Markdown nested in centered HTML containers."""

    def enable_nested_markdown(match):
        attributes = match.group("attributes")
        if re.search(r"\bmarkdown\s*=", attributes, re.IGNORECASE):
            return match.group(0)
        return f'<div{attributes} markdown="1">'

    normalized_text = CENTERED_DIV_PATTERN.sub(enable_nested_markdown, markdown_text)
    return markdown.markdown(
        normalized_text,
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )


class ErrorResponse:
    """Minimal response object returned when a GitHub request fails."""

    def __init__(self, message, status_code=503):
        self.status_code = status_code
        self.text = message


def get_github_token():
    """Read a GitHub token without exposing it to logs."""
    token = os.environ.get("GH_TOKEN", "") or os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token

    token_file = os.path.join(BASE_DIR, "github_token.txt")
    try:
        if os.path.exists(token_file):
            with open(token_file, encoding="utf-8") as file:
                return file.read().strip().replace('"', "").replace("'", "")
    except OSError as error:
        app.logger.warning("无法读取 GitHub token 文件: %s", error)

    return config.get("github_token", "")


# 创建通用的GitHub API请求函数
def get_http_session():
    """Return one connection-pooled HTTP session per worker thread."""
    if not hasattr(_thread_state, "session"):
        _thread_state.session = requests.Session()
    return _thread_state.session


def make_github_request(
    url,
    timeout=GITHUB_REQUEST_TIMEOUT,
    accept="application/vnd.github+json",
):
    try:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        github_token = get_github_token()
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        return get_http_session().get(url, headers=headers, timeout=timeout)
    except requests.RequestException as error:
        app.logger.warning("GitHub API 请求失败 (%s): %s", url, error)
        return ErrorResponse(str(error))


def get_github_repositories(username):
    """Fetch all public repositories for a GitHub user."""
    repositories = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{username}/repos"
            f"?sort=pushed&per_page=100&page={page}"
        )
        response = make_github_request(url)
        if response.status_code != 200:
            app.logger.warning(
                "无法获取 GitHub 仓库列表，状态码: %s", response.status_code
            )
            break

        page_items = response.json()
        if not isinstance(page_items, list):
            app.logger.warning("GitHub 仓库列表响应格式无效")
            break

        repositories.extend(page_items)
        if len(page_items) < 100:
            break
        page += 1

    return repositories


def select_popular_repositories(username, repositories, limit=6):
    """Select substantive repositories ordered by stars and recent activity."""
    selected = sorted(
        (
            repository
            for repository in repositories
            if not repository.get("fork", False)
            and not repository.get("archived", False)
            and repository.get("name", "").lower() not in {username.lower(), "homepage"}
        ),
        key=lambda repository: (
            repository.get("stargazers_count", 0),
            repository.get("pushed_at") or "",
        ),
        reverse=True,
    )[:limit]
    public_fields = (
        "name",
        "html_url",
        "stargazers_count",
        "description",
        "language",
        "pushed_at",
    )
    results = []
    for repository in selected:
        item = {field: repository.get(field) for field in public_fields}
        localized_description = REPOSITORY_DESCRIPTIONS.get(repository["name"], {})
        item["description_zh"] = localized_description.get("zh") or item["description"]
        item["description_en"] = localized_description.get("en") or item["description"]
        item["language_color"] = LANGUAGE_COLORS.get(
            item["language"], "#94a3b8"
        )
        results.append(item)
    return results


# 从 GitHub API 获取用户信息
def get_github_user_info():
    print("开始获取GitHub用户信息")
    github_url = config.get("github_url", "https://github.com/example")
    username = github_url.rstrip("/").split("/")[-1]
    print(f"配置的GitHub URL: {github_url}")
    print(f"提取的用户名: {username}")

    snapshot = load_stats_snapshot(username)
    if snapshot and snapshot.get("popular_repos") is not None:
        popular_repositories = snapshot.get("popular_repos", [])
        for repository in popular_repositories:
            repository["language_color"] = LANGUAGE_COLORS.get(
                repository.get("language"), "#94a3b8"
            )
        return {
            "username": username,
            "avatar_url": snapshot.get("avatar_url", ""),
            "name": snapshot.get("name") or config.get("name", username),
            "bio": config.get("bio", "Python Developer"),
            "total_repos": snapshot.get("total_repos", 0),
            "total_stars": snapshot.get("total_stars", 0),
            "readme_content_en": get_local_readme("en"),
            "readme_content_zh": get_local_readme("zh"),
            "popular_repos": popular_repositories,
            "language_distribution": snapshot.get("language_distribution", []),
            "star_history": snapshot.get("star_history", []),
        }

    try:
        print(f"准备请求GitHub API: https://api.github.com/users/{username}")

        # 获取用户信息
        user_response = make_github_request(f"https://api.github.com/users/{username}")
        print(f"GitHub API响应状态码: {user_response.status_code}")

        if user_response.status_code != 200:
            raise RuntimeError(f"GitHub 用户接口返回 {user_response.status_code}")

        user_data = user_response.json()
        print(f"成功获取用户数据: {user_data.get('name')}, {user_data.get('login')}")

        repositories = get_github_repositories(username)
        total_repos = user_data.get("public_repos", len(repositories))
        total_stars = sum(
            repository.get("stargazers_count", 0) for repository in repositories
        )

        sorted_repositories = sorted(
            repositories,
            key=lambda repository: repository.get("pushed_at") or "",
            reverse=True,
        )
        popular_repositories = select_popular_repositories(username, repositories)
        stats = collect_github_stats(username, sorted_repositories)

        return {
            "username": username,
            "avatar_url": user_data.get("avatar_url"),
            "name": user_data.get("name") or config.get("name") or username,
            "bio": config.get("bio", "Python Developer"),
            "total_repos": total_repos,
            "total_stars": total_stars,
            "readme_content_en": get_local_readme("en"),
            "readme_content_zh": get_local_readme("zh"),
            "popular_repos": popular_repositories,
            "language_distribution": stats["language_distribution"],
            "star_history": stats["star_history"],
        }
    except Exception:
        app.logger.exception("获取 GitHub 用户信息失败")

    # 如果获取失败，返回默认值
    return {
        "username": username,
        "avatar_url": "",
        "name": config.get("name", "Example User"),
        "bio": config.get("bio", "Python Developer"),
        "total_repos": 0,
        "total_stars": 0,
        "readme_content_en": get_local_readme("en"),
        "readme_content_zh": get_local_readme("zh"),
        "popular_repos": [],
        "language_distribution": [],
        "star_history": [],
    }


def load_stats_snapshot(username):
    """Load the latest public GitHub statistics snapshot from disk."""
    current_time = time.time()
    if (
        _stats_cache["username"] == username
        and _stats_cache["data"] is not None
        and current_time - _stats_cache["cache_time"] < STATS_CACHE_TTL
    ):
        return _stats_cache["data"]

    try:
        with open(STATS_CACHE_PATH, encoding="utf-8") as file:
            snapshot = json.load(file)

        if snapshot.get("username") != username:
            raise ValueError("统计快照与当前 GitHub 用户不匹配")

        _stats_cache.update(
            {"username": username, "data": snapshot, "cache_time": current_time}
        )
        return snapshot
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        app.logger.info("GitHub 统计快照不可用，将实时生成: %s", error)
        return None


def collect_github_stats(username, repositories):
    """Collect independent statistics concurrently for snapshot generation."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        language_future = executor.submit(
            get_language_distribution, username, repositories
        )
        star_future = executor.submit(get_star_history, username, repositories)

        return {
            "language_distribution": language_future.result(),
            "star_history": star_future.result(),
        }


# 获取真实的语言分布数据
def get_language_distribution(username, repos):
    """
    从 GitHub API 获取用户所有仓库的真实语言字节数分布
    """
    try:
        print("开始获取真实语言分布数据")

        language_bytes = {}
        repositories = [repo for repo in repos[:15] if not repo.get("fork", False)]

        def fetch_languages(repo):
            languages_url = (
                f"https://api.github.com/repos/{username}/{repo['name']}/languages"
            )
            response = make_github_request(languages_url)
            if response.status_code != 200:
                app.logger.warning(
                    "无法获取仓库 %s 的语言数据，状态码: %s",
                    repo["name"],
                    response.status_code,
                )
                return {}
            data = response.json()
            return data if isinstance(data, dict) else {}

        with ThreadPoolExecutor(max_workers=MAX_REPOSITORY_WORKERS) as executor:
            for languages_data in executor.map(fetch_languages, repositories):
                for language, bytes_count in languages_data.items():
                    language_bytes[language] = (
                        language_bytes.get(language, 0) + bytes_count
                    )

        if not language_bytes:
            print("未获取到语言数据")
            return []

        # GitHub 官方语言颜色映射
        github_language_colors = {
            "Python": "#3572A5",
            "JavaScript": "#f1e05a",
            "TypeScript": "#3178c6",
            "Java": "#b07219",
            "C": "#555555",
            "C++": "#f34b7d",
            "C#": "#178600",
            "Go": "#00ADD8",
            "Rust": "#dea584",
            "Ruby": "#701516",
            "PHP": "#4F5D95",
            "Swift": "#F05138",
            "Kotlin": "#A97BFF",
            "Dart": "#00B4AB",
            "Scala": "#c22d40",
            "R": "#198CE7",
            "MATLAB": "#e16737",
            "Shell": "#89e051",
            "Bash": "#89e051",
            "PowerShell": "#012456",
            "HTML": "#e34c26",
            "CSS": "#563d7c",
            "SCSS": "#c6538c",
            "Less": "#1d365d",
            "Vue": "#41b883",
            "Svelte": "#ff3e00",
            "Lua": "#000080",
            "Perl": "#0298c3",
            "Haskell": "#5e5086",
            "Elixir": "#6e4a7e",
            "Clojure": "#db5855",
            "Erlang": "#B83998",
            "Julia": "#a270ba",
            "Objective-C": "#438eff",
            "Assembly": "#6E4C13",
            "Makefile": "#427819",
            "Dockerfile": "#384d54",
            "TeX": "#3D6117",
            "Jupyter Notebook": "#DA5B0B",
            "Vim Script": "#199f4b",
            "Emacs Lisp": "#c065db",
            "CMake": "#DA3434",
            "Batchfile": "#C1F12E",
            "Fortran": "#4d41b1",
            "VHDL": "#adb2cb",
            "Verilog": "#b2b7f8",
            "Cuda": "#3A4E3A",
            "Cython": "#fedf5b",
        }

        # 按字节数排序，取前 10 种语言
        sorted_languages = sorted(
            language_bytes.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # 计算总字节数（仅前10种）
        total_bytes = sum(bytes_count for _, bytes_count in sorted_languages)

        # 构建结果
        distribution = []
        for lang, bytes_count in sorted_languages:
            color = github_language_colors.get(lang, "#858585")
            percentage = round((bytes_count / total_bytes) * 100, 1)
            distribution.append(
                {
                    "name": lang,
                    "color": color,
                    "bytes": bytes_count,
                    "percentage": percentage,
                }
            )

        print(f"语言分布: {[(d['name'], d['percentage']) for d in distribution]}")
        return distribution

    except Exception as e:
        print(f"获取语言分布数据异常: {e}")
        return []


# 获取所有项目的 Star History
def get_star_history(username, repos):
    """
    获取用户所有仓库的 star 数随时间的累计变化
    通过遍历有 star 的仓库，获取每个 star 的时间戳
    """
    try:
        print("开始获取 Star History 数据")

        # 筛选出有 star 的仓库
        starred_repos = [r for r in repos if r.get("stargazers_count", 0) > 0]

        if not starred_repos:
            print("没有仓库有 star，返回空数据")
            return []

        def fetch_repo_stars(repo):
            events = []
            repo_name = repo["name"]
            star_count = repo.get("stargazers_count", 0)
            try:
                # 使用 star 详情 API（包含时间戳），并读取全部分页。
                page_count = (star_count + 99) // 100
                for page in range(1, page_count + 1):
                    stars_url = (
                        f"https://api.github.com/repos/{username}/{repo_name}/stargazers"
                        f"?per_page=100&page={page}"
                    )
                    response = make_github_request(
                        stars_url,
                        accept="application/vnd.github.star+json",
                    )
                    if response.status_code != 200:
                        app.logger.warning(
                            "无法获取仓库 %s 的 star 记录，状态码: %s",
                            repo_name,
                            response.status_code,
                        )
                        break

                    for stargazer in response.json():
                        starred_at = stargazer.get("starred_at", "")
                        if starred_at:
                            events.append(starred_at)

            except Exception as e:
                print(f"获取仓库 {repo_name} 的 star 数据时出错: {e}")
            return events

        star_events = []
        with ThreadPoolExecutor(max_workers=MAX_REPOSITORY_WORKERS) as executor:
            for repo_events in executor.map(fetch_repo_stars, starred_repos):
                star_events.extend(repo_events)

        if not star_events:
            print("没有获取到 star 事件数据")
            return []

        # 按时间排序
        star_events.sort()

        # 构建累计 star 数据，按月聚合
        monthly_data = {}
        cumulative = 0

        for event_time in star_events:
            try:
                dt = datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ")
                month_key = dt.strftime("%Y-%m")
                cumulative += 1
                monthly_data[month_key] = cumulative
            except (TypeError, ValueError) as error:
                app.logger.warning("忽略无效的 star 时间 %r: %s", event_time, error)

        if not monthly_data:
            return []

        # 填充缺失的月份（确保曲线连续）
        sorted_months = sorted(monthly_data.keys())
        first_month = sorted_months[0]
        last_month = datetime.now().strftime("%Y-%m")

        # 生成从第一个月到当前月的所有月份
        all_months = []
        current = datetime.strptime(first_month, "%Y-%m")
        end = datetime.strptime(last_month, "%Y-%m")

        while current <= end:
            all_months.append(current.strftime("%Y-%m"))
            # 下一个月
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        # 填充数据
        result = []
        last_value = 0
        for month in all_months:
            if month in monthly_data:
                last_value = monthly_data[month]
            result.append({"month": month, "stars": last_value})

        # 如果数据点太多，进行采样（保留最多 24 个点）
        if len(result) > 24:
            step = len(result) / 24
            sampled = []
            for i in range(24):
                idx = int(i * step)
                sampled.append(result[idx])
            # 确保最后一个点是最新的
            sampled[-1] = result[-1]
            result = sampled

        print(f"Star History: {len(result)} 个数据点, 总计 {result[-1]['stars']} stars")
        return result

    except Exception as e:
        print(f"获取 Star History 异常: {e}")
        import traceback

        traceback.print_exc()
        return []


def get_local_markdown(config_key, default_filename, fallback_html):
    """Render a configured local Markdown file."""
    try:
        file_path = os.path.join(BASE_DIR, config.get(config_key, default_filename))
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as f:
                return render_markdown(f.read())
    except Exception as e:
        app.logger.warning("读取本地 Markdown 出错 (%s): %s", config_key, e)
    return fallback_html


# 读取本地个人介绍文件
def get_local_readme(language="en"):
    config_key = f"introduction_file_{language}"
    default_filename = config.get("introduction_file", "Introduction.md")
    if language == "zh":
        fallback_html = "<p>个人介绍暂时不可用。</p>"
    else:
        fallback_html = "<p>The introduction is temporarily unavailable.</p>"
    return get_local_markdown(config_key, default_filename, fallback_html)


def get_local_tech_stack(language="en"):
    """Read the localized toolkit content."""
    filename = "TechStack.zh.md" if language == "zh" else "TechStack.md"
    return get_local_markdown(f"tech_stack_file_{language}", filename, "")


@app.route("/")
def index():
    try:
        global _cache
        current_time = time.time()

        if _cache["github_info"] and (current_time - _cache["cache_time"] < CACHE_TTL):
            github_info = _cache["github_info"]
        else:
            github_info = get_github_user_info()
            _cache["github_info"] = github_info
            _cache["cache_time"] = current_time

        # 补全 contact
        default_contact = {
            "email": "",
            "orcid": "",
            "cv": "",
            "qq": "",
            "wechat": "",
            "bilibili": "",
            "douyin": "",
            "xiaohongshu": "",
            "google_scholar": "",
            "kaggle": "",
        }
        if "contact" not in config:
            config["contact"] = default_contact
        else:
            for key, value in default_contact.items():
                if key not in config["contact"]:
                    config["contact"][key] = value

        # 检查背景图片
        background_image = config.get("background", {}).get("image", "background.webp")
        possible_paths = [
            os.path.join(BASE_DIR, background_image),
            os.path.join(BASE_DIR, "public", background_image),
            os.path.join(BASE_DIR, "static", background_image),
        ]

        background_exists = False
        background_path = background_image

        for path in possible_paths:
            if os.path.exists(path):
                background_exists = True
                if "public" in path:
                    background_path = f"/{background_image}"
                elif "static" in path:
                    background_path = f"/static/{background_image}"
                break

        local_avatar_source = os.path.join(BASE_DIR, "public", "avatar.png")
        avatar_path = (
            "/avatar.png"
            if os.path.isfile(local_avatar_source)
            else github_info.get("avatar_url", "")
        )

        return render_template(
            "index.html",
            github_info=github_info,
            config=config,
            now=datetime.now(),
            background_exists=background_exists,
            background_path=background_path,
            avatar_path=avatar_path,
            static_css_path="/styles.css",
            tech_stack_content_zh=get_local_tech_stack("zh"),
            tech_stack_content_en=get_local_tech_stack("en"),
        )
    except Exception:
        app.logger.exception("渲染首页失败")
        return "页面暂时无法加载，请稍后重试。", 500


@app.route("/api/config")
def get_config():
    public_config = {
        key: value for key, value in config.items() if key != "github_token"
    }
    return jsonify(public_config)


@app.route("/styles.css")
def serve_stylesheet():
    """Serve the compiled stylesheet during local Flask development."""
    return send_from_directory(os.path.join(BASE_DIR, "public"), "styles.css")


# 提供根目录下的静态文件访问
@app.route("/<path:filename>")
def serve_root_file(filename):
    # 只允许访问特定的文件类型
    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".svg",
        ".css",
        ".js",
    }
    file_ext = os.path.splitext(filename)[1].lower()

    if file_ext not in allowed_extensions:
        abort(404)

    for directory in (BASE_DIR, os.path.join(BASE_DIR, "public")):
        if os.path.isfile(os.path.join(directory, filename)):
            return send_from_directory(directory, filename)
    abort(404)


def generate_static_html():
    """生成可部署到 GitHub Pages 的静态文件。"""
    print("开始生成静态 HTML 文件...")

    static_dir = os.path.join(BASE_DIR, "static_build")
    os.makedirs(static_dir, exist_ok=True)

    try:
        for filename in os.listdir(static_dir):
            file_path = os.path.join(static_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

        template_dir = os.path.join(BASE_DIR, "templates")
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )
        template = env.get_template("index.html")

        background_image = config["background"]["image"]
        background_source = os.path.join(BASE_DIR, background_image)
        if not os.path.isfile(background_source):
            background_source = os.path.join(BASE_DIR, "public", background_image)
        background_exists = os.path.isfile(background_source)
        avatar_source = os.path.join(BASE_DIR, "public", "avatar.png")
        avatar_exists = os.path.isfile(avatar_source)
        github_info = get_github_user_info()

        render_args = {
            "config": config,
            "github_info": github_info,
            "now": datetime.now(),
            "background_exists": background_exists,
            "background_path": os.path.basename(background_image),
            "avatar_path": (
                "avatar.png" if avatar_exists else github_info.get("avatar_url", "")
            ),
            "static_css_path": "styles.css",
            "tech_stack_content_zh": get_local_tech_stack("zh"),
            "tech_stack_content_en": get_local_tech_stack("en"),
        }

        print("渲染HTML模板...")
        html_content = template.render(**render_args)

        html_path = os.path.join(static_dir, "index.html")
        with open(html_path, "w", encoding="utf-8") as file:
            file.write(html_content)

        print(f"静态HTML文件已保存到: {html_path}")

        if background_exists:
            destination = os.path.join(static_dir, os.path.basename(background_image))
            shutil.copy2(background_source, destination)
            print(f"已复制资源文件: {background_image}")

        if avatar_exists:
            shutil.copy2(avatar_source, os.path.join(static_dir, "avatar.png"))
            print("已复制资源文件: public/avatar.png")

        stylesheet_source = os.path.join(BASE_DIR, "public", "styles.css")
        if os.path.isfile(stylesheet_source):
            shutil.copy2(stylesheet_source, os.path.join(static_dir, "styles.css"))
            print("已复制资源文件: public/styles.css")

        print("\n静态文件生成成功！")
        print(f"输出目录: {static_dir}")
    except Exception:
        app.logger.exception("生成静态文件失败")
        return False

    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "generate_static":
        sys.exit(0 if generate_static_html() else 1)
    else:
        debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "5000"))
        app.run(debug=debug, host=host, port=port)
