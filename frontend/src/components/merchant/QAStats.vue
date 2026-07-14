<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/** 携带鉴权头的请求头 */
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

/** 原始关键词对象，兼容不同后端字段命名 */
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

// 来源与类型显示配置
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

const sourceDistribution = computed<{ key: string; label: string; value: number }[]>(() => {
  if (!stats.value) return []
  const dist = stats.value.source_distribution || {}
  const entries = Object.entries(dist)
  if (entries.length === 0) return []
  return entries.map(([key, value]) => ({
    key,
    label: sourceLabel(key),
    value: Number(value) || 0,
  }))
})

const typeDistribution = computed<{ key: string; label: string; value: number }[]>(() => {
  if (!stats.value) return []
  const dist = stats.value.type_distribution || {}
  const entries = Object.entries(dist)
  if (entries.length === 0) return []
  return entries.map(([key, value]) => ({
    key,
    label: typeLabel(key),
    value: Number(value) || 0,
  }))
})

/** 关键词条目，统一为 { keyword, count } 结构 */
const keywordItems = computed<KeywordItem[]>(() => {
  if (!stats.value || !stats.value.top_keywords) return []
  return stats.value.top_keywords.map((k) => {
    if (typeof k === 'string') return { keyword: k, count: 1 }
    return { keyword: k.keyword || k.word || '', count: Number(k.count || k.frequency || 1) }
  }).filter((k) => k.keyword)
})

/** 最大频次，用于映射字号 */
const maxCount = computed(() => {
  return keywordItems.value.reduce((max, k) => Math.max(max, k.count), 1)
})

const minCount = computed(() => {
  return keywordItems.value.reduce((min, k) => Math.min(min, k.count), 1)
})

/** 根据频次计算字号（14px ~ 32px 之间） */
function keywordFontSize(count: number): string {
  if (keywordItems.value.length === 0) return '14px'
  const range = maxCount.value - minCount.value
  if (range === 0) return '18px'
  const ratio = (count - minCount.value) / range
  const size = 14 + ratio * 18
  return `${size.toFixed(0)}px`
}

/** 根据频次计算颜色深浅 */
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
  // 截取到分钟
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

    if (statsRes.ok) {
      stats.value = await statsRes.json()
    } else {
      const err = await statsRes.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${statsRes.status}`)
    }

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

onMounted(() => {
  loadStats()
})
</script>

<template>
  <div class="qa-page">
    <div v-if="error" class="qa-error">{{ error }}</div>

    <div v-if="loading" class="qa-loading">
      <div class="qa-spinner"></div>
      <p>加载中...</p>
    </div>

    <template v-else>
      <!-- 统计卡片 -->
      <div class="qa-stat-cards">
        <div class="qa-stat-card qa-stat-card--main">
          <div class="qa-stat-card__value">{{ totalQuestions }}</div>
          <div class="qa-stat-card__label">总问题数</div>
        </div>

        <!-- 来源分布卡片 -->
        <div class="qa-stat-card">
          <div class="qa-stat-card__title">按来源分布</div>
          <div v-if="sourceDistribution.length" class="qa-distribution">
            <div v-for="item in sourceDistribution" :key="item.key" class="qa-dist-row">
              <span class="qa-dist-label">{{ item.label }}</span>
              <div class="qa-dist-bar-wrap">
                <div
                  class="qa-dist-bar"
                  :style="{ width: percent(item.value, sourceTotal()) }"
                ></div>
              </div>
              <span class="qa-dist-value">{{ item.value }} ({{ percent(item.value, sourceTotal()) }})</span>
            </div>
          </div>
          <div v-else class="qa-na">暂无数据</div>
        </div>

        <!-- 类型分布卡片 -->
        <div class="qa-stat-card">
          <div class="qa-stat-card__title">按类型分布</div>
          <div v-if="typeDistribution.length" class="qa-distribution">
            <div v-for="item in typeDistribution" :key="item.key" class="qa-dist-row">
              <span class="qa-dist-label">{{ item.label }}</span>
              <div class="qa-dist-bar-wrap">
                <div
                  class="qa-dist-bar qa-dist-bar--type"
                  :style="{ width: percent(item.value, typeTotal()) }"
                ></div>
              </div>
              <span class="qa-dist-value">{{ item.value }} ({{ percent(item.value, typeTotal()) }})</span>
            </div>
          </div>
          <div v-else class="qa-na">暂无数据</div>
        </div>
      </div>

      <!-- 高频问题关键词云 -->
      <div class="qa-section">
        <h3 class="qa-section__title">高频问题关键词</h3>
        <div v-if="keywordItems.length" class="qa-cloud">
          <span
            v-for="kw in keywordItems"
            :key="kw.keyword"
            class="qa-cloud-tag"
            :style="{
              fontSize: keywordFontSize(kw.count),
              opacity: keywordOpacity(kw.count),
            }"
          >
            {{ kw.keyword }}
          </span>
        </div>
        <div v-else class="qa-na">暂无关键词数据</div>
      </div>

      <!-- 问答记录列表 -->
      <div class="qa-section">
        <h3 class="qa-section__title">问答记录（最近 50 条）</h3>
        <div v-if="records.length" class="qa-records">
          <div v-for="(record, idx) in records" :key="record.id ?? idx" class="qa-record">
            <div class="qa-record__head">
              <span class="qa-record__time">{{ formatTime(record.time || record.created_at) }}</span>
              <span class="qa-record__source" :class="{ 'qa-record__source--rag': (record.source || '').includes('rag') || (record.source || '').includes('data') }">
                {{ sourceLabel(record.source) }}
              </span>
              <span class="qa-record__type">{{ typeLabel(record.question_type || record.type) }}</span>
            </div>
            <div class="qa-record__question">
              <span class="qa-record__q-label">问：</span>{{ record.question }}
            </div>
            <div v-if="record.answer" class="qa-record__answer">
              <span class="qa-record__a-label">答：</span>{{ record.answer }}
            </div>
          </div>
        </div>
        <div v-else class="qa-na">暂无问答记录</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.qa-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 统计卡片 */
.qa-stat-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.qa-stat-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel);
  padding: 20px;
  box-shadow: var(--shadow, 0 2px 8px rgba(0, 0, 0, 0.08));
}

.qa-stat-card--main {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark));
  color: #fff;
  border-color: var(--brand-dark);
}

.qa-stat-card--main .qa-stat-card__value {
  font-size: 48px;
  font-weight: 800;
  line-height: 1;
  margin-bottom: 8px;
}

.qa-stat-card--main .qa-stat-card__label {
  font-size: 15px;
  opacity: 0.9;
}

.qa-stat-card__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--brand-dark);
  margin-bottom: 14px;
}

/* 分布条 */
.qa-distribution {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.qa-dist-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.qa-dist-label {
  width: 64px;
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.qa-dist-bar-wrap {
  flex: 1;
  height: 18px;
  background: rgba(217, 95, 45, 0.08);
  border-radius: 9px;
  overflow: hidden;
}

.qa-dist-bar {
  height: 100%;
  border-radius: 9px;
  background: linear-gradient(90deg, var(--brand), var(--brand-dark));
  transition: width 0.4s ease;
  min-width: 4px;
}

.qa-dist-bar--type {
  background: linear-gradient(90deg, var(--green, #1f8a5b), #155a3c);
}

.qa-dist-value {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
}

/* 区块 */
.qa-section {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel);
  padding: 20px;
}

.qa-section__title {
  margin: 0 0 16px;
  font-size: 17px;
  font-weight: 700;
  color: var(--brand-dark);
}

/* 关键词云 */
.qa-cloud {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  line-height: 1.6;
}

.qa-cloud-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 16px;
  color: var(--brand-dark);
  background: rgba(217, 95, 45, 0.1);
  font-weight: 600;
  transition: all 0.2s;
  cursor: default;
}

.qa-cloud-tag:hover {
  background: rgba(217, 95, 45, 0.2);
  transform: translateY(-2px);
}

/* 问答记录 */
.qa-records {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 560px;
  overflow-y: auto;
  padding-right: 4px;
}

.qa-record {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.5);
  transition: box-shadow 0.2s;
}

.qa-record:hover {
  box-shadow: var(--shadow, 0 2px 8px rgba(0, 0, 0, 0.08));
}

.qa-record__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.qa-record__time {
  font-size: 12px;
  color: var(--muted);
}

.qa-record__source {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(188, 131, 33, 0.15);
  color: var(--yellow, #bc8321);
}

.qa-record__source--rag {
  background: rgba(31, 138, 91, 0.15);
  color: var(--green, #1f8a5b);
}

.qa-record__type {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  background: rgba(217, 95, 45, 0.1);
  color: var(--brand-dark);
}

.qa-record__question {
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink);
  margin-bottom: 4px;
}

.qa-record__q-label {
  font-weight: 700;
  color: var(--brand);
}

.qa-record__answer {
  font-size: 13px;
  line-height: 1.6;
  color: var(--muted);
}

.qa-record__a-label {
  font-weight: 700;
  color: var(--green, #1f8a5b);
}

/* 通用 */
.qa-na {
  text-align: center;
  color: var(--muted);
  padding: 24px 0;
  font-size: 14px;
}

.qa-loading {
  text-align: center;
  padding: 60px 0;
  color: var(--muted);
}

.qa-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: qa-spin 1s linear infinite;
  margin: 0 auto 12px;
}

@keyframes qa-spin {
  to {
    transform: rotate(360deg);
  }
}

.qa-error {
  background: #fee;
  color: #c33;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
}

@media (max-width: 768px) {
  .qa-stat-cards {
    grid-template-columns: 1fr;
  }
}
</style>
