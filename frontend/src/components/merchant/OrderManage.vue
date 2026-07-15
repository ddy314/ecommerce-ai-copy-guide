<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/** 携带鉴权头的请求头 */
function authHeaders(extra: Record<string, string> = {}): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

// ---------- 类型定义 ----------
type OrderStatus = 'all' | 'pending' | 'paid' | 'shipped' | 'completed' | 'cancelled' | 'returning' | 'returned'

interface OrderItem {
  product_id: number
  product_name: string
  image_url: string | null
  price: number | null
  quantity: number
}

interface AddressSnapshot {
  recipient: string | null
  phone: string | null
  full_address: string | null
}

interface Order {
  id: number
  order_no: string
  user_id: number
  username?: string | null
  status: string
  total_amount: number
  created_at: string
  paid_at: string | null
  shipped_at: string | null
  completed_at: string | null
  cancelled_at: string | null
  items: OrderItem[]
  address_snapshot: AddressSnapshot | null
  tracking_no?: string | null
  return_tracking_no?: string | null
  exchange_tracking_no?: string | null
  return_status?: string | null
  return_reason?: string | null
  return_applied_at?: string | null
  return_completed_at?: string | null
}

interface StatusCounts {
  pending?: number
  paid?: number
  shipped?: number
  completed?: number
  cancelled?: number
  [key: string]: number | undefined
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
const statusCounts = ref<StatusCounts>({})
const searchKeyword = ref('')

// 发货中状态（防止重复点击）
const shippingIds = ref<Set<number>>(new Set())
// 取消中状态
const cancellingIds = ref<Set<number>>(new Set())

// 发货弹窗
const shipModalVisible = ref(false)
const pendingShipOrder = ref<Order | null>(null)
const shipTrackingNo = ref('')

// 取消弹窗
const cancelModalVisible = ref(false)
const pendingCancelOrder = ref<Order | null>(null)

// 退货/换货弹窗
const returnModalVisible = ref(false)
const exchangeModalVisible = ref(false)
const pendingReturnOrder = ref<Order | null>(null)
const pendingExchangeOrder = ref<Order | null>(null)
const exchangeTrackingNo = ref('')

// 退货/换货处理中状态
const returningIds = ref<Set<number>>(new Set())
const exchangingIds = ref<Set<number>>(new Set())

// 提示 Toast
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

// ---------- 状态映射（标签 + 颜色 + 徽章背景） ----------
const statusMap: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: '待付款', color: 'var(--brand)', bg: 'rgba(217, 95, 45, 0.12)' },
  paid: { label: '已付款', color: 'var(--green)', bg: 'rgba(31, 138, 91, 0.12)' },
  shipped: { label: '已发货', color: '#1677ff', bg: 'rgba(22, 119, 255, 0.12)' },
  completed: { label: '已完成', color: 'var(--muted)', bg: 'rgba(118, 107, 94, 0.12)' },
  cancelled: { label: '已取消', color: '#999', bg: 'rgba(153, 153, 153, 0.14)' },
  returning: { label: '退换货中', color: '#faad14', bg: 'rgba(250, 173, 20, 0.14)' },
  returned: { label: '售后完成', color: '#722ed1', bg: 'rgba(114, 46, 209, 0.12)' },
}

function getStatusInfo(status: string): { label: string; color: string; bg: string } {
  return statusMap[status] || { label: status, color: 'var(--muted)', bg: 'rgba(118, 107, 94, 0.12)' }
}

// ---------- 汇总卡片配置 ----------
const summaryCards = computed(() => [
  { key: 'pending' as const, label: '待付款', count: statusCounts.value.pending || 0, color: 'var(--brand)' },
  { key: 'paid' as const, label: '已付款', count: statusCounts.value.paid || 0, color: 'var(--green)' },
  { key: 'shipped' as const, label: '已发货', count: statusCounts.value.shipped || 0, color: '#1677ff' },
  { key: 'returning' as const, label: '退换货中', count: statusCounts.value.returning || 0, color: '#faad14' },
  { key: 'completed' as const, label: '已完成', count: statusCounts.value.completed || 0, color: 'var(--muted)' },
  { key: 'cancelled' as const, label: '已取消', count: statusCounts.value.cancelled || 0, color: '#999' },
])

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
    params.set('page', currentPage.value.toString())
    params.set('page_size', pageSize.value.toString())
    if (activeStatus.value !== 'all') params.set('status', activeStatus.value)
    if (searchKeyword.value.trim()) params.set('keyword', searchKeyword.value.trim())

    const res = await fetch(
      `${API_BASE}/api/merchant/orders?${params.toString()}`,
      { headers: authHeaders() },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    const data = await res.json()
    orders.value = data.orders || []
    total.value = data.total || 0
    totalPages.value = data.total_pages || 1
    statusCounts.value = data.status_counts || {}
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载订单失败'
  } finally {
    loading.value = false
  }
}

function onSearch() {
  currentPage.value = 1
  loadOrders()
}

function clearSearch() {
  searchKeyword.value = ''
  currentPage.value = 1
  loadOrders()
}

// ---------- 切换状态 Tab ----------
function selectStatus(status: OrderStatus) {
  if (activeStatus.value === status) return
  activeStatus.value = status
  currentPage.value = 1
  loadOrders()
}

function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadOrders()
  }
}

// ---------- 发货 ----------
function openShipModal(order: Order) {
  pendingShipOrder.value = order
  shipTrackingNo.value = order.tracking_no || ''
  shipModalVisible.value = true
}

function closeShipModal() {
  shipModalVisible.value = false
  pendingShipOrder.value = null
  shipTrackingNo.value = ''
}

async function executeShipOrder() {
  const order = pendingShipOrder.value
  if (!order) return
  const trackingNo = shipTrackingNo.value.trim()
  if (!trackingNo) {
    showToast('请填写快递单号', 'error')
    return
  }
  closeShipModal()
  if (shippingIds.value.has(order.id)) return
  shippingIds.value.add(order.id)
  try {
    const res = await fetch(
      `${API_BASE}/api/merchant/orders/${order.id}/ship`,
      {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ tracking_no: trackingNo }),
      },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    showToast('发货成功', 'success')
    await loadOrders()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '发货失败', 'error')
  } finally {
    shippingIds.value.delete(order.id)
  }
}

// ---------- 取消订单 ----------
function openCancelModal(order: Order) {
  pendingCancelOrder.value = order
  cancelModalVisible.value = true
}

function closeCancelModal() {
  cancelModalVisible.value = false
  pendingCancelOrder.value = null
}

async function executeCancelOrder() {
  const order = pendingCancelOrder.value
  if (!order) return
  closeCancelModal()
  if (cancellingIds.value.has(order.id)) return
  cancellingIds.value.add(order.id)
  try {
    const res = await fetch(
      `${API_BASE}/api/merchant/orders/${order.id}/cancel`,
      { method: 'POST', headers: authHeaders({ 'Content-Type': 'application/json' }) },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    showToast('订单已取消', 'success')
    await loadOrders()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '取消失败', 'error')
  } finally {
    cancellingIds.value.delete(order.id)
  }
}

// ---------- 退货确认 ----------
function openReturnModal(order: Order) {
  pendingReturnOrder.value = order
  returnModalVisible.value = true
}

function closeReturnModal() {
  returnModalVisible.value = false
  pendingReturnOrder.value = null
}

async function executeConfirmReturn() {
  const order = pendingReturnOrder.value
  if (!order) return
  closeReturnModal()
  if (returningIds.value.has(order.id)) return
  returningIds.value.add(order.id)
  try {
    const res = await fetch(
      `${API_BASE}/api/merchant/orders/${order.id}/confirm-return`,
      { method: 'POST', headers: authHeaders({ 'Content-Type': 'application/json' }) },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    showToast('退货已确认，退款已自动处理', 'success')
    await loadOrders()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '确认退货失败', 'error')
  } finally {
    returningIds.value.delete(order.id)
  }
}

// ---------- 换货确认 ----------
function openExchangeModal(order: Order) {
  pendingExchangeOrder.value = order
  exchangeTrackingNo.value = order.exchange_tracking_no || ''
  exchangeModalVisible.value = true
}

function closeExchangeModal() {
  exchangeModalVisible.value = false
  pendingExchangeOrder.value = null
  exchangeTrackingNo.value = ''
}

async function executeConfirmExchange() {
  const order = pendingExchangeOrder.value
  if (!order) return
  const trackingNo = exchangeTrackingNo.value.trim()
  if (!trackingNo) {
    showToast('请填写新换货物的快递单号', 'error')
    return
  }
  closeExchangeModal()
  if (exchangingIds.value.has(order.id)) return
  exchangingIds.value.add(order.id)
  try {
    const res = await fetch(
      `${API_BASE}/api/merchant/orders/${order.id}/confirm-exchange`,
      {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ tracking_no: trackingNo }),
      },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    showToast('换货已确认，新商品已发货', 'success')
    await loadOrders()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '确认换货失败', 'error')
  } finally {
    exchangingIds.value.delete(order.id)
  }
}

// ---------- 格式化 ----------
function formatPrice(val: number | null | undefined): string {
  if (val === null || val === undefined) return '--'
  return val.toFixed(2)
}

function formatTime(time: string | null | undefined): string {
  if (!time) return '--'
  return time.replace('T', ' ').slice(0, 19)
}

/** 买家信息：优先显示用户名，否则显示用户 ID */
function buyerLabel(order: Order): string {
  if (order.username) return order.username
  return `用户 #${order.user_id}`
}

/** 商品总件数 */
function itemCount(order: Order): number {
  return order.items.reduce((sum, item) => sum + item.quantity, 0)
}

onMounted(() => {
  loadOrders()
})
</script>

<template>
  <div class="om-page">
    <!-- 提示 Toast -->
    <transition name="om-toast">
      <div v-if="toast.visible" :class="['om-toast', `om-toast--${toast.type}`]">
        {{ toast.message }}
      </div>
    </transition>

    <!-- 状态汇总卡片 -->
    <div class="om-summary">
      <div
        v-for="card in summaryCards"
        :key="card.key"
        :class="['om-summary__card', { active: activeStatus === card.key }]"
        @click="selectStatus(card.key)"
      >
        <span class="om-summary__count" :style="{ color: card.color }">{{ card.count }}</span>
        <span class="om-summary__label">{{ card.label }}</span>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="om-search-bar">
      <input
        v-model="searchKeyword"
        type="text"
        class="om-search-input"
        placeholder="搜索订单号 / 买家用户名 / 用户ID"
        @keydown.enter="onSearch"
      />
      <button class="om-btn om-btn--primary" @click="onSearch">搜索</button>
      <button v-if="searchKeyword" class="om-btn om-btn--ghost" @click="clearSearch">清空</button>
    </div>

    <!-- 状态筛选 Tab -->
    <div class="om-tabs">
      <button
        v-for="tab in statusTabs"
        :key="tab.key"
        :class="['om-tab', { active: activeStatus === tab.key }]"
        @click="selectStatus(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="om-error">{{ error }}</div>

    <!-- 加载中 -->
    <div v-if="loading" class="om-loading">
      <div class="om-spinner"></div>
      <p>正在加载订单...</p>
    </div>

    <!-- 订单列表 -->
    <div v-else-if="orders.length > 0" class="om-list">
      <div v-for="order in orders" :key="order.id" class="om-card">
        <!-- 卡片头部：订单号、时间、状态 -->
        <div class="om-card__header">
          <div class="om-card__meta">
            <span class="om-card__no">订单号：{{ order.order_no }}</span>
            <span class="om-card__time">{{ formatTime(order.created_at) }}</span>
          </div>
          <span
            class="om-card__status"
            :style="{ color: getStatusInfo(order.status).color, background: getStatusInfo(order.status).bg }"
          >
            {{ getStatusInfo(order.status).label }}
          </span>
        </div>

        <!-- 买家信息 + 收货地址 -->
        <div class="om-card__buyer">
          <div class="om-card__buyer-item">
            <span class="om-card__buyer-label">买家</span>
            <span class="om-card__buyer-value">{{ buyerLabel(order) }}</span>
          </div>
          <template v-if="order.address_snapshot">
            <div class="om-card__buyer-item">
              <span class="om-card__buyer-label">收货人</span>
              <span class="om-card__buyer-value">{{ order.address_snapshot.recipient || '--' }}</span>
            </div>
            <div class="om-card__buyer-item">
              <span class="om-card__buyer-label">电话</span>
              <span class="om-card__buyer-value">{{ order.address_snapshot.phone || '--' }}</span>
            </div>
            <div class="om-card__buyer-item om-card__buyer-item--full">
              <span class="om-card__buyer-label">地址</span>
              <span class="om-card__buyer-value">{{ order.address_snapshot.full_address || '--' }}</span>
            </div>
          </template>
        </div>

        <!-- 商品列表 -->
        <div class="om-card__items">
          <div
            v-for="(item, idx) in order.items"
            :key="idx"
            class="om-card__item"
          >
            <div class="om-card__item-image">
              <img
                v-if="item.image_url"
                :src="item.image_url"
                :alt="item.product_name"
                @error="(e: any) => e.target.style.display = 'none'"
              />
              <div v-else class="om-card__item-noimg">无图</div>
            </div>
            <div class="om-card__item-info">
              <span class="om-card__item-name" :title="item.product_name">{{ item.product_name }}</span>
              <span class="om-card__item-price">¥{{ formatPrice(item.price) }} × {{ item.quantity }}</span>
            </div>
          </div>
          <div v-if="order.items.length === 0" class="om-card__items-empty">暂无商品信息</div>
        </div>

        <!-- 卡片底部：合计 + 操作 -->
        <div class="om-card__footer">
          <div class="om-card__total">
            <div>共 {{ itemCount(order) }} 件商品，合计：<strong>¥{{ formatPrice(order.total_amount) }}</strong></div>
            <div v-if="order.return_reason || order.return_applied_at" class="om-card__aftersale">
              <div v-if="order.return_reason" class="om-card__aftersale-reason">
                退换原因：{{ order.return_reason }}
              </div>
              <div v-if="order.return_applied_at" class="om-card__aftersale-time">
                申请时间：{{ formatTime(order.return_applied_at) }}
              </div>
            </div>
            <div v-if="order.tracking_no" class="om-card__tracking">
              快递单号：{{ order.tracking_no }}
            </div>
            <div v-if="order.return_tracking_no" class="om-card__tracking om-card__tracking--return">
              退货单号：{{ order.return_tracking_no }}
            </div>
            <div v-if="order.exchange_tracking_no" class="om-card__tracking om-card__tracking--exchange">
              换货单号：{{ order.exchange_tracking_no }}
            </div>
          </div>
          <div class="om-card__actions">
            <button
              v-if="order.status === 'paid'"
              class="om-btn om-btn--primary"
              :disabled="shippingIds.has(order.id)"
              @click="openShipModal(order)"
            >
              {{ shippingIds.has(order.id) ? '发货中...' : '发货' }}
            </button>
            <template v-if="order.status === 'returning' && order.return_status === 'returning'">
              <button
                class="om-btn om-btn--danger"
                :disabled="returningIds.has(order.id)"
                @click="openReturnModal(order)"
              >
                {{ returningIds.has(order.id) ? '处理中...' : '确认退货' }}
              </button>
              <button
                class="om-btn om-btn--warning"
                :disabled="exchangingIds.has(order.id)"
                @click="openExchangeModal(order)"
              >
                {{ exchangingIds.has(order.id) ? '处理中...' : '确认换货' }}
              </button>
            </template>
            <button
              v-if="!['completed', 'cancelled', 'returned', 'returning'].includes(order.status)"
              class="om-btn om-btn--danger"
              :disabled="cancellingIds.has(order.id)"
              @click="openCancelModal(order)"
            >
              {{ cancellingIds.has(order.id) ? '取消中...' : '取消订单' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="om-pagination">
        <button
          class="om-page-btn"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          上一页
        </button>
        <button
          v-for="page in pageNumbers"
          :key="page"
          :class="['om-page-btn', { active: page === currentPage }]"
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
        <button
          class="om-page-btn"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          下一页
        </button>
        <span class="om-page-info">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条</span>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="om-empty">
      <div class="om-empty__icon">单</div>
      <h3>暂无订单</h3>
      <p>当前状态下还没有订单数据</p>
    </div>

    <!-- 发货弹窗 -->
    <transition name="om-modal">
      <div v-if="shipModalVisible" class="om-modal-overlay" @click.self="closeShipModal">
        <div class="om-modal om-modal--sm">
          <div class="om-modal__header">
            <h2>填写快递单号</h2>
            <button class="om-modal__close" @click="closeShipModal">×</button>
          </div>
          <div class="om-modal__body">
            <div class="om-form-group">
              <label>订单号</label>
              <div class="om-form-static">{{ pendingShipOrder?.order_no }}</div>
            </div>
            <div class="om-form-group">
              <label>快递公司 / 快递单号 <span class="om-required">*</span></label>
              <input
                v-model="shipTrackingNo"
                type="text"
                placeholder="例如：顺丰 SF1234567890"
                @keydown.enter="executeShipOrder"
              />
            </div>
            <div class="om-confirm-actions">
              <button class="om-btn om-btn--ghost" @click="closeShipModal">取消</button>
              <button class="om-btn om-btn--primary" :disabled="!shipTrackingNo.trim()" @click="executeShipOrder">确认发货</button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 取消订单弹窗 -->
    <transition name="om-modal">
      <div v-if="cancelModalVisible" class="om-modal-overlay" @click.self="closeCancelModal">
        <div class="om-modal om-modal--sm">
          <div class="om-modal__header">
            <h2>取消订单</h2>
            <button class="om-modal__close" @click="closeCancelModal">×</button>
          </div>
          <div class="om-modal__body">
            <div class="om-confirm-body">
              <div class="om-confirm-icon om-confirm-icon--warning">!</div>
              <p class="om-confirm-text">确定要取消该订单吗？</p>
              <p class="om-confirm-hint">订单取消后将无法恢复，已支付金额将按原路退回。</p>
              <div v-if="pendingCancelOrder" class="om-cancel-order-info">
                <span>订单号：{{ pendingCancelOrder.order_no }}</span>
                <span>合计：<strong>¥{{ formatPrice(pendingCancelOrder.total_amount) }}</strong></span>
              </div>
            </div>
            <div class="om-confirm-actions">
              <button class="om-btn om-btn--ghost" @click="closeCancelModal">再想想</button>
              <button class="om-btn om-btn--danger" @click="executeCancelOrder">确认取消</button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 确认退货弹窗 -->
    <transition name="om-modal">
      <div v-if="returnModalVisible" class="om-modal-overlay" @click.self="closeReturnModal">
        <div class="om-modal om-modal--sm">
          <div class="om-modal__header">
            <h2>确认退货并退款</h2>
            <button class="om-modal__close" @click="closeReturnModal">×</button>
          </div>
          <div class="om-modal__body">
            <div class="om-confirm-body">
              <div class="om-confirm-icon om-confirm-icon--danger">↺</div>
              <p class="om-confirm-text">确定同意该退货申请吗？</p>
              <p class="om-confirm-hint">确认后系统将自动按原支付方式退款给用户，订单进入售后完成状态。</p>
              <div v-if="pendingReturnOrder" class="om-cancel-order-info">
                <span>订单号：{{ pendingReturnOrder.order_no }}</span>
                <span>退货单号：{{ pendingReturnOrder.return_tracking_no || '--' }}</span>
                <span>退款金额：<strong>¥{{ formatPrice(pendingReturnOrder.total_amount) }}</strong></span>
              </div>
            </div>
            <div class="om-confirm-actions">
              <button class="om-btn om-btn--ghost" @click="closeReturnModal">再想想</button>
              <button
                class="om-btn om-btn--danger"
                :disabled="returningIds.has(pendingReturnOrder?.id ?? -1)"
                @click="executeConfirmReturn"
              >
                {{ returningIds.has(pendingReturnOrder?.id ?? -1) ? '处理中...' : '确认退货并退款' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 确认换货弹窗 -->
    <transition name="om-modal">
      <div v-if="exchangeModalVisible" class="om-modal-overlay" @click.self="closeExchangeModal">
        <div class="om-modal om-modal--sm">
          <div class="om-modal__header">
            <h2>确认换货并发货</h2>
            <button class="om-modal__close" @click="closeExchangeModal">×</button>
          </div>
          <div class="om-modal__body">
            <div class="om-form-group">
              <label>订单号</label>
              <div class="om-form-static">{{ pendingExchangeOrder?.order_no }}</div>
            </div>
            <div class="om-form-group">
              <label>新换货快递单号 <span class="om-required">*</span></label>
              <input
                v-model="exchangeTrackingNo"
                type="text"
                placeholder="例如：顺丰 SF1234567890"
                @keydown.enter="executeConfirmExchange"
              />
            </div>
            <div class="om-confirm-hint" style="margin-top: -8px; margin-bottom: 18px;">
              确认后订单将重新进入已发货状态，用户可正常确认收货。
            </div>
            <div class="om-confirm-actions">
              <button class="om-btn om-btn--ghost" @click="closeExchangeModal">取消</button>
              <button
                class="om-btn om-btn--warning"
                :disabled="!exchangeTrackingNo.trim() || exchangingIds.has(pendingExchangeOrder?.id ?? -1)"
                @click="executeConfirmExchange"
              >
                {{ exchangingIds.has(pendingExchangeOrder?.id ?? -1) ? '处理中...' : '确认换货' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.om-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
}

/* Toast */
.om-toast {
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

.om-toast--success {
  background: var(--green);
}

.om-toast--error {
  background: var(--brand);
}

.om-toast-enter-active,
.om-toast-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.om-toast-enter-from,
.om-toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}

/* 状态汇总卡片 */
.om-summary {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.om-summary__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
  cursor: pointer;
  transition: all 0.2s;
}

.om-summary__card:hover {
  border-color: var(--brand);
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
}

.om-summary__card.active {
  border-color: var(--brand);
  box-shadow: 0 0 0 1px var(--brand) inset;
  background: rgba(217, 95, 45, 0.04);
}

.om-summary__count {
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
}

.om-summary__label {
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
}

/* 状态 Tab */
.om-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid var(--line);
  overflow-x: auto;
}

.om-tab {
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

.om-tab:hover {
  color: var(--brand);
}

.om-tab.active {
  color: var(--brand);
  border-bottom-color: var(--brand);
  font-weight: 700;
}

/* 加载 */
.om-loading {
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}

.om-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: om-spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes om-spin {
  to {
    transform: rotate(360deg);
  }
}

/* 错误 */
.om-error {
  background: #fff0f0;
  color: #c33;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
}

/* 订单列表 */
.om-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.om-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.om-card:hover {
  border-color: rgba(217, 95, 45, 0.4);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

/* 卡片头部 */
.om-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: rgba(217, 95, 45, 0.03);
  border-bottom: 1px solid var(--line);
}

.om-card__meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.om-card__no {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.om-card__time {
  font-size: 13px;
  color: var(--muted);
}

.om-card__status {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

/* 买家信息 */
.om-card__buyer {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px 20px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--line);
  background: rgba(0, 0, 0, 0.015);
}

.om-card__buyer-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.om-card__buyer-item--full {
  grid-column: 1 / -1;
}

.om-card__buyer-label {
  font-size: 12px;
  color: var(--muted);
}

.om-card__buyer-value {
  font-size: 13px;
  color: var(--ink);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 商品列表 */
.om-card__items {
  padding: 16px 20px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.om-card__items-empty {
  grid-column: 1 / -1;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
  padding: 12px 0;
}

.om-card__item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255, 252, 246, 0.5);
}

.om-card__item-image {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f4ef;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.om-card__item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.om-card__item-noimg {
  font-size: 11px;
  color: var(--muted);
}

.om-card__item-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
  min-width: 0;
}

.om-card__item-name {
  font-size: 13px;
  color: var(--ink);
  font-weight: 500;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.om-card__item-price {
  font-size: 12px;
  color: var(--muted);
}

/* 卡片底部 */
.om-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-top: 1px solid var(--line);
  background: rgba(217, 95, 45, 0.02);
  gap: 12px;
  flex-wrap: wrap;
}

.om-card__total {
  font-size: 14px;
  color: var(--muted);
}

.om-card__total strong {
  font-size: 18px;
  color: var(--brand);
  font-weight: 800;
}

.om-card__tracking {
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
}

.om-card__tracking--return {
  color: #faad14;
}

.om-card__tracking--exchange {
  color: #1677ff;
}

.om-card__aftersale {
  margin-top: 6px;
  padding: 8px 10px;
  background: rgba(250, 173, 20, 0.08);
  border-radius: 8px;
  font-size: 12px;
  color: var(--ink);
  line-height: 1.6;
}

.om-card__aftersale-reason {
  font-weight: 600;
}

.om-card__aftersale-time {
  color: var(--muted);
}

.om-card__actions {
  display: flex;
  gap: 10px;
}

/* 按钮 */
.om-btn {
  padding: 8px 22px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.om-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.om-btn--primary {
  color: #fff;
  background: var(--brand);
  border-color: var(--brand);
}

.om-btn--primary:hover:not(:disabled) {
  background: var(--brand-dark);
  border-color: var(--brand-dark);
}

.om-btn--danger {
  color: #fff;
  background: #c33;
  border-color: #c33;
}

.om-btn--danger:hover:not(:disabled) {
  background: #a52a2a;
  border-color: #a52a2a;
}

.om-btn--warning {
  color: #fff;
  background: #faad14;
  border-color: #faad14;
}

.om-btn--warning:hover:not(:disabled) {
  background: #d48806;
  border-color: #d48806;
}

/* 搜索栏 */
.om-search-bar {
  display: flex;
  gap: 10px;
  align-items: center;
}

.om-search-input {
  flex: 1;
  min-width: 0;
  padding: 10px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 14px;
  background: var(--panel);
  color: var(--ink);
}

.om-search-input:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

/* 空状态 */
.om-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}

.om-empty__icon {
  display: inline-grid;
  width: 72px;
  height: 72px;
  place-items: center;
  border-radius: 20px;
  margin-bottom: 20px;
  font-size: 30px;
  font-weight: 800;
  color: #fffaf0;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
}

.om-empty h3 {
  font-size: 20px;
  color: var(--ink);
  margin: 0 0 8px;
}

.om-empty p {
  font-size: 14px;
  margin: 0;
}

/* 分页 */
.om-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.om-page-btn {
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--ink);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.om-page-btn:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand);
}

.om-page-btn.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.om-page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.om-page-info {
  margin-left: 12px;
  font-size: 13px;
  color: var(--muted);
}

/* 弹窗 */
.om-modal-overlay {
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

.om-modal {
  width: min(520px, 100%);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.3);
}

.om-modal--sm {
  width: min(420px, 100%);
}

.om-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--line);
}

.om-modal__header h2 {
  font-size: 18px;
  margin: 0;
}

.om-modal__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.06);
  font-size: 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.om-modal__close:hover {
  background: rgba(0, 0, 0, 0.14);
}

.om-modal__body {
  padding: 24px;
  overflow-y: auto;
}

.om-form-group {
  margin-bottom: 18px;
}

.om-form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 8px;
}

.om-form-group input {
  width: 100%;
  padding: 11px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  background: #fff;
  box-sizing: border-box;
}

.om-form-group input:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

.om-form-static {
  padding: 11px 14px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 10px;
  font-size: 14px;
  color: var(--muted);
}

.om-required {
  color: #c33;
}

.om-confirm-body {
  text-align: center;
  padding: 8px 8px 24px;
}

.om-confirm-icon {
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

.om-confirm-icon--warning {
  background: linear-gradient(135deg, #faad14, #f59e0b);
  box-shadow: 0 12px 30px rgba(250, 173, 20, 0.25);
}

.om-confirm-icon--danger {
  background: linear-gradient(135deg, #c33, #a52a2a);
  box-shadow: 0 12px 30px rgba(204, 51, 51, 0.25);
}

.om-confirm-text {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink);
  margin: 0 0 8px;
}

.om-confirm-hint {
  font-size: 13px;
  color: var(--muted);
  margin: 0;
  line-height: 1.6;
}

.om-confirm-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

.om-cancel-order-info {
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

.om-cancel-order-info strong {
  color: var(--brand);
  font-size: 15px;
}

.om-modal-enter-active,
.om-modal-leave-active {
  transition: opacity 0.25s;
}

.om-modal-enter-active .om-modal,
.om-modal-leave-active .om-modal {
  transition: transform 0.25s;
}

.om-modal-enter-from,
.om-modal-leave-to {
  opacity: 0;
}

.om-modal-enter-from .om-modal,
.om-modal-leave-to .om-modal {
  transform: scale(0.95) translateY(20px);
}

/* 响应式 */
@media (max-width: 900px) {
  .om-summary {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .om-card__header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .om-card__buyer {
    grid-template-columns: 1fr 1fr;
  }

  .om-card__footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .om-card__actions {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 560px) {
  .om-summary {
    grid-template-columns: repeat(2, 1fr);
  }

  .om-card__buyer {
    grid-template-columns: 1fr;
  }
}
</style>
