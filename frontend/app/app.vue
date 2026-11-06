<template>
  <div>
    <NuxtRouteAnnouncer />

    <!-- UAT 测试环境横幅 -->
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
  ],
})
</script>
