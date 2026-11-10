// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  modules: ['@nuxt/content', '@nuxtjs/sitemap'],
  css: ['~/assets/css/main.css'],

  site: {
    url: 'https://cn2kr.net',
    name: 'cn2kr',
    description: '중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다',
  },

  app: {
    head: {
      link: [
        // Pretendard 字体（韩国现代常用字体，토스/네이버 等在用）
        {
          rel: 'stylesheet',
          href: 'https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css',
          crossorigin: '',
        },
      ],
    },
  },

  runtimeConfig: {
    public: {
      // Supabase（anon key 是公开的，故意用 NUXT_PUBLIC_ 前缀）
      supabaseUrl: process.env.NUXT_PUBLIC_SUPABASE_URL || '',
      supabaseAnonKey: process.env.NUXT_PUBLIC_SUPABASE_ANON_KEY || '',
      // Kakao 分享（JavaScript app key，公开）
      kakaoAppKey: process.env.NUXT_PUBLIC_KAKAO_APP_KEY || '',
      // UAT 测试环境标记（uat 项目设 NUXT_PUBLIC_IS_UAT=true 时加 noindex）
      isUat: process.env.NUXT_PUBLIC_IS_UAT || '',
    },
  },

  // 静态生成友好：@nuxt/content 的内容在构建时预渲染
  nitro: {
    prerender: {
      crawlLinks: true,
    },
  },
})
