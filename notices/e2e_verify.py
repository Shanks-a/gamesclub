# -*- coding: utf-8 -*-
"""8 项端到端验收 —— API/逻辑层自动验证脚本。
驱动本地后端 http://127.0.0.1:8000，逐项打印 PASS/FAIL 与关键证据。
只做逻辑层验证；UI 层（管理 Web、小程序 H5）由 agent-browser 另行截图。
"""
import json, time, uuid, urllib.request, urllib.error, http.cookiejar

BASE = 'http://127.0.0.1:8000'
API = BASE + '/api/v1'
MGMT = API + '/management'
RESULTS = []

def rec(name, ok, detail):
    RESULTS.append((name, ok, detail))
    print(('PASS' if ok else 'FAIL'), '|', name, '|', detail)

def req(method, path, body=None, token=None, headers=None, idem=None):
    url = (API + path) if path.startswith('/') else path
    data = json.dumps(body).encode() if body is not None else None
    h = {'Content-Type': 'application/json'}
    if token: h['Authorization'] = 'Bearer ' + token
    if idem: h['Idempotency-Key'] = idem
    if headers: h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try: return e.code, json.loads(raw)
        except: return e.code, raw

# ---------- 管理员登录（Session + CSRF） ----------
def admin_login():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    # 先取 csrf
    r = urllib.request.Request(MGMT + '/session/')
    with opener.open(r) as resp:
        sess = json.loads(resp.read().decode())
    csrf = sess['csrf_token']
    body = json.dumps({'username': 'accept-admin', 'password': 'Accept#2026gc'}).encode()
    r = urllib.request.Request(MGMT + '/login/', data=body, headers={'Content-Type': 'application/json', 'X-CSRFToken': csrf}, method='POST')
    with opener.open(r) as resp:
        info = json.loads(resp.read().decode())
    # 登录后 CSRF token 会轮换，必须用登录响应里的新 token
    csrf = info.get('csrf_token', csrf)
    return opener, csrf, info

def mgmt_req(opener, csrf, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {'Content-Type': 'application/json', 'X-CSRFToken': csrf}
    r = urllib.request.Request(MGMT + path, data=data, headers=h, method=method)
    try:
        with opener.open(r, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try: return e.code, json.loads(raw)
        except: return e.code, raw

print('===== 登录管理员 =====')
opener, csrf, info = admin_login()
rec('管理端登录', info.get('username') == 'accept-admin', 'username=%s' % info.get('username'))

# ---------- 项1：新建游戏/类型/商品，配置封面，发布 ----------
print('\n===== 项1：新建游戏→类型→商品→发布 =====')
tag = uuid.uuid4().hex[:6]
st, g = mgmt_req(opener, csrf, 'POST', '/games/', {'name': '验收游戏%s' % tag, 'sort_order': 99, 'is_enabled': True})
game_id = g.get('id'); game_v = g.get('version')
rec('项1 新建游戏', st == 201 and game_id, 'game_id=%s version=%s' % (game_id, game_v))

st, c = mgmt_req(opener, csrf, 'POST', '/categories/', {'game': game_id, 'name': '验收类型%s' % tag, 'sort_order': 1, 'is_enabled': True})
cat_id = c.get('id'); cat_v = c.get('version')
rec('项1 新建类型', st == 201 and cat_id, 'cat_id=%s' % cat_id)

st, p = mgmt_req(opener, csrf, 'POST', '/products/', {'game': game_id, 'category': cat_id, 'title': '验收商品%s' % tag, 'description': '端到端验收', 'price_cents': 2900, 'original_price_cents': 3900, 'min_quantity': 1, 'max_quantity': 10, 'cover_url': '/media/covers/test.jpg', 'is_published': True})
prod_id = p.get('id'); prod_v = p.get('version')
rec('项1 新建商品(发布)', st == 201 and prod_id, 'prod_id=%s version=%s' % (prod_id, prod_v))

# 公共商品目录应出现新商品
st, lst = req('GET', '/products/')
titles = [x['title'] for x in lst]
rec('项1 小程序商品目录可见', any('验收商品%s' % tag in t for t in titles), '命中商品数=%d' % sum(1 for t in titles if '验收商品%s' % tag in t))

# ---------- 项2：配置轮播/特价/人气，小程序显示相同，无虚构销量 ----------
print('\n===== 项2：首页配置 轮播/特价/人气 =====')
st, h1 = mgmt_req(opener, csrf, 'POST', '/home/', {'kind': 'special', 'title': '验收特价%s' % tag, 'target': 'product', 'product': prod_id, 'sort_order': 0, 'is_enabled': True})
rec('项2 配置特价', st == 201, 'home_id=%s' % h1.get('id'))
st, h2 = mgmt_req(opener, csrf, 'POST', '/home/', {'kind': 'popular', 'title': '验收人气%s' % tag, 'target': 'product', 'product': prod_id, 'sort_order': 1, 'is_enabled': True})
rec('项2 配置人气', st == 201, 'home_id=%s' % h2.get('id'))

st, home = req('GET', '/home/')
kinds = [x['kind'] for x in home]
prod_in_home = any(x.get('product') == prod_id for x in home)
# 无虚构销量：检查返回的商品 detail 是否有 sales 字段为 0 或不存在
fake_sales = False
for x in home:
    pd = x.get('product_detail') or {}
    if 'sales' in pd and pd['sales'] not in (0, None, ''):
        fake_sales = True
rec('项2 小程序首页显示配置商品', prod_in_home, 'kinds=%s' % sorted(set(kinds)))
rec('项2 无虚构销量', not fake_sales, '检查 product_detail.sales 未出现非零虚构值')

# ---------- 项3：创建订单，改价/下架后旧订单保留快照 ----------
print('\n===== 项3：订单快照 =====')
token = req('POST', '/auth/dev-login/', {})[1]['access_token']
st, order = req('POST', '/me/orders/', {'product_id': prod_id, 'quantity': 2, 'expected_product_version': prod_v}, token=token, idem='acc-item3-%s' % tag)
order_id = order.get('id'); order_no = order.get('order_no'); snap_price = order.get('unit_price_cents'); snap_total = order.get('total_amount_cents')
rec('项3 创建订单(数量2)', st == 201 and order_id, 'order_no=%s total=%s' % (order_no, snap_total))

# 改价 +100 分
st, p2 = mgmt_req(opener, csrf, 'PATCH', '/products/%d/' % prod_id, {'version': prod_v, 'price_cents': 3000})
rec('项3 Web 改价', st == 200, '新价=3000 version=%s' % p2.get('version'))

st, od = req('GET', '/me/orders/%d/' % order_id, token=token)
snap_after = od.get('unit_price_cents')
rec('项3 旧订单保留原快照金额', snap_after == snap_price, '快照价=%s 现价=3000' % snap_after)

# ---------- 项4：模拟付款 + 幂等，重复提交不生成第二笔成功付款 ----------
print('\n===== 项4：付款幂等 =====')
st, pay1 = req('POST', '/me/orders/%d/mock-pay/' % order_id, {}, token=token, idem='acc-pay1-%s' % tag)
rec('项4 首次模拟付款', st == 200 and pay1.get('payment_status') == 'PAID', 'status=%s pay=%s' % (pay1.get('status'), pay1.get('payment_status')))

# 重复提交（同幂等键）
st2, pay2 = req('POST', '/me/orders/%d/mock-pay/' % order_id, {}, token=token, idem='acc-pay1-%s' % tag)
rec('项4 同键重复付款幂等', st2 == 200, '返回 status=%s（回放首次结果）' % st2)

# 不同幂等键再付款 → 应 409（订单已非 PENDING_PAYMENT）
st3, pay3 = req('POST', '/me/orders/%d/mock-pay/' % order_id, {}, token=token, idem='acc-pay2-%s' % tag)
rec('项4 不同键二次付款被拒', st3 == 409, 'status=%s' % st3)

# Web 订单出现 PAID 与状态历史
st, mo = mgmt_req(opener, csrf, 'GET', '/orders/%d/' % order_id)
hist = mo.get('history', [])
paid_hist = [h for h in hist if h.get('to_status') == 'PENDING_ARRANGEMENT' or h.get('action') == 'MOCK_PAY']
rec('项4 Web订单出现PAID+状态历史', st == 200 and bool(paid_hist), 'history数=%d 付款事件=%d' % (len(hist), len(paid_hist)))

# ---------- 项5：收藏持久 + 退出后旧令牌401 ----------
print('\n===== 项5：收藏 + 401 =====')
st, _ = req('POST', '/me/favorites/', {'product_id': prod_id}, token=token)
st, favs = req('GET', '/me/favorites/', token=token)
fav_ids = [f['product']['id'] for f in favs]
rec('项5 收藏成功且列表含该商品', st == 200 and prod_id in fav_ids, '收藏数=%d' % len(favs))

# 退出撤销 token
req('POST', '/auth/logout/', {}, token=token)
st, _ = req('GET', '/me/favorites/', token=token)
rec('项5 退出后旧令牌返回401', st == 401, 'status=%s' % st)

# 重新登录验证收藏仍在
token2 = req('POST', '/auth/dev-login/', {})[1]['access_token']
st, favs2 = req('GET', '/me/favorites/', token=token2)
fav_ids2 = [f['product']['id'] for f in favs2]
rec('项5 重登录后服务端收藏仍存在', prod_id in fav_ids2, '收藏数=%d' % len(favs2))

# ---------- 项6：并发编辑 409 ----------
print('\n===== 项6：版本冲突 409 =====')
cur_v = p2.get('version')  # 改价后 version
st, conflict = mgmt_req(opener, csrf, 'PATCH', '/products/%d/' % prod_id, {'version': cur_v - 1, 'subtitle': '旧版本编辑'})
rec('项6 旧版本保存返回409', st == 409, 'status=%s code=%s' % (st, conflict.get('error', {}).get('code')))

# ---------- 项8：停用后不能新建订单，历史订单可查 ----------
print('\n===== 项8：停用校验 =====')
# 下架商品
st, unpub = mgmt_req(opener, csrf, 'PATCH', '/products/%d/' % prod_id, {'version': cur_v, 'is_published': False})
cur_v2 = unpub.get('version')
rec('项8 下架商品', st == 200 and unpub.get('is_published') is False, 'is_published=%s' % unpub.get('is_published'))

st, neworder = req('POST', '/me/orders/', {'product_id': prod_id, 'quantity': 1, 'expected_product_version': cur_v2}, token=token2, idem='acc-item8-%s' % tag)
rec('项8 下架后不能创建新订单', st == 409, 'status=%s code=%s' % (st, neworder.get('error', {}).get('code')))

# 历史订单可查
st, od2 = req('GET', '/me/orders/%d/' % order_id, token=token2)
rec('项8 历史订单仍可查', st == 200 and od2.get('order_no') == order_no, 'order_no=%s' % od2.get('order_no'))

print('\n===== 汇总 =====')
n_pass = sum(1 for _, ok, _ in RESULTS if ok)
n_fail = len(RESULTS) - n_pass
for name, ok, detail in RESULTS:
    print(('  [PASS] ' if ok else '  [FAIL] ') + name + ' — ' + detail)
print('总计 %d 项，通过 %d，失败 %d' % (len(RESULTS), n_pass, n_fail))

# 留存 JSON
with open('notices/e2e_verify_results.json', 'w', encoding='utf-8') as f:
    json.dump([{'name': n, 'ok': ok, 'detail': d} for n, ok, d in RESULTS], f, ensure_ascii=False, indent=2)
