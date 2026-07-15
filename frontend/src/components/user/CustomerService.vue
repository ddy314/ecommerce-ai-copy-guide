<script setup lang="ts">
import { ref, inject, onMounted, onUnmounted, watch, nextTick, type Ref } from 'vue'
import {
  ChatBubbleLeftRightIcon,
  CubeIcon,
  PaperAirplaneIcon,
  ChatBubbleBottomCenterTextIcon,
  SparklesIcon,
} from '@heroicons/vue/24/outline'
import FormInput from '../ui/FormInput.vue'
import { resolveAvatarUrl } from '../../utils/avatar'

interface CSMessage {
  id: number
  user_id: number
  product_id?: number
  sender_id?: number
  sender_role: 'user' | 'merchant' | 'ai'
  content: string
  is_read: boolean
  created_at: string
  user_nickname?: string
  user_display_id?: string
  user_avatar_url?: string
  merchant_nickname?: string
  merchant_avatar_url?: string
  product_name?: string
  product_display_id?: string
}

interface UserInfo {
  id?: number
  nickname?: string
  username?: string
  avatar?: string | null
}

interface MerchantInfo {
  id?: number
  nickname?: string
  username?: string
  avatar?: string | null
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const csProductId = inject<Ref<number | null>>('csProductId', ref(null))

const messages = ref<CSMessage[]>([])
const input = ref('')
const sending = ref(false)
const box = ref<HTMLElement | null>(null)
const product = ref<{ id: number; name: string } | null>(null)
const userInfo = ref<UserInfo | null>(null)
const merchantInfo = ref<MerchantInfo | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

function formatTime(t: string | undefined): string {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

function renderMarkdown(text: string): string {
  if (!text) return ''
  let html = text
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\n/g, '<br>')
  html = html.replace(/•\s?(.+?)(<br>|$)/g, '<li>$1</li>')
  html = html.replace(/(<li>[\s\S]*?<\/li>)(?!\s*<li>)/g, (match) => {
    return '<ul class="cs-list">' + match + '</ul>'
  })
  html = html.replace(/<\/li><br><li>/g, '</li><li>')
  html = html.replace(/<br>(<ul)/g, '$1')
  html = html.replace(/(<\/ul>)<br>/g, '$1')
  return html
}

function senderLabel(role: string): string {
  if (role === 'merchant') return '商'
  if (role === 'ai') return 'AI'
  return '我'
}

function messageAvatar(msg: CSMessage): string {
  if (msg.sender_role === 'user') return resolveAvatarUrl(userInfo.value?.avatar)
  if (msg.sender_role === 'merchant') return resolveAvatarUrl(msg.merchant_avatar_url || merchantInfo.value?.avatar)
  return ''
}

async function loadUserInfo() {
  try {
    const stored = localStorage.getItem('userInfo')
    if (stored) {
      userInfo.value = JSON.parse(stored)
    }
    const res = await fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders() })
    if (res.ok) {
      const data = await res.json()
      const u = data.user || data
      userInfo.value = u
      localStorage.setItem('userInfo', JSON.stringify(u))
    }
  } catch (e) {
    console.error('加载用户信息失败', e)
  }
}

async function loadMerchantInfo() {
  try {
    const res = await fetch(`${API_BASE}/api/cs/merchant/profile`, { headers: authHeaders() })
    if (!res.ok) return
    const data = await res.json()
    merchantInfo.value = data.merchant || null
  } catch (e) {
    console.error('加载商家信息失败', e)
  }
}

async function loadMessages() {
  try {
    const res = await fetch(`${API_BASE}/api/cs/messages/my`, { headers: authHeaders() })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    messages.value = data.messages || []
  } catch (e) {
    console.error('加载客服消息失败', e)
  }
}

async function loadProduct(id: number) {
  try {
    const res = await fetch(`${API_BASE}/api/products/${id}`, { headers: authHeaders() })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    product.value = data.product ? { id: data.product.id, name: data.product.name } : null
  } catch {
    product.value = null
  }
}

async function sendMessage(content: string, productId?: number) {
  if (!content.trim() || sending.value) return
  sending.value = true
  try {
    const payload: Record<string, unknown> = { content: content.trim() }
    if (productId) payload.product_id = productId
    const res = await fetch(`${API_BASE}/api/cs/messages`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    await loadMessages()
  } catch (e) {
    alert(e instanceof Error ? e.message : '发送失败')
  } finally {
    sending.value = false
  }
}

async function send() {
  const text = input.value.trim()
  if (!text) return
  input.value = ''
  await sendMessage(text, product.value?.id)
}

async function sendProductInquiry(productId: number, productName: string) {
  await sendMessage(`我想咨询这个商品：${productName}`, productId)
}

function scrollToBottom() {
  nextTick(() => {
    if (box.value) box.value.scrollTop = box.value.scrollHeight
  })
}

watch(messages, scrollToBottom, { deep: true })

// 监听从商品详情页「询问客服」跳转，自动发送商品咨询
watch(
  csProductId,
  async (newId) => {
    if (newId) {
      await loadProduct(newId)
      if (product.value) {
        await sendProductInquiry(product.value.id, product.value.name)
      }
      csProductId.value = null
    }
  },
  { immediate: true },
)

onMounted(() => {
  loadUserInfo()
  loadMerchantInfo()
  loadMessages()
  pollTimer = setInterval(loadMessages, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="max-w-4xl mx-auto h-[calc(100vh-7rem)] fade-in-up">
    <div class="bg-white rounded-3xl shadow-card h-full flex flex-col overflow-hidden border border-primary-light/50">
      <!-- 头部 -->
      <div class="bg-gradient-to-r from-primary to-accent-blue px-6 py-4 flex items-center justify-between text-white shrink-0">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
            <ChatBubbleLeftRightIcon class="w-6 h-6" />
          </div>
          <div>
            <h2 class="font-bold text-lg">客服咨询</h2>
            <p class="text-xs text-white/80">AI 智能客服在线，商家也可接入回复</p>
          </div>
        </div>
        <div v-if="product" class="hidden sm:flex items-center space-x-2 bg-white/20 backdrop-blur-sm rounded-xl px-3 py-1.5">
          <CubeIcon class="w-4 h-4" />
          <span class="text-sm">咨询商品：{{ product.name }}</span>
        </div>
      </div>

      <!-- 商品信息（移动端） -->
      <div v-if="product" class="sm:hidden px-4 py-2 bg-primary-light/30 border-b border-primary-light/50 text-sm text-primary-dark flex items-center space-x-2">
        <CubeIcon class="w-4 h-4" />
        <span>咨询商品：{{ product.name }}</span>
      </div>

      <!-- 消息区 -->
      <div ref="box" class="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-page">
        <div v-if="messages.length === 0" class="text-center text-gray-400 py-10">
          <ChatBubbleLeftRightIcon class="w-12 h-12 mx-auto mb-3 text-primary/30" />
          <p>还没有消息，向客服提问吧～</p>
          <p class="text-xs mt-1">AI 会根据商品库自动为您推荐和解答</p>
        </div>
        <div
          v-for="(msg, idx) in messages"
          :key="msg.id || idx"
          :class="msg.sender_role === 'user' ? 'text-right' : 'text-left'"
          class="fade-in-up"
        >
          <div
            class="flex items-end space-x-2"
            :class="msg.sender_role === 'user' ? 'flex-row-reverse space-x-reverse' : ''"
          >
            <!-- 头像 -->
            <img
              v-if="messageAvatar(msg)"
              :src="messageAvatar(msg)"
              class="w-9 h-9 rounded-full object-cover border border-primary-light flex-shrink-0"
              alt="avatar"
            />
            <div
              v-else
              class="w-9 h-9 rounded-full flex items-center justify-center text-white flex-shrink-0"
              :class="{
                'bg-gradient-to-br from-primary to-primary-dark': msg.sender_role === 'user',
                'bg-gradient-to-br from-accent-blue to-primary': msg.sender_role === 'merchant',
                'bg-gradient-to-br from-green-400 to-emerald-500': msg.sender_role === 'ai',
              }"
            >
              <SparklesIcon v-if="msg.sender_role === 'ai'" class="w-4 h-4" />
              <span v-else class="text-xs font-bold">{{ senderLabel(msg.sender_role) }}</span>
            </div>

            <div class="max-w-[78%]">
              <div
                v-if="msg.sender_role === 'ai'"
                class="text-xs text-green-600 mb-1 text-left"
              >
                智能客服
              </div>
              <div
                v-if="msg.sender_role === 'ai'"
                class="inline-block px-4 py-2.5 rounded-2xl text-sm max-w-full leading-relaxed shadow-sm bg-green-50 text-gray-800 border border-green-100 rounded-bl-sm text-left"
                v-html="renderMarkdown(msg.content)"
              ></div>
              <div
                v-else
                class="inline-block px-4 py-2.5 rounded-2xl text-sm max-w-full whitespace-pre-wrap leading-relaxed shadow-sm text-left"
                :class="msg.sender_role === 'user'
                  ? 'bg-gradient-to-r from-primary to-primary-dark text-white rounded-br-sm'
                  : 'bg-white text-gray-800 border border-primary-light/50 rounded-bl-sm'"
              >
                {{ msg.content }}
              </div>
            </div>
          </div>
          <p
            class="text-xs text-gray-400 mt-1"
            :class="msg.sender_role === 'user' ? 'pr-11' : 'pl-11'"
          >
            {{ formatTime(msg.created_at) }}
          </p>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="p-4 bg-white border-t border-primary-light/50 shrink-0">
        <div class="flex items-center space-x-3">
          <FormInput
            v-model="input"
            @keydown.enter="send"
            type="text"
            placeholder="请输入您想咨询的问题"
            :icon="ChatBubbleBottomCenterTextIcon"
            class="flex-1"
            input-class="rounded-xl py-3"
          />
          <button
            @click="send"
            :disabled="!input.trim() || sending"
            class="bg-gradient-to-r from-primary to-primary-dark text-white px-5 py-3 rounded-xl hover:shadow-lg hover:shadow-primary/30 disabled:opacity-60 transition-all flex items-center space-x-1"
          >
            <PaperAirplaneIcon class="w-5 h-5" />
            <span class="hidden sm:inline">发送</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.cs-list) {
  margin: 6px 0;
  padding-left: 16px;
  list-style: none;
}
:deep(.cs-list li) {
  position: relative;
  margin-bottom: 4px;
}
:deep(.cs-list li::before) {
  content: '•';
  position: absolute;
  left: -14px;
  color: #9B87F5;
  font-weight: bold;
}
</style>
