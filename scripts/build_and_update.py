# -*- coding: utf-8 -*-
"""
自动构建并更新 gist 配置 —— 基于机场提供的完整 Clash 配置，只注入彩色图标。

关键修复(2026-11-13)：
  之前用默认 UA 拉裸 vless 列表，自己手工转换 -> 丢失 DNS 等关键配置 -> 订阅后无法上网。
  现在改为：用 clash-verge UA 拉取机场下发的"完整 Clash 配置"（自带 dns/proxies/
  proxy-groups/rules/rule-providers），脚本只做一件事：给每个 proxy-group 注入 icon。
  这样源头正确，自动更新不会再生成坏配置。

用法(本地): python scripts/build_and_update.py  (需环境变量 SUB_URL)
用法(Action): 由 update-gist.yml 调用
环境变量:
  SUB_URL    机场订阅地址 (必填)
  GIST_TOKEN 有 gist scope 的 PAT (提供则更新 gist)
  GIST_ID    gist id (与 GIST_TOKEN 一起提供则更新)
  GIST_FILENAME  gist 中的文件名 (默认 mihomo_crypto_v3.yaml)
"""
import os
import sys
import json
import urllib.request
import io

import yaml

BASE = "https://cdn.jsdelivr.net/gh/Apple9898/ACL4SSR@main/icons/"

# 分组名 -> 图标文件（与 clash.icons.js 中 EXACT 映射一致）
ICON_MAP = {
    "🚀 节点选择": "mini_Static.png",
    "🚀 手动切换": "mini_Available.png",
    "♻️ 自动选择": "qure_Auto.png",
    "🔯 故障转移": "qure_ULB.png",
    "🔮 负载均衡": "qure_Round_Robin.png",
    "💰 数字货币": "btc.png",
    "🤖 Ai平台": "qure_AI.png",
    "🤖 Claude": "sins_Claude.png",
    "🤖 OpenAI": "mini_OpenAI.png",
    "✨ Gemini": "sins_Gemini.png",
    "🐦 推特": "x_twitter.png",
    "🎵 TikTok": "qure_TikTok.png",
    "🎧 Spotify": "sins_Spotify.png",
    "🎶 网易音乐": "qure_Music.png",
    "🎮 游戏平台": "qure_Game.png",
    "▶️ 油管视频": "qure_YouTube.png",
    "🎥 奈飞视频": "mini_Netflix.png",
    "🏰 迪士尼": "qure_Disney.png",
    "🔍 谷歌": "mini_Google.png",
    "☁️ Cloudflare": "qure_Cloudflare.png",
    "📺 巴哈姆特": "qure_Bahamut.png",
    "📺 哔哩哔哩": "qure_bilibili.png",
    "📢 谷歌FCM": "mini_Google.png",
    "Ⓜ️ 微软Bing": "mini_Bing.png",
    "Ⓜ️ 微软云盘": "qure_Microsoft.png",
    "Ⓜ️ 微软服务": "qure_Microsoft.png",
    "🍎 苹果服务": "qure_Apple.png",
    "🍏 苹果国际": "qure_Apple.png",
    "🌍 国外媒体": "qure_ForeignMedia.png",
    "🌏 国内媒体": "qure_China.png",
    "🔞 成人内容": "qure_Heart.png",
    "🛑 广告拦截": "qure_AdBlack.png",
    "🍃 应用净化": "qure_Filter.png",
    "🎯 全球直连": "qure_China.png",
    "🐟 漏网之鱼": "qure_Final.png",
    "🇭🇰 香港节点": "mini_HK.png",
    "🇯🇵 日本节点": "mini_JP.png",
    "🇺🇲 美国节点": "mini_US.png",
    "🇨🇳 台湾节点": "mini_TW.png",
    "🇸🇬 狮城节点": "mini_SG.png",
    "🇰🇷 韩国节点": "mini_KR.png",
    "🔞 成人内容": "qure_Heart.png",
    "🛑 广告拦截": "qure_AdBlack.png",
}

# 兜底: 关键词 -> 图标（无精确匹配时）
KEYWORD_ICON = [
    ("币", "btc.png"),
    ("加密", "btc.png"),
    ("数字货币", "btc.png"),
    ("AI", "qure_AI.png"),
    ("Claude", "sins_Claude.png"),
    ("Gemini", "sins_Gemini.png"),
    ("Telegram", "mini_Telegram.png"),
    ("电报", "mini_Telegram.png"),
    ("YouTube", "qure_YouTube.png"),
    ("油管", "qure_YouTube.png"),
    ("Netflix", "mini_Netflix.png"),
    ("奈飞", "mini_Netflix.png"),
    ("Disney", "qure_Disney.png"),
    ("Spotify", "sins_Spotify.png"),
    ("TikTok", "qure_TikTok.png"),
    ("推特", "x_twitter.png"),
    ("Twitter", "x_twitter.png"),
    ("谷歌", "mini_Google.png"),
    ("Cloudflare", "qure_Cloudflare.png"),
    ("DIRECT", "qure_Direct.png"),
]


def fetch_full_config(url):
    """用 clash-verge UA 拉取完整 Clash 配置（不是裸 vless）"""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "clash-verge/v2.4.5"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def pick_icon(name):
    if not name:
        return None
    n = name.strip()
    if n == "DIRECT":
        return "qure_Direct.png"
    if n in ICON_MAP:
        return ICON_MAP[n]
    for kw, icon in KEYWORD_ICON:
        if kw in n:
            return icon
    return None


def build(sub_url):
    """以完整配置为基础，仅注入 icon"""
    raw = fetch_full_config(sub_url)
    data = yaml.safe_load(raw)
    if not data or "proxies" not in data:
        raise RuntimeError("未获取到完整配置或缺少 proxies")

    groups = data.get("proxy-groups", []) or []
    injected = 0
    for g in groups:
        if not isinstance(g, dict):
            continue
        icon_file = pick_icon(g.get("name", ""))
        if icon_file:
            g["icon"] = BASE + icon_file
            injected += 1

    print(f"完整配置: {len(data.get('proxies', []))} 节点, {len(groups)} 分组, 注入 {injected} 个图标")

    out = io.StringIO()
    yaml.safe_dump(data, out, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return out.getvalue()


def get_gist_content(token, gist_id, filename):
    req = urllib.request.Request(
        f"https://api.github.com/gists/{gist_id}",
        headers={
            "Authorization": f"token {token}",
            "User-Agent": "qwenpaw-gist-updater",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        gist = json.loads(resp.read().decode("utf-8"))
    return gist.get("files", {}).get(filename, {}).get("content", "")


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
    filename = os.environ.get("GIST_FILENAME", "mihomo_crypto_v3.yaml")
    if not sub_url:
        print("缺少 SUB_URL 环境变量")
        sys.exit(1)

    content = build(sub_url)
    print(f"构建完成: {len(content)} 字符")

    with open("mihomo_crypto_latest.yaml", "w", encoding="utf-8") as f:
        f.write(content)

    if token and gist_id:
        old = get_gist_content(token, gist_id, filename)
        if old == content:
            print("内容无变化，跳过更新")
        else:
            resp = update_gist(content, token, gist_id, filename)
            print(f"gist 已更新: https://gist.github.com/Apple9898/{gist_id}")
    else:
        print("未提供 GIST_TOKEN/GIST_ID，仅本地生成 mihomo_crypto_latest.yaml")


if __name__ == "__main__":
    main()