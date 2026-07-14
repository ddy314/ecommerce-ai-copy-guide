<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Login from './components/Login.vue'
import MerchantLayout from './components/merchant/MerchantLayout.vue'
import UserLayout from './components/user/UserLayout.vue'
// 复用已有功能组件作为商家后台的子页面
import CopyGenerator from './components/CopyGenerator.vue'
import ReviewAnalyzer from './components/ReviewAnalyzer.vue'
import LiveScriptGenerator from './components/LiveScriptGenerator.vue'
// 用户前台页面组件
import ProductBrowse from './components/user/ProductBrowse.vue'
import UserProfile from './components/user/UserProfile.vue'
// 商家后台新增功能组件
import ProductManage from './components/merchant/ProductManage.vue'
import KnowledgeBaseManage from './components/merchant/KnowledgeBaseManage.vue'
import QAStats from './components/merchant/QAStats.vue'
import UserManage from './components/merchant/UserManage.vue'
import OrderManage from './components/merchant/OrderManage.vue'
import RevenueDashboard from './components/merchant/RevenueDashboard.vue'
import MerchantCustomerService from './components/merchant/MerchantCustomerService.vue'

// 应用视图状态：未登录 / 商家后台 / 用户前台
type AppView = 'login' | 'merchant' | 'user'

interface UserInfo {
  username: string
  role: 'user' | 'merchant'
  nickname?: string
  token?: string
  [key: string]: unknown
}

const currentView = ref<AppView>('login')
const userInfo = ref<UserInfo | null>(null)

// 占位页面配置（子页面组件尚未创建时展示）
interface PlaceholderConfig {
  icon: string
  title: string
  desc: string
  tag: string
}

const merchantPlaceholders: Record<string, PlaceholderConfig> = {}

// 应用启动时检查本地登录态，实现刷新保持登录
onMounted(() => {
  const stored = localStorage.getItem('userInfo')
  if (stored) {
    try {
      const info = JSON.parse(stored) as UserInfo
      if (info && info.username && info.role) {
        userInfo.value = info
        currentView.value = info.role === 'merchant' ? 'merchant' : 'user'
      } else {
        throw new Error('无效的用户信息')
      }
    } catch {
      localStorage.removeItem('userInfo')
      localStorage.removeItem('token')
      currentView.value = 'login'
    }
  }
})

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

      <!-- 占位 -->
      <div
        v-else-if="merchantPlaceholders[page as string]"
        class="page-placeholder"
      >
        <span class="page-placeholder__icon">{{ merchantPlaceholders[page as string].icon }}</span>
        <h3>{{ merchantPlaceholders[page as string].title }}</h3>
        <p>{{ merchantPlaceholders[page as string].desc }}</p>
        <p class="page-placeholder__hint">
          组件 <code>{{ merchantPlaceholders[page as string].tag }}</code> 待实现
        </p>
      </div>
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
</template>

<style>
/* App.vue 使用全局样式占位（非 scoped），以便子组件继承项目 CSS 变量体系 */
</style>

<style scoped>
/* 子页面占位样式 */
.page-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 60px 20px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel);
  color: var(--muted);
  min-height: 420px;
}

.page-placeholder__icon {
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

.page-placeholder h3 {
  margin: 0 0 8px;
  font-size: 20px;
  color: var(--ink);
}

.page-placeholder p {
  margin: 0;
  font-size: 14px;
}

.page-placeholder__hint {
  margin-top: 16px !important;
  font-size: 13px !important;
}

.page-placeholder code {
  display: inline-block;
  margin: 0 4px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand-dark);
  font-size: 12px;
}
</style>
