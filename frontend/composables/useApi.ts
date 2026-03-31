/**
 * 與 FastAPI 後端溝通的 composable
 */
export function useApi() {
  const config = useRuntimeConfig()
  const supabase = useSupabaseClient()

  async function getAuthHeaders(): Promise<Record<string, string>> {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  async function apiGet<T>(path: string): Promise<T> {
    const headers = await getAuthHeaders()
    const data = await $fetch<T>(`${config.public.apiBase}${path}`, { headers })
    return data
  }

  async function apiPost<T>(path: string, body?: unknown): Promise<T> {
    const headers = await getAuthHeaders()
    const data = await $fetch<T>(`${config.public.apiBase}${path}`, {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return data
  }

  async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
    const headers = await getAuthHeaders()
    const data = await $fetch<T>(`${config.public.apiBase}${path}`, {
      method: 'PATCH',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return data
  }

  async function apiDelete<T>(path: string): Promise<T> {
    const headers = await getAuthHeaders()
    const data = await $fetch<T>(`${config.public.apiBase}${path}`, {
      method: 'DELETE',
      headers,
    })
    return data
  }

  async function apiUpload<T>(path: string, file: File, extraFields?: Record<string, string>): Promise<T> {
    const headers = await getAuthHeaders()
    const formData = new FormData()
    formData.append('file', file)
    if (extraFields) {
      for (const [k, v] of Object.entries(extraFields)) {
        formData.append(k, v)
      }
    }
    const data = await $fetch<T>(`${config.public.apiBase}${path}`, {
      method: 'POST',
      headers,
      body: formData,
    })
    return data
  }

  return { apiGet, apiPost, apiPatch, apiDelete, apiUpload }
}
