# Jianan Yang · Personal Homepage

用于展示个人简介、研究成果、教育经历与开源项目的个人主页。基于 **Flask + Jinja + Tailwind CSS** 构建，支持动态运行，也可以导出为静态站点。

[快速开始](#快速开始) · [内容与配置](#内容与配置) · [部署方式](#部署方式) · [性能设计](#性能设计) · [资源维护](#资源维护)

## 功能概览

- **双语内容**：支持中文与英文切换，个人介绍和工具箱分别通过 Markdown 维护。
- **主题切换**：支持浅色、深色及跟随系统的主题设置。
- **个人展示**：集中展示个人资料、教育与实习经历、研究成果和热门项目。
- **GitHub 数据**：展示仓库统计、Star 趋势和语言分布，使用本地快照减少实时 API 请求。
- **响应式布局**：适配桌面与移动设备，并提供背景专注模式。

## 快速开始

需要 **Python 3.10–3.13**、**Node.js 与 npm**，以及 Git。Python 依赖与版本范围分别见 [requirements.txt](requirements.txt) 和 [pyproject.toml](pyproject.toml)。

### 1. 获取项目

```bash
git clone https://github.com/Mathematics-Yang/homepage.git
cd homepage
```

### 2. 创建 Python 环境并安装依赖

按操作系统选择对应命令：

<details>
<summary>Windows · PowerShell</summary>

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

</details>

<details>
<summary>macOS / Linux · Shell</summary>

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

</details>

### 3. 构建样式并启动

```bash
npm ci
npm run build:css
```

**Windows：**

```powershell
.\.venv\Scripts\python.exe app.py
```

**macOS / Linux：**

```bash
./.venv/bin/python app.py
```

浏览器打开 **[http://localhost:5000](http://localhost:5000)** 即可预览。

> 下文的 `python` 命令均指项目虚拟环境中的 Python。可以激活虚拟环境，也可以像上面一样使用解释器的完整相对路径。

## 内容与配置

日常更新主要涉及配置文件和 Markdown，无需修改页面逻辑。

| 想要修改的内容 | 对应文件 |
| --- | --- |
| 联系方式、教育经历、研究成果、主题与背景设置 | [config.json](config.json) |
| 中文 / 英文个人介绍 | [Introduction.zh.md](Introduction.zh.md) / [Introduction.md](Introduction.md) |
| 中文 / 英文工具箱 | [TechStack.zh.md](TechStack.zh.md) / [TechStack.md](TechStack.md) |
| 页面结构与交互 | [templates/index.html](templates/index.html) |
| Tailwind 样式与配色 | [assets/css/input.css](assets/css/input.css)、[tailwind.config.js](tailwind.config.js) |
| GitHub 数据快照 | [data/github_stats.json](data/github_stats.json) |
| 头像、背景、图标字体与编译后的 CSS | [public/](public/) |

[app.py](app.py) 负责页面渲染、资源服务与静态导出；[default/default_config.json](default/default_config.json) 提供缺省配置。

修改 Tailwind 类名或配色后，重新生成样式：

```bash
npm run build:css
```

### GitHub 数据更新

首页优先读取与当前 GitHub 用户匹配的本地快照。快照可用时，无需等待 GitHub API 即可渲染；缺失或不匹配时，会尝试实时获取数据。

手动刷新快照：

```bash
python scripts/update_github_stats.py
```

仓库还配置了 [Update GitHub stats](.github/workflows/update-github-stats.yml) 工作流，计划每 6 小时更新一次，也支持手动触发。更换 `github_url` 后，应同步生成对应用户的快照。

访问 GitHub API 时，可通过环境变量 `GH_TOKEN` 或 `GITHUB_TOKEN` 提供凭据。本地也支持 `github_token.txt`；该文件已排除于 Git、Vercel 和 Docker 构建上下文。请勿将 Token 写入公开配置或提交到仓库。

## 部署方式

### Vercel

仓库包含 [api/index.py](api/index.py) 入口和 [vercel.json](vercel.json) 配置，可用于部署 Flask 版本。

`public/styles.css` 已纳入版本控制。修改页面样式后，先在本地重新构建 CSS，再将生成文件与源码一同提交；需要 GitHub API 凭据时，在部署环境中配置环境变量。

### 静态站点

导出 HTML、样式、图片和字体：

```bash
npm run build:css
python app.py generate_static
```

生成的 `static_build/` 可发布到 GitHub Pages 或其他静态托管服务。部署时上传该目录中的完整内容，而不是直接发布 Flask 源码。

静态版本的个人信息与统计数据在构建时写入页面；内容更新后需重新构建并发布。`static_build/` 是可重新生成的产物，不提交 Git。

### Docker

先确保 CSS 已构建，再创建并运行镜像：

```bash
npm run build:css
docker build -t personal-homepage .
docker run --rm -p 5000:5000 personal-homepage
```

镜像使用仓库中的 [Dockerfile](Dockerfile)。此外，[deploy.sh](deploy.sh) 提供安装依赖、本地运行和静态构建等辅助命令，可在 Bash、Git Bash 或 WSL 中使用。

## 性能设计

页面采用预编译样式、本地图标字体和按需加载资源，减少首屏对第三方服务的依赖。

| 优化项 | 调整前 | 当前方案 |
| --- | --- | --- |
| 头像 | PNG，约 314 KiB | WebP，约 24 KiB |
| 图标字体 | 完整字体，约 404 KiB | 本地子集，约 8 KiB，覆盖 43 个图标 |
| 外部图标样式表 | 2 张阻塞样式表 | 本地 CSS |
| 工具箱徽章 | 54 个图片标签直接加载 | 原生懒加载、异步解码与低优先级 |

以上体积为资源文件大小对比，实际加载速度还取决于网络与托管环境。工具箱徽章和 GitHub 概览卡片仍使用外部服务；Chart.js 在切换到分析视图时按需加载。

缓存按资源类型配置：

- **首页**：配置 1 小时 CDN 缓存，并允许在后台更新过期内容。
- **静态资源**：链接带内容版本号；Flask 对当前版本资源及带哈希文件名的字体设置长期缓存。
- **Vercel 静态文件**：CSS 和图片缓存 1 小时，字体缓存 1 年。

修改资源后，重启 Flask 或重新构建、部署，以更新资源版本号。具体实现见 [app.py](app.py) 与 [vercel.json](vercel.json)。

## 资源维护

### 更换头像与背景

线上优先使用 `public/avatar.webp` 和 `public/background.webp`。原始图片 `public/avatar.png` 与根目录下的 `background.jpg` 保留用于后续编辑，默认不会上传到 Vercel 或打包进 Docker 镜像。

更换头像后，可用 Pillow 生成 WebP。Pillow 仅用于资源制作，不属于服务器运行依赖：

```bash
python -m pip install Pillow
python -c "from PIL import Image; im=Image.open('public/avatar.png').convert('RGB'); im.thumbnail((320,320), Image.Resampling.LANCZOS); im.save('public/avatar.webp', 'WEBP', quality=85, method=6)"
```

### 添加图标

图标映射位于 [public/icons.css](public/icons.css)。添加新图标时，需要同时扩展对应字体子集；仅添加 CSS 类名不会自动引入新字形。字体来源与许可说明见 [public/fonts/NOTICE.md](public/fonts/NOTICE.md)。

### 本地生成文件

`.venv/`、`node_modules/`、`static_build/` 和各类缓存目录均已加入忽略规则。它们用于本地开发或构建，不属于需要提交的项目内容。

## 许可证

项目代码遵循 [MIT License](LICENSE)。图标字体遵循各自的许可条款，详见 [字体许可说明](public/fonts/NOTICE.md)。
