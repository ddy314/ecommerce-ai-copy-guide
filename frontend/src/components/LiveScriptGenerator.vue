<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type LiveScriptResponse } from '../api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<LiveScriptResponse | null>(null)

// 脚本类型：live / short
const scriptType = ref<'live' | 'short'>('live')

// ---------- 商品选择相关 ----------
interface Product {
  id: number
  name: string
  category: string
  price: number | null
  brand: string | null
}

const categories = ref<string[]>([])
const categoryCounts = ref<Record<string, number>>({})
const products = ref<Product[]>([])
const selectedCategory = ref('')
const selectedProductId = ref<number | null>(null)
const productLoading = ref(false)

const form = ref({
  product_name: '云感护腰办公椅',
  category: '',
  audience: '久坐办公人群',
  product_specs: '',
  duration: 5,
  tone: '热情自然',
  highlights_text: '护腰支撑\n透气坐垫\n稳固耐用',
})

const toneOptions = [
  { value: '热情自然', desc: '亲切有活力，适合带货', icon: '🔥' },
  { value: '专业严谨', desc: '突出参数与可信度', icon: '📐' },
  { value: '轻松幽默', desc: '轻松有趣，易传播', icon: '😄' },
  { value: '亲切温馨', desc: '像朋友聊天，拉近距离', icon: '💬' },
]

// 加载商品分类列表
async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/api/products?page=1&page_size=1`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    categories.value = data.categories || []
    categoryCounts.value = data.category_counts || {}
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

const durationLabel = computed(() => (scriptType.value === 'live' ? '直播时长（分钟）' : '视频时长（秒）'))
const durationMax = computed(() => (scriptType.value === 'live' ? 120 : 180))

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
      duration_minutes: form.value.duration,
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
  const typeName = scriptType.value === 'live' ? '直播脚本' : '短视频脚本'
  const unit = scriptType.value === 'live' ? '分钟' : '秒'
  lines.push(`${typeName}：${r.product_name}`)
  lines.push(`时长：${r.duration_minutes} ${unit} | 语气：${r.tone}`)
  lines.push('')
  if (r.segments?.length) {
    lines.push('【分段脚本】')
    r.segments.forEach((segment, index) => {
      lines.push(`${index + 1}. ${segment.name}（${segment.minutes} ${unit}）`)
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
  const typeName = scriptType.value === 'live' ? '直播脚本' : '短视频脚本'
  link.href = url
  link.download = `${typeName}_${result.value.product_name}_${new Date().toISOString().slice(0, 10)}.txt`
  link.click()
  URL.revokeObjectURL(url)
}

const currentStep = computed(() => (result.value ? 3 : 2))

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
      <div class="page-header__text">
        <h1>直播 / 短视频脚本生成</h1>
        <p>根据商品信息、卖点和时长生成直播或短视频脚本与互动问题</p>
      </div>
    </div>

    <div class="steps">
      <div
        v-for="(s, idx) in ['选择商品', '设置参数', '生成脚本']"
        :key="idx"
        :class="['step', { active: idx + 1 <= currentStep, current: idx + 1 === currentStep }]"
      >
        <span class="step__num">{{ idx + 1 }}</span>
        <span class="step__label">{{ s }}</span>
      </div>
    </div>

    <div class="content-grid">
      <form class="input-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label class="field-label">脚本类型</label>
          <div class="type-tabs">
            <button
              type="button"
              :class="['type-tab', { active: scriptType === 'live' }]"
              @click="scriptType = 'live'"
            >
              <span class="type-icon">📺</span>
              <span>直播脚本</span>
            </button>
            <button
              type="button"
              :class="['type-tab', { active: scriptType === 'short' }]"
              @click="scriptType = 'short'"
            >
              <span class="type-icon">🎬</span>
              <span>短视频脚本</span>
            </button>
          </div>
        </div>

        <div class="card db-card">
          <div class="card__title">
            <span class="card__dot"></span>
            从数据库选择商品
          </div>
          <div class="select-row">
            <select
              v-model="selectedCategory"
              class="select-item"
              @change="onCategoryChange"
            >
              <option value="">选择分类</option>
              <option v-for="cat in categories" :key="cat" :value="cat">
                {{ cat }}<template v-if="categoryCounts[cat]"> ({{ categoryCounts[cat] }})</template>
              </option>
            </select>
            <select
              v-model="selectedProductId"
              class="select-item"
              :disabled="!selectedCategory || productLoading"
              @change="onProductChange"
            >
              <option :value="null">选择商品</option>
              <option v-if="productLoading" :value="null" disabled>加载中...</option>
              <template v-else>
                <option v-for="product in products" :key="product.id" :value="product.id">
                  {{ product.name }}
                </option>
              </template>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label class="field-label">商品名称 <span class="required">*</span></label>
          <input v-model="form.product_name" type="text" placeholder="例如：云感护腰办公椅" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="field-label">{{ durationLabel }}</label>
            <input
              v-model.number="form.duration"
              type="number"
              min="1"
              :max="durationMax"
              placeholder="5"
            />
          </div>

          <div class="form-group">
            <label class="field-label">目标观众</label>
            <input v-model="form.audience" type="text" placeholder="例如：久坐办公人群" />
          </div>
        </div>

        <div class="form-group">
          <label class="field-label">脚本语气</label>
          <div class="tone-options">
            <label
              v-for="opt in toneOptions"
              :key="opt.value"
              class="tone-option"
              :class="{ active: form.tone === opt.value }"
            >
              <input type="radio" v-model="form.tone" :value="opt.value" />
              <span class="tone-icon">{{ opt.icon }}</span>
              <span class="tone-name">{{ opt.value }}</span>
              <span class="tone-desc">{{ opt.desc }}</span>
            </label>
          </div>
        </div>

        <div class="form-group">
          <label class="field-label">商品规格 / 卖点</label>
          <textarea v-model="form.product_specs" rows="3" placeholder="可填写核心参数或卖点描述"></textarea>
        </div>

        <div class="form-group">
          <label class="field-label">脚本亮点（每行一个）</label>
          <textarea
            v-model="form.highlights_text"
            rows="3"
            placeholder="护腰支撑&#10;透气坐垫&#10;稳固耐用"
          ></textarea>
        </div>

        <button type="submit" class="btn-primary" :disabled="loading">
          <span class="btn-icon">✨</span>
          {{ loading ? '生成中...' : '生成脚本' }}
        </button>
      </form>

      <div class="result-panel">
        <div v-if="error" class="error-message">{{ error }}</div>

        <div v-if="result" class="result-content">
          <div class="result-meta">
            <div class="result-tags">
              <span class="meta-tag">{{ scriptType === 'live' ? '直播' : '短视频' }}</span>
              <span class="meta-product">{{ result.product_name }}</span>
              <span class="meta-tag meta-tag--secondary">
                {{ result.duration_minutes }} {{ scriptType === 'live' ? '分钟' : '秒' }}
              </span>
              <span class="meta-tag meta-tag--secondary">{{ result.tone }}</span>
            </div>
            <div class="result-actions">
              <button class="action-btn" @click="downloadTxt">下载 txt</button>
            </div>
          </div>

          <div class="result-card">
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
                <span class="overview-value">{{ result.duration_minutes }} {{ scriptType === 'live' ? '分钟' : '秒' }}</span>
              </div>
              <div class="overview-card">
                <span class="overview-label">语气</span>
                <span class="overview-value">{{ result.tone }}</span>
              </div>
            </div>
          </div>

          <div class="result-card">
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
                    <span class="segment-duration">{{ segment.minutes }} {{ scriptType === 'live' ? '分钟' : '秒' }}</span>
                  </div>
                </div>
                <p class="segment-script">{{ segment.script }}</p>
                <p v-if="segment.action_hint" class="segment-hint">
                  <strong>动作提示：</strong>{{ segment.action_hint }}
                </p>
              </div>
            </div>
          </div>

          <div v-if="result.interaction_questions.length > 0" class="result-card">
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

          <div v-if="result.explanation_flow && result.explanation_flow.length > 0" class="result-card">
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

          <div v-if="result.conversion_scripts && result.conversion_scripts.length > 0" class="result-card">
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

        <div v-else-if="loading" class="skeleton-wrap">
          <div class="skeleton skeleton--title"></div>
          <div v-for="i in 3" :key="i" class="skeleton skeleton--line"></div>
          <div class="skeleton skeleton--slogan"></div>
        </div>

        <div v-else class="empty-state">
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <polygon points="23 7 16 12 23 17 23 7"></polygon>
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
            </svg>
          </div>
          <p>填写商品信息后点击“生成脚本”查看结果</p>
          <span class="empty-hint">支持直播脚本与短视频脚本两种模式</span>
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

.type-tabs {
  display: flex;
  gap: 6px;
  padding: 5px;
  background: rgba(0, 0, 0, 0.035);
  border-radius: 14px;
}

.type-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
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

.type-tab.active {
  background: #fff;
  color: var(--brand);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.07);
}

.type-icon {
  font-size: 16px;
  line-height: 1;
}

.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}

.db-card {
  padding: 18px;
  background: rgba(217, 95, 45, 0.03);
}

.card__title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 14px;
}

.card__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--brand);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 100%;
  overflow: hidden;
  min-width: 0;
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

.select-row .select-item:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tone-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.tone-option {
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

.tone-option:hover {
  border-color: var(--brand);
  transform: translateY(-1px);
}

.tone-option.active {
  border-color: var(--brand);
  background: linear-gradient(135deg, rgba(217, 95, 45, 0.08), rgba(217, 95, 45, 0.03));
  box-shadow: 0 0 0 1px var(--brand) inset;
}

.tone-option input {
  display: none;
}

.tone-icon {
  position: absolute;
  top: 10px;
  right: 12px;
  font-size: 16px;
  opacity: 0.35;
}

.tone-option.active .tone-icon {
  opacity: 1;
}

.tone-name {
  font-weight: 700;
  color: var(--brand-dark);
}

.tone-desc {
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

.result-card h3 {
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

  .form-row,
  .overview-cards,
  .tone-options {
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
