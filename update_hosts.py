import os
import sys
import time

import requests

# VirusTotal 免费层限制：4 次/分钟、500 次/天。
# 这里每次请求间隔 16 秒，13 个域名约 3.5 分钟跑完，不会触发 429。
REQUEST_INTERVAL = 16
MAX_RETRY = 2

session = requests.Session()
session.headers['X-Apikey'] = os.getenv('VIRUSTOTAL_API_KEY') or ''

_last_call = [0.0]

_STATS = {'domains_queried': 0, 'domains_ok': 0, 'records_found': 0}



def _throttle():
    """控制请求节奏，保证两次请求间隔至少 REQUEST_INTERVAL 秒。"""
    elapsed = time.time() - _last_call[0]
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_call[0] = time.time()


def subdomains(domain):
    for attempt in range(MAX_RETRY + 1):
        _throttle()
        try:
            resp = session.get(
                f'https://www.virustotal.com/api/v3/domains/{domain}/subdomains?limit=1000',
                timeout=30,
            )
        except requests.RequestException as exc:
            if attempt < MAX_RETRY:
                time.sleep(10 * (attempt + 1))
                continue
            print(f'[WARN] {domain}: 网络异常 {exc}', file=sys.stderr)
            return []

        if resp.ok:
            try:
                payload = resp.json()
            except ValueError:
                print(f'[WARN] {domain}: 返回非 JSON', file=sys.stderr)
                return []
            return [
                x['id'] for x in payload.get('data', [])
                if 'attributes' in x
                and any(r.get('type', ' ')[0] == 'A'
                        for r in x['attributes'].get('last_dns_records', []))
            ]

        # 429 限流：等待后重试
        if resp.status_code == 429 and attempt < MAX_RETRY:
            wait = 60 * (attempt + 1)
            print(f'[WARN] {domain}: 触发限流 429，{wait}s 后重试', file=sys.stderr)
            time.sleep(wait)
            continue

        # 其它错误（401 密钥失效 / 403 配额用尽等）：记录后跳过，不中断整个流程
        print(f'[WARN] {domain}: HTTP {resp.status_code} '
              f'{resp.text[:200]}', file=sys.stderr)
        return []

    return []


def sub(domain, fn=None):
    items = [x for x in subdomains(domain) if not fn or fn(x)]
    _STATS['domains_queried'] += 1
    _STATS['records_found'] += len(items)
    _STATS['domains_ok'] += 1 if items else 0
    return '\n'.join(f'0.0.0.0 {x}' for x in items)




hosts = f'''127.0.0.1       localhost
::1             ip6-localhost

# 某些影视/动漫 APP 广告拦截规则

{sub('sigmob.cn')}

{sub('ugdtimg.com')}

0.0.0.0 open.e.kuaishou.com

0.0.0.0 open.e.kuaishou.cn

{sub('adkwai.com')}

{sub('adukwai.com')}

{sub('e.qq.com')}

{sub('gdt.qq.com')}

0.0.0.0 gray.i.gdt.qq.com
0.0.0.0 q.i.gdt.qq.com

0.0.0.0 gray.v.gdt.qq.com

{sub('pangolin-sdk-toutiao.com')}

{sub('pangolin-sdk-toutiao-b.com')}

0.0.0.0 api-access.pangolin-sdk-toutiao1.com

{sub('snssdk.com', lambda x: x.startswith(('pangolin', 'tnc')))}

{sub('zijieapi.com', lambda x: x.startswith(('tnc')))}

{sub('pglstatp-toutiao.com')}

{sub('ctobsnssdk.com')}

0.0.0.0 api.hzsanjiaomao.com

0.0.0.0 api.juliangcili.com

{sub('anythinktech.com')}

0.0.0.0 utoken.umeng.com
0.0.0.0 ulogs.umeng.com

0.0.0.0 mobads.baidu.com
0.0.0.0 mobads-logs.baidu.com
0.0.0.0 als.baidu.com
0.0.0.0 hmma.baidu.com
'''

# 统计本次实际抓到的动态域名条数（静态规则不计）
dynamic_lines = _STATS['records_found']

with open('hosts', 'w') as f:
    f.write(hosts)

print(f'[OK] hosts 已生成，共 {hosts.count(chr(10)) + 1} 行')
print(f'[INFO] 查询域名 {_STATS["domains_queried"]} 个，'
      f'成功 {_STATS["domains_ok"]} 个，抓取记录 {_STATS["records_found"]} 条')
if dynamic_lines == 0:
    # 一个动态域名都没抓到，说明 API 全部失败（无密钥 / 配额用尽 / 被封）
    # 让 workflow 明确失败，而不是静默生成一份空白的 hosts
    print('[ERROR] 未获取到任何动态子域名，请检查 VIRUSTOTAL_API_KEY 是否有效',
          file=sys.stderr)
    sys.exit(1)


