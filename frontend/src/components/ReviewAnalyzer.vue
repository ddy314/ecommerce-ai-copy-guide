<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type ReviewAnalysisResponse, type ComplaintItem } from '../api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/** 携带鉴权头的请求头 */
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

// 文件上传相关状态
const uploading = ref(false)
const uploadError = ref<string | null>(null)
const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

// 允许的文件类型
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

/** 饼图百分比 */
const positivePercent = computed(() => getSentimentPercentage(result.value?.sentiment.positive ?? 0))
const neutralPercent = computed(() => getSentimentPercentage(result.value?.sentiment.neutral ?? 0))
const negativePercent = computed(() => getSentimentPercentage(result.value?.sentiment.negative ?? 0))

/** conic-gradient 饼图样式 */
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

/** 吐槽点解析：兼容字符串与对象结构 */
function complaintText(c: string | ComplaintItem): string {
  if (typeof c === 'string') return c
  const cat = c.category ? `[${c.category}] ` : ''
  return cat + c.content
}

/** 文件类型校验 */
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
  // 选择文件后自动上传分析
  uploadAndAnalyze(file)
}

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) handleFileSelect(file)
  // 重置 input 以便重复选择同一文件
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

/** 上传文件并自动分析 */
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
    // 接口可能直接返回分析结果，也可能返回评论列表需要再分析
    if (data.sentiment || data.total !== undefined) {
      result.value = data as ReviewAnalysisResponse
    } else if (data.reviews && Array.isArray(data.reviews)) {
      // 返回评论列表，调用分析接口
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

// === 数据库商品选择相关方法 ===

/** 格式化商品价格展示 */
function formatProductPrice(price: number | null | undefined): string {
  if (price === null || price === undefined || price === 0) return ''
  return ` ¥${price}`
}

/** 从数据库获取商品分类列表 */
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

/** 分类变化时，拉取该分类下的商品列表 */
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

/** 商品选择变化时，自动填充商品名称 */
function onProductSelectChange(e: Event) {
  const target = e.target as HTMLSelectElement
  selectedProductId.value = target.value ? Number(target.value) : null
  if (selectedProductId.value === null) return
  const product = products.value.find((p) => p.id === selectedProductId.value)
  if (product) {
    form.value.product_name = product.name
  }
}

/** 加载选中商品的评论到文本框 */
async function loadProductReviews() {
  if (selectedProductId.value === null) return
  loadingReviews.value = true
  dbError.value = null
  try {
    const res = await fetch(
      `${API_BASE}/api/products/${selectedProductId.value}/reviews?limit=50`,
      { headers: authHeaders() },
    )
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
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

onMounted(() => {
  fetchCategories()
})

</script>

<template>
  <div class="feature-page">
    <div class="page-header">
      <h1>评论情感分析</h1>
      <p>分析商品评论的情感分布、关键词和痛点，支持手动输入与文件上传</p>
    </div>

    <div class="content-grid">
      <div class="input-column">
        <!-- 手动输入表单 -->
        <form class="input-form" @submit.prevent="handleSubmit">
          <!-- 从数据库选择商品 -->
          <div class="form-group db-picker">
            <label>从数据库选择商品</label>
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
                :value="selectedProductId"
                class="db-select"
                :disabled="loadingProducts || !selectedCategory"
                @change="onProductSelectChange"
              >
                <option :value="null">
                  {{ loadingProducts ? '加载商品中...' : !selectedCategory ? '请先选择分类' : '选择商品' }}
                </option>
                <option v-for="p in products" :key="p.id" :value="p.id">
                  {{ p.name }}
                </option>
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

          <div class="form-group">
            <label>评论列表（每行一条）*</label>
            <textarea
              v-model="form.reviews_text"
              rows="8"
              required
              placeholder="这个产品非常好用，质量稳定&#10;做工精致，推荐购买&#10;物流很快，包装完好"
            ></textarea>
          </div>

          <button type="submit" class="btn-primary" :disabled="loading">
            {{ loading ? '分析中...' : '分析评论' }}
          </button>
        </form>

        <!-- 分隔线 -->
        <div class="divider">
          <span>或</span>
        </div>

        <!-- 文件上传区域 -->
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
            <div class="upload-icon">↑</div>
            <p class="upload-text">
              <strong>拖拽文件到此处</strong> 或 <strong>点击上传</strong>
            </p>
            <p class="upload-hint">支持 txt / csv / md / xlsx / docx 格式</p>
          </template>
        </div>
        <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>
      </div>

      <!-- 结果展示 -->
      <div class="result-panel">
        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="uploadError && !result" class="error-message">{{ uploadError }}</div>

        <div v-if="result" class="result-content">
          <!-- 情感分布饼图 -->
          <div class="result-section">
            <h3>情感分布</h3>
            <div class="sentiment-chart">
              <div class="pie-chart" :style="pieStyle">
                <div class="pie-center">
                  <span class="pie-total">{{ result.total }}</span>
                  <span class="pie-label">总评论</span>
                </div>
              </div>
              <div class="pie-legend">
                <div class="legend-item">
                  <span class="legend-dot legend-dot--positive"></span>
                  <span class="legend-name">正面</span>
                  <span class="legend-value">{{ result.sentiment.positive }} ({{ positivePercent }}%)</span>
                </div>
                <div class="legend-item">
                  <span class="legend-dot legend-dot--neutral"></span>
                  <span class="legend-name">中性</span>
                  <span class="legend-value">{{ result.sentiment.neutral }} ({{ neutralPercent }}%)</span>
                </div>
                <div class="legend-item">
                  <span class="legend-dot legend-dot--negative"></span>
                  <span class="legend-name">负面</span>
                  <span class="legend-value">{{ result.sentiment.negative }} ({{ negativePercent }}%)</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 好评 -->
          <div
            v-if="result.sentiment_detail?.positive_reviews?.length"
            class="result-section result-section--positive"
          >
            <h3>好评精选</h3>
            <ul class="review-list">
              <li v-for="(r, i) in result.sentiment_detail.positive_reviews" :key="'pos' + i">
                {{ r }}
              </li>
            </ul>
          </div>

          <!-- 差评 -->
          <div
            v-if="result.sentiment_detail?.negative_reviews?.length"
            class="result-section result-section--negative"
          >
            <h3>差评反馈</h3>
            <ul class="review-list">
              <li v-for="(r, i) in result.sentiment_detail.negative_reviews" :key="'neg' + i">
                {{ r }}
              </li>
            </ul>
          </div>

          <!-- 吐槽点 -->
          <div
            v-if="result.sentiment_detail?.complaints?.length"
            class="result-section result-section--complaint"
          >
            <h3>用户吐槽点</h3>
            <ul class="review-list">
              <li v-for="(c, i) in result.sentiment_detail.complaints" :key="'cmp' + i">
                {{ complaintText(c) }}
              </li>
            </ul>
          </div>

          <!-- 关键词 -->
          <div v-if="result.top_keywords.length > 0" class="result-section">
            <h3>高频关键词</h3>
            <div class="keywords">
              <span v-for="keyword in result.top_keywords" :key="keyword" class="keyword-tag">
                {{ keyword }}
              </span>
            </div>
          </div>

          <!-- 痛点 -->
          <div v-if="result.pain_points.length > 0" class="result-section">
            <h3>用户痛点</h3>
            <ul class="pain-points">
              <li v-for="point in result.pain_points" :key="point">{{ point }}</li>
            </ul>
          </div>

          <!-- 优化建议 -->
          <div v-if="result.optimization_suggestions.length > 0" class="result-section">
            <h3>优化建议</h3>
            <ul class="suggestions">
              <li v-for="suggestion in result.optimization_suggestions" :key="suggestion">
                {{ suggestion }}
              </li>
            </ul>
          </div>
        </div>

        <div v-else-if="!loading && !uploading" class="empty-state">
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
  padding: 40px 20px;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 32px;
  margin: 0 0 8px 0;
}

.page-header p {
  color: var(--muted);
  margin: 0;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
}

.input-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  min-width: 0;
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
  font-weight: 600;
  font-size: 14px;
}

.form-group input,
.form-group textarea {
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  font-size: 15px;
  font-family: inherit;
  background: var(--panel);
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow-wrap: break-word;
}

.form-group textarea {
  resize: none;
  min-height: 160px;
  word-break: break-all;
}

/* 数据库商品选择 */
.db-picker {
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(217, 95, 45, 0.03);
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
  background: var(--panel);
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
}

.db-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-load-reviews {
  padding: 12px 24px;
  background: var(--panel);
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

.btn-primary {
  padding: 14px 24px;
  background: var(--brand);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--brand-dark);
  transform: translateY(-2px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 分隔线 */
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

/* 文件上传区域 */
.upload-zone {
  border: 2px dashed var(--line);
  border-radius: 16px;
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--panel);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
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
  display: inline-grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 50%;
  font-size: 24px;
  font-weight: 700;
  color: var(--brand);
  background: rgba(217, 95, 45, 0.1);
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
  to {
    transform: rotate(360deg);
  }
}

.upload-error {
  background: #fee;
  color: #c33;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
}

/* 结果面板 */
.result-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 24px;
  min-height: 400px;
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.result-section {
  padding: 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.5);
}

.result-section h3 {
  font-size: 16px;
  margin: 0 0 16px 0;
  color: var(--brand-dark);
}

/* 饼图 */
.sentiment-chart {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.pie-chart {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  flex: 0 0 auto;
  position: relative;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.pie-center {
  position: absolute;
  inset: 28px;
  border-radius: 50%;
  background: var(--panel);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.pie-total {
  font-size: 28px;
  font-weight: 800;
  color: var(--brand-dark);
  line-height: 1;
}

.pie-label {
  font-size: 12px;
  color: var(--muted);
  margin-top: 4px;
}

.pie-legend {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-width: 160px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex: 0 0 auto;
}

.legend-dot--positive {
  background: var(--green, #1f8a5b);
}

.legend-dot--neutral {
  background: var(--yellow, #bc8321);
}

.legend-dot--negative {
  background: var(--brand, #d95f2d);
}

.legend-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  width: 40px;
}

.legend-value {
  font-size: 14px;
  color: var(--muted);
}

/* 评价列表 */
.review-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-list li {
  padding: 10px 14px;
  border-radius: 8px;
  line-height: 1.5;
  font-size: 14px;
}

.result-section--positive .review-list li {
  background: rgba(31, 138, 91, 0.08);
  border-left: 3px solid var(--green, #1f8a5b);
}

.result-section--negative .review-list li {
  background: rgba(217, 95, 45, 0.08);
  border-left: 3px solid var(--brand, #d95f2d);
}

.result-section--complaint .review-list li {
  background: rgba(228, 57, 60, 0.08);
  border-left: 3px solid #e4393c;
}

.result-section--complaint h3 {
  color: #c5282b;
}

.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-tag {
  padding: 6px 14px;
  background: rgba(217, 95, 45, 0.1);
  border: 1px solid rgba(217, 95, 45, 0.3);
  border-radius: 20px;
  font-size: 14px;
  color: var(--brand-dark);
}

.pain-points {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pain-points li {
  padding: 10px 14px;
  background: rgba(217, 95, 45, 0.08);
  border-radius: 8px;
  border-left: 3px solid var(--brand);
  line-height: 1.5;
  font-size: 14px;
}

.suggestions {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.suggestions li {
  padding: 10px 14px;
  background: rgba(31, 138, 91, 0.08);
  border-radius: 8px;
  border-left: 3px solid var(--green, #1f8a5b);
  line-height: 1.5;
  font-size: 14px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--muted);
  text-align: center;
  min-height: 360px;
}

@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .sentiment-chart {
    flex-direction: column;
    align-items: flex-start;
  }

  .db-selects {
    flex-direction: column;
  }
}
</style>
