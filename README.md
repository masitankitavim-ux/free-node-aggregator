# Free Node Aggregator · 免费节点自动聚合订阅

每天自动从多个开源免费节点项目抓取节点 → 去重 → **真实连通性测试** → 按
`国旗 地区 | 延迟 | 来源` 打标记 → 生成 Clash / Base64 两种订阅，并提交回仓库。
直接订阅仓库里的 raw 链接即可。

> ⚠️ 免费节点来源公开、随时失效，仅供学习 / 测试网络连通性使用。请勿用于任何违法用途。

## 特性

- **多源聚合**：13 个订阅源（10 个项目），base64 与 Clash YAML 两种格式都支持
- **协议支持**：vmess / vless / trojan / ss / hysteria2 / tuic
- **去重**：按 `类型 + 服务器 + 端口 + 凭据` 去重；过滤内网 / 环回 / 保留地址
- **真实连通性测试**：用 mihomo 实际发一次 HTTP 请求穿过每个节点，只保留真正能通的
- **两级筛选**：先 TCP 快速预筛（砍掉大部分死节点），再 mihomo 真穿透，兼顾速度与准确性
- **打标记**：节点名 = `🇺🇸 US | 🟢128ms | v2rayfree-001`
- **策略组**：自动生成 `节点选择 / 自动选择 / 按地区分组 / 全球直连`
- **零成本**：纯 GitHub Actions 运行，无需服务器

## 为什么不用 TCP ping 测速

最初的版本用「TCP 连接耗时」当延迟。**这是错的**：大量免费节点是「CDN 前置」的
（server 填的是 Fastly / Cloudflare 的 anycast IP），GitHub 机房连这些 CDN 边缘只要 1ms，
但节点背后的代理服务早就死了。结果就是测出来满屏 1ms / 2ms，**全部用不了**。

现在改为真实穿透测试：起一个 mihomo 实例，把每个节点挂上去，调它的 delay 接口
**实际发一次 HTTP 请求**（`http://www.gstatic.com/generate_204`）穿过该节点。
只有真正通的节点才会返回延迟，其余全部丢弃。

## 目录结构

```
free-node-aggregator/
├── aggregator.py                 # 主程序：抓取/解析/去重/预筛/真测/生成订阅
├── config.yaml                   # 节点源 + 输出/测试/标记配置
├── requirements.txt              # 依赖(仅 PyYAML)
├── .github/workflows/update.yml  # 定时任务：每天 06:00(北京时间)跑一次并提交
└── output/                       # 生成的订阅(由 Action 提交)
    ├── clash.yaml                # Clash / Mihomo / Stash 订阅
    ├── v2ray.txt                 # Base64 通用订阅
    ├── nodes.txt                 # 明文节点链接
    └── meta.json                 # 本次运行统计
```

## 部署到 GitHub Actions

1. 新建仓库，把本项目推上去：
   ```bash
   git init && git add -A && git commit -m "init"
   git branch -M main
   git remote add origin git@github.com:<用户名>/<仓库名>.git
   git push -u origin main
   ```
2. 仓库 **Settings → Actions → General → Workflow permissions** 选
   **Read and write permissions**（否则无法把结果提交回来）。
3. **Actions** 里手动点一次 `Update Free Nodes` → `Run workflow` 验证；之后每天 06:00 自动跑。

Workflow 会自动下载 mihomo（`MIHOMO_VERSION` 可改）用于真实测试。

## 订阅链接

把 `<用户名>` `<仓库名>` 换成你自己的（分支默认 `main`）：

| 客户端 | 链接 |
| --- | --- |
| Clash / Mihomo / Stash | `https://raw.githubusercontent.com/<用户名>/<仓库名>/main/output/clash.yaml` |
| v2rayN / v2rayNG / Shadowrocket / 通用 | `https://raw.githubusercontent.com/<用户名>/<仓库名>/main/output/v2ray.txt` |

> raw 链接有 CDN 缓存，刚更新完可能几分钟才生效。可用 jsDelivr 加速：
> `https://cdn.jsdelivr.net/gh/<用户名>/<仓库名>@main/output/clash.yaml`

## 本地运行

需要一个 mihomo 可执行文件（真实测试用）：

```bash
# Linux/macOS
curl -L -o mihomo.gz https://github.com/MetaCubeX/mihomo/releases/download/v1.19.32/mihomo-linux-amd64-compatible-v1.19.32.gz
gunzip -f mihomo.gz && chmod +x mihomo

pip install -r requirements.txt
python aggregator.py --config config.yaml --out output --mihomo ./mihomo
```

Windows 就下 `mihomo-windows-amd64-compatible-*.zip`，解压后把 exe 路径传给 `--mihomo`。

常用参数：

```bash
python aggregator.py --no-test                       # 跳过测试，只验证抓取/解析(秒级)
python aggregator.py --only-sources v2rayfree,mfuu   # 只跑指定源，调试用
python aggregator.py --mihomo /path/to/mihomo        # 指定 mihomo 路径
```

没有 mihomo 时会退回 TCP 测速，并在日志里明确警告结果不可靠。

## 配置说明（config.yaml）

| 配置 | 说明 |
| --- | --- |
| `output.max_nodes` | 最终保留节点数上限 |
| `output.max_latency_ms` | 超过该延迟的节点丢弃 |
| `output.min_nodes` | 低于该数量则以退出码 1 报警 |
| `test.mode` | `mihomo`（真实穿透，推荐）/ `tcp`（仅 TCP 连接，不可靠） |
| `test.mihomo_bin` | mihomo 路径（或 PATH 里的名字） |
| `test.mihomo_url` | 穿透测试目标 URL |
| `test.mihomo_timeout_ms` | 单节点穿透超时 |
| `test.tcp_prefilter` | 是否先做 TCP 快速预筛 |
| `test.single_concurrency` | 逐节点测速的并发数 |
| `test.timeout` / `attempts` / `concurrency` | TCP 预筛参数 |
| `mark.prefix` / `mark.latency_tiers` | 节点名标记与延迟分级 |
| `sources` | 节点源列表（`name` / `type: base64\|clash` / `url`） |

## 已知限制

- **免费节点不稳定**：实测同一批节点几分钟后约七成仍可用，掉线属正常现象。
- **测速位置**：GitHub Actions 跑在海外机房，测出的是「机房 → 节点」延迟，和你本地实测有差异。
- **地区识别**：基于节点名里的国旗 / 关键词，名字里没有地区信息的会归到 `🏳 XX`。
- **运行时长**：全量约 8-12 分钟（8000+ 去重节点，两级筛选）。

## License

MIT