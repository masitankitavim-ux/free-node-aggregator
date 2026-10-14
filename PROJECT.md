---
project: free-node-aggregator
version: v1.2
kind: project
updatedAt: 2026-10-15T01:10:00+08:00
summary: 每天自动聚合多个开源免费节点源，用 mihomo 做真实连通性测试后生成 Clash / Base64 订阅（GitHub Actions 驱动 + 可选本地国内视角跑）
entry: python aggregator.py --config config.yaml --out output --mihomo ./mihomo
---

# free-node-aggregator v1.2

## 用途

把散落在多个 GitHub 仓库里的免费节点订阅聚合到一处：抓取 → 解析 → 去重 → TCP 预筛
→ **mihomo 真实连通性测试** → 打「地区/延迟/来源」标记 → 生成 Clash 与 Base64 两种订阅。
每天由 GitHub Actions 自动跑一次并提交回仓库；也可以用 `run_local.bat` 在本机跑一遍，
拿到「国内视角」真正能用的节点。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `aggregator.py` | 主程序（抓取/解析/去重/预筛/真测/标记/输出） |
| `config.yaml` | 节点源列表 + 输出/测试/标记配置 |
| `run_local.bat` | 一键本地跑（Windows，国内视角，推荐） |
| `get_mihomo.ps1` | 自动下载 mihomo（国内镜像优先） |
| `.github/workflows/update.yml` | 定时任务 + 自动下载 mihomo + 提交 |
| `output/clash.yaml` | 生成的 Clash / Mihomo 订阅 |
| `output/v2ray.txt` | 生成的 Base64 通用订阅 |
| `output/nodes.txt` | 明文节点链接 |
| `output/meta.json` | 本次运行统计 |

## 运行环境与依赖

- Python 3.9+（实测 3.12.10）
- 依赖：`PyYAML>=6.0`
- 真实测试需要 mihomo 可执行文件（`--mihomo` 指定；workflow 与 `run_local.bat` 会自动准备）

## 如何启动 / 使用

```bash
pip install -r requirements.txt
python aggregator.py --config config.yaml --out output --mihomo ./mihomo
```

Windows 直接双击 `run_local.bat`。

## 已完成功能

- 13 个订阅源（10 个项目），base64 与 Clash YAML 双格式；容错解析（源 YAML 语法错也能逐行救回）
- vmess / vless / trojan / ss / hysteria2 / tuic 六协议解析
- 按 (类型+服务器+端口+凭据) 去重；过滤内网/环回/保留地址；端口脏数据容错
- **两级筛选**：TCP 快速预筛 → mihomo 真穿透（实际发 HTTP 请求穿过节点），只留真正能通的
- **分批真测**：`test.batch` 控制每个 mihomo 实例挂多少节点（默认 100），内存小也能跑
- **防跑飞**：单批配置自愈最多剔 25 个 + 整轮真测总时间预算（`test.mihomo_budget_sec`）
- **国内可用抓取**：`raw.githubusercontent` 给短超时，失败自动回退 jsDelivr / ghfast.top / ghproxy.net
- 节点名打标记：`🇺🇸 US | 🟢128ms | v2rayfree-001`；Clash 按地区自动分组 + `♻️ 自动选择`(url-test)
- GitHub Actions 每天自动更新并提交；本机可用 `run_local.bat` 跑国内视角

## 待办 / 下一步

- 免费节点本身不稳定（实测几分钟后就有掉线），可考虑连续测两次提高留存
- 地区识别基于节点名关键词，可接入离线 GeoIP 库
- 想让「国内视角」结果全自动更新，需要一台国内机器定时跑（本机任务计划程序或国内服务器）

## 关键文件

| 文件 | 作用 |
| --- | --- |
| `aggregator.py` | 全部核心逻辑 |
| `config.yaml` | 源与参数 |
| `run_local.bat` / `get_mihomo.ps1` | 本机（国内）跑 + 自动装 mihomo |
| `.github/workflows/update.yml` | 定时 + 手动触发 + 下载 mihomo |

## 本版本变更

- **v1.2（2026-10-15）**：
  1. 修复 `mihomo_test` **根本没分批**的 bug —— `test.batch` 配了没用，8000+ 节点全塞进
     一个 mihomo 实例，小内存机器直接 OOM（实测成都服务器被拖死）。
  2. 加防跑飞：单批自愈最多剔 25 个（原来最多 128 次 `mihomo -t`），`mihomo -t` 超时 180s→60s，
     整轮真测加总时间预算。
  3. `fetch()` 抓取加国内镜像回退（jsDelivr / ghfast.top / ghproxy.net），原地址超时降到 10s。
  4. `output.max_nodes` 200 → **600**。
  5. 新增 `run_local.bat` + `get_mihomo.ps1`（国内视角一键跑）。
  6. README 补上实测的「海外 vs 国内」存活率对比。
- **v1.1（2026-10-14）**：修复「节点全部不可用」的致命问题。原实现用 TCP 连接耗时当延迟，
  而大量节点是 CDN 前置（server 是 Fastly/Cloudflare anycast IP），机房连 CDN 边缘仅 1ms，
  导致输出满屏 1ms 的僵尸节点。改为 mihomo 真实穿透测试；并加 TCP 预筛控制耗时。
- v1：首个可用版本。