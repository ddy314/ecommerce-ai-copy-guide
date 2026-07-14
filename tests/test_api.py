from backend.app import create_app


def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_health():
    response = client().get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_capabilities():
    response = client().get("/api/capabilities")

    assert response.status_code == 200
    assert response.get_json()["mode"] == "mock"


def test_generate_copy():
    response = client().post(
        "/api/copy/generate",
        json={
            "product_name": "云感护腰办公椅",
            "audience": "久坐办公人群",
            "tone": "专业可信",
            "selling_points": ["护腰支撑", "透气坐垫"],
        },
    )

    body = response.get_json()
    assert response.status_code == 200
    assert "云感护腰办公椅" in body["title"]
    assert body["selling_points"]


def test_review_analysis_validation():
    response = client().post("/api/reviews/analyze", json={"reviews": []})

    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_list_products():
    """测试商品列表查询（需要数据库，跳过）"""
    import pytest
    pytest.skip("需要 PostgreSQL 数据库，跳过单元测试")


def test_list_products_with_category():
    """测试按分类查询商品（需要数据库，跳过）"""
    import pytest
    pytest.skip("需要 PostgreSQL 数据库，跳过单元测试")


def test_list_products_with_keyword():
    """测试关键词搜索商品（需要数据库，跳过）"""
    import pytest
    pytest.skip("需要 PostgreSQL 数据库，跳过单元测试")


def test_get_product_not_found():
    """测试查询不存在的商品（需要数据库，跳过）"""
    import pytest
    pytest.skip("需要 PostgreSQL 数据库，跳过单元测试")


def test_get_product_reviews():
    """测试获取商品评论（需要数据库，跳过）"""
    import pytest
    pytest.skip("需要 PostgreSQL 数据库，跳过单元测试")
