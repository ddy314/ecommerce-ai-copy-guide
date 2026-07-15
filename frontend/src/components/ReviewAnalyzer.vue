<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type ReviewAnalysisResponse, type ComplaintItem } from '../api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function authHeaders(extra: Record<string, string> = {}): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<ReviewAnalysisResponse | null>(null)

const uploading = ref(false)
const uploadError = ref<string | null>(null)
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const allowedExtensions = ['.txt', '.csv', '.md', '.xlsx', '.docx']
const allowedMimeTypes = [
  'text/plain',
  'text/csv',
  'text/markdown',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

const form = ref({
  product_name: '示例商品',
  reviews_text: `这个产品非常好用，质量稳定
做工精致，推荐购买
物流很快，包装完好
价格有点贵，但质量不错
失望，收到货有异味，材质粗糙
客服态度很好，问题解决了
整体体验不错，会继续回购`,
})

// === 数据库商品选择相关状态 ===
interface ProductOption {
  id: number
  name: string
  price: number | null
  category?: string
}

const categories = ref<string[]>([])
const selectedCategory = ref('')
const products = ref<ProductOption[]>([])
const selectedProductId = ref<number | null>(null)
const loadingCategories = ref(false)
const loadingProducts = ref(false)
const loadingReviews = ref(false)
const dbError = ref<string | null>(null)

function getReviewsList(): string[] {
  return form.value.reviews_text.split('\n').filter(s => s.trim())
}

async function handleSubmit() {
  loading.value = true
  error.value = null
  try {
    result.value = await api.analyzeReviews({
      product_name: form.value.product_name,
      reviews: getReviewsList(),
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '分析失败'
  } finally {
    loading.value = false
  }
}

const positivePercent = computed(() => getSentimentPercentage(result.value?.sentiment.positive ?? 0))
const neutralPercent = computed(() => getSentimentPercentage(result.value?.sentiment.neutral ?? 0))
const negativePercent = computed(() => getSentimentPercentage(result.value?.sentiment.negative ?? 0))

const pieStyle = computed(() => {
  const pos = positivePercent.value
  const neu = neutralPercent.value
  const neg = negativePercent.value
  const posEnd = pos
  const neuEnd = pos + neu
  return {
    background: `conic-gradient(
      var(--green, #1f8a5b) 0% ${posEnd}%,
      var(--yellow, #bc8321) ${posEnd}% ${neuEnd}%,
      var(--brand, #d95f2d) ${neuEnd}% ${100 - neg + neg}%
    )`,
  }
})

function getSentimentPercentage(count: number): number {
  if (!result.value || result.value.total === 0) return 0
  return Math.round((count / result.value.total) * 100)
}

function complaintText(c: string | ComplaintItem): string {
  if (typeof c === 'string') return c
  const cat = c.category ? `[${c.category}] ` : ''
  return cat + c.content
}

function isValidFile(file: File): boolean {
  const name = file.name.toLowerCase()
  const hasExt = allowedExtensions.some((ext) => name.endsWith(ext))
  const hasMime = allowedMimeTypes.includes(file.type)
  return hasExt || hasMime || file.type === ''
}

function handleFileSelect(file: File) {
  if (!isValidFile(file)) {
    uploadError.value = '不支持的文件类型，请上传 txt/csv/md/xlsx/docx 文件'
    return
  }
  uploadError.value = null
  selectedFile.value = file
  uploadAndAnalyze(file)
}

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) handleFileSelect(file)
  target.value = ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFileSelect(file)
}

function onDragOver() {
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function triggerFileInput() {
  fileInput.value?.click()
}

async function uploadAndAnalyze(file: File) {
  uploading.value = true
  uploadError.value = null
  error.value = null
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('product_name', form.value.product_name || file.name)

    const res = await fetch(`${API_BASE}/api/user/reviews/upload`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }

    const data = await res.json()
    if (data.sentiment || data.total !== undefined) {
      result.value = data as ReviewAnalysisResponse
    } else if (data.reviews && Array.isArray(data.reviews)) {
      result.value = await api.analyzeReviews({
        product_name: form.value.product_name,
        reviews: data.reviews,
      })
    } else if (data.analysis) {
      result.value = data.analysis as ReviewAnalysisResponse
    } else {
      throw new Error('上传成功但未返回可分析的数据')
    }
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : '上传分析失败'
  } finally {
    uploading.value = false
    selectedFile.value = null
  }
}

async function fetchCategories() {
  loadingCategories.value = true
  dbError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/products?page=1&page_size=1`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    categories.value = data.categories || []
  } catch (e) {
    dbError.value = e instanceof Error ? e.message : '获取商品分类失败'
  } finally {
    loadingCategories.value = false
  }
}

async function onCategoryChange() {
  selectedProductId.value = null
  products.value = []
  if (!selectedCategory.value) return
  loadingProducts.value = true
  dbError.value = null
  try {
    const url = `${API_BASE}/api/products?category=${encodeURIComponent(selectedCategory.value)}&page=1&page_size=100`
    const res = await fetch(url, { headers: authHeaders() })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    products.value = data.products || []
  } catch (e) {
    dbError.value = e instanceof Error ? e.message : '获取商品列表失败'
  } finally {
    loadingProducts.value = false
  }
}

function onProductSelectChange(e: Event) {
  const target = e.target as HTMLSelectElement
  const raw = target.value.trim()
  const pid = raw ? Number(raw) : null
  selectedProductId.value = pid && !isNaN(pid) ? pid : null
  if (selectedProductId.value === null) return
  const product = products.value.find((p) => p.id === selectedProductId.value)
  if (product) {
    form.value.product_name = product.name
  }
}

async function loadProductReviews() {
  const pid = selectedProductId.value
  if (pid === null || pid === undefined || isNaN(pid)) return
  loadingReviews.value = true
  dbError.value = null
  try {
    const res = await fetch(
      `${API_BASE}/api/products/${pid}/reviews?limit=50`,
      { headers: authHeaders() },
    )
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    const data = await res.json()
    const list = (data.reviews || []) as Array<string | { content?: string }>
    const contents = list
      .map((r) => (typeof r === 'string' ? r : r.content))
      .filter((c): c is string => !!c && c.trim() !== '')
    form.value.reviews_text = contents.join('\n')
  } catch (e) {
    dbError.value = e instanceof Error ? e.message : '加载商品评论失败'
  } finally {
    loadingReviews.value = false
  }
}

function buildReportText(r: ReviewAnalysisResponse): string {
  const lines: string[] = []
  lines.push(`评论情感分析报告：${r.product_name}`)
  lines.push('')
  lines.push(`总评论数：${r.total}`)
  lines.push(`正面：${r.sentiment.positive} 条（${positivePercent.value}%）`)
  lines.push(`中性：${r.sentiment.neutral} 条（${neutralPercent.value}%）`)
  lines.push(`负面：${r.sentiment.negative} 条（${negativePercent.value}%）`)
  lines.push('')
  if (r.top_keywords.length) {
    lines.push('高频关键词：')
    lines.push(...r.top_keywords.map(k => `· ${k}`))
    lines.push('')
  }
  if (r.pain_points.length) {
    lines.push('用户痛点：')
    lines.push(...r.pain_points.map(p => `· ${p}`))
    lines.push('')
  }
  if (r.optimization_suggestions.length) {
    lines.push('优化建议：')
    lines.push(...r.optimization_suggestions.map(s => `· ${s}`))
    lines.push('')
  }
  if (r.sentiment_detail?.positive_reviews?.length) {
    lines.push('好评精选：')
    lines.push(...r.sentiment_detail.positive_reviews.map(rv => `✓ ${rv}`))
    lines.push('')
  }
  if (r.sentiment_detail?.negative_reviews?.length) {
    lines.push('差评反馈：')
    lines.push(...r.sentiment_detail.negative_reviews.map(rv => `✗ ${rv}`))
    lines.push('')
  }
  if (r.sentiment_detail?.complaints?.length) {
    lines.push('用户吐槽点：')
    lines.push(...r.sentiment_detail.complaints.map(c => `! ${complaintText(c)}`))
    lines.push('')
  }
  return lines.join('\n')
}

function downloadTxt() {
  if (!result.value) return
  const text = buildReportText(result.value)
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `评论情感分析_${result.value.product_name}_${new Date().toISOString().slice(0, 10)}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

const currentStep = computed(() => (result.value ? 3 : 2))

onMounted(() => {
  fetchCategories()
})
</script>

<template>
  <div class="feature-page">
    <div class="page-header">
      <div class="page-header__icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </div>
      <div class="page-header__text">
        <h1>评论情感分析</h1>
        <p>分析商品评论的情感分布、关键词和痛点，支持手动输入与文件上传</p>
      </div>
    </div>

    <div class="steps">
      <div
        v-for="(s, idx) in ['选择商品', '输入评论', '查看分析']"
        :key="idx"
        :class="['step', { active: idx + 1 <= currentStep, current: idx + 1 === currentStep }]"
      >
        <span class="step__num">{{ idx + 1 }}</span>
        <span class="step__label">{{ s }}</span>
      </div>
    </div>

    <div class="content-grid">
      <div class="input-column">
        <div class="card db-card">
          <div class="card__title">
            <span class="card__dot"></span>
            从数据库选择商品
          </div>
          <div class="db-picker">
            <div class="db-selects">
              <select
                v-model="selectedCategory"
                class="db-select"
                :disabled="loadingCategories"
                @change="onCategoryChange"
              >
                <option value="">{{ loadingCategories ? '加载分类中...' : '选择商品分类' }}</option>
                <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
              </select>
              <select
                :value="selectedProductId ?? ''"
                class="db-select"
                :disabled="loadingProducts || !selectedCategory"
                @change="onProductSelectChange"
              >
                <option value="">
                  {{ loadingProducts ? '加载商品中...' : !selectedCategory ? '请先选择分类' : '选择商品' }}
                </option>
                <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <button
              type="button"
              class="btn-load-reviews"
              :disabled="selectedProductId === null || loadingReviews"
              @click="loadProductReviews"
            >
              {{ loadingReviews ? '加载中...' : '加载商品评论' }}
            </button>
            <div v-if="dbError" class="db-error">{{ dbError }}</div>
          </div>
        </div>

        <form class="card input-form" @submit.prevent="handleSubmit">
          <div class="card__title">
            <span class="card__dot"></span>
            手动输入评论
          </div>
          <div class="form-group">
            <label>商品名称</label>
            <input v-model="form.product_name" type="text" placeholder="例如：示例商品" />
          </div>
          <div class="form-group">
            <label>评论列表（每行一条）<span class="required">*</span></label>
            <textarea
              v-model="form.reviews_text"
              rows="8"
              required
              placeholder="这个产品非常好用，质量稳定&#10;做工精致，推荐购买&#10;物流很快，包装完好"
            ></textarea>
            <span class="input-hint">已输入 {{ getReviewsList().length }} 条评论</span>
          </div>
          <button type="submit" class="btn-primary" :disabled="loading">
            {{ loading ? '分析中...' : '分析评论' }}
          </button>
        </form>

        <div class="divider">
          <span>或</span>
        </div>

        <div
          class="upload-zone"
          :class="{ dragging: isDragging, uploading }"
          @click="triggerFileInput"
          @dragover.prevent="onDragOver"
          @dragleave.prevent="onDragLeave"
          @drop.prevent="onDrop"
        >
          <input
            ref="fileInput"
            type="file"
            class="file-input"
            accept=".txt,.csv,.md,.xlsx,.docx"
            @change="onFileChange"
          />
          <template v-if="uploading">
            <div class="upload-spinner"></div>
            <p class="upload-text">正在上传并分析...</p>
          </template>
          <template v-else>
            <div class="upload-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17,8 12,3 7,8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
            </div>
            <p class="upload-text">
              <strong>拖拽文件到此处</strong> 或 <strong>点击上传</strong>
            </p>
            <p class="upload-hint">支持 txt / csv / md / xlsx / docx 格式</p>
            <p v-if="selectedFile" class="upload-file">已选择：{{ selectedFile.name }}</p>
          </template>
        </div>
        <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>
      </div>

      <div class="result-panel">
        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="uploadError && !result" class="error-message">{{ uploadError }}</div>

        <div v-if="result" class="result-content">
          <div class="result-meta">
            <div class="result-tags">
              <span class="meta-product">{{ result.product_name }}</span>
              <span class="meta-tag">共 {{ result.total }} 条评论</span>
            </div>
            <div class="result-actions">
              <button class="action-btn" @click="downloadTxt">下载 txt</button>
            </div>
          </div>

          <div class="result-card">
            <div class="section-label">
              <span class="section-dot"></span>
              <h3>情感分布</h3>
            </div>
            <div class="sentiment-chart">
              <div class="pie-chart" :style="pieStyle">
                <div class="pie-center">
                  <span class="pie-total">{{ result.total }}</span>
                  <span class="pie-label">总评论</span>
                </div>
              </div>
              <div class="sentiment-bars">
                <div class="bar-row">
                  <span class="bar-label">正面</span>
                  <div class="bar-track">
                    <div class="bar-fill bar-fill--positive" :style="{ width: positivePercent + '%' }"></div>
                  </div>
                  <span class="bar-value">{{ result.sentiment.positive }} ({{ positivePercent }}%)</span>
                </div>
                <div class="bar-row">
                  <span class="bar-label">中性</span>
                  <div class="bar-track">
                    <div class="bar-fill bar-fill--neutral" :style="{ width: neutralPercent + '%' }"></div>
                  </div>
                  <span class="bar-value">{{ result.sentiment.neutral }} ({{ neutralPercent }}%)</span>
                </div>
                <div class="bar-row">
                  <span class="bar-label">负面</span>
                  <div class="bar-track">
                    <div class="bar-fill bar-fill--negative" :style="{ width: negativePercent + '%' }"></div>
                  </div>
                  <span class="bar-value">{{ result.sentiment.negative }} ({{ negativePercent }}%)</span>
                </div>
              </div>
            </div>
            <div class="sentiment-stats">
              <div class="stat-card stat-card--positive">
                <span class="stat-value">{{ result.sentiment.positive }}</span>
                <span class="stat-label">正面</span>
              </div>
              <div class="stat-card stat-card--neutral">
                <span class="stat-value">{{ result.sentiment.neutral }}</span>
                <span class="stat-label">中性</span>
              </div>
              <div class="stat-card stat-card--negative">
                <span class="stat-value">{{ result.sentiment.negative }}</span>
                <span class="stat-label">负面</span>
              </div>
            </div>
          </div>

          <div v-if="result.top_keywords.length > 0" class="result-card">
            <div class="section-label">
              <span class="section-dot"></span>
              <h3>高频关键词</h3>
            </div>
            <div class="keywords">
              <span v-for="keyword in result.top_keywords" :key="keyword" class="keyword-tag">{{ keyword }}</span>
            </div>
          </div>

          <div v-if="result.pain_points.length > 0" class="result-card result-card--negative">
            <div class="section-label">
              <span class="section-dot section-dot--negative"></span>
              <h3>用户痛点</h3>
            </div>
            <ul class="point-list">
              <li v-for="point in result.pain_points" :key="point">{{ point }}</li>
            </ul>
          </div>

          <div v-if="result.optimization_suggestions.length > 0" class="result-card result-card--positive">
            <div class="section-label">
              <span class="section-dot section-dot--positive"></span>
              <h3>优化建议</h3>
            </div>
            <ul class="point-list">
              <li v-for="suggestion in result.optimization_suggestions" :key="suggestion">{{ suggestion }}</li>
            </ul>
          </div>

          <div
            v-if="result.sentiment_detail?.positive_reviews?.length"
            class="result-card result-card--positive"
          >
            <div class="section-label">
              <span class="section-dot section-dot--positive"></span>
              <h3>好评精选</h3>
            </div>
            <ul class="review-list">
              <li v-for="(r, i) in result.sentiment_detail.positive_reviews" :key="'pos' + i">
                <span class="review-badge review-badge--positive">✓</span>
                {{ r }}
              </li>
            </ul>
          </div>

          <div
            v-if="result.sentiment_detail?.negative_reviews?.length"
            class="result-card result-card--negative"
          >
            <div class="section-label">
              <span class="section-dot section-dot--negative"></span>
              <h3>差评反馈</h3>
            </div>
            <ul class="review-list">
              <li v-for="(r, i) in result.sentiment_detail.negative_reviews" :key="'neg' + i">
                <span class="review-badge review-badge--negative">✗</span>
                {{ r }}
              </li>
            </ul>
          </div>

          <div
            v-if="result.sentiment_detail?.complaints?.length"
            class="result-card result-card--complaint"
          >
            <div class="section-label">
              <span class="section-dot section-dot--complaint"></span>
              <h3>用户吐槽点</h3>
            </div>
            <ul class="review-list">
              <li v-for="(c, i) in result.sentiment_detail.complaints" :key="'cmp' + i">
                <span class="review-badge review-badge--complaint">!</span>
                {{ complaintText(c) }}
              </li>
            </ul>
          </div>
        </div>

        <div v-else-if="loading || uploading" class="skeleton-wrap">
          <div class="skeleton skeleton--chart"></div>
          <div v-for="i in 3" :key="i" class="skeleton skeleton--line"></div>
        </div>

        <div v-else class="empty-state">
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <p>输入评论或上传文件后查看分析结果</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.feature-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 36px 20px 48px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 28px;
}

.page-header__icon {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark, #8a3a1f));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12px 28px rgba(217, 95, 45, 0.28);
  flex-shrink: 0;
}

.page-header__icon svg {
  width: 30px;
  height: 30px;
}

.page-header__text h1 {
  font-size: 30px;
  margin: 0 0 6px 0;
  color: var(--ink);
}

.page-header__text p {
  color: var(--muted);
  margin: 0;
  font-size: 15px;
}

.steps {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
  padding: 14px 18px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.step {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 14px;
  font-weight: 600;
  transition: color 0.2s;
}

.step__num {
  width: 26px;
  height: 26px;
  display: inline-grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.06);
  font-size: 13px;
}

.step.active .step__num {
  background: var(--brand);
  color: #fff;
}

.step.current {
  color: var(--brand-dark);
}

.step:not(:last-child)::after {
  content: '';
  width: 28px;
  height: 1px;
  background: var(--line);
  margin-left: 4px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 28px;
  align-items: start;
}

.input-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.card__title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 16px;
}

.card__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--brand);
}

.db-picker {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.db-selects {
  display: flex;
  flex-direction: row;
  gap: 10px;
  min-width: 0;
  max-width: 100%;
}

.db-select {
  flex: 1;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 15px;
  font-family: inherit;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  transition: border-color 0.2s;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.db-select:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

.db-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-load-reviews {
  padding: 12px 24px;
  background: rgba(217, 95, 45, 0.08);
  color: var(--brand);
  border: 1px solid var(--brand);
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-load-reviews:hover:not(:disabled) {
  background: var(--brand);
  color: white;
  transform: translateY(-1px);
}

.btn-load-reviews:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.db-error {
  background: #fee;
  color: #c33;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
}

.input-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 100%;
  overflow: hidden;
  min-width: 0;
}

.form-group label {
  font-weight: 700;
  font-size: 14px;
  color: var(--ink);
}

.required {
  color: var(--brand);
}

.form-group input,
.form-group textarea {
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: 13px;
  font-size: 15px;
  font-family: inherit;
  background: #fff;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;
  overflow-wrap: break-word;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

.form-group textarea {
  resize: vertical;
  min-height: 160px;
  line-height: 1.6;
  word-break: break-all;
}

.input-hint {
  font-size: 13px;
  color: var(--muted);
  text-align: right;
}

.btn-primary {
  padding: 14px 24px;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark, #8a3a1f));
  color: white;
  border: none;
  border-radius: 13px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 8px 20px rgba(217, 95, 45, 0.25);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 26px rgba(217, 95, 45, 0.32);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--muted);
  font-size: 14px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--line);
}

.upload-zone {
  border: 2px dashed var(--line);
  border-radius: 18px;
  padding: 34px 22px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--panel);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.upload-zone:hover {
  border-color: var(--brand);
  background: rgba(217, 95, 45, 0.04);
}

.upload-zone.dragging {
  border-color: var(--brand);
  background: rgba(217, 95, 45, 0.1);
  transform: scale(1.01);
}

.upload-zone.uploading {
  border-color: var(--brand);
  pointer-events: none;
  opacity: 0.8;
}

.file-input {
  display: none;
}

.upload-icon {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--brand);
  background: rgba(217, 95, 45, 0.1);
}

.upload-icon svg {
  width: 26px;
  height: 26px;
}

.upload-text {
  margin: 0;
  font-size: 15px;
  color: var(--ink);
}

.upload-text strong {
  color: var(--brand);
}

.upload-hint {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.upload-file {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--brand-dark);
  font-weight: 600;
}

.upload-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: ra-spin 1s linear infinite;
  margin-bottom: 4px;
}

@keyframes ra-spin {
  to { transform: rotate(360deg); }
}

.upload-error {
  background: #fee;
  color: #c33;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
}

.result-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 26px;
  min-height: 540px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.error-message {
  background: #fff0f0;
  color: #c33;
  padding: 12px 16px;
  border-radius: 11px;
  margin-bottom: 16px;
  font-size: 14px;
  border: 1px solid rgba(192, 57, 43, 0.15);
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
  animation: fade-up 0.45s ease;
}

.result-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--line);
  flex-wrap: wrap;
}

.result-tags {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.meta-product {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}

.meta-tag {
  display: inline-block;
  padding: 5px 12px;
  background: var(--brand);
  color: white;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.result-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.result-card {
  padding: 18px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.04);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  transition: transform 0.2s;
}

.result-card:hover {
  transform: translateY(-1px);
}

.result-card--positive {
  background: linear-gradient(135deg, rgba(31, 138, 91, 0.06), rgba(31, 138, 91, 0.02));
  border-color: rgba(31, 138, 91, 0.15);
}

.result-card--negative {
  background: linear-gradient(135deg, rgba(217, 95, 45, 0.06), rgba(217, 95, 45, 0.02));
  border-color: rgba(217, 95, 45, 0.15);
}

.result-card--complaint {
  background: linear-gradient(135deg, rgba(228, 57, 60, 0.06), rgba(228, 57, 60, 0.02));
  border-color: rgba(228, 57, 60, 0.15);
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.section-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--brand);
}

.section-dot--positive {
  background: var(--green, #1f8a5b);
}

.section-dot--negative {
  background: var(--brand, #d95f2d);
}

.section-dot--complaint {
  background: #e4393c;
}

.result-card h3 {
  font-size: 15px;
  margin: 0;
  color: var(--brand-dark);
}

.sentiment-chart {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.pie-chart {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  flex: 0 0 auto;
  position: relative;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.pie-center {
  position: absolute;
  inset: 26px;
  border-radius: 50%;
  background: var(--panel);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.pie-total {
  font-size: 26px;
  font-weight: 800;
  color: var(--brand-dark);
  line-height: 1;
}

.pie-label {
  font-size: 12px;
  color: var(--muted);
  margin-top: 4px;
}

.sentiment-bars {
  flex: 1;
  min-width: 180px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.bar-label {
  width: 38px;
  font-weight: 600;
  color: var(--ink);
}

.bar-track {
  flex: 1;
  height: 10px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 999px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.8s ease;
}

.bar-fill--positive {
  background: var(--green, #1f8a5b);
}

.bar-fill--neutral {
  background: var(--yellow, #bc8321);
}

.bar-fill--negative {
  background: var(--brand, #d95f2d);
}

.bar-value {
  color: var(--muted);
  min-width: 80px;
  text-align: right;
}

.sentiment-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.02);
}

.stat-card--positive {
  background: rgba(31, 138, 91, 0.08);
}

.stat-card--neutral {
  background: rgba(188, 131, 33, 0.08);
}

.stat-card--negative {
  background: rgba(217, 95, 45, 0.08);
}

.stat-value {
  font-size: 22px;
  font-weight: 800;
  color: var(--ink);
}

.stat-label {
  font-size: 13px;
  color: var(--muted);
}

.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-tag {
  padding: 6px 14px;
  background: rgba(217, 95, 45, 0.1);
  border: 1px solid rgba(217, 95, 45, 0.25);
  border-radius: 20px;
  font-size: 14px;
  color: var(--brand-dark);
  transition: all 0.2s;
}

.keyword-tag:hover {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.point-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.point-list li {
  padding: 12px 16px;
  border-radius: 11px;
  border-left: 3px solid var(--brand);
  line-height: 1.5;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.7);
}

.result-card--positive .point-list li {
  border-left-color: var(--green, #1f8a5b);
}

.result-card--complaint .point-list li {
  border-left-color: #e4393c;
}

.review-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-list li {
  padding: 12px 14px;
  border-radius: 11px;
  line-height: 1.5;
  font-size: 14px;
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.7);
}

.result-card--positive .review-list li {
  border-left: 3px solid var(--green, #1f8a5b);
}

.result-card--negative .review-list li {
  border-left: 3px solid var(--brand, #d95f2d);
}

.result-card--complaint .review-list li {
  border-left: 3px solid #e4393c;
}

.review-badge {
  width: 22px;
  height: 22px;
  display: inline-grid;
  place-items: center;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  color: #fff;
}

.review-badge--positive {
  background: var(--green, #1f8a5b);
}

.review-badge--negative {
  background: var(--brand, #d95f2d);
}

.review-badge--complaint {
  background: #e4393c;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 360px;
  color: var(--muted);
  text-align: center;
}

.empty-icon {
  width: 76px;
  height: 76px;
  color: var(--line);
  margin-bottom: 16px;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.skeleton-wrap {
  display: flex;
  flex-direction: column;
  gap: 14px;
  animation: pulse 1.6s infinite;
}

.skeleton {
  background: linear-gradient(90deg, rgba(0, 0, 0, 0.04) 25%, rgba(0, 0, 0, 0.08) 50%, rgba(0, 0, 0, 0.04) 75%);
  background-size: 200% 100%;
  border-radius: 12px;
  animation: shimmer 1.6s infinite;
}

.skeleton--chart {
  height: 180px;
}

.skeleton--line {
  height: 90px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.75; }
}

@keyframes fade-up {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 820px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .steps {
    overflow-x: auto;
  }

  .sentiment-chart {
    flex-direction: column;
    align-items: flex-start;
  }

  .sentiment-stats {
    grid-template-columns: 1fr;
  }

  .db-selects {
    flex-direction: column;
  }
}
</style>
