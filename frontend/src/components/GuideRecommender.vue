<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  api,
  type GuideRecommendationResponse,
  type GuideQAResponse,
  type CrossRecommendResponse,
} from '../api'

type TabKey = 'recommend' | 'qa' | 'cross'

const activeTab = ref<TabKey>('recommend')

const tabs: Array<{ key: TabKey; label: string }> = [
  { key: 'recommend', label: '推荐' },
  { key: 'qa', label: '智能问答' },
  { key: 'cross', label: '跨商品推荐' },
]

/* ---------------- 推荐 Tab ---------------- */
const loadingRecommend = ref(false)
const recommendError = ref<string | null>(null)
const recommendResult = ref<GuideRecommendationResponse | null>(null)

const recommendForm = ref({
  user_need: '预算 300 元以内，送给经常加班的朋友',
  budget: '300元以内',
  products_text: '高性价比基础款\n品质升级款\n礼赠套装款',
})

function getProductsList(): string[] {
  return recommendForm.value.products_text.split('\n').filter(s => s.trim())
}

async function handleRecommend() {
  loadingRecommend.value = true
  recommendError.value = null
  try {
    recommendResult.value = await api.recommendGuide({
      user_need: recommendForm.value.user_need,
      budget: recommendForm.value.budget,
      products: getProductsList(),
    })
  } catch (e) {
    recommendError.value = e instanceof Error ? e.message : '推荐失败'
  } finally {
    loadingRecommend.value = false
  }
}

/* ---------------- 智能问答 Tab ---------------- */
const loadingQA = ref(false)
const qaError = ref<string | null>(null)
const qaResult = ref<GuideQAResponse | null>(null)

const qaForm = ref({
  question: '这款椅子适合腰椎间盘突出的人坐吗？',
  product_name: '云感护腰办公椅',
  product_specs: '腰托可调、网布透气、承重150kg',
  category: '办公家具',
})

async function handleQA() {
  loadingQA.value = true
  qaError.value = null
  try {
    qaResult.value = await api.guideQA({
      question: qaForm.value.question,
      product_name: qaForm.value.product_name,
      product_specs: qaForm.value.product_specs,
      category: qaForm.value.category,
    })
  } catch (e) {
    qaError.value = e instanceof Error ? e.message : '问答失败'
  } finally {
    loadingQA.value = false
  }
}

/* ---------------- 跨商品推荐 Tab ---------------- */
const loadingCross = ref(false)
const crossError = ref<string | null>(null)
const crossResult = ref<CrossRecommendResponse | null>(null)

const crossForm = ref({
  product_name: '云感护腰办公椅',
  category: '办公家具',
  budget: '500-1000元',
  preferenceInput: '',
  user_preferences: [] as string[],
})

function addPreference() {
  const value = crossForm.value.preferenceInput.trim()
  if (value && !crossForm.value.user_preferences.includes(value)) {
    crossForm.value.user_preferences.push(value)
  }
  crossForm.value.preferenceInput = ''
}

function removePreference(tag: string) {
  crossForm.value.user_preferences = crossForm.value.user_preferences.filter(t => t !== tag)
}

function onPreferenceKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault()
    addPreference()
  }
}

const loadingAny = computed(
  () => loadingRecommend.value || loadingQA.value || loadingCross.value
)

async function handleCross() {
  loadingCross.value = true
  crossError.value = null
  try {
    crossResult.value = await api.crossRecommend({
      product_name: crossForm.value.product_name,
      category: crossForm.value.category,
      user_preferences: crossForm.value.user_preferences,
      budget: crossForm.value.budget,
    })
  } catch (e) {
    crossError.value = e instanceof Error ? e.message : '推荐失败'
  } finally {
    loadingCross.value = false
  }
}

function scoreColor(score: number): string {
  if (score >= 80) return 'var(--green)'
  if (score >= 60) return 'var(--yellow)'
  return 'var(--brand)'
}
</script>

<template>
  <div class="feature-page">
    <div class="page-header">
      <h1>智能导购推荐</h1>
      <p>根据用户需求、预算和偏好，生成可解释的推荐理由、智能问答和跨商品推荐</p>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 推荐 Tab -->
    <div v-show="activeTab === 'recommend'" class="content-grid">
      <form class="input-form" @submit.prevent="handleRecommend">
        <div class="form-group">
          <label>用户需求 *</label>
          <textarea
            v-model="recommendForm.user_need"
            rows="3"
            required
            placeholder="例如：预算 300 元以内，送给经常加班的朋友"
          ></textarea>
        </div>

        <div class="form-group">
          <label>预算范围</label>
          <input v-model="recommendForm.budget" type="text" placeholder="例如：300元以内" />
        </div>

        <div class="form-group">
          <label>候选商品（每行一个）</label>
          <textarea
            v-model="recommendForm.products_text"
            rows="5"
            placeholder="高性价比基础款&#10;品质升级款&#10;礼赠套装款"
