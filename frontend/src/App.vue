<script setup lang="ts">
import { defineAsyncComponent, ref } from 'vue'
import { ConfigProvider } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import { AnimatePresence, motion } from 'motion-v'
import Login from './components/Login.vue'
import { appTheme, pageMotion } from './theme'

// 登录后再按角色和页面加载业务代码，避免首屏下载整套商家端与用户端。
const MerchantLayout = defineAsyncComponent(() => import('./components/merchant/MerchantLayout.vue'))
const UserLayout = defineAsyncComponent(() => import('./components/user/UserLayout.vue'))
const CopyGenerator = defineAsyncComponent(() => import('./components/CopyGenerator.vue'))
const ReviewAnalyzer = defineAsyncComponent(() => import('./components/ReviewAnalyzer.vue'))
const LiveScriptGenerator = defineAsyncComponent(() => import('./components/LiveScriptGenerator.vue'))
const ProductBrowse = defineAsyncComponent(() => import('./components/user/ProductBrowse.vue'))
const UserProfile = defineAsyncComponent(() => import('./components/user/UserProfile.vue'))
const ProductManage = defineAsyncComponent(() => import('./components/merchant/ProductManage.vue'))
const KnowledgeBaseManage = defineAsyncComponent(() => import('./components/merchant/KnowledgeBaseManage.vue'))
const QAStats = defineAsyncComponent(() => import('./components/merchant/QAStats.vue'))
const UserManage = defineAsyncComponent(() => import('./components/merchant/UserManage.vue'))
const OrderManage = defineAsyncComponent(() => import('./components/merchant/OrderManage.vue'))
const RevenueDashboard = defineAsyncComponent(() => import('./components/merchant/RevenueDashboard.vue'))
const MerchantCustomerService = defineAsyncComponent(
  () => import('./components/merchant/MerchantCustomerService.vue'),
)

// 应用视图状态：未登录 / 商家后台 / 用户前台
type AppView = 'login' | 'merchant' | 'user'

interface UserInfo {
  username: string
  role: 'user' | 'merchant'
  nickname?: string
  token?: string
  [key: string]: unknown
}

function restoreSession(): UserInfo | null {
  const stored = localStorage.getItem('userInfo')
  if (!stored) return null

  try {
    const info = JSON.parse(stored) as UserInfo
    if (info?.username && (info.role === 'merchant' || info.role === 'user')) return info
  } catch {
    // 统一在下方清理损坏或过期的本地会话。
  }
  localStorage.removeItem('userInfo')
  localStorage.removeItem('token')
  return null
}

const userInfo = ref<UserInfo | null>(restoreSession())
const currentView = ref<AppView>(
  userInfo.value ? (userInfo.value.role === 'merchant' ? 'merchant' : 'user') : 'login',
)

// 登录成功：根据角色分流
function handleLoginSuccess(info: UserInfo) {
  userInfo.value = info
  currentView.value = info.role === 'merchant' ? 'merchant' : 'user'
}

// 退出登录：回到登录页
function handleLogout() {
  userInfo.value = null
  currentView.value = 'login'
}
</script>

<template>
  <ConfigProvider :locale="zhCN" :theme="appTheme">
    <AnimatePresence mode="wait">
      <motion.div
        :key="currentView"
        class="min-h-screen"
        :initial="pageMotion.initial"
        :animate="pageMotion.animate"
        :exit="pageMotion.exit"
        :transition="pageMotion.transition"
      >
        <!-- 未登录：显示统一登录页 -->
        <Login v-if="currentView === 'login'" @login-success="handleLoginSuccess" />

        <!-- 商家管理员：商家后台 -->
        <MerchantLayout
          v-else-if="currentView === 'merchant' && userInfo"
          :user-info="userInfo"
          @logout="handleLogout"
        >
          <template #default="{ page }">
      <!-- 收入面板 -->
      <RevenueDashboard v-if="page === 'dashboard'" />

      <!-- 商品管理 -->
      <ProductManage v-else-if="page === 'products'" />

      <!-- 订单管理 -->
      <OrderManage v-else-if="page === 'orders'" />

      <!-- 文案生成 -->
      <CopyGenerator v-else-if="page === 'copy'" />

      <!-- 知识库管理 -->
      <KnowledgeBaseManage v-else-if="page === 'knowledge'" />

      <!-- 评论分析 -->
      <ReviewAnalyzer v-else-if="page === 'review'" />

      <!-- 直播脚本 -->
      <LiveScriptGenerator v-else-if="page === 'live'" />

      <!-- 用户问答统计 -->
      <QAStats v-else-if="page === 'qa-stats'" />

      <!-- 用户管理 -->
      <UserManage v-else-if="page === 'users'" />

      <!-- 客服管理 -->
      <MerchantCustomerService v-else-if="page === 'customer-service'" />

          </template>
        </MerchantLayout>

        <!-- 普通用户：用户前台 -->
        <UserLayout
          v-else-if="currentView === 'user' && userInfo"
          :user-info="userInfo"
          @logout="handleLogout"
        >
          <template #default="{ page }">
      <!-- 商品浏览 -->
      <ProductBrowse v-if="page === 'products'" />

      <!-- 个人中心（内含购物车、我的订单等子标签） -->
      <UserProfile v-else-if="page === 'profile'" />
          </template>
        </UserLayout>
      </motion.div>
    </AnimatePresence>
  </ConfigProvider>
</template>
