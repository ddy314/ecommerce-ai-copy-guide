<script setup lang="ts">
import { ref, computed, provide } from 'vue'
import { Button, Card, Layout, LayoutContent } from 'ant-design-vue'
import { motion } from 'motion-v'
import NavBar from '../common/NavBar.vue'
import ChatWidget from '../common/ChatWidget.vue'
import CustomerService from './CustomerService.vue'
import {
  CustomerServiceOutlined,
  HomeOutlined,
  ShopOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'

interface UserInfo {
  username: string
  role: 'user' | 'merchant'
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

type UserPage = 'home' | 'products' | 'profile' | 'customer-service'

const menuItems: { key: UserPage; label: string; icon: any }[] = [
  { key: 'home', label: '首页', icon: HomeOutlined },
  { key: 'products', label: '商品浏览', icon: ShopOutlined },
  { key: 'customer-service', label: '客服咨询', icon: CustomerServiceOutlined },
  { key: 'profile', label: '个人中心', icon: UserOutlined },
]

const activePage = ref<UserPage>('home')

const activeMenu = computed(() =>
  menuItems.find((m) => m.key === activePage.value) ?? menuItems[0],
)

function selectPage(key: string) {
  activePage.value = key as UserPage
}

// 用于从 AI 聊天跳转到特定商品详情
const targetProductId = ref<number | null>(null)

function navigateToProduct(productId: number) {
  targetProductId.value = productId
  activePage.value = 'products'
}

// 跳转到客服并带商品信息
const csProductId = ref<number | null>(null)

function navigateToCustomerService(productId?: number) {
  if (productId) csProductId.value = productId
  activePage.value = 'customer-service'
}

// 向子组件提供页面跳转方法
provide('navigate', selectPage)
provide('navigateToProduct', navigateToProduct)
provide('navigateToCustomerService', navigateToCustomerService)
provide('targetProductId', targetProductId)
provide('csProductId', csProductId)

function handleLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('userInfo')
  emit('logout')
}

</script>

<template>
  <Layout class="min-h-screen">
    <NavBar
      :user-info="props.userInfo"
      :active-page="activePage"
      @select-page="selectPage"
      @logout="handleLogout"
    />

    <LayoutContent class="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
      <!-- 首页 -->
      <div v-if="activePage === 'home'" class="fade-in-up space-y-8">
        <!-- Hero -->
        <section class="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-primary to-primary-dark text-white p-8 sm:p-12 lg:p-16 shadow-card">
          <motion.div
            class="hero-orb hero-orb--one absolute w-64 h-64 rounded-full bg-white/10 blur-3xl pointer-events-none"
            :animate="{ x: [0, 24, 0], y: [0, 20, 0] }"
            :transition="{ duration: 14, repeat: Infinity, ease: 'easeInOut' }"
          />
          <motion.div
            class="hero-orb hero-orb--two absolute w-80 h-80 rounded-full bg-accent-blue/20 blur-3xl pointer-events-none"
            :animate="{ x: [0, -28, 0], y: [0, -18, 0] }"
            :transition="{ duration: 17, repeat: Infinity, ease: 'easeInOut' }"
          />
          <div class="relative z-10 max-w-2xl">
            <p class="text-xs sm:text-sm font-bold tracking-widest uppercase text-white/80 mb-4">
              欢迎回来，{{ props.userInfo.nickname || props.userInfo.username }}
            </p>
            <h1 class="text-3xl sm:text-4xl lg:text-5xl font-extrabold leading-tight mb-6">
              发现好物，AI 智能导购为您推荐
            </h1>
            <p class="text-sm sm:text-base text-white/85 leading-relaxed mb-8 max-w-xl">
              浏览真实电商商品数据，AI 智能导购根据您的需求推荐最合适的商品，右下角随时召唤智能助手解答疑问。
            </p>
            <div class="flex flex-wrap gap-4">
              <Button
                size="large"
                @click="selectPage('products')"
                class="!border-0 !font-semibold !text-violet-700"
              >
                开始购物
              </Button>
              <Button
                size="large"
                ghost
                @click="selectPage('customer-service')"
                class="!font-semibold"
              >
                联系客服
              </Button>
            </div>
          </div>
        </section>

        <!-- 功能卡片 -->
        <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <motion.div
            v-for="item in menuItems"
            :key="item.key"
            @click="selectPage(item.key)"
            :while-hover="{ y: -6, scale: 1.01 }"
            :while-press="{ scale: 0.985 }"
            :transition="{ type: 'spring', stiffness: 380, damping: 26 }"
            class="cursor-pointer"
          >
            <Card :bordered="false" class="h-full">
              <div class="mb-4 grid h-12 w-12 place-items-center rounded-xl bg-violet-600 text-xl text-white shadow-lg shadow-violet-200">
                <component :is="item.icon" />
              </div>
              <h3 class="mb-1 text-lg font-bold text-slate-800">{{ item.label }}</h3>
              <p class="text-sm text-slate-500">点击进入{{ item.label }}页面</p>
            </Card>
          </motion.div>
        </section>

        <!-- 平台亮点 -->
        <section class="bg-white rounded-2xl p-6 sm:p-8 border border-primary-light/50 shadow-card">
          <h3 class="text-xl font-bold text-gray-800 mb-6 flex items-center">
            <span class="w-1.5 h-5 rounded-full bg-primary mr-3"></span>
            平台亮点
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <div class="text-center p-6 rounded-2xl bg-primary-light/30 border border-primary-light/40 hover:-translate-y-1 transition-transform">
              <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-accent-blue text-white flex items-center justify-center text-xl font-bold mx-auto mb-4 shadow-lg shadow-primary/20">
                AI
              </div>
              <h4 class="font-bold text-gray-800 mb-2">智能导购</h4>
              <p class="text-sm text-gray-500 leading-relaxed">基于 RAG 检索增强，根据您的需求精准推荐商品</p>
            </div>
            <div class="text-center p-6 rounded-2xl bg-accent-blue/10 border border-accent-blue/20 hover:-translate-y-1 transition-transform">
              <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent-blue to-primary text-white flex items-center justify-center text-xl font-bold mx-auto mb-4 shadow-lg shadow-accent-blue/20">
                数
              </div>
              <h4 class="font-bold text-gray-800 mb-2">真实数据</h4>
              <p class="text-sm text-gray-500 leading-relaxed">覆盖数码、美妆、母婴等海量真实电商商品</p>
            </div>
            <div class="text-center p-6 rounded-2xl bg-green-50 border border-green-100 hover:-translate-y-1 transition-transform">
              <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-green-400 to-emerald-500 text-white flex items-center justify-center text-xl font-bold mx-auto mb-4 shadow-lg shadow-green-200">
                购
              </div>
              <h4 class="font-bold text-gray-800 mb-2">一站式购物</h4>
              <p class="text-sm text-gray-500 leading-relaxed">浏览、收藏、加购、下单、支付全流程闭环体验</p>
            </div>
          </div>
        </section>
      </div>

      <!-- 客服咨询 -->
      <CustomerService v-else-if="activePage === 'customer-service'" />

      <!-- 其它页面 -->
      <template v-else>
        <div class="mb-6 fade-in-up">
          <h2 class="text-2xl font-bold text-gray-800 flex items-center space-x-2">
            <component :is="activeMenu.icon" class="w-6 h-6 text-primary" />
            <span>{{ activeMenu.label }}</span>
          </h2>
        </div>
        <slot :page="activePage">
          <div class="bg-white rounded-2xl border border-primary-light/50 p-16 text-center text-gray-500 min-h-[420px] flex flex-col items-center justify-center fade-in-up">
            <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-primary-dark text-white flex items-center justify-center text-3xl font-bold mb-4 shadow-lg">
              {{ activeMenu.label.charAt(0) }}
            </div>
            <h3 class="text-xl font-bold text-gray-800 mb-2">{{ activeMenu.label }}</h3>
            <p>该功能页面正在建设中，敬请期待。</p>
          </div>
        </slot>
      </template>
    </LayoutContent>

    <ChatWidget />
  </Layout>
</template>

<style scoped>
.hero-orb--one {
  left: 8%;
  top: 15%;
}

.hero-orb--two {
  left: 82%;
  top: 62%;
}
</style>
