<script setup lang="ts">
import { ref, watch, nextTick, onMounted, inject } from 'vue'
import {
  SparklesIcon,
  XMarkIcon,
  PaperAirplaneIcon,
  ChatBubbleLeftEllipsisIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/vue/24/solid'
import FormInput from '../ui/FormInput.vue'

interface ProductCard {
  id: number
  name: string
  price: number
  rating?: number
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

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

const navigateToProduct = inject<(productId: number) => void>('navigateToProduct', () => {})

const open = ref(false)
const input = ref('')
const loading = ref(false)
const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    content: '您好！我是 AI 智能导购助手，可以帮您推荐商品、查询价格、对比评价。请问有什么可以帮您？',
  },
])
const box = ref<HTMLElement | null>(null)

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (box.value) box.value.scrollTop = box.value.scrollHeight
  })
}

function openProductDetail(productId?: number) {
  if (!productId) return
  open.value = false
  navigateToProduct(productId)
}

function isEmptyLoadingMessage(idx: number): boolean {
  const msg = messages.value[idx]
  if (!msg || msg.role !== 'assistant') return false
  if (idx !== messages.value.length - 1) return false
  const hasContent = !!msg.content || !!msg.product || !!(msg.relatedProducts && msg.relatedProducts.length)
  return loading.value && !hasContent
}

watch(messages, scrollToBottom, { deep: true })

onMounted(() => {
  scrollToBottom()
})

function renderMarkdown(text: string): string {
  if (!text) return ''
  let html = text
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\n/g, '<br>')
  html = html.replace(/•\s?(.+?)(<br>|$)/g, '<li>$1</li>')
  html = html.replace(/(<li>[\s\S]*?<\/li>)(?!\s*<li>)/g, (match) => {
    return '<ul class="cw-list">' + match + '</ul>'
  })
  html = html.replace(/<\/li><br><li>/g, '</li><li>')
  html = html.replace(/<br>(<ul)/g, '$1')
  html = html.replace(/(<\/ul>)<br>/g, '$1')
  return html
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  scrollToBottom()

  const assistantMsg: ChatMessage = {
    role: 'assistant',
    content: '',
    product: null,
    relatedProducts: [],
  }
  messages.value.push(assistantMsg)
  scrollToBottom()

  try {
    const response = await fetch(`${API_BASE}/api/user/qa/stream`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ question: text }),
    })

    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
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
            } else if (event.type === 'error') {
              assistantMsg.content = '回答生成失败：' + (event.message || '未知错误')
            }
            scrollToBottom()
          } catch {
            // ignore
          }
        }
      }
    }

    if (!assistantMsg.content) {
      assistantMsg.content = '抱歉，我暂时无法回答这个问题，请稍后再试。'
    }
  } catch {
    assistantMsg.content = '服务暂时不可用，请稍后再试。'
  }
  loading.value = false
  scrollToBottom()
}
</script>

<template>
  <div class="fixed bottom-6 right-6 z-50 flex flex-col items-end">
    <div
      v-if="open"
      class="bg-white w-80 sm:w-96 h-[520px] rounded-2xl shadow-2xl flex flex-col border border-primary-light/50 mb-4 overflow-hidden modal-in"
    >
      <div class="bg-gradient-to-r from-primary to-accent-blue text-white px-5 py-4 flex justify-between items-center shrink-0">
        <div class="flex items-center space-x-2">
          <SparklesIcon class="w-5 h-5" />
          <span class="font-medium">AI智能导购</span>
        </div>
        <button
          @click="open = false"
          class="text-white/80 hover:text-white hover:bg-white/20 rounded-lg p-1 transition-colors"
        >
          <XMarkIcon class="w-5 h-5" />
        </button>
      </div>
      <div ref="box" class="flex-1 overflow-y-auto p-4 space-y-4 bg-page">
        <template v-for="(msg, idx) in messages" :key="idx">
          <div
            v-if="!isEmptyLoadingMessage(idx)"
            :class="msg.role === 'user' ? 'text-right' : 'text-left'"
            class="fade-in-up"
            :style="{ animationDelay: idx * 50 + 'ms' }"
          >
            <div
              class="flex items-end space-x-2"
              :class="msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''"
            >
              <div
                class="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold"
                :class="msg.role === 'user'
                  ? 'bg-gradient-to-br from-primary to-accent-blue text-white'
                  : 'bg-gradient-to-br from-primary to-primary-dark text-white'"
              >
                {{ msg.role === 'user' ? '我' : 'AI' }}
              </div>
              <div class="max-w-[78%]">
                <div
                  v-if="msg.content"
                  :class="msg.role === 'user'
                    ? 'bg-gradient-to-r from-primary to-primary-dark text-white rounded-br-sm'
                    : 'bg-white text-gray-800 border border-primary-light/50 shadow-sm rounded-bl-sm'"
                  class="inline-block px-4 py-2.5 rounded-2xl text-sm whitespace-pre-wrap leading-relaxed text-left"
                  v-html="renderMarkdown(msg.content)"
                ></div>
                <!-- 商品卡片 -->
                <div
                  v-if="msg.product"
                  class="mt-2 bg-white rounded-xl border border-primary-light/50 p-3 shadow-sm text-left cursor-pointer hover:border-primary transition-colors"
                  @click="openProductDetail(msg.product?.id)"
                >
                  <div class="flex space-x-3">
                    <img
                      v-if="msg.product.image_url"
                      :src="msg.product.image_url"
                      class="w-16 h-16 rounded-lg object-cover flex-shrink-0"
                    />
                    <div class="flex-1 min-w-0">
                      <div class="text-sm font-semibold text-gray-800 truncate">{{ msg.product.name }}</div>
                      <div class="text-xs text-gray-500 mt-1">
                        <span class="text-primary font-bold">¥{{ msg.product.price?.toFixed(2) || '--' }}</span>
                        <span v-if="msg.product.rating" class="ml-2">{{ msg.product.rating }}分</span>
                      </div>
                    </div>
                  </div>
                </div>
                <!-- 相关推荐 -->
                <div v-if="msg.relatedProducts && msg.relatedProducts.length" class="mt-2 space-y-2">
                  <div class="text-xs text-gray-400 text-left">相关推荐</div>
                  <div
                    v-for="rp in msg.relatedProducts"
                    :key="rp.id"
                    class="bg-white rounded-xl border border-primary-light/50 p-2 shadow-sm text-left flex space-x-2 cursor-pointer hover:border-primary transition-colors"
                    @click="openProductDetail(rp.id)"
                  >
                    <img
                      v-if="rp.image_url"
                      :src="rp.image_url"
                      class="w-10 h-10 rounded-lg object-cover flex-shrink-0"
                    />
                    <div class="flex-1 min-w-0">
                      <div class="text-xs font-medium text-gray-800 truncate">{{ rp.name }}</div>
                      <div class="text-xs text-primary font-semibold">¥{{ rp.price?.toFixed(2) || '--' }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
        <div v-if="loading" class="text-left fade-in-up">
          <div class="flex items-center space-x-2">
            <div class="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center text-xs font-bold text-white">AI</div>
            <div class="bg-white text-gray-500 border border-primary-light/50 shadow-sm inline-flex items-center space-x-1 px-4 py-2.5 rounded-2xl text-sm">
              <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"></span>
              <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
              <span class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
            </div>
          </div>
        </div>
      </div>
      <div class="p-4 border-t border-primary-light/50 bg-white shrink-0">
        <div class="flex space-x-2">
          <FormInput
            v-model="input"
            @keydown.enter="send"
            type="text"
            placeholder="咨询尺码、材质、售后等"
            :icon="ChatBubbleLeftRightIcon"
            class="flex-1"
            input-class="rounded-xl py-2.5"
          />
          <button
            @click="send"
            :disabled="loading || !input.trim()"
            class="bg-gradient-to-r from-primary to-primary-dark text-white px-4 py-2.5 rounded-xl hover:shadow-lg hover:shadow-primary/30 disabled:opacity-60 transition-all"
          >
            <PaperAirplaneIcon class="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
    <button
      @click="open = !open"
      class="relative w-14 h-14 rounded-full bg-gradient-to-r from-primary via-primary-light to-accent-blue text-white shadow-lg shadow-primary/40 hover:shadow-xl hover:shadow-primary/50 hover:scale-105 transition-all duration-300 flex items-center justify-center pulse-ring"
    >
      <ChatBubbleLeftEllipsisIcon v-if="!open" class="w-7 h-7" />
      <XMarkIcon v-else class="w-7 h-7" />
    </button>
  </div>
</template>

<style scoped>
:deep(.cw-list) {
  margin: 6px 0;
  padding-left: 16px;
  list-style: none;
}
:deep(.cw-list li) {
  position: relative;
  margin-bottom: 4px;
}
:deep(.cw-list li::before) {
  content: '•';
  position: absolute;
  left: -14px;
  color: #9B87F5;
  font-weight: bold;
}
</style>
