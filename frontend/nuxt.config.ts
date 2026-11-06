// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  modules: ['@nuxt/content'],
  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      // Supabase（anon key 是公开的，故意用 NUXT_PUBLIC_ 前缀）
      supabaseUrl: process.env.NUXT_PUBLIC_SUPABASE_URL || '',
      supabaseAnonKey: process.env.NUXT_PUBLIC_SUPABASE_ANON_KEY || '',
    },
  },

  // 静态生成友好：@nuxt/content 的内容在构建时预渲染
  nitro: {
    prerender: {
      crawlLinks: true,
    },
  },
})
