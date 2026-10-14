# Free Node Aggregator · 免费节点自动聚合订阅

每天自动从多个开源免费节点项目抓取节点 → 去重 → **TCP 测速** → 按 `国旗 地区 | 延迟 | 来源` 打标记
→ 生成 Clash / Base64 两种订阅，并提交回仓库。直接订阅仓库里的 raw 链接即可。

> ⚠️ 免费节点来源公开、随时失效，仅供学习 / 测试网络连通性使用。请勿用于任何违法用途。

## 特性

- **多源聚合**：13 个订阅源（10 个项目），base64 与 Clash YAML 两种格式都支持
- **协议支持**：vmess / vless / trojan / ss / hysteria2 / tuic
- **去重**：按 `类型 + 服务器 + 端口 + 凭据` 去重
- **测速**：并发 TCP 连接测延迟，取多次最小值，按延迟排序
- **打标记**：节点名 = `🇺🇸 US | 🟢128ms | v2rayfree-001`（国旗/地区、延迟分级、来源）
- **策略组**：自动生成 `节点选择 / 自动选择 / 按地区分组 / 全球直连`
- **零成本**：纯 GitHub Actions 运行，无需服务器

## 目录结构

```
free-node-aggregator/
├── aggregator.py                 # 主程序：抓取/解析/去重/测速/生成订阅
├── config.yaml                   # 节点源 + 输出/测速/标记配置
├── requirements.txt              # 依赖(仅 PyYAML)
├── .github/workflows/update.yml  # 定时任务：每天 06:00(北京时间)跑一次并提交
└── output/                       # 生成的订阅(由 Action 提交)
    ├── clash.yaml                # Clash / Mihomo / Stash 订阅
    ├── v2ray.txt                 # Base64 通用订阅
    ├── nodes.txt                 # 明文节点链接
    └── meta.json                 # 本次运行统计
```

## 部署到 GitHub Actions

1. 新建一个仓库，把本项目文件全部推上去：
   ```bash
   git init && git add -A && git commit -m "init"
   git branch -M main
   git remote add origin git@github.com:<你的用户名>/<仓库名>.git
   git push -u origin main
   ```
2. 仓库 **Settings → Actions → General → Workflow permissions** 选 **Read and write permissions**（否则无法把结果提交回来）。
3. **Actions** 标签页里手动点一次 `Update Free Nodes` → `Run workflow` 验证；之后每天 06:00（北京时间）自动跑。

## 订阅链接

把 `<用户名>` `<仓库名>` 换成你自己的，分支默认 `main`：

| 客户端 | 链接 |
| --- | --- |
| Clash / Mihomo / Stash | `https://raw.githubusercontent.com/<用户名>/<仓库名>/main/output/clash.yaml` |
| v2rayN / v2rayNG / Shadowrocket / 通用 | `https://raw.githubusercontent.com/<用户名>/<仓库名>/main/output/v2ray.txt` |

> raw 链接有 CDN 缓存，刚更新完可能几分钟才生效。想更快可用 jsDelivr 加速：
> `https://cdn.jsdelivr.net/gh/<用户名>/<仓库名>@main/output/clash.yaml`
> 或在仓库开启 **GitHub Pages**，用 `https://<用户名>.github.io/<仓库名>/output/clash.yaml`。

## 本地运行

```bash
pip install -r requirements.txt
python aggregator.py --config config.yaml --out output
```

常用参数：

```bash
python aggregator.py --no-test                       # 跳过测速，只验证抓取/解析(秒级)
python aggregator.py --only-sources v2rayfree,mfuu   # 只跑指定源，调试用
```

## 配置说明（config.yaml）

| 配置 | 说明 |
| --- | --- |
| `output.max_nodes` | 最终保留节点数上限（按延迟截断） |
| `output.max_latency_ms` | 超过该延迟的节点丢弃 |
| `output.min_nodes` | 低于该数量则以退出码 1 报警（可在 CI 里做告警） |
| `test.enabled` | 是否测速 |
| `test.timeout` / `attempts` / `concurrency` | 单次超时 / 次数 / 并发 |
| `test.keep_udp` | hysteria2/tuic 是 UDP，无法 TCP 测速，保留并标记 `⚪??ms` |
| `mark.prefix` | 是否给节点名加标记前缀 |
| `mark.latency_tiers` | 延迟分级阈值，决定 🟢🟡🟠🔴 |
| `sources` | 节点源列表（`name` / `type: base64\|clash` / `url`） |

## 已知限制

- **测速位置**：GitHub Actions 跑在海外机房，测出的是「机房 → 节点」延迟，和你本地实测会有差异；追求准的话本地跑一次。
- **UDP 节点**：hysteria2 / tuic 走 QUIC(UDP)，TCP 测速无意义，脚本保留但不测延迟（标记 `⚪??ms`，排在最后）。
- **地区识别**：基于节点名里的国旗 / 关键词，名字里没有地区信息的会归到 `🏳 XX`。
- **可用性**：免费节点寿命短、随时失效，属正常现象。

## License

MIT
