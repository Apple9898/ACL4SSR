# -*- coding: utf-8 -*-
"""构建完整 Mihomo 配置：vless 节点 + 彩色图标分组 + 币圈规则"""
import urllib.parse
import re
from collections import defaultdict

# 注意: 必须用 testingcf.jsdelivr.net（jsDelivr 的 Cloudflare 入口）
# cdn.jsdelivr.net 会把国内请求路由到 Fastly 节点，而 Fastly 对本仓库的
# PNG 图标持久返回 301 跳转到 raw.githubusercontent.com（国内被墙），
# 导致 Clash Verge 图标下载失败。Cloudflare 入口实测 200 正常。
BASE = "https://testingcf.jsdelivr.net/gh/Apple9898/ACL4SSR@main/icons/"

FLAG = {
    "SG": "\U0001F1F8\U0001F1EC",  # 🇸🇬
    "HK": "\U0001F1ED\U0001F1F0",  # 🇭🇰
    "TW": "\U0001F1F9\U0001F1FC",  # 🇹🇼
    "JP": "\U0001F1EF\U0001F1F5",  # 🇯🇵
    "US": "\U0001F1FA\U0001F1F8",  # 🇺🇸
    "KR": "\U0001F1F0\U0001F1F7",  # 🇰🇷
}


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
    lines = []
    lines.append(f"  - name: {node['name']}")
    lines.append("    type: vless")
    lines.append(f"    server: {node['server']}")
    lines.append(f"    port: {node['port']}")
    lines.append(f"    uuid: {node['uuid']}")
    lines.append("    udp: true")
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


def main():
    with open("mynodes.txt", "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    nodes = []
    for line in raw_lines:
        n = parse_vless(line)
        if n:
            nodes.append(n)
    print(f"解析到 {len(nodes)} 个节点")

    # 重命名：国家码 + 国旗 emoji + 序号（参考用户原配置风格）
    counter = defaultdict(int)
    renamed = []
    for n in nodes:
        cc = country_code(n["name"])
        if cc in FLAG:
            counter[cc] += 1
            idx = counter[cc]
            base = f"{FLAG[cc]} {cc}"
            n["name"] = base if idx == 1 else f"{base} {idx}"
        else:
            counter[n["name"]] += 1
            idx = counter[n["name"]]
            n["name"] = n["name"] if idx == 1 else f"{n['name']} {idx}"
        renamed.append(n)

    # 展示前 10 个名字
    for n in renamed[:12]:
        print("  ", n["name"])

    # ========== proxies ==========
    proxies_yml = "\n".join(to_clash_yaml(n) for n in renamed)

    # ========== proxy-groups（带彩色图标）==========
    def group(name, gtype, icon, *, proxies=None, url=None, interval=300, include_all=False, filter_=None):
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

    # 地区组名称（先定义，供后面的调度组引用）
    G_HK = "\U0001F1ED\U0001F1F0 香港节点"
    G_TW = "\U0001F1F9\U0001F1FC 台湾节点"
    G_SG = "\U0001F1F8\U0001F1EC 狮城节点"
    G_JP = "\U0001F1EF\U0001F1F5 日本节点"
    G_US = "\U0001F1FA\U0001F1F8 美国节点"
    G_KR = "\U0001F1F0\U0001F1F7 韩国节点"
    G_AUTO = "\u267B\uFE0F 自动选择"
    G_FB = "\U0001F52F 故障转移"
    G_LB = "\U0001F52E 负载均衡"
    G_MANUAL = "\U0001F680 手动切换"
    G_SELECT = "\U0001F680 节点选择"
    G_FINAL = "\U0001F41F 漏网之鱼"

    area_list = [G_HK, G_TW, G_SG, G_JP, G_US, G_KR]

    # 节点选择：总开关。成员只放「并联」的独立调度组和地区组，不再内嵌巨型节点列表
    # 末端不放 DIRECT —— 避免所有节点挂掉时静默直连暴露真实 IP
    g_select_members = [G_AUTO, G_FB, G_LB] + area_list + [G_MANUAL, G_FINAL]

    groups = []
    groups.append(group(G_SELECT, "select", "mini_Static.png", proxies=g_select_members))
    groups.append(group(G_MANUAL, "select", "mini_Available.png", include_all=True))
    groups.append(group(G_AUTO, "url-test", "qure_Auto.png",
                        url="https://www.gstatic.com/generate_204", interval=300, include_all=True))
    # 故障转移 / 负载均衡：成员改为六个地区组（组级），不再 include-all 全量节点
    # 地区组内部已各自 url-test，天然分散；这样健康检查从 102×2 降到 6×2 次组级探测
    groups.append(group(G_FB, "fallback", "qure_ULB.png",
                        url="https://www.gstatic.com/generate_204", interval=300,
                        proxies=area_list))
    groups.append(group(G_LB, "load-balance", "qure_Round_Robin.png",
                        url="https://www.gstatic.com/generate_204", interval=300,
                        proxies=area_list))

    area = [
        (G_HK, "mini_HK.png", "(?i)HK|香港|港"),
        (G_TW, "mini_TW.png", "(?i)TW|台湾|台"),
        (G_SG, "mini_SG.png", "(?i)SG|新加坡|狮城"),
        (G_JP, "mini_JP.png", "(?i)JP|日本"),
        (G_US, "mini_US.png", "(?i)US|美国"),
        (G_KR, "mini_KR.png", "(?i)KR|韩国"),
    ]
    for name, icon, pattern in area:
        # 地区组同时支持按名称自动包含 + 显式列出（兼容 Clash Verge 各种内核版本）
        groups.append(group(name, "url-test", icon,
                            url="https://www.gstatic.com/generate_204", interval=300,
                            include_all=True, filter_=pattern))

    # 业务分组可选的出口（顺序即优先级，用户可在界面上改）
    business_proxies = [G_SG, G_JP, G_HK, G_TW, G_US, G_KR,
                        G_AUTO, G_FB, G_MANUAL, "DIRECT"]

    bz = [
        ("\U0001F4B0 数字货币", "btc.png"),
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
    ]
    for name, icon in bz:
        groups.append(group(name, "select", icon, proxies=business_proxies))

    # 漏网之鱼：独立备用出口组（成员是原始调度组，不回指节点选择/漏网之鱼，避免循环）
    groups.append(group(G_FINAL, "select", "qure_Final.png",
                        proxies=[G_AUTO, G_FB, G_LB] + area_list + [G_MANUAL]))

    groups_yml = "\n".join(groups)

    # ========== 币圈规则（全部交易所） ==========
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

    crypto_rules = []
    # 先按后缀（避免 keyword 提前截获 suffix 语义，这里统一用 DOMAIN-SUFFIX）
    for d in crypto_domains:
        crypto_rules.append(f"  - DOMAIN-SUFFIX,{d},\U0001F4B0 数字货币")
    crypto_rules.append("  - DOMAIN-KEYWORD,bitunix,\U0001F4B0 数字货币")
    crypto_rules.append("  - DOMAIN-KEYWORD,binance,\U0001F4B0 数字货币")
    crypto_rules.append("  - DOMAIN-KEYWORD,bybit,\U0001F4B0 数字货币")
    crypto_rules.append("  - DOMAIN-KEYWORD,okx,\U0001F4B0 数字货币")
    crypto_rules.append("  - DOMAIN-KEYWORD,crypto,\U0001F4B0 数字货币")

    rules_yml = "\n".join(crypto_rules)

    # ========== 平台分流规则（让每个分组真正生效） ==========
    # 顺序很重要：越具体的平台越靠前，避免被通用 GEOSITE 抢走
    platform_rules = [
        # --- AI 平台（OpenAI / Claude / Gemini 先于通用 Ai平台） ---
        ("GEOSITE,openai",              "\U0001F916 OpenAI"),
        ("GEOSITE,anthropic",           "\U0001F916 Claude"),
        ("GEOSITE,google-gemini",       "\u2728 Gemini"),
        ("GEOSITE,category-ai-!cn",     "\U0001F916 Ai平台"),
        # --- 流媒体 ---
        ("GEOSITE,youtube",             "\u25B6\uFE0F 油管视频"),
        ("GEOSITE,netflix",             "\U0001F3A5 奈飞视频"),
        ("GEOSITE,disney",              "\U0001F3F0 迪士尼"),
        ("GEOSITE,spotify",             "\U0001F3A7 Spotify"),
        ("GEOSITE,tiktok",              "\U0001F3B5 TikTok"),
        # --- 社交通讯 ---
        ("GEOSITE,telegram",            "\U0001F4F2 电报消息"),
        ("GEOSITE,twitter",             "\U0001F426 推特"),
        # --- 基础服务 ---
        ("GEOSITE,google",              "\U0001F50D 谷歌"),
        ("GEOSITE,cloudflare",          "\u2601\uFE0F Cloudflare"),
        ("GEOSITE,apple@cn",            "\U0001F34E 苹果服务"),
        ("GEOSITE,apple",               "\U0001F34E 苹果服务"),
        # --- 媒体聚合 / 内容分类 ---
        ("GEOSITE,category-media-cn",   "\U0001F30F 国内媒体"),
        ("GEOSITE,category-media",      "\U0001F30D 国外媒体"),
        ("GEOSITE,category-porn",       "\U0001F51E 成人内容"),
    ]
    platform_rules_yml = "\n".join(f"  - {k},{v}" for k, v in platform_rules)

    # ========== 组装 ==========
    final = []
    final.append("# Mihomo config: cryptos exchanges + colored icons")
    final.append("# nodes from edge.raysol.dpdns.org (edgetunel)")
    final.append("# icons: https://github.com/Apple9898/ACL4SSR")
    final.append("")
    final.append("proxies:")
    final.append(proxies_yml)
    final.append("")
    final.append("proxy-groups:")
    final.append(groups_yml)
    final.append("")
    final.append("rules:")
    final.append("  # 1) 私有网络")
    final.append("  - GEOSITE,private,\U0001F3AF 全球直连")
    final.append("  - GEOIP,private,\U0001F3AF 全球直连,no-resolve")
    final.append("  # 2) 广告拦截")
    final.append("  - GEOSITE,category-ads-all,\U0001F6D1 广告拦截")
    final.append("  # 3) 币圈")
    final.append(rules_yml)
    final.append("  # 3.5) Cloudflare 全量（必须早于 GEOSITE,openai，否则 challenges.cloudflare.com 被 OpenAI 抢走）")
    final.append("  - DOMAIN-SUFFIX,cloudflare.com,☁️ Cloudflare")
    final.append("  - DOMAIN-SUFFIX,workers.dev,☁️ Cloudflare")
    final.append("  - DOMAIN-SUFFIX,cfargotunnel.com,☁️ Cloudflare")
    final.append("  - DOMAIN-SUFFIX,pagecdn.io,☁️ Cloudflare")
    final.append("  - DOMAIN-SUFFIX,cloudflareinsights.com,☁️ Cloudflare")
    final.append("  # 4) 平台分流（按具体度排序）")
    final.append(platform_rules_yml)
    final.append("  # 5) 国内直连")
    final.append("  - GEOSITE,cn,\U0001F3AF 全球直连")
    final.append("  - GEOIP,cn,\U0001F3AF 全球直连")
    final.append("  # 6) 兜底：走总开关，这样「🚀 节点选择」切什么，所有未匹配流量跟什么")
    final.append(f"  - MATCH,{G_SELECT}")
    final.append("")

    content = "\n".join(final)
    with open("mihomo_crypto.yaml", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n生成 mihomo_crypto.yaml: {len(content)} 字符")
    # 统计
    print(f"  节点: {len(renamed)}")
    print(f"  分组: {len(groups)}")
    print(f"  币圈规则: {len(crypto_rules)}")
    print(f"  平台规则: {len(platform_rules)}")


if __name__ == "__main__":
    main()