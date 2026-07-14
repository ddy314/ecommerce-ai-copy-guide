<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'

interface Product {
  id: number
  platform: string
  product_id: string
  name: string
  category: string
  price: number | null
  brand: string | null
  selling_points: string | null
  image_url: string | null
  detail_url: string | null
  sales_count: number | null
  rating: number | null
  review_count: number
  created_at: string
}

interface Stats {
  total_products: number
  total_categories: number
  categories: string[]
  category_stats: Record<string, {
    count: number
    avg_price: number
    min_price: number
    max_price: number
  }>
}

const loading = ref(false)
const error = ref<string | null>(null)
const products = ref<Product[]>([])
const categories = ref<string[]>([])
const total = ref(0)
const totalPages = ref(1)
const currentPage = ref(1)
const pageSize = ref(20)
const selectedCategory = ref('')
const keyword = ref('')
const stats = ref<Stats | null>(null)
const showStats = ref(false)

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function loadProducts() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    if (selectedCategory.value) params.set('category', selectedCategory.value)
    if (keyword.value) params.set('keyword', keyword.value)
    params.set('page', currentPage.value.toString())
    params.set('page_size', pageSize.value.toString())

    const response = await fetch(`${apiBaseUrl}/api/products?${params.toString()}`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    products.value = data.products || []
    categories.value = data.categories || []
    total.value = data.total || 0
    totalPages.value = data.total_pages || 1
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const response = await fetch(`${apiBaseUrl}/api/stats`)
    if (response.ok) {
      stats.value = await response.json()
      showStats.value = true
    }
  } catch (e) {
    console.error('加载统计数据失败:', e)
  }
}

function selectCategory(cat: string) {
  selectedCategory.value = cat
  currentPage.value = 1
  loadProducts()
}

function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadProducts()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

function changePageSize(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadProducts()
}

function searchProducts() {
  currentPage.value = 1
  loadProducts()
}

const pageNumbers = computed(() => {
  const pages = []
  const maxVisible = 7
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2))
  let end = Math.min(totalPages.value, start + maxVisible - 1)
  
  if (end - start < maxVisible - 1) {
    start = Math.max(1, end - maxVisible + 1)
  }
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

onMounted(() => {
  loadProducts()
  loadStats()
})
</script>

<template>
  <div class="feature-page">
    <div class="page-header">
      <div class="header-content">
        <div>
          <h1>商品数据库</h1>
          <p>从京东爬取的真实商品数据，共 <strong>{{ total }}</strong> 个商品</p>
        </div>
        <button class="stats-btn" @click="showStats = !showStats">
          {{ showStats ? '隐藏统计' : '显示统计' }}
        </button>
      </div>
    </div>

    <!-- 统计面板 -->
    <div v-if="showStats && stats" class="stats-panel">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ stats.total_products }}</div>
          <div class="stat-label">商品总数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.total_categories }}</div>
          <div class="stat-label">分类数量</div>
        </div>
      </div>
      
      <div class="category-stats">
        <h3>分类详情</h3>
        <div class="category-grid">
          <div v-for="(catStat, catName) in stats.category_stats" :key="catName" class="category-card">
            <h4>{{ catName }}</h4>
            <div class="cat-stats">
              <div class="cat-stat">
                <span class="cat-stat-label">数量</span>
                <span class="cat-stat-value">{{ catStat.count }}</span>
              </div>
              <div class="cat-stat">
                <span class="cat-stat-label">均价</span>
                <span class="cat-stat-value">¥{{ catStat.avg_price.toFixed(0) }}</span>
              </div>
              <div class="cat-stat">
                <span class="cat-stat-label">价格区间</span>
                <span class="cat-stat-value">¥{{ catStat.min_price.toFixed(0) }} - ¥{{ catStat.max_price.toFixed(0) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="toolbar">
      <div class="search-bar">
        <input
          v-model="keyword"
          type="text"
          placeholder="搜索商品名称或分类..."
          class="search-input"
          @keyup.enter="searchProducts"
        />
        <button class="search-btn" @click="searchProducts">搜索</button>
      </div>
      
      <div class="category-tags">
        <button
          :class="['tag', { active: !selectedCategory }]"
          @click="selectCategory('')"
        >
          全部
        </button>
        <button
          v-for="cat in categories"
          :key="cat"
          :class="['tag', { active: selectedCategory === cat }]"
          @click="selectCategory(cat)"
        >
          {{ cat }}
        </button>
      </div>

      <div class="page-size-selector">
        <label>每页显示：</label>
        <select v-model.number="pageSize" @change="changePageSize(pageSize)">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>
    </div>

    <div v-if="error" class="error-message">{{ error }}</div>

    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else class="product-grid">
      <div v-for="product in products" :key="product.id" class="product-card">
        <div class="product-image">
          <img
            v-if="product.image_url"
            :src="product.image_url"
            :alt="product.name"
            @error="(e: any) => e.target.style.display = 'none'"
          />
          <div v-else class="no-image">暂无图片</div>
        </div>
        <div class="product-info">
          <h3 class="product-name" :title="product.name">{{ product.name }}</h3>
          <div class="product-meta">
            <span v-if="product.price" class="price">¥{{ product.price.toFixed(2) }}</span>
            <span v-if="product.brand" class="brand">{{ product.brand }}</span>
          </div>
          <div class="product-stats">
            <span v-if="product.review_count" class="stat">
              {{ product.review_count }} 条评论
            </span>
            <span v-if="product.rating" class="stat">
              评分 {{ product.rating }}
            </span>
            <span v-if="product.sales_count" class="stat">
              销量 {{ product.sales_count }}
            </span>
          </div>
          <div class="product-category">
            <span class="category-tag">{{ product.category }}</span>
            <span class="platform-tag">{{ product.platform.toUpperCase() }}</span>
          </div>
          <a
            v-if="product.detail_url"
            :href="product.detail_url"
            target="_blank"
            class="detail-link"
          >
            查看详情 →
          </a>
        </div>
      </div>
    </div>

    <!-- 分页控件 -->
    <div v-if="!loading && totalPages > 1" class="pagination">
      <button
        :disabled="currentPage === 1"
        @click="goToPage(currentPage - 1)"
        class="page-btn"
      >
        上一页
      </button>
      
      <button
        v-for="page in pageNumbers"
        :key="page"
        :class="['page-btn', { active: page === currentPage }]"
        @click="goToPage(page)"
      >
        {{ page }}
      </button>
      
      <button
        :disabled="currentPage === totalPages"
        @click="goToPage(currentPage + 1)"
        class="page-btn"
      >
        下一页
      </button>
      
      <span class="page-info">
        第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条
      </span>
    </div>

    <div v-if="!loading && products.length === 0 && !error" class="empty-state">
      <p>暂无商品数据，请先运行爬虫爬取商品数据</p>
      <code>python crawl_detail.py --init-db</code>
    </div>
  </div>
</template>

<style scoped>
.feature-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
}

.page-header {
  margin-bottom: 32px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}

.page-header h1 {
  font-size: 32px;
  margin: 0 0 8px 0;
}

.page-header p {
  color: var(--muted);
  margin: 0;
}

.stats-btn {
  padding: 10px 20px;
  background: var(--brand);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.stats-btn:hover {
  background: var(--brand-dark);
}

/* 统计面板 */
.stats-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 32px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-dark) 100%);
  color: white;
  padding: 24px;
  border-radius: 12px;
  text-align: center;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
}

.category-stats h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.category-card {
  background: rgba(217, 95, 45, 0.05);
  border: 1px solid rgba(217, 95, 45, 0.2);
  border-radius: 12px;
  padding: 16px;
}

.category-card h4 {
  margin: 0 0 12px 0;
  color: var(--brand-dark);
  font-size: 16px;
}

.cat-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cat-stat {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.cat-stat-label {
  color: var(--muted);
}

.cat-stat-value {
  font-weight: 600;
  color: var(--text);
}

/* 工具栏 */
.toolbar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.search-bar {
  display: flex;
  gap: 12px;
  max-width: 600px;
}

.search-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 15px;
  font-family: inherit;
  background: var(--panel);
}

.search-btn {
  padding: 12px 24px;
  background: var(--brand);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-size: 15px;
  transition: background 0.2s;
}

.search-btn:hover {
  background: var(--brand-dark);
}

.category-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  padding: 6px 16px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.tag:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.tag.active {
  background: var(--brand);
  color: white;
  border-color: var(--brand);
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--muted);
}

.page-size-selector select {
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  font-size: 14px;
  cursor: pointer;
}

/* 加载动画 */
.loading {
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 商品网格 */
.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.product-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
  background: var(--panel);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.product-image {
  height: 180px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-image {
  color: var(--muted);
  font-size: 14px;
}

.product-info {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.product-name {
  font-size: 15px;
  margin: 0 0 12px 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.price {
  color: #e4393c;
  font-size: 20px;
  font-weight: 700;
}

.brand {
  color: var(--muted);
  font-size: 13px;
}

.product-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.stat {
  font-size: 12px;
  color: var(--muted);
}

.product-category {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.category-tag,
.platform-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand-dark);
}

.platform-tag {
  background: rgba(31, 138, 91, 0.1);
  color: var(--green);
}

.detail-link {
  margin-top: auto;
  color: var(--brand);
  text-decoration: none;
  font-size: 13px;
  transition: color 0.2s;
}

.detail-link:hover {
  color: var(--brand-dark);
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 40px;
  flex-wrap: wrap;
}

.page-btn {
  padding: 8px 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--text);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.page-btn:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand);
}

.page-btn.active {
  background: var(--brand);
  color: white;
  border-color: var(--brand);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  margin-left: 16px;
  font-size: 14px;
  color: var(--muted);
}

/* 错误和空状态 */
.error-message {
  background: #fee;
  color: #c33;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}

.empty-state code {
  display: block;
  margin-top: 12px;
  padding: 8px 16px;
  background: #f5f5f5;
  border-radius: 8px;
  font-size: 14px;
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
  }
  
  .product-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }
  
  .category-grid {
    grid-template-columns: 1fr;
  }
  
  .pagination {
    gap: 4px;
  }
  
  .page-btn {
    padding: 6px 12px;
    font-size: 13px;
  }
}
</style>
