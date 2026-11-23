# -*- coding: utf-8 -*-
"""回血口径 e2e：拼车 + 回收全链路（v1.6.20）。"""
import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8017"
def call(method, path, data=None, cookie=None, expect=200):
    h = {"Content-Type": "application/json"} if data is not None else {}
    if cookie: h["Cookie"] = cookie
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, body, h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            code, payload, sc = r.status, r.read(), r.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as e:
        code, payload, sc = e.code, e.read(), ""
    assert code == expect, f"{method} {path} -> {code}: {payload[:200]}"
    return (json.loads(payload) if payload and payload[0] in b'{[' else {}), sc

def get_sub(sub_id, C):
    subs, _ = call("GET", "/api/subscriptions", None, C)
    return next(x for x in subs if x["id"] == sub_id)

_, sc = call("POST", "/api/login", {"password": "test123"})
C = sc.split(";")[0]
def ok(name, cond):
    assert cond, name
    print("OK " + name)

s, _ = call("POST", "/api/subscriptions", {"name":"拼车测试","amount":48,"currency":"CNY","cycle":"monthly","next_billing_date":"2026-12-05","payment_method":"auto","share_count":4}, C)
ok("拼车创建 share_count=4", s["share_count"] == 4)
ok("份额月均 12", s["monthly_cost_share"] == 12.0)
ok("净月均 12（无回收）", s["monthly_cost_net"] == 12.0)

r, _ = call("POST", f"/api/subscriptions/{s['id']}/rebates", {"date":"2026-11-20","amount":10,"note":"拼车对象出钱"}, C)
ok("回收记入", r["amount"] == 10)
s2 = get_sub(s["id"], C)
ok("回收后净月均 2（月付摊 1 个月）", s2["monthly_cost_net"] == 2.0)

s3, _ = call("PUT", f"/api/subscriptions/{s['id']}", {"share_count":1}, C)
ok("share_count=1 归零", s3["share_count"] == 0)
ok("不拼车后净=48-回收10=38（回收独立于拼车）", s3["monthly_cost_net"] == 38.0)

lst, _ = call("GET", f"/api/subscriptions/{s['id']}/rebates", None, C)
ok("回收列表 1 笔合计 10", len(lst["rebates"]) == 1 and lst["total"] == 10)
call("DELETE", f"/api/subscriptions/{s['id']}/rebates/{lst['rebates'][0]['id']}", None, C)
lst2, _ = call("GET", f"/api/subscriptions/{s['id']}/rebates", None, C)
ok("删除后列表空", len(lst2["rebates"]) == 0)

s4, _ = call("POST", "/api/subscriptions", {"name":"年付回收测试","amount":128,"currency":"CNY","cycle":"yearly","next_billing_date":"2027-01-01","payment_method":"manual"}, C)
call("POST", f"/api/subscriptions/{s4['id']}/rebates", {"date":"2026-11-01","amount":80}, C)
s4b = get_sub(s4["id"], C)
ok("年付回收摊销 净 4", s4b["monthly_cost_net"] == 4.0)

st, _ = call("GET", "/api/stats", None, C)
ok("stats 有 monthly_total_net", "monthly_total_net" in st)
ok("净 < 标价", st["monthly_total_net"] < st["monthly_total"])

call("POST", f"/api/subscriptions/{s['id']}/rebates", {"date":"2026-11-20","amount":-5}, C, expect=400)
print("OK 回收负数 400")
call("PUT", f"/api/subscriptions/{s['id']}", {"share_count":100}, C, expect=400)
print("OK 拼车人数 100 400")

call("DELETE", f"/api/subscriptions/{s['id']}", None, C)
call("DELETE", f"/api/subscriptions/{s4['id']}", None, C)
print("回血口径 e2e 全部通过")
