<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type LiveScriptResponse } from '../api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<LiveScriptResponse | null>(null)

// ---------- 商品选择相关 ----------
interface Product {
  id: number
  name: string
  category: string
  price: number | null
  brand: string | null
}

const categories = ref<string[]>([])
const products = ref<Product[]>([])
const selectedCategory = ref('')
const selectedProductId = ref<number | null>(null)
const productLoading = ref(false)

const form = ref({
  product_name: '云感护腰办公椅',
  category: '',
  audience: '久坐办公人群',
  product_specs: '',
  duration_minutes: 5,
  tone: '热情自然',
  highlights_text: '护腰支撑\n透气坐垫\n稳固耐用',
})

// 加载商品分类列表
async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/api/products?page=1&page_size=1`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    categories.value = data.categories || []
  } catch (e) {
    console.error('加载分类失败:', e)
  }
}

// 根据分类加载商品列表
async function loadProducts() {
  if (!selectedCategory.value) {
    products.value = []
    return
  }
  productLoading.value = true
  try {
    const response = await fetch(
      `${API_BASE}/api/products?category=${encodeURIComponent(selectedCategory.value)}&page=1&page_size=100`
    )
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    products.value = data.products || []
  } catch (e) {
    console.error('加载商品失败:', e)
    products.value = []
  } finally {
    productLoading.value = false
  }
}

// 切换分类时重置商品选择并重新加载
function onCategoryChange() {
  selectedProductId.value = null
  loadProducts()
}

// 选择商品后自动填充表单字段
function onProductChange() {
  const product = products.value.find(p => p.id === selectedProductId.value)
  if (product) {
    form.value.product_name = product.name
    form.value.category = product.category
  }
}

async function handleSubmit() {
  if (!form.value.product_name.trim()) {
    error.value = '请输入商品名称'
    return
  }
  loading.value = true
  error.value = null
  try {
    result.value = await api.generateLiveScript({
      product_name: form.value.product_name,
      product_specs: form.value.product_specs,
      audience: form.value.audience,
      duration_minutes: form.value.duration_minutes,
      tone: form.value.tone,
      highlights: form.value.highlights_text.split('\n').filter(s => s.trim()),
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成失败'
  } finally {
    loading.value = false
  }
}

/** 拼接脚本为 txt 文本 */
function buildScriptText(r: LiveScriptResponse): string {
  const lines: string[] = []
  lines.push(`直播脚本：${r.product_name}`)
  lines.push(`时长：${r.duration_minutes} 分钟 | 语气：${r.tone}`)
  lines.push('')
  if (r.segments?.length) {
    lines.push('【分段脚本】')
    r.segments.forEach((segment, index) => {
      lines.push(`${index + 1}. ${segment.name}（${segment.minutes} 分钟）`)
      lines.push(segment.script)
      if (segment.action_hint) {
        lines.push(`动作提示：${segment.action_hint}`)
      }
      lines.push('')
    })
  }
  if (r.interaction_questions?.length) {
    lines.push('【互动问题】')
    r.interaction_questions.forEach((q, index) => lines.push(`${index + 1}. ${q}`))
    lines.push('')
  }
  if (r.explanation_flow?.length) {
    lines.push('【讲解流程】')
    r.explanation_flow.forEach((step) => {
      lines.push(`步骤 ${step.step}：${step.title}`)
      lines.push(step.script)
      if (step.key_points?.length) {
        lines.push('要点：' + step.key_points.join('；'))
      }
      lines.push('')
    })
  }
  if (r.conversion_scripts?.length) {
    lines.push('【转化话术】')
    r.conversion_scripts.forEach((s, index) => lines.push(`${index + 1}. ${s}`))
    lines.push('')
  }
  return lines.join('\n')
}

/** 下载 txt */
function downloadTxt() {
  if (!result.value) return
  const text = buildScriptText(result.value)
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `直播脚本_${result.value.product_name}_${new Date().toISOString().slice(0, 10)}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

// 组件挂载时加载分类列表
onMounted(() => {
  loadCategories()
})
</script>

<template>
  <div class="feature-page">
    <div class="page-header">
      <div class="page-header__icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="23 7 16 12 23 17 23 7"></polygon>
          <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
        </svg>
      </div>
      <div>
        <h1>直播脚本生成</h1>
        <p>根据商品信息、卖点和直播时长生成分段脚本与互动问题</p>
      </div>
    </div>

    <div class="content-grid">
      <form class="input-form" @submit.prevent="handleSubmit">
        <div class="form-group product-select-group">
          <label>从数据库选择商品</label>
          <div class="select-row">
            <select
              v-model="selectedCategory"
              class="select-item"
              @change="onCategoryChange"
            >
              <option value="">选择分类</option>
              <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
            <select
              v-model="selectedProductId"
              class="select-item"
              :disabled="!selectedCategory || productLoading"
              @change="onProductChange"
            >
              <option :value="null">选择商品</option>
              <option v-for="product in products" :key="product.id" :value="product.id">
                {{ product.name }}
              </option>
            </select>
          </div>
          <p v-if="productLoading" class="select-hint">商品加载中...</p>
        </div>

        <div class="form-group">
          <label>商品名称 <span class="required">*</span></label>
          <input v-model="form.product_name" type="text" placeholder="例如：云感护腰办公椅" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>直播时长（分钟）</label>
            <input
              v-model.number="form.duration_minutes"
              type="number"
              min="1"
              max="120"
              placeholder="5"
            />
          </div>

          <div class="form-group">
            <label>直播语气</label>
            <select v-model="form.tone">
              <option value="热情自然">热情自然</option>
              <option value="专业严谨">专业严谨</option>
              <option value="轻松幽默">轻松幽默</option>
              <option value="亲切温馨">亲切温馨</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>目标观众</label>
          <input v-model="form.audience" type="text" placeholder="例如：久坐办公人群" />
        </div>

        <div class="form-group">
          <label>商品规格 / 卖点</label>
          <textarea v-model="form.product_specs" rows="3" placeholder="可填写核心参数或卖点描述"></textarea>
        </div>

        <div class="form-group">
          <label>直播亮点（每行一个）</label>
          <textarea
            v-model="form.highlights_text"
            rows="3"
            placeholder="护腰支撑&#10;透气坐垫&#10;稳固耐用"
          ></textarea>
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          <span class="btn-icon">🎬</span>
          {{ loading ? '生成中...' : '生成脚本' }}
        </button>
      </form>

      <div class="result-panel">
        <div v-if="error" class="error-message">{{ error }}</div>

        <div v-if="result" class="result-content">
          <div class="result-meta">
            <div class="result-tags">
              <span class="meta-product">{{ result.product_name }}</span>
              <span class="meta-tag">{{ result.duration_minutes }} 分钟</span>
              <span class="meta-tag meta-tag--secondary">{{ result.tone }}</span>
            </div>
            <div class="result-actions">
              <button class="action-btn" @click="downloadTxt">下载 txt</button>
            </div>
          </div>

          <div class="result-section">
            <div class="section-label">
              <span class="section-dot"></span>
              <h3>脚本概览</h3>
            </div>
            <div class="overview-cards">
              <div class="overview-card">
                <span class="overview-label">商品</span>
                <span class="overview-value">{{ result.product_name }}</span>
              </div>
              <div class="overview-card">
                <span class="overview-label">时长</span>
                <span class="overview-value">{{ result.duration_minutes }} 分钟</span>
              </div>
              <div class="overview-card">
                <span class="overview-label">语气</span>
                <span class="overview-value">{{ result.tone }}</span>
              </div>
            </div>
          </div>

          <div class="result-section">
            <div class="section-label">
              <span class="section-dot"></span>
              <h3>分段脚本</h3>
            </div>
            <div class="segments">
              <div v-for="(segment, index) in result.segments" :key="index" class="segment-card">
                <div class="segment-header">
                  <span class="segment-number">{{ index + 1 }}</span>
                  <div class="segment-info">
                    <h4>{{ segment.name }}</h4>
                    <span class="segment-duration">{{ segment.minutes }} 分钟</span>
                  </div>
                </div>
                <p class="segment-script">{{ segment.script }}</p>
                <p v-if="segment.action_hint" class="segment-hint">
                  <strong>动作提示：</strong>{{ segment.action_hint }}
                </p>
              </div>
            </div>
          </div>

          <div v-if="result.interaction_questions.length > 0" class="result-section">
            <div class="section-label">
              <span class="section-dot section-dot--accent"></span>
              <h3>互动问题</h3>
            </div>
            <ul class="questions">
              <li v-for="(question, index) in result.interaction_questions" :key="index">
                {{ question }}
              </li>
            </ul>
          </div>

          <div v-if="result.explanation_flow && result.explanation_flow.length > 0" class="result-section">
            <div class="section-label">
              <span class="section-dot section-dot--accent"></span>
              <h3>讲解流程</h3>
            </div>
            <div class="flow-steps">
              <div v-for="step in result.explanation_flow" :key="step.step" class="flow-step">
                <div class="flow-step__header">
                  <span class="flow-step__num">{{ step.step }}</span>
                  <h4>{{ step.title }}</h4>
                </div>
                <p class="flow-step__script">{{ step.script }}</p>
                <div v-if="step.key_points && step.key_points.length > 0" class="flow-step__points">
                  <span v-for="(point, idx) in step.key_points" :key="idx" class="flow-point">{{ point }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="result.conversion_scripts && result.conversion_scripts.length > 0" class="result-section">
            <div class="section-label">
              <span class="section-dot section-dot--accent"></span>
              <h3>转化话术</h3>
            </div>
            <ul class="conversion-list">
              <li v-for="(script, index) in result.conversion_scripts" :key="index">
                {{ script }}
              </li>
            </ul>
          </div>
        </div>

        <div v-else-if="!loading" class="empty-state">
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <polygon points="23 7 16 12 23 17 23 7"></polygon>
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
            </svg>
          </div>
          <p>填写商品信息后点击“生成脚本”查看结果</p>
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
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
}

.page-header__icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--brand), var(--brand-dark, #8a3a1f));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(217, 95, 45, 0.25);
}

.page-header__icon svg {
  width: 28px;
  height: 28px;
}

.page-header h1 {
  font-size: 32px;
  margin: 0 0 6px 0;
  color: var(--ink);
}

.page-header p {
  color: var(--muted);
  margin: 0;
  font-size: 15px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
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
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
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
.form-group select,
.form-group textarea {
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
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
  min-height: 90px;
  line-height: 1.6;
  word-break: break-all;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

/* 商品选择下拉区 */
.product-select-group .select-row {
  display: flex;
  gap: 12px;
  min-width: 0;
  max-width: 100%;
}

.product-select-group .select-item {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.product-select-group .select-item:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.product-select-group .select-hint {
  margin: 4px 0 0 0;
  font-size: 13px;
  color: var(--muted);
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-primary:hover:not(:disabled) {
  background: var(--brand-dark);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(217, 95, 45, 0.25);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 18px;
  line-height: 1;
}

.result-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 24px;
  min-height: 520px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 12px 16px;
  border-radius: 10px;
  margin-bottom: 16px;
  font-size: 14px;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: fade-up 0.4s ease;
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

.meta-tag--secondary {
  background: rgba(217, 95, 45, 0.12);
  color: var(--brand-dark);
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

.result-section {
  padding: 18px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.04);
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

.section-dot--accent {
  background: var(--green, #1f8a5b);
}

.result-section h3 {
  font-size: 15px;
  margin: 0;
  color: var(--brand-dark);
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.overview-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px;
  border-radius: 12px;
  background: rgba(217, 95, 45, 0.06);
}

.overview-label {
  font-size: 12px;
  color: var(--muted);
}

.overview-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.4;
}

.segments {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.segment-card {
  padding: 16px;
  background: rgba(217, 95, 45, 0.04);
  border: 1px solid rgba(217, 95, 45, 0.15);
  border-radius: 14px;
}

.segment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.segment-number {
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 50%;
  background: var(--brand);
  color: white;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}

.segment-info {
  flex: 1;
}

.segment-info h4 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: var(--brand-dark);
}

.segment-duration {
  font-size: 13px;
  color: var(--muted);
}

.segment-script {
  margin: 0 0 10px 0;
  line-height: 1.7;
  color: var(--ink);
  white-space: pre-line;
}

.segment-hint {
  margin: 0;
  padding: 10px 12px;
  background: rgba(31, 138, 91, 0.08);
  border-radius: 8px;
  font-size: 13px;
  color: var(--ink);
  line-height: 1.5;
}

.segment-hint strong {
  color: var(--green, #1f8a5b);
}

.questions {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.questions li {
  padding: 12px 16px;
  background: rgba(31, 138, 91, 0.08);
  border-radius: 10px;
  border-left: 3px solid var(--green, #1f8a5b);
  line-height: 1.5;
}

.flow-steps {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.flow-step {
  padding: 14px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 12px;
}

.flow-step__header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.flow-step__num {
  display: inline-grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  background: var(--brand);
  color: white;
  font-weight: 700;
  font-size: 13px;
}

.flow-step__header h4 {
  margin: 0;
  font-size: 15px;
  color: var(--brand-dark);
}

.flow-step__script {
  margin: 0 0 10px 0;
  line-height: 1.7;
  color: var(--ink);
}

.flow-step__points {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.flow-point {
  padding: 4px 10px;
  background: rgba(217, 95, 45, 0.08);
  border-radius: 20px;
  font-size: 12px;
  color: var(--brand-dark);
}

.conversion-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conversion-list li {
  padding: 12px 16px;
  background: rgba(217, 95, 45, 0.08);
  border-radius: 10px;
  border-left: 3px solid var(--brand);
  line-height: 1.5;
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
  width: 72px;
  height: 72px;
  color: var(--line);
  margin-bottom: 16px;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .form-row,
  .overview-cards {
    grid-template-columns: 1fr;
  }

  .product-select-group .select-row {
    flex-direction: column;
  }

  .result-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
