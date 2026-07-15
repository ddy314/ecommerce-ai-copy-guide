<script setup lang="ts">
import { ref, onMounted, inject, provide } from 'vue'
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
} from '@heroicons/vue/24/outline'
import ShoppingCart from './ShoppingCart.vue'
import MyOrders from './MyOrders.vue'
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
  product_id?: number
}

interface HistoryProduct {
  id: number
  name: string
  image_url: string | null
  price: number | null
  category: string | null
  viewed_at: string
  product_id?: number
}

// ---------- 导航 ----------
const navigate = inject<(page: string) => void>('navigate', () => {})
const navigateToProduct = inject<(productId: number) => void>('navigateToProduct', () => navigate('products'))

// ---------- 状态 ----------
const loading = ref(true)
const userInfo = ref<UserInfo | null>(null)

// ---------- 编辑资料弹窗
const editVisible = ref(false)
const editForm = ref({ nickname: '', phone: '', email: '' })
const editLoading = ref(false)

// ---------- 头像上传
const avatarInput = ref<HTMLInputElement | null>(null)
const avatarLoading = ref(false)

function triggerAvatarUpload() {
  avatarInput.value?.click()
}

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
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    const data = await response.json()
    const updatedUser = data.user || { ...userInfo.value, avatar: data.avatar }
    userInfo.value = updatedUser
    // 同步更新 localStorage，保持登录态信息一致
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

// 地址管理
const addresses = ref<Address[]>([])
const addressModalVisible = ref(false)
const addressEditMode = ref<'add' | 'edit'>('add')
const addressForm = ref<Address>({
  id: 0,
  recipient: '',
  phone: '',
  province: '',
  city: '',
  district: '',
  detail: '',
  is_default: false,
})
const addressLoading = ref(false)

// 收藏
const favorites = ref<FavoriteProduct[]>([])

// 浏览记录
const history = ref<HistoryProduct[]>([])

// 当前 Tab
const activeTab = ref<'favorites' | 'history' | 'cart' | 'orders'>('favorites')

// 提供给子组件（ShoppingCart）切换到订单标签的能力
provide('switchToOrdersTab', () => { activeTab.value = 'orders' })

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

// ---------- 加载用户信息 ----------
async function loadUserInfo() {
  loading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/auth/me`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    userInfo.value = data.user || data
  } catch {
    // 降级：使用 localStorage 中的信息
    const stored = localStorage.getItem('userInfo')
    if (stored) {
      try {
        const info = JSON.parse(stored)
        userInfo.value = {
          id: 0,
          username: info.username || '',
          nickname: info.nickname || info.username || '',
          phone: info.phone || '',
          email: info.email || '',
          avatar: info.avatar || null,
          role: info.role || 'user',
          created_at: info.created_at || '',
        }
      } catch {
        // ignore
      }
    }
  } finally {
    loading.value = false
  }
}

// ---------- 编辑资料 ----------
function openEditModal() {
  if (userInfo.value) {
    editForm.value = {
      nickname: userInfo.value.nickname || '',
      phone: userInfo.value.phone || '',
      email: userInfo.value.email || '',
    }
  }
  editVisible.value = true
}

async function saveProfile() {
  editLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/api/auth/profile`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify(editForm.value),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    const data = await response.json()
    const updatedUser = data.user || { ...userInfo.value, ...editForm.value }
    userInfo.value = updatedUser
    // 同步更新 localStorage，避免刷新后资料回退
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
  } finally {
    editLoading.value = false
  }
}

// ---------- 地址管理 ----------
async function loadAddresses() {
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    addresses.value = data.addresses || data || []
  } catch {
    // 静默失败
  }
}

function openAddressModal(mode: 'add' | 'edit', addr?: Address) {
  addressEditMode.value = mode
  if (mode === 'edit' && addr) {
    addressForm.value = { ...addr }
  } else {
    addressForm.value = {
      id: 0,
      recipient: '',
      phone: '',
      province: '',
      city: '',
      district: '',
      detail: '',
      is_default: false,
    }
  }
  addressModalVisible.value = true
}

async function saveAddress() {
  if (!addressForm.value.recipient || !addressForm.value.phone || !addressForm.value.detail) {
    showToast('请填写完整收货信息', 'error')
    return
  }
  addressLoading.value = true
  try {
    const url =
      addressEditMode.value === 'add'
        ? `${API_BASE}/api/user/addresses`
        : `${API_BASE}/api/user/addresses/${addressForm.value.id}`
    const method = addressEditMode.value === 'add' ? 'POST' : 'PUT'
    const response = await fetch(url, {
      method,
      headers: authHeaders(),
      body: JSON.stringify(addressForm.value),
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    showToast(addressEditMode.value === 'add' ? '地址添加成功' : '地址修改成功')
    addressModalVisible.value = false
    await loadAddresses()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '保存地址失败', 'error')
  } finally {
    addressLoading.value = false
  }
}

async function deleteAddress(addr: Address) {
  if (!confirm('确定要删除该地址吗？')) return
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses/${addr.id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    showToast('地址已删除')
    await loadAddresses()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '删除失败', 'error')
  }
}

async function setDefaultAddress(addr: Address) {
  try {
    const response = await fetch(`${API_BASE}/api/user/addresses/${addr.id}`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify({ ...addr, is_default: true }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    showToast('已设为默认地址')
    await loadAddresses()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '设置失败', 'error')
  }
}

// ---------- 收藏 ----------
async function loadFavorites() {
  try {
    const response = await fetch(`${API_BASE}/api/user/favorites`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    favorites.value = data.favorites || data || []
  } catch {
    // 静默失败
  }
}

async function removeFavorite(item: FavoriteProduct) {
  if (!confirm('确定要取消收藏该商品吗？')) return
  try {
    const productId = item.product_id || item.id
    const response = await fetch(`${API_BASE}/api/user/favorites/${productId}`, {
      method: 'POST',
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    showToast('已取消收藏')
    favorites.value = favorites.value.filter((f) => (f.product_id || f.id) !== productId)
  } catch (e) {
    showToast(e instanceof Error ? e.message : '取消收藏失败', 'error')
  }
}

// ---------- 浏览记录 ----------
async function loadHistory() {
  try {
    const response = await fetch(`${API_BASE}/api/user/history`, {
      headers: authHeaders(),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    history.value = data.history || data || []
  } catch {
    // 静默失败
  }
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

onMounted(() => {
  loadUserInfo()
  loadAddresses()
  loadFavorites()
  loadHistory()
})
</script>

<template>
  <div class="relative space-y-5 animate-fade-in-up">
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
          'fixed top-20 left-1/2 -translate-x-1/2 z-50 px-6 py-2.5 rounded-full text-sm font-semibold text-white shadow-lg',
          toast.type === 'success' ? 'bg-emerald-500' : 'bg-rose-500',
        ]"
      >
        {{ toast.message }}
      </div>
    </transition>

    <!-- 加载中 -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20 text-gray-400">
      <div class="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-3"></div>
      <p>正在加载...</p>
    </div>

    <template v-else-if="userInfo">
      <!-- 用户信息卡片 -->
      <div class="bg-white rounded-2xl border border-primary-light/50 shadow-card overflow-hidden relative">
        <div class="h-2 bg-gradient-to-r from-primary to-accent-blue"></div>
        <div class="p-6 flex flex-col sm:flex-row items-center sm:items-start gap-5">
          <div class="relative shrink-0 group">
            <div class="w-24 h-24 rounded-full overflow-hidden border-4 border-primary-light shadow-lg">
              <img
                v-if="userInfo.avatar"
                :src="resolveAvatarUrl(userInfo.avatar)"
                :alt="userInfo.nickname"
                class="w-full h-full object-cover"
              />
              <div
                v-else
                class="w-full h-full bg-gradient-to-br from-primary to-accent-blue flex items-center justify-center text-3xl font-bold text-white"
              >
                {{ getAvatarChar().toUpperCase() }}
              </div>
            </div>
            <button
              @click="triggerAvatarUpload"
              :disabled="avatarLoading"
              class="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center shadow-md hover:bg-primary-dark transition-colors disabled:opacity-60"
            >
              <CameraIcon class="w-4 h-4" />
            </button>
            <div
              v-if="avatarLoading"
              class="absolute inset-0 rounded-full flex items-center justify-center bg-black/40 text-white text-xs font-semibold"
            >
              上传中
            </div>
            <input
              ref="avatarInput"
              type="file"
              accept="image/*"
              class="hidden"
              @change="handleAvatarChange"
            />
          </div>

          <div class="flex-1 text-center sm:text-left">
            <h2 class="text-2xl font-bold text-gray-800">{{ userInfo.nickname || userInfo.username }}</h2>
            <p class="text-sm text-gray-500 mt-1">账号：{{ userInfo.username }}</p>
            <div class="flex flex-wrap items-center justify-center sm:justify-start gap-3 mt-3 text-xs text-gray-500">
              <span v-if="userInfo.phone" class="inline-flex items-center gap-1 bg-gray-50 px-2.5 py-1 rounded-lg">
                手机：{{ userInfo.phone }}
              </span>
              <span v-if="userInfo.email" class="inline-flex items-center gap-1 bg-gray-50 px-2.5 py-1 rounded-lg">
                邮箱：{{ userInfo.email }}
              </span>
            </div>
          </div>

          <button
            @click="openEditModal"
            class="shrink-0 inline-flex items-center gap-1.5 px-5 py-2 rounded-full border border-primary text-primary text-sm font-semibold hover:bg-primary hover:text-white transition-all"
          >
            <PencilIcon class="w-4 h-4" />
            编辑资料
          </button>
        </div>
      </div>

      <!-- 快捷入口 -->
      <div class="grid grid-cols-2 gap-4">
        <div
          @click="activeTab = 'cart'"
          class="group bg-white rounded-2xl border border-primary-light/50 shadow-card p-5 flex items-center gap-4 cursor-pointer hover:-translate-y-1 hover:shadow-card-hover transition-all"
        >
          <div class="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-colors">
            <ShoppingCartIcon class="w-6 h-6" />
          </div>
          <div>
            <div class="font-bold text-gray-800">购物车</div>
            <div class="text-xs text-gray-500 mt-0.5">查看和管理购物车商品</div>
          </div>
        </div>
        <div
          @click="activeTab = 'orders'"
          class="group bg-white rounded-2xl border border-primary-light/50 shadow-card p-5 flex items-center gap-4 cursor-pointer hover:-translate-y-1 hover:shadow-card-hover transition-all"
        >
          <div class="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-colors">
            <ClipboardDocumentListIcon class="w-6 h-6" />
          </div>
          <div>
            <div class="font-bold text-gray-800">我的订单</div>
            <div class="text-xs text-gray-500 mt-0.5">查看订单与物流状态</div>
          </div>
        </div>
      </div>

      <!-- 收货地址 -->
      <div class="bg-white rounded-2xl border border-primary-light/50 shadow-card overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <MapPinIcon class="w-4 h-4" />
            </div>
            <h3 class="font-bold text-gray-800">收货地址</h3>
          </div>
          <button
            @click="openAddressModal('add')"
            class="inline-flex items-center gap-1 px-4 py-2 rounded-xl border border-primary text-primary text-sm font-medium hover:bg-primary hover:text-white transition-colors"
          >
            + 新增地址
          </button>
        </div>

        <div v-if="addresses.length" class="divide-y divide-gray-50">
          <div
            v-for="addr in addresses"
            :key="addr.id"
            :class="['px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4', addr.is_default ? 'bg-primary-light/20' : '']"
          >
            <div class="flex items-start gap-3">
              <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary shrink-0 mt-0.5">
                <MapPinIcon class="w-4 h-4" />
              </div>
              <div>
                <div class="flex items-center gap-3">
                  <span class="font-bold text-gray-800">{{ addr.recipient }}</span>
                  <span class="text-sm text-gray-500">{{ addr.phone }}</span>
                  <span
                    v-if="addr.is_default"
                    class="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-md bg-primary text-white text-[10px] font-medium"
                  >
                    <StarIcon class="w-3 h-3" /> 默认
                  </span>
                </div>
                <p class="text-sm text-gray-600 mt-1">
                  {{ addr.province }} {{ addr.city }} {{ addr.district }} {{ addr.detail }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2 pl-11 sm:pl-0">
              <button
                v-if="!addr.is_default"
                @click="setDefaultAddress(addr)"
                class="px-3 py-1.5 rounded-lg text-xs font-medium text-primary bg-primary/5 hover:bg-primary hover:text-white transition-colors"
              >
                设为默认
              </button>
              <button
                @click="openAddressModal('edit', addr)"
                class="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                编辑
              </button>
              <button
                @click="deleteAddress(addr)"
                class="px-3 py-1.5 rounded-lg text-xs font-medium text-rose-600 bg-rose-50 hover:bg-rose-500 hover:text-white transition-colors"
              >
                删除
              </button>
            </div>
          </div>
        </div>

        <div v-else class="flex flex-col items-center justify-center py-10 text-gray-400">
          <MapPinIcon class="w-10 h-10 mb-2 text-primary/30" />
          <p class="text-sm">暂无收货地址</p>
          <p class="text-xs mt-1 mb-3">添加一个地址，购物下单更方便</p>
          <button
            @click="openAddressModal('add')"
            class="px-4 py-2 rounded-xl text-sm font-medium bg-primary text-white hover:bg-primary-dark transition-colors"
          >
            + 新增地址
          </button>
        </div>
      </div>

      <!-- 收藏 / 浏览记录 / 购物车 / 订单 -->
      <div class="bg-white rounded-2xl border border-primary-light/50 shadow-card overflow-hidden">
        <div class="px-6 border-b border-gray-100">
          <div class="flex items-center gap-6 overflow-x-auto scrollbar-hide">
            <button
              v-for="tab in [
                { key: 'favorites', label: '我的收藏', count: favorites.length, icon: HeartIcon },
                { key: 'history', label: '浏览记录', count: history.length, icon: ClockIcon },
                { key: 'cart', label: '购物车', count: null, icon: ShoppingCartIcon },
                { key: 'orders', label: '我的订单', count: null, icon: ClipboardDocumentListIcon },
              ]"
              :key="tab.key"
              @click="activeTab = tab.key as any"
              :class="[
                'flex items-center gap-2 py-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                activeTab === tab.key
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-primary',
              ]"
            >
              <component :is="tab.icon" class="w-4 h-4" />
              {{ tab.label }}
              <span v-if="tab.count !== null" class="text-xs">({{ tab.count }})</span>
            </button>
          </div>
        </div>

        <div class="p-5">
          <!-- 我的收藏 -->
          <div v-if="activeTab === 'favorites'" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            <div
              v-for="item in favorites"
              :key="item.id"
              class="group bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-card hover:-translate-y-1 transition-all overflow-hidden cursor-pointer"
              @click="navigateToProduct(item.id)"
            >
              <div class="aspect-square bg-gray-100 overflow-hidden">
                <img
                  v-if="item.image_url"
                  :src="resolveAvatarUrl(item.image_url)"
                  :alt="item.name"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  @error="(e: any) => (e.target.style.display = 'none')"
                />
                <div v-else class="w-full h-full flex items-center justify-center text-gray-300 text-xs">暂无图片</div>
              </div>
              <div class="p-3">
                <h4 class="text-sm font-medium text-gray-800 line-clamp-2 h-10">{{ item.name }}</h4>
                <div class="flex items-center justify-between mt-2">
                  <span class="text-sm font-bold text-primary">¥{{ formatPrice(item.price) }}</span>
                  <span v-if="item.category" class="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">{{ item.category }}</span>
                </div>
              </div>
              <button
                @click.stop="removeFavorite(item)"
                class="w-full py-2 text-xs text-rose-500 bg-rose-50 hover:bg-rose-500 hover:text-white transition-colors flex items-center justify-center gap-1"
              >
                <TrashIcon class="w-3 h-3" /> 取消收藏
              </button>
            </div>
            <div v-if="!favorites.length" class="col-span-full text-center py-10 text-gray-400">
              <HeartIcon class="w-10 h-10 mx-auto mb-2 text-primary/30" />
              <p>暂无收藏商品</p>
            </div>
          </div>

          <!-- 浏览记录 -->
          <div v-if="activeTab === 'history'" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            <div
              v-for="item in history"
              :key="item.id"
              class="group bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-card hover:-translate-y-1 transition-all overflow-hidden cursor-pointer"
              @click="navigateToProduct(item.id)"
            >
              <div class="aspect-square bg-gray-100 overflow-hidden">
                <img
                  v-if="item.image_url"
                  :src="resolveAvatarUrl(item.image_url)"
                  :alt="item.name"
                  class="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  @error="(e: any) => (e.target.style.display = 'none')"
                />
                <div v-else class="w-full h-full flex items-center justify-center text-gray-300 text-xs">暂无图片</div>
              </div>
              <div class="p-3">
                <h4 class="text-sm font-medium text-gray-800 line-clamp-2 h-10">{{ item.name }}</h4>
                <div class="flex items-center justify-between mt-2">
                  <span class="text-sm font-bold text-primary">¥{{ formatPrice(item.price) }}</span>
                </div>
                <p class="text-[10px] text-gray-400 mt-1">浏览于 {{ formatTime(item.viewed_at) }}</p>
              </div>
            </div>
            <div v-if="!history.length" class="col-span-full text-center py-10 text-gray-400">
              <ClockIcon class="w-10 h-10 mx-auto mb-2 text-primary/30" />
              <p>暂无浏览记录</p>
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

    <!-- 编辑资料弹窗 -->
    <div
      v-if="editVisible"
      class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in-up"
      @click.self="editVisible = false"
    >
      <div class="bg-white rounded-2xl shadow-card w-full max-w-md overflow-hidden animate-modal-in">
        <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 class="text-lg font-bold text-gray-800">编辑资料</h3>
          <button
            @click="editVisible = false"
            class="w-8 h-8 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 flex items-center justify-center transition-colors"
          >
            ×
          </button>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1.5">昵称</label>
            <input
              v-model="editForm.nickname"
              type="text"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none text-sm"
              placeholder="请输入昵称"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1.5">手机号</label>
            <input
              v-model="editForm.phone"
              type="text"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none text-sm"
              placeholder="请输入手机号"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1.5">邮箱</label>
            <input
              v-model="editForm.email"
              type="text"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none text-sm"
              placeholder="请输入邮箱"
            />
          </div>
        </div>
        <div class="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
          <button
            @click="editVisible = false"
            class="px-4 py-2 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            @click="saveProfile"
            :disabled="editLoading"
            class="px-5 py-2 rounded-xl text-sm font-medium bg-primary text-white hover:bg-primary-dark transition-colors disabled:opacity-60"
          >
            {{ editLoading ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 地址新增/编辑弹窗 -->
    <div
      v-if="addressModalVisible"
      class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in-up"
      @click.self="addressModalVisible = false"
    >
      <div class="bg-white rounded-2xl shadow-card w-full max-w-lg overflow-hidden animate-modal-in">
        <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <MapPinIcon class="w-4 h-4" />
            </div>
            <h3 class="text-lg font-bold text-gray-800">
              {{ addressEditMode === 'add' ? '新增收货地址' : '编辑收货地址' }}
            </h3>
          </div>
          <button
            @click="addressModalVisible = false"
            class="w-8 h-8 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 flex items-center justify-center transition-colors"
          >
            ×
          </button>
        </div>
        <div class="p-6 space-y-5">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">
                收货人 <span class="text-rose-500">*</span>
              </label>
              <input
                v-model="addressForm.recipient"
                type="text"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none text-sm"
                placeholder="请输入收货人姓名"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">
                手机号 <span class="text-rose-500">*</span>
              </label>
              <input
                v-model="addressForm.phone"
                type="tel"
                maxlength="11"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none text-sm"
                placeholder="请输入手机号"
              />
            </div>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">省份</label>
              <input
                v-model="addressForm.province"
                type="text"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none text-sm"
                placeholder="省份"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">城市</label>
              <input
                v-model="addressForm.city"
                type="text"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none text-sm"
                placeholder="城市"
              />
            </div>
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">区/县</label>
              <input
                v-model="addressForm.district"
                type="text"
                class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none text-sm"
                placeholder="区/县"
              />
            </div>
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1.5">
              详细地址 <span class="text-rose-500">*</span>
            </label>
            <textarea
              v-model="addressForm.detail"
              rows="2"
              class="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none text-sm resize-none"
              placeholder="请输入街道、门牌号、楼栋等"
            ></textarea>
          </div>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="addressForm.is_default" class="w-4 h-4 text-primary rounded border-gray-300 focus:ring-primary" />
            <span class="text-sm text-gray-700">设为默认地址（下单时默认使用该地址）</span>
          </label>
        </div>
        <div class="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
          <button
            @click="addressModalVisible = false"
            class="px-4 py-2 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            @click="saveAddress"
            :disabled="addressLoading"
            class="px-5 py-2 rounded-xl text-sm font-medium bg-primary text-white hover:bg-primary-dark transition-colors disabled:opacity-60"
          >
            {{ addressLoading ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
