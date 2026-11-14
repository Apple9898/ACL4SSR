# -*- coding: utf-8 -*-
"""
构建并更新 gist —— 产出 32 分组结构（含全彩色图标 + 币圈规则）。

流程：
  1) 从 SUB_URL 拉取订阅（v2rayN UA -> base64 vless 列表），解码写 mynodes.txt
  2) 调用 build_config.py（被 import 方式复用）产出 32 分组配置
  3) 更新 gist mihomo_crypto_v3.yaml + 仓库 mihomo_crypto_v3.yaml

用法(本地): 设置 SUB_URL/GIST_TOKEN/GIST_ID 环境变量后 python scripts/build_and_update.py
用法(Action): 由 update-gist.yml 调用
"""
import os
import sys
import re
import base64
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_config as bc  # 复用 32 分组构建逻辑


def fetch_vless_list(sub_url):
    """用 v2rayN UA 拉裸 vless 订阅（base64 编码），解码返回行列表"""
    req = urllib.request.Request(sub_url, headers={"User-Agent": "v2rayN/6.23"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    txt = re.sub(r"\s+", "", raw)
    txt += "=" * (-len(txt) % 4)
    dec = base64.b64decode(txt).decode("utf-8", errors="replace")
    lines = [l for l in dec.splitlines() if l.strip() and "vless://" in l]
    if not lines:
        raise RuntimeError("未从订阅解析到 vless 节点")
    return lines


def get_gist_content(token, gist_id, filename):
    req = urllib.request.Request(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"token {token}", "User-Agent": "qwenpaw-gist-updater",
                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        gist = json.loads(resp.read().decode("utf-8"))
    return gist.get("files", {}).get(filename, {}).get("content", "")


def update_gist(content, token, gist_id, filename="mihomo_crypto_v3.yaml"):
    body = json.dumps({"files": {filename: {"content": content}}}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/gists/{gist_id}", data=body, method="PATCH",
        headers={"Authorization": f"token {token}", "User-Agent": "qwenpaw-gist-updater",
                 "Content-Type": "application/json", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


FALLBACK_GROUPS = [
    ("🚀 节点选择", "https://www.apple.com/library/test/success.html", 300, 150),
    ("🚀 手动切换", "https://www.apple.com/library/test/success.html", 300, 150),
    ("🐟 漏网之鱼", "https://www.apple.com/library/test/success.html", 300, 150),
]

# 重组「🚀 节点选择」和「🐟 漏网之鱼」的 proxies 顺序：自动选择→故障转移→国家→手动切换→DIRECT
# 用国旗完整字符匹配（而非前缀），避免 Unicode 码点顺序问题
REORDER_AUTO = ["♻️ 自动选择", "🔯 故障转移", "🔮 负载均衡"]
REORDER_COUNTRY = [
    "🇭🇰 香港节点",
    "🇹🇼 台湾节点",
    "🇸🇬 狮城节点",
    "🇯🇵 日本节点",
    "🇺🇸 美国节点",
    "🇰🇷 韩国节点",
]
REORDER_AFTER = ["🚀 手动切换", "DIRECT"]


def _reorder_proxies(names):
    """按 自动选择→故障转移→负载均衡→国家节点→手动切换→DIRECT 重排"""
    order = REORDER_AUTO + REORDER_COUNTRY + REORDER_AFTER
    reordered = []
    for target in order:
        for n in names:
            if n == target or (target in n and n not in reordered):
                reordered.append(n)
    # 补上遗漏的
    for n in names:
        if n not in reordered:
            reordered.append(n)
    return reordered


def convert_to_fallback(yaml_text):
    """将关键 select 分组转为 fallback，添加 url/interval/tolerance，重组 proxies 顺序"""
    import yaml as _yaml
    data = _yaml.safe_load(yaml_text)
    if not data or "proxy-groups" not in data:
        return yaml_text

    groups = data["proxy-groups"]
    for g in groups:
        if not isinstance(g, dict):
            continue
        name = g.get("name", "")
        for target, url, interval, tolerance in FALLBACK_GROUPS:
            if name == target:
                g["type"] = "fallback"
                g["url"] = url
                g["interval"] = interval
                g["tolerance"] = tolerance
                # 重组 proxies 顺序
                if "proxies" in g and isinstance(g["proxies"], list):
                    g["proxies"] = _reorder_proxies(g["proxies"])
                print(f"  转换: {name} -> fallback (url={url}, interval={interval}, tolerance={tolerance})")
                break

    out = _yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return out


def build_32(sub_url):
    """复用 build_config 的 32 分组构建, 返回 YAML 文本"""
    lines = fetch_vless_list(sub_url)
    # 写入 build_config 期望的 mynodes.txt
    with open("mynodes.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    # 调用 build_config.main 的构建本体（会写 mihomo_crypto.yaml）
    bc.main()
    with open("mihomo_crypto.yaml", "r", encoding="utf-8") as f:
        content = f.read()
    # 后处理：将关键 select 分组转为 fallback
    print("转换关键分组为 fallback...")
    content = convert_to_fallback(content)
    return content


def main():
    sub_url = os.environ.get("SUB_URL", "")
    token = os.environ.get("GIST_TOKEN", "")
    gist_id = os.environ.get("GIST_ID", "")
    filename = os.environ.get("GIST_FILENAME", "mihomo_crypto_v3.yaml")
    if not sub_url:
        print("缺少 SUB_URL 环境变量")
        sys.exit(1)

    content = build_32(sub_url)
    print(f"32 分组构建完成: {len(content)} 字符")

    # 写仓库文件（供 jsDelivr + artifact + 提交）
    with open("mihomo_crypto_latest.yaml", "w", encoding="utf-8") as f:
        f.write(content)

    # 校验结构
    import yaml
    d = yaml.safe_load(content)
    n_proxies = len(d.get("proxies", []))
    n_groups = len(d.get("proxy-groups", []))
    n_icons = sum(1 for g in d.get("proxy-groups", []) if g.get("icon"))
    n_crypto = sum(1 for r in d.get("rules", []) if "数字货币" in str(r))
    print(f"校验: {n_proxies} 节点 / {n_groups} 分组 / {n_icons} 图标 / {n_crypto} 币圈规则")
    if n_groups != 32 or n_icons != 32:
        print("警告: 分组/图标数不是 32, 结构异常")

    if token and gist_id:
        old = get_gist_content(token, gist_id, filename)
        if old == content:
            print("内容无变化，跳过 gist 更新")
        else:
            update_gist(content, token, gist_id, filename)
            print(f"gist 已更新: https://gist.github.com/Apple9898/{gist_id}")
    else:
        print("未提供 GIST_TOKEN/GIST_ID，仅本地生成 mihomo_crypto_latest.yaml")


if __name__ == "__main__":
    main()