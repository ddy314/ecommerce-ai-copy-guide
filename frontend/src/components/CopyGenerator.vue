<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type CopyGenerationResponse } from '../api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<CopyGenerationResponse | null>(null)

// 输入模式：db / manual
const inputMode = ref<'db' | 'manual'>('db')

const form = ref({
  product_name: '云感护腰办公椅',
  category: '',
  price: '',
  audience: '久坐办公人群',
  style: '专业',
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

async function fetchCategories() {
  try {
    const response = await fetch(`${API_BASE}/api/products?page=1&page_size=1`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    categories.value = data.categories || []
    categoryCounts.value = data.category_counts || {}
  } catch (e) {
    console.warn('加载类目失败:', e)
  }
}

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
    const response = await fetch(`${API_BASE}/api/products?${params.toString()}`)
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

function onProductChange() {
  if (selectedProductId.value == null) return
  const product = products.value.find((p) => p.id === selectedProductId.value)
  if (!product) return
  form.value.product_name = product.name
  form.value.category = product.category
  form.value.price = product.price != null ? String(product.price) : ''
}

const styleOptions = [
  { value: '简洁', desc: '直击卖点，干净利落', icon: '✦' },
  { value: '高端', desc: '质感与格调，彰显品位', icon: '◆' },
  { value: '活泼', desc: '轻松有趣，贴近用户', icon: '★' },
  { value: '专业', desc: '可信严谨，强调参数', icon: '●' },
  { value: '促销', desc: '限时优惠，刺激下单', icon: '▲' },
]

const copied = ref(false)
const editableResult = ref<CopyGenerationResponse | null>(null)
const editableSellingPointsText = ref('')
const editingResult = ref(false)

function enterEditMode() {
  if (!result.value) return
  editableResult.value = JSON.parse(JSON.stringify(result.value))
  editableSellingPointsText.value = editableResult.value!.selling_points.join('\n')
  editingResult.value = true
}

function saveEdit() {
  if (!editableResult.value) return
  editableResult.value.selling_points = editableSellingPointsText.value
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean)
  result.value = { ...editableResult.value }
  editingResult.value = false
  editableResult.value = null
  editableSellingPointsText.value = ''
}

function cancelEdit() {
  editingResult.value = false
  editableResult.value = null
  editableSellingPointsText.value = ''
}

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

function downloadTxt() {
  if (!result.value) return
  const text = buildCopyText(result.value)
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `商品文案_${result.value.product_name}_${new Date().toISOString().slice(0, 10)}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

async function copyResult() {
  if (!result.value) return
  const text = buildCopyText(result.value)
  try {
    await navigator.clipboard.writeText(text)
  } catch {
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
  setTimeout(() => (copied.value = false), 2000)
}

async function handleSubmit() {
  if (!form.value.product_name.trim()) {
    error.value = '请输入商品名称'
    return
  }
  loading.value = true
  error.value = null
  try {
    result.value = await api.generateCopy({
      product_name: form.value.product_name,
      audience: form.value.audience,
      style: form.value.style,
      selling_points: form.value.selling_points_text.split('\n').filter((s) => s.trim()),
    })
    editingResult.value = false
    editableResult.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成失败'
  } finally {
    loading.value = false
  }
}

// ---------- 导入商品管理 ----------
const importModalVisible = ref(false)
const importLoading = ref(false)
const importError = ref<string | null>(null)
const importPublish = ref(true)

function openImportModal() {
  importPublish.value = true
  importError.value = null
  importModalVisible.value = true
}

function closeImportModal() {
  importModalVisible.value = false
}

function authHeaders(extra: Record<string, string> = {}): HeadersInit {
  const token = localStorage.getItem('token')
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

async function confirmImport() {
  if (!result.value) return
  importLoading.value = true
  importError.value = null
  try {
    const payload = {
      name: result.value.product_name || form.value.product_name,
      category: form.value.category || '综合',
      price: form.value.price ? Number(form.value.price) : 0,
      selling_points: result.value.selling_points.join('\n'),
      specs: result.value.detail_copy,
      image_url: '',
      image_urls: [],
      videos: [],
      is_published: importPublish.value,
    }
    const res = await fetch(`${API_BASE}/api/merchant/products`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.message || `HTTP ${res.status}`)
    }
    importModalVisible.value = false
    alert(importPublish.value ? '商品已导入并上架' : '商品已导入（未上架）')
  } catch (e) {
    importError.value = e instanceof Error ? e.message : '导入失败'
  } finally {
    importLoading.value = false
  }
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
          <path d="M12 20h9"></path>
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
        </svg>
      </div>
      <div class="page-header__text">
        <h1>商品文案生成</h1>
        <p>输入商品信息，AI 一键生成标题、卖点、详情页文案和广告语</p>
      </div>
    </div>

    <div class="steps">
      <div
        v-for="(s, idx) in ['选择商品', '设置参数', '生成文案']"
        :key="idx"
        :class="['step', { active: idx + 1 <= currentStep, current: idx + 1 === currentStep }]"
      >
        <span class="step__num">{{ idx + 1 }}</span>
        <span class="step__label">{{ s }}</span>
      </div>
    </div>

    <div class="content-grid">
      <form class="input-form" @submit.prevent="handleSubmit">
        <div class="mode-tabs">
          <button
            type="button"
            :class="['mode-tab', { active: inputMode === 'db' }]"
            @click="inputMode = 'db'"
          >
            从数据库选择
          </button>
          <button
            type="button"
            :class="['mode-tab', { active: inputMode === 'manual' }]"
            @click="inputMode = 'manual'"
          >
            手动输入商品
          </button>
        </div>

        <div v-if="inputMode === 'db'" class="mode-panel">
          <label class="field-label">选择商品</label>
          <div class="select-row">
            <select v-model="selectedCategory" class="select-item" @change="onCategoryChange">
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
                <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }}</option>
              </template>
            </select>
          </div>
        </div>

        <template v-if="inputMode === 'manual'">
          <div class="form-group">
            <label class="field-label">商品名称 <span class="required">*</span></label>
            <input v-model="form.product_name" type="text" placeholder="例如：云感护腰办公椅" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="field-label">商品类目</label>
              <input v-model="form.category" type="text" placeholder="例如：办公家具" />
            </div>
            <div class="form-group">
              <label class="field-label">参考价格（元）</label>
              <input v-model="form.price" type="number" step="0.01" placeholder="0.00" />
            </div>
          </div>
        </template>

        <div class="form-group">
          <label class="field-label">目标人群</label>
          <input v-model="form.audience" type="text" placeholder="例如：久坐办公人群" />
        </div>

        <div class="form-group">
          <label class="field-label">商品卖点（每行一个）</label>
          <textarea
            v-model="form.selling_points_text"
            rows="4"
            placeholder="护腰支撑&#10;透气坐垫&#10;稳固耐用"
          ></textarea>
        </div>

        <div class="form-group">
          <label class="field-label">文案风格</label>
          <div class="style-options">
            <label
              v-for="opt in styleOptions"
              :key="opt.value"
              class="style-option"
              :class="{ active: form.style === opt.value }"
            >
              <input type="radio" v-model="form.style" :value="opt.value" />
              <span class="style-icon">{{ opt.icon }}</span>
              <span class="style-name">{{ opt.value }}</span>
              <span class="style-desc">{{ opt.desc }}</span>
            </label>
          </div>
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          <span class="btn-icon">✨</span>
          {{ loading ? '生成中...' : '生成文案' }}
        </button>
      </form>

      <div class="result-panel">
        <div v-if="error" class="error-message">{{ error }}</div>

        <div v-if="result" class="result-content">
          <div class="result-meta">
            <div class="result-tags">
              <span class="meta-tag">{{ result.style }}</span>
              <span class="meta-product">{{ result.product_name }}</span>
            </div>
            <div class="result-actions">
              <button class="action-btn" @click="copyResult">{{ copied ? '已复制' : '复制' }}</button>
              <button class="action-btn" @click="downloadTxt">下载 txt</button>
              <button class="action-btn action-btn--primary" @click="openImportModal">导入商品管理</button>
            </div>
          </div>

          <div class="result-card">
            <div class="section-label">
              <span class="section-dot"></span>
              <h3>推荐标题</h3>
            </div>
            <div v-if="editingResult && editableResult" class="edit-field">
              <input v-model="editableResult.title" type="text" />
            </div>
            <p v-else class="highlight-text">{{ result.title }}</p>
          </div>

          <div class="result-card">
            <div class="section-label">
              <span class="section-dot"></span>
              <h3>商品卖点</h3>
            </div>
            <ul v-if="!editingResult" class="selling-points">
              <li v-for="point in result.selling_points" :key="point">{{ point }}</li>
            </ul>
            <div v-else-if="editableResult" class="edit-field">
              <textarea v-model="editableSellingPointsText" rows="4" placeholder="每行一个卖点"></textarea>
            </div>
          </div>

          <div class="result-card">
            <div class="section-label">
              <span class="section-dot"></span>
              <h3>详情页文案</h3>
            </div>
            <div v-if="editingResult && editableResult" class="edit-field">
              <textarea v-model="editableResult.detail_copy" rows="6"></textarea>
            </div>
            <p v-else class="detail-copy">{{ result.detail_copy }}</p>
          </div>

          <div class="result-card result-card--slogan">
            <div class="section-label">
              <span class="section-dot"></span>
              <h3>广告语</h3>
            </div>
            <div v-if="editingResult && editableResult" class="edit-field">
              <input v-model="editableResult.ad_slogan" type="text" />
            </div>
            <blockquote v-else>{{ result.ad_slogan }}</blockquote>
          </div>

          <div class="edit-actions">
            <template v-if="!editingResult">
              <button class="btn-ghost" @click="enterEditMode">✎ 编辑文案</button>
            </template>
            <template v-else>
              <button class="btn-ghost" @click="cancelEdit">取消</button>
              <button class="btn-primary btn-primary--sm" @click="saveEdit">保存修改</button>
            </template>
          </div>
        </div>

        <div v-else-if="loading" class="skeleton-wrap">
          <div class="skeleton skeleton--title"></div>
          <div v-for="i in 3" :key="i" class="skeleton skeleton--line"></div>
          <div class="skeleton skeleton--slogan"></div>
        </div>

        <div v-else class="empty-state">
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
          </div>
          <p>填写商品信息后点击"生成文案"查看结果</p>
          <span class="empty-hint">支持从数据库选择或手动输入商品信息</span>
        </div>
      </div>
    </div>

    <transition name="modal">
      <div v-if="importModalVisible" class="modal-overlay" @click.self="closeImportModal">
        <div class="modal modal--sm">
          <div class="modal__header">
            <h3>导入到商品管理</h3>
            <button class="modal__close" @click="closeImportModal">×</button>
          </div>
          <div class="modal__body">
            <p class="modal__desc">将当前生成的文案一键创建为商品，您可以在商品管理页面继续编辑。</p>
            <div class="import-preview">
              <div class="import-row">
                <span class="import-label">商品名称</span>
                <span class="import-value">{{ result?.product_name || form.product_name }}</span>
              </div>
              <div class="import-row">
                <span class="import-label">类目</span>
                <span class="import-value">{{ form.category || '综合' }}</span>
              </div>
              <div class="import-row">
                <span class="import-label">价格</span>
                <span class="import-value">{{ form.price ? `¥${Number(form.price).toFixed(2)}` : '未填写' }}</span>
              </div>
            </div>
            <label class="publish-toggle">
              <input v-model="importPublish" type="checkbox" />
              <span class="toggle-track" :class="{ 'toggle-track--on': importPublish }"></span>
              <span>{{ importPublish ? '导入后立即上架' : '导入后暂不上架' }}</span>
            </label>
            <div v-if="importError" class="modal__error">{{ importError }}</div>
          </div>
          <div class="modal__footer">
            <button class="btn-ghost" @click="closeImportModal">取消</button>
            <button class="btn-primary btn-primary--sm" :disabled="importLoading" @click="confirmImport">
              {{ importLoading ? '导入中...' : '确认导入' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
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

.input-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
  min-width: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 26px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.mode-tabs {
  display: flex;
  gap: 6px;
  padding: 5px;
  background: rgba(0, 0, 0, 0.035);
  border-radius: 14px;
}

.mode-tab {
  flex: 1;
  padding: 11px 16px;
  border: none;
  border-radius: 11px;
  background: transparent;
  color: var(--muted);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-tab.active {
  background: #fff;
  color: var(--brand);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.07);
}

.mode-panel {
  animation: fade-in 0.3s ease;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 100%;
  overflow: hidden;
  min-width: 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.field-label {
  font-weight: 700;
  font-size: 14px;
  color: var(--ink);
}

.required {
  color: var(--brand);
}

.form-group input,
.form-group select,
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
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(217, 95, 45, 0.1);
}

.form-group select {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.form-group textarea {
  resize: vertical;
  min-height: 96px;
  line-height: 1.6;
}

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
  gap: 2px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.style-option:hover {
  border-color: var(--brand);
  transform: translateY(-1px);
}

.style-option.active {
  border-color: var(--brand);
  background: linear-gradient(135deg, rgba(217, 95, 45, 0.08), rgba(217, 95, 45, 0.03));
  box-shadow: 0 0 0 1px var(--brand) inset;
}

.style-option input {
  display: none;
}

.style-icon {
  position: absolute;
  top: 10px;
  right: 12px;
  font-size: 16px;
  color: var(--brand);
  opacity: 0.35;
}

.style-option.active .style-icon {
  opacity: 1;
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
  background: linear-gradient(135deg, var(--brand), var(--brand-dark, #8a3a1f));
  color: white;
  border: none;
  border-radius: 13px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
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

.btn-primary--sm {
  padding: 10px 18px;
  font-size: 14px;
}

.btn-ghost {
  padding: 10px 18px;
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--line);
  border-radius: 11px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-ghost:hover {
  border-color: var(--brand);
  color: var(--brand);
}

.btn-icon {
  font-size: 18px;
  line-height: 1;
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

.meta-tag {
  display: inline-block;
  padding: 5px 12px;
  background: var(--brand);
  color: white;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}

.meta-product {
  font-size: 15px;
  color: var(--muted);
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

.action-btn--primary {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}

.action-btn--primary:hover {
  background: var(--brand-dark);
  color: #fff;
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

.result-card--slogan {
  background: linear-gradient(135deg, #211a14, #5d301e);
  color: #ffe0bd;
  border: none;
}

.result-card--slogan .section-label h3 {
  color: #ffe0bd;
}

.result-card--slogan .section-dot {
  background: #ffb380;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.section-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--brand);
}

.result-card h3 {
  font-size: 15px;
  margin: 0;
  color: var(--brand-dark);
}

.highlight-text {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.5;
  margin: 0;
  color: var(--ink);
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
  padding: 12px 16px;
  background: rgba(217, 95, 45, 0.06);
  border-radius: 11px;
  border-left: 3px solid var(--brand);
  font-weight: 500;
}

.detail-copy {
  margin: 0;
  line-height: 1.8;
  color: var(--ink);
  white-space: pre-line;
}

blockquote {
  margin: 0;
  padding: 0;
  font-size: 18px;
  font-style: italic;
  line-height: 1.5;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 4px;
}

.edit-field input,
.edit-field textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--brand);
  border-radius: 11px;
  font-size: 15px;
  font-family: inherit;
  background: #fff;
  box-sizing: border-box;
}

.edit-field textarea {
  resize: vertical;
  line-height: 1.6;
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

.empty-hint {
  font-size: 13px;
  margin-top: 6px;
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

.skeleton--title {
  height: 32px;
  width: 80%;
}

.skeleton--line {
  height: 72px;
}

.skeleton--slogan {
  height: 96px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.75; }
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
  backdrop-filter: blur(3px);
}

.modal {
  background: var(--panel);
  border-radius: 20px;
  width: min(440px, 100%);
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
}

.modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--line);
}

.modal__header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--ink);
}

.modal__close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.05);
  color: var(--muted);
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal__body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.modal__desc {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
}

.import-preview {
  background: rgba(0, 0, 0, 0.03);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.import-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.import-label {
  color: var(--muted);
}

.import-value {
  color: var(--ink);
  font-weight: 600;
  max-width: 60%;
  text-align: right;
}

.publish-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  font-weight: 600;
  color: var(--ink);
}

.publish-toggle input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-track {
  width: 48px;
  height: 26px;
  border-radius: 999px;
  background: var(--line);
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}

.toggle-track::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.toggle-track--on {
  background: var(--brand);
}

.toggle-track--on::after {
  transform: translateX(22px);
}

.modal__error {
  background: #fee;
  color: #c33;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
}

.modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid var(--line);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
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

  .style-options,
  .form-row {
    grid-template-columns: 1fr;
  }

  .select-row {
    flex-direction: column;
  }

  .result-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
