<template>
  <div>
    <NuxtRouteAnnouncer />

    <!-- UAT 测试环境横幅（仅 UAT 域名显示） -->
    <div v-if="isUat" class="uat-banner">⚠️ UAT 테스트 환경 — 실제 운영 사이트(cn2kr.net)가 아닙니다</div>

    <!-- 顶部导航 -->
    <header class="header">
      <div class="container header-inner">
        <NuxtLink to="/" class="logo" @click="handleHomeClick">cn<span class="dot">2</span>kr</NuxtLink>
        <nav class="nav">
          <NuxtLink to="/" @click="handleHomeClick">홈</NuxtLink>
          <NuxtLink v-for="cat in cats" :key="cat.slug" :to="`/category/${cat.slug}`">
            {{ cat.name }}
          </NuxtLink>
          <div class="nav-right">
            <NuxtLink to="/about">about</NuxtLink>
            <NuxtLink to="/tools">Tool</NuxtLink>
            <NuxtLink to="/search" aria-label="검색" class="nav-search">
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M10 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 1.5A4.5 4.5 0 1 1 10 14.5 4.5 4.5 0 0 1 10 5.5zm6.2 10.3 3.5 3.5-1.06 1.06-3.5-3.5a7.5 7.5 0 0 1-1.1-1.1z" fill="currentColor"/></svg>
            </NuxtLink>
          </div>
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
            <p style="margin-top: 12px; font-size: 14px; line-height: 1.7;">📧 jinguangdong_949<span>@</span>naver.com<br>📞 010-9638-5158</p>
          </div>
          <div class="col">
            <h4>카테고리</h4>
            <NuxtLink v-for="cat in cats" :key="cat.slug" :to="`/category/${cat.slug}`">
              {{ cat.name }}
            </NuxtLink>
          </div>
          <div class="col">
            <h4>사이트</h4>
            <NuxtLink to="/about">about</NuxtLink>
            <NuxtLink to="/tools">Tool</NuxtLink>
            <a href="/rss.xml" target="_blank" rel="noopener">RSS</a>
            <a href="/sitemap.xml" target="_blank" rel="noopener">사이트맵</a>
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
const route = useRoute()

// 点击 logo/홈：已在首页时滚动到顶部（否则 NuxtLink 正常导航到首页）
function handleHomeClick(e) {
  if (route.path === '/') {
    e.preventDefault()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// 只在 UAT 域名显示测试横幅（生产域名自动隐藏）
const isUat = computed(() => {
  if (typeof window === 'undefined') return false
  const h = window.location.hostname
  return h === 'uat.cn2kr.net' || h === 'cn2kr-uat.pages.dev'
})

// 全局 SEO 基础：语言 + 标题模板 + 站点级结构化数据
useHead({
  htmlAttrs: { lang: 'ko' },
  titleTemplate: (title) => {
    if (!title) return 'cn2kr — 중국 테크·여행·직구'
    if (title.startsWith('cn2kr — ')) return title // 首页 title 已含 cn2kr，不再重复追加
    return `${title} — cn2kr`
  },
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
