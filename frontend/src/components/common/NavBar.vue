<script setup lang="ts">
import {
  HomeIcon,
  ShoppingBagIcon,
  ChatBubbleLeftRightIcon,
  UserIcon,
  SparklesIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/vue/24/outline'
import { resolveAvatarUrl } from '../../utils/avatar'

interface UserInfo {
  username: string
  role: 'user' | 'merchant'
  nickname?: string
  avatar?: string
}

const props = defineProps<{
  userInfo: UserInfo
  activePage: string
}>()

const emit = defineEmits<{
  (e: 'select-page', page: string): void
  (e: 'logout'): void
}>()

const menu = [
  { key: 'home', name: '首页', icon: HomeIcon },
  { key: 'products', name: '商品浏览', icon: ShoppingBagIcon },
  { key: 'customer-service', name: '客服咨询', icon: ChatBubbleLeftRightIcon },
  { key: 'profile', name: '个人中心', icon: UserIcon },
]

function isActive(path: string) {
  return props.activePage === path
}
</script>

<template>
  <nav class="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-primary-light/50 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16 items-center">
        <div class="flex items-center space-x-8">
          <button
            @click="emit('select-page', 'home')"
            class="flex items-center space-x-2 text-xl font-bold bg-gradient-to-r from-primary to-primary-dark bg-clip-text text-transparent"
          >
            <SparklesIcon class="w-6 h-6 text-primary" />
            <span>AI电商助手</span>
          </button>
          <div class="hidden md:flex space-x-1">
            <button
              v-for="item in menu"
              :key="item.key"
              @click="emit('select-page', item.key)"
              :class="isActive(item.key)
                ? 'text-primary bg-primary-light'
                : 'text-gray-600 hover:text-primary hover:bg-primary-light/50'"
              class="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200"
            >
              <component :is="item.icon" class="w-4 h-4" />
              <span>{{ item.name }}</span>
            </button>
          </div>
        </div>
        <div class="flex items-center space-x-4">
          <div class="flex items-center space-x-2 bg-white rounded-full pl-2 pr-3 py-1 shadow-sm border border-primary-light/50">
            <img
              v-if="props.userInfo.avatar"
              :src="resolveAvatarUrl(props.userInfo.avatar)"
              class="w-8 h-8 rounded-full object-cover"
            />
            <div
              v-else
              class="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent-blue flex items-center justify-center text-white text-xs font-bold"
            >
              {{ (props.userInfo.nickname || props.userInfo.username || 'U').charAt(0).toUpperCase() }}
            </div>
            <span class="text-sm text-gray-700 font-medium hidden sm:block">{{ props.userInfo.nickname || props.userInfo.username }}</span>
          </div>
          <button
            @click="emit('logout')"
            class="flex items-center space-x-1 text-sm text-red-500 hover:text-white hover:bg-red-500 px-3 py-1.5 rounded-full transition-all duration-200"
          >
            <ArrowRightOnRectangleIcon class="w-4 h-4" />
            <span class="hidden sm:inline">退出</span>
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>
