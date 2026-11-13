<template>
  <div>
    <!-- 三栏布局：左 widgets + 主新闻流 + 右 widgets -->
    <div class="container portal-grid">
      <!-- 左栏 widgets -->
      <aside class="portal-left">
        <section class="widget">
          <h3 class="widget-title">인기 글</h3>
          <ol class="widget-rank">
            <li v-for="(p, i) in popularPosts" :key="p.path">
              <NuxtLink :to="p.path">
                <span class="widget-num">{{ i + 1 }}</span>
                <span class="widget-text">{{ p.title }}</span>
              </NuxtLink>
            </li>
          </ol>
        </section>
        <section class="widget">
          <h3 class="widget-title">카테고리</h3>
          <ul class="widget-list">
            <li v-for="cat in CATEGORIES" :key="cat.slug">
              <NuxtLink :to="`/category/${cat.slug}`">{{ cat.name }}</NuxtLink>
            </li>
          </ul>
        </section>
      </aside>

      <!-- 主内容：新闻流 -->
      <main class="portal-center">
        <!-- 大头图头条 -->
        <NuxtLink v-if="lead" :to="lead.path" class="lead-card">
          <div class="lead-thumb">
            <img :src="lead.meta?.image" :alt="lead.title" loading="eager" />
          </div>
          <div class="lead-body">
            <h1>{{ lead.title }}</h1>
            <span class="lead-meta">
              <span :style="{ color: categoryColor(lead.meta?.category) }">{{ lead.meta?.category }}</span>
              <span>·</span>
              <span>{{ formatDate(lead.meta?.date) }}</span>
            </span>
          </div>
        </NuxtLink>

        <!-- 排名标题 -->
        <ol class="rank-list">
          <li v-for="(p, i) in rankPosts" :key="p.path">
            <NuxtLink :to="p.path" class="rank-item">
              <span class="rank-num">{{ i + 2 }}</span>
              <h3>{{ p.title }}</h3>
            </NuxtLink>
          </li>
        </ol>

        <!-- 新闻流（图左文右） -->
        <div class="news-list">
          <NuxtLink v-for="p in feedPosts" :key="p.path" :to="p.path" class="news-item">
            <div class="news-thumb">
              <img :src="p.meta?.image" :alt="p.title" loading="eager" />
            </div>
            <div class="news-body">
              <h3>{{ p.title }}</h3>
              <span class="news-meta">
                <span :style="{ color: categoryColor(p.meta?.category) }">{{ p.meta?.category }}</span>
                <span>·</span>
                <span>{{ formatDate(p.meta?.date) }}</span>
              </span>
            </div>
          </NuxtLink>
        </div>

        <div v-if="feedPosts.length < allRestPosts.length" class="load-more-wrap">
          <button class="load-more" type="button" @click="loadMore">
            더 보기 <span class="load-more-count">({{ allRestPosts.length - feedPosts.length }}개 남음)</span>
          </button>
        </div>
      </main>

      <!-- 右栏 widgets -->
      <aside class="portal-right">
        <section class="widget">
          <h3 class="widget-title">환율</h3>
          <div class="widget-rate">
            <span>1 CNY</span>
            <span class="widget-eq">=</span>
            <strong>190 KRW</strong>
          </div>
          <NuxtLink to="/tools" class="widget-link">환율·관세 계산기 →</NuxtLink>
        </section>
        <section class="widget">
          <h3 class="widget-title">cn2kr</h3>
          <ul class="widget-list">
            <li><NuxtLink to="/about">소개</NuxtLink></li>
            <li><NuxtLink to="/tools">실용 도구</NuxtLink></li>
            <li><NuxtLink to="/search">검색</NuxtLink></li>
          </ul>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { CATEGORIES, categoryColor } from '~/composables/useCategories'

const { data: posts } = await useAsyncData('home-posts', () =>
  queryCollection('articles').all()
)

const sortedPosts = computed(() =>
  [...(posts.value || [])].sort((a, b) =>
    (b.meta?.date || '').localeCompare(a.meta?.date || '')
  )
)

const lead = computed(() => sortedPosts.value[0] || null)
const rankPosts = computed(() => sortedPosts.value.slice(1, 5))
const allRestPosts = computed(() => sortedPosts.value.slice(5))

const popularPosts = computed(() => sortedPosts.value.slice(0, 6))

const visibleCount = ref(12)
const feedPosts = computed(() => allRestPosts.value.slice(0, visibleCount.value))

function loadMore() {
  visibleCount.value += 12
}

function formatDate(d) {
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
  } catch {
    return d
  }
}

useSeoMeta({
  title: 'cn2kr — 중국 테크·여행·직구',
  description: '중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다. 중국 직구, 여행, 테크 실전 정보를 매일 업데이트합니다.',
  ogTitle: 'cn2kr — 중국 테크·여행·직구',
  ogDescription: '중국의 테크 · 여행 · 직구를 한국 시선으로 소개합니다.',
  ogUrl: 'https://cn2kr.net',
})
</script>
