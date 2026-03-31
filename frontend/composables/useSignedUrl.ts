/**
 * 產生 Supabase Storage signed URL 的 composable
 */
export function useSignedUrl() {
  const supabase = useSupabaseClient()

  async function getSignedUrl(bucket: string, path: string, expiresIn = 3600): Promise<string | null> {
    if (!path) return null
    try {
      const { data, error } = await supabase.storage
        .from(bucket)
        .createSignedUrl(path, expiresIn)
      if (error) return null
      return data.signedUrl
    } catch {
      return null
    }
  }

  return { getSignedUrl }
}
