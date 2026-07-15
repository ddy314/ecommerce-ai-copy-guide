<script setup lang="ts">
import { ref, computed } from 'vue'
import SideBar from '../common/SideBar.vue'
import {
  ChartPieIcon,
  CubeIcon,
  SparklesIcon,
  BookOpenIcon,
  ChatBubbleLeftRightIcon,
  VideoCameraIcon,
  ClipboardDocumentListIcon,
  UsersIcon,
} from '@heroicons/vue/24/outline'

interface UserInfo {
  username: string
  role: string
  nickname?: string
  avatar?: string
  [key: string]: unknown
}

const props = defineProps<{
  userInfo: UserInfo
}>()

const emit = defineEmits<{
  (e: 'logout'): void
}>()

type MerchantPage =
  | 'dashboard'
  | 'products'
  | 'orders'
  | 'copy'
  | 'knowledge'
  | 'review'
  | 'live'
  | 'qa-stats'
  | 'users'
  | 'profile'
  | 'customer-service'

const menuItems: { key: MerchantPage; name: string; icon: any; desc: string }[] = [
  { key: 'dashboard', name: '数据看板', icon: ChartPieIcon, desc: '收入组成与商品流量监测' },
  { key: 'products', name: '商品管理', icon: CubeIcon, desc: '管理商品信息与上下架' },
  { key: 'orders', name: '订单管理', icon: ClipboardDocumentListIcon, desc: '查看订单并发货管理' },
  { key: 'copy', name: '文案生成', icon: SparklesIcon, desc: 'AI 生成商品营销文案' },
  { key: 'knowledge', name: '知识库管理', icon: BookOpenIcon, desc: '维护商品知识库内容' },
  { key: 'review', name: '评论分析', icon: ChatBubbleLeftRightIcon, desc: '评论情感与痛点分析' },
  { key: 'live', name: '直播脚本', icon: VideoCameraIcon, desc: '生成直播带货话术' },
  { key: 'qa-stats', name: '用户问答统计', icon: ChatBubbleLeftRightIcon, desc: '用户咨询数据分析' },
  { key: 'users', name: '用户管理', icon: UsersIcon, desc: '管理系统用户账号与权限' },
  { key: 'customer-service', name: '客服管理', icon: ChatBubbleLeftRightIcon, desc: '回复用户咨询消息' },
]

const activePage = ref<MerchantPage>('dashboard')

const activeMenu = computed(() => {
  if (activePage.value === 'profile') {
    return { name: '个人中心', desc: '商家账号资料管理' }
  }
  return menuItems.find((m) => m.key === activePage.value)
})

function selectPage(key: string) {
  activePage.value = key as MerchantPage
}

function handleLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('userInfo')
  emit('logout')
}

function handleAvatarUpdated(avatar: string) {
  props.userInfo.avatar = avatar
  const stored = localStorage.getItem('userInfo')
  if (stored) {
    try {
      const info = JSON.parse(stored)
      info.avatar = avatar
      localStorage.setItem('userInfo', JSON.stringify(info))
    } catch {
      // ignore
    }
  }
}
</script>

<template>
  <div class="min-h-screen flex bg-page">
    <SideBar
      :user-info="props.userInfo"
      :active-page="activePage"
      :menu="menuItems"
      @select-page="selectPage"
      @logout="handleLogout"
      @avatar-updated="handleAvatarUpdated"
    />
    <main class="flex-1 p-6 overflow-auto">
      <div v-if="activeMenu" class="mb-6 fade-in-up">
        <h2 class="text-2xl font-bold text-gray-800">{{ activeMenu.name }}</h2>
        <p class="text-sm text-gray-500 mt-1">{{ activeMenu.desc }}</p>
      </div>
      <div class="bg-white rounded-2xl border border-primary-light/50 p-6 min-h-[420px] shadow-card fade-in-up">
        <slot :page="activePage">
          <div class="h-full flex flex-col items-center justify-center text-center text-gray-500 py-16">
            <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-primary-dark text-white flex items-center justify-center text-3xl font-bold mb-4 shadow-lg">
              {{ activeMenu?.name.charAt(0) || '商' }}
            </div>
            <h3 class="text-xl font-bold text-gray-800 mb-2">{{ activeMenu?.name || '商家后台' }}</h3>
            <p>该功能页面正在建设中，敬请期待。</p>
          </div>
        </slot>
      </div>
    </main>
  </div>
</template>
