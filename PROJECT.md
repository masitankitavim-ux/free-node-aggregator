---
project: free-node-aggregator
version: v1
kind: project
updatedAt: 2026-10-14T21:05:00+08:00
summary: 每天自动聚合多个开源免费节点源，测速去重后生成 Clash / Base64 订阅（GitHub Actions 驱动）
entry: python aggregator.py --config config.yaml --out output
---

# free-node-aggregator v1

## 用途

把散落在多个 GitHub 仓库里的免费节点订阅聚合到一处：抓取 → 解析 → 去重 → TCP 测速
→ 打「地区/延迟/来源」标记 → 生成 Clash 与 Base64 两种订阅。
每天由 GitHub Actions 自动跑一次并提交回仓库，用户直接订阅 raw 链接即可。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `aggregator.py` | 主程序（抓取/解析/去重/测速/标记/输出） |
| `config.yaml` | 节点源列表 + 输出/测速/标记配置 |
| `.github/workflows/update.yml` | 定时任务：每天 22:00 UTC（北京 06:00）跑一次并提交 |
| `output/clash.yaml` | 生成的 Clash / Mihomo 订阅 |
| `output/v2ray.txt` | 生成的 Base64 通用订阅 |
| `output/nodes.txt` | 明文节点链接 |
| `output/meta.json` | 本次运行统计 |

## 运行环境与依赖

- Python 3.9+（实测 3.12.10）
- 依赖：`PyYAML>=6.0`（`pip install -r requirements.txt`）

## 如何启动 / 使用

```bash
pip install -r requirements.txt
python aggregator.py --config config.yaml --out output
# 调试：
python aggregator.py --no-test                     # 跳过测速
python aggregator.py --only-sources mfuu,v2rayfree # 只跑指定源
```

## 已完成功能

- 13 个订阅源（10 个项目），base64 与 Clash YAML 双格式
- vmess / vless / trojan / ss / hysteria2 / tuic 六协议解析
- 按 (类型+服务器+端口+凭据) 去重；过滤内网/环回/保留地址；端口脏数据容错
- 并发 DNS 解析（带超时）+ TCP 连接测速，按延迟排序
- 节点名打标记：`🇺🇸 US | 🟢128ms | v2rayfree-001`
- Clash 策略组：节点选择 / 自动选择 / 按地区分组 / 全球直连
- GitHub Actions 每天自动更新并提交

## 待办 / 下一步

- 地区识别目前基于节点名关键词，名字无地区信息的会归到 `🏳 XX`；可接入离线 GeoIP 库
- CI 测速反映的是「GitHub 机房 → 节点」延迟，与本地实测有差异

## 关键文件

| 文件 | 作用 |
| --- | --- |
| `aggregator.py` | 全部核心逻辑 |
| `config.yaml` | 源与参数 |
| `.github/workflows/update.yml` | 定时 + 手动触发 |

## 本版本变更

- v1：首个可用版本。2026-10-14 全量实测：原始 18282 → 去重 8158 → 存活 2589(本地)/3823(CI) → 输出 200 节点。
