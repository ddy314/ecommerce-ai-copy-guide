<script setup lang="ts">
import { ref, onMounted, inject, provide } from 'vue'
import ShoppingCart from './ShoppingCart.vue'
import MyOrders from './MyOrders.vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

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
  <div class="user-profile">
    <!-- 提示 Toast -->
    <transition name="toast">
      <div v-if="toast.visible" :class="['up-toast', `up-toast--${toast.type}`]">
        {{ toast.message }}
      </div>
    </transition>

    <!-- 加载中 -->
    <div v-if="loading" class="up-loading">
      <div class="up-loading__spinner"></div>
      <p>正在加载...</p>
    </div>

    <template v-else>
      <!-- 用户信息卡片 -->
      <div class="up-user-card">
        <div class="up-user-card__avatar" @click="triggerAvatarUpload">
          <img
            v-if="userInfo?.avatar"
            :src="userInfo.avatar"
            :alt="userInfo.nickname"
          />
          <span v-else>{{ getAvatarChar() }}</span>
          <div v-if="avatarLoading" class="up-user-card__avatar-loading">上传中</div>
          <div v-else class="up-user-card__avatar-tip">点击上传</div>
          <input
            ref="avatarInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="handleAvatarChange"
          />
        </div>
        <div class="up-user-card__info">
          <h2 class="up-user-card__name">{{ userInfo?.nickname || userInfo?.username }}</h2>
          <div class="up-user-card__meta">
            <span class="up-user-card__account">账号：{{ userInfo?.username }}</span>
            <span v-if="userInfo?.phone" class="up-user-card__phone">手机：{{ userInfo.phone }}</span>
            <span v-if="userInfo?.email" class="up-user-card__email">邮箱：{{ userInfo.email }}</span>
          </div>
        </div>
        <button class="up-user-card__edit" @click="openEditModal">编辑资料</button>
      </div>

      <!-- 快捷入口 -->
      <div class="up-quick-entry">
        <div class="up-quick-card" @click="activeTab = 'cart'">
          <span class="up-quick-card__icon">车</span>
          <div>
            <span class="up-quick-card__title">购物车</span>
            <span class="up-quick-card__desc">查看和管理购物车商品</span>
          </div>
        </div>
        <div class="up-quick-card" @click="activeTab = 'orders'">
          <span class="up-quick-card__icon">单</span>
          <div>
            <span class="up-quick-card__title">我的订单</span>
            <span class="up-quick-card__desc">查看订单与物流状态</span>
          </div>
        </div>
      </div>

      <!-- 收货地址管理 -->
      <div class="up-section up-section--address">
        <div class="up-section__header">
          <div class="up-section__title-wrap">
            <span class="up-section__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
            </span>
            <h3 class="up-section__title">收货地址</h3>
          </div>
          <button class="up-section__add" @click="openAddressModal('add')">
            <span class="up-section__add-icon">+</span>
            <span>新增地址</span>
          </button>
        </div>

        <div v-if="addresses.length > 0" class="up-addr-list">
          <div
            v-for="addr in addresses"
            :key="addr.id"
            :class="['up-addr', { 'up-addr--default': addr.is_default }]"
          >
            <div class="up-addr__main">
              <div class="up-addr__pin">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                  <circle cx="12" cy="10" r="3"></circle>
                </svg>
              </div>
              <div class="up-addr__info">
                <div class="up-addr__head">
                  <span class="up-addr__name">{{ addr.recipient }}</span>
                  <span class="up-addr__phone">{{ addr.phone }}</span>
                  <span v-if="addr.is_default" class="up-addr__tag">默认</span>
                </div>
                <p class="up-addr__detail">
                  <span class="up-addr__region">{{ addr.province }} {{ addr.city }} {{ addr.district }}</span>
                  <span class="up-addr__street">{{ addr.detail }}</span>
                </p>
              </div>
            </div>
            <div class="up-addr__actions">
              <button
                v-if="!addr.is_default"
                class="up-addr__btn up-addr__btn--default"
                @click="setDefaultAddress(addr)"
                title="设为默认地址"
              >
                <span>设为默认</span>
              </button>
              <button class="up-addr__btn" @click="openAddressModal('edit', addr)">编辑</button>
              <button class="up-addr__btn up-addr__btn--del" @click="deleteAddress(addr)">删除</button>
            </div>
          </div>
        </div>
        <div v-else class="up-section__empty">
          <div class="up-section__empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
              <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
              <line x1="12" y1="22.08" x2="12" y2="12"></line>
            </svg>
          </div>
          <p>暂无收货地址</p>
          <p class="up-section__empty-hint">添加一个地址，购物下单更方便</p>
          <button class="up-section__add" @click="openAddressModal('add')">
            <span class="up-section__add-icon">+</span>
            <span>新增地址</span>
          </button>
        </div>
      </div>

      <!-- 收藏、浏览记录、购物车、订单 Tab -->
      <div class="up-section">
        <div class="up-tabs">
          <button
            :class="['up-tab', { active: activeTab === 'favorites' }]"
            @click="activeTab = 'favorites'"
          >
            我的收藏 ({{ favorites.length }})
          </button>
          <button
            :class="['up-tab', { active: activeTab === 'history' }]"
            @click="activeTab = 'history'"
          >
            浏览记录 ({{ history.length }})
          </button>
          <button
            :class="['up-tab', { active: activeTab === 'cart' }]"
            @click="activeTab = 'cart'"
          >
            购物车
          </button>
          <button
            :class="['up-tab', { active: activeTab === 'orders' }]"
            @click="activeTab = 'orders'"
          >
            我的订单
          </button>
        </div>

        <!-- 我的收藏 -->
        <div v-if="activeTab === 'favorites'">
          <div v-if="favorites.length > 0" class="up-product-grid">
            <div
              v-for="item in favorites"
              :key="item.id"
              class="up-product-card"
              @click="navigateToProduct(item.id)"
            >
              <div class="up-product-card__image">
                <img
                  v-if="item.image_url"
                  :src="item.image_url"
                  :alt="item.name"
                  @error="(e: any) => e.target.style.display = 'none'"
                />
                <div v-if="!item.image_url" class="up-product-card__noimg">暂无图片</div>
              </div>
              <div class="up-product-card__body">
                <h4 class="up-product-card__name">{{ item.name }}</h4>
                <span class="up-product-card__price">¥{{ formatPrice(item.price) }}</span>
                <span v-if="item.category" class="up-product-card__cat">{{ item.category }}</span>
              </div>
              <button
                class="up-product-card__remove"
                @click.stop="removeFavorite(item)"
              >
                取消收藏
              </button>
            </div>
          </div>
          <div v-else class="up-section__empty">
            <p>暂无收藏商品</p>
          </div>
        </div>

        <!-- 浏览记录 -->
        <div v-if="activeTab === 'history'">
          <div v-if="history.length > 0" class="up-product-grid">
            <div
              v-for="item in history"
              :key="item.id"
              class="up-product-card"
              @click="navigateToProduct(item.id)"
            >
              <div class="up-product-card__image">
                <img
                  v-if="item.image_url"
                  :src="item.image_url"
                  :alt="item.name"
                  @error="(e: any) => e.target.style.display = 'none'"
                />
                <div v-if="!item.image_url" class="up-product-card__noimg">暂无图片</div>
              </div>
              <div class="up-product-card__body">
                <h4 class="up-product-card__name">{{ item.name }}</h4>
                <span class="up-product-card__price">¥{{ formatPrice(item.price) }}</span>
                <span class="up-product-card__time">浏览于 {{ formatTime(item.viewed_at) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="up-section__empty">
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
    </template>

    <!-- 编辑资料弹窗 -->
    <transition name="modal">
      <div v-if="editVisible" class="up-modal-overlay" @click.self="editVisible = false">
        <div class="up-modal">
          <div class="up-modal__header">
            <h2>编辑资料</h2>
            <button class="up-modal__close" @click="editVisible = false">×</button>
          </div>
          <div class="up-modal__body">
            <div class="up-form-field">
              <label>昵称</label>
              <input v-model="editForm.nickname" type="text" placeholder="请输入昵称" />
            </div>
            <div class="up-form-field">
              <label>手机号</label>
              <input v-model="editForm.phone" type="text" placeholder="请输入手机号" />
            </div>
            <div class="up-form-field">
              <label>邮箱</label>
              <input v-model="editForm.email" type="text" placeholder="请输入邮箱" />
            </div>
          </div>
          <div class="up-modal__footer">
            <button class="up-btn up-btn--ghost" @click="editVisible = false">取消</button>
            <button class="up-btn up-btn--primary" :disabled="editLoading" @click="saveProfile">
              {{ editLoading ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 地址新增/编辑弹窗 -->
    <transition name="modal">
      <div v-if="addressModalVisible" class="up-modal-overlay" @click.self="addressModalVisible = false">
        <div class="up-modal up-modal--address">
          <div class="up-modal__header">
            <div class="up-modal__title-wrap">
            <span class="up-modal__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
            </span>
            <h2>{{ addressEditMode === 'add' ? '新增收货地址' : '编辑收货地址' }}</h2>
          </div>
            <button class="up-modal__close" @click="addressModalVisible = false">×</button>
          </div>
          <div class="up-modal__body">
            <div class="up-form-section">
              <div class="up-form-section__label">联系人信息</div>
              <div class="up-form-row">
                <div class="up-form-field">
                  <label>收货人 <span class="up-form__required">*</span></label>
                  <input v-model="addressForm.recipient" type="text" placeholder="请输入收货人姓名" />
                </div>
                <div class="up-form-field">
                  <label>手机号 <span class="up-form__required">*</span></label>
                  <input v-model="addressForm.phone" type="tel" maxlength="11" placeholder="请输入手机号" />
                </div>
              </div>
            </div>

            <div class="up-form-section">
              <div class="up-form-section__label">所在地区</div>
              <div class="up-form-row up-form-row--3">
                <div class="up-form-field">
                  <label>省份</label>
                  <input v-model="addressForm.province" type="text" placeholder="省份" />
                </div>
                <div class="up-form-field">
                  <label>城市</label>
                  <input v-model="addressForm.city" type="text" placeholder="城市" />
                </div>
                <div class="up-form-field">
                  <label>区/县</label>
                  <input v-model="addressForm.district" type="text" placeholder="区/县" />
                </div>
              </div>
            </div>

            <div class="up-form-section">
              <div class="up-form-section__label">详细地址</div>
              <div class="up-form-field">
                <label>街道/门牌号 <span class="up-form__required">*</span></label>
                <textarea
                  v-model="addressForm.detail"
                  rows="2"
                  placeholder="请输入详细地址，如街道、门牌号、楼栋等"
                ></textarea>
              </div>
            </div>

            <label class="up-form-check">
              <input type="checkbox" v-model="addressForm.is_default" />
              <span class="up-form-check__box"></span>
              <span>设为默认地址（下单时默认使用该地址）</span>
            </label>
          </div>
          <div class="up-modal__footer">
            <button class="up-btn up-btn--ghost" @click="addressModalVisible = false">取消</button>
            <button class="up-btn up-btn--primary" :disabled="addressLoading" @click="saveAddress">
              {{ addressLoading ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.user-profile {
  position: relative;
}

/* Toast */
.up-toast {
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

.up-toast--success {
  background: var(--green);
}

.up-toast--error {
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

/* 加载 */
.up-loading {
  text-align: center;
  padding: 80px 20px;
  color: var(--muted);
}

.up-loading__spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: up-spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes up-spin {
  to { transform: rotate(360deg); }
}

/* 用户信息卡片 */
.up-user-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 28px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  margin-bottom: 20px;
  position: relative;
  overflow: hidden;
}

.up-user-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--brand), var(--brand-dark));
}

.up-user-card__avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  color: #fffaf0;
  font-size: 32px;
  font-weight: 800;
  flex-shrink: 0;
}

.up-user-card__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.up-user-card__avatar-tip,
.up-user-card__avatar-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.2s;
  border-radius: 50%;
  cursor: pointer;
}

.up-user-card__avatar:hover .up-user-card__avatar-tip {
  opacity: 1;
}

.up-user-card__avatar-loading {
  opacity: 1;
}

.up-user-card__info {
  flex: 1;
}

.up-user-card__name {
  font-size: 22px;
  margin: 0 0 10px;
  color: var(--ink);
}

.up-user-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: var(--muted);
}

.up-user-card__edit {
  padding: 10px 24px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  background: transparent;
  color: var(--brand);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.up-user-card__edit:hover {
  background: var(--brand);
  color: #fff;
}

/* 快捷入口 */
.up-quick-entry {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.up-quick-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}

.up-quick-card:hover {
  transform: translateY(-3px);
  border-color: var(--brand);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.up-quick-card__icon {
  display: inline-grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 14px;
  color: #fffaf0;
  font-weight: 800;
  font-size: 20px;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  flex-shrink: 0;
}

.up-quick-card__title {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 4px;
}

.up-quick-card__desc {
  display: block;
  font-size: 13px;
  color: var(--muted);
}

/* 区块 */
.up-section {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 24px;
  margin-bottom: 20px;
}

.up-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.up-section__title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.up-section__icon {
  width: 22px;
  height: 22px;
  color: var(--brand);
  display: flex;
  align-items: center;
  justify-content: center;
}

.up-section__icon svg {
  width: 100%;
  height: 100%;
}

.up-section__title {
  font-size: 18px;
  margin: 0;
  color: var(--ink);
  font-weight: 700;
}

.up-section__add {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  background: rgba(217, 95, 45, 0.06);
  color: var(--brand);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.up-section__add:hover {
  background: var(--brand);
  color: #fff;
}

.up-section__add-icon {
  font-size: 16px;
  line-height: 1;
}

.up-section__empty {
  text-align: center;
  padding: 48px 20px;
  color: var(--muted);
  font-size: 14px;
}

.up-section__empty-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 12px;
  color: var(--line);
  display: flex;
  align-items: center;
  justify-content: center;
}

.up-section__empty-icon svg {
  width: 100%;
  height: 100%;
}

.up-section__empty-hint {
  font-size: 13px;
  color: var(--muted);
  margin: 4px 0 16px;
}

.up-section__empty button {
  margin-top: 0;
}

/* 地址列表 */
.up-addr-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.up-addr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
  transition: all 0.2s ease;
}

.up-addr:hover {
  border-color: var(--brand);
  box-shadow: 0 4px 14px rgba(217, 95, 45, 0.08);
}

.up-addr--default {
  border-color: var(--brand);
  background: linear-gradient(135deg, rgba(217, 95, 45, 0.04), rgba(217, 95, 45, 0.01));
  box-shadow: 0 4px 14px rgba(217, 95, 45, 0.06);
}

.up-addr__main {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  flex: 1;
  min-width: 0;
}

.up-addr__pin {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(217, 95, 45, 0.1), rgba(217, 95, 45, 0.04));
  color: var(--brand);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.up-addr__pin svg {
  width: 20px;
  height: 20px;
}

.up-addr__info {
  flex: 1;
  min-width: 0;
}

.up-addr__head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.up-addr__name {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}

.up-addr__phone {
  font-size: 13px;
  color: var(--muted);
  background: rgba(0, 0, 0, 0.04);
  padding: 2px 8px;
  border-radius: 999px;
}

.up-addr__tag {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: var(--brand);
}

.up-addr__detail {
  margin: 0;
  font-size: 14px;
  color: var(--muted);
  line-height: 1.6;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.up-addr__region {
  font-weight: 500;
  color: var(--ink);
}

.up-addr__street {
  color: var(--muted);
}

.up-addr__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.up-addr__btn {
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.up-addr__btn:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: rgba(217, 95, 45, 0.04);
}

.up-addr__btn--default:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.up-addr__btn--del:hover {
  border-color: #c33;
  color: #c33;
  background: rgba(204, 51, 51, 0.04);
}

/* Tab */
.up-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  border-bottom: 2px solid var(--line);
}

.up-tab {
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
}

.up-tab:hover {
  color: var(--brand);
}

.up-tab.active {
  color: var(--brand);
  border-bottom-color: var(--brand);
  font-weight: 700;
}

/* 商品卡片网格 */
.up-product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 14px;
}

.up-product-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  background: var(--panel);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.up-product-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
}

.up-product-card__image {
  height: 140px;
  background: #f8f4ef;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.up-product-card__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.up-product-card__noimg {
  font-size: 13px;
  color: var(--muted);
}

.up-product-card__body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.up-product-card__name {
  font-size: 13px;
  margin: 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--ink);
}

.up-product-card__price {
  font-size: 16px;
  font-weight: 700;
  color: var(--brand);
}

.up-product-card__cat {
  font-size: 11px;
  color: var(--muted);
  padding: 1px 6px;
  background: rgba(217, 95, 45, 0.08);
  border-radius: 4px;
  width: fit-content;
}

.up-product-card__time {
  font-size: 11px;
  color: var(--muted);
}

.up-product-card__remove {
  margin: 0 12px 12px;
  padding: 6px 0;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.up-product-card__remove:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: rgba(217, 95, 45, 0.06);
}

/* 弹窗 */
.up-modal-overlay {
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

.up-modal {
  width: min(560px, 100%);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.3);
}

.up-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--line);
}

.up-modal__header h2 {
  font-size: 18px;
  margin: 0;
}

.up-modal__title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.up-modal__icon {
  width: 24px;
  height: 24px;
  color: var(--brand);
  display: flex;
  align-items: center;
  justify-content: center;
}

.up-modal__icon svg {
  width: 100%;
  height: 100%;
}

.up-modal--address {
  width: min(520px, 100%);
}

.up-modal__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.06);
  font-size: 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.up-modal__close:hover {
  background: rgba(0, 0, 0, 0.14);
}

.up-modal__body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 表单 */
.up-form-section__label {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 10px;
  padding-left: 10px;
  border-left: 3px solid var(--brand);
}

.up-form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.up-form-row--3 {
  grid-template-columns: repeat(3, 1fr);
}

.up-form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.up-form-field label {
  font-size: 13px;
  color: var(--muted);
  font-weight: 600;
}

.up-form__required {
  color: var(--brand);
  margin-left: 2px;
}

.up-form-field input,
.up-form-field textarea {
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  background: var(--panel);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.up-form-field textarea {
  resize: vertical;
  line-height: 1.5;
}

.up-form-field input:focus,
.up-form-field textarea:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

.up-form-check {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--ink);
  cursor: pointer;
  padding: 4px 0;
}

.up-form-check input[type='checkbox'] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.up-form-check__box {
  width: 20px;
  height: 20px;
  border: 2px solid var(--line);
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.up-form-check__box::after {
  content: '✓';
  font-size: 13px;
  color: #fff;
  opacity: 0;
  transform: scale(0.8);
  transition: all 0.2s;
}

.up-form-check input[type='checkbox']:checked + .up-form-check__box {
  background: var(--brand);
  border-color: var(--brand);
}

.up-form-check input[type='checkbox']:checked + .up-form-check__box::after {
  opacity: 1;
  transform: scale(1);
}

/* 按钮 */
.up-btn {
  padding: 10px 24px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.up-btn--ghost {
  color: var(--muted);
  background: transparent;
  border-color: var(--line);
}

.up-btn--ghost:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.up-btn--primary {
  color: #fff;
  background: var(--brand);
  border-color: var(--brand);
}

.up-btn--primary:hover:not(:disabled) {
  background: var(--brand-dark);
}

.up-btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.up-modal__footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 18px 24px;
  border-top: 1px solid var(--line);
}

/* 弹窗过渡 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s;
}

.modal-enter-active .up-modal,
.modal-leave-active .up-modal {
  transition: transform 0.25s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .up-modal,
.modal-leave-to .up-modal {
  transform: scale(0.95) translateY(20px);
}

/* 响应式 */
@media (max-width: 768px) {
  .up-user-card {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }

  .up-user-card__meta {
    justify-content: center;
  }

  .up-quick-entry {
    grid-template-columns: 1fr;
  }

  .up-addr {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
  }

  .up-addr__main {
    width: 100%;
  }

  .up-addr__actions {
    width: 100%;
    justify-content: flex-end;
  }

  .up-form-row,
  .up-form-row--3 {
    grid-template-columns: 1fr !important;
  }

  .up-product-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
}
</style>
