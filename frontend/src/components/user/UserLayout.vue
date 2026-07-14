<script setup lang="ts">
import { ref, computed, nextTick, provide, onMounted, onUnmounted } from 'vue'

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

type UserPage = 'home' | 'products' | 'profile'

const menuItems: { key: UserPage; label: string; icon: string }[] = [
  { key: 'home', label: '首页', icon: '首' },
  { key: 'products', label: '商品浏览', icon: '品' },
  { key: 'profile', label: '个人中心', icon: '我' },
]

const activePage = ref<UserPage>('home')

// 用于从 AI 聊天跳转到特定商品详情
const targetProductId = ref<number | null>(null)

const activeMenu = computed(() =>
  menuItems.find((m) => m.key === activePage.value) ?? menuItems[0],
)

function selectPage(key: UserPage) {
  activePage.value = key
}

// 跳转到商品浏览页并打开指定商品详情
function navigateToProduct(productId: number) {
  targetProductId.value = productId
  activePage.value = 'products'
}

// 向子组件提供页面跳转方法
provide('navigate', selectPage)
provide('navigateToProduct', navigateToProduct)
provide('targetProductId', targetProductId)

function handleLogout() {
  localStorage.removeItem('token')
  localStorage.removeItem('userInfo')
  emit('logout')
}

// ---------- 悬浮 AI 智能咨询 ----------
interface ProductCard {
  id: number
  name: string
  price: number
  rating: number
  category?: string
  image_url?: string
  brand?: string
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  product?: ProductCard | null
  relatedProducts?: ProductCard[]
}

const aiOpen = ref(false)
const aiInput = ref('')
const aiSending = ref(false)
const chatMessages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    content: '您好！我是电商AI智能导购助手，可以帮您推荐商品、查询价格、对比评价。请问有什么可以帮您？',
  },
])

const chatBodyRef = ref<HTMLElement | null>(null)

// ---------- 面板拖拽与缩放 ----------
const PANEL_DEFAULT_WIDTH = 480
const PANEL_DEFAULT_HEIGHT = 580
const PANEL_MIN_WIDTH = 320
const PANEL_MIN_HEIGHT = 400

const panelX = ref(0)
const panelY = ref(0)
const panelWidth = ref(PANEL_DEFAULT_WIDTH)
const panelHeight = ref(PANEL_DEFAULT_HEIGHT)

const isDragging = ref(false)
const isResizing = ref(false)

let dragStartMouseX = 0
let dragStartMouseY = 0
let dragStartPanelX = 0
let dragStartPanelY = 0
let resizeStartMouseX = 0
let resizeStartMouseY = 0
let resizeStartWidth = 0
let resizeStartHeight = 0

function getMaxWidth() {
  return Math.floor(window.innerWidth * 0.9)
}

function getMaxHeight() {
  return Math.floor(window.innerHeight * 0.9)
}

function clampPanelX(x: number) {
  return Math.max(0, Math.min(x, window.innerWidth - panelWidth.value))
}

function clampPanelY(y: number) {
  return Math.max(0, Math.min(y, window.innerHeight - panelHeight.value))
}

function startDrag(e: MouseEvent) {
  if ((e.target as HTMLElement).closest('.ai-panel__close')) return
  isDragging.value = true
  dragStartMouseX = e.clientX
  dragStartMouseY = e.clientY
  dragStartPanelX = panelX.value
  dragStartPanelY = panelY.value
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  e.preventDefault()
}

function onDrag(e: MouseEvent) {
  if (!isDragging.value) return
  const dx = e.clientX - dragStartMouseX
  const dy = e.clientY - dragStartMouseY
  panelX.value = clampPanelX(dragStartPanelX + dx)
  panelY.value = clampPanelY(dragStartPanelY + dy)
}

function stopDrag() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

function startResize(e: MouseEvent) {
  isResizing.value = true
  resizeStartMouseX = e.clientX
  resizeStartMouseY = e.clientY
  resizeStartWidth = panelWidth.value
  resizeStartHeight = panelHeight.value
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  e.preventDefault()
  e.stopPropagation()
}

function onResize(e: MouseEvent) {
  if (!isResizing.value) return
  const dw = e.clientX - resizeStartMouseX
  const dh = e.clientY - resizeStartMouseY
  panelWidth.value = Math.max(PANEL_MIN_WIDTH, Math.min(resizeStartWidth + dw, getMaxWidth()))
  panelHeight.value = Math.max(PANEL_MIN_HEIGHT, Math.min(resizeStartHeight + dh, getMaxHeight()))
  panelX.value = clampPanelX(panelX.value)
  panelY.value = clampPanelY(panelY.value)
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

function handleWindowResize() {
  panelWidth.value = Math.max(PANEL_MIN_WIDTH, Math.min(panelWidth.value, getMaxWidth()))
  panelHeight.value = Math.max(PANEL_MIN_HEIGHT, Math.min(panelHeight.value, getMaxHeight()))
  panelX.value = clampPanelX(panelX.value)
  panelY.value = clampPanelY(panelY.value)
}

onMounted(() => {
  window.addEventListener('resize', handleWindowResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
})

function toggleAI() {
  aiOpen.value = !aiOpen.value
  if (aiOpen.value) {
    panelWidth.value = Math.max(PANEL_MIN_WIDTH, Math.min(PANEL_DEFAULT_WIDTH, getMaxWidth()))
    panelHeight.value = Math.max(PANEL_MIN_HEIGHT, Math.min(PANEL_DEFAULT_HEIGHT, getMaxHeight()))
    panelX.value = Math.max(0, window.innerWidth - panelWidth.value - 24)
    panelY.value = Math.max(0, window.innerHeight - panelHeight.value - 24)
    nextTick(() => scrollToBottom())
  }
}

function scrollToBottom() {
  const el = chatBodyRef.value
  if (el) el.scrollTop = el.scrollHeight
}

// ---------- Markdown 简易渲染 ----------
function renderMarkdown(text: string): string {
  if (!text) return ''
  let html = text
  // 转义 HTML
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // 粗体 **text**
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 换行
  html = html.replace(/\n/g, '<br>')
  // 列表项 •
  html = html.replace(/•\s?(.+?)(<br>|$)/g, '<li>$1</li>')
  // 把连续的 <li> 包裹在 <ul> 中
  html = html.replace(/(<li>[\s\S]*?<\/li>)(?!\s*<li>)/g, (match) => {
    return '<ul class="chat-list">' + match + '</ul>'
  })
  html = html.replace(/<\/li><br><li>/g, '</li><li>')
  // 清理多余 <br> 在 <ul> 前后
  html = html.replace(/<br>(<ul)/g, '$1')
  html = html.replace(/(<\/ul>)<br>/g, '$1')
  return html
}

// ---------- 加购物车 ----------
const cartAdding = ref<number | null>(null)

async function addToCart(productId: number) {
  cartAdding.value = productId
  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  try {
    const res = await fetch(`${API_BASE}/api/user/cart`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({ product_id: productId, quantity: 1 }),
    })
    if (res.ok) {
      // 可以加一个 toast 提示
    }
  } catch {
    // ignore
  }
  cartAdding.value = null
}

// ---------- SSE 流式发送消息 ----------
async function sendAIMessage() {
  const text = aiInput.value.trim()
  if (!text || aiSending.value) return
  chatMessages.value.push({ role: 'user', content: text })
  aiInput.value = ''
  aiSending.value = true
  nextTick(() => scrollToBottom())

  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

  // 创建一个空的 assistant 消息，后续逐步填充
  const assistantMsg: ChatMessage = {
    role: 'assistant',
    content: '',
    product: null,
    relatedProducts: [],
  }
  chatMessages.value.push(assistantMsg)
  nextTick(() => scrollToBottom())

  try {
    const response = await fetch(`${API_BASE}/api/user/qa/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({ question: text }),
    })

    if (!response.ok) {
      assistantMsg.content = '抱歉，服务暂时不可用，请稍后再试。'
      aiSending.value = false
      return
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6))

            if (event.type === 'product') {
              assistantMsg.product = event.data
            } else if (event.type === 'related') {
              assistantMsg.relatedProducts = event.data
            } else if (event.type === 'text') {
              assistantMsg.content += event.content
            } else if (event.type === 'done') {
              // 完成
            } else if (event.type === 'error') {
              assistantMsg.content = '回答生成失败：' + (event.message || '未知错误')
            }
            nextTick(() => scrollToBottom())
          } catch {
            // ignore parse errors
          }
        }
      }
    }

    // 如果没有收到任何文本
    if (!assistantMsg.content) {
      assistantMsg.content = '抱歉，我暂时无法回答这个问题，请稍后再试。'
    }
  } catch {
    assistantMsg.content = '网络连接异常，请检查网络后重试。'
  }
  aiSending.value = false
  nextTick(() => scrollToBottom())
}
</script>

<template>
  <div class="user-layout">
    <!-- 顶部导航栏 -->
    <header class="u-header">
      <div class="u-header__inner">
        <div class="u-brand" @click="selectPage('home')">
          <span class="u-brand__icon">AI</span>
          <div class="u-brand__text">
            <h1>电商AI商品文案生成与智能导购助手</h1>
            <span class="u-brand__sub">智能购物 · 懂你所想</span>
          </div>
        </div>

        <!-- 导航菜单 -->
        <nav class="u-menu">
          <button
            v-for="item in menuItems"
            :key="item.key"
            :class="['u-menu__item', { active: activePage === item.key }]"
            @click="selectPage(item.key)"
          >
            {{ item.label }}
          </button>
        </nav>

        <div class="u-header__right">
          <div class="u-user">
            <span class="u-user__avatar">{{ props.userInfo.nickname?.charAt(0) || props.userInfo.username.charAt(0) }}</span>
            <div class="u-user__info">
              <span class="u-user__name">{{ props.userInfo.nickname || props.userInfo.username }}</span>
              <span class="u-user__role">普通用户</span>
            </div>
          </div>
          <button class="u-logout" @click="handleLogout">退出登录</button>
        </div>
      </div>
    </header>

    <!-- 内容区域 -->
    <main class="u-content">
      <!-- 首页 -->
      <div v-if="activePage === 'home'" class="u-home">
        <!-- Hero 横幅 -->
        <section class="u-hero">
          <p class="u-hero__eyebrow">欢迎回来，{{ props.userInfo.nickname || props.userInfo.username }}</p>
          <h2 class="u-hero__title">发现好物，智能导购为您推荐</h2>
          <p class="u-hero__lead">
            浏览真实电商商品数据，AI 智能导购根据您的需求推荐最合适的商品，
            右下角随时召唤智能助手解答疑问。
          </p>
          <div class="u-hero__actions">
            <button class="u-btn u-btn--primary" @click="selectPage('products')">开始购物</button>
            <button class="u-btn u-btn--ghost" @click="toggleAI">咨询AI助手</button>
          </div>
        </section>

        <!-- 功能导航卡片 -->
        <section class="u-cards">
          <article
            v-for="item in menuItems.filter((m) => m.key !== 'home')"
            :key="item.key"
            class="u-card"
            @click="selectPage(item.key)"
          >
            <span class="u-card__icon">{{ item.icon }}</span>
            <h3>{{ item.label }}</h3>
            <p>点击进入{{ item.label }}页面</p>
          </article>
        </section>

        <!-- 平台亮点 -->
        <section class="u-features">
          <h3 class="u-features__title">平台亮点</h3>
          <div class="u-features__grid">
            <div class="u-feature">
              <div class="u-feature__icon">AI</div>
              <h4>智能导购</h4>
              <p>基于 RAG 检索增强，根据您的需求精准推荐商品</p>
            </div>
            <div class="u-feature">
              <div class="u-feature__icon">数</div>
              <h4>真实数据</h4>
              <p>覆盖数码、美妆、母婴等9大品类海量真实电商商品</p>
            </div>
            <div class="u-feature">
              <div class="u-feature__icon">购</div>
              <h4>一站式购物</h4>
              <p>浏览、收藏、加购、下单、支付全流程闭环体验</p>
            </div>
          </div>
        </section>
      </div>

      <!-- 其它页面 -->
      <template v-else>
        <div class="u-content__head">
          <h2>{{ activeMenu.label }}</h2>
        </div>
        <slot :page="activePage">
          <div class="u-placeholder">
            <span class="u-placeholder__icon">{{ activeMenu.icon }}</span>
            <h3>{{ activeMenu.label }}</h3>
            <p>该功能页面正在建设中，敬请期待。</p>
          </div>
        </slot>
      </template>
    </main>

    <!-- 悬浮 AI 智能咨询按钮 -->
    <div class="ai-fab">
      <!-- 聊天窗口 -->
      <transition name="ai-panel">
        <div
          v-if="aiOpen"
          class="ai-panel"
          :style="{
            left: panelX + 'px',
            top: panelY + 'px',
            width: panelWidth + 'px',
            height: panelHeight + 'px',
          }"
        >
          <div class="ai-panel__header" @mousedown="startDrag">
            <div class="ai-panel__title">
              <span class="ai-panel__avatar">AI</span>
              <div>
                <span class="ai-panel__name">智能导购助手</span>
                <span class="ai-panel__status">
                  <i class="ai-panel__dot"></i> 在线
                </span>
              </div>
            </div>
            <button class="ai-panel__close" @click="toggleAI">×</button>
          </div>

          <div ref="chatBodyRef" class="ai-panel__body">
            <div
              v-for="(msg, idx) in chatMessages"
              :key="idx"
              :class="['ai-msg', `ai-msg--${msg.role}`]"
            >
              <span v-if="msg.role === 'assistant'" class="ai-msg__avatar">AI</span>
              <div class="ai-msg__content">
                <!-- 文本气泡 -->
                <div
                  v-if="msg.content"
                  class="ai-msg__bubble"
                  v-html="renderMarkdown(msg.content)"
                ></div>
                <!-- 商品卡片 -->
                <div v-if="msg.product" class="chat-product-card" @click="navigateToProduct(msg.product.id)">
                  <img
                    v-if="msg.product.image_url"
                    :src="msg.product.image_url"
                    :alt="msg.product.name"
                    class="chat-product-card__img"
                  />
                  <div class="chat-product-card__body">
                    <div class="chat-product-card__name">{{ msg.product.name }}</div>
                    <div class="chat-product-card__meta">
                      <span class="chat-product-card__price">¥{{ msg.product.price.toFixed(0) }}</span>
                      <span class="chat-product-card__rating">{{ msg.product.rating }}分</span>
                      <span v-if="msg.product.brand" class="chat-product-card__brand">{{ msg.product.brand }}</span>
                    </div>
                    <button
                      class="chat-product-card__btn"
                      :disabled="cartAdding === msg.product.id"
                      @click.stop="addToCart(msg.product.id)"
                    >
                      {{ cartAdding === msg.product.id ? '添加中...' : '加入购物车' }}
                    </button>
                  </div>
                </div>
                <!-- 相关商品推荐 -->
                <div v-if="msg.relatedProducts && msg.relatedProducts.length" class="chat-related">
                  <div class="chat-related__title">相关推荐</div>
                  <div
                    v-for="rp in msg.relatedProducts"
                    :key="rp.id"
                    class="chat-related__item"
                    @click="navigateToProduct(rp.id)"
                  >
                    <img
                      v-if="rp.image_url"
                      :src="rp.image_url"
                      :alt="rp.name"
                      class="chat-related__img"
                    />
                    <div class="chat-related__info">
                      <div class="chat-related__name">{{ rp.name }}</div>
                      <div class="chat-related__meta">
                        <span class="chat-product-card__price">¥{{ rp.price.toFixed(0) }}</span>
                        <span class="chat-product-card__rating">{{ rp.rating }}分</span>
                      </div>
                    </div>
                    <button
                      class="chat-related__btn"
                      :disabled="cartAdding === rp.id"
                      @click.stop="addToCart(rp.id)"
                    >
                      {{ cartAdding === rp.id ? '...' : '加购' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="aiSending && (!chatMessages.length || !chatMessages[chatMessages.length - 1].content)" class="ai-msg ai-msg--assistant">
              <span class="ai-msg__avatar">AI</span>
              <div class="ai-msg__bubble ai-msg__typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>

          <div class="ai-panel__footer">
            <input
              v-model="aiInput"
              type="text"
              placeholder="输入您的问题..."
              :disabled="aiSending"
              @keyup.enter="sendAIMessage"
            />
            <button class="ai-panel__send" :disabled="aiSending || !aiInput.trim()" @click="sendAIMessage">
              发送
            </button>
          </div>

          <!-- 右下角缩放手柄（透明但保持功能） -->
          <div class="ai-panel__resize" @mousedown="startResize"></div>
        </div>
      </transition>

      <!-- 悬浮按钮 -->
      <button v-if="!aiOpen" class="ai-fab__btn" @click="toggleAI">
        <span class="ai-fab__icon">AI</span>
        <span class="ai-fab__label">智能咨询</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.user-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 顶部导航 */
.u-header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: var(--panel);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(18px);
}

.u-header__inner {
  width: min(1440px, 100% - 32px);
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 0;
}

.u-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  flex: 0 0 auto;
}

.u-brand__icon {
  display: inline-grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 12px;
  color: #fffaf0;
  font-weight: 800;
  font-size: 16px;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
}

.u-brand__text h1 {
  margin: 0;
  font-size: 15px;
  line-height: 1.2;
  color: var(--brand-dark);
  letter-spacing: -0.01em;
}

.u-brand__sub {
  font-size: 12px;
  color: var(--muted);
}

/* 导航菜单 */
.u-menu {
  display: flex;
  gap: 4px;
  flex: 1 1 auto;
  justify-content: center;
}

.u-menu__item {
  padding: 8px 14px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.u-menu__item:hover {
  background: rgba(217, 95, 45, 0.08);
  color: var(--brand);
}

.u-menu__item.active {
  background: var(--brand);
  color: white;
  border-color: var(--brand);
}

.u-header__right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 0 0 auto;
}

.u-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.u-user__avatar {
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 50%;
  color: #fffaf0;
  font-weight: 700;
  font-size: 15px;
  background: var(--brand-dark);
}

.u-user__info {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.u-user__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.u-user__role {
  font-size: 12px;
  color: var(--muted);
}

.u-logout {
  padding: 8px 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.u-logout:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: rgba(217, 95, 45, 0.06);
}

/* 内容区 */
.u-content {
  flex: 1;
  width: min(1440px, 100% - 32px);
  margin: 0 auto;
  padding: 24px 0 48px;
}

.u-content__head {
  margin-bottom: 20px;
}

.u-content__head h2 {
  margin: 0;
  font-size: 24px;
  letter-spacing: -0.02em;
  color: var(--ink);
}

/* 首页 */
.u-home {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.u-hero {
  border: 1px solid var(--line);
  border-radius: 24px;
  background: linear-gradient(135deg, var(--brand-dark), var(--brand));
  color: #fffaf0;
  padding: clamp(28px, 4vw, 48px);
  position: relative;
  overflow: hidden;
}

.u-hero::after {
  position: absolute;
  right: -60px;
  bottom: -90px;
  width: 240px;
  height: 240px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  background: repeating-linear-gradient(
    45deg,
    rgba(255, 255, 255, 0.08) 0 9px,
    transparent 9px 18px
  );
  content: '';
}

.u-hero__eyebrow {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: rgba(255, 250, 240, 0.85);
  position: relative;
  z-index: 1;
}

.u-hero__title {
  margin: 0;
  font-size: clamp(26px, 3vw, 36px);
  line-height: 1.15;
  letter-spacing: -0.03em;
  position: relative;
  z-index: 1;
}

.u-hero__lead {
  margin: 16px 0 0;
  max-width: 560px;
  font-size: 15px;
  line-height: 1.75;
  color: rgba(255, 250, 240, 0.88);
  position: relative;
  z-index: 1;
}

.u-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 24px;
  position: relative;
  z-index: 1;
}

.u-btn {
  padding: 11px 22px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s;
  border: 1px solid transparent;
}

.u-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(33, 26, 20, 0.18);
}

.u-btn--primary {
  color: var(--brand-dark);
  background: #fffaf0;
}

.u-btn--ghost {
  color: #fffaf0;
  background: rgba(255, 255, 255, 0.16);
  border-color: rgba(255, 255, 255, 0.3);
}

/* 2x2 网格布局 */
.u-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.u-card {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel);
  padding: 36px 32px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  backdrop-filter: blur(18px);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-height: 160px;
}

.u-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow);
}

.u-card__icon {
  display: inline-grid;
  width: 56px;
  height: 56px;
  place-items: center;
  border-radius: 16px;
  margin-bottom: 20px;
  color: #fffaf0;
  font-weight: 800;
  font-size: 22px;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
}

.u-card h3 {
  margin: 0 0 8px;
  font-size: 22px;
  color: var(--ink);
}

.u-card p {
  margin: 0;
  font-size: 14px;
  color: var(--muted);
}

/* 平台亮点 */
.u-features {
  border: 1px solid var(--line);
  border-radius: 20px;
  background: var(--panel);
  padding: 32px;
}

.u-features__title {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 800;
  color: var(--ink);
  position: relative;
  padding-left: 14px;
}

.u-features__title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 20px;
  border-radius: 2px;
  background: linear-gradient(180deg, var(--brand), var(--brand-dark));
}

.u-features__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.u-feature {
  text-align: center;
  padding: 28px 20px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(217, 95, 45, 0.04), rgba(217, 95, 45, 0.01));
  border: 1px solid rgba(217, 95, 45, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}

.u-feature:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(217, 95, 45, 0.1);
}

.u-feature__icon {
  display: inline-grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 14px;
  margin-bottom: 16px;
  color: #fffaf0;
  font-weight: 800;
  font-size: 18px;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  box-shadow: 0 4px 12px rgba(217, 95, 45, 0.25);
}

.u-feature:nth-child(2) .u-feature__icon {
  background: linear-gradient(135deg, #2d8a4e, #1a5e35);
  box-shadow: 0 4px 12px rgba(45, 138, 78, 0.25);
}

.u-feature:nth-child(3) .u-feature__icon {
  background: linear-gradient(135deg, #1677ff, #0050b3);
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.25);
}

.u-feature h4 {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}

.u-feature p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--muted);
}

@media (max-width: 768px) {
  .u-features__grid {
    grid-template-columns: 1fr;
  }
}

/* 占位 */
.u-placeholder {
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

.u-placeholder__icon {
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

.u-placeholder h3 {
  margin: 0 0 8px;
  font-size: 20px;
  color: var(--ink);
}

.u-placeholder p {
  margin: 0;
  font-size: 14px;
}

/* ---------- 悬浮 AI 咨询 ---------- */
.ai-fab {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 100;
}

.ai-fab__btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px 12px 12px;
  border: none;
  border-radius: 999px;
  color: #fffaf0;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  cursor: pointer;
  box-shadow: 0 12px 32px rgba(217, 95, 45, 0.4);
  transition: transform 0.2s, box-shadow 0.2s;
}

.ai-fab__btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 16px 40px rgba(217, 95, 45, 0.5);
}

.ai-fab__icon {
  display: inline-grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  font-weight: 800;
  font-size: 13px;
}

.ai-fab__label {
  font-size: 14px;
  font-weight: 600;
}

/* 聊天面板 */
.ai-panel {
  position: fixed;
  min-width: 320px;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  overflow: hidden;
  background: var(--panel);
  border: 1px solid var(--line);
  box-shadow: 0 24px 60px rgba(33, 26, 20, 0.24);
  backdrop-filter: blur(18px);
}

.ai-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: linear-gradient(135deg, var(--brand-dark), var(--brand));
  color: #fffaf0;
  cursor: move;
  user-select: none;
}

.ai-panel__title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-panel__avatar {
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.22);
  font-weight: 800;
  font-size: 13px;
}

.ai-panel__name {
  display: block;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
}

.ai-panel__status {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: rgba(255, 250, 240, 0.85);
}

.ai-panel__dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #6fe0a8;
}

.ai-panel__close {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
  color: #fffaf0;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.2s;
}

.ai-panel__close:hover {
  background: rgba(255, 255, 255, 0.32);
}

.ai-panel__body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: rgba(255, 252, 246, 0.5);
}

.ai-msg {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  max-width: 100%;
}

.ai-msg--user {
  justify-content: flex-end;
}

.ai-msg__avatar {
  flex: 0 0 auto;
  display: inline-grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  background: var(--brand-dark);
  color: #fffaf0;
  font-size: 11px;
  font-weight: 800;
  margin-top: 2px;
}

.ai-msg__content {
  max-width: 82%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-msg__bubble {
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.ai-msg--assistant .ai-msg__bubble {
  background: #fffaf0;
  border: 1px solid var(--line);
  border-bottom-left-radius: 4px;
  color: var(--ink);
}

.ai-msg--user .ai-msg__bubble {
  background: var(--brand);
  color: #fffaf0;
  border-bottom-right-radius: 4px;
}

/* markdown 列表样式 */
.ai-msg__bubble :deep(.chat-list) {
  margin: 6px 0;
  padding-left: 18px;
  list-style: none;
}

.ai-msg__bubble :deep(.chat-list li) {
  position: relative;
  margin-bottom: 4px;
}

.ai-msg__bubble :deep(.chat-list li::before) {
  content: '•';
  position: absolute;
  left: -14px;
  color: var(--brand);
  font-weight: bold;
}

/* 商品卡片 */
.chat-product-card {
  display: flex;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fffaf0;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.chat-product-card:hover {
  border-color: var(--brand);
  box-shadow: 0 4px 12px rgba(217, 95, 45, 0.12);
}

.chat-product-card__img {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
}

.chat-product-card__body {
  flex: 1;
  min-width: 0;
}

.chat-product-card__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.chat-product-card__meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 4px;
}

.chat-product-card__price {
  font-size: 16px;
  font-weight: 800;
  color: var(--brand);
}

.chat-product-card__rating {
  font-size: 12px;
  color: #f5a623;
  font-weight: 600;
}

.chat-product-card__brand {
  font-size: 11px;
  color: var(--muted);
  background: rgba(217, 95, 45, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
}

.chat-product-card__btn {
  margin-top: 6px;
  padding: 4px 12px;
  border: none;
  border-radius: 6px;
  background: var(--brand);
  color: #fffaf0;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.chat-product-card__btn:hover:not(:disabled) {
  background: var(--brand-dark);
}

.chat-product-card__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 相关推荐 */
.chat-related {
  margin-top: 4px;
}

.chat-related__title {
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  margin-bottom: 6px;
}

.chat-related__item {
  display: flex;
  gap: 8px;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  align-items: center;
}

.chat-related__item:hover {
  background: rgba(217, 95, 45, 0.06);
}

.chat-related__img {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.chat-related__info {
  flex: 1;
  min-width: 0;
}

.chat-related__name {
  font-size: 12px;
  color: var(--ink);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-related__meta {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-top: 2px;
}

.chat-related__btn {
  flex-shrink: 0;
  padding: 3px 10px;
  border: none;
  border-radius: 6px;
  background: rgba(217, 95, 45, 0.12);
  color: var(--brand);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.chat-related__btn:hover:not(:disabled) {
  background: rgba(217, 95, 45, 0.2);
}

.chat-related__btn:disabled {
  opacity: 0.5;
}

.ai-msg__typing {
  display: flex;
  gap: 4px;
  align-items: center;
}

.ai-msg__typing span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--muted);
  animation: typing 1.2s infinite ease-in-out;
}

.ai-msg__typing span:nth-child(2) {
  animation-delay: 0.2s;
}

.ai-msg__typing span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-5px);
    opacity: 1;
  }
}

.ai-panel__footer {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--line);
  background: var(--panel);
}

.ai-panel__footer input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 14px;
  font-family: inherit;
  background: rgba(255, 255, 255, 0.7);
  transition: border-color 0.2s;
}

.ai-panel__footer input:focus {
  outline: none;
  border-color: var(--brand);
}

.ai-panel__send {
  padding: 10px 18px;
  border: none;
  border-radius: 999px;
  color: #fffaf0;
  background: var(--brand);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.ai-panel__send:hover:not(:disabled) {
  background: var(--brand-dark);
}

.ai-panel__send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 右下角缩放手柄 - 透明但保持功能 */
.ai-panel__resize {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 20px;
  height: 20px;
  cursor: nwse-resize;
  z-index: 5;
  opacity: 0;
  background: transparent;
}

/* 面板过渡 */
.ai-panel-enter-active,
.ai-panel-leave-active {
  transition: opacity 0.25s, transform 0.25s;
}

.ai-panel-enter-from,
.ai-panel-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.96);
}

@media (max-width: 760px) {
  .u-header__inner {
    flex-wrap: wrap;
    gap: 12px;
  }

  .u-menu {
    order: 4;
    width: 100%;
    overflow-x: auto;
    justify-content: flex-start;
  }

  .u-user__info {
    display: none;
  }

  .u-brand__text h1 {
    font-size: 13px;
  }

  .u-cards {
    grid-template-columns: 1fr;
  }

  .ai-panel {
    width: calc(100vw - 32px);
  }
}
</style>
