"""API 端到端测试脚本"""
import requests
import json

BASE = "http://localhost:8000"
passed = 0
failed = 0

def test(name, func):
    global passed, failed
    try:
        func()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1

# 1. 用户登录
user_token = None
def test_login():
    global user_token
    r = requests.post(f"{BASE}/api/auth/login", json={"username":"user","password":"user123","role":"user"})
    assert r.status_code == 200, f"status={r.status_code}, body={r.text}"
    data = r.json()
    assert "token" in data
    user_token = data["token"]

test("用户登录", test_login)

# 2. 商品列表
def test_products():
    r = requests.get(f"{BASE}/api/products?page=1&page_size=3")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0, "no products"

test("商品列表", test_products)

# 3. 加入购物车
def test_add_cart():
    r = requests.post(f"{BASE}/api/user/cart",
        json={"product_id": 3, "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code in (200, 201), f"status={r.status_code}, body={r.text}"

test("加入购物车", test_add_cart)

# 4. 获取购物车
def test_get_cart():
    r = requests.get(f"{BASE}/api/user/cart",
        headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] > 0, "cart empty"

test("获取购物车", test_get_cart)

# 5. 文案生成
def test_copy():
    r = requests.post(f"{BASE}/api/copy/generate",
        json={"product_name":"测试椅子","style":"高端","audience":"白领","selling_points":["护腰","透气"]})
    assert r.status_code == 200, f"status={r.status_code}, body={r.text}"
    data = r.json()
    assert "title" in data

test("文案生成(高端风格)", test_copy)

# 6. 评论分析
def test_reviews():
    r = requests.post(f"{BASE}/api/reviews/analyze",
        json={"product_name":"测试","reviews":["质量很好，推荐","太差了，退货了","还不错吧","物流很快"]})
    assert r.status_code == 200
    data = r.json()
    assert "sentiment" in data
    assert "sentiment_detail" in data

test("评论情感分析", test_reviews)

# 7. 跨商品推荐
def test_cross():
    r = requests.post(f"{BASE}/api/guide/cross-recommend",
        json={"product_name":"办公椅","user_preferences":["性价比"]})
    assert r.status_code == 200, f"status={r.status_code}, body={r.text}"
    data = r.json()
    assert len(data["recommendations"]) > 0

test("跨商品推荐", test_cross)

# 8. 导购问答
def test_qa():
    r = requests.post(f"{BASE}/api/guide/qa",
        json={"question":"这款椅子适合多高的人坐？","product_specs":"160-180cm","category":"办公家具"})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data

test("导购问答", test_qa)

# 9. 直播脚本
def test_script():
    r = requests.post(f"{BASE}/api/scripts/live",
        json={"product_name":"测试产品","duration_minutes":10,"tone":"热情自然"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["segments"]) > 0
    assert len(data["explanation_flow"]) > 0

test("直播脚本生成", test_script)

# 10. 添加地址
def test_address():
    r = requests.post(f"{BASE}/api/user/addresses",
        json={"name":"测试","phone":"13800138000","province":"北京市","city":"北京市","district":"海淀区","detail":"中关村大街1号"},
        headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code in (200, 201), f"status={r.status_code}, body={r.text}"

test("添加收货地址", test_address)

# 11. RAG 问答
def test_rag():
    r = requests.post(f"{BASE}/api/user/qa/ask",
        json={"question":"这个产品的尺寸是多少？"},
        headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200, f"status={r.status_code}, body={r.text}"
    data = r.json()
    assert "answer" in data

test("RAG智能问答", test_rag)

# 12. 商家登录+商品管理
merchant_token = None
def test_merchant():
    global merchant_token
    r = requests.post(f"{BASE}/api/auth/login", json={"username":"merchant","password":"merchant123","role":"merchant"})
    assert r.status_code == 200
    merchant_token = r.json()["token"]

test("商家登录", test_merchant)

def test_merchant_products():
    r = requests.get(f"{BASE}/api/merchant/products?page=1",
        headers={"Authorization": f"Bearer {merchant_token}"})
    assert r.status_code == 200
    assert r.json()["total"] > 0

test("商家商品列表", test_merchant_products)

def test_knowledge():
    r = requests.get(f"{BASE}/api/merchant/knowledge",
        headers={"Authorization": f"Bearer {merchant_token}"})
    assert r.status_code == 200

test("知识库列表", test_knowledge)

def test_qa_stats():
    r = requests.get(f"{BASE}/api/merchant/qa/stats",
        headers={"Authorization": f"Bearer {merchant_token}"})
    assert r.status_code == 200

test("问答统计", test_qa_stats)

# 13. 创建订单
def test_create_order():
    r = requests.post(f"{BASE}/api/user/orders",
        json={"address_id": 1, "pay_method": "wechat"},
        headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code in (200, 201, 400), f"status={r.status_code}, body={r.text}"

test("创建订单", test_create_order)

# 14. 商品详情
def test_product_detail():
    r = requests.get(f"{BASE}/api/products/1")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data

test("商品详情", test_product_detail)

# 15. 导购推荐
def test_recommend():
    r = requests.post(f"{BASE}/api/guide/recommend",
        json={"user_need":"预算300元以内送朋友","budget":"300","products":["保温杯","T恤"]})
    assert r.status_code == 200
    data = r.json()
    assert "recommended_product" in data

test("导购推荐", test_recommend)

print(f"\n{'='*40}")
print(f"RESULT: {passed} passed, {failed} failed")
print(f"{'='*40}")
