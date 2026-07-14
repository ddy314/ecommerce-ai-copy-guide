/**
 * API 服务层
 * 封装与后端的 HTTP 请求
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface CopyGenerationRequest {
  product_name: string
  audience?: string
  style?: string
  selling_points?: string[]
}

interface CopyGenerationResponse {
  product_name: string
  style: string
  title: string
  selling_points: string[]
  detail_copy: string
  ad_slogan: string
}

interface GuideRecommendationRequest {
  user_need: string
  budget?: string
  products?: string[]
}

interface GuideRecommendationResponse {
  user_need: string
  budget: string
  recommended_product: string
  reason: string
  alternatives: string[]
  guide_message: string
}

interface GuideQARequest {
  question: string
  product_name?: string
  product_specs?: string
  category?: string
  question_type?: string
}

interface GuideQAResponse {
  question: string
  question_type: string
  answer: string
  related_tips: string[]
}

interface CrossRecommendRequest {
  product_name: string
  category?: string
  user_preferences?: string[]
  budget?: string
}

interface CrossRecommendationItem {
  product_name: string
  reason: string
  match_score: number
}

interface CrossRecommendResponse {
  current_product: string
  user_preferences: string[]
  recommendations: CrossRecommendationItem[]
}

interface ReviewAnalysisRequest {
  product_name?: string
  reviews: string[]
}

/** 吐槽点：可能是字符串（含 [分类] 前缀）或对象 */
interface ComplaintItem {
  category?: string
  content: string
}

interface SentimentDetail {
  positive_reviews: string[]
  negative_reviews: string[]
  complaints: Array<string | ComplaintItem>
}

interface ReviewAnalysisResponse {
  product_name: string
  total: number
  sentiment: {
    positive: number
    neutral: number
    negative: number
  }
  sentiment_detail?: SentimentDetail
  top_keywords: string[]
  pain_points: string[]
  optimization_suggestions: string[]
}

interface LiveScriptRequest {
  product_name: string
  product_specs?: string
  audience?: string
  duration_minutes?: number
  tone?: string
  highlights?: string[]
}

interface ExplanationFlowStep {
  step: number
  title: string
  script: string
  key_points: string[]
}

interface LiveScriptSegment {
  name: string
  minutes: number
  script: string
  action_hint?: string
}

interface LiveScriptResponse {
  product_name: string
  duration_minutes: number
  tone: string
  segments: LiveScriptSegment[]
  interaction_questions: string[]
  explanation_flow?: ExplanationFlowStep[]
  conversion_scripts?: string[]
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: '请求失败' }))
    throw new Error(error.message || `HTTP ${response.status}`)
  }
  return response.json()
}

export const api = {
  /**
   * 生成商品文案
   */
  async generateCopy(data: CopyGenerationRequest): Promise<CopyGenerationResponse> {
    const response = await fetch(`${API_BASE_URL}/api/copy/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse<CopyGenerationResponse>(response)
  },

  /**
   * 智能导购推荐
   */
  async recommendGuide(data: GuideRecommendationRequest): Promise<GuideRecommendationResponse> {
    const response = await fetch(`${API_BASE_URL}/api/guide/recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse<GuideRecommendationResponse>(response)
  },

  /**
   * 智能导购问答
   */
  async guideQA(data: GuideQARequest): Promise<GuideQAResponse> {
    const response = await fetch(`${API_BASE_URL}/api/guide/qa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse<GuideQAResponse>(response)
  },

  /**
   * 跨商品推荐
   */
  async crossRecommend(data: CrossRecommendRequest): Promise<CrossRecommendResponse> {
    const response = await fetch(`${API_BASE_URL}/api/guide/cross-recommend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse<CrossRecommendResponse>(response)
  },

  /**
   * 评论情感分析
   */
  async analyzeReviews(data: ReviewAnalysisRequest): Promise<ReviewAnalysisResponse> {
    const response = await fetch(`${API_BASE_URL}/api/reviews/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse<ReviewAnalysisResponse>(response)
  },

  /**
   * 直播脚本生成
   */
  async generateLiveScript(data: LiveScriptRequest): Promise<LiveScriptResponse> {
    const response = await fetch(`${API_BASE_URL}/api/scripts/live`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse<LiveScriptResponse>(response)
  },

  /**
   * 健康检查
   */
  async checkHealth(): Promise<{ status: string; version: string }> {
    const response = await fetch(`${API_BASE_URL}/health`)
    return handleResponse(response)
  },
}

export type {
  CopyGenerationRequest,
  CopyGenerationResponse,
  GuideRecommendationRequest,
  GuideRecommendationResponse,
  GuideQARequest,
  GuideQAResponse,
  CrossRecommendRequest,
  CrossRecommendResponse,
  CrossRecommendationItem,
  ReviewAnalysisRequest,
  ReviewAnalysisResponse,
  SentimentDetail,
  ComplaintItem,
  LiveScriptRequest,
  LiveScriptResponse,
  ExplanationFlowStep,
  LiveScriptSegment,
}
