<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

// ---------- 类型定义 ----------
type OrderStatus = 'all' | 'pending' | 'paid' | 'shipped' | 'completed' | 'cancelled' | 'returning' | 'returned'

interface OrderItem {
  product_id: number
  product_name: string
  image_url: string | null
  price: number | null
  quantity: number
}

interface Order {
  id: number
  order_no: string
  status: string
  total_amount: number
  pay_method: string | null
  remark: string | null
  created_at: string
  paid_at: string | null
  shipped_at: string | null
  completed_at: string | null
  cancelled_at: string | null
  address: string | null
  items: OrderItem[]
  tracking_no?: string | null
  return_tracking_no?: string | null
  return_status?: string | null
  return_reason?: string | null
  return_applied_at?: string | null
  return_completed_at?: string | null
}

interface ReviewMediaItem {
  file?: File
  url: string
  uploading: boolean
  error?: string
}

// ---------- 状态 ----------
const loading = ref(false)
const error = ref<string | null>(null)
const orders = ref<Order[]>([])
const activeStatus = ref<OrderStatus>('all')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const totalPages = ref(1)

// 详情弹窗
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailOrder = ref<Order | null>(null)

// 确认收货弹窗
const confirmVisible = ref(false)
const pendingConfirmOrder = ref<Order | null>(null)

// 取消订单弹窗
const cancelVisible = ref(false)
const pendingCancelOrder = ref<Order | null>(null)

// 评价弹窗
const reviewVisible = ref(false)
const reviewLoading = ref(false)
const reviewOrder = ref<Order | null>(null)
const reviewProduct = ref<OrderItem | null>(null)
const reviewForm = ref({
  product_id: 0,
  rating: 5,
  content: '',
  image_urls: [] as string[],
  videos: [] as string[],
})
const reviewImages = ref<ReviewMediaItem[]>([])
const reviewVideos = ref<ReviewMediaItem[]>([])
const reviewUploading = ref(false)

// 退换货弹窗
const returnVisible = ref(false)
const returnLoading = ref(false)
const returnOrder = ref<Order | null>(null)
const returnForm = ref({
  return_type: 'return' as 'return' | 'exchange',
  reason: '',
})

// 退货快递单号弹窗
const returnTrackingVisible = ref(false)
const returnTrackingLoading = ref(false)
const returnTrackingOrder = ref<Order | null>(null)
const returnTrackingNo = ref('')

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

// ---------- 状态 Tab 配置 ----------
const statusTabs: { key: OrderStatus; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'pending', label: '待付款' },
  { key: 'paid', label: '已付款' },
  { key: 'shipped', label: '已发货' },
  { key: 'returning', label: '退换货中' },
  { key: 'returned', label: '售后完成' },
  { key: 'completed', label: '已完成' },
  { key: 'cancelled', label: '已取消' },
]

// ---------- 状态映射 ----------
const statusMap: Record<string, { label: string; color: string }> = {
  pending: { label: '待付款', color: 'var(--brand)' },
  paid: { label: '已付款', color: 'var(--green)' },
  shipped: { label: '已发货', color: '#1677ff' },
  completed: { label: '已完成', color: 'var(--muted)' },
  cancelled: { label: '已取消', color: '#999' },
  returning: { label: '退换货中', color: '#faad14' },
  returned: { label: '售后完成', color: '#722ed1' },
}

function getStatusInfo(status: string): { label: string; color: string } {
  return statusMap[status] || { label: status, color: 'var(--muted)' }
}

// ---------- 分页数字 ----------
const pageNumbers = computed(() => {
  const pages: number[] = []
  const maxVisible = 7
  let start = Math.max(1, currentPage.value - Math.floor(maxVisible / 2))
  const end = Math.min(totalPages.value, start + maxVisible - 1)
  if (end - start < maxVisible - 1) {
    start = Math.max(1, end - maxVisible + 1)
  }
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

// ---------- 加载订单列表 ----------
async function loadOrders() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    if (activeStatus.value !== 'all') params.set('status', activeStatus.value)
    params.set('page', currentPage.value.toString())
    params.set('page_size', pageSize.value.toString())

    const response = await fetch(`${API_BASE}/api/user/orders?${params.toString()}`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    orders.value = data.orders || []
    total.value = data.total || 0
    totalPages.value = data.total_pages || 1
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载订单失败'
  } finally {
    loading.value = false
  }
}

// ---------- 切换状态 Tab ----------
function selectStatus(status: OrderStatus) {
  activeStatus.value = status
  currentPage.value = 1
  loadOrders()
}

function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadOrders()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// ---------- 订单详情 ----------
async function openDetail(order: Order) {
  detailVisible.value = true
  detailLoading.value = true
  detailOrder.value = null
  try {
    const response = await fetch(`${API_BASE}/api/user/orders/${order.id}`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    detailOrder.value = data.order || data
  } catch {
    // 降级：使用列表中的信息
    detailOrder.value = order
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detailVisible.value = false
  detailOrder.value = null
}

// ---------- 去支付 ----------
async function payOrder(order: Order, event?: Event) {
  event?.stopPropagation()
  try {
    const response = await fetch(`${API_BASE}/api/user/orders/${order.id}/pay`, {
      method: 'POST',
      headers: authHeaders(),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('支付成功')
    await loadOrders()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '支付失败', 'error')
  }
}

// ---------- 取消订单 ----------
const CANCELLABLE_STATUSES = ['pending', 'paid']

function showCancelModal(order: Order, event?: Event) {
  event?.stopPropagation()
  pendingCancelOrder.value = order
  cancelVisible.value = true
}

function closeCancelModal() {
  cancelVisible.value = false
  pendingCancelOrder.value = null
}

async function executeCancelOrder() {
  const order = pendingCancelOrder.value
  if (!order) return
  closeCancelModal()
  try {
    const response = await fetch(`${API_BASE}/api/user/orders/${order.id}/cancel`, {
      method: 'POST',
      headers: authHeaders(),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('订单已取消')
    await loadOrders()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '取消失败', 'error')
  }
}

// ---------- 确认收货 ----------
function showConfirmModal(order: Order, event?: Event) {
  event?.stopPropagation()
  pendingConfirmOrder.value = order
  confirmVisible.value = true
}

function closeConfirmModal() {
  confirmVisible.value = false
  pendingConfirmOrder.value = null
}

async function executeConfirmReceipt() {
  const order = pendingConfirmOrder.value
  if (!order) return
  closeConfirmModal()
  try {
    const response = await fetch(`${API_BASE}/api/user/orders/${order.id}/confirm`, {
      method: 'POST',
      headers: authHeaders(),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('已确认收货')
    await loadOrders()
    // 打开评价弹窗（可选）
    openReviewModal(order)
  } catch (e) {
    showToast(e instanceof Error ? e.message : '确认收货失败', 'error')
  }
}

// ---------- 评价 ----------
function openReviewModal(order: Order) {
  reviewOrder.value = order
  // 默认评价第一个商品
  const firstItem = order.items[0] || null
  reviewProduct.value = firstItem
  reviewForm.value = {
    product_id: firstItem?.product_id || 0,
    rating: 5,
    content: '',
    image_urls: [],
    videos: [],
  }
  reviewImages.value = []
  reviewVideos.value = []
  reviewVisible.value = true
}

function closeReviewModal() {
  reviewVisible.value = false
  reviewOrder.value = null
  reviewProduct.value = null
}

function selectReviewProduct(item: OrderItem) {
  reviewProduct.value = item
  reviewForm.value.product_id = item.product_id
}

async function uploadReviewMedia(file: File): Promise<string> {
  const data = new FormData()
  data.append('file', file)
  const response = await fetch(`${API_BASE}/api/user/reviews/upload-media`, {
    method: 'POST',
    headers: { ...(localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}) },
    body: data,
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.message || `上传失败 ${response.status}`)
  }
  const json = await response.json()
  return json.url
}

async function handleReviewImageSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  input.value = ''
  const items: ReviewMediaItem[] = files.map((file) => ({ file, url: URL.createObjectURL(file), uploading: true }))
  reviewImages.value.push(...items)
  reviewUploading.value = true
  for (const item of items) {
    try {
      const url = await uploadReviewMedia(item.file!)
      item.url = url
      item.uploading = false
      reviewForm.value.image_urls.push(url)
    } catch (e) {
      item.error = e instanceof Error ? e.message : '上传失败'
      item.uploading = false
    }
  }
  reviewUploading.value = reviewImages.value.some((i) => i.uploading) || reviewVideos.value.some((i) => i.uploading)
}

async function handleReviewVideoSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  input.value = ''
  const items: ReviewMediaItem[] = files.map((file) => ({ file, url: URL.createObjectURL(file), uploading: true }))
  reviewVideos.value.push(...items)
  reviewUploading.value = true
  for (const item of items) {
    try {
      const url = await uploadReviewMedia(item.file!)
      item.url = url
      item.uploading = false
      reviewForm.value.videos.push(url)
    } catch (e) {
      item.error = e instanceof Error ? e.message : '上传失败'
      item.uploading = false
    }
  }
  reviewUploading.value = reviewImages.value.some((i) => i.uploading) || reviewVideos.value.some((i) => i.uploading)
}

function removeReviewImage(url: string) {
  reviewForm.value.image_urls = reviewForm.value.image_urls.filter((u) => u !== url)
  reviewImages.value = reviewImages.value.filter((i) => i.url !== url)
}

function removeReviewVideo(url: string) {
  reviewForm.value.videos = reviewForm.value.videos.filter((u) => u !== url)
  reviewVideos.value = reviewVideos.value.filter((i) => i.url !== url)
}

async function submitReview() {
  if (!reviewForm.value.product_id) return
  if (reviewUploading.value) {
    showToast('请等待媒体上传完成', 'error')
    return
  }
  reviewLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/user/reviews/submit`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(reviewForm.value),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('评价提交成功')
    closeReviewModal()
    await loadOrders()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '评价提交失败', 'error')
  } finally {
    reviewLoading.value = false
  }
}

function skipReview() {
  closeReviewModal()
}

// ---------- 退换货 ----------
function canApplyReturn(order: Order): boolean {
  return !['pending', 'cancelled', 'returning', 'returned'].includes(order.status)
}

function showReturnModal(order: Order, event?: Event) {
  event?.stopPropagation()
  returnOrder.value = order
  returnForm.value = { return_type: 'return', reason: '' }
  returnVisible.value = true
}

function closeReturnModal() {
  returnVisible.value = false
  returnOrder.value = null
  returnForm.value = { return_type: 'return', reason: '' }
}

async function submitReturn() {
  const order = returnOrder.value
  if (!order) return
  if (!returnForm.value.reason.trim()) {
    showToast('请填写退换货原因', 'error')
    return
  }
  returnLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/user/orders/${order.id}/apply-return`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        return_type: returnForm.value.return_type,
        reason: returnForm.value.reason.trim(),
      }),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('退换货申请已提交')
    closeReturnModal()
    await loadOrders()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '申请失败', 'error')
  } finally {
    returnLoading.value = false
  }
}

// ---------- 退货快递单号 ----------
function showReturnTrackingModal(order: Order, event?: Event) {
  event?.stopPropagation()
  returnTrackingOrder.value = order
  returnTrackingNo.value = order.return_tracking_no || ''
  returnTrackingVisible.value = true
}

function closeReturnTrackingModal() {
  returnTrackingVisible.value = false
  returnTrackingOrder.value = null
  returnTrackingNo.value = ''
}

async function submitReturnTracking() {
  const order = returnTrackingOrder.value
  if (!order) return
  const trackingNo = returnTrackingNo.value.trim()
  if (!trackingNo) {
    showToast('请填写退货快递单号', 'error')
    return
  }
  returnTrackingLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/user/orders/${order.id}/return-tracking`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ tracking_no: trackingNo }),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast('退货快递单号已提交')
    closeReturnTrackingModal()
    await loadOrders()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '提交失败', 'error')
  } finally {
    returnTrackingLoading.value = false
  }
}

// ---------- 格式化 ----------
function formatPrice(price: number | null | undefined): string {
  if (price == null) return '--'
  return price.toFixed(2)
}

function formatTime(time: string | null): string {
  if (!time) return '--'
  return time.replace('T', ' ').slice(0, 19)
}

onMounted(() => {
  loadOrders()
})
</script>

<template>
  <div class="my-orders">
    <!-- 提示 Toast -->
    <transition name="toast">
      <div v-if="toast.visible" :class="['mo-toast', `mo-toast--${toast.type}`]">
        {{ toast.message }}
      </div>
    </transition>

    <!-- 状态筛选 Tab -->
    <div class="mo-tabs">
      <button
        v-for="tab in statusTabs"
        :key="tab.key"
        :class="['mo-tab', { active: activeStatus === tab.key }]"
        @click="selectStatus(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="mo-error">{{ error }}</div>

    <!-- 加载中 -->
    <div v-if="loading" class="mo-loading">
      <div class="mo-loading__spinner"></div>
      <p>正在加载订单...</p>
    </div>

    <!-- 订单列表 -->
    <div v-else-if="orders.length > 0" class="mo-list">
      <div
        v-for="order in orders"
        :key="order.id"
        class="mo-card"
        @click="openDetail(order)"
      >
        <!-- 卡片头部 -->
        <div class="mo-card__header">
          <div class="mo-card__meta">
            <span class="mo-card__no">订单号：{{ order.order_no }}</span>
            <span class="mo-card__time">{{ formatTime(order.created_at) }}</span>
          </div>
          <span
            class="mo-card__status"
            :style="{ color: getStatusInfo(order.status).color }"
          >
            {{ getStatusInfo(order.status).label }}
          </span>
        </div>

        <!-- 商品快照 -->
        <div class="mo-card__items">
          <div
            v-for="(item, idx) in order.items.slice(0, 4)"
            :key="idx"
            class="mo-card__item"
          >
            <div class="mo-card__item-image">
              <img
                v-if="item.image_url"
                :src="item.image_url"
                :alt="item.product_name"
                @error="(e: any) => e.target.style.display = 'none'"
              />
              <div v-if="!item.image_url" class="mo-card__item-noimg">无图</div>
            </div>
            <div class="mo-card__item-info">
              <span class="mo-card__item-name">{{ item.product_name }}</span>
              <span class="mo-card__item-price">¥{{ formatPrice(item.price) }} × {{ item.quantity }}</span>
            </div>
          </div>
          <div v-if="order.items.length > 4" class="mo-card__more">
            还有 {{ order.items.length - 4 }} 件商品...
          </div>
        </div>

        <!-- 卡片底部 -->
        <div class="mo-card__footer">
          <div class="mo-card__total">
            共 {{ order.items.reduce((s, i) => s + i.quantity, 0) }} 件商品，
            合计：<strong>¥{{ formatPrice(order.total_amount) }}</strong>
          </div>
          <div class="mo-card__actions" @click.stop>
            <!-- 待付款 / 已付款：可取消 + 可支付 -->
            <template v-if="order.status === 'pending'">
              <button class="mo-btn mo-btn--ghost" @click="showCancelModal(order, $event)">取消订单</button>
              <button class="mo-btn mo-btn--primary" @click="payOrder(order, $event)">去支付</button>
            </template>
            <!-- 已付款 — 等待商家发货 -->
            <template v-else-if="order.status === 'paid'">
              <button class="mo-btn mo-btn--ghost" @click="showCancelModal(order, $event)">取消订单</button>
              <span class="mo-btn mo-btn--hint">等待商家发货</span>
            </template>
            <!-- 已发货 -->
            <template v-else-if="order.status === 'shipped'">
              <button class="mo-btn mo-btn--ghost" @click="showReturnModal(order, $event)">退换货</button>
              <button class="mo-btn mo-btn--primary" @click="showConfirmModal(order, $event)">确认收货</button>
            </template>
            <!-- 已完成 -->
            <template v-else-if="order.status === 'completed'">
              <button class="mo-btn mo-btn--ghost" @click="showReturnModal(order, $event)">退换货</button>
              <button class="mo-btn mo-btn--ghost" @click="openDetail(order)">查看详情</button>
            </template>
            <!-- 退换货中 -->
            <template v-else-if="order.status === 'returning'">
              <button
                v-if="order.return_applied_at && !order.return_tracking_no"
                class="mo-btn mo-btn--primary"
                @click="showReturnTrackingModal(order, $event)"
              >
                填写退货单号
              </button>
              <button class="mo-btn mo-btn--ghost" @click="openDetail(order)">查看详情</button>
            </template>
            <!-- 其他状态 -->
            <button v-else class="mo-btn mo-btn--ghost" @click="openDetail(order)">查看详情</button>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="mo-pagination">
        <button
          class="mo-page-btn"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          上一页
        </button>
        <button
          v-for="page in pageNumbers"
          :key="page"
          :class="['mo-page-btn', { active: page === currentPage }]"
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
        <button
          class="mo-page-btn"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          下一页
        </button>
        <span class="mo-page-info">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条</span>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="mo-empty">
      <div class="mo-empty__icon">单</div>
      <h3>暂无订单</h3>
      <p>快去挑选心仪的商品吧</p>
    </div>

    <!-- 订单详情弹窗 -->
    <transition name="modal">
      <div v-if="detailVisible" class="mo-modal-overlay" @click.self="closeDetail">
        <div class="mo-modal">
          <div class="mo-modal__header">
            <h2>订单详情</h2>
            <button class="mo-modal__close" @click="closeDetail">×</button>
          </div>

          <!-- 加载中 -->
          <div v-if="detailLoading" class="mo-modal__loading">
            <div class="mo-loading__spinner"></div>
            <p>加载订单详情...</p>
          </div>

          <!-- 详情内容 -->
          <div v-else-if="detailOrder" class="mo-modal__body">
            <!-- 订单基本信息 -->
            <div class="mo-detail-section">
              <div class="mo-detail-section__title">订单信息</div>
              <div class="mo-detail-grid">
                <div class="mo-detail-item">
                  <span class="mo-detail-item__label">订单编号</span>
                  <span class="mo-detail-item__value">{{ detailOrder.order_no }}</span>
                </div>
                <div class="mo-detail-item">
                  <span class="mo-detail-item__label">下单时间</span>
                  <span class="mo-detail-item__value">{{ formatTime(detailOrder.created_at) }}</span>
                </div>
                <div class="mo-detail-item">
                  <span class="mo-detail-item__label">订单状态</span>
                  <span
                    class="mo-detail-item__value"
                    :style="{ color: getStatusInfo(detailOrder.status).color, fontWeight: '700' }"
                  >
                    {{ getStatusInfo(detailOrder.status).label }}
                  </span>
                </div>
                <div class="mo-detail-item">
                  <span class="mo-detail-item__label">支付方式</span>
                  <span class="mo-detail-item__value">
                    {{ detailOrder.pay_method === 'wechat' ? '微信支付' : detailOrder.pay_method === 'alipay' ? '支付宝' : '--' }}
                  </span>
                </div>
                <div v-if="detailOrder.paid_at" class="mo-detail-item">
                  <span class="mo-detail-item__label">支付时间</span>
                  <span class="mo-detail-item__value">{{ formatTime(detailOrder.paid_at) }}</span>
                </div>
                <div v-if="detailOrder.shipped_at" class="mo-detail-item">
                  <span class="mo-detail-item__label">发货时间</span>
                  <span class="mo-detail-item__value">{{ formatTime(detailOrder.shipped_at) }}</span>
                </div>
                <div v-if="detailOrder.completed_at" class="mo-detail-item">
                  <span class="mo-detail-item__label">完成时间</span>
                  <span class="mo-detail-item__value">{{ formatTime(detailOrder.completed_at) }}</span>
                </div>
                <div v-if="detailOrder.cancelled_at" class="mo-detail-item">
                  <span class="mo-detail-item__label">取消时间</span>
                  <span class="mo-detail-item__value">{{ formatTime(detailOrder.cancelled_at) }}</span>
                </div>
                <div v-if="detailOrder.tracking_no" class="mo-detail-item">
                  <span class="mo-detail-item__label">快递单号</span>
                  <span class="mo-detail-item__value">{{ detailOrder.tracking_no }}</span>
                </div>
                <div v-if="detailOrder.return_tracking_no" class="mo-detail-item">
                  <span class="mo-detail-item__label">退货单号</span>
                  <span class="mo-detail-item__value">{{ detailOrder.return_tracking_no }}</span>
                </div>
                <div v-if="detailOrder.return_reason" class="mo-detail-item mo-detail-item--full">
                  <span class="mo-detail-item__label">售后原因</span>
                  <span class="mo-detail-item__value">{{ detailOrder.return_reason }}</span>
                </div>
              </div>
            </div>

            <!-- 收货地址 -->
            <div v-if="detailOrder.address" class="mo-detail-section">
              <div class="mo-detail-section__title">收货地址</div>
              <p class="mo-detail-address">{{ detailOrder.address }}</p>
            </div>

            <!-- 商品列表 -->
            <div class="mo-detail-section">
              <div class="mo-detail-section__title">商品清单</div>
              <div class="mo-detail-products">
                <div
                  v-for="(item, idx) in detailOrder.items"
                  :key="idx"
                  class="mo-detail-product"
                >
                  <div class="mo-detail-product__image">
                    <img
                      v-if="item.image_url"
                      :src="item.image_url"
                      :alt="item.product_name"
                      @error="(e: any) => e.target.style.display = 'none'"
                    />
                    <div v-if="!item.image_url" class="mo-card__item-noimg">无图</div>
                  </div>
                  <div class="mo-detail-product__info">
                    <span class="mo-detail-product__name">{{ item.product_name }}</span>
                    <span class="mo-detail-product__price">¥{{ formatPrice(item.price) }}</span>
                  </div>
                  <div class="mo-detail-product__qty">× {{ item.quantity }}</div>
                  <div class="mo-detail-product__subtotal">
                    ¥{{ formatPrice((item.price ?? 0) * item.quantity) }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 备注 -->
            <div v-if="detailOrder.remark" class="mo-detail-section">
              <div class="mo-detail-section__title">订单备注</div>
              <p class="mo-detail-remark">{{ detailOrder.remark }}</p>
            </div>

            <!-- 金额汇总 -->
            <div class="mo-detail-section">
              <div class="mo-detail-summary">
                <div class="mo-detail-summary__row">
                  <span>商品总数</span>
                  <span>{{ detailOrder.items.reduce((s, i) => s + i.quantity, 0) }} 件</span>
                </div>
                <div class="mo-detail-summary__row mo-detail-summary__row--total">
                  <span>订单总额</span>
                  <span class="mo-detail-summary__amount">¥{{ formatPrice(detailOrder.total_amount) }}</span>
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="mo-detail-actions">
              <button
                v-if="CANCELLABLE_STATUSES.includes(detailOrder.status)"
                class="mo-btn mo-btn--ghost"
                @click="showCancelModal(detailOrder); closeDetail()"
              >
                取消订单
              </button>
              <button
                v-if="detailOrder.status === 'pending'"
                class="mo-btn mo-btn--primary"
                @click="payOrder(detailOrder); closeDetail()"
              >
                去支付
              </button>
              <span
                v-if="detailOrder.status === 'paid'"
                class="mo-detail-hint"
              >
                等待商家发货中...
              </span>
              <button
                v-if="detailOrder.status === 'shipped'"
                class="mo-btn mo-btn--ghost"
                @click="showReturnModal(detailOrder); closeDetail()"
              >
                退换货
              </button>
              <button
                v-if="detailOrder.status === 'shipped'"
                class="mo-btn mo-btn--primary"
                @click="showConfirmModal(detailOrder); closeDetail()"
              >
                确认收货
              </button>
              <button
                v-if="canApplyReturn(detailOrder)"
                class="mo-btn mo-btn--ghost"
                @click="showReturnModal(detailOrder); closeDetail()"
              >
                申请售后
              </button>
              <button
                v-if="detailOrder.status === 'returning' && !detailOrder.return_tracking_no"
                class="mo-btn mo-btn--primary"
                @click="showReturnTrackingModal(detailOrder); closeDetail()"
              >
                填写退货单号
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 确认收货弹窗 -->
    <transition name="modal">
      <div v-if="confirmVisible" class="mo-modal-overlay" @click.self="closeConfirmModal">
        <div class="mo-modal mo-modal--sm">
          <div class="mo-modal__header">
            <h2>确认收货</h2>
            <button class="mo-modal__close" @click="closeConfirmModal">×</button>
          </div>
          <div class="mo-modal__body">
            <div class="mo-confirm-body">
              <div class="mo-confirm-icon mo-confirm-icon--success">✓</div>
              <p class="mo-confirm-text">确认已收到商品并完成订单吗？</p>
              <p class="mo-confirm-hint">确认后订单状态将变为“已完成”，您也可以稍后对该商品进行评价。</p>
            </div>
            <div class="mo-confirm-actions">
              <button class="mo-btn mo-btn--ghost" @click="closeConfirmModal">再等等</button>
              <button class="mo-btn mo-btn--primary" @click="executeConfirmReceipt">确认收货</button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 取消订单弹窗 -->
    <transition name="modal">
      <div v-if="cancelVisible" class="mo-modal-overlay" @click.self="closeCancelModal">
        <div class="mo-modal mo-modal--sm">
          <div class="mo-modal__header">
            <h2>取消订单</h2>
            <button class="mo-modal__close" @click="closeCancelModal">×</button>
          </div>
          <div class="mo-modal__body">
            <div class="mo-confirm-body">
              <div class="mo-confirm-icon mo-confirm-icon--warning">!</div>
              <p class="mo-confirm-text">确定要取消该订单吗？</p>
              <p class="mo-confirm-hint">
                订单取消后将无法恢复，{{ pendingCancelOrder?.status === 'paid' ? '已支付金额将按原路退回。' : '无需支付任何费用。' }}
              </p>
              <div v-if="pendingCancelOrder" class="mo-cancel-order-info">
                <span>订单号：{{ pendingCancelOrder.order_no }}</span>
                <span>合计：<strong>¥{{ formatPrice(pendingCancelOrder.total_amount) }}</strong></span>
              </div>
            </div>
            <div class="mo-confirm-actions">
              <button class="mo-btn mo-btn--ghost" @click="closeCancelModal">再想想</button>
              <button class="mo-btn mo-btn--danger" @click="executeCancelOrder">确认取消</button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 评价弹窗 -->
    <transition name="modal">
      <div v-if="reviewVisible" class="mo-modal-overlay" @click.self="closeReviewModal">
        <div class="mo-modal mo-modal--md">
          <div class="mo-modal__header">
            <h2>发表评价</h2>
            <button class="mo-modal__close" @click="closeReviewModal">×</button>
          </div>
          <div v-if="reviewLoading" class="mo-modal__loading">
            <div class="mo-loading__spinner"></div>
            <p>提交评价中...</p>
          </div>
          <div v-else class="mo-modal__body">
            <!-- 选择评价商品 -->
            <div v-if="reviewOrder && reviewOrder.items.length > 1" class="mo-review-section">
              <div class="mo-review-section__title">选择要评价的商品</div>
              <div class="mo-review-products">
                <div
                  v-for="item in reviewOrder.items"
                  :key="item.product_id"
                  :class="['mo-review-product', { active: reviewProduct?.product_id === item.product_id }]"
                  @click="selectReviewProduct(item)"
                >
                  <img v-if="item.image_url" :src="item.image_url" :alt="item.product_name" />
                  <div v-else class="mo-review-product__noimg">无图</div>
                  <span class="mo-review-product__name">{{ item.product_name }}</span>
                </div>
              </div>
            </div>

            <!-- 评分 -->
            <div class="mo-review-section">
              <div class="mo-review-section__title">商品评分</div>
              <div class="mo-review-rating">
                <button
                  v-for="n in 5"
                  :key="n"
                  :class="['mo-review-star', { active: n <= reviewForm.rating }]"
                  @click="reviewForm.rating = n"
                >
                  ★
                </button>
                <span class="mo-review-rating__text">{{ reviewForm.rating }} 分</span>
              </div>
            </div>

            <!-- 评价内容 -->
            <div class="mo-review-section">
              <div class="mo-review-section__title">评价内容</div>
              <textarea
                v-model="reviewForm.content"
                class="mo-review-textarea"
                rows="4"
                placeholder="分享您的使用体验，帮助其他买家做出选择（选填）"
              ></textarea>
            </div>

            <!-- 上传图片 -->
            <div class="mo-review-section">
              <div class="mo-review-section__title">
                上传图片
                <span class="mo-review-section__hint">（选填，最多 6 张）</span>
              </div>
              <div class="mo-review-media">
                <div v-for="(img, idx) in reviewImages" :key="idx" class="mo-review-media__item">
                  <img :src="img.url" />
                  <div v-if="img.uploading" class="mo-review-media__mask">
                    <div class="mo-loading__spinner"></div>
                  </div>
                  <div v-if="img.error" class="mo-review-media__error" :title="img.error">!</div>
                  <button class="mo-review-media__remove" @click="removeReviewImage(img.url)">×</button>
                </div>
                <label v-if="reviewImages.length < 6" class="mo-review-media__add">
                  <input type="file" accept="image/*" multiple @change="handleReviewImageSelect" />
                  <span>+</span>
                </label>
              </div>
            </div>

            <!-- 上传视频 -->
            <div class="mo-review-section">
              <div class="mo-review-section__title">
                上传视频
                <span class="mo-review-section__hint">（选填，最多 3 个）</span>
              </div>
              <div class="mo-review-media">
                <div v-for="(video, idx) in reviewVideos" :key="idx" class="mo-review-media__item mo-review-media__item--video">
                  <video :src="video.url" controls></video>
                  <div v-if="video.uploading" class="mo-review-media__mask">
                    <div class="mo-loading__spinner"></div>
                  </div>
                  <div v-if="video.error" class="mo-review-media__error" :title="video.error">!</div>
                  <button class="mo-review-media__remove" @click="removeReviewVideo(video.url)">×</button>
                </div>
                <label v-if="reviewVideos.length < 3" class="mo-review-media__add">
                  <input type="file" accept="video/*" multiple @change="handleReviewVideoSelect" />
                  <span>+</span>
                </label>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="mo-review-actions">
              <button class="mo-btn mo-btn--ghost" @click="skipReview">暂不评价</button>
              <button
                class="mo-btn mo-btn--primary"
                :disabled="reviewUploading"
                @click="submitReview"
              >
                提交评价
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 退换货弹窗 -->
    <transition name="modal">
      <div v-if="returnVisible" class="mo-modal-overlay" @click.self="closeReturnModal">
        <div class="mo-modal mo-modal--sm">
          <div class="mo-modal__header">
            <h2>申请退换货</h2>
            <button class="mo-modal__close" @click="closeReturnModal">×</button>
          </div>
          <div class="mo-modal__body">
            <div class="mo-form-group">
              <label>服务类型</label>
              <div class="mo-return-types">
                <label :class="['mo-return-type', { active: returnForm.return_type === 'return' }]">
                  <input v-model="returnForm.return_type" type="radio" value="return" />
                  <span>退货</span>
                </label>
                <label :class="['mo-return-type', { active: returnForm.return_type === 'exchange' }]">
                  <input v-model="returnForm.return_type" type="radio" value="exchange" />
                  <span>换货</span>
                </label>
              </div>
            </div>
            <div class="mo-form-group">
              <label>原因描述 <span class="mo-required">*</span></label>
              <textarea
                v-model="returnForm.reason"
                class="mo-review-textarea"
                rows="4"
                placeholder="请填写退换货原因，例如：尺码不合适 / 商品破损 / 与描述不符"
              ></textarea>
            </div>
            <div class="mo-confirm-actions">
              <button class="mo-btn mo-btn--ghost" @click="closeReturnModal">取消</button>
              <button
                class="mo-btn mo-btn--primary"
                :disabled="returnLoading || !returnForm.reason.trim()"
                @click="submitReturn"
              >
                {{ returnLoading ? '提交中...' : '提交申请' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 退货快递单号弹窗 -->
    <transition name="modal">
      <div v-if="returnTrackingVisible" class="mo-modal-overlay" @click.self="closeReturnTrackingModal">
        <div class="mo-modal mo-modal--sm">
          <div class="mo-modal__header">
            <h2>填写退货快递单号</h2>
            <button class="mo-modal__close" @click="closeReturnTrackingModal">×</button>
          </div>
          <div class="mo-modal__body">
            <p class="mo-confirm-hint" style="text-align:left;margin-bottom:16px;">
              商家已同意退换货，请将商品寄回并填写快递单号，方便商家跟进。
            </p>
            <div class="mo-form-group">
              <label>退货快递单号 <span class="mo-required">*</span></label>
              <input
                v-model="returnTrackingNo"
                type="text"
                placeholder="例如：顺丰 SF1234567890"
                @keydown.enter="submitReturnTracking"
              />
            </div>
            <div class="mo-confirm-actions">
              <button class="mo-btn mo-btn--ghost" @click="closeReturnTrackingModal">取消</button>
              <button
                class="mo-btn mo-btn--primary"
                :disabled="returnTrackingLoading || !returnTrackingNo.trim()"
                @click="submitReturnTracking"
              >
                {{ returnTrackingLoading ? '提交中...' : '确认提交' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.my-orders {
  position: relative;
}

/* Toast */
.mo-toast {
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

.mo-toast--success {
  background: var(--green);
}

.mo-toast--error {
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

/* 状态 Tab */
.mo-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 2px solid var(--line);
  overflow-x: auto;
}

.mo-tab {
  padding: 10px 20px;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  background: transparent;
  color: var(--muted);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.mo-tab:hover {
  color: var(--brand);
}

.mo-tab.active {
  color: var(--brand);
  border-bottom-color: var(--brand);
  font-weight: 700;
}

/* 加载 */
.mo-loading {
  text-align: center;
  padding: 80px 20px;
  color: var(--muted);
}

.mo-loading__spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: mo-spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes mo-spin {
  to { transform: rotate(360deg); }
}

/* 错误 */
.mo-error {
  background: #fff0f0;
  color: #c33;
  padding: 14px 18px;
  border-radius: 12px;
  margin-bottom: 20px;
  font-size: 14px;
}

/* 订单列表 */
.mo-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mo-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.mo-card:hover {
  border-color: var(--brand);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.mo-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: rgba(217, 95, 45, 0.03);
  border-bottom: 1px solid var(--line);
}

.mo-card__meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.mo-card__no {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.mo-card__time {
  font-size: 13px;
  color: var(--muted);
}

.mo-card__status {
  font-size: 14px;
  font-weight: 700;
}

/* 商品快照 */
.mo-card__items {
  padding: 16px 20px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.mo-card__item {
  display: flex;
  gap: 10px;
  align-items: center;
  max-width: 280px;
}

.mo-card__item-image {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f4ef;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.mo-card__item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mo-card__item-noimg {
  font-size: 11px;
  color: var(--muted);
}

.mo-card__item-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.mo-card__item-name {
  font-size: 13px;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.mo-card__item-price {
  font-size: 12px;
  color: var(--muted);
}

.mo-card__more {
  font-size: 13px;
  color: var(--muted);
  align-self: center;
}

/* 卡片底部 */
.mo-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-top: 1px solid var(--line);
  background: rgba(217, 95, 45, 0.02);
}

.mo-card__total {
  font-size: 14px;
  color: var(--muted);
}

.mo-card__total strong {
  font-size: 18px;
  color: var(--brand);
  font-weight: 800;
}

.mo-card__actions {
  display: flex;
  gap: 10px;
}

/* 按钮 */
.mo-btn {
  padding: 8px 20px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.mo-btn--ghost {
  color: var(--muted);
  background: transparent;
  border-color: var(--line);
}

.mo-btn--ghost:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.mo-btn--hint {
  color: var(--muted);
  font-size: 13px;
  padding: 8px 14px;
}

.mo-detail-hint {
  color: var(--muted);
  font-size: 14px;
  padding: 8px 0;
}

.mo-btn--primary {
  color: #fff;
  background: var(--brand);
  border-color: var(--brand);
}

.mo-btn--primary:hover {
  background: var(--brand-dark);
}

.mo-btn--danger {
  color: #fff;
  background: #c33;
  border-color: #c33;
}

.mo-btn--danger:hover {
  background: #a52a2a;
}

.mo-cancel-order-info {
  margin-top: 16px;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--muted);
  text-align: left;
}

.mo-cancel-order-info strong {
  color: var(--brand);
  font-size: 15px;
}

/* 空状态 */
.mo-empty {
  text-align: center;
  padding: 80px 20px;
  color: var(--muted);
}

.mo-empty__icon {
  display: inline-grid;
  width: 80px;
  height: 80px;
  place-items: center;
  border-radius: 24px;
  margin-bottom: 20px;
  font-size: 32px;
  font-weight: 800;
  color: #fffaf0;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
}

.mo-empty h3 {
  font-size: 20px;
  color: var(--ink);
  margin: 0 0 8px;
}

.mo-empty p {
  font-size: 14px;
  margin: 0;
}

/* 分页 */
.mo-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-top: 28px;
  flex-wrap: wrap;
}

.mo-page-btn {
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.mo-page-btn:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand);
}

.mo-page-btn.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.mo-page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.mo-page-info {
  margin-left: 12px;
  font-size: 13px;
  color: var(--muted);
}

/* 详情弹窗 */
.mo-modal-overlay {
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

.mo-modal {
  width: min(720px, 100%);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.3);
}

.mo-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--line);
}

.mo-modal__header h2 {
  font-size: 18px;
  margin: 0;
}

.mo-modal__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.06);
  font-size: 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.mo-modal__close:hover {
  background: rgba(0, 0, 0, 0.14);
}

.mo-modal__loading {
  text-align: center;
  padding: 80px 20px;
  color: var(--muted);
}

.mo-modal__body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.mo-detail-section {
  margin-bottom: 24px;
}

.mo-detail-section:last-child {
  margin-bottom: 0;
}

.mo-detail-section__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid var(--brand);
}

.mo-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.mo-detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  background: rgba(217, 95, 45, 0.03);
  border-radius: 8px;
}

.mo-detail-item__label {
  font-size: 12px;
  color: var(--muted);
}

.mo-detail-item__value {
  font-size: 14px;
  color: var(--ink);
  font-weight: 500;
}

.mo-detail-address {
  margin: 0;
  padding: 12px 14px;
  background: rgba(217, 95, 45, 0.03);
  border-radius: 8px;
  font-size: 14px;
  color: var(--ink);
  line-height: 1.6;
}

.mo-detail-products {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mo-detail-product {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
}

.mo-detail-product__image {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f4ef;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.mo-detail-product__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mo-detail-product__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.mo-detail-product__name {
  font-size: 14px;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.mo-detail-product__price {
  font-size: 13px;
  color: var(--muted);
}

.mo-detail-product__qty {
  font-size: 14px;
  color: var(--muted);
}

.mo-detail-product__subtotal {
  font-size: 15px;
  font-weight: 700;
  color: var(--brand);
  min-width: 80px;
  text-align: right;
}

.mo-detail-remark {
  margin: 0;
  padding: 12px 14px;
  background: rgba(250, 173, 20, 0.06);
  border-radius: 8px;
  font-size: 14px;
  color: var(--ink);
  line-height: 1.6;
}

.mo-detail-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 18px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(217, 95, 45, 0.02);
}

.mo-detail-summary__row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--muted);
}

.mo-detail-summary__row--total {
  padding-top: 10px;
  border-top: 1px solid var(--line);
  font-size: 16px;
  color: var(--ink);
  font-weight: 700;
}

.mo-detail-summary__amount {
  font-size: 22px;
  color: var(--brand);
  font-weight: 800;
}

.mo-detail-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

.mo-detail-actions .mo-btn {
  padding: 10px 28px;
  font-size: 14px;
}

/* 确认收货 / 评价弹窗尺寸 */
.mo-modal--sm {
  width: min(420px, 100%);
}

.mo-modal--md {
  width: min(560px, 100%);
}

/* 确认收货 */
.mo-confirm-body {
  text-align: center;
  padding: 16px 8px 24px;
}

.mo-confirm-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  color: #fff;
  font-size: 32px;
  display: inline-grid;
  place-items: center;
  margin-bottom: 16px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
}

.mo-confirm-icon--success {
  background: linear-gradient(135deg, var(--green), #10b981);
  box-shadow: 0 12px 30px rgba(52, 211, 153, 0.25);
}

.mo-confirm-icon--warning {
  background: linear-gradient(135deg, #faad14, #f59e0b);
  box-shadow: 0 12px 30px rgba(250, 173, 20, 0.25);
}

.mo-confirm-text {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink);
  margin: 0 0 8px;
}

.mo-confirm-hint {
  font-size: 13px;
  color: var(--muted);
  margin: 0;
  line-height: 1.6;
}

.mo-confirm-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

/* 评价 */
.mo-review-section {
  margin-bottom: 22px;
}

.mo-review-section__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid var(--brand);
}

.mo-review-section__hint {
  font-size: 12px;
  color: var(--muted);
  font-weight: 400;
  margin-left: 6px;
}

.mo-review-products {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.mo-review-product {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
  cursor: pointer;
  transition: all 0.2s;
  max-width: 220px;
}

.mo-review-product:hover,
.mo-review-product.active {
  border-color: var(--brand);
  background: rgba(155, 135, 245, 0.06);
}

.mo-review-product img,
.mo-review-product__noimg {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  background: #f8f4ef;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--muted);
}

.mo-review-product__name {
  font-size: 13px;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.mo-review-rating {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mo-review-star {
  width: 34px;
  height: 34px;
  border: none;
  background: transparent;
  font-size: 26px;
  color: #e5e7eb;
  cursor: pointer;
  transition: color 0.2s, transform 0.15s;
  line-height: 1;
}

.mo-review-star:hover,
.mo-review-star.active {
  color: var(--yellow);
}

.mo-review-star:hover {
  transform: scale(1.1);
}

.mo-review-rating__text {
  font-size: 14px;
  color: var(--muted);
  margin-left: 8px;
}

.mo-review-textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
  font-size: 14px;
  font-family: inherit;
  color: var(--ink);
  resize: vertical;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.mo-review-textarea:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(155, 135, 245, 0.1);
}

.mo-review-media {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.mo-review-media__item {
  width: 88px;
  height: 88px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--line);
  position: relative;
  background: #f8f4ef;
}

.mo-review-media__item--video {
  width: 140px;
  height: 88px;
}

.mo-review-media__item img,
.mo-review-media__item video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mo-review-media__mask {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
}

.mo-review-media__mask .mo-loading__spinner {
  width: 24px;
  height: 24px;
  border-width: 2px;
  margin: 0;
}

.mo-review-media__error {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ef4444;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mo-review-media__remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.mo-review-media__remove:hover {
  background: rgba(0, 0, 0, 0.7);
}

.mo-review-media__add {
  width: 88px;
  height: 88px;
  border: 1px dashed var(--brand);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--brand);
  font-size: 28px;
  background: rgba(155, 135, 245, 0.04);
  transition: background 0.2s;
}

.mo-review-media__add:hover {
  background: rgba(155, 135, 245, 0.1);
}

.mo-review-media__add input {
  display: none;
}

.mo-review-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

/* 退换货类型选择 */
.mo-return-types {
  display: flex;
  gap: 12px;
}

.mo-return-type {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: var(--ink);
}

.mo-return-type input {
  display: none;
}

.mo-return-type.active,
.mo-return-type:hover {
  border-color: var(--brand);
  background: rgba(217, 95, 45, 0.06);
  color: var(--brand);
}

/* 弹窗过渡 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s;
}

.modal-enter-active .mo-modal,
.modal-leave-active .mo-modal {
  transition: transform 0.25s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .mo-modal,
.modal-leave-to .mo-modal {
  transform: scale(0.95) translateY(20px);
}

/* 响应式 */
@media (max-width: 768px) {
  .mo-card__header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .mo-card__meta {
    flex-direction: column;
    gap: 4px;
  }

  .mo-card__footer {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .mo-card__actions {
    width: 100%;
    justify-content: flex-end;
  }

  .mo-detail-grid {
    grid-template-columns: 1fr;
  }

  .mo-detail-product {
    flex-wrap: wrap;
  }
}
</style>
