<template>
  <div>
    <NuxtRouteAnnouncer />

    <!-- UAT 测试环境横幅（仅 UAT 域名显示） -->
    <div v-if="isUat" class="uat-banner">⚠️ UAT 테스트 환경 — 실제 운영 사이트(cn2kr.net)가 아닙니다</div>

    <!-- 顶部导航 -->
    <header class="header">
      <div class="container header-inner">
        <NuxtLink to="/" class="logo">cn<span class="dot">2</span>kr</NuxtLink>
        <nav class="nav">
          <NuxtLink to="/">홈</NuxtLink>
          <NuxtLink v-for="cat in cats" :key="cat.slug" :to="`/category/${cat.slug}`">
            {{ cat.name }}
          </NuxtLink>
          <NuxtLink to="/about">소개</NuxtLink>
          <NuxtLink to="/tools">도구</NuxtLink>
          <NuxtLink to="/search" aria-label="검색" class="nav-search">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M10 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 1.5A4.5 4.5 0 1 1 10 14.5 4.5 4.5 0 0 1 10 5.5zm6.2 10.3 3.5 3.5-1.06 1.06-3.5-3.5a7.5 7.5 0 0 1-1.1-1.1z" fill="currentColor"/></svg>
          </NuxtLink>
        </nav>
      </div>
    </header>

    <!-- 页面内容 -->
    <main>
      <NuxtPage />
    </main>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="container">
        <div class="footer-inner">
          <div>
            <div class="logo">cn<span class="dot">2</span>kr</div>
            <p style="margin-top: 8px; font-size: 14px;">중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다</p>
          </div>
          <div class="col">
            <h4>카테고리</h4>
            <NuxtLink v-for="cat in cats" :key="cat.slug" :to="`/category/${cat.slug}`">
              {{ cat.name }}
            </NuxtLink>
          </div>
          <div class="col">
            <h4>사이트</h4>
            <NuxtLink to="/about">소개</NuxtLink>
            <NuxtLink to="/tools">실용 도구</NuxtLink>
          </div>
        </div>
        <div class="footer-bottom">© {{ new Date().getFullYear() }} cn2kr — All rights reserved</div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { CATEGORIES } from '~/composables/useCategories'

const cats = CATEGORIES

// 只在 UAT 域名显示测试横幅（生产域名自动隐藏）
const isUat = computed(() => {
  if (typeof window === 'undefined') return false
  const h = window.location.hostname
  return h === 'uat.cn2kr.net' || h === 'cn2kr-uat.pages.dev'
})

// 全局 SEO 基础：语言 + 标题模板 + 站点级结构化数据
useHead({
  htmlAttrs: { lang: 'ko' },
  titleTemplate: (title) => (title ? `${title} — cn2kr` : 'cn2kr — 중국 테크·여행·직구'),
  meta: [
    {
      name: 'description',
      content: '중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다',
    },
    { property: 'og:site_name', content: 'cn2kr' },
    { property: 'og:type', content: 'website' },
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'naver-site-verification', content: '5528fa2e3fdd838f3123f7bc5cbfa69a5b4c34a8' },
  ],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'cn2kr',
        url: 'https://cn2kr.net',
        description: '중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다',
      }),
    },
    // Kakao 分享 SDK（카카오톡 공유용）
    {
      src: 'https://t1.kakaocdn.net/kakao_js_sdk/2.7.1/kakao.min.js',
      defer: true,
      crossorigin: 'anonymous',
    },
  ],
})

// UAT 构建时加 noindex（防止测试站被搜索引擎收录，避免重复内容）
const config = useRuntimeConfig()
if (config.public.isUat === 'true') {
  useHead({ meta: [{ name: 'robots', content: 'noindex, nofollow' }] })
}

// Kakao SDK 初始化（需要 NUXT_PUBLIC_KAKAO_APP_KEY）
onMounted(() => {
  const key = config.public.kakaoAppKey
  if (window.Kakao && key && !window.Kakao.isInitialized()) {
    window.Kakao.init(key)
  }
})
</script>
