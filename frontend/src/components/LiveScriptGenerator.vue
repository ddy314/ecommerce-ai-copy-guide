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
  duration_minutes: 5,
  tone: '热情自然',
  highlights_text: '护腰支撑\n透气坐垫\n稳固耐用',
})

function getHighlightsList(): string[] {
  return form.value.highlights_text.split('\n').filter(s => s.trim())
}

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
  if (!form.value.product_name) {
    error.value = '请先从数据库选择商品'
    return
  }
  loading.value = true
  error.value = null
  try {
    result.value = await api.generateLiveScript({
      product_name: form.value.product_name,
      duration_minutes: form.value.duration_minutes,
      tone: form.value.tone,
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '生成失败'
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载分类列表
onMounted(() => {
  loadCategories()
})
</script>

<template>
  <div class="feature-page">
    <div class="page-header">
      <h1>直播脚本生成</h1>
      <p>根据商品信息和直播时长生成分段脚本和互动问题</p>
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

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '生成中...' : '生成脚本' }}
        </button>
      </form>

      <div class="result-panel">
        <div v-if="error" class="error-message">{{ error }}</div>

        <div v-if="result" class="result-content">
          <div class="result-section">
            <h3>脚本概览</h3>
            <p class="overview">
              商品：<strong>{{ result.product_name }}</strong> | 
              时长：<strong>{{ result.duration_minutes }}分钟</strong> | 
              语气：<strong>{{ result.tone }}</strong>
            </p>
          </div>

          <div class="result-section">
            <h3>分段脚本</h3>
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
              </div>
            </div>
          </div>

          <div v-if="result.interaction_questions.length > 0" class="result-section">
            <h3>互动问题</h3>
            <ul class="questions">
              <li v-for="(question, index) in result.interaction_questions" :key="index">
                {{ question }}
              </li>
            </ul>
          </div>
        </div>

        <div v-else-if="!loading" class="empty-state">
          <p>填写商品信息后点击"生成脚本"查看结果</p>
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
}

.form-group textarea {
  resize: none;
  min-height: 100px;
  word-break: break-all;
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

.overview {
  margin: 0;
  line-height: 1.6;
}

.overview strong {
  color: var(--brand);
}

.segments {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.segment-card {
  padding: 16px;
  background: rgba(217, 95, 45, 0.05);
  border: 1px solid rgba(217, 95, 45, 0.2);
  border-radius: 12px;
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
}

.segment-duration {
  font-size: 13px;
  color: var(--muted);
}

.segment-script {
  margin: 0;
  line-height: 1.6;
  color: var(--ink);
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
  border-radius: 8px;
  border-left: 3px solid var(--green);
  line-height: 1.5;
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

  .product-select-group .select-row {
    flex-direction: column;
  }
}
</style>
