<script setup lang="ts">
import { ref, computed, onMounted, inject, watch, type Ref } from 'vue'

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
}

interface ProductDetail extends Product {
  specs?: string | Record<string, string> | null
  description?: string | null
  stock?: number | null
  reviews?: ProductReview[]
}

// ---------- 导航（由 UserLayout provide） ----------
const navigate = inject<(page: string) => void>('navigate', () => {})
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

// 立即购买 - 结算弹窗
const checkoutVisible = ref(false)
const checkoutLoading = ref(false)
const addresses = ref<any[]>([])
const selectedAddressId = ref<number | null>(null)
const payMethod = ref<'wechat' | 'alipay'>('wechat')
const remark = ref('')
const showAddressForm = ref(false)
const addressForm = ref({ recipient: '', phone: '', province: '', city: '', district: '', detail: '' })
const addressFormLoading = ref(false)

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
  } catch {
    // 降级：使用列表中的基本信息
    detailProduct.value = { ...product, reviews: [] }
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

  recordHistory(productId)

  try {
    const response = await fetch(`${API_BASE}/api/products/${productId}`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    detailProduct.value = data.product || data
    isFavorited.value = data.is_favorited || false
  } catch {
    detailLoading.value = false
  } finally {
    detailLoading.value = false
  }
}

// 监听 AI 聊天的商品跳转
watch(targetProductId, (newId) => {
  if (newId) {
    openDetailById(newId)
    // 消费后重置，避免重复触发
    targetProductId.value = null
  }
})

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
async function handleBuyNow() {
  if (!detailProduct.value) return
  // 添加到购物车（标记为选中）
  addToCart(detailProduct.value.id, detailQuantity.value)
  // 打开结算弹窗
  checkoutVisible.value = true
  await loadAddresses()
}

// ---------- 结算：加载地址 ----------
async function loadAddresses() {
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    addresses.value = data.addresses || data || []
    const defaultAddr = addresses.value.find((a: any) => a.is_default)
    if (defaultAddr) {
      selectedAddressId.value = defaultAddr.id
    } else if (addresses.value.length > 0) {
      selectedAddressId.value = addresses.value[0].id
    }
  } catch {
    showToast('加载地址失败', 'error')
  }
}

function formatAddress(addr: any): string {
  return `${addr.province}${addr.city}${addr.district}${addr.detail}`
}

// ---------- 结算：新增地址 ----------
function toggleAddressForm() {
  showAddressForm.value = !showAddressForm.value
  if (showAddressForm.value) {
    addressForm.value = { recipient: '', phone: '', province: '', city: '', district: '', detail: '' }
  }
}

async function saveAddress() {
  if (!addressForm.value.recipient || !addressForm.value.phone || !addressForm.value.detail) {
    showToast('请填写完整收货信息', 'error')
    return
  }
  addressFormLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(addressForm.value),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('地址添加成功')
    showAddressForm.value = false
    await loadAddresses()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '添加地址失败', 'error')
  } finally {
    addressFormLoading.value = false
  }
}

// ---------- 结算：确认下单 ----------
async function confirmDirectOrder() {
  if (!selectedAddressId.value) {
    showToast('请选择收货地址', 'error')
    return
  }
  checkoutLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/user/orders`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        address_id: selectedAddressId.value,
        pay_method: payMethod.value,
        remark: remark.value,
      }),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('下单成功！')
    checkoutVisible.value = false
    closeDetail()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '下单失败', 'error')
  } finally {
    checkoutLoading.value = false
  }
}

function closeCheckout() {
  checkoutVisible.value = false
  showAddressForm.value = false
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
        v-for="cat in categories"
        :key="cat"
        :class="['pb-cat', { active: selectedCategory === cat || (!selectedCategory && cat === categories[0]) }]"
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
            <div class="pb-modal__top">
              <!-- 大图 -->
              <div class="pb-modal__image">
                <img
                  v-if="detailProduct.image_url"
                  :src="detailProduct.image_url"
                  :alt="detailProduct.name"
                />
                <div v-else class="pb-card__noimg pb-card__noimg--lg">暂无图片</div>
              </div>

              <!-- 基本信息 -->
              <div class="pb-modal__info">
                <h2 class="pb-modal__name">{{ detailProduct.name }}</h2>
                <div class="pb-modal__price-row">
                  <span class="pb-modal__price">¥{{ formatPrice(detailProduct.price) }}</span>
                  <span v-if="detailProduct.brand" class="pb-modal__brand">{{ detailProduct.brand }}</span>
                </div>

                <!-- 评分 -->
                <div v-if="detailProduct.rating" class="pb-modal__rating">
                  <span class="pb-card__stars">{{ '★'.repeat(Math.round(detailProduct.rating)) }}</span>
                  <span>{{ detailProduct.rating }} 分</span>
                  <span v-if="detailProduct.review_count" class="pb-modal__review-count">
                    {{ detailProduct.review_count }} 条评论
                  </span>
                </div>

                <!-- 规格 -->
                <div v-if="formatSpecs(detailProduct.specs).length > 0" class="pb-modal__specs">
                  <div class="pb-modal__section-title">商品规格</div>
                  <div class="pb-modal__spec-list">
                    <div
                      v-for="[key, val] in formatSpecs(detailProduct.specs)"
                      :key="key"
                      class="pb-modal__spec"
                    >
                      <span class="pb-modal__spec-key">{{ key }}</span>
                      <span class="pb-modal__spec-val">{{ val }}</span>
                    </div>
                  </div>
                </div>

                <!-- 卖点 -->
                <div v-if="detailProduct.selling_points" class="pb-modal__points">
                  <div class="pb-modal__section-title">商品卖点</div>
                  <p class="pb-modal__points-text">{{ detailProduct.selling_points }}</p>
                </div>

                <!-- 数量选择 -->
                <div class="pb-modal__qty">
                  <span class="pb-modal__qty-label">数量</span>
                  <div class="pb-modal__qty-ctrl">
                    <button @click="decreaseQty">−</button>
                    <span>{{ detailQuantity }}</span>
                    <button @click="increaseQty">+</button>
                  </div>
                </div>

                <!-- 操作按钮 -->
                <div class="pb-modal__actions">
                  <button class="pb-modal__btn pb-modal__btn--cart" @click="handleAddToCartFromDetail">
                    加入购物车
                  </button>
                  <button class="pb-modal__btn pb-modal__btn--buy" @click="handleBuyNow">
                    立即购买
                  </button>
                  <button
                    :class="['pb-modal__btn', 'pb-modal__btn--fav', { active: isFavorited }]"
                    @click="toggleFavorite"
                  >
                    {{ isFavorited ? '已收藏' : '收藏' }}
                  </button>
                </div>
              </div>
            </div>

            <!-- 评论列表 -->
            <div class="pb-modal__reviews">
              <div class="pb-modal__section-title">用户评论</div>
              <div v-if="detailProduct.reviews && detailProduct.reviews.length > 0" class="pb-review-list">
                <div
                  v-for="review in detailProduct.reviews"
                  :key="review.id"
                  class="pb-review"
                >
                  <div class="pb-review__head">
                    <span class="pb-review__user">{{ review.user_name }}</span>
                    <span class="pb-review__rating">
                      {{ '★'.repeat(Math.round(review.rating)) }}
                    </span>
                    <span class="pb-review__date">{{ review.created_at }}</span>
                  </div>
                  <p class="pb-review__content">{{ review.content }}</p>
                </div>
              </div>
              <div v-else class="pb-review-empty">暂无评论</div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 立即购买 - 确认订单弹窗 -->
    <transition name="pb-fade">
      <div v-if="checkoutVisible" class="pb-checkout-overlay" @click.self="closeCheckout">
        <div class="pb-checkout-modal">
          <div class="pb-checkout-header">
            <h2>确认订单</h2>
            <button class="pb-checkout-close" @click="closeCheckout">×</button>
          </div>

          <!-- 收货地址 -->
          <div class="pb-checkout-section">
            <div class="pb-checkout-section__title">收货地址</div>
            <div v-if="addresses.length === 0 && !showAddressForm" class="pb-checkout-empty">
              暂无收货地址，
              <span class="pb-checkout-link" @click="toggleAddressForm">新增地址</span>
            </div>
            <div v-for="addr in addresses" :key="addr.id" :class="['pb-checkout-addr', { active: selectedAddressId === addr.id }]" @click="selectedAddressId = addr.id">
              <input type="radio" :checked="selectedAddressId === addr.id" readonly />
              <div class="pb-checkout-addr__info">
                <span class="pb-checkout-addr__name">{{ addr.recipient }} {{ addr.phone }}</span>
                <span v-if="addr.is_default" class="pb-checkout-addr__tag">默认</span>
                <span class="pb-checkout-addr__detail">{{ formatAddress(addr) }}</span>
              </div>
            </div>
            <button v-if="!showAddressForm && addresses.length > 0" class="pb-checkout-addaddr" @click="toggleAddressForm">+ 新增收货地址</button>

            <!-- 新增地址表单 -->
            <div v-if="showAddressForm" class="pb-checkout-addrform">
              <div class="pb-checkout-addrform__row">
                <input v-model="addressForm.recipient" placeholder="收货人姓名" />
                <input v-model="addressForm.phone" placeholder="手机号" />
              </div>
              <div class="pb-checkout-addrform__row">
                <input v-model="addressForm.province" placeholder="省" />
                <input v-model="addressForm.city" placeholder="市" />
                <input v-model="addressForm.district" placeholder="区/县" />
              </div>
              <input v-model="addressForm.detail" placeholder="详细地址" class="pb-checkout-addrform__full" />
              <div class="pb-checkout-addrform__btns">
                <button class="pb-checkout-btn--ghost" @click="toggleAddressForm">取消</button>
                <button class="pb-checkout-btn--primary" :disabled="addressFormLoading" @click="saveAddress">
                  {{ addressFormLoading ? '保存中...' : '保存地址' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 支付方式 -->
          <div class="pb-checkout-section">
            <div class="pb-checkout-section__title">支付方式</div>
            <div class="pb-checkout-pay">
              <label :class="['pb-checkout-pay__option', { active: payMethod === 'wechat' }]">
                <input type="radio" value="wechat" v-model="payMethod" />
                <span class="pb-checkout-pay__icon pb-checkout-pay__icon--wechat">微</span>
                <span>微信支付</span>
              </label>
              <label :class="['pb-checkout-pay__option', { active: payMethod === 'alipay' }]">
                <input type="radio" value="alipay" v-model="payMethod" />
                <span class="pb-checkout-pay__icon pb-checkout-pay__icon--alipay">支</span>
                <span>支付宝</span>
              </label>
            </div>
          </div>

          <!-- 订单备注 -->
          <div class="pb-checkout-section">
            <div class="pb-checkout-section__title">订单备注</div>
            <input v-model="remark" class="pb-checkout-remark" placeholder="选填，给商家留言（如配送时间、发票信息等）" />
          </div>

          <!-- 订单摘要 -->
          <div class="pb-checkout-section">
            <div class="pb-checkout-section__title">订单摘要</div>
            <div class="pb-checkout-summary">
              <div class="pb-checkout-summary__row">
                <span>商品数量</span>
                <span>{{ detailQuantity }} 件</span>
              </div>
              <div class="pb-checkout-summary__row">
                <span>商品总额</span>
                <span>¥{{ formatPrice((detailProduct?.price || 0) * detailQuantity) }}</span>
              </div>
              <div class="pb-checkout-summary__row pb-checkout-summary__row--total">
                <span>应付金额</span>
                <span class="pb-checkout-summary__amount">¥{{ formatPrice((detailProduct?.price || 0) * detailQuantity) }}</span>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="pb-checkout-footer">
            <button class="pb-checkout-btn--ghost" @click="closeCheckout">取消</button>
            <button class="pb-checkout-btn--primary" :disabled="checkoutLoading || !selectedAddressId" @click="confirmDirectOrder">
              {{ checkoutLoading ? '提交中...' : '确认下单' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
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

.pb-modal__top {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 28px;
  margin-bottom: 28px;
}

.pb-modal__image {
  width: 100%;
  height: 340px;
  border-radius: 14px;
  overflow: hidden;
  background: #f8f4ef;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pb-modal__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pb-modal__info {
  display: flex;
  flex-direction: column;
}

.pb-modal__name {
  font-size: 22px;
  line-height: 1.3;
  margin: 0 0 14px;
  color: var(--ink);
}

.pb-modal__price-row {
  display: flex;
  align-items: baseline;
  gap: 14px;
  margin-bottom: 14px;
}

.pb-modal__price {
  font-size: 32px;
  font-weight: 800;
  color: var(--brand);
}

.pb-modal__brand {
  font-size: 14px;
  color: var(--muted);
}

.pb-modal__rating {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 20px;
}

.pb-modal__rating .pb-card__stars {
  font-size: 15px;
}

.pb-modal__review-count {
  margin-left: auto;
}

.pb-modal__section-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 10px;
  padding-left: 10px;
  border-left: 3px solid var(--brand);
}

.pb-modal__specs {
  margin-bottom: 20px;
}

.pb-modal__spec-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.pb-modal__spec {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(217, 95, 45, 0.05);
  border-radius: 8px;
  font-size: 13px;
}

.pb-modal__spec-key {
  color: var(--muted);
  flex-shrink: 0;
}

.pb-modal__spec-val {
  color: var(--ink);
  font-weight: 500;
}

.pb-modal__points {
  margin-bottom: 20px;
}

.pb-modal__points-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--muted);
  margin: 0;
  padding: 12px 14px;
  background: rgba(217, 95, 45, 0.05);
  border-radius: 10px;
}

.pb-modal__qty {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 22px;
}

.pb-modal__qty-label {
  font-size: 14px;
  color: var(--muted);
}

.pb-modal__qty-ctrl {
  display: flex;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}

.pb-modal__qty-ctrl button {
  width: 36px;
  height: 36px;
  border: none;
  background: var(--panel);
  font-size: 18px;
  cursor: pointer;
  color: var(--ink);
  transition: background 0.2s;
}

.pb-modal__qty-ctrl button:hover {
  background: rgba(217, 95, 45, 0.08);
  color: var(--brand);
}

.pb-modal__qty-ctrl span {
  width: 48px;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
}

.pb-modal__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.pb-modal__btn {
  padding: 12px 28px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.pb-modal__btn--cart {
  color: var(--brand);
  background: transparent;
}

.pb-modal__btn--cart:hover {
  background: rgba(217, 95, 45, 0.08);
}

.pb-modal__btn--buy {
  color: #fff;
  background: var(--brand);
  border-color: var(--brand);
}

.pb-modal__btn--buy:hover {
  background: var(--brand-dark);
  border-color: var(--brand-dark);
}

.pb-modal__btn--fav {
  color: var(--muted);
  background: transparent;
  border-color: var(--line);
}

.pb-modal__btn--fav:hover {
  border-color: var(--yellow);
  color: var(--yellow);
}

.pb-modal__btn--fav.active {
  border-color: var(--yellow);
  color: var(--yellow);
  background: rgba(250, 173, 20, 0.08);
}

/* 评论 */
.pb-modal__reviews {
  border-top: 1px solid var(--line);
  padding-top: 24px;
}

.pb-review-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.pb-review {
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(217, 95, 45, 0.02);
}

.pb-review__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
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
  line-height: 1.6;
  color: var(--ink);
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

  .pb-modal__top {
    grid-template-columns: 1fr;
  }

  .pb-modal__image {
    height: 240px;
  }

  .pb-modal__spec-list {
    grid-template-columns: 1fr;
  }
}

/* ===== 立即购买结算弹窗 ===== */
.pb-checkout-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.pb-checkout-modal {
  width: min(520px, 100%);
  max-height: 85vh;
  overflow-y: auto;
  background: var(--bg, #fdfaf6);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.pb-checkout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--line, #eee);
}

.pb-checkout-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--ink, #2a2520);
}

.pb-checkout-close {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.06);
  color: var(--muted, #999);
  font-size: 18px;
  cursor: pointer;
  display: grid;
  place-items: center;
}

.pb-checkout-close:hover {
  background: rgba(0, 0, 0, 0.12);
}

.pb-checkout-section {
  padding: 16px 24px;
  border-bottom: 1px solid var(--line, #eee);
}

.pb-checkout-section__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink, #2a2520);
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid var(--brand, #d95f2d);
}

.pb-checkout-empty {
  font-size: 13px;
  color: var(--muted, #999);
}

.pb-checkout-link {
  color: var(--brand, #d95f2d);
  cursor: pointer;
  font-weight: 600;
}

.pb-checkout-addr {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--line, #eee);
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.pb-checkout-addr.active {
  border-color: var(--brand, #d95f2d);
  background: rgba(217, 95, 45, 0.04);
}

.pb-checkout-addr input[type="radio"] {
  margin-top: 3px;
  accent-color: var(--brand, #d95f2d);
}

.pb-checkout-addr__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pb-checkout-addr__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink, #2a2520);
}

.pb-checkout-addr__tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  color: #fff;
  background: var(--brand, #d95f2d);
  margin-left: 6px;
}

.pb-checkout-addr__detail {
  font-size: 12px;
  color: var(--muted, #999);
}

.pb-checkout-addaddr {
  width: 100%;
  padding: 10px;
  border: 1px dashed var(--brand, #d95f2d);
  border-radius: 10px;
  background: transparent;
  color: var(--brand, #d95f2d);
  font-size: 13px;
  cursor: pointer;
  margin-top: 4px;
}

.pb-checkout-addrform {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pb-checkout-addrform__row {
  display: flex;
  gap: 8px;
}

.pb-checkout-addrform__row input,
.pb-checkout-addrform__full {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--line, #eee);
  border-radius: 8px;
  font-size: 13px;
  background: var(--panel, #fff);
}

.pb-checkout-addrform__btns {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 4px;
}

.pb-checkout-pay {
  display: flex;
  gap: 12px;
}

.pb-checkout-pay__option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid var(--line, #eee);
  cursor: pointer;
  font-size: 14px;
}

.pb-checkout-pay__option.active {
  border-color: var(--brand, #d95f2d);
  background: rgba(217, 95, 45, 0.04);
}

.pb-checkout-pay__option input[type="radio"] {
  accent-color: var(--brand, #d95f2d);
}

.pb-checkout-pay__icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.pb-checkout-pay__icon--wechat {
  background: #07c160;
}

.pb-checkout-pay__icon--alipay {
  background: #1677ff;
}

.pb-checkout-remark {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--line, #eee);
  border-radius: 8px;
  font-size: 13px;
  background: var(--panel, #fff);
}

.pb-checkout-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pb-checkout-summary__row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--muted, #999);
}

.pb-checkout-summary__row--total {
  padding-top: 8px;
  border-top: 1px solid var(--line, #eee);
  font-weight: 700;
  color: var(--ink, #2a2520);
}

.pb-checkout-summary__amount {
  color: var(--brand, #d95f2d);
  font-size: 18px;
}

.pb-checkout-footer {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  justify-content: flex-end;
}

.pb-checkout-btn--ghost {
  padding: 10px 24px;
  border: 1px solid var(--line, #eee);
  border-radius: 10px;
  background: transparent;
  color: var(--muted, #999);
  font-size: 14px;
  cursor: pointer;
}

.pb-checkout-btn--primary {
  padding: 10px 24px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--brand, #d95f2d), var(--brand-dark, #b84a1e));
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.pb-checkout-btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
