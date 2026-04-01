export type AiExplainLanguage = 'zh-TW' | 'en'

export interface AiExplainState {
  loading: Ref<boolean>
  error: Ref<string | null>
  explanation: Ref<string | null>
  cached: Ref<boolean>
  model: Ref<string | null>
  fetchExplanation: (questionId: string, language?: AiExplainLanguage) => Promise<void>
  reset: () => void
}

export function useAiExplain(): AiExplainState {
  const supabase = useSupabaseClient()

  const loading = ref(false)
  const error = ref<string | null>(null)
  const explanation = ref<string | null>(null)
  const cached = ref(false)
  const model = ref<string | null>(null)

  async function fetchExplanation(
    questionId: string,
    language: AiExplainLanguage = 'zh-TW',
  ): Promise<void> {
    if (loading.value) return

    loading.value = true
    error.value = null

    try {
      const { data, error: fnError } = await supabase.functions.invoke('ai-explain', {
        body: { question_id: questionId, language },
      })

      if (fnError) {
        throw new Error(fnError.message ?? 'AI 詳解載入失敗')
      }

      if (!data?.explanation) {
        throw new Error('未收到有效的 AI 回應')
      }

      explanation.value = data.explanation as string
      cached.value = data.cached === true
      model.value = (data.model as string) ?? null
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'AI 詳解載入失敗，請稍後再試'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  function reset(): void {
    loading.value = false
    error.value = null
    explanation.value = null
    cached.value = false
    model.value = null
  }

  return { loading, error, explanation, cached, model, fetchExplanation, reset }
}
