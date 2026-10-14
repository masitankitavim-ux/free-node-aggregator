# Free Node Aggregator · 免费节点自动聚合订阅

每天自动从多个开源免费节点项目抓取节点 → 去重 → **真实连通性测试** → 按
`国旗 地区 | 延迟 | 来源` 打标记 → 生成 Clash / Base64 两种订阅。

- GitHub Actions 每天 06:00（北京时间）自动跑一次并提交结果
- 也可以在本机跑一次 `run_local.bat`，拿到**国内视角**真正能用的节点

> ⚠️ 免费节点来源公开、随时失效，仅供学习 / 测试网络连通性使用。请勿用于任何违法用途。

## 特性

- **多源聚合**：13 个订阅源（10 个项目），base64 与 Clash YAML 两种格式都支持
- **协议支持**：vmess / vless / trojan / ss / hysteria2 / tuic
- **去重**：按 `类型 + 服务器 + 端口 + 凭据` 去重；过滤内网 / 环回 / 保留地址
- **真实连通性测试**：用 mihomo 实际发一次 HTTP 请求穿过每个节点，只保留真正能通的
- **两级筛选**：先 TCP 快速预筛（砍掉大部分死节点），再 mihomo 真穿透，兼顾速度与准确性
- **国内可用的抓取链路**：`raw.githubusercontent` 不通时自动回退 jsDelivr / ghfast / ghproxy
- **打标记**：节点名 = `🇺🇸 US | 🟢128ms | v2rayfree-001`
- **策略组**：自动生成 `节点选择 / ♻️ 自动选择(url-test) / 按地区分组 / 全球直连`
- **零成本**：GitHub Actions 即可运行，无需服务器

## 为什么不用 TCP ping 测速

最初的版本用「TCP 连接耗时」当延迟。**这是错的**：大量免费节点是「CDN 前置」的
（server 填的是 Fastly / Cloudflare 的 anycast IP），GitHub 机房连这些 CDN 边缘只要 1ms，
但节点背后的代理服务早就死了。结果就是测出来满屏 1ms / 2ms，**全部用不了**。

现在改为真实穿透测试：起一个 mihomo 实例，把每个节点挂上去，调它的 delay 接口
**实际发一次 HTTP 请求**（`http://www.gstatic.com/generate_204`）穿过该节点。
只有真正通的节点才会返回延迟，其余全部丢弃。

## 测速位置：为什么海外测出来的节点国内还是用不了

真实穿透测试解决了「1ms 假延迟」，但还有第二个、更隐蔽的问题：**测速的位置**。

GitHub Actions 跑在海外机房。节点「从海外机房能通」≠「从国内能通」。
同一批免费节点的实测：

| 测速位置 | 原始去重 | 真实存活 | 存活率 |
| --- | --- | --- | --- |
| GitHub Actions（海外机房） | 8168 | **471** | 5.8% |
| 国内机器（本地实跑） | 8075 | **43** | 0.5% |

**海外测出来「活」的节点，回到国内只剩 7~8% 还能用。** 免费节点里大量是
Cloudflare / Fastly 前置的 anycast 节点，海外连得通，国内那条路早被墙了。

所以有两条路：

1. **GitHub Actions 自动更新**（免维护）— 产出「全球存活池」，保留上限放大到
   **600** 个，配合 `♻️ 自动选择`（url-test）策略组，客户端自动挑当前能用的。
2. **本机跑 `run_local.bat`**（推荐，国内用户）— 同一套脚本在你自己的机器上跑，
   测出来的就是「国内 → 节点」，直接拿到那 40~50 个真正能用的。

## 目录结构

```
free-node-aggregator/
├── aggregator.py                 # 主程序：抓取/解析/去重/预筛/真测/生成订阅
├── config.yaml                   # 节点源 + 输出/测试/标记配置
├── requirements.txt              # 依赖(仅 PyYAML)
├── run_local.bat                 # 一键本地跑（国内视角，Windows）
├── get_mihomo.ps1                # 自动下载 mihomo（国内镜像优先）
├── .github/workflows/update.yml  # 定时任务：每天 06:00(北京时间)跑一次并提交
└── output/                       # 生成的订阅
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

> **国内直连 raw 大概率失败**，换下面任一镜像即可（把路径拼在后面）。
> 以下为 2026-10-15 国内家宽实测（同一文件）：
>
> | 镜像 | 结果 | 耗时 |
> | --- | --- | --- |
> | `https://ghfast.top/https://raw.githubusercontent.com/<用户名>/<仓库名>/main/output/clash.yaml` | ✅ 可用 | 4.1s |
> | `https://ghproxy.net/https://raw.githubusercontent.com/<用户名>/<仓库名>/main/output/clash.yaml` | ✅ 可用 | 4.8s |
> | `https://raw.githubusercontent.com/<用户名>/<仓库名>/main/output/clash.yaml` | 时通时不通 | — |
> | `https://cdn.jsdelivr.net/gh/<用户名>/<仓库名>@main/output/clash.yaml` | 不稳定（实测当时不可达） | — |
> | `https://gh-proxy.com/...` | 403 | 0.6s |
>
> **推荐直接用 ghfast.top**；raw 链接有 CDN 缓存，刚更新完可能几分钟才生效。

## 本地运行（推荐，国内视角）

Windows 直接双击 **`run_local.bat`**：它会自动找（或下载）mihomo，然后跑完整流程，
结果写到 `output/`。

想让它每天自动跑并把结果推到 GitHub，用任务计划程序：

```powershell
# 每天 09:00 跑一次（示例）
$act = New-ScheduledTaskAction -Execute "$PWD\run_local.bat" -WorkingDirectory "$PWD"
$trg = New-ScheduledTaskTrigger -Daily -At 09:00
Register-ScheduledTask -TaskName "FreeNodeAggregator" -Action $act -Trigger $trg -RunLevel Highest
```

> 本机推 GitHub 如果被 reset，给 git 挂个代理：
> `git config http.proxy socks5h://127.0.0.1:10808`（端口按你自己的代理改）。

命令行用法：

```bash
pip install -r requirements.txt
python aggregator.py --config config.yaml --out output --mihomo ./mihomo
```

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
| `output.max_nodes` | 最终保留节点数上限（默认 600） |
| `output.max_latency_ms` | 超过该延迟的节点丢弃 |
| `output.min_nodes` | 低于该数量则以退出码 1 报警 |
| `test.mode` | `mihomo`（真实穿透，推荐）/ `tcp`（仅 TCP 连接，不可靠） |
| `test.mihomo_bin` | mihomo 路径（或 PATH 里的名字） |
| `test.mihomo_url` | 穿透测试目标 URL |
| `test.mihomo_timeout_ms` | 单节点穿透超时 |
| `test.mihomo_budget_sec` | 整轮真测的总时间预算，超了就用已有结果收尾 |
| `test.tcp_prefilter` | 是否先做 TCP 快速预筛 |
| `test.batch` | 每批交给一个 mihomo 实例的节点数（省内存） |
| `test.single_concurrency` | 逐节点测速的并发数 |
| `test.timeout` / `attempts` / `concurrency` | TCP 预筛参数 |
| `mark.prefix` / `mark.latency_tiers` | 节点名标记与延迟分级 |
| `sources` | 节点源列表（`name` / `type: base64\|clash` / `url`） |

## 已知限制

- **免费节点不稳定**：实测同一批节点几分钟后就有掉线，属正常现象。
- **测速位置决定结果**：Actions 跑在海外，产出的是「全球存活池」；要国内精准结果请本地跑。
- **地区识别**：基于节点名里的国旗 / 关键词，名字里没有地区信息的会归到 `🏳 XX`。
- **运行时长**：全量约 8~15 分钟（8000+ 去重节点，两级筛选）。机器内存小请调小 `test.batch`。

## License

MIT