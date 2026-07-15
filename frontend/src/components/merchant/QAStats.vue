<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  ChatBubbleLeftRightIcon,
  SparklesIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
} from '@heroicons/vue/24/outline'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function authHeaders(extra: Record<string, string> = {}): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

interface KeywordItem {
  keyword: string
  count: number
}

interface RawKeyword {
  keyword?: string
  word?: string
  count?: number
  frequency?: number
  [key: string]: unknown
}

interface QAStats {
  total_questions?: number
  total?: number
  source_distribution?: Record<string, number>
  type_distribution?: Record<string, number>
  top_keywords?: Array<RawKeyword | string>
}

interface QARecord {
  id?: number
  time?: string
  created_at?: string
  question: string
  answer?: string
  source?: string
  question_type?: string
  type?: string
}

const loading = ref(false)
const error = ref<string | null>(null)
const stats = ref<QAStats | null>(null)
const records = ref<QARecord[]>([])
const keywordQuery = ref('')
const recordQuery = ref('')

const sourceLabels: Record<string, string> = {
  rag: 'RAG检索',
  data_rag: '数据驱动',
  template: '模板回复',
  knowledge: '知识库',
  fallback: '兜底回复',
}

const typeLabels: Record<string, string> = {
  size: '尺寸规格',
  function: '功能使用',
  matching: '搭配推荐',
  match: '搭配推荐',
  recommend: '商品推荐',
  price: '价格性价比',
  brand: '品牌咨询',
  review: '评价口碑',
  compare: '对比分析',
  after_sale: '售后服务',
  after_sale_service: '售后服务',
  general: '综合咨询',
}

const sourceColors: Record<string, string> = {
  rag: 'bg-emerald-500',
  data_rag: 'bg-emerald-500',
  template: 'bg-blue-500',
  knowledge: 'bg-amber-500',
  fallback: 'bg-slate-400',
}

const typeColors: Record<string, string> = {
  recommend: 'bg-purple-500',
  price: 'bg-rose-500',
  brand: 'bg-blue-500',
  review: 'bg-amber-500',
  size: 'bg-cyan-500',
  matching: 'bg-pink-500',
  after_sale: 'bg-slate-500',
  general: 'bg-emerald-500',
  function: 'bg-indigo-500',
  compare: 'bg-orange-500',
}

function sourceLabel(src?: string): string {
  if (!src) return '未知'
  return sourceLabels[src] || src
}

function typeLabel(t?: string): string {
  if (!t) return '其他'
  return typeLabels[t] || t
}

const totalQuestions = computed(() => {
  if (!stats.value) return 0
  return stats.value.total_questions ?? stats.value.total ?? 0
})

const sourceDistribution = computed<{ key: string; label: string; value: number; color: string }[]>(() => {
  if (!stats.value) return []
  const dist = stats.value.source_distribution || {}
  return Object.entries(dist)
    .filter(([, value]) => Number(value) > 0)
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .map(([key, value]) => ({
      key,
      label: sourceLabel(key),
      value: Number(value) || 0,
      color: sourceColors[key] || 'bg-primary',
    }))
})

const typeDistribution = computed<{ key: string; label: string; value: number; color: string }[]>(() => {
  if (!stats.value) return []
  const dist = stats.value.type_distribution || {}
  return Object.entries(dist)
    .filter(([, value]) => Number(value) > 0)
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .map(([key, value]) => ({
      key,
      label: typeLabel(key),
      value: Number(value) || 0,
      color: typeColors[key] || 'bg-primary',
    }))
})

const keywordItems = computed<KeywordItem[]>(() => {
  if (!stats.value || !stats.value.top_keywords) return []
  return stats.value.top_keywords
    .map((k) => {
      if (typeof k === 'string') return { keyword: k, count: 1 }
      return { keyword: k.keyword || k.word || '', count: Number(k.count || k.frequency || 1) }
    })
    .filter((k) => k.keyword)
    .sort((a, b) => b.count - a.count)
})

const filteredKeywords = computed(() => {
  if (!keywordQuery.value.trim()) return keywordItems.value
  const q = keywordQuery.value.toLowerCase()
  return keywordItems.value.filter((k) => k.keyword.toLowerCase().includes(q))
})

const filteredRecords = computed(() => {
  if (!recordQuery.value.trim()) return records.value
  const q = recordQuery.value.toLowerCase()
  return records.value.filter(
    (r) =>
      r.question.toLowerCase().includes(q) ||
      (r.answer && r.answer.toLowerCase().includes(q)) ||
      sourceLabel(r.source).toLowerCase().includes(q) ||
      typeLabel(r.question_type || r.type).toLowerCase().includes(q),
  )
})

const maxCount = computed(() => keywordItems.value.reduce((max, k) => Math.max(max, k.count), 1))
const minCount = computed(() => keywordItems.value.reduce((min, k) => Math.min(min, k.count), 1))

function keywordFontSize(count: number): string {
  if (keywordItems.value.length === 0) return '14px'
  const range = maxCount.value - minCount.value
  if (range === 0) return '18px'
  const ratio = (count - minCount.value) / range
  const size = 14 + ratio * 22
  return `${size.toFixed(0)}px`
}

function keywordOpacity(count: number): number {
  if (keywordItems.value.length === 0) return 1
  const range = maxCount.value - minCount.value
  if (range === 0) return 1
  const ratio = (count - minCount.value) / range
  return 0.5 + ratio * 0.5
}

function sourceTotal(): number {
  return sourceDistribution.value.reduce((sum, s) => sum + s.value, 0)
}

function typeTotal(): number {
  return typeDistribution.value.reduce((sum, t) => sum + t.value, 0)
}

function percent(value: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

function formatTime(t?: string): string {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 16)
}

async function loadStats() {
  loading.value = true
  error.value = null
  try {
    const [statsRes, recordsRes] = await Promise.all([
      fetch(`${API_BASE}/api/merchant/qa/stats`, { headers: authHeaders() }),
      fetch(`${API_BASE}/api/merchant/qa/records?limit=50`, { headers: authHeaders() }),
    ])

    if (!statsRes.ok) {
      const err = await statsRes.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${statsRes.status}`)
    }
    stats.value = await statsRes.json()

    if (recordsRes.ok) {
      const data = await recordsRes.json()
      records.value = data.records || data.items || data.list || data || []
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载统计数据失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>

<template>
  <div class="min-h-[calc(100vh-7rem)] space-y-6 animate-fade-in-up">
    <!-- 页面头部 -->
    <div class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary via-primary to-accent-blue p-6 sm:p-8 shadow-xl shadow-primary/20">
      <div class="absolute top-0 right-0 w-64 h-64 rounded-full bg-white/10 blur-3xl -translate-y-1/2 translate-x-1/4 pointer-events-none"></div>
      <div class="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-accent-blue/20 blur-3xl translate-y-1/3 -translate-x-1/4 pointer-events-none"></div>
      <div class="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl sm:text-3xl font-extrabold text-white flex items-center gap-3">
            <ChatBubbleLeftRightIcon class="w-8 h-8" />
            用户问答统计
          </h1>
          <p class="text-white/70 text-sm mt-2">洞察用户咨询趋势，优化客服与 RAG 回答质量</p>
        </div>
        <button
          @click="loadStats"
          :disabled="loading"
          class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-white/20 backdrop-blur-sm text-white text-sm font-semibold hover:bg-white/30 transition-all disabled:opacity-60"
        >
          <ArrowPathIcon :class="['w-4 h-4', loading && 'animate-spin']" />
          刷新数据
        </button>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="bg-rose-50 border border-rose-100 text-rose-600 px-5 py-3 rounded-2xl text-sm font-medium flex items-center gap-2">
      <svg class="w-5 h-5 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      {{ error }}
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-24 text-gray-400">
      <div class="w-14 h-14 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-4"></div>
      <p class="text-sm">正在加载问答数据...</p>
    </div>

    <template v-else>
      <!-- 核心指标卡 -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
        <!-- 总问题数 -->
        <div class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary to-primary-dark p-6 text-white shadow-lg shadow-primary/20">
          <div class="absolute -top-6 -right-6 w-32 h-32 rounded-full bg-white/10 blur-2xl pointer-events-none"></div>
          <div class="relative z-10 flex items-center gap-4">
            <div class="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <ChatBubbleLeftRightIcon class="w-7 h-7" />
            </div>
            <div>
              <div class="text-4xl font-extrabold">{{ totalQuestions }}</div>
              <div class="text-sm text-white/80 mt-0.5">总问题数</div>
            </div>
          </div>
        </div>

        <!-- 来源分布 -->
        <div class="bg-white rounded-3xl border border-primary-light/40 shadow-sm p-5 md:col-span-2">
          <div class="flex items-center gap-2 mb-4">
            <SparklesIcon class="w-5 h-5 text-primary" />
            <h3 class="font-bold text-gray-800">按来源分布</h3>
          </div>
          <div v-if="sourceDistribution.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            <div
              v-for="item in sourceDistribution"
              :key="item.key"
              class="relative overflow-hidden rounded-2xl bg-gray-50 p-4 border border-gray-100 hover:shadow-md transition-shadow"
            >
              <div class="absolute top-0 left-0 w-1 h-full" :class="item.color"></div>
              <div class="text-xs text-gray-500 mb-1">{{ item.label }}</div>
              <div class="text-2xl font-extrabold text-gray-800">{{ item.value }}</div>
              <div class="text-xs text-gray-400 mt-1">{{ percent(item.value, sourceTotal()) }}</div>
            </div>
          </div>
          <div v-else class="text-center text-gray-400 py-8 text-sm">暂无来源数据</div>
        </div>
      </div>

      <!-- 类型分布 + 关键词云 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <!-- 类型分布 -->
        <div class="bg-white rounded-3xl border border-primary-light/40 shadow-sm p-5">
          <div class="flex items-center gap-2 mb-4">
            <DocumentTextIcon class="w-5 h-5 text-primary" />
            <h3 class="font-bold text-gray-800">按类型分布</h3>
          </div>
          <div v-if="typeDistribution.length" class="space-y-3">
            <div v-for="item in typeDistribution" :key="item.key" class="group">
              <div class="flex items-center justify-between text-sm mb-1.5">
                <span class="font-medium text-gray-700 flex items-center gap-2">
                  <span class="w-2.5 h-2.5 rounded-full" :class="item.color"></span>
                  {{ item.label }}
                </span>
                <span class="text-gray-500 text-xs font-semibold">{{ item.value }} · {{ percent(item.value, typeTotal()) }}</span>
              </div>
              <div class="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-700 ease-out"
                  :class="item.color"
                  :style="{ width: percent(item.value, typeTotal()) }"
                ></div>
              </div>
            </div>
          </div>
          <div v-else class="text-center text-gray-400 py-8 text-sm">暂无类型数据</div>
        </div>

        <!-- 高频关键词云 -->
        <div class="bg-white rounded-3xl border border-primary-light/40 shadow-sm p-5">
          <div class="flex items-center justify-between gap-3 mb-4">
            <div class="flex items-center gap-2">
              <MagnifyingGlassIcon class="w-5 h-5 text-primary" />
              <h3 class="font-bold text-gray-800">高频问题关键词</h3>
            </div>
            <div class="relative">
              <MagnifyingGlassIcon class="w-4 h-4 text-gray-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                v-model="keywordQuery"
                type="text"
                placeholder="搜索关键词..."
                class="pl-8 pr-3 py-1.5 text-xs rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none w-36"
              />
            </div>
          </div>
          <div v-if="filteredKeywords.length" class="flex flex-wrap gap-2.5 min-h-[120px] content-start">
            <span
              v-for="kw in filteredKeywords"
              :key="kw.keyword"
              class="inline-flex items-center px-3 py-1.5 rounded-full font-semibold transition-all hover:-translate-y-0.5 hover:shadow-sm cursor-default"
              :style="{
                fontSize: keywordFontSize(kw.count),
                opacity: keywordOpacity(kw.count),
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                color: '#7c3aed',
              }"
            >
              {{ kw.keyword }}
              <span class="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full bg-white/60 text-primary/80">{{ kw.count }}</span>
            </span>
          </div>
          <div v-else class="text-center text-gray-400 py-8 text-sm">{{ keywordQuery ? '无匹配关键词' : '暂无关键词数据' }}</div>
        </div>
      </div>

      <!-- 问答记录 -->
      <div class="bg-white rounded-3xl border border-primary-light/40 shadow-sm p-5">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
          <div class="flex items-center gap-2">
            <ChatBubbleLeftRightIcon class="w-5 h-5 text-primary" />
            <h3 class="font-bold text-gray-800">问答记录</h3>
            <span class="text-xs text-gray-400 font-normal">最近 {{ records.length }} 条</span>
          </div>
          <div class="relative w-full sm:w-64">
            <MagnifyingGlassIcon class="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              v-model="recordQuery"
              type="text"
              placeholder="搜索问题、回答、来源或类型..."
              class="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/10 outline-none"
            />
          </div>
        </div>

        <div v-if="filteredRecords.length" class="space-y-3 max-h-[640px] overflow-y-auto pr-1">
          <div
            v-for="(record, idx) in filteredRecords"
            :key="record.id ?? idx"
            class="group rounded-2xl border border-gray-100 bg-gray-50/50 hover:bg-white hover:shadow-md hover:border-primary-light/50 transition-all p-4"
          >
            <div class="flex flex-wrap items-center gap-2 mb-2.5">
              <span class="text-xs text-gray-400 font-medium">{{ formatTime(record.time || record.created_at) }}</span>
              <span
                class="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                :class="[
                  (record.source || '').includes('rag') || (record.source || '').includes('data')
                    ? 'bg-emerald-50 text-emerald-600'
                    : 'bg-amber-50 text-amber-600',
                ]"
              >
                {{ sourceLabel(record.source) }}
              </span>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-primary/10 text-primary">
                {{ typeLabel(record.question_type || record.type) }}
              </span>
            </div>
            <div class="text-sm text-gray-800 font-medium leading-relaxed mb-1.5">
              <span class="text-primary font-bold">问：</span>{{ record.question }}
            </div>
            <div v-if="record.answer" class="text-sm text-gray-500 leading-relaxed line-clamp-3">
              <span class="text-emerald-600 font-bold">答：</span>{{ record.answer }}
            </div>
          </div>
        </div>
        <div v-else class="text-center text-gray-400 py-10 text-sm">
          {{ recordQuery ? '无匹配记录' : '暂无问答记录' }}
        </div>
      </div>
    </template>
  </div>
</template>
