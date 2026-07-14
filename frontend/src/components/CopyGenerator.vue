<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type CopyGenerationResponse } from '../api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<CopyGenerationResponse | null>(null)

const form = ref({
  product_name: '云感护腰办公椅',
  category: '',
  audience: '久坐办公人群',
  style: '专业',
  selling_points: ['护腰支撑', '透气坐垫', '稳固耐用'],
  selling_points_text: '护腰支撑\n透气坐垫\n稳固耐用',
})

// ---------- 商品数据库选择 ----------
interface Product {
  id: number
  name: string
  category: string
  price: number | null
}

const categories = ref<string[]>([])
const categoryCounts = ref<Record<string, number>>({})
const selectedCategory = ref('')
const products = ref<Product[]>([])
const selectedProductId = ref<number | null>(null)
const productsLoading = ref(false)

/** 拉取类目列表（附带 category_counts） */
async function fetchCategories() {
  try {
    const response = await fetch(
      `${API_BASE}/api/products?page=1&page_size=1`
    )
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    categories.value = data.categories || []
    categoryCounts.value = data.category_counts || {}
  } catch (e) {
    // 静默失败，不影响手动填写
    console.warn('加载类目失败:', e)
  }
}

/** 选择类目后拉取该类目下的商品列表 */
async function onCategoryChange() {
  products.value = []
  selectedProductId.value = null
  if (!selectedCategory.value) return

  productsLoading.value = true
  try {
    const params = new URLSearchParams()
    params.set('category', selectedCategory.value)
    params.set('page', '1')
    params.set('page_size', '100')
    const response = await fetch(
      `${API_BASE}/api/products?${params.toString()}`
    )
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    products.value = data.products || []
  } catch (e) {
    console.warn('加载商品列表失败:', e)
    products.value = []
  } finally {
    productsLoading.value = false
  }
}

/** 选择商品后自动填充表单字段 */
function onProductChange() {
  if (selectedProductId.value == null) return
  const product = products.value.find(p => p.id === selectedProductId.value)
  if (!product) return
  form.value.product_name = product.name
  form.value.category = product.category
}

const styleOptions = [
  { value: '简洁', desc: '直击卖点，干净利落' },
  { value: '高端', desc: '质感与格调，彰显品位' },
  { value: '活泼', desc: '轻松有趣，贴近用户' },
  { value: '专业', desc: '可信严谨，强调参数' },
  { value: '促销', desc: '限时优惠，刺激下单' },
]

// 一键复制状态
const copied = ref(false)

/** 拼接文案结果为纯文本 */
function buildCopyText(r: CopyGenerationResponse): string {
  return [
    `【${r.style}风格】${r.title}`,
    '',
    '商品卖点：',
    ...r.selling_points.map((p) => `· ${p}`),
    '',
    '详情页文案：',
    r.detail_copy,
    '',
    `广告语：${r.ad_slogan}`,
  ].join('\n')
}

async function copyResult() {
  if (!result.value) return
  const text = buildCopyText(result.value)
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    // 兼容旧浏览器
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
  }
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 2000)
}

async function handleSubmit() {
  if (!form.value.product_name) {
    error.value = '请先从数据库选择商品'
    return
  }
  loading.value = true
  error.value = null
  try {
    result.value = await api.generateCopy({
      product_name: form.value.product_name,
      audience: form.value.audience,
      style: form.value.style,
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成失败'
  } finally {
    loading.value = false
  }
}

// 组件挂载时拉取类目列表，供下拉选择
onMounted(() => {
  fetchCategories()
})
</script>

<template>
  <div class="feature-page">
    <div class="page-header">
      <h1>商品文案生成</h1>
      <p>输入商品信息，AI 将生成标题、卖点、详情页文案和广告语</p>
    </div>

    <div class="content-grid">
      <form class="input-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>从数据库选择商品</label>
          <div class="select-row">
            <select
              v-model="selectedCategory"
              class="select-item"
              @change="onCategoryChange"
            >
              <option value="">请选择类目</option>
              <option v-for="cat in categories" :key="cat" :value="cat">
                {{ cat }}<template v-if="categoryCounts[cat]"> ({{ categoryCounts[cat] }})</template>
              </option>
            </select>
            <select
              v-model="selectedProductId"
              class="select-item"
              :disabled="!selectedCategory || productsLoading"
              @change="onProductChange"
            >
              <option :value="null">请选择商品</option>
              <option v-if="productsLoading" :value="null" disabled>加载中...</option>
              <template v-else>
                <option v-for="p in products" :key="p.id" :value="p.id">
                  {{ p.name }}
                </option>
              </template>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>目标人群</label>
          <input v-model="form.audience" type="text" placeholder="例如：久坐办公人群" />
        </div>

        <div class="form-group">
          <label>文案风格</label>
          <div class="style-options">
            <label
              v-for="opt in styleOptions"
              :key="opt.value"
              class="style-option"
              :class="{ active: form.style === opt.value }"
            >
              <input type="radio" v-model="form.style" :value="opt.value" />
              <span class="style-name">{{ opt.value }}</span>
              <span class="style-desc">{{ opt.desc }}</span>
            </label>
          </div>
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '生成中...' : '生成文案' }}
        </button>
      </form>

      <div class="result-panel">
        <div v-if="error" class="error-message">{{ error }}</div>

        <div v-if="result" class="result-content">
          <div class="result-meta">
            <span class="meta-tag">{{ result.style }}</span>
            <span class="meta-product">{{ result.product_name }}</span>
            <button class="copy-btn" @click="copyResult">
              {{ copied ? '已复制' : '一键复制' }}
            </button>
          </div>

          <div class="result-section">
            <h3>推荐标题</h3>
            <p class="highlight-text">{{ result.title }}</p>
          </div>

          <div class="result-section">
            <h3>商品卖点</h3>
            <ul class="selling-points">
              <li v-for="point in result.selling_points" :key="point">{{ point }}</li>
            </ul>
          </div>

          <div class="result-section">
            <h3>详情页文案</h3>
            <p>{{ result.detail_copy }}</p>
          </div>

          <div class="result-section">
            <h3>广告语</h3>
            <blockquote>{{ result.ad_slogan }}</blockquote>
          </div>
        </div>

        <div v-else-if="!loading" class="empty-state">
          <p>填写商品信息后点击"生成文案"查看结果</p>
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
.form-group select,
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

.form-group select {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.form-group textarea {
  resize: none;
  min-height: 100px;
  word-break: break-all;
}

/* 商品选择下拉区 */
.select-row {
  display: flex;
  gap: 12px;
  min-width: 0;
  max-width: 100%;
}

.select-row .select-item {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.style-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.style-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
  cursor: pointer;
  transition: all 0.2s;
}

.style-option:hover {
  border-color: var(--brand);
}

.style-option.active {
  border-color: var(--brand);
  background: rgba(217, 95, 45, 0.1);
  box-shadow: 0 0 0 1px var(--brand) inset;
}

.style-option input {
  display: none;
}

.style-name {
  font-weight: 700;
  color: var(--brand-dark);
}

.style-desc {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
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

.result-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--line);
}

.meta-tag {
  display: inline-block;
  padding: 4px 12px;
  background: var(--brand);
  color: white;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.meta-product {
  font-size: 15px;
  color: var(--muted);
  flex: 1;
}

.copy-btn {
  margin-left: auto;
  padding: 6px 16px;
  border: 1px solid var(--brand);
  border-radius: 20px;
  background: rgba(217, 95, 45, 0.08);
  color: var(--brand-dark);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.copy-btn:hover {
  background: var(--brand);
  color: white;
}

.result-section h3 {
  font-size: 16px;
  margin: 0 0 12px 0;
  color: var(--brand-dark);
}

.highlight-text {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.4;
  margin: 0;
}

.selling-points {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selling-points li {
  padding: 10px 14px;
  background: rgba(217, 95, 45, 0.08);
  border-radius: 8px;
  border-left: 3px solid var(--brand);
}

blockquote {
  margin: 0;
  padding: 16px;
  background: linear-gradient(135deg, #211a14, #5d301e);
  color: #ffe0bd;
  border-radius: 12px;
  font-size: 18px;
  font-style: italic;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--muted);
  text-align: center;
}

@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .style-options {
    grid-template-columns: 1fr;
  }

  .select-row {
    flex-direction: column;
  }
}
</style>
