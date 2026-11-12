// Auto-inject colored icons for Clash Verge Rev (Mihomo)
// 彩色图标自动注入脚本 —— 订阅更新时自动为代理分组打上图标
// 图标托管在: https://github.com/Apple9898/ACL4SSR/tree/main/icons
// 用法: Clash Verge Rev -> 订阅 -> 编辑增强(Script) -> URL 填本文件地址
// 或: 订阅右键 -> 编辑文件 -> 把本文件内容粘贴到 Script 增强里
// CDN: https://cdn.jsdelivr.net/gh/Apple9898/ACL4SSR@main/clash.icons.js

function main(config, profileName) {
  const BASE = "https://cdn.jsdelivr.net/gh/Apple9898/ACL4SSR@main/icons/";

  function icon(name) {
    return BASE + name;
  }

  // 精确分组名 -> 图标文件名
  const EXACT = {
    "🚀 节点选择": "mini_Static.png",
    "🚀 手动切换": "mini_Available.png",
    "♻️ 自动选择": "qure_Auto.png",
    "🔯 故障转移": "qure_ULB.png",
    "🔮 负载均衡": "qure_Round_Robin.png",
    "💰 数字货币": "qure_Cryptocurrency.png",
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
    "🌏 国内媒体": "qure_China.png",
    "🌍 国外媒体": "qure_ForeignMedia.png",
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
  };

  // 兜底: 按关键词模糊匹配（无精确匹配时）
  const KEYWORD = [
    ["币", "qure_Cryptocurrency.png"],
    ["加密", "qure_Cryptocurrency.png"],
    ["HK", "mini_HK.png"],
    ["香港", "mini_HK.png"],
    ["JP", "mini_JP.png"],
    ["日本", "mini_JP.png"],
    ["US", "mini_US.png"],
    ["美国", "mini_US.png"],
    ["TW", "mini_TW.png"],
    ["台湾", "mini_TW.png"],
    ["SG", "mini_SG.png"],
    ["狮城", "mini_SG.png"],
    ["新加坡", "mini_SG.png"],
    ["KR", "mini_KR.png"],
    ["韩国", "mini_KR.png"],
    ["AI", "qure_AI.png"],
    ["GPT", "mini_OpenAI.png"],
    ["OpenAI", "mini_OpenAI.png"],
    ["Claude", "sins_Claude.png"],
    ["Gemini", "sins_Gemini.png"],
    ["Telegram", "mini_Telegram.png"],
    ["电报", "mini_Telegram.png"],
    ["YouTube", "qure_YouTube.png"],
    ["油管", "qure_YouTube.png"],
    ["Netflix", "mini_Netflix.png"],
    ["奈飞", "mini_Netflix.png"],
    ["Disney", "qure_Disney.png"],
    ["Spotify", "sins_Spotify.png"],
    ["TikTok", "qure_TikTok.png"],
    ["Twitter", "x_twitter.png"],
    ["推特", "x_twitter.png"],
    ["DIRECT", "qure_Direct.png"],
    ["直连", "qure_Direct.png"],
  ];

  if (!config || !Array.isArray(config["proxy-groups"])) {
    return config;
  }

  for (const g of config["proxy-groups"]) {
    if (!g || !g.name) continue;
    const name = String(g.name).trim();
    if (name === "DIRECT") {
      g.icon = icon("qure_Direct.png");
      continue;
    }
    if (EXACT[name]) {
      g.icon = icon(EXACT[name]);
      continue;
    }
    for (const [kw, file] of KEYWORD) {
      if (name.includes(kw)) {
        g.icon = icon(file);
        break;
      }
    }
  }

  return config;
}