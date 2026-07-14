<script setup lang="ts">
import { ref } from 'vue'
import {
  SparklesIcon,
  ArrowLeftOnRectangleIcon,
  UserCircleIcon,
} from '@heroicons/vue/24/outline'

interface UserInfo {
  username: string
  role: string
  nickname?: string
  avatar?: string
  [key: string]: unknown
}

interface MenuItem {
  key: string
  name: string
  icon: any
  desc?: string
}

const props = defineProps<{
  userInfo: UserInfo
  activePage: string
  menu: MenuItem[]
  title?: string
  subtitle?: string
}>()

const emit = defineEmits<{
  (e: 'select-page', page: string): void
  (e: 'logout'): void
  (e: 'avatar-updated', avatar: string): void
}>()

function isActive(path: string) {
  return props.activePage === path
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const avatarInput = ref<HTMLInputElement | null>(null)
const avatarLoading = ref(false)

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

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

    const response = await fetch(`${API_BASE}/api/auth/avatar`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${response.status}`)
    }
    const data = await response.json()
    emit('avatar-updated', data.avatar)
  } catch {
    // 静默失败，避免打断导航
  } finally {
    avatarLoading.value = false
    if (input) input.value = ''
  }
}
</script>

<template>
  <aside class="w-64 min-h-screen flex flex-col bg-white text-gray-800 relative overflow-hidden border-r border-primary-light/50">
    <!-- 装饰光晕 -->
    <div class="absolute top-0 left-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2 pointer-events-none"></div>
    <div class="absolute bottom-0 right-0 w-64 h-64 bg-accent-blue/20 rounded-full blur-3xl translate-x-1/2 translate-y-1/2 pointer-events-none"></div>

    <div class="p-6 relative z-10">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent-blue flex items-center justify-center shadow-lg shadow-primary/20">
          <SparklesIcon class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="text-lg font-bold text-gray-800">{{ title || '商家后台' }}</h1>
          <p class="text-xs text-primary">{{ subtitle || 'AI电商运营管理中心' }}</p>
        </div>
      </div>
    </div>

    <nav class="flex-1 px-4 space-y-1.5 relative z-10">
      <button
        v-for="item in menu"
        :key="item.key"
        @click="emit('select-page', item.key)"
        :class="isActive(item.key)
          ? 'bg-primary-light text-primary shadow-sm shadow-primary/10 translate-x-1'
          : 'hover:bg-primary-light/50 hover:translate-x-1 text-gray-600 hover:text-primary'"
        class="w-full text-left flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group"
      >
        <component :is="item.icon" class="w-5 h-5" :class="isActive(item.key) ? 'text-primary' : 'text-primary/70 group-hover:text-primary'" />
        <div class="flex-1 min-w-0">
          <span class="text-sm font-medium">{{ item.name }}</span>
          <p v-if="item.desc" class="text-[11px] text-gray-400 truncate">{{ item.desc }}</p>
        </div>
        <div v-if="isActive(item.key)" class="ml-auto w-1.5 h-1.5 rounded-full bg-primary"></div>
      </button>
    </nav>

    <div class="p-4 relative z-10">
      <div class="bg-page rounded-2xl p-4 border border-primary-light/50">
        <div class="flex items-center space-x-3 mb-3">
          <div class="relative w-10 h-10 cursor-pointer group" @click="triggerAvatarUpload">
            <img
              v-if="props.userInfo.avatar"
              :src="props.userInfo.avatar"
              class="w-10 h-10 rounded-full object-cover"
            />
            <div
              v-else
              class="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-accent-blue flex items-center justify-center text-sm font-bold text-white"
            >
              {{ (props.userInfo.nickname || props.userInfo.username || 'M').charAt(0).toUpperCase() }}
            </div>
            <div
              class="absolute inset-0 rounded-full flex items-center justify-center text-[10px] font-medium text-white bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              {{ avatarLoading ? '...' : '上传' }}
            </div>
            <input
              ref="avatarInput"
              type="file"
              accept="image/*"
              class="hidden"
              @change="handleAvatarChange"
            />
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium truncate">{{ props.userInfo.nickname || props.userInfo.username }}</div>
            <div class="text-xs text-primary">商家管理员</div>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <button
            @click="emit('select-page', 'profile')"
            class="flex items-center justify-center space-x-1 text-primary hover:text-white hover:bg-primary rounded-xl py-2 text-sm transition-all duration-200"
          >
            <UserCircleIcon class="w-4 h-4" />
            <span>个人中心</span>
          </button>
          <button
            @click="emit('logout')"
            class="flex items-center justify-center space-x-1 text-red-500 hover:text-white hover:bg-red-500 rounded-xl py-2 text-sm transition-all duration-200"
          >
            <ArrowLeftOnRectangleIcon class="w-4 h-4" />
            <span>退出</span>
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>
