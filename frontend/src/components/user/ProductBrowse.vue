<script setup lang="ts">
import { ref, computed, onMounted, inject, watch, type Ref } from 'vue'
import CheckoutModal, { type CheckoutItem } from './CheckoutModal.vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// ---------- 类型定义 ----------
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

interface ProductReview {
  id: number
  user_name: string
  rating: number
  content: string
  created_at: string
  image_urls?: string[]
  videos?: string[]
}

interface ProductDetail extends Product {
  specs?: string | Record<string, string> | null
  description?: string | null
  stock?: number | null
  reviews?: ProductReview[]
  image_urls?: string[]
  original_price?: number | null
}

// ---------- 导航（由 UserLayout provide） ----------
const navigate = inject<(page: string) => void>('navigate', () => {})
const navigateToCustomerService = inject<(productId?: number) => void>('navigateToCustomerService', () => {})
const targetProductId = inject<Ref<number | null>>('targetProductId', ref(null))

// ---------- 状态 ----------
const loading = ref(false)
const error = ref<string | null>(null)
const products = ref<Product[]>([])
const categories = ref<string[]>([])
const categoryCounts = ref<Record<string, number>>({})
const total = ref(0)
const totalPages = ref(1)
const currentPage = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const selectedCategory = ref('')
const sortBy = ref<'default' | 'price_asc' | 'price_desc' | 'rating'>('default')

// 详情弹窗
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailProduct = ref<ProductDetail | null>(null)
const detailQuantity = ref(1)
const isFavorited = ref(false)
const activeImageUrl = ref<string>('')

// 立即购买结算弹窗
const checkoutVisible = ref(false)
const checkoutItems = ref<CheckoutItem[]>([])


// 提示
const toast = ref<{ visible: boolean; message: string; type: 'success' | 'error' }>({
  visible: false,
  message: '',
  type: 'success',
})
let toastTimer: ReturnType<typeof setTimeout> | null = null

function showToast(message: string, type: 'success' | 'error' = 'success') {
  toast.value = { visible: true, message, type }
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toast.value.visible = false
  }, 2500)
}

// ---------- 请求头 ----------
function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

// ---------- 商品详情图库 ----------
const galleryImages = computed(() => {
  if (!detailProduct.value) return []
  const urls: string[] = []
  if (detailProduct.value.image_url) urls.push(detailProduct.value.image_url)
  if (detailProduct.value.image_urls?.length) {
    detailProduct.value.image_urls.forEach((url) => {
      if (url && !urls.includes(url)) urls.push(url)
    })
  }
  return urls
})

// ---------- 排序后的商品列表 ----------
const sortedProducts = computed(() => {
  const list = [...products.value]
  if (sortBy.value === 'price_asc') {
    list.sort((a, b) => (a.price ?? 0) - (b.price ?? 0))
  } else if (sortBy.value === 'price_desc') {
    list.sort((a, b) => (b.price ?? 0) - (a.price ?? 0))
  } else if (sortBy.value === 'rating') {
    list.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0))
  }
  return list
})

// ---------- 分页数字 ----------
const pageNumbers = computed(() => {
  const pages: (number | string)[] = []
  const tp = totalPages.value
  const cp = currentPage.value
  
  if (tp <= 7) {
    // 总页数≤7，全部显示
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    // 总页数>7，智能显示
    pages.push(1)
    if (cp > 3) pages.push('...')
    
    const start = Math.max(2, cp - 1)
    const end = Math.min(tp - 1, cp + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    
    if (cp < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
})

// ---------- 加载商品列表 ----------
async function loadProducts() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    if (selectedCategory.value) params.set('category', selectedCategory.value)
    if (keyword.value) params.set('keyword', keyword.value)
    params.set('page', currentPage.value.toString())
    params.set('page_size', pageSize.value.toString())

    const response = await fetch(`${API_BASE}/api/products?${params.toString()}`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    products.value = data.products || []
    categories.value = data.categories || []
    categoryCounts.value = data.category_counts || {}
    total.value = data.total || 0
    totalPages.value = data.total_pages || 1
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载商品失败'
  } finally {
    loading.value = false
  }
}

// ---------- 搜索 / 筛选 / 排序 ----------
function searchProducts() {
  currentPage.value = 1
  loadProducts()
}

function selectCategory(cat: string) {
  selectedCategory.value = cat
  currentPage.value = 1
  loadProducts()
}

function changeSort() {
  // 客户端排序，无需重新请求
}

function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadProducts()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// ---------- 商品详情 ----------
async function openDetail(product: Product) {
  detailVisible.value = true
  detailLoading.value = true
  detailProduct.value = null
  detailQuantity.value = 1
  isFavorited.value = false
  activeImageUrl.value = product.image_url || ''

  // 记录浏览历史
  recordHistory(product.id)

  try {
    const response = await fetch(`${API_BASE}/api/products/${product.id}`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    detailProduct.value = data.product || data
    isFavorited.value = data.is_favorited || false
    const imgs = galleryImages.value
    activeImageUrl.value = imgs[0] || ''
  } catch {
    // 降级：使用列表中的基本信息
    detailProduct.value = { ...product, reviews: [] }
    activeImageUrl.value = product.image_url || ''
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detailVisible.value = false
  detailProduct.value = null
}

// 通过商品ID直接打开详情（从AI聊天跳转）
async function openDetailById(productId: number) {
  detailVisible.value = true
  detailLoading.value = true
  detailProduct.value = null
  detailQuantity.value = 1
  isFavorited.value = false
  activeImageUrl.value = ''

  recordHistory(productId)

  try {
    const response = await fetch(`${API_BASE}/api/products/${productId}`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    detailProduct.value = data.product || data
    isFavorited.value = data.is_favorited || false
    const imgs = galleryImages.value
    activeImageUrl.value = imgs[0] || ''
  } catch {
    detailLoading.value = false
  } finally {
    detailLoading.value = false
  }
}

// 监听外部跳转商品详情（收藏 / 浏览记录 / AI 聊天）
watch(
  targetProductId,
  (newId) => {
    if (newId) {
      openDetailById(newId)
      // 消费后重置，避免重复触发
      targetProductId.value = null
    }
  },
  { immediate: true },
)

// ---------- 加入购物车 ----------
async function addToCart(productId: number, quantity: number = 1) {
  try {
    const response = await fetch(`${API_BASE}/api/user/cart`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ product_id: productId, quantity }),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('已加入购物车')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '加入购物车失败', 'error')
  }
}

function handleAddToCartFromCard(product: Product, event: Event) {
  event.stopPropagation()
  addToCart(product.id, 1)
}

function handleAddToCartFromDetail() {
  if (!detailProduct.value) return
  addToCart(detailProduct.value.id, detailQuantity.value)
}

// ---------- 立即购买 ----------
function handleBuyNow() {
  if (!detailProduct.value) return
  const product = detailProduct.value
  checkoutItems.value = [
    {
      product_id: product.id,
      product_name: product.name,
      product_image: product.image_url || null,
      product_price: product.price,
      product_category: product.category || null,
      quantity: detailQuantity.value,
    },
  ]
  checkoutVisible.value = true
}

function closeCheckout() {
  checkoutVisible.value = false
}

function onCheckoutSuccess() {
  checkoutVisible.value = false
  closeDetail()
  showToast('下单成功！')
  // 跳转个人中心，用户可在「我的订单」中查看
  navigate('profile')
}

// ---------- 询问客服 ----------
function handleAskCustomerService() {
  if (!detailProduct.value) return
  const productId = detailProduct.value.id
  closeDetail()
  navigateToCustomerService(productId)
}

// ---------- 收藏 / 取消收藏 ----------
async function toggleFavorite() {
  if (!detailProduct.value) return
  const productId = detailProduct.value.id
  try {
    const response = await fetch(`${API_BASE}/api/user/favorites/${productId}`, {
      method: 'POST',
      headers: authHeaders(),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    isFavorited.value = !isFavorited.value
    showToast(isFavorited.value ? '已收藏' : '已取消收藏')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '收藏操作失败', 'error')
  }
}

// ---------- 记录浏览历史 ----------
async function recordHistory(productId: number) {
  try {
    await fetch(`${API_BASE}/api/user/history/${productId}`, {
      method: 'POST',
      headers: authHeaders(),
    })
  } catch {
    // 静默失败
  }
}

// ---------- 数量增减 ----------
function increaseQty() {
  detailQuantity.value++
}

function decreaseQty() {
  if (detailQuantity.value > 1) detailQuantity.value--
}

// ---------- 格式化 ----------
function formatPrice(price: number | null | undefined): string {
  if (price == null) return '--'
  return price.toFixed(2)
}

function formatSpecs(specs: ProductDetail['specs']): Array<[string, string]> {
  if (!specs) return []
  if (typeof specs === 'string') {
    try {
      const parsed = JSON.parse(specs)
      if (typeof parsed === 'object') return Object.entries(parsed)
    } catch {
      return [['规格', specs]]
    }
  }
  if (typeof specs === 'object') return Object.entries(specs)
  return []
}

onMounted(() => {
  loadProducts()
  // 安全兜底：从个人中心等页面跳转过来时，如果 targetProductId 仍存在则直接打开详情
  if (targetProductId.value) {
    const pid = targetProductId.value
    targetProductId.value = null
    openDetailById(pid)
  }
})
</script>

<template>
  <div class="product-browse">
    <!-- 提示 Toast -->
    <transition name="toast">
      <div v-if="toast.visible" :class="['pb-toast', `pb-toast--${toast.type}`]">
        {{ toast.message }}
      </div>
    </transition>

    <!-- 工具栏：搜索 + 类目 + 排序 -->
    <div class="pb-toolbar">
      <div class="pb-search">
        <input
          v-model="keyword"
          type="text"
          placeholder="搜索商品名称、品牌..."
          class="pb-search__input"
          @keyup.enter="searchProducts"
        />
        <button class="pb-search__btn" @click="searchProducts">搜索</button>
      </div>

      <div class="pb-sort">
        <label>排序：</label>
        <select v-model="sortBy" class="pb-sort__select" @change="changeSort">
          <option value="default">默认</option>
          <option value="price_asc">价格从低到高</option>
          <option value="price_desc">价格从高到低</option>
          <option value="rating">评分优先</option>
        </select>
      </div>
    </div>

    <!-- 类目筛选 -->
    <div class="pb-categories">
      <button
        :class="['pb-cat', { active: selectedCategory === '' }]"
        @click="selectCategory('')"
      >
        全部
        <span v-if="total" class="pb-cat__count">{{ total }}</span>
      </button>
      <button
        v-for="cat in categories"
        :key="cat"
        :class="['pb-cat', { active: selectedCategory === cat }]"
        @click="selectCategory(cat)"
      >
        {{ cat }}
        <span v-if="categoryCounts[cat]" class="pb-cat__count">{{ categoryCounts[cat] }}</span>
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="pb-error">{{ error }}</div>

    <!-- 加载中 -->
    <div v-if="loading" class="pb-loading">
      <div class="pb-loading__spinner"></div>
      <p>正在加载商品...</p>
    </div>

    <!-- 商品网格 -->
    <div v-else-if="sortedProducts.length > 0" class="pb-grid">
      <div
        v-for="product in sortedProducts"
        :key="product.id"
        class="pb-card"
        @click="openDetail(product)"
      >
        <div class="pb-card__image">
          <img
            v-if="product.image_url"
            :src="product.image_url"
            :alt="product.name"
            @error="(e: any) => { e.target.style.display = 'none'; e.target.nextElementSibling.style.display = 'flex' }"
          />
          <div v-if="!product.image_url" class="pb-card__noimg">暂无图片</div>
          <div v-else class="pb-card__noimg" style="display: none">暂无图片</div>
        </div>
        <div class="pb-card__body">
          <h3 class="pb-card__name" :title="product.name">{{ product.name }}</h3>
          <div class="pb-card__meta">
            <span class="pb-card__price">¥{{ formatPrice(product.price) }}</span>
            <span v-if="product.rating" class="pb-card__rating">
              <span class="pb-card__stars">{{ '★'.repeat(Math.round(product.rating)) }}</span>
              {{ product.rating }}
            </span>
          </div>
          <div class="pb-card__tags">
            <span v-if="product.category" class="pb-card__tag">{{ product.category }}</span>
            <span v-if="product.brand" class="pb-card__tag pb-card__tag--brand">{{ product.brand }}</span>
            <span v-if="product.sales_count" class="pb-card__sales">销量 {{ product.sales_count }}</span>
          </div>
          <button
            class="pb-card__cart-btn"
            @click="handleAddToCartFromCard(product, $event)"
          >
            加入购物车
          </button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="pb-empty">
      <div class="pb-empty__icon">品</div>
      <p>暂无符合条件的商品</p>
      <button class="pb-empty__btn" @click="keyword = ''; selectedCategory = ''; searchProducts()">清除筛选</button>
    </div>

    <!-- 分页 -->
    <div v-if="!loading && totalPages > 1" class="pb-pagination">
      <button
        class="pb-page-btn"
        :disabled="currentPage === 1"
        @click="goToPage(currentPage - 1)"
      >
        上一页
      </button>
      <template v-for="(page, idx) in pageNumbers" :key="idx">
        <span v-if="page === '...'" class="pb-page-ellipsis">...</span>
        <button
          v-else
          :class="['pb-page-btn', { active: page === currentPage }]"
          @click="goToPage(page as number)"
        >
          {{ page }}
        </button>
      </template>
      <button
        class="pb-page-btn"
        :disabled="currentPage === totalPages"
        @click="goToPage(currentPage + 1)"
      >
        下一页
      </button>
      <span class="pb-page-info">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 件</span>
    </div>

    <!-- 商品详情弹窗 -->
    <transition name="modal">
      <div v-if="detailVisible" class="pb-modal-overlay" @click.self="closeDetail">
        <div class="pb-modal">
          <button class="pb-modal__close" @click="closeDetail">×</button>

          <!-- 加载中 -->
          <div v-if="detailLoading" class="pb-modal__loading">
            <div class="pb-loading__spinner"></div>
            <p>加载商品详情...</p>
          </div>

          <!-- 详情内容 -->
          <div v-else-if="detailProduct" class="pb-modal__content">
            <!-- 头部标题区 -->
            <div class="pb-detail__header">
              <div class="pb-detail__badges">
                <span v-if="detailProduct.category" class="pb-detail__badge pb-detail__badge--cat">{{ detailProduct.category }}</span>
                <span v-if="detailProduct.brand" class="pb-detail__badge pb-detail__badge--brand">{{ detailProduct.brand }}</span>
                <span v-if="detailProduct.platform && detailProduct.platform !== 'manual'" class="pb-detail__badge pb-detail__badge--platform">{{ detailProduct.platform }}</span>
              </div>
              <h2 class="pb-detail__name">{{ detailProduct.name }}</h2>
            </div>

            <div class="pb-detail__body">
              <!-- 左侧：图库 -->
              <div class="pb-detail__gallery">
                <div class="pb-detail__main-image">
                  <img
                    v-if="activeImageUrl"
                    :src="activeImageUrl"
                    :alt="detailProduct.name"
                  />
                  <div v-else class="pb-detail__noimg">暂无图片</div>
                </div>
                <div v-if="galleryImages.length > 1" class="pb-detail__thumbs">
                  <button
                    v-for="(url, idx) in galleryImages"
                    :key="idx"
                    :class="['pb-detail__thumb', { active: activeImageUrl === url }]"
                    @click="activeImageUrl = url"
                  >
                    <img :src="url" />
                  </button>
                </div>
              </div>

              <!-- 右侧：信息 -->
              <div class="pb-detail__info">
                <div class="pb-detail__price-row">
                  <span class="pb-detail__price">¥{{ formatPrice(detailProduct.price) }}</span>
                  <span v-if="detailProduct.original_price" class="pb-detail__original-price">
                    ¥{{ formatPrice(detailProduct.original_price) }}
                  </span>
                </div>

                <div class="pb-detail__meta-row">
                  <div v-if="detailProduct.rating" class="pb-detail__rating">
                    <span class="pb-card__stars">{{ '★'.repeat(Math.round(detailProduct.rating)) }}</span>
                    <span>{{ detailProduct.rating }} 分</span>
                  </div>
                  <span v-if="detailProduct.review_count" class="pb-detail__review-count">
                    {{ detailProduct.review_count }} 条评论
                  </span>
                  <span v-if="detailProduct.sales_count" class="pb-detail__sales">
                    销量 {{ detailProduct.sales_count }}
                  </span>
                </div>

                <!-- 规格 -->
                <div v-if="formatSpecs(detailProduct.specs).length > 0" class="pb-detail__specs">
                  <div class="pb-detail__section-title">规格参数</div>
                  <div class="pb-detail__spec-list">
                    <div
                      v-for="[key, val] in formatSpecs(detailProduct.specs)"
                      :key="key"
                      class="pb-detail__spec"
                    >
                      <span class="pb-detail__spec-key">{{ key }}</span>
                      <span class="pb-detail__spec-val">{{ val }}</span>
                    </div>
                  </div>
                </div>

                <!-- 卖点 -->
                <div v-if="detailProduct.selling_points" class="pb-detail__points">
                  <div class="pb-detail__section-title">商品卖点</div>
                  <p class="pb-detail__points-text">{{ detailProduct.selling_points }}</p>
                </div>

                <!-- 数量选择 -->
                <div class="pb-detail__qty">
                  <span class="pb-detail__qty-label">数量</span>
                  <div class="pb-detail__qty-ctrl">
                    <button @click="decreaseQty">−</button>
                    <span>{{ detailQuantity }}</span>
                    <button @click="increaseQty">+</button>
                  </div>
                </div>

                <!-- 操作按钮 -->
                <div class="pb-detail__actions">
                  <button class="pb-detail__btn pb-detail__btn--cart" @click="handleAddToCartFromDetail">
                    加入购物车
                  </button>
                  <button class="pb-detail__btn pb-detail__btn--buy" @click="handleBuyNow">
                    立即购买
                  </button>
                  <button
                    :class="['pb-detail__btn', 'pb-detail__btn--fav', { active: isFavorited }]"
                    @click="toggleFavorite"
                  >
                    {{ isFavorited ? '已收藏' : '收藏' }}
                  </button>
                </div>

                <!-- 询问客服 -->
                <div class="pb-detail__cs">
                  <div class="pb-detail__cs-title">
                    <span>💬</span>
                    <span>有疑问？咨询客服</span>
                  </div>
                  <p class="pb-detail__cs-desc">想了解商品细节、售后政策或搭配建议，可以一键发送当前商品给客服。</p>
                  <button class="pb-detail__btn pb-detail__btn--cs" @click="handleAskCustomerService">
                    询问客服
                  </button>
                </div>
              </div>
            </div>

            <!-- 评论列表 -->
            <div class="pb-detail__reviews">
              <div class="pb-detail__section-title">
                用户评论
                <span v-if="detailProduct.reviews?.length" class="pb-detail__reviews-count">共 {{ detailProduct.reviews.length }} 条</span>
              </div>
              <div v-if="detailProduct.reviews && detailProduct.reviews.length > 0" class="pb-review-list">
                <div
                  v-for="review in detailProduct.reviews"
                  :key="review.id"
                  class="pb-review"
                >
                  <div class="pb-review__head">
                    <div class="pb-review__avatar">{{ review.user_name?.charAt(0) || '用' }}</div>
                    <div class="pb-review__meta">
                      <span class="pb-review__user">{{ review.user_name }}</span>
                      <span class="pb-review__rating">
                        {{ '★'.repeat(Math.round(review.rating)) }}
                      </span>
                    </div>
                    <span class="pb-review__date">{{ review.created_at }}</span>
                  </div>
                  <p class="pb-review__content">{{ review.content }}</p>
                  <!-- 评论图片/视频 -->
                  <div v-if="(review.image_urls?.length || review.videos?.length)" class="pb-review__media">
                    <div
                      v-for="(url, idx) in review.image_urls || []"
                      :key="`img-${idx}`"
                      class="pb-review__media-item"
                    >
                      <img :src="url" />
                    </div>
                    <div
                      v-for="(url, idx) in review.videos || []"
                      :key="`video-${idx}`"
                      class="pb-review__media-item pb-review__media-item--video"
                    >
                      <video :src="url" controls></video>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="pb-review-empty">暂无评论</div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 立即购买结算弹窗 -->
    <CheckoutModal
      :visible="checkoutVisible"
      :items="checkoutItems"
      mode="buy-now"
      @close="closeCheckout"
      @success="onCheckoutSuccess"
    />
  </div>
</template>

<style scoped>
.product-browse {
  position: relative;
}

/* Toast */
.pb-toast {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
  padding: 12px 28px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.pb-toast--success {
  background: var(--green);
}

.pb-toast--error {
  background: var(--brand);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}

/* 工具栏 */
.pb-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pb-search {
  display: flex;
  gap: 8px;
  flex: 1;
  max-width: 520px;
}

.pb-search__input {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 14px;
  font-family: inherit;
  background: var(--panel);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.pb-search__input:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.12);
}

.pb-search__btn {
  padding: 10px 24px;
  border: none;
  border-radius: 999px;
  color: #fffaf0;
  background: var(--brand);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.pb-search__btn:hover {
  background: var(--brand-dark);
}

.pb-sort {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--muted);
}

.pb-sort__select {
  padding: 8px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
}

.pb-sort__select:focus {
  outline: none;
  border-color: var(--brand);
}

/* 类目筛选 */
.pb-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;
}

.pb-cat {
  padding: 6px 18px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--panel);
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.pb-cat:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.pb-cat.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.pb-cat__count {
  display: inline-block;
  margin-left: 4px;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 11px;
  background: rgba(0, 0, 0, 0.08);
}

.pb-cat.active .pb-cat__count {
  background: rgba(255, 255, 255, 0.25);
}

/* 加载 */
.pb-loading {
  text-align: center;
  padding: 80px 20px;
  color: var(--muted);
}

.pb-loading__spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: pb-spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes pb-spin {
  to { transform: rotate(360deg); }
}

/* 错误 */
.pb-error {
  background: #fff0f0;
  color: #c33;
  padding: 14px 18px;
  border-radius: 12px;
  margin-bottom: 20px;
  font-size: 14px;
}

/* 商品网格 */
.pb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 18px;
}

.pb-card {
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  background: var(--panel);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.pb-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.1);
}

.pb-card__image {
  height: 200px;
  background: #f8f4ef;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.pb-card__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.pb-card:hover .pb-card__image img {
  transform: scale(1.06);
}

.pb-card__noimg {
  color: var(--muted);
  font-size: 14px;
}

.pb-card__noimg--lg {
  font-size: 18px;
}

.pb-card__body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.pb-card__name {
  font-size: 14px;
  margin: 0 0 10px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 39px;
}

.pb-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.pb-card__price {
  color: var(--brand);
  font-size: 20px;
  font-weight: 700;
}

.pb-card__rating {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
}

.pb-card__stars {
  color: var(--yellow);
  letter-spacing: 1px;
}

.pb-card__tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.pb-card__tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand-dark);
}

.pb-card__tag--brand {
  background: rgba(82, 196, 26, 0.1);
  color: var(--green);
}

.pb-card__sales {
  font-size: 11px;
  color: var(--muted);
  margin-left: auto;
}

.pb-card__cart-btn {
  margin-top: auto;
  padding: 8px 0;
  border: none;
  border-radius: 8px;
  color: #fff;
  background: var(--brand);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.pb-card__cart-btn:hover {
  background: var(--brand-dark);
}

/* 空状态 */
.pb-empty {
  text-align: center;
  padding: 80px 20px;
  color: var(--muted);
}

.pb-empty__icon {
  display: inline-grid;
  width: 72px;
  height: 72px;
  place-items: center;
  border-radius: 20px;
  margin-bottom: 20px;
  font-size: 28px;
  font-weight: 800;
  color: #fffaf0;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
}

.pb-empty__btn {
  margin-top: 16px;
  padding: 8px 20px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  background: transparent;
  color: var(--brand);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.pb-empty__btn:hover {
  background: var(--brand);
  color: #fff;
}

/* 分页 */
.pb-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-top: 36px;
  flex-wrap: wrap;
}

.pb-page-btn {
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.pb-page-btn:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand);
}

.pb-page-btn.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.pb-page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pb-page-ellipsis {
  padding: 7px 4px;
  color: var(--muted);
  font-size: 13px;
}

.pb-page-info {
  margin-left: 12px;
  font-size: 13px;
  color: var(--muted);
}

/* 详情弹窗 */
.pb-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 150;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.pb-modal {
  width: min(900px, 100%);
  max-height: 88vh;
  overflow-y: auto;
  background: var(--panel);
  border-radius: 18px;
  position: relative;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.3);
}

.pb-modal__close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 10;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.08);
  color: var(--ink);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.2s;
}

.pb-modal__close:hover {
  background: rgba(0, 0, 0, 0.18);
}

.pb-modal__loading {
  text-align: center;
  padding: 100px 20px;
  color: var(--muted);
}

.pb-modal__content {
  padding: 28px;
}

.pb-detail__header {
  margin-bottom: 24px;
}

.pb-detail__badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.pb-detail__badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.pb-detail__badge--cat {
  color: var(--brand-dark);
  background: rgba(155, 135, 245, 0.1);
}

.pb-detail__badge--brand {
  color: var(--green);
  background: rgba(52, 211, 153, 0.1);
}

.pb-detail__badge--platform {
  color: var(--muted);
  background: rgba(107, 114, 128, 0.1);
}

.pb-detail__name {
  font-size: 26px;
  line-height: 1.3;
  margin: 0;
  color: var(--ink);
  font-weight: 800;
}

.pb-detail__body {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
  gap: 32px;
  margin-bottom: 32px;
}

/* 图库 */
.pb-detail__gallery {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.pb-detail__main-image {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 20px;
  overflow: hidden;
  background: linear-gradient(135deg, #f8f4ef, #f0f4ff);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12px 40px rgba(155, 135, 245, 0.1);
}

.pb-detail__main-image img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  transition: transform 0.4s ease;
}

.pb-detail__main-image:hover img {
  transform: scale(1.03);
}

.pb-detail__noimg {
  color: var(--muted);
  font-size: 16px;
}

.pb-detail__thumbs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.pb-detail__thumb {
  width: 64px;
  height: 64px;
  border: 2px solid transparent;
  border-radius: 12px;
  overflow: hidden;
  background: #f8f4ef;
  cursor: pointer;
  padding: 0;
  transition: border-color 0.2s, transform 0.2s;
}

.pb-detail__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pb-detail__thumb:hover {
  transform: translateY(-2px);
}

.pb-detail__thumb.active {
  border-color: var(--brand);
}

/* 信息区 */
.pb-detail__info {
  display: flex;
  flex-direction: column;
}

.pb-detail__price-row {
  display: flex;
  align-items: baseline;
  gap: 14px;
  margin-bottom: 14px;
}

.pb-detail__price {
  font-size: 36px;
  font-weight: 800;
  color: var(--brand);
}

.pb-detail__original-price {
  font-size: 16px;
  color: var(--muted);
  text-decoration: line-through;
}

.pb-detail__meta-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
  font-size: 13px;
  color: var(--muted);
}

.pb-detail__rating {
  display: flex;
  align-items: center;
  gap: 6px;
}

.pb-detail__rating .pb-card__stars {
  font-size: 15px;
}

.pb-detail__review-count {
  padding-left: 16px;
  border-left: 1px solid var(--line);
}

.pb-detail__sales {
  padding-left: 16px;
  border-left: 1px solid var(--line);
}

.pb-detail__section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid var(--brand);
}

.pb-detail__specs {
  margin-bottom: 20px;
}

.pb-detail__spec-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.pb-detail__spec {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(155, 135, 245, 0.06);
  border-radius: 10px;
  font-size: 13px;
}

.pb-detail__spec-key {
  color: var(--muted);
  flex-shrink: 0;
}

.pb-detail__spec-val {
  color: var(--ink);
  font-weight: 500;
}

.pb-detail__points {
  margin-bottom: 20px;
}

.pb-detail__points-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--muted);
  margin: 0;
  padding: 14px 16px;
  background: rgba(253, 230, 138, 0.12);
  border-radius: 12px;
}

.pb-detail__qty {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
}

.pb-detail__qty-label {
  font-size: 14px;
  color: var(--muted);
}

.pb-detail__qty-ctrl {
  display: flex;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
  background: var(--panel);
}

.pb-detail__qty-ctrl button {
  width: 38px;
  height: 38px;
  border: none;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
  color: var(--ink);
  transition: background 0.2s, color 0.2s;
}

.pb-detail__qty-ctrl button:hover {
  background: rgba(155, 135, 245, 0.1);
  color: var(--brand);
}

.pb-detail__qty-ctrl span {
  width: 52px;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
}

.pb-detail__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}

.pb-detail__btn {
  padding: 12px 28px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.pb-detail__btn--cart {
  color: var(--brand);
  background: transparent;
}

.pb-detail__btn--cart:hover {
  background: rgba(155, 135, 245, 0.1);
}

.pb-detail__btn--buy {
  color: #fff;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  border-color: transparent;
  box-shadow: 0 8px 24px rgba(155, 135, 245, 0.25);
}

.pb-detail__btn--buy:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(155, 135, 245, 0.35);
}

.pb-detail__btn--fav {
  color: var(--muted);
  background: transparent;
  border-color: var(--line);
}

.pb-detail__btn--fav:hover {
  border-color: var(--yellow);
  color: var(--yellow);
}

.pb-detail__btn--fav.active {
  border-color: var(--yellow);
  color: var(--yellow);
  background: rgba(250, 173, 20, 0.08);
}

.pb-detail__cs {
  margin-top: auto;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(155, 135, 245, 0.06), rgba(147, 197, 253, 0.08));
}

.pb-detail__cs-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 6px;
}

.pb-detail__cs-desc {
  font-size: 13px;
  color: var(--muted);
  margin: 0 0 12px;
  line-height: 1.6;
}

.pb-detail__btn--cs {
  color: #fff;
  background: linear-gradient(135deg, var(--accent-blue), #60a5fa);
  border-color: transparent;
  padding: 10px 24px;
  font-size: 14px;
}

.pb-detail__btn--cs:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(147, 197, 253, 0.3);
}

/* 评论 */
.pb-detail__reviews {
  border-top: 1px solid var(--line);
  padding-top: 28px;
}

.pb-detail__reviews-count {
  font-size: 13px;
  color: var(--muted);
  font-weight: 400;
  margin-left: 10px;
  padding-left: 10px;
  border-left: 1px solid var(--line);
}

.pb-review-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.pb-review {
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(155, 135, 245, 0.03);
}

.pb-review__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.pb-review__avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  color: #fff;
  display: inline-grid;
  place-items: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.pb-review__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pb-review__user {
  font-weight: 600;
  font-size: 14px;
  color: var(--ink);
}

.pb-review__rating {
  color: var(--yellow);
  font-size: 13px;
  letter-spacing: 1px;
}

.pb-review__date {
  margin-left: auto;
  font-size: 12px;
  color: var(--muted);
}

.pb-review__content {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--ink);
}

.pb-review__media {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.pb-review__media-item {
  width: 88px;
  height: 88px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--line);
  background: #f8f4ef;
}

.pb-review__media-item--video {
  width: 150px;
  height: 88px;
}

.pb-review__media-item img,
.pb-review__media-item video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pb-review-empty {
  text-align: center;
  padding: 30px;
  color: var(--muted);
  font-size: 14px;
}

/* 弹窗过渡 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s;
}

.modal-enter-active .pb-modal,
.modal-leave-active .pb-modal {
  transition: transform 0.25s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .pb-modal,
.modal-leave-to .pb-modal {
  transform: scale(0.95);
}

/* 响应式 */
@media (max-width: 768px) {
  .pb-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .pb-search {
    max-width: none;
  }

  .pb-detail__body {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .pb-detail__name {
    font-size: 20px;
  }

  .pb-detail__price {
    font-size: 28px;
  }

  .pb-detail__spec-list {
    grid-template-columns: 1fr;
  }

  .pb-detail__actions {
    flex-direction: column;
  }

  .pb-detail__btn {
    width: 100%;
  }
}
</style>
