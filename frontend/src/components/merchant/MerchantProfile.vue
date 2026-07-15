<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  UserCircleIcon,
  EnvelopeIcon,
  PhoneIcon,
  CalendarIcon,
  ShieldCheckIcon,
  PencilIcon,
  CameraIcon,
} from '@heroicons/vue/24/outline'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const emit = defineEmits<{
  (e: 'update:user-info', info: Record<string, unknown>): void
}>()

interface UserInfo {
  id: number
  username: string
  nickname: string
  phone: string | null
  email: string | null
  avatar: string | null
  role: string
  created_at: string
}

const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const user = ref<UserInfo | null>(null)
const editVisible = ref(false)
const editForm = ref({ nickname: '', phone: '', email: '' })
const avatarInput = ref<HTMLInputElement | null>(null)

function authHeaders(extra: Record<string, string> = {}): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

function showMessage(text: string, type: 'success' | 'error' = 'success') {
  message.value = { text, type }
  setTimeout(() => {
    message.value = null
  }, 3000)
}

async function loadProfile() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders() })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    user.value = data.user || data
  } catch (e) {
    showMessage(e instanceof Error ? e.message : '加载资料失败', 'error')
  } finally {
    loading.value = false
  }
}

function openEdit() {
  if (!user.value) return
  editForm.value = {
    nickname: user.value.nickname || '',
    phone: user.value.phone || '',
    email: user.value.email || '',
  }
  editVisible.value = true
}

async function saveProfile() {
  saving.value = true
  try {
    const res = await fetch(`${API_BASE}/api/auth/profile`, {
      method: 'PUT',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(editForm.value),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    const data = await res.json()
    const updated = data.user || { ...user.value, ...editForm.value }
    user.value = updated as UserInfo
    syncLocalStorage(updated)
    emit('update:user-info', updated)
    editVisible.value = false
    showMessage('资料保存成功')
  } catch (e) {
    showMessage(e instanceof Error ? e.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

function triggerAvatar() {
  avatarInput.value?.click()
}

async function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !user.value) return

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/api/auth/avatar`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    const data = await res.json()
    const updated = { ...user.value, avatar: data.avatar || user.value.avatar }
    user.value = updated as UserInfo
    syncLocalStorage(updated)
    emit('update:user-info', updated)
    showMessage('头像更新成功')
  } catch (e) {
    showMessage(e instanceof Error ? e.message : '头像上传失败', 'error')
  } finally {
    uploading.value = false
    if (input) input.value = ''
  }
}

function syncLocalStorage(info: Record<string, unknown>) {
  const stored = localStorage.getItem('userInfo')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      localStorage.setItem('userInfo', JSON.stringify({ ...parsed, ...info }))
    } catch {
      // ignore
    }
  }
}

function formatTime(iso?: string | null): string {
  if (!iso) return '-'
  return iso.slice(0, 19).replace('T', ' ')
}

onMounted(() => {
  loadProfile()
})
</script>

<template>
  <div class="space-y-6 animate-fade-in-up">
    <div
      v-if="message"
      :class="[
        'rounded-xl px-4 py-3 text-sm font-medium',
        message.type === 'success'
          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
          : 'bg-rose-50 text-rose-700 border border-rose-100',
      ]"
    >
      {{ message.text }}
    </div>

    <div v-if="loading" class="flex flex-col items-center justify-center py-20 text-gray-400">
      <div class="w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-3"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="user" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 左侧资料卡 -->
      <div class="lg:col-span-1">
        <div class="bg-white rounded-2xl border border-primary-light/50 shadow-card p-6 text-center">
          <div class="relative inline-block mx-auto mb-4">
            <div class="w-28 h-28 rounded-full overflow-hidden border-4 border-primary-light shadow-lg mx-auto">
              <img
                v-if="user.avatar"
                :src="user.avatar"
                alt="avatar"
                class="w-full h-full object-cover"
              />
              <div
                v-else
                class="w-full h-full bg-gradient-to-br from-primary to-accent-blue flex items-center justify-center text-3xl font-bold text-white"
              >
                {{ (user.nickname || user.username || 'M').charAt(0).toUpperCase() }}
              </div>
            </div>
            <button
              @click="triggerAvatar"
              :disabled="uploading"
              class="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center shadow-md hover:bg-primary-dark transition-colors disabled:opacity-60"
            >
              <CameraIcon class="w-4 h-4" />
            </button>
            <input
              ref="avatarInput"
              type="file"
              accept="image/*"
              class="hidden"
              @change="handleAvatarChange"
            />
          </div>
          <h3 class="text-xl font-bold text-gray-800">{{ user.nickname || user.username }}</h3>
          <p class="text-sm text-primary font-medium mt-1">商家管理员</p>
          <p class="text-xs text-gray-400 mt-1">@{{ user.username }}</p>

          <button
            @click="openEdit"
            class="mt-6 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-primary text-primary hover:bg-primary hover:text-white transition-all text-sm font-medium"
          >
            <PencilIcon class="w-4 h-4" />
            编辑资料
          </button>
        </div>
      </div>

      <!-- 右侧详情 -->
      <div class="lg:col-span-2">
        <div class="bg-white rounded-2xl border border-primary-light/50 shadow-card p-6">
          <h4 class="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
            <UserCircleIcon class="w-5 h-5 text-primary" />
            账号信息
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                <UserCircleIcon class="w-5 h-5" />
              </div>
              <div>
                <p class="text-xs text-gray-400 mb-0.5">用户名</p>
                <p class="text-sm font-semibold text-gray-800">{{ user.username }}</p>
              </div>
            </div>
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                <ShieldCheckIcon class="w-5 h-5" />
              </div>
              <div>
                <p class="text-xs text-gray-400 mb-0.5">角色</p>
                <p class="text-sm font-semibold text-gray-800">商家管理员</p>
              </div>
            </div>
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                <PhoneIcon class="w-5 h-5" />
              </div>
              <div>
                <p class="text-xs text-gray-400 mb-0.5">手机号</p>
                <p class="text-sm font-semibold text-gray-800">{{ user.phone || '未填写' }}</p>
              </div>
            </div>
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                <EnvelopeIcon class="w-5 h-5" />
              </div>
              <div>
                <p class="text-xs text-gray-400 mb-0.5">邮箱</p>
                <p class="text-sm font-semibold text-gray-800">{{ user.email || '未填写' }}</p>
              </div>
            </div>
            <div class="flex items-start gap-3 md:col-span-2">
              <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
                <CalendarIcon class="w-5 h-5" />
              </div>
              <div>
                <p class="text-xs text-gray-400 mb-0.5">注册时间</p>
                <p class="text-sm font-semibold text-gray-800">{{ formatTime(user.created_at) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

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
            :disabled="saving"
            class="px-5 py-2 rounded-xl text-sm font-medium bg-primary text-white hover:bg-primary-dark transition-colors disabled:opacity-60"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
