export interface CopyQuestionData {
  question_no: number
  question_type: 'single' | 'multiple'
  stem_text: string | null
  question_options: Array<{
    option_key: string
    option_text: string | null
    sort_order: number
    is_correct: boolean
  }>
  groupIntroText?: string | null
}

export function useCopyQuestion() {
  const copiedId = ref<string | null>(null)

  function buildText(data: CopyQuestionData): string {
    const lines: string[] = []

    if (data.groupIntroText?.trim()) {
      lines.push('【題組說明】')
      lines.push(data.groupIntroText.trim())
      lines.push('')
    }

    const typeLabel = data.question_type === 'multiple' ? '複選題' : '單選題'
    lines.push(`第 ${data.question_no} 題（${typeLabel}）`)
    if (data.stem_text?.trim()) {
      lines.push(data.stem_text.trim())
    }
    lines.push('')

    const sorted = [...data.question_options].sort((a, b) => a.sort_order - b.sort_order)
    for (const opt of sorted) {
      lines.push(`(${opt.option_key}) ${opt.option_text?.trim() ?? ''}`)
    }

    const correctKeys = sorted.filter((o) => o.is_correct).map((o) => o.option_key)
    if (correctKeys.length > 0) {
      lines.push('')
      lines.push(`正確答案：${correctKeys.join('、')}`)
    }

    return lines.join('\n')
  }

  async function copyQuestion(id: string, data: CopyQuestionData): Promise<void> {
    if (!import.meta.client) return
    const text = buildText(data)
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      // Fallback for older browsers / non-secure contexts
      const el = document.createElement('textarea')
      el.value = text
      el.setAttribute('readonly', '')
      Object.assign(el.style, { position: 'absolute', left: '-9999px', top: '0' })
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    copiedId.value = id
    setTimeout(() => {
      if (copiedId.value === id) copiedId.value = null
    }, 2000)
  }

  return { copiedId, copyQuestion }
}
