# -*- coding: utf-8 -*-
"""检查 /home/ 返回与商品可售状态的一致性"""
import json, urllib.request

def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode())

home = get('http://127.0.0.1:8000/api/v1/home/')
print('home 条目数:', len(home))
for e in home:
    pd = e.get('product_detail') or {}
    print('-', e.get('kind'), '|', e.get('title'), '| product_id:', e.get('product'),
          '| is_available:', pd.get('is_available'), '| is_published:', pd.get('is_published'))

print()
print('--- 商品 7 当前状态 ---')
try:
    p7 = get('http://127.0.0.1:8000/api/v1/products/7/')
    print('product 7:', p7.get('title'), '| is_published:', p7.get('is_published'), '| is_available:', p7.get('is_available'))
except Exception as ex:
    print('product 7 详情请求失败(可能已从公共目录移除):', ex)

print()
print('--- 公共商品目录中的商品 id ---')
prods = get('http://127.0.0.1:8000/api/v1/products/')
print('可见商品 ids:', [p['id'] for p in prods])
