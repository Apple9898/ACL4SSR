# -*- coding: utf-8 -*-
"""
自动构建并更新 gist 配置
用法(本地): python scripts/build_and_update.py  (需环境变量 SUB_URL)
用法(Action): 由 update-gist.yml 调用
环境变量:
  SUB_URL    机场订阅地址 (必填)
  GIST_TOKEN 有 gist scope 的 PAT (提供则更新 gist)
  GIST_ID    gist id (与 GIST_TOKEN 一起提供则更新)
"""
import os
import sys
import json
import urllib.request
import urllib.parse
import re
from collections import defaultdict

BASE = "https://cdn.jsdelivr.net/gh/Apple9898/ACL4SSR@main/icons/"

FLAG = {
    "SG": "\U0001F1F8\U0001F1EC",  # 🇸🇬
    "HK": "\U0001F1ED\U0001F1F0",  # 🇭🇰
    "TW": "\U0001F1F9\U0001F1FC",  # 🇹🇼
    "JP": "\U0001F1EF\U0001F1F5",  # 🇯🇵
    "US": "\U0001F1FA\U0001F1F8",  # 🇺🇸
    "KR": "\U0001F1F0\U0001F1F7",  # 🇰🇷
}


def fetch_nodes(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (qwenpaw gist-updater)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_vless(line):
    line = line.strip()
    if "vless://" not in line:
        return None
    body = line[len("vless://"):]
    if "#" in body:
        head, name = body.split("#", 1)
        name = urllib.parse.unquote(name)
    else:
        head, name = body, ""
    if "@" not in head:
        return None
    uuid, server = head.split("@", 1)
    params = {}
    if ":" in server:
        host, port = server.rsplit(":", 1)
        if "?" in port:
            port, query = port.split("?", 1)
            for kv in query.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    params[k] = urllib.parse.unquote(v)
        port = int(port)
    else:
        host, port = server, 443
    uuid = uuid.strip("/")
    return {
        "name": name,
        "type": "vless",
        "server": host,
        "port": port,
        "uuid": uuid,
        "udp": True,
        "tls": params.get("security", "").lower() in ("tls", "reality"),
        "network": params.get("type", "tcp"),
        "sni": params.get("sni", ""),
        "host": params.get("host", ""),
        "path": params.get("path", ""),
        "flow": params.get("flow", ""),
        "fp": params.get("fp", "chrome"),
    }


def country_code(node_name):
    m = re.match(r"^([A-Za-z]{2})", node_name)
    return m.group(1).upper() if m else ""


def to_clash_yaml(node):
    lines = [f"  - name: {node['name']}", "    type: vless",
             f"    server: {node['server']}", f"    port: {node['port']}",
             f"    uuid: {node['uuid']}", "    udp: true"]
    if node["tls"]:
        lines.append("    tls: true")
    if node.get("sni"):
        lines.append(f"    servername: {node['sni']}")
    if node.get("fp"):
        lines.append(f"    client-fingerprint: {node['fp']}")
    if node["network"] == "ws":
        lines.append("    network: ws")
        lines.append("    ws-opts:")
        lines.append(f"      path: \"{node.get('path') or '/'}\"")
        if node.get("host"):
            lines.append("      headers:")
            lines.append(f"        Host: {node['host']}")
    elif node["network"] == "grpc":
        lines.append("    network: grpc")
        lines.append("    grpc-opts:")
        lines.append(f"      grpc-service-name: {node.get('path','').lstrip('/')}")
    else:
        lines.append(f"    network: {node['network']}")
    return "\n".join(lines)


def build(sub_url):
    raw = fetch_nodes(sub_url)
    nodes = []
    for line in raw.splitlines():
        n = parse_vless(line)
        if n:
            nodes.append(n)
    if not nodes:
        raise RuntimeError("未解析到任何节点")

    counter = defaultdict(int)
    for n in nodes:
        cc = country_code(n["name"])
        if cc in FLAG:
            counter[cc] += 1
            idx = counter[cc]
            n["name"] = f"{FLAG[cc]} {cc}" if idx == 1 else f"{FLAG[cc]} {cc} {idx}"
        else:
            counter[n["name"]] += 1
            idx = counter[n["name"]]
            n["name"] = n["name"] if idx == 1 else f"{n['name']} {idx}"

    proxies_yml = "\n".join(to_clash_yaml(n) for n in nodes)

    def group(name, gtype, icon, *, proxies=None, url=None, interval=300,
              include_all=False, filter_=None):
        lines = [f"  - name: {name}", f"    type: {gtype}", f"    icon: {BASE}{icon}"]
        if include_all:
            lines.append("    include-all: true")
        if filter_:
            lines.append(f"    filter: {filter_}")
        if proxies:
            lines.append("    proxies:")
            for p in proxies:
                lines.append(f"      - {p}")
        if url:
            lines.append(f"    url: {url}")
            lines.append(f"    interval: {interval}")
        return "\n".join(lines)

    g_all = [f"{FLAG['HK']} 香港节点", f"{FLAG['TW']} 台湾节点", f"{FLAG['SG']} 狮城节点",
             f"{FLAG['JP']} 日本节点", f"{FLAG['US']} 美国节点", f"{FLAG['KR']} 韩国节点",
             "\u267B\uFE0F 自动选择", "\U0001F680 手动切换", "DIRECT"]

    groups = []
    groups.append(group("\U0001F680 节点选择", "select", "mini_Static.png", proxies=g_all))
    groups.append(group("\U0001F680 手动切换", "select", "mini_Available.png", include_all=True))
    groups.append(group("\u267B\uFE0F 自动选择", "url-test", "qure_Auto.png",
                        url="https://www.gstatic.com/generate_204", interval=300, include_all=True))
    groups.append(group("\U0001F52F 故障转移", "fallback", "qure_ULB.png",
                        url="https://www.gstatic.com/generate_204", interval=300, include_all=True))
    groups.append(group("\U0001F52E 负载均衡", "load-balance", "qure_Round_Robin.png",
                        url="https://www.gstatic.com/generate_204", interval=300, include_all=True))

    area = [
        ("\U0001F1ED\U0001F1F0 香港节点", "mini_HK.png", "(?i)HK|香港|港"),
        ("\U0001F1F9\U0001F1FC 台湾节点", "mini_TW.png", "(?i)TW|台湾|台"),
        ("\U0001F1F8\U0001F1EC 狮城节点", "mini_SG.png", "(?i)SG|新加坡|狮城"),
        ("\U0001F1EF\U0001F1F5 日本节点", "mini_JP.png", "(?i)JP|日本"),
        ("\U0001F1FA\U0001F1F8 美国节点", "mini_US.png", "(?i)US|美国"),
        ("\U0001F1F0\U0001F1F7 韩国节点", "mini_KR.png", "(?i)KR|韩国"),
    ]
    for name, icon, pattern in area:
        groups.append(group(name, "url-test", icon,
                            url="https://www.gstatic.com/generate_204", interval=300,
                            include_all=True, filter_=pattern))

    business_proxies = [f"\U0001F1F8\U0001F1EC 狮城节点", f"\U0001F1EF\U0001F1F5 日本节点",
                        f"\U0001F1ED\U0001F1F0 香港节点", f"\U0001F1F9\U0001F1FC 台湾节点",
                        f"\U0001F1FA\U0001F1F8 美国节点", f"\U0001F1F0\U0001F1F7 韩国节点",
                        "\u267B\uFE0F 自动选择", "\U0001F680 手动切换", "DIRECT"]

    bz = [
        ("\U0001F4B0 数字货币", "qure_Cryptocurrency.png"),
        ("\U0001F916 Ai平台", "qure_AI.png"),
        ("\U0001F916 Claude", "sins_Claude.png"),
        ("\U0001F916 OpenAI", "mini_OpenAI.png"),
        ("\u2728 Gemini", "sins_Gemini.png"),
        ("\U0001F4F2 电报消息", "mini_Telegram.png"),
        ("\u25B6\uFE0F 油管视频", "qure_YouTube.png"),
        ("\U0001F3A5 奈飞视频", "mini_Netflix.png"),
        ("\U0001F3F0 迪士尼", "qure_Disney.png"),
        ("\U0001F3A7 Spotify", "sins_Spotify.png"),
        ("\U0001F3B5 TikTok", "qure_TikTok.png"),
        ("\U0001F426 推特", "x_twitter.png"),
        ("\U0001F50D 谷歌", "mini_Google.png"),
        ("\u2601\uFE0F Cloudflare", "qure_Cloudflare.png"),
        ("\U0001F34E 苹果服务", "qure_Apple.png"),
        ("\U0001F30D 国外媒体", "qure_ForeignMedia.png"),
        ("\U0001F30F 国内媒体", "qure_China.png"),
        ("\U0001F51E 成人内容", "qure_Heart.png"),
        ("\U0001F6D1 广告拦截", "qure_AdBlack.png"),
        ("\U0001F3AF 全球直连", "qure_Direct.png"),
        ("\U0001F41F 漏网之鱼", "qure_Final.png"),
    ]
    for name, icon in bz:
        groups.append(group(name, "select", icon, proxies=business_proxies))

    groups_yml = "\n".join(groups)

    crypto_domains = [
        "binance.com","binance.us","binance.org","binancezh.cc","bnappzh.com","bnappzh.co","bnbstatic.com","bntrace.com",
        "okx.com","okex.com","bybit.com","bybit.me","bybit.uk","gate.io","coinbase.com","coinbase.us","kraken.com",
        "kucoin.com","bitfinex.com","bitstamp.net","bitmex.com","htx.com","htx.me","huobi.com","huobi.me",
        "bitget.com","bitget.global","bitget.im","mexc.com","mexc.global","mexc.io","bingx.com","bingx.net",
        "bitmart.com","phemex.com","deribit.com","crypto.com","gemini.com","bitflyer.com","bitbank.cc","coincheck.com",
        "upbit.com","bithumb.com","korbit.co.kr","coinone.co.kr","zb.com","aex.com","bibox.com","liquid.com",
        "poloniex.com","ftx.com","okcoin.com","coinw.com","lbank.com","xt.com","woo.network","dydx.exchange",
        "dydx.trade","bitrue.com","coinex.com","ascendex.com","whitebit.com","digifinex.com","bitpanda.com",
        "bit2me.com","bitso.com","mercadobitcoin.com.br","metamask.io","trustwallet.com","blockchain.com",
        "debank.com","etherscan.io","coingecko.com","coinmarketcap.com","bitcointalk.org","aicoin.com","bitunix.com",
        "bitunix.io","bitunix",
    ]
    rules_yml = "\n".join(f"  - DOMAIN-SUFFIX,{d},\U0001F4B0 数字货币" for d in crypto_domains)
    rules_yml += "\n".join([
        "", "  - DOMAIN-KEYWORD,bitunix,\U0001F4B0 数字货币",
        "  - DOMAIN-KEYWORD,binance,\U0001F4B0 数字货币",
        "  - DOMAIN-KEYWORD,bybit,\U0001F4B0 数字货币",
        "  - DOMAIN-KEYWORD,okx,\U0001F4B0 数字货币",
        "  - DOMAIN-KEYWORD,crypto,\U0001F4B0 数字货币",
    ])

    final = [
        "# Mihomo config: cryptos exchanges + colored icons",
        "# nodes auto-updated by GitHub Actions",
        f"# source: {sub_url}",
        "# icons: https://github.com/Apple9898/ACL4SSR",
        "",
        "proxies:",
        proxies_yml,
        "",
        "proxy-groups:",
        groups_yml,
        "",
        "rules:",
        "  - GEOSITE,private,DIRECT",
        "  - GEOIP,private,DIRECT",
        "  - GEOSITE,category-ads-all,\U0001F6D1 广告拦截",
        rules_yml,
        "  - GEOSITE,cn,\U0001F3AF 全球直连",
        "  - GEOIP,cn,\U0001F3AF 全球直连",
        f"  - MATCH,\U0001F41F 漏网之鱼",
        "",
    ]
    return "\n".join(final)


def update_gist(content, token, gist_id, filename="mihomo_crypto_v3.yaml"):
    body = json.dumps({"files": {filename: {"content": content}}}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/gists/{gist_id}",
        data=body,
        method="PATCH",
        headers={
            "Authorization": f"token {token}",
            "User-Agent": "qwenpaw-gist-updater",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    sub_url = os.environ.get("SUB_URL", "")
    token = os.environ.get("GIST_TOKEN", "")
    gist_id = os.environ.get("GIST_ID", "")
    if not sub_url:
        print("缺少 SUB_URL 环境变量")
        sys.exit(1)

    content = build(sub_url)
    print(f"构建完成: {len(content)} 字符")

    with open("mihomo_crypto_latest.yaml", "w", encoding="utf-8") as f:
        f.write(content)

    if token and gist_id:
        resp = update_gist(content, token, gist_id)
        print(f"gist 已更新: https://gist.github.com/Apple9898/{gist_id}")
    else:
        print("未提供 GIST_TOKEN/GIST_ID，仅本地生成 mihomo_crypto_latest.yaml")


if __name__ == "__main__":
    main()