#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Free Node Aggregator
====================

抓取多个开源免费节点源 -> 解析(share link / clash yaml) -> 去重
-> TCP 连接测速 -> 打地区/延迟/来源标记 -> 生成订阅:
    output/clash.yaml   Clash / Mihomo / Stash 订阅(带策略组)
    output/v2ray.txt    Base64 通用订阅(v2rayN / v2rayNG / Shadowrocket ...)
    output/nodes.txt    明文节点链接(方便肉眼查看)
    output/meta.json    本次运行的统计信息

只依赖 PyYAML。设计为可在 GitHub Actions 里每天跑。
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import ipaddress
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.parse as up
import urllib.request as ur

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FreeNodeAggregator/1.0"
SUPPORTED = {"vmess", "vless", "trojan", "ss", "hysteria2", "tuic"}
UDP_ONLY = {"hysteria2", "tuic"}  # 这类是 QUIC/UDP，TCP 测速无意义

# --------------------------------------------------------------------------- #
# 地区识别(基于节点名里的国旗 / 关键词)
# --------------------------------------------------------------------------- #
REGION_KEYWORDS = [
    ("HK", ["香港", "hongkong", "hong kong", "hong-kong", "hk", "🇭🇰", "港"]),
    ("TW", ["台湾", "台灣", "taiwan", "tw", "🇹🇼", "台北", "新北"]),
    ("JP", ["日本", "japan", "jp", "🇯🇵", "东京", "大阪", "tokyo", "osaka"]),
    ("KR", ["韩国", "韓國", "korea", "kr", "🇰🇷", "首尔", "seoul"]),
    ("SG", ["新加坡", "singapore", "sg", "🇸🇬", "狮城"]),
    ("US", ["美国", "美國", "united states", "usa", "us", "🇺🇸", "洛杉矶", "los angeles",
            "san jose", "seattle", "new york", "dallas", "miami", "phoenix", "chicago"]),
    ("GB", ["英国", "英國", "united kingdom", "uk", "gb", "🇬🇧", "伦敦", "london"]),
    ("DE", ["德国", "德國", "germany", "de", "🇩🇪", "法兰克福", "frankfurt"]),
    ("FR", ["法国", "法國", "france", "fr", "🇫🇷", "巴黎", "paris"]),
    ("NL", ["荷兰", "荷蘭", "netherlands", "nl", "🇳🇱", "阿姆斯特丹", "amsterdam"]),
    ("RU", ["俄罗斯", "俄羅斯", "russia", "ru", "🇷🇺", "莫斯科", "moscow"]),
    ("CA", ["加拿大", "canada", "ca", "🇨🇦", "多伦多", "toronto", "montreal"]),
    ("AU", ["澳大利亚", "澳洲", "australia", "au", "🇦🇺", "悉尼", "sydney"]),
    ("IN", ["印度", "india", "in", "🇮🇳", "孟买", "mumbai"]),
    ("TR", ["土耳其", "turkey", "tr", "🇹🇷", "伊斯坦布尔", "istanbul"]),
    ("VN", ["越南", "vietnam", "vn", "🇻🇳"]),
    ("TH", ["泰国", "泰國", "thailand", "th", "🇹🇭", "曼谷", "bangkok"]),
    ("MY", ["马来西亚", "馬來西亞", "malaysia", "my", "🇲🇾", "吉隆坡"]),
    ("PH", ["菲律宾", "菲律賓", "philippines", "ph", "🇵🇭"]),
    ("ID", ["印尼", "印度尼西亚", "indonesia", "id", "🇮🇩", "雅加达"]),
    ("BR", ["巴西", "brazil", "br", "🇧🇷", "圣保罗"]),
    ("AR", ["阿根廷", "argentina", "ar", "🇦🇷"]),
    ("IT", ["意大利", "italy", "it", "🇮🇹", "米兰", "milan"]),
    ("ES", ["西班牙", "spain", "es", "🇪🇸", "马德里", "madrid"]),
    ("SE", ["瑞典", "sweden", "se", "🇸🇪", "斯德哥尔摩"]),
    ("FI", ["芬兰", "finland", "fi", "🇫🇮", "赫尔辛基"]),
    ("NO", ["挪威", "norway", "no", "🇳🇴"]),
    ("DK", ["丹麦", "denmark", "dk", "🇩🇰"]),
    ("PL", ["波兰", "poland", "pl", "🇵🇱", "华沙"]),
    ("CH", ["瑞士", "switzerland", "ch", "🇨🇭", "苏黎世"]),
    ("AT", ["奥地利", "austria", "at", "🇦🇹", "维也纳"]),
    ("IE", ["爱尔兰", "ireland", "ie", "🇮🇪", "都柏林"]),
    ("RO", ["罗马尼亚", "romania", "ro", "🇷🇴"]),
    ("UA", ["乌克兰", "ukraine", "ua", "🇺🇦", "基辅"]),
    ("KZ", ["哈萨克斯坦", "kazakhstan", "kz", "🇰🇿"]),
    ("AE", ["阿联酋", "迪拜", "emirates", "uae", "ae", "🇦🇪", "dubai"]),
    ("SA", ["沙特", "saudi", "sa", "🇸🇦"]),
    ("IL", ["以色列", "israel", "il", "🇮🇱"]),
    ("IR", ["伊朗", "iran", "ir", "🇮🇷", "德黑兰"]),
    ("ZA", ["南非", "south africa", "za", "🇿🇦"]),
    ("EG", ["埃及", "egypt", "eg", "🇪🇬"]),
    ("MX", ["墨西哥", "mexico", "mx", "🇲🇽"]),
    ("CL", ["智利", "chile", "cl", "🇨🇱"]),
    ("NZ", ["新西兰", "紐西蘭", "new zealand", "nz", "🇳🇿"]),
    ("MO", ["澳门", "澳門", "macao", "macau", "mo", "🇲🇴"]),
    ("CN", ["中国", "中國", "china", "cn", "🇨🇳"]),
]


def flag_to_cc(s: str):
    """从字符串里提取国旗 emoji 对应的两位国家码。"""
    ri = [c for c in s if 0x1F1E6 <= ord(c) <= 0x1F1FF]
    for i in range(len(ri) - 1):
        a, b = ri[i], ri[i + 1]
        if 0x1F1E6 <= ord(a) <= 0x1F1FF and 0x1F1E6 <= ord(b) <= 0x1F1FF:
            return chr(ord(a) - 0x1F1E6 + 65) + chr(ord(b) - 0x1F1E6 + 65)
    return None


def cc_to_flag(cc: str) -> str:
    if not cc or cc == "XX" or len(cc) != 2 or not cc.isalpha():
        return "🏳"
    return "".join(chr(0x1F1E6 + ord(c.upper()) - 65) for c in cc)


def detect_region(name: str) -> str:
    if not name:
        return "XX"
    cc = flag_to_cc(name)
    if cc:
        return cc
    low = name.lower()
    for code, keys in REGION_KEYWORDS:
        for k in keys:
            if k.isascii():
                if len(k) <= 3 and k.isalpha():
                    if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", low):
                        return code
                elif k in low:
                    return code
            elif k in name:
                return code
    return "XX"


# --------------------------------------------------------------------------- #
# base64 / 解析工具
# --------------------------------------------------------------------------- #
def b64d(s: str) -> str:
    """宽松的 base64 解码(自动补 padding、兼容 urlsafe)。"""
    s = re.sub(r"\s+", "", s or "")
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * ((-len(s)) % 4)
    return base64.b64decode(s).decode("utf-8", "ignore")


def maybe_decode_sub(text: str) -> str:
    """订阅内容可能是 base64，也可能是明文，这里都兼容。"""
    if "://" in text:
        return text
    try:
        dec = b64d(text)
        if "://" in dec:
            return dec
    except Exception:
        pass
    return text


def ws_path(p: dict) -> str:
    o = p.get("ws-opts") or {}
    return o.get("path") or p.get("ws-path") or ""


def ws_host(p: dict) -> str:
    o = p.get("ws-opts") or {}
    h = o.get("headers") or {}
    return h.get("Host") or h.get("host") or ""


# --------------------------------------------------------------------------- #
# share link -> clash proxy dict
# --------------------------------------------------------------------------- #
def _parse_vmess(link: str):
    obj = json.loads(b64d(link[8:]))
    server, port = obj.get("add"), int(obj.get("port"))
    net = (obj.get("net") or "tcp").lower()
    tls = str(obj.get("tls", "")).lower() in ("tls", "reality", "true", "1")
    p = {
        "name": obj.get("ps") or f"{server}:{port}",
        "type": "vmess",
        "server": server,
        "port": port,
        "uuid": obj.get("id"),
        "alterId": int(obj.get("aid") or 0),
        "cipher": obj.get("scy") or "auto",
        "udp": True,
    }
    if tls:
        p["tls"] = True
        if obj.get("sni"):
            p["servername"] = obj["sni"]
        elif obj.get("host"):
            p["servername"] = obj["host"]
        if obj.get("fp"):
            p["client-fingerprint"] = obj["fp"]
    if net == "ws":
        p["network"] = "ws"
        opts = {}
        if obj.get("path"):
            opts["path"] = obj["path"]
        if obj.get("host"):
            opts["headers"] = {"Host": obj["host"]}
        if opts:
            p["ws-opts"] = opts
    elif net == "grpc":
        p["network"] = "grpc"
        p["grpc-opts"] = {"grpc-service-name": obj.get("path") or obj.get("serviceName") or ""}
    else:
        p["network"] = "tcp"
    return p


def _parse_vless(link: str):
    u = up.urlparse(link)
    q = dict(up.parse_qsl(u.query))
    server, port = u.hostname, int(u.port)
    p = {
        "name": up.unquote(u.fragment) or f"{server}:{port}",
        "type": "vless",
        "server": server,
        "port": port,
        "uuid": up.unquote(u.username or ""),
        "udp": True,
    }
    sec = (q.get("security") or "").lower()
    if sec in ("tls", "reality", "xtls"):
        p["tls"] = True
        if q.get("sni"):
            p["servername"] = q["sni"]
        if q.get("fp"):
            p["client-fingerprint"] = q["fp"]
        if q.get("alpn"):
            p["alpn"] = [x for x in q["alpn"].split(",") if x]
        if sec == "reality":
            p["reality-opts"] = {"public-key": q.get("pbk", ""), "short-id": q.get("sid", "")}
    if q.get("flow"):
        p["flow"] = q["flow"]
    net = (q.get("type") or "tcp").lower()
    if net == "ws":
        p["network"] = "ws"
        opts = {}
        if q.get("path"):
            opts["path"] = up.unquote(q["path"])
        if q.get("host"):
            opts["headers"] = {"Host": up.unquote(q["host"])}
        if opts:
            p["ws-opts"] = opts
    elif net == "grpc":
        p["network"] = "grpc"
        p["grpc-opts"] = {"grpc-service-name": q.get("serviceName", "")}
    else:
        p["network"] = "tcp"
    return p


def _parse_trojan(link: str):
    u = up.urlparse(link)
    q = dict(up.parse_qsl(u.query))
    server, port = u.hostname, int(u.port)
    p = {
        "name": up.unquote(u.fragment) or f"{server}:{port}",
        "type": "trojan",
        "server": server,
        "port": port,
        "password": up.unquote(u.username or ""),
        "udp": True,
    }
    if q.get("sni"):
        p["sni"] = q["sni"]
    if q.get("allowInsecure") in ("1", "true"):
        p["skip-cert-verify"] = True
    if (q.get("type") or "").lower() == "ws":
        p["network"] = "ws"
        opts = {}
        if q.get("path"):
            opts["path"] = up.unquote(q["path"])
        if q.get("host"):
            opts["headers"] = {"Host": q["host"]}
        if opts:
            p["ws-opts"] = opts
    return p


def _parse_ss(link: str):
    body = link[5:]
    name = ""
    if "#" in body:
        body, frag = body.split("#", 1)
        name = up.unquote(frag)
    if "?" in body:
        body = body.split("?", 1)[0]
    if "@" in body:
        userinfo, hostport = body.rsplit("@", 1)
        if ":" not in userinfo:
            userinfo = b64d(userinfo)
    else:
        dec = b64d(body)
        userinfo, hostport = dec.rsplit("@", 1)
    method, pw = userinfo.split(":", 1)
    host, port = hostport.rsplit(":", 1)
    return {
        "name": name or f"{host}:{port}",
        "type": "ss",
        "server": host,
        "port": int(port),
        "cipher": method,
        "password": pw,
        "udp": True,
    }


def _parse_hy2(link: str):
    u = up.urlparse(link)
    q = dict(up.parse_qsl(u.query))
    server, port = u.hostname, int(u.port or 443)
    pw = up.unquote(u.username or "")
    if u.password:
        pw = f"{pw}:{up.unquote(u.password)}"
    p = {
        "name": up.unquote(u.fragment) or f"{server}:{port}",
        "type": "hysteria2",
        "server": server,
        "port": port,
        "password": pw,
    }
    if q.get("sni"):
        p["sni"] = q["sni"]
    if q.get("insecure") in ("1", "true"):
        p["skip-cert-verify"] = True
    if q.get("obfs"):
        p["obfs"] = q["obfs"]
    if q.get("obfs-password"):
        p["obfs-password"] = q["obfs-password"]
    return p


def _parse_tuic(link: str):
    u = up.urlparse(link)
    q = dict(up.parse_qsl(u.query))
    server, port = u.hostname, int(u.port or 443)
    p = {
        "name": up.unquote(u.fragment) or f"{server}:{port}",
        "type": "tuic",
        "server": server,
        "port": port,
        "uuid": up.unquote(u.username or ""),
        "password": up.unquote(u.password or ""),
    }
    if q.get("sni"):
        p["sni"] = q["sni"]
    if q.get("alpn"):
        p["alpn"] = [x for x in q["alpn"].split(",") if x]
    if q.get("allow_insecure") in ("1", "true"):
        p["skip-cert-verify"] = True
    return p


PARSERS = {
    "vmess://": _parse_vmess,
    "vless://": _parse_vless,
    "trojan://": _parse_trojan,
    "trojan-go://": _parse_trojan,
    "ss://": _parse_ss,
    "hysteria2://": _parse_hy2,
    "hy2://": _parse_hy2,
    "tuic://": _parse_tuic,
}


def parse_link(link: str):
    link = (link or "").strip()
    for prefix, fn in PARSERS.items():
        if link.startswith(prefix):
            try:
                return fn(link)
            except Exception:
                return None
    return None


# --------------------------------------------------------------------------- #
# clash proxy dict -> share link(让 clash 源里的节点也能进 v2ray 订阅)
# --------------------------------------------------------------------------- #
def to_link(p: dict):
    t, server, port = p.get("type"), p.get("server"), p.get("port")
    frag = up.quote(str(p.get("name", "")), safe="")
    try:
        if t == "vmess":
            obj = {
                "v": "2", "ps": p.get("name"), "add": server, "port": str(port),
                "id": p.get("uuid", ""), "aid": str(p.get("alterId", 0)),
                "scy": p.get("cipher", "auto"), "net": p.get("network", "tcp"), "type": "none",
            }
            if p.get("tls"):
                obj["tls"] = "tls"
            if p.get("servername"):
                obj["sni"] = p["servername"]
            if p.get("client-fingerprint"):
                obj["fp"] = p["client-fingerprint"]
            if p.get("network") == "ws":
                obj["path"] = ws_path(p)
                obj["host"] = ws_host(p)
            if p.get("network") == "grpc":
                obj["path"] = (p.get("grpc-opts") or {}).get("grpc-service-name", "")
            return "vmess://" + base64.b64encode(
                json.dumps(obj, ensure_ascii=False).encode()).decode()
        if t == "vless":
            q = {"encryption": "none", "security": "tls" if p.get("tls") else "none",
                 "type": p.get("network", "tcp")}
            if p.get("reality-opts"):
                q["security"] = "reality"
                q["pbk"] = p["reality-opts"].get("public-key", "")
                q["sid"] = p["reality-opts"].get("short-id", "")
            if p.get("servername"):
                q["sni"] = p["servername"]
            if p.get("flow"):
                q["flow"] = p["flow"]
            if p.get("client-fingerprint"):
                q["fp"] = p["client-fingerprint"]
            if q["type"] == "ws":
                q["path"] = ws_path(p) or "/"
                if ws_host(p):
                    q["host"] = ws_host(p)
            if q["type"] == "grpc":
                q["serviceName"] = (p.get("grpc-opts") or {}).get("grpc-service-name", "")
            return "vless://%s@%s:%s?%s#%s" % (p.get("uuid", ""), server, port,
                                              up.urlencode(q), frag)
        if t == "trojan":
            q = {}
            if p.get("sni"):
                q["sni"] = p["sni"]
            if p.get("skip-cert-verify"):
                q["allowInsecure"] = "1"
            if p.get("network") == "ws":
                q["type"] = "ws"
                q["path"] = ws_path(p) or "/"
                if ws_host(p):
                    q["host"] = ws_host(p)
            return "trojan://%s@%s:%s?%s#%s" % (
                up.quote(str(p.get("password", ""))), server, port, up.urlencode(q), frag)
        if t == "ss":
            ui = base64.urlsafe_b64encode(
                ("%s:%s" % (p.get("cipher", ""), p.get("password", ""))).encode()
            ).decode().rstrip("=")
            return "ss://%s@%s:%s#%s" % (ui, server, port, frag)
        if t == "hysteria2":
            q = {}
            if p.get("sni"):
                q["sni"] = p["sni"]
            if p.get("skip-cert-verify"):
                q["insecure"] = "1"
            if p.get("obfs"):
                q["obfs"] = p["obfs"]
            if p.get("obfs-password"):
                q["obfs-password"] = p["obfs-password"]
            return "hysteria2://%s@%s:%s?%s#%s" % (
                up.quote(str(p.get("password", ""))), server, port, up.urlencode(q), frag)
        if t == "tuic":
            q = {}
            if p.get("sni"):
                q["sni"] = p["sni"]
            if p.get("alpn"):
                q["alpn"] = ",".join(p["alpn"]) if isinstance(p["alpn"], list) else p["alpn"]
            if p.get("skip-cert-verify"):
                q["allow_insecure"] = "1"
            return "tuic://%s:%s@%s:%s?%s#%s" % (
                p.get("uuid", ""), up.quote(str(p.get("password", ""))), server, port,
                up.urlencode(q), frag)
    except Exception:
        return None
    return None


# --------------------------------------------------------------------------- #
# 抓取
# --------------------------------------------------------------------------- #
BAD_HOSTS = {"localhost", "0.0.0.0", "127.0.0.1", "::1", ""}


def _safe_port(v) -> int:
    """从脏数据里提取端口,例如 '443?' -> 443。无法解析返回 0。"""
    m = re.search(r"\d+", str(v or ""))
    return int(m.group()) if m else 0


def is_valid_server(server) -> bool:
    """过滤内网 / 环回 / 保留地址(部分源里混有 127.0.0.1 之类的假节点)。"""
    if not isinstance(server, str) or not server.strip():
        return False
    s = server.strip().strip("[]").lower()
    if s in BAD_HOSTS:
        return False
    try:
        ip = ipaddress.ip_address(s)
    except ValueError:
        return True
    return not (ip.is_private or ip.is_loopback or ip.is_reserved
                or ip.is_link_local or ip.is_multicast or ip.is_unspecified)


def fetch(url: str, retries: int = 3, timeout: int = 25) -> str:
    last = None
    for i in range(retries):
        try:
            req = ur.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with ur.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def load_clash_proxies(text: str):
    """解析 Clash YAML 的 proxies。整份 YAML 报错时回退到逐行解析（很多源的 YAML 本身有语法错）。"""
    if yaml is None:
        return []
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and isinstance(data.get("proxies"), list):
            return data["proxies"]
    except Exception:  # noqa: BLE001
        pass
    out = []
    for line in text.splitlines():
        st = line.strip()
        if not st.startswith("-"):
            continue
        body = st[1:].strip()
        if not body.startswith("{"):
            continue
        try:
            d = yaml.safe_load(body)
            if isinstance(d, dict):
                out.append(d)
        except Exception:  # noqa: BLE001
            continue
    return out


def nodes_from_text(text: str, source: str, kind: str):
    out = []
    if kind == "clash":
        for pr in load_clash_proxies(text):
            if not isinstance(pr, dict):
                continue
            if str(pr.get("type", "")).lower() not in SUPPORTED:
                continue
            if not pr.get("server") or not pr.get("port"):
                continue
            out.append((pr, source))
    else:
        text = maybe_decode_sub(text)
        for line in text.splitlines():
            line = line.strip()
            if "://" not in line:
                continue
            p = parse_link(line)
            if p:
                out.append((p, source))
    return out


# --------------------------------------------------------------------------- #
# 去重 / 测速 / 标记
# --------------------------------------------------------------------------- #
def dedup_key(p: dict):
    cred = p.get("uuid") or p.get("password") or ""
    return (str(p.get("type", "")).lower(), str(p.get("server", "")).lower(),
            _safe_port(p.get("port")), str(cred))


def _is_ip(s: str) -> bool:
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def resolve_many(hosts, workers: int = 128, timeout: float = 5.0):
    """并发解析域名，单域名超过 timeout 视为失败（避免 getaddrinfo 卡死整体）。"""
    hosts = list(hosts)
    results, lock = {}, threading.Lock()
    cursor = {"i": 0}

    def worker():
        while True:
            with lock:
                i = cursor["i"]
                cursor["i"] += 1
            if i >= len(hosts):
                return
            h = hosts[i]
            try:
                ip = socket.gethostbyname(h)
            except Exception:  # noqa: BLE001
                ip = None
            with lock:
                results[h] = ip

    n = max(1, min(workers, len(hosts)))
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout)
    for h in hosts:
        results.setdefault(h, None)
    return results


def tcp_ping(target: str, port: int, timeout: float, attempts: int):
    """对已解析的目标(IP 或域名)做 TCP 连接测延迟，取多次最小值(ms)。"""
    best = None
    for _ in range(attempts):
        t0 = time.perf_counter()
        try:
            with socket.create_connection((target, int(port)), timeout=timeout):
                dt = (time.perf_counter() - t0) * 1000.0
                best = dt if best is None else min(best, dt)
        except Exception:  # noqa: BLE001
            pass
    return best


def run_test(nodes, cfg):
    tcfg = cfg.get("test", {})
    timeout = float(tcfg.get("timeout", 2.0))
    attempts = int(tcfg.get("attempts", 1))
    workers = int(tcfg.get("concurrency", 128))
    keep_udp = bool(tcfg.get("keep_udp", True))

    tcp_nodes = [n for n in nodes if n["proxy"]["type"] not in UDP_ONLY]
    hosts = {n["proxy"]["server"] for n in tcp_nodes if not _is_ip(n["proxy"]["server"])}
    dns = {}
    if hosts:
        print(f"[~] 并发解析 {len(hosts)} 个域名 ...")
        dns = resolve_many(hosts, workers=workers, timeout=5.0)

    def work(node):
        p = node["proxy"]
        if p["type"] in UDP_ONLY:
            node["latency"], node["tested"] = None, False
            return node
        node["tested"] = True
        server = p["server"]
        target = server if _is_ip(server) else dns.get(server)
        node["latency"] = tcp_ping(target, p["port"], timeout, attempts) if target else None
        return node

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, nodes))
    if not keep_udp:
        nodes = [n for n in nodes if n["proxy"]["type"] not in UDP_ONLY]
    return nodes


def tier_emoji(lat, cfg):
    if lat is None:
        return "⚪"
    t = cfg.get("mark", {}).get("latency_tiers", {})
    if lat <= t.get("fast", 300):
        return "🟢"
    if lat <= t.get("good", 800):
        return "🟡"
    if lat <= t.get("ok", 1500):
        return "🟠"
    return "🔴"


def mark_names(nodes, cfg):
    mcfg = cfg.get("mark", {})
    prefix = mcfg.get("prefix", True)
    used = set()
    for i, n in enumerate(nodes, 1):
        p = n["proxy"]
        cc = n["region"]
        flag = cc_to_flag(cc)
        lat = n["latency"]
        ms = f"{int(round(lat))}ms" if lat is not None else "??ms"
        if prefix:
            name = f"{flag} {cc} | {tier_emoji(lat, cfg)}{ms} | {n['source']}-{i:03d}"
        else:
            name = p.get("name") or f"{p['server']}:{p['port']}"
        while name in used:
            name += "_"
        used.add(name)
        p["name"] = name


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #
BASE_GROUPS = [
    {"name": "🚀 节点选择", "type": "select", "proxies": []},
    {"name": "♻️ 自动选择", "type": "url-test", "url": "https://www.gstatic.com/generate_204",
     "interval": 300, "tolerance": 50, "proxies": []},
    {"name": "🌍 全球直连", "type": "select", "proxies": ["DIRECT", "🚀 节点选择"]},
]
RULES = [
    "GEOIP,LAN,🌍 全球直连,no-resolve",
    "GEOIP,CN,🌍 全球直连",
    "MATCH,🚀 节点选择",
]


def write_clash(nodes, path):
    names = [n["proxy"]["name"] for n in nodes]
    groups = [dict(g) for g in BASE_GROUPS]
    groups[1]["proxies"] = names or ["DIRECT"]

    # 按地区分组
    by_region = {}
    for n in nodes:
        by_region.setdefault(n["region"], []).append(n["proxy"]["name"])
    region_group_names = []
    for cc, members in sorted(by_region.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        gname = f"{cc_to_flag(cc)} {cc}"
        groups.append({"name": gname, "type": "url-test",
                       "url": "https://www.gstatic.com/generate_204",
                       "interval": 300, "tolerance": 50, "proxies": members})
        region_group_names.append(gname)

    groups[0]["proxies"] = ["♻️ 自动选择", "DIRECT"] + region_group_names + names

    doc = {
        "mixed-port": 7890,
        "allow-lan": False,
        "bind-address": "*",
        "mode": "rule",
        "log-level": "warning",
        "ipv6": False,
        "external-controller": "127.0.0.1:9090",
        "dns": {
            "enable": True,
            "ipv6": False,
            "enhanced-mode": "fake-ip",
            "fake-ip-range": "198.18.0.1/16",
            "nameserver": ["223.5.5.5", "119.29.29.29", "8.8.8.8"],
            "fallback": ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query"],
        },
        "proxies": [n["proxy"] for n in nodes],
        "proxy-groups": groups,
        "rules": RULES,
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, width=4096)


def write_outputs(nodes, out_dir, meta):
    os.makedirs(out_dir, exist_ok=True)
    links = [l for l in (to_link(n["proxy"]) for n in nodes) if l]

    with open(os.path.join(out_dir, "nodes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(links) + "\n")
    with open(os.path.join(out_dir, "v2ray.txt"), "w", encoding="utf-8") as f:
        f.write(base64.b64encode("\n".join(links).encode()).decode())
    write_clash(nodes, os.path.join(out_dir, "clash.yaml"))
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return links


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_args():
    ap = argparse.ArgumentParser(description="免费节点聚合 / 测速 / 生成订阅")
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("-o", "--out", default="output")
    ap.add_argument("--no-test", action="store_true", help="跳过测速(调试用)")
    ap.add_argument("--only-sources", default="", help="只跑指定源(逗号分隔,调试用)")
    return ap.parse_args()


def main():
    args = parse_args()
    if yaml is None:
        print("需要 PyYAML: pip install pyyaml", file=sys.stderr)
        return 2
    cfg = load_config(args.config)
    sources = cfg.get("sources", [])
    if args.only_sources:
        wanted = {s.strip() for s in args.only_sources.split(",") if s.strip()}
        sources = [s for s in sources if s.get("name") in wanted]

    t0 = time.time()
    all_nodes, per_source = [], {}
    for src in sources:
        name, url, kind = src.get("name"), src.get("url"), src.get("type", "base64")
        try:
            text = fetch(url)
            got = nodes_from_text(text, name, kind)
            all_nodes.extend(got)
            per_source[name] = len(got)
            print(f"[+] {name:<18} {kind:<7} -> {len(got):>5} 节点  ({len(text)} bytes)")
        except Exception as e:  # noqa: BLE001
            per_source[name] = 0
            print(f"[!] {name:<18} 抓取失败: {e}")

    # 去重
    seen, uniq = set(), []
    for p, source in all_nodes:
        if not is_valid_server(p.get("server")):
            continue
        port = _safe_port(p.get("port"))
        if port <= 0 or port > 65535:
            continue
        p["port"] = port
        k = dedup_key(p)
        if k in seen:
            continue
        seen.add(k)
        uniq.append({"proxy": p, "source": source, "region": detect_region(p.get("name", ""))})
    print(f"[=] 原始 {len(all_nodes)} -> 去重后 {len(uniq)}")

    # 测速
    if not args.no_test and cfg.get("test", {}).get("enabled", True):
        print(f"[~] TCP 测速中(并发 {cfg.get('test',{}).get('concurrency',64)}) ...")
        run_test(uniq, cfg)
    else:
        for n in uniq:
            n["latency"], n["tested"] = None, False

    # 过滤 + 排序
    max_ms = float(cfg.get("output", {}).get("max_latency_ms", 3000))
    max_nodes = int(cfg.get("output", {}).get("max_nodes", 200))

    alive = [n for n in uniq if n.get("tested") and n["latency"] is not None
             and n["latency"] <= max_ms]
    untested = [n for n in uniq if not n.get("tested")]
    alive.sort(key=lambda n: n["latency"])
    kept = (alive + untested)[:max_nodes]

    mark_names(kept, cfg)

    meta = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "sources": per_source,
        "raw_total": len(all_nodes),
        "unique": len(uniq),
        "tested_ok": len(alive),
        "kept": len(kept),
        "by_region": {},
        "by_type": {},
        "min_latency_ms": (round(min(n["latency"] for n in alive), 1) if alive else None),
        "avg_latency_ms": (round(sum(n["latency"] for n in alive) / len(alive), 1) if alive else None),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    for n in kept:
        meta["by_region"][n["region"]] = meta["by_region"].get(n["region"], 0) + 1
        t = n["proxy"]["type"]
        meta["by_type"][t] = meta["by_type"].get(t, 0) + 1

    links = write_outputs(kept, args.out, meta)

    print(f"[=] 存活(<= {int(max_ms)}ms) {len(alive)} / 未测速 {len(untested)} -> 输出 {len(kept)} 节点")
    print(f"[=] 地区: {meta['by_region']}")
    print(f"[=] 协议: {meta['by_type']}")
    print(f"[=] 最快 {meta['min_latency_ms']}ms  平均 {meta['avg_latency_ms']}ms")
    print(f"[✓] 已写入 {args.out}/clash.yaml  {args.out}/v2ray.txt  ({len(links)} 条链接)  "
          f"耗时 {meta['elapsed_sec']}s")

    min_nodes = int(cfg.get("output", {}).get("min_nodes", 0))
    if min_nodes and len(kept) < min_nodes:
        print(f"[!] 警告: 节点数 {len(kept)} 低于阈值 {min_nodes}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

