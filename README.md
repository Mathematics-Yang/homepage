# 个人主页

Flask + Jinja 页面，Tailwind CSS 在本地预编译。保留中文/英文、深浅主题、背景模式和 GitHub 图表；也可以导出为静态站点。

## 文件布局

| 路径 | 用途 |
| --- | --- |
| `app.py`、`templates/index.html` | 服务端逻辑与页面模板 |
| `config.json`、`default/default_config.json` | 当前配置与缺省配置 |
| `Introduction*.md`、`TechStack*.md` | 中英文个人介绍与工具箱内容 |
| `public/` | 线上使用的 WebP 图片、CSS 与字体 |
| `assets/css/input.css`、`tailwind.config.js` | Tailwind 构建输入与配置 |
| `data/github_stats.json` | GitHub 数据快照，正常首页请求不需要实时查询 GitHub |
| `scripts/update_github_stats.py`、`.github/workflows/` | 更新快照的脚本和定时工作流 |
| `api/index.py`、`vercel.json` | Vercel 部署入口与缓存规则 |
| `Dockerfile`、`deploy.sh` | Docker 与静态站点构建方式 |
| `background.jpg`、`public/avatar.png` | 保留的原始图片；线上优先使用 WebP，部署时排除原图 |
| `static_build/` | 生成的静态站点，可重新构建，不提交 Git |
| `.venv/`、`node_modules/` | 本地依赖环境，不提交 Git，不上传部署 |

`github_token.txt` 是本地凭据，已排除于 Git、Vercel 和 Docker 构建上下文；也可以通过环境变量 `GH_TOKEN` 或 `GITHUB_TOKEN` 提供凭据。

## 本地运行与构建

在已激活的 Python 虚拟环境中运行：

```sh
python -m pip install -r requirements.txt
npm ci
npm run build:css
python app.py
```

访问 `http://localhost:5000/`。Windows 下也可直接使用 `.venv\Scripts\python.exe` 替代 `python`。

```sh
# 修改模板中的 Tailwind 类或配色后重新生成 CSS
npm run build:css

# 生成可发布到 GitHub Pages 等平台的目录
python app.py generate_static

# 按需刷新 GitHub 数据快照（此步骤需要网络）
python scripts/update_github_stats.py
```

## 本次性能优化

- 头像使用 320 × 320 WebP：321,619 字节降至 24,640 字节，原图仍保留。
- 图标使用本地 WOFF2 子集：四套完整字体约 414 KB 缩至 8,176 字节，取消两张外部阻塞样式表，保留现有 43 个图标。
- 工具箱的 54 个徽章标签（27 个不同 URL）使用原生懒加载、异步解码和低优先级。它们仍依赖 shields.io，只在接近视口时加载；原本就延迟加载的 GitHub 卡片和按需加载的 Chart.js 保持原有方式。
- 页面资源链接带内容版本号；Flask 对当前版本资源和文件名含哈希的字体设置长期缓存，未带版本号的资源缓存 1 小时。Vercel 的静态 CSS/图片规则采用 1 小时缓存，字体采用 1 年缓存；首页配置 1 小时 CDN 缓存。修改资源后需重启 Flask 或重新构建/部署以更新版本号。
- 缓存策略依据 [Vercel Cache-Control 文档](https://vercel.com/docs/caching/cache-control-headers)；线上缓存命中情况仍需在部署后检查。

本地验证覆盖：页面文字/图标用法与修改前一致、离线快照渲染、内嵌 JavaScript 语法、动态与静态资源路径、缓存及 304 响应、字体字符映射和轮廓、CSS 与静态站点构建。没有线上地址及可用浏览器，本次未获得真实 LCP、CLS 或 Lighthouse 分数，资源体积减少不等同于相同比例的加载时间改善。

## 资源维护与清理

更换头像时同步更新 `public/avatar.webp`。可用 Pillow 转换原图（仅资源制作时需要，不属于服务器依赖）：

```sh
python -m pip install Pillow
python -c "from PIL import Image; im=Image.open('public/avatar.png').convert('RGB'); im.thumbnail((320,320), Image.Resampling.LANCZOS); im.save('public/avatar.webp', 'WEBP', quality=85, method=6)"
```

图标映射在 `public/icons.css`，来源与许可证见 `public/fonts/NOTICE.md`。添加新图标时，需要一并扩展相应字体子集，而不只是增加 CSS 类。

已清理与根目录原图完全相同的 `default/background.jpg`、未引用的 `index.js` 和 CSS、试验字体及中间文件、静态构建产物和 Python/检查工具缓存。原有受 Git 跟踪的文件可以从历史版本恢复；临时文件已转存到系统临时目录下的 `homepage-cleanup-*` 备份。发布静态站点时按上面的命令重新生成 `static_build/`；构建和缓存目录在后续开发时可能重新产生，已加入忽略规则。
