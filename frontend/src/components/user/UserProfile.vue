<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject, provide, nextTick } from 'vue'
import {
  ShoppingCartIcon,
  ClipboardDocumentListIcon,
  MapPinIcon,
  HeartIcon,
  ClockIcon,
  CameraIcon,
  PencilIcon,
  TrashIcon,
  StarIcon,
  EnvelopeIcon,
  PhoneIcon,
  UserIcon,
  CalendarDaysIcon,
  SparklesIcon,
  PlusIcon,
  XMarkIcon,
  MinusIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/vue/24/outline'
import ShoppingCart from './ShoppingCart.vue'
import MyOrders from './MyOrders.vue'
import CheckoutModal, { type CheckoutItem } from './CheckoutModal.vue'
import { resolveAvatarUrl } from '../../utils/avatar'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// ---------- 类型定义 ----------
interface UserInfo {
  id: number
  username: string
  nickname: string
  phone: string
  email: string
  avatar: string | null
  role: string
  created_at: string
}

interface Address {
  id: number
  recipient: string
  phone: string
  province: string
  city: string
  district: string
  detail: string
  is_default: boolean
}

interface FavoriteProduct {
  id: number
  name: string
  image_url: string | null
  price: number | null
  category: string | null
  favorited_at: string
  product_id: number
}

interface HistoryProduct {
  id: number
  name: string
  image_url: string | null
  price: number | null
  category: string | null
  viewed_at: string
  product_id: number
}

// ---------- 导航 ----------
const navigateToCustomerService = inject<(productId?: number) => void>('navigateToCustomerService', () => {})

// ---------- 商品详情弹窗（内嵌在个人中心，不跳转商品浏览页） ----------
interface ProductDetail {
  id: number
  name: string
  category: string
  price: number | null
  brand: string | null
  selling_points: string | null
  image_url: string | null
  image_urls?: string[]
  original_price?: number | null
  rating?: number | null
  review_count?: number
  sales_count?: number | null
  specs?: string | Record<string, string> | null
  description?: string | null
  stock?: number | null
  platform?: string
  reviews?: Array<{
    id: number
    user_name: string
    rating: number
    content: string
    created_at: string
    image_urls?: string[]
    videos?: string[]
  }>
}

const detailVisible = ref(false)
const detailLoading = ref(false)
const detailError = ref<string | null>(null)
const detailProduct = ref<ProductDetail | null>(null)
const detailQuantity = ref(1)
const isFavorited = ref(false)
const activeImageUrl = ref('')
const checkoutVisible = ref(false)
const checkoutItems = ref<CheckoutItem[]>([])

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

async function openProductDetail(productId: number) {
  if (!productId || productId <= 0) {
    detailVisible.value = true
    detailError.value = '无效的商品ID'
    showToast('无效的商品ID', 'error')
    return
  }
  detailVisible.value = true
  detailLoading.value = true
  detailError.value = null
  detailProduct.value = null
  detailQuantity.value = 1
  isFavorited.value = false
  activeImageUrl.value = ''
  nextTick(() => window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }))
  try {
    const response = await fetch(`${API_BASE}/api/products/${productId}`, { headers: authHeaders() })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    const data = await response.json()
    detailProduct.value = data.product || data
    isFavorited.value = data.is_favorited || false
    const imgs = galleryImages.value
    activeImageUrl.value = imgs[0] || ''
  } catch (e) {
    detailError.value = e instanceof Error ? e.message : '加载失败'
    showToast('商品详情加载失败：' + detailError.value, 'error')
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detailVisible.value = false
  detailProduct.value = null
  detailError.value = null
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

function increaseQty() { detailQuantity.value++ }
function decreaseQty() { if (detailQuantity.value > 1) detailQuantity.value-- }

async function addToCartFromDetail() {
  if (!detailProduct.value) return
  try {
    const response = await fetch(`${API_BASE}/api/user/cart`, {
      method: 'POST', headers: authHeaders(),
      body: JSON.stringify({ product_id: detailProduct.value.id, quantity: detailQuantity.value }),
    })
    if (!response.ok) { const err = await response.json().catch(() => ({})); throw new Error(err.message || `HTTP ${response.status}`) }
    showToast('已加入购物车')
  } catch (e) { showToast(e instanceof Error ? e.message : '加入购物车失败', 'error') }
}

function handleBuyNow() {
  if (!detailProduct.value) return
  const p = detailProduct.value
  checkoutItems.value = [{
    product_id: p.id, product_name: p.name, product_image: p.image_url || null,
    product_price: p.price, product_category: p.category || null, quantity: detailQuantity.value,
  }]
  checkoutVisible.value = true
}

function closeCheckout() { checkoutVisible.value = false }

function onCheckoutSuccess() {
  checkoutVisible.value = false
  closeDetail()
  showToast('下单成功！')
}

async function toggleFavoriteDetail() {
  if (!detailProduct.value) return
  const productId = detailProduct.value.id
  try {
    const response = await fetch(`${API_BASE}/api/user/favorites/${productId}`, { method: 'POST', headers: authHeaders() })
    if (!response.ok) { const err = await response.json().catch(() => ({})); throw new Error(err.message || `HTTP ${response.status}`) }
    isFavorited.value = !isFavorited.value
    showToast(isFavorited.value ? '已收藏' : '已取消收藏')
    if (!isFavorited.value) {
      favorites.value = favorites.value.filter((f) => (f.product_id || f.id) !== productId)
    }
  } catch (e) { showToast(e instanceof Error ? e.message : '收藏操作失败', 'error') }
}

function handleAskCustomerService() {
  if (!detailProduct.value) return
  const productId = detailProduct.value.id
  closeDetail()
  navigateToCustomerService(productId)
}

// ---------- 装饰球动画 ----------
const orbPositions = ref([
  { x: 15, y: 20, s: 0.6, d: 8 },
  { x: 75, y: 35, s: 0.4, d: 12 },
  { x: 45, y: 70, s: 0.5, d: 10 },
  { x: 85, y: 15, s: 0.3, d: 14 },
])
let orbTimer: ReturnType<typeof setInterval> | null = null

// ---------- 状态 ----------
const loading = ref(true)
const userInfo = ref<UserInfo | null>(null)
const activeTab = ref<'favorites' | 'history' | 'cart' | 'orders'>('favorites')
const editVisible = ref(false)
const editForm = ref({ nickname: '', phone: '', email: '' })
const editLoading = ref(false)
const avatarInput = ref<HTMLInputElement | null>(null)
const avatarLoading = ref(false)
const addresses = ref<Address[]>([])
const addressModalVisible = ref(false)
const addressEditMode = ref<'add' | 'edit'>('add')
const addressForm = ref<Address>({
  id: 0, recipient: '', phone: '', province: '', city: '', district: '', detail: '', is_default: false,
})
const addressLoading = ref(false)
const favorites = ref<FavoriteProduct[]>([])
const history = ref<HistoryProduct[]>([])
const toast = ref<{ visible: boolean; message: string; type: 'success' | 'error' }>({ visible: false, message: '', type: 'success' })
let toastTimer: ReturnType<typeof setTimeout> | null = null

// 统计数据
const stats = computed(() => ({
  favorites: favorites.value.length,
  history: history.value.length,
  addresses: addresses.value.length,
}))

// 计算注册天数
const daysSinceJoined = computed(() => {
  if (!userInfo.value?.created_at) return 0
  const created = new Date(userInfo.value.created_at)
  const now = new Date()
  return Math.max(1, Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24)))
})

provide('switchToOrdersTab', () => { activeTab.value = 'orders' })

// ---------- 提示 ----------
function showToast(message: string, type: 'success' | 'error' = 'success') {
  toast.value = { visible: true, message, type }
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value.visible = false }, 2500)
}

// ---------- 请求头 ----------
function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

// ---------- 加载用户信息 ----------
async function loadUserInfo() {
  loading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders() })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    userInfo.value = data.user || data
  } catch {
    const stored = localStorage.getItem('userInfo')
    if (stored) {
      try {
        const info = JSON.parse(stored)
        userInfo.value = {
          id: 0, username: info.username || '', nickname: info.nickname || info.username || '',
          phone: info.phone || '', email: info.email || '', avatar: info.avatar || null,
          role: info.role || 'user', created_at: info.created_at || '',
        }
      } catch { /* ignore */ }
    }
  } finally {
    loading.value = false
  }
}

// ---------- 头像上传 ----------
function triggerAvatarUpload() { avatarInput.value?.click() }

async function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  avatarLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_BASE}/api/auth/avatar`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!response.ok) { const err = await response.json().catch(() => ({})); throw new Error(err.message || `HTTP ${response.status}`) }
    const data = await response.json()
    const updatedUser = data.user || { ...userInfo.value, avatar: data.avatar }
    userInfo.value = updatedUser
    const stored = localStorage.getItem('userInfo')
    if (stored) {
      const info = JSON.parse(stored)
      info.avatar = updatedUser.avatar || data.avatar || info.avatar
      localStorage.setItem('userInfo', JSON.stringify(info))
    }
    showToast('头像上传成功')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '头像上传失败', 'error')
  } finally {
    avatarLoading.value = false
    if (input) input.value = ''
  }
}

// ---------- 编辑资料 ----------
function openEditModal() {
  if (userInfo.value) {
    editForm.value = { nickname: userInfo.value.nickname || '', phone: userInfo.value.phone || '', email: userInfo.value.email || '' }
  }
  editVisible.value = true
}

async function saveProfile() {
  editLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/auth/profile`, {
      method: 'PUT', headers: authHeaders(), body: JSON.stringify(editForm.value),
    })
    if (!response.ok) { const err = await response.json().catch(() => ({})); throw new Error(err.message || `HTTP ${response.status}`) }
    const data = await response.json()
    const updatedUser = data.user || { ...userInfo.value, ...editForm.value }
    userInfo.value = updatedUser
    const stored = localStorage.getItem('userInfo')
    if (stored) {
      const info = JSON.parse(stored)
      info.nickname = updatedUser.nickname || editForm.value.nickname
      info.phone = updatedUser.phone || editForm.value.phone || info.phone
      info.email = updatedUser.email || editForm.value.email || info.email
      localStorage.setItem('userInfo', JSON.stringify(info))
    }
    showToast('资料修改成功')
    editVisible.value = false
  } catch (e) {
    showToast(e instanceof Error ? e.message : '修改失败', 'error')
  } finally { editLoading.value = false }
}

// ---------- 地址管理 ----------
async function loadAddresses() {
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses`, { headers: authHeaders() })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    addresses.value = data.addresses || data || []
  } catch { /* 静默失败 */ }
}

function openAddressModal(mode: 'add' | 'edit', addr?: Address) {
  addressEditMode.value = mode
  if (mode === 'edit' && addr) {
    addressForm.value = { ...addr }
  } else {
    addressForm.value = { id: 0, recipient: '', phone: '', province: '', city: '', district: '', detail: '', is_default: false }
  }
  addressModalVisible.value = true
}

async function saveAddress() {
  if (!addressForm.value.recipient || !addressForm.value.phone || !addressForm.value.detail) {
    showToast('请填写完整收货信息', 'error'); return
  }
  addressLoading.value = true
  try {
    const url = addressEditMode.value === 'add' ? `${API_BASE}/api/user/addresses` : `${API_BASE}/api/user/addresses/${addressForm.value.id}`
    const method = addressEditMode.value === 'add' ? 'POST' : 'PUT'
    const response = await fetch(url, { method, headers: authHeaders(), body: JSON.stringify(addressForm.value) })
    if (!response.ok) { const err = await response.json().catch(() => ({})); throw new Error(err.message || `HTTP ${response.status}`) }
    showToast(addressEditMode.value === 'add' ? '地址添加成功' : '地址修改成功')
    addressModalVisible.value = false
    await loadAddresses()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '保存地址失败', 'error')
  } finally { addressLoading.value = false }
}

async function deleteAddress(addr: Address) {
  if (!confirm('确定要删除该地址吗？')) return
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses/${addr.id}`, { method: 'DELETE', headers: authHeaders() })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    showToast('地址已删除')
    await loadAddresses()
  } catch (e) { showToast(e instanceof Error ? e.message : '删除失败', 'error') }
}

async function setDefaultAddress(addr: Address) {
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses/${addr.id}`, {
      method: 'PUT', headers: authHeaders(), body: JSON.stringify({ ...addr, is_default: true }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    showToast('已设为默认地址')
    await loadAddresses()
  } catch (e) { showToast(e instanceof Error ? e.message : '设置失败', 'error') }
}

// ---------- 收藏 ----------
async function loadFavorites() {
  try {
    const response = await fetch(`${API_BASE}/api/user/favorites`, { headers: authHeaders() })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    favorites.value = data.favorites || data || []
  } catch { /* 静默失败 */ }
}

async function removeFavorite(item: FavoriteProduct) {
  if (!confirm('确定要取消收藏该商品吗？')) return
  try {
    const productId = item.product_id
    const response = await fetch(`${API_BASE}/api/user/favorites/${productId}`, { method: 'POST', headers: authHeaders() })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    showToast('已取消收藏')
    favorites.value = favorites.value.filter((f) => f.product_id !== productId)
  } catch (e) { showToast(e instanceof Error ? e.message : '取消收藏失败', 'error') }
}

// ---------- 浏览记录 ----------
async function loadHistory() {
  try {
    const response = await fetch(`${API_BASE}/api/user/history`, { headers: authHeaders() })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    history.value = data.history || data || []
  } catch { /* 静默失败 */ }
}

// ---------- 格式化 ----------
function formatPrice(price: number | null | undefined): string {
  if (price == null) return '--'
  return price.toFixed(2)
}

function formatTime(time: string): string {
  if (!time) return '--'
  return time.replace('T', ' ').slice(0, 19)
}

function getAvatarChar(): string {
  if (userInfo.value?.nickname) return userInfo.value.nickname.charAt(0)
  if (userInfo.value?.username) return userInfo.value.username.charAt(0)
  return 'U'
}

// Tab 列表
const tabs = [
  { key: 'favorites' as const, label: '我的收藏', count: computed(() => favorites.value.length), icon: HeartIcon },
  { key: 'history' as const, label: '浏览记录', count: computed(() => history.value.length), icon: ClockIcon },
  { key: 'cart' as const, label: '购物车', count: computed(() => null), icon: ShoppingCartIcon },
  { key: 'orders' as const, label: '我的订单', count: computed(() => null), icon: ClipboardDocumentListIcon },
]

onMounted(() => {
  loadUserInfo()
  loadAddresses()
  loadFavorites()
  loadHistory()
  let t = 0
  orbTimer = setInterval(() => {
    t += 0.015
    orbPositions.value = orbPositions.value.map((o, i) => ({
      ...o,
      x: o.x + Math.sin(t * (0.7 + i * 0.3)) * 0.8,
      y: o.y + Math.cos(t * (0.6 + i * 0.4)) * 0.6,
    }))
  }, 50)
})

onUnmounted(() => {
  if (orbTimer) clearInterval(orbTimer)
})
</script>

<template>
  <div class="relative space-y-6 animate-fade-in-up">
    <!-- Toast -->
    <transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div
        v-if="toast.visible"
        :class="[
          'fixed top-20 left-1/2 -translate-x-1/2 z-50 px-6 py-2.5 rounded-full text-sm font-semibold text-white shadow-lg backdrop-blur-sm',
          toast.type === 'success' ? 'bg-emerald-500/90' : 'bg-rose-500/90',
        ]"
      >
        {{ toast.message }}
      </div>
    </transition>

    <!-- 加载中 -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-32 text-gray-400">
      <div class="relative">
        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-accent-blue animate-pulse"></div>
        <div class="absolute inset-0 rounded-2xl border-2 border-primary animate-ping opacity-20"></div>
      </div>
      <p class="mt-5 text-sm font-medium">正在加载个人中心...</p>
    </div>

    <template v-else-if="userInfo">
      <!-- ==================== 个人信息头部 ==================== -->
      <div class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary via-primary to-accent-blue shadow-xl shadow-primary/20">
        <!-- 装饰球 -->
        <div
          v-for="(orb, i) in orbPositions"
          :key="i"
          class="absolute w-24 h-24 rounded-full bg-white/10 blur-2xl pointer-events-none"
          :style="{
            left: orb.x + '%',
            top: orb.y + '%',
            width: (orb.s * 160) + 'px',
            height: (orb.s * 160) + 'px',
            transitionDuration: (orb.d * 100) + 'ms',
          }"
        ></div>
        <!-- 背景网格 -->
        <div class="absolute inset-0 opacity-5" style="background-image: radial-gradient(circle, #fff 1px, transparent 1px); background-size: 24px 24px;"></div>

        <div class="relative z-10 p-6 sm:p-8">
          <div class="flex flex-col sm:flex-row items-center sm:items-start gap-6">
            <!-- 头像 -->
            <div class="relative shrink-0 group">
              <div class="relative">
                <div class="absolute -inset-1 rounded-full bg-white/30 blur-md animate-pulse"></div>
                <div class="w-28 h-28 rounded-full overflow-hidden ring-4 ring-white/40 shadow-2xl relative">
                  <img
                    v-if="userInfo.avatar"
                    :src="resolveAvatarUrl(userInfo.avatar)"
                    :alt="userInfo.nickname"
                    class="w-full h-full object-cover"
                  />
                  <div
                    v-else
                    class="w-full h-full bg-gradient-to-br from-white/20 to-white/5 flex items-center justify-center text-4xl font-extrabold text-white"
                  >
                    {{ getAvatarChar().toUpperCase() }}
                  </div>
                </div>
                <button
                  @click="triggerAvatarUpload"
                  :disabled="avatarLoading"
                  class="absolute -bottom-1 -right-1 w-10 h-10 rounded-full bg-white text-primary flex items-center justify-center shadow-lg hover:scale-110 transition-transform disabled:opacity-60"
                >
                  <CameraIcon class="w-5 h-5" />
                </button>
              </div>
              <div
                v-if="avatarLoading"
                class="absolute inset-0 rounded-full flex items-center justify-center bg-black/40 text-white text-xs font-semibold backdrop-blur-sm"
              >
                上传中
              </div>
              <input ref="avatarInput" type="file" accept="image/*" class="hidden" @change="handleAvatarChange" />
            </div>

            <!-- 信息 -->
            <div class="flex-1 text-center sm:text-left">
              <div class="flex items-center justify-center sm:justify-start gap-2">
                <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {{ userInfo.nickname || userInfo.username }}
                </h1>
                <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white/20 text-white text-xs font-medium backdrop-blur-sm">
                  <SparklesIcon class="w-3 h-3" />
                  会员
                </span>
              </div>
              <p class="text-white/70 text-sm mt-1 flex items-center justify-center sm:justify-start gap-2">
                <UserIcon class="w-3.5 h-3.5" />
                @{{ userInfo.username }}
              </p>
              <div class="flex flex-wrap items-center justify-center sm:justify-start gap-4 mt-3 text-white/80 text-xs">
                <span v-if="userInfo.phone" class="inline-flex items-center gap-1">
                  <PhoneIcon class="w-3.5 h-3.5" /> {{ userInfo.phone }}
                </span>
                <span v-if="userInfo.email" class="inline-flex items-center gap-1">
                  <EnvelopeIcon class="w-3.5 h-3.5" /> {{ userInfo.email }}
                </span>
                <span class="inline-flex items-center gap-1">
                  <CalendarDaysIcon class="w-3.5 h-3.5" /> 加入 {{ daysSinceJoined }} 天
                </span>
              </div>
            </div>

            <button
              @click="openEditModal"
              class="shrink-0 inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-white/20 backdrop-blur-sm text-white text-sm font-semibold hover:bg-white/30 border border-white/20 transition-all hover:scale-105"
            >
              <PencilIcon class="w-4 h-4" />
              编辑资料
            </button>
          </div>

          <!-- 统计条 -->
          <div class="grid grid-cols-3 gap-4 mt-6 pt-5 border-t border-white/15">
            <div class="text-center">
              <div class="text-2xl font-extrabold text-white">{{ stats.favorites }}</div>
              <div class="text-xs text-white/60 mt-0.5">收藏商品</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-extrabold text-white">{{ stats.history }}</div>
              <div class="text-xs text-white/60 mt-0.5">浏览记录</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-extrabold text-white">{{ stats.addresses }}</div>
              <div class="text-xs text-white/60 mt-0.5">收货地址</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 快捷入口 ==================== -->
      <div class="grid grid-cols-2 gap-4">
        <div
          @click="activeTab = 'cart'"
          class="group relative overflow-hidden bg-white rounded-2xl border border-primary-light/50 shadow-sm hover:shadow-lg hover:shadow-primary/10 hover:-translate-y-1 transition-all duration-300 cursor-pointer p-5"
        >
          <div class="absolute top-0 right-0 w-16 h-16 rounded-bl-full bg-primary/5 group-hover:bg-primary/10 transition-colors"></div>
          <div class="relative flex items-center gap-4">
            <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
              <ShoppingCartIcon class="w-6 h-6" />
            </div>
            <div>
              <div class="font-bold text-gray-800 group-hover:text-primary transition-colors">购物车</div>
              <div class="text-xs text-gray-400 mt-0.5">查看和管理购物车商品</div>
            </div>
          </div>
        </div>
        <div
          @click="activeTab = 'orders'"
          class="group relative overflow-hidden bg-white rounded-2xl border border-primary-light/50 shadow-sm hover:shadow-lg hover:shadow-primary/10 hover:-translate-y-1 transition-all duration-300 cursor-pointer p-5"
        >
          <div class="absolute top-0 right-0 w-16 h-16 rounded-bl-full bg-accent-blue/10 group-hover:bg-accent-blue/20 transition-colors"></div>
          <div class="relative flex items-center gap-4">
            <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-accent-blue/15 to-accent-blue/5 flex items-center justify-center text-accent-blue group-hover:scale-110 transition-transform">
              <ClipboardDocumentListIcon class="w-6 h-6" />
            </div>
            <div>
              <div class="font-bold text-gray-800 group-hover:text-primary transition-colors">我的订单</div>
              <div class="text-xs text-gray-400 mt-0.5">查看订单与物流状态</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 收货地址 ==================== -->
      <div class="bg-white rounded-2xl border border-primary-light/40 shadow-sm overflow-hidden">
        <div class="px-6 py-4 flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
              <MapPinIcon class="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 class="font-bold text-gray-800">收货地址</h3>
              <p class="text-xs text-gray-400">{{ addresses.length }} 个地址</p>
            </div>
          </div>
          <button
            @click="openAddressModal('add')"
            class="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary text-white text-sm font-medium hover:bg-primary-dark hover:shadow-md hover:shadow-primary/20 transition-all"
          >
            <PlusIcon class="w-4 h-4" />
            新增
          </button>
        </div>

        <div v-if="addresses.length" class="px-4 pb-4 space-y-3">
          <div
            v-for="addr in addresses"
            :key="addr.id"
            :class="[
              'relative rounded-2xl p-4 border transition-all hover:shadow-sm group',
              addr.is_default
                ? 'bg-primary-light/30 border-primary/30'
                : 'bg-gray-50/50 border-gray-100 hover:border-primary-light/60',
            ]"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex items-start gap-3 min-w-0">
                <div :class="[
                  'w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5',
                  addr.is_default ? 'bg-primary text-white shadow-sm' : 'bg-gray-100 text-gray-400',
                ]">
                  <MapPinIcon class="w-5 h-5" />
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-bold text-gray-800">{{ addr.recipient }}</span>
                    <span class="text-sm text-gray-500">{{ addr.phone }}</span>
                    <span
                      v-if="addr.is_default"
                      class="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-md bg-primary text-white text-[10px] font-semibold shadow-sm"
                    >
                      <StarIcon class="w-3 h-3" /> 默认
                    </span>
                  </div>
                  <p class="text-sm text-gray-600 mt-1 truncate">
                    {{ addr.province }} {{ addr.city }} {{ addr.district }} {{ addr.detail }}
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-1.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  v-if="!addr.is_default"
                  @click="setDefaultAddress(addr)"
                  class="px-2.5 py-1.5 rounded-lg text-xs font-medium text-primary bg-primary/5 hover:bg-primary hover:text-white transition-colors"
                >
                  默认
                </button>
                <button
                  @click="openAddressModal('edit', addr)"
                  class="px-2.5 py-1.5 rounded-lg text-xs font-medium text-gray-500 bg-gray-100 hover:bg-gray-200 transition-colors"
                >
                  编辑
                </button>
                <button
                  @click="deleteAddress(addr)"
                  class="px-2.5 py-1.5 rounded-lg text-xs font-medium text-rose-500 bg-rose-50 hover:bg-rose-500 hover:text-white transition-colors"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="flex flex-col items-center justify-center py-12 text-gray-400">
          <div class="w-16 h-16 rounded-2xl bg-primary/5 flex items-center justify-center mb-3">
            <MapPinIcon class="w-8 h-8 text-primary/30" />
          </div>
          <p class="text-sm font-medium">暂无收货地址</p>
          <p class="text-xs mt-1 mb-4">添加一个地址，购物下单更方便</p>
          <button
            @click="openAddressModal('add')"
            class="px-5 py-2 rounded-xl text-sm font-medium bg-primary text-white hover:bg-primary-dark transition-colors shadow-sm"
          >
            + 新增地址
          </button>
        </div>
      </div>

      <!-- ==================== 内容标签页 ==================== -->
      <div class="bg-white rounded-2xl border border-primary-light/40 shadow-sm overflow-hidden">
        <!-- Tab 导航 -->
        <div class="px-4 sm:px-6 pt-4">
          <div class="flex items-center gap-1 bg-gray-50 rounded-2xl p-1">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              @click="activeTab = tab.key"
              :class="[
                'flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300',
                activeTab === tab.key
                  ? 'bg-white text-primary shadow-sm'
                  : 'text-gray-500 hover:text-gray-700',
              ]"
            >
              <component :is="tab.icon" class="w-4 h-4" />
              <span class="hidden sm:inline">{{ tab.label }}</span>
              <span v-if="tab.count.value !== null && tab.count.value > 0" class="text-xs">({{ tab.count.value }})</span>
            </button>
          </div>
        </div>

        <div class="p-5">
          <!-- 我的收藏 -->
          <div v-if="activeTab === 'favorites'">
            <div v-if="favorites.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              <div
                v-for="item in favorites"
                :key="item.id"
                class="group relative bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-1.5 transition-all duration-300 overflow-hidden cursor-pointer"
                @click="openProductDetail(item.product_id)"
              >
                <div class="aspect-square bg-gray-50 overflow-hidden">
                  <img
                    v-if="item.image_url"
                    :src="resolveAvatarUrl(item.image_url)"
                    :alt="item.name"
                    class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                    @error="(e: any) => (e.target.style.display = 'none')"
                  />
                  <div v-else class="w-full h-full flex items-center justify-center">
                    <div class="w-12 h-12 rounded-xl bg-primary/5 flex items-center justify-center">
                      <HeartIcon class="w-6 h-6 text-primary/30" />
                    </div>
                  </div>
                  <div class="absolute top-2 left-2">
                    <span v-if="item.category" class="px-2 py-0.5 rounded-full bg-white/90 backdrop-blur-sm text-[10px] font-medium text-primary shadow-sm">
                      {{ item.category }}
                    </span>
                  </div>
                </div>
                <div class="p-3">
                  <h4 class="text-sm font-semibold text-gray-800 line-clamp-2 leading-snug min-h-[2.5rem]">{{ item.name }}</h4>
                  <div class="flex items-center justify-between mt-2">
                    <span class="text-base font-extrabold text-primary">¥{{ formatPrice(item.price) }}</span>
                  </div>
                </div>
                <button
                  @click.stop="removeFavorite(item)"
                  class="w-full py-2.5 text-xs font-medium text-rose-500 bg-rose-50/80 hover:bg-rose-500 hover:text-white transition-colors flex items-center justify-center gap-1.5"
                >
                  <TrashIcon class="w-3.5 h-3.5" /> 取消收藏
                </button>
              </div>
            </div>
            <div v-else class="flex flex-col items-center justify-center py-16 text-gray-400">
              <div class="w-20 h-20 rounded-3xl bg-primary/5 flex items-center justify-center mb-4">
                <HeartIcon class="w-10 h-10 text-primary/30" />
              </div>
              <p class="text-sm font-medium">暂无收藏商品</p>
              <p class="text-xs mt-1">去逛逛商品，点亮喜欢的好物吧</p>
            </div>
          </div>

          <!-- 浏览记录 -->
          <div v-if="activeTab === 'history'">
            <div v-if="history.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              <div
                v-for="item in history"
                :key="item.id"
                class="group relative bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-1.5 transition-all duration-300 overflow-hidden cursor-pointer"
                @click="openProductDetail(item.product_id)"
              >
                <div class="aspect-square bg-gray-50 overflow-hidden">
                  <img
                    v-if="item.image_url"
                    :src="resolveAvatarUrl(item.image_url)"
                    :alt="item.name"
                    class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                    @error="(e: any) => (e.target.style.display = 'none')"
                  />
                  <div v-else class="w-full h-full flex items-center justify-center">
                    <div class="w-12 h-12 rounded-xl bg-primary/5 flex items-center justify-center">
                      <ClockIcon class="w-6 h-6 text-primary/30" />
                    </div>
                  </div>
                  <div class="absolute top-2 left-2">
                    <span v-if="item.category" class="px-2 py-0.5 rounded-full bg-white/90 backdrop-blur-sm text-[10px] font-medium text-primary shadow-sm">
                      {{ item.category }}
                    </span>
                  </div>
                </div>
                <div class="p-3">
                  <h4 class="text-sm font-semibold text-gray-800 line-clamp-2 leading-snug min-h-[2.5rem]">{{ item.name }}</h4>
                  <div class="flex items-center justify-between mt-2">
                    <span class="text-base font-extrabold text-primary">¥{{ formatPrice(item.price) }}</span>
                  </div>
                  <p class="text-[10px] text-gray-400 mt-1.5 flex items-center gap-1">
                    <ClockIcon class="w-3 h-3" />
                    {{ formatTime(item.viewed_at) }}
                  </p>
                </div>
              </div>
            </div>
            <div v-else class="flex flex-col items-center justify-center py-16 text-gray-400">
              <div class="w-20 h-20 rounded-3xl bg-primary/5 flex items-center justify-center mb-4">
                <ClockIcon class="w-10 h-10 text-primary/30" />
              </div>
              <p class="text-sm font-medium">暂无浏览记录</p>
              <p class="text-xs mt-1">浏览过的商品会在这里展示</p>
            </div>
          </div>

          <!-- 购物车 -->
          <div v-if="activeTab === 'cart'">
            <ShoppingCart />
          </div>

          <!-- 我的订单 -->
          <div v-if="activeTab === 'orders'">
            <MyOrders />
          </div>
        </div>
      </div>
    </template>

    <!-- ==================== 编辑资料弹窗 ==================== -->
    <Teleport to="body">
      <transition
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="editVisible"
          class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
          @click.self="editVisible = false"
        >
          <transition
            enter-active-class="transition duration-300 ease-out"
            enter-from-class="opacity-0 scale-95 translate-y-4"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-active-class="transition duration-200 ease-in"
            leave-from-class="opacity-100 scale-100 translate-y-0"
            leave-to-class="opacity-0 scale-95 translate-y-4"
          >
            <div v-if="editVisible" class="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden">
              <div class="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                  <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                    <PencilIcon class="w-5 h-5 text-primary" />
                  </div>
                  <h3 class="text-lg font-bold text-gray-800">编辑资料</h3>
                </div>
                <button
                  @click="editVisible = false"
                  class="w-9 h-9 rounded-xl hover:bg-gray-100 text-gray-400 hover:text-gray-600 flex items-center justify-center transition-colors"
                >
                  <XMarkIcon class="w-5 h-5" />
                </button>
              </div>
              <div class="p-6 space-y-5">
                <div>
                  <label class="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">昵称</label>
                  <input
                    v-model="editForm.nickname"
                    type="text"
                    class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none text-sm font-medium transition-all"
                    placeholder="请输入昵称"
                  />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">手机号</label>
                  <input
                    v-model="editForm.phone"
                    type="text"
                    maxlength="11"
                    class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none text-sm font-medium transition-all"
                    placeholder="请输入手机号"
                  />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">邮箱</label>
                  <input
                    v-model="editForm.email"
                    type="email"
                    class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none text-sm font-medium transition-all"
                    placeholder="请输入邮箱"
                  />
                </div>
              </div>
              <div class="px-6 py-4 border-t border-gray-100 flex justify-end gap-3 bg-gray-50/50">
                <button
                  @click="editVisible = false"
                  class="px-5 py-2.5 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors"
                >
                  取消
                </button>
                <button
                  @click="saveProfile"
                  :disabled="editLoading"
                  class="px-6 py-2.5 rounded-xl text-sm font-semibold bg-primary text-white hover:bg-primary-dark hover:shadow-lg hover:shadow-primary/20 transition-all disabled:opacity-60"
                >
                  {{ editLoading ? '保存中...' : '保存修改' }}
                </button>
              </div>
            </div>
          </transition>
        </div>
      </transition>
    </Teleport>

    <!-- ==================== 地址新增/编辑弹窗 ==================== -->
    <Teleport to="body">
      <transition
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="addressModalVisible"
          class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
          @click.self="addressModalVisible = false"
        >
          <transition
            enter-active-class="transition duration-300 ease-out"
            enter-from-class="opacity-0 scale-95 translate-y-4"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-active-class="transition duration-200 ease-in"
            leave-from-class="opacity-100 scale-100 translate-y-0"
            leave-to-class="opacity-0 scale-95 translate-y-4"
          >
            <div v-if="addressModalVisible" class="bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden">
              <div class="px-6 py-5 border-b border-gray-100 flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                  <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center">
                    <MapPinIcon class="w-5 h-5 text-primary" />
                  </div>
                  <h3 class="text-lg font-bold text-gray-800">
                    {{ addressEditMode === 'add' ? '新增收货地址' : '编辑收货地址' }}
                  </h3>
                </div>
                <button
                  @click="addressModalVisible = false"
                  class="w-9 h-9 rounded-xl hover:bg-gray-100 text-gray-400 hover:text-gray-600 flex items-center justify-center transition-colors"
                >
                  <XMarkIcon class="w-5 h-5" />
                </button>
              </div>
              <div class="p-6 space-y-5">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">
                      收货人 <span class="text-rose-500">*</span>
                    </label>
                    <input
                      v-model="addressForm.recipient"
                      type="text"
                      class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none text-sm font-medium transition-all"
                      placeholder="请输入收货人姓名"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">
                      手机号 <span class="text-rose-500">*</span>
                    </label>
                    <input
                      v-model="addressForm.phone"
                      type="tel"
                      maxlength="11"
                      class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none text-sm font-medium transition-all"
                      placeholder="请输入手机号"
                    />
                  </div>
                </div>
                <div class="grid grid-cols-3 gap-3">
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">省份</label>
                    <input
                      v-model="addressForm.province"
                      type="text"
                      class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none text-sm font-medium transition-all"
                      placeholder="省份"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">城市</label>
                    <input
                      v-model="addressForm.city"
                      type="text"
                      class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none text-sm font-medium transition-all"
                      placeholder="城市"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">区/县</label>
                    <input
                      v-model="addressForm.district"
                      type="text"
                      class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none text-sm font-medium transition-all"
                      placeholder="区/县"
                    />
                  </div>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">
                    详细地址 <span class="text-rose-500">*</span>
                  </label>
                  <textarea
                    v-model="addressForm.detail"
                    rows="2"
                    class="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-4 focus:ring-primary/10 outline-none text-sm font-medium resize-none transition-all"
                    placeholder="请输入街道、门牌号、楼栋等"
                  ></textarea>
                </div>
                <label class="flex items-center gap-3 cursor-pointer group">
                  <div class="relative">
                    <input type="checkbox" v-model="addressForm.is_default" class="sr-only peer" />
                    <div class="w-5 h-5 rounded-lg border-2 border-gray-300 peer-checked:border-primary peer-checked:bg-primary flex items-center justify-center transition-colors">
                      <svg v-if="addressForm.is_default" class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" /></svg>
                    </div>
                  </div>
                  <span class="text-sm text-gray-600 group-hover:text-gray-800 transition-colors">设为默认地址（下单时默认使用该地址）</span>
                </label>
              </div>
              <div class="px-6 py-4 border-t border-gray-100 flex justify-end gap-3 bg-gray-50/50">
                <button
                  @click="addressModalVisible = false"
                  class="px-5 py-2.5 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors"
                >
                  取消
                </button>
                <button
                  @click="saveAddress"
                  :disabled="addressLoading"
                  class="px-6 py-2.5 rounded-xl text-sm font-semibold bg-primary text-white hover:bg-primary-dark hover:shadow-lg hover:shadow-primary/20 transition-all disabled:opacity-60"
                >
                  {{ addressLoading ? '保存中...' : '保存' }}
                </button>
              </div>
            </div>
          </transition>
        </div>
      </transition>
    </Teleport>

    <!-- ==================== 商品详情弹窗（内嵌，Teleport 到 body） ==================== -->
    <Teleport to="body">
      <transition
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="detailVisible"
          class="fixed inset-0 z-[200] bg-black/50 backdrop-blur-sm flex items-start sm:items-center justify-center p-4 overflow-y-auto"
          @click.self="closeDetail"
        >
          <div class="bg-white rounded-3xl shadow-2xl w-full max-w-4xl my-8 relative max-h-[90vh] overflow-y-auto">
            <button
              @click="closeDetail"
              class="absolute top-4 right-4 z-10 w-10 h-10 rounded-full bg-black/10 hover:bg-black/20 text-gray-600 hover:text-gray-800 flex items-center justify-center transition-colors backdrop-blur-sm"
            >
              <XMarkIcon class="w-5 h-5" />
            </button>

            <!-- 加载中 -->
            <div v-if="detailLoading" class="flex flex-col items-center justify-center py-32 text-gray-400">
              <div class="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-4"></div>
              <p class="text-sm">加载商品详情...</p>
            </div>

            <!-- 错误提示 -->
            <div v-else-if="detailError" class="flex flex-col items-center justify-center py-24 px-6">
              <div class="w-16 h-16 rounded-2xl bg-rose-50 flex items-center justify-center mb-4">
                <svg class="w-8 h-8 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
              </div>
              <p class="text-base font-semibold text-gray-700">商品详情加载失败</p>
              <p class="text-sm text-gray-400 mt-1 text-center max-w-sm">{{ detailError }}</p>
              <button
                @click="closeDetail"
                class="mt-5 px-6 py-2 rounded-xl bg-primary text-white text-sm font-medium hover:bg-primary-dark transition-colors"
              >
                关闭弹窗
              </button>
            </div>

            <!-- 详情内容 -->
            <div v-else-if="detailProduct" class="p-6 sm:p-8">
              <!-- 标题 -->
              <div class="mb-5">
                <div class="flex flex-wrap gap-2 mb-3">
                  <span v-if="detailProduct.category" class="px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">{{ detailProduct.category }}</span>
                  <span v-if="detailProduct.brand" class="px-2.5 py-1 rounded-full bg-green-50 text-green-600 text-xs font-medium">{{ detailProduct.brand }}</span>
                  <span v-if="detailProduct.platform && detailProduct.platform !== 'manual'" class="px-2.5 py-1 rounded-full bg-blue-50 text-blue-500 text-xs font-medium">{{ detailProduct.platform }}</span>
                </div>
                <h2 class="text-xl sm:text-2xl font-extrabold text-gray-800 leading-tight">{{ detailProduct.name }}</h2>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <!-- 左：图库 -->
                <div>
                  <div class="aspect-square bg-gray-50 rounded-2xl overflow-hidden flex items-center justify-center">
                    <img v-if="activeImageUrl" :src="resolveAvatarUrl(activeImageUrl)" :alt="detailProduct.name" class="w-full h-full object-cover" />
                    <div v-else class="text-gray-300 text-sm">暂无图片</div>
                  </div>
                  <div v-if="galleryImages.length > 1" class="flex gap-2 mt-3 overflow-x-auto pb-1">
                    <button
                      v-for="(url, idx) in galleryImages"
                      :key="idx"
                      :class="[
                        'w-16 h-16 rounded-xl overflow-hidden border-2 transition-all flex-shrink-0',
                        activeImageUrl === url ? 'border-primary shadow-md' : 'border-transparent opacity-60 hover:opacity-100',
                      ]"
                      @click="activeImageUrl = url"
                    >
                      <img :src="resolveAvatarUrl(url)" class="w-full h-full object-cover" />
                    </button>
                  </div>
                </div>

                <!-- 右：信息 -->
                <div class="flex flex-col">
                  <!-- 价格 -->
                  <div class="flex items-end gap-3 mb-4">
                    <span class="text-3xl font-extrabold text-primary">¥{{ formatPrice(detailProduct.price) }}</span>
                    <span v-if="detailProduct.original_price" class="text-sm text-gray-400 line-through mb-1">¥{{ formatPrice(detailProduct.original_price) }}</span>
                  </div>

                  <!-- 评分 -->
                  <div class="flex flex-wrap items-center gap-3 mb-4 text-sm text-gray-500">
                    <span v-if="detailProduct.rating" class="flex items-center gap-1">
                      <span class="text-amber-400">{{ '★'.repeat(Math.round(detailProduct.rating)) }}</span>
                      <span class="font-semibold text-gray-700">{{ detailProduct.rating }}</span> 分
                    </span>
                    <span v-if="detailProduct.review_count" class="text-gray-400">|</span>
                    <span v-if="detailProduct.review_count">{{ detailProduct.review_count }} 条评论</span>
                    <span v-if="detailProduct.sales_count" class="text-gray-400">|</span>
                    <span v-if="detailProduct.sales_count">销量 {{ detailProduct.sales_count }}</span>
                  </div>

                  <!-- 规格 -->
                  <div v-if="formatSpecs(detailProduct.specs).length > 0" class="mb-4">
                    <div class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">规格参数</div>
                    <div class="grid grid-cols-2 gap-2">
                      <div v-for="[key, val] in formatSpecs(detailProduct.specs)" :key="key" class="bg-gray-50 rounded-lg px-3 py-2">
                        <div class="text-xs text-gray-400">{{ key }}</div>
                        <div class="text-sm text-gray-700 font-medium">{{ val }}</div>
                      </div>
                    </div>
                  </div>

                  <!-- 卖点 -->
                  <div v-if="detailProduct.selling_points" class="mb-4">
                    <div class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">商品卖点</div>
                    <p class="text-sm text-gray-600 leading-relaxed bg-amber-50/50 rounded-xl p-3">{{ detailProduct.selling_points }}</p>
                  </div>

                  <!-- 数量 -->
                  <div class="flex items-center gap-4 mb-5">
                    <span class="text-sm font-medium text-gray-600">数量</span>
                    <div class="flex items-center gap-3 bg-gray-50 rounded-xl px-2 py-1">
                      <button @click="decreaseQty" class="w-8 h-8 rounded-lg hover:bg-gray-200 flex items-center justify-center transition-colors">
                        <MinusIcon class="w-4 h-4 text-gray-500" />
                      </button>
                      <span class="w-8 text-center text-sm font-bold text-gray-800">{{ detailQuantity }}</span>
                      <button @click="increaseQty" class="w-8 h-8 rounded-lg hover:bg-gray-200 flex items-center justify-center transition-colors">
                        <PlusIcon class="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                  </div>

                  <!-- 操作按钮 -->
                  <div class="flex flex-wrap gap-3 mb-4">
                    <button
                      @click="addToCartFromDetail"
                      class="flex-1 min-w-[120px] px-5 py-3 rounded-xl border-2 border-primary text-primary font-semibold text-sm hover:bg-primary/5 transition-colors"
                    >
                      加入购物车
                    </button>
                    <button
                      @click="handleBuyNow"
                      class="flex-1 min-w-[120px] px-5 py-3 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white font-semibold text-sm shadow-md hover:shadow-lg hover:shadow-primary/20 transition-all"
                    >
                      立即购买
                    </button>
                    <button
                      :class="[
                        'px-5 py-3 rounded-xl font-semibold text-sm transition-all border-2',
                        isFavorited
                          ? 'bg-primary text-white border-primary'
                          : 'border-gray-200 text-gray-500 hover:border-primary hover:text-primary',
                      ]"
                      @click="toggleFavoriteDetail"
                    >
                      {{ isFavorited ? '已收藏' : '收藏' }}
                    </button>
                  </div>

                  <!-- 客服 -->
                  <button
                    @click="handleAskCustomerService"
                    class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-50 text-blue-500 text-sm font-medium hover:bg-blue-100 transition-colors"
                  >
                    <ChatBubbleLeftRightIcon class="w-4 h-4" />
                    询问客服
                  </button>
                </div>
              </div>

              <!-- 评论 -->
              <div v-if="detailProduct.reviews && detailProduct.reviews.length > 0" class="mt-6 pt-6 border-t border-gray-100">
                <h3 class="font-bold text-gray-800 mb-4 flex items-center gap-2">
                  <span>用户评论</span>
                  <span class="text-xs text-gray-400 font-normal">共 {{ detailProduct.reviews.length }} 条</span>
                </h3>
                <div class="space-y-4">
                  <div v-for="review in detailProduct.reviews" :key="review.id" class="bg-gray-50/50 rounded-2xl p-4">
                    <div class="flex items-center gap-2 mb-2">
                      <div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent-blue flex items-center justify-center text-white text-xs font-bold">
                        {{ review.user_name?.charAt(0) || '用' }}
                      </div>
                      <span class="text-sm font-medium text-gray-700">{{ review.user_name }}</span>
                      <span class="text-xs text-amber-400">{{ '★'.repeat(Math.round(review.rating)) }}</span>
                      <span class="text-xs text-gray-400 ml-auto">{{ review.created_at?.slice(0, 10) }}</span>
                    </div>
                    <p class="text-sm text-gray-600 leading-relaxed">{{ review.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

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
/* 输入框自动填充样式修复 */
:deep(input:-webkit-autofill),
:deep(input:-webkit-autofill:hover),
:deep(input:-webkit-autofill:focus) {
  -webkit-box-shadow: 0 0 0 30px white inset !important;
  -webkit-text-fill-color: #1f2937 !important;
}
</style>