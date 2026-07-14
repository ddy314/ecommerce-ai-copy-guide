<script setup lang="ts">
import { ref } from 'vue'
import {
  api,
  type GuideRecommendationResponse,
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
