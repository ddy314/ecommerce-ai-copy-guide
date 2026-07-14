<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  ChatBubbleLeftRightIcon,
  CubeIcon,
  PaperAirplaneIcon,
  ChatBubbleBottomCenterTextIcon,
  InboxIcon,
} from '@heroicons/vue/24/outline'
import FormInput from '../ui/FormInput.vue'

interface Thread {
  user_id: number
  user_nickname: string
  user_display_id: string
  user_avatar_url: string
  last_message: string
  last_time: string
  unread_count: number
  product_id: number | null
}

interface CSMessage {
  id: number
  user_id: number
  product_id?: number
  sender_role: 'user' | 'merchant'
  content: string
  is_read: boolean
  created_at: string
  user_nickname?: string
  user_display_id?: string
  user_avatar_url?: string
  product_name?: string
  product_display_id?: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const threads = ref<Thread[]>([])
const messages = ref<CSMessage[]>([])
const activeUserId = ref<number | null>(null)
const input = ref('')
const sending = ref(false)
const box = ref<HTMLElement | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const activeThread = computed(() =>
  threads.value.find((t) => t.user_id === activeUserId.value),
)
const totalUnread = computed(() =>
  threads.value.reduce((s, t) => s + (t.unread_count || 0), 0),
)
const activeProductName = computed(() => {
  const msg = messages.value.find((m) => m.product_name)
  return msg ? msg.product_name : ''
})

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

function normalizeImage(url: string | undefined): string {
  if (!url) return ''
  return url.startsWith('http') ? url : `${API_BASE}${url}`
}

function formatTime(t: string | undefined): string {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

async function loadThreads() {
  try {
    const res = await fetch(`${API_BASE}/api/cs/merchant/threads`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    threads.value = data.threads || []
  } catch (e) {
    console.error('加载客服会话失败', e)
  }
}

async function loadMessages(userId: number) {
  try {
    const res = await fetch(`${API_BASE}/api/cs/merchant/threads/${userId}`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    messages.value = data.messages || []
  } catch (e) {
    console.error('加载消息失败', e)
  }
}

function selectThread(t: Thread) {
  activeUserId.value = t.user_id
  loadMessages(t.user_id)
}

async function sendReply() {
  const text = input.value.trim()
  if (!text || sending.value || !activeUserId.value) return
  sending.value = true
  input.value = ''
  try {
    const res = await fetch(
      `${API_BASE}/api/cs/merchant/threads/${activeUserId.value}/reply`,
      {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ content: text }),
      },
    )
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    await Promise.all([loadMessages(activeUserId.value), loadThreads()])
  } catch (e) {
    alert(e instanceof Error ? e.message : '回复失败')
  } finally {
    sending.value = false
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (box.value) box.value.scrollTop = box.value.scrollHeight
  })
}

watch(messages, scrollToBottom, { deep: true })

onMounted(() => {
  loadThreads()
  pollTimer = setInterval(async () => {
    await loadThreads()
    if (activeUserId.value) await loadMessages(activeUserId.value)
  }, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="h-[calc(100vh-7rem)] flex gap-4 fade-in-up">
    <!-- 会话列表 -->
    <div class="w-80 card flex flex-col overflow-hidden shrink-0 bg-white rounded-2xl border border-primary-light/50 shadow-card">
      <div class="px-5 py-4 border-b border-primary-light/50 flex items-center justify-between">
        <h2 class="font-bold text-gray-800 flex items-center space-x-2">
          <ChatBubbleLeftRightIcon class="w-5 h-5 text-primary" />
          <span>客服会话</span>
        </h2>
        <span v-if="totalUnread" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
          {{ totalUnread }} 条未读
        </span>
      </div>
      <div class="flex-1 overflow-y-auto p-3 space-y-2 bg-page">
        <div v-if="threads.length === 0" class="text-center text-gray-400 py-10">
          <InboxIcon class="w-10 h-10 mx-auto mb-2 text-primary/30" />
          <p class="text-sm">暂无用户咨询</p>
        </div>
        <button
          v-for="t in threads"
          :key="t.user_id"
          @click="selectThread(t)"
          class="w-full text-left p-3 rounded-2xl transition-all border"
          :class="activeUserId === t.user_id
            ? 'bg-primary-light border-primary/30 shadow-sm'
            : 'bg-white border-transparent hover:bg-white hover:border-primary-light hover:shadow-sm'"
        >
          <div class="flex items-center space-x-3">
            <img
              v-if="t.user_avatar_url"
              :src="normalizeImage(t.user_avatar_url)"
              class="w-10 h-10 rounded-full object-cover border border-primary-light"
            />
            <div
              v-else
              class="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-accent-blue flex items-center justify-center text-white text-sm font-bold"
            >
              {{ (t.user_nickname || 'U').charAt(0).toUpperCase() }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between">
                <span class="font-medium text-gray-800 truncate">{{ t.user_nickname }}</span>
                <span
                  v-if="t.unread_count"
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 ml-2"
                >
                  {{ t.unread_count }}
                </span>
              </div>
              <p class="text-xs text-gray-500 truncate mt-0.5">{{ t.last_message }}</p>
              <p class="text-[10px] text-gray-400 mt-0.5">{{ formatTime(t.last_time) }}</p>
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- 聊天详情 -->
    <div class="flex-1 card flex flex-col overflow-hidden min-w-0 bg-white rounded-2xl border border-primary-light/50 shadow-card">
      <div v-if="!activeUserId" class="flex-1 flex flex-col items-center justify-center text-gray-400 bg-page">
        <ChatBubbleLeftRightIcon class="w-16 h-16 mb-4 text-primary/30" />
        <p>请从左侧选择一个会话进行回复</p>
      </div>
      <template v-else>
        <div class="px-6 py-4 border-b border-primary-light/50 flex items-center justify-between bg-white shrink-0">
          <div class="flex items-center space-x-3">
            <img
              v-if="activeThread?.user_avatar_url"
              :src="normalizeImage(activeThread.user_avatar_url)"
              class="w-10 h-10 rounded-full object-cover border border-primary-light"
            />
            <div
              v-else
              class="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-accent-blue flex items-center justify-center text-white text-sm font-bold"
            >
              {{ (activeThread?.user_nickname || 'U').charAt(0).toUpperCase() }}
            </div>
            <div>
              <h3 class="font-bold text-gray-800">{{ activeThread?.user_nickname }}</h3>
              <p class="text-xs text-gray-500">{{ activeThread?.user_display_id }}</p>
            </div>
          </div>
          <div v-if="activeProductName" class="hidden md:flex items-center space-x-2 bg-primary-light/50 rounded-xl px-3 py-1.5">
            <CubeIcon class="w-4 h-4 text-primary" />
            <span class="text-sm text-primary-dark truncate max-w-[200px]">{{ activeProductName }}</span>
          </div>
        </div>

        <div ref="box" class="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-page">
          <div
            v-for="(msg, idx) in messages"
            :key="msg.id || idx"
            :class="msg.sender_role === 'merchant' ? 'text-right' : 'text-left'"
            class="fade-in-up"
          >
            <div
              class="flex items-end space-x-2"
              :class="msg.sender_role === 'merchant' ? 'flex-row-reverse space-x-reverse' : ''"
            >
              <div
                class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                :class="msg.sender_role === 'merchant'
                  ? 'bg-gradient-to-br from-primary to-primary-dark'
                  : 'bg-gradient-to-br from-accent-blue to-primary'"
              >
                {{ msg.sender_role === 'merchant' ? '商' : '用' }}
              </div>
              <div
                class="inline-block px-4 py-2.5 rounded-2xl text-sm max-w-[70%] whitespace-pre-wrap leading-relaxed shadow-sm"
                :class="msg.sender_role === 'merchant'
                  ? 'bg-gradient-to-r from-primary to-primary-dark text-white rounded-br-sm'
                  : 'bg-white text-gray-800 border border-primary-light/50 rounded-bl-sm'"
              >
                {{ msg.content }}
              </div>
            </div>
            <p
              class="text-xs text-gray-400 mt-1"
              :class="msg.sender_role === 'merchant' ? 'pr-11' : 'pl-11'"
            >
              {{ formatTime(msg.created_at) }}
            </p>
          </div>
        </div>

        <div class="p-4 bg-white border-t border-primary-light/50 shrink-0">
          <div class="flex items-center space-x-3">
            <FormInput
              v-model="input"
              @keydown.enter="sendReply"
              type="text"
              placeholder="请输入回复内容"
              :icon="ChatBubbleBottomCenterTextIcon"
              class="flex-1"
              input-class="rounded-xl py-3"
            />
            <button
              @click="sendReply"
              :disabled="!input.trim() || sending"
              class="bg-gradient-to-r from-primary to-primary-dark text-white px-5 py-3 rounded-xl hover:shadow-lg hover:shadow-primary/30 disabled:opacity-60 transition-all flex items-center space-x-1"
            >
              <PaperAirplaneIcon class="w-5 h-5" />
              <span>回复</span>
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
