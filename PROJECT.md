---
project: free-node-aggregator
version: v1.1
kind: project
updatedAt: 2026-10-14T23:20:00+08:00
summary: 每天自动聚合多个开源免费节点源，用 mihomo 做真实连通性测试后生成 Clash / Base64 订阅（GitHub Actions 驱动）
entry: python aggregator.py --config config.yaml --out output --mihomo ./mihomo
---

# free-node-aggregator v1.1

## 用途

把散落在多个 GitHub 仓库里的免费节点订阅聚合到一处：抓取 → 解析 → 去重 → TCP 预筛
→ **mihomo 真实连通性测试** → 打「地区/延迟/来源」标记 → 生成 Clash 与 Base64 两种订阅。
每天由 GitHub Actions 自动跑一次并提交回仓库，用户直接订阅 raw 链接即可。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `aggregator.py` | 主程序（抓取/解析/去重/预筛/真测/标记/输出） |
| `config.yaml` | 节点源列表 + 输出/测试/标记配置 |
| `.github/workflows/update.yml` | 定时任务 + 自动下载 mihomo + 提交 |
| `output/clash.yaml` | 生成的 Clash / Mihomo 订阅 |
| `output/v2ray.txt` | 生成的 Base64 通用订阅 |
| `output/nodes.txt` | 明文节点链接 |
| `output/meta.json` | 本次运行统计 |

## 运行环境与依赖

- Python 3.9+（实测 3.12.10）
- 依赖：`PyYAML>=6.0`
- 真实测试需要 mihomo 可执行文件（`--mihomo` 指定；workflow 里自动下载）

## 如何启动 / 使用

```bash
pip install -r requirements.txt
python aggregator.py --config config.yaml --out output --mihomo ./mihomo
```

## 已完成功能

- 13 个订阅源（10 个项目），base64 与 Clash YAML 双格式；容错解析（源 YAML 语法错也能逐行救回）
- vmess / vless / trojan / ss / hysteria2 / tuic 六协议解析
- 按 (类型+服务器+端口+凭据) 去重；过滤内网/环回/保留地址；端口脏数据容错
- **两级筛选**：TCP 快速预筛 → mihomo 真穿透（实际发 HTTP 请求穿过节点），只留真正能通的
- mihomo 配置自愈：遇到非法节点逐个剔除（否则一个坏节点会让整份配置被拒）
- 节点名打标记：`🇺🇸 US | 🟢128ms | v2rayfree-001`；Clash 按地区自动分组
- GitHub Actions 每天自动更新并提交

## 待办 / 下一步

- 免费节点本身不稳定（实测几分钟后约七成仍可用），可考虑连续测两次提高留存
- 地区识别基于节点名关键词，可接入离线 GeoIP 库

## 关键文件

| 文件 | 作用 |
| --- | --- |
| `aggregator.py` | 全部核心逻辑 |
| `config.yaml` | 源与参数 |
| `.github/workflows/update.yml` | 定时 + 手动触发 + 下载 mihomo |

## 本版本变更

- **v1.1（2026-10-14）**：修复「节点全部不可用」的致命问题。原实现用 TCP 连接耗时当延迟，
  而大量节点是 CDN 前置（server 是 Fastly/Cloudflare anycast IP），机房连 CDN 边缘仅 1ms，
  导致输出满屏 1ms 的僵尸节点。改为 mihomo 真实穿透测试；并加 TCP 预筛控制耗时。
  实测：8164 去重 → 预筛 1776 → 真活 43（旧版输出 200 个全部不可用）。
- v1：首个可用版本。