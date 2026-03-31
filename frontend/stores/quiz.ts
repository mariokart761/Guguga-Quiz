import { defineStore } from 'pinia'

export interface Paper {
  id: string
  title: string
  source_type: string
  exam_year: number | null
  term: string | null
  subject: string | null
  description: string | null
  total_questions: number
  is_published: boolean
  created_at: string
}

export interface Question {
  id: string
  paper_id: string
  group_id: string | null
  question_no: number
  question_type: 'single' | 'multiple'
  stem_html: string
  stem_text: string | null
  explanation_html: string | null
  difficulty: string | null
  question_options: QuestionOption[]
  question_assets?: QuestionAsset[]
}

export interface QuestionOption {
  id: string
  question_id: string
  option_key: string
  option_html: string
  option_text: string | null
  sort_order: number
  is_correct: boolean
}

export interface QuestionAsset {
  id: string
  object_path: string
  bucket_name: string
}

export interface Attempt {
  id: string
  user_id: string
  paper_id: string
  mode: 'practice' | 'mock_exam' | 'wrong_review'
  started_at: string
  submitted_at: string | null
  score: number | null
  correct_count: number
  wrong_count: number
  duration_seconds: number | null
}

export interface AttemptAnswer {
  id: string
  attempt_id: string
  question_id: string
  selected_answers: string[]
  is_correct: boolean
  answered_at: string
}

export const useQuizStore = defineStore('quiz', () => {
  const supabase = useSupabaseClient()

  // 試卷列表
  const papers = ref<Paper[]>([])
  const papersLoading = ref(false)

  // 目前作答的 attempt
  const currentAttempt = ref<Attempt | null>(null)
  const currentQuestions = ref<Question[]>([])
  const currentAnswers = ref<Record<string, string[]>>({})

  // ============================================================
  // 試卷相關
  // ============================================================

  async function fetchPapers(filters?: { subject?: string; exam_year?: number }) {
    papersLoading.value = true
    try {
      let query = supabase
        .schema('quiz')
        .from('papers')
        .select('*')
        .eq('is_published', true)
        .order('exam_year', { ascending: false })

      if (filters?.subject) query = query.eq('subject', filters.subject)
      if (filters?.exam_year) query = query.eq('exam_year', filters.exam_year)

      const { data } = await query
      papers.value = (data as Paper[]) ?? []
    } finally {
      papersLoading.value = false
    }
  }

  async function fetchPaperWithQuestions(paperId: string) {
    const { data: paperData } = await supabase
      .schema('quiz')
      .from('papers')
      .select('*')
      .eq('id', paperId)
      .single()

    const { data: questionsData } = await supabase
      .schema('quiz')
      .from('questions')
      .select('*, question_options(*), question_assets(*)')
      .eq('paper_id', paperId)
      .order('question_no')

    return {
      paper: paperData as Paper | null,
      questions: (questionsData as Question[]) ?? [],
    }
  }

  // ============================================================
  // 作答相關
  // ============================================================

  async function startAttempt(
    userId: string,
    paperId: string,
    mode: Attempt['mode'],
    questions: Question[],
  ) {
    const { data } = await supabase
      .schema('quiz')
      .from('attempts')
      .insert({
        user_id: userId,
        paper_id: paperId,
        mode,
      })
      .select()
      .single()

    const attempt = data as Attempt

    // 持久化已選題目 IDs，練習頁重新整理後仍可正確篩題
    if (import.meta.client && questions.length > 0) {
      sessionStorage.setItem(
        `attempt_qids_${attempt.id}`,
        JSON.stringify(questions.map((q) => q.id)),
      )
    }

    currentAttempt.value = attempt
    currentQuestions.value = questions
    currentAnswers.value = {}
    return attempt
  }

  async function submitAnswer(
    attemptId: string,
    questionId: string,
    selectedAnswers: string[],
    correctKeys: string[],
  ) {
    const isCorrect =
      selectedAnswers.length === correctKeys.length &&
      selectedAnswers.every((k) => correctKeys.includes(k))

    await supabase.schema('quiz').from('attempt_answers').insert({
      attempt_id: attemptId,
      question_id: questionId,
      selected_answers: selectedAnswers,
      is_correct: isCorrect,
    })

    currentAnswers.value[questionId] = selectedAnswers
    return isCorrect
  }

  async function submitAttempt(attemptId: string) {
    const answers = await supabase
      .schema('quiz')
      .from('attempt_answers')
      .select('is_correct')
      .eq('attempt_id', attemptId)

    const allAnswers = (answers.data ?? []) as { is_correct: boolean }[]
    const correctCount = allAnswers.filter((a) => a.is_correct).length
    const wrongCount = allAnswers.length - correctCount
    const score = allAnswers.length > 0
      ? Math.round((correctCount / allAnswers.length) * 100)
      : 0

    await supabase
      .schema('quiz')
      .from('attempts')
      .update({
        submitted_at: new Date().toISOString(),
        correct_count: correctCount,
        wrong_count: wrongCount,
        score,
      })
      .eq('id', attemptId)

    currentAttempt.value = null
    currentQuestions.value = []
    currentAnswers.value = {}
  }

  // ============================================================
  // 收藏
  // ============================================================

  async function toggleBookmark(userId: string, questionId: string): Promise<boolean> {
    const { data: existing } = await supabase
      .schema('quiz')
      .from('bookmarks')
      .select('user_id')
      .eq('user_id', userId)
      .eq('question_id', questionId)
      .maybeSingle()

    if (existing) {
      await supabase
        .schema('quiz')
        .from('bookmarks')
        .delete()
        .eq('user_id', userId)
        .eq('question_id', questionId)
      return false
    } else {
      await supabase
        .schema('quiz')
        .from('bookmarks')
        .insert({ user_id: userId, question_id: questionId })
      return true
    }
  }

  async function toggleWrongBook(userId: string, questionId: string): Promise<boolean> {
    const { data: existing } = await supabase
      .schema('quiz')
      .from('wrong_question_stats')
      .select('user_id')
      .eq('user_id', userId)
      .eq('question_id', questionId)
      .maybeSingle()

    if (existing) {
      await supabase
        .schema('quiz')
        .from('wrong_question_stats')
        .delete()
        .eq('user_id', userId)
        .eq('question_id', questionId)
      return false
    } else {
      await supabase
        .schema('quiz')
        .from('wrong_question_stats')
        .insert({ user_id: userId, question_id: questionId, wrong_count: 1, last_wrong_at: new Date().toISOString() })
      return true
    }
  }

  async function fetchBookmarks(userId: string) {
    const { data } = await supabase
      .schema('quiz')
      .from('bookmarks')
      .select('question_id, created_at, questions(*, question_options(*), question_assets(*), papers(title, subject, exam_year))')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
    return (data ?? []) as Array<{ question_id: string; created_at: string; questions: Question }>
  }

  // ============================================================
  // 錯題本
  // ============================================================

  async function fetchWrongStats(userId: string) {
    const { data } = await supabase
      .schema('quiz')
      .from('wrong_question_stats')
      .select('*, questions(*, question_options(*), question_assets(*), papers(title, subject, exam_year))') 
      .eq('user_id', userId)
      .order('last_wrong_at', { ascending: false })
    return data ?? []
  }

  // ============================================================
  // 成績記錄
  // ============================================================

  async function fetchMyAttempts(userId: string) {
    const { data } = await supabase
      .schema('quiz')
      .from('attempts')
      .select('*, papers(title, subject)')
      .eq('user_id', userId)
      .not('submitted_at', 'is', null)
      .order('submitted_at', { ascending: false })
      .limit(50)
    return data ?? []
  }

  return {
    papers,
    papersLoading,
    currentAttempt,
    currentQuestions,
    currentAnswers,
    fetchPapers,
    fetchPaperWithQuestions,
    startAttempt,
    submitAnswer,
    submitAttempt,
    toggleBookmark,
    toggleWrongBook,
    fetchBookmarks,
    fetchWrongStats,
    fetchMyAttempts,
  }
})
