<script setup lang="ts">
import { ref, computed } from 'vue'

interface UserInfo {
  username: string
  role: string
  nickname?: string
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

const menuItems: { key: MerchantPage; label: string; icon: string; desc: string }[] = [
  { key: 'dashboard', label: '收入面板', icon: '收', desc: '收入组成与商品流量监测' },
  { key: 'products', label: '商品管理', icon: '品', desc: '管理商品信息与上下架' },
  { key: 'orders', label: '订单管理', icon: '单', desc: '查看订单并发货管理' },
  { key: 'copy', label: '文案生成', icon: '文', desc: 'AI 生成商品营销文案' },
  { key: 'knowledge', label: '知识库管理', icon: '库', desc: '维护商品知识库内容' },
  { key: 'review', label: '评论分析', icon: '评', desc: '评论情感与痛点分析' },
  { key: 'live', label: '直播脚本', icon: '播', desc: '生成直播带货话术' },
  { key: 'qa-stats', label: '用户问答统计', icon: '问', desc: '用户咨询数据分析' },
  { key: 'users', label: '用户管理', icon: '人', desc: '管理系统用户账号与权限' },
]

const activePage = ref<MerchantPage>('products')

const activeMenu = computed(() =>
  menuItems.find((m) => m.key === activePage.value) ?? menuItems[0],
)

function selectPage(key: MerchantPage) {
  activePage.value = key
}

function handleLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('userInfo')
  emit('logout')
}
</script>

<template>
  <div class="merchant-layout">
    <!-- 主体内容 -->
    <div class="m-body">
      <!-- 侧边菜单 -->
      <aside class="m-sidebar">
        <div class="m-sidebar__brand">
          <span class="m-sidebar__brand-icon">AI</span>
          <span class="m-sidebar__brand-text">商家管理后台</span>
        </div>
        <div class="m-sidebar__title">功能菜单</div>
        <ul class="m-sidebar__list">
          <li
            v-for="item in menuItems"
            :key="item.key"
            :class="['m-sidebar__item', { active: activePage === item.key }]"
            @click="selectPage(item.key)"
          >
            <span class="m-sidebar__icon">{{ item.icon }}</span>
            <div class="m-sidebar__text">
              <span class="m-sidebar__label">{{ item.label }}</span>
              <span class="m-sidebar__desc">{{ item.desc }}</span>
            </div>
          </li>
        </ul>
        <!-- 底部用户信息 -->
        <div class="m-sidebar__footer">
          <div class="m-user">
            <span class="m-user__avatar">{{ props.userInfo.nickname?.charAt(0) || props.userInfo.username.charAt(0) }}</span>
            <div class="m-user__info">
              <span class="m-user__name">{{ props.userInfo.nickname || props.userInfo.username }}</span>
              <span class="m-user__role">商家管理员</span>
            </div>
          </div>
          <button class="m-logout" @click="handleLogout">退出登录</button>
        </div>
      </aside>

      <!-- 内容区域 -->
      <main class="m-content">
        <div class="m-content__head">
          <div>
            <h2>{{ activeMenu.label }}</h2>
            <p>{{ activeMenu.desc }}</p>
          </div>
        </div>

        <div class="m-content__body">
          <!-- 子页面通过 slot 注入；未匹配时展示占位 -->
          <slot :page="activePage">
            <div class="m-placeholder">
              <span class="m-placeholder__icon">{{ activeMenu.icon }}</span>
              <h3>{{ activeMenu.label }}</h3>
              <p>该功能页面正在建设中，敬请期待。</p>
              <p class="m-placeholder__hint">当前页面标识：<code>{{ activePage }}</code></p>
            </div>
          </slot>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.merchant-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 顶部导航 */
/* 侧边栏品牌区 */
.m-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 10px 16px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 12px;
}

.m-sidebar__brand-icon {
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 10px;
  color: #fffaf0;
  font-weight: 800;
  font-size: 14px;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  flex-shrink: 0;
}

.m-sidebar__brand-text {
  font-size: 15px;
  font-weight: 800;
  color: var(--brand-dark);
  letter-spacing: -0.01em;
}

/* 用户信息 */
.m-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.m-user__avatar {
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 50%;
  color: #fffaf0;
  font-weight: 700;
  font-size: 15px;
  background: var(--brand-dark);
  flex-shrink: 0;
}

.m-user__info {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
  min-width: 0;
}

.m-user__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.m-user__role {
  font-size: 12px;
  color: var(--muted);
}

.m-logout {
  padding: 8px 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
  margin-top: 8px;
}

.m-logout:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: rgba(217, 95, 45, 0.06);
}

.m-sidebar__footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

/* 主体 */
.m-body {
  flex: 1;
  width: min(1440px, 100% - 32px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 24px;
  padding: 24px 0 48px;
}

/* 侧边菜单 */
.m-sidebar {
  position: sticky;
  top: 24px;
  align-self: start;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel);
  padding: 16px;
  backdrop-filter: blur(18px);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
}

.m-sidebar__title {
  padding: 4px 10px 12px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}

.m-sidebar__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.m-sidebar__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.m-sidebar__item:hover {
  background: rgba(217, 95, 45, 0.06);
}

.m-sidebar__item.active {
  background: rgba(217, 95, 45, 0.1);
  box-shadow: 0 0 0 1px var(--brand) inset;
}

.m-sidebar__icon {
  display: inline-grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 10px;
  color: #fffaf0;
  font-weight: 700;
  font-size: 14px;
  background: var(--brand-dark);
}

.m-sidebar__item.active .m-sidebar__icon {
  background: var(--brand);
}

.m-sidebar__text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.m-sidebar__label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.m-sidebar__desc {
  font-size: 12px;
  color: var(--muted);
}

/* 内容区 */
.m-content {
  min-width: 0;
}

.m-content__head {
  margin-bottom: 20px;
}

.m-content__head h2 {
  margin: 0 0 6px;
  font-size: 24px;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.m-content__head p {
  margin: 0;
  font-size: 14px;
  color: var(--muted);
}

.m-content__body {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel);
  padding: 24px;
  min-height: 420px;
  backdrop-filter: blur(18px);
}

/* 占位 */
.m-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}

.m-placeholder__icon {
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

.m-placeholder h3 {
  margin: 0 0 8px;
  font-size: 20px;
  color: var(--ink);
}

.m-placeholder p {
  margin: 0;
  font-size: 14px;
}

.m-placeholder__hint {
  margin-top: 16px !important;
  font-size: 13px !important;
}

.m-placeholder code {
  display: inline-block;
  margin-left: 6px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand-dark);
  font-size: 12px;
}

@media (max-width: 1100px) {
  .m-body {
    grid-template-columns: 1fr;
  }

  .m-sidebar {
    position: static;
  }

  .m-sidebar__list {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .m-sidebar__item {
    flex: 1 1 auto;
    min-width: 200px;
  }
}

@media (max-width: 760px) {
  .m-header__inner {
    flex-wrap: wrap;
    gap: 12px;
  }

  .m-menu {
    order: 3;
    width: 100%;
    justify-content: flex-start;
    overflow-x: auto;
  }

  .m-user__info {
    display: none;
  }
}
</style>
