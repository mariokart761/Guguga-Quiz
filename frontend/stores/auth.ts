import { defineStore } from 'pinia'
import type { User } from '@supabase/supabase-js'

interface UserRole {
  user_id: string
  role: 'admin' | 'member'
  can_manage_questions: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const supabase = useSupabaseClient()
  const user = useSupabaseUser()

  const userRole = ref<UserRole | null>(null)
  const isLoadingRole = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => userRole.value?.role === 'admin')
  const canManageQuestions = computed(
    () => userRole.value?.role === 'admin' || userRole.value?.can_manage_questions === true,
  )

  async function fetchUserRole() {
    if (!user.value) {
      userRole.value = null
      return
    }
    isLoadingRole.value = true
    try {
      const { data, error } = await supabase
        .schema('quiz')
        .from('user_roles')
        .select('*')
        .eq('user_id', user.value.id)
        .maybeSingle()

      if (error) {
        console.warn('[AuthStore] fetchUserRole error:', error.message, error.code)
        userRole.value = null
      } else {
        userRole.value = data as UserRole | null
      }
    } catch (e) {
      console.warn('[AuthStore] fetchUserRole exception:', e)
      userRole.value = null
    } finally {
      isLoadingRole.value = false
    }
  }

  async function signInWithEmail(email: string) {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${window.location.origin}/` },
    })
    return { error }
  }

  async function signInWithGoogle() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/` },
    })
    return { error }
  }

  async function signOut() {
    await supabase.auth.signOut()
    userRole.value = null
    await navigateTo('/login')
  }

  // 監聽使用者變動
  watch(user, async (newUser) => {
    if (newUser) {
      await fetchUserRole()
    } else {
      userRole.value = null
    }
  }, { immediate: true })

  return {
    user,
    userRole,
    isLoggedIn,
    isAdmin,
    canManageQuestions,
    isLoadingRole,
    fetchUserRole,
    signInWithEmail,
    signInWithGoogle,
    signOut,
  }
})
