import { createClient } from '@supabase/supabase-js'

// 单例缓存（可能是 null，表示未配置 Supabase）
let _client = undefined

export function useSupabase() {
  if (_client !== undefined) return _client

  const config = useRuntimeConfig()
  const url = config.public.supabaseUrl
  const key = config.public.supabaseAnonKey

  if (!url || !key) {
    // 未配置：返回 null，组件会静默降级（点赞/评论不生效，但不报错）
    _client = null
    return null
  }

  _client = createClient(url, key, {
    auth: { persistSession: true, autoRefreshToken: true },
  })
  return _client
}
