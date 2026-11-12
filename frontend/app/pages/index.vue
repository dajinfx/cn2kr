<template>
  <div>
    <!-- 两栏：左文字流 + 右 widgets -->
    <div class="container yahoo-main">
      <!-- 左：新闻文字流 -->
      <div class="yahoo-left">
        <!-- 헤드라인 -->
        <div class="yahoo-section">
          <h2 class="yahoo-sec-title">헤드라인</h2>
          <ol class="yahoo-rank">
            <li v-for="(p, i) in topPosts" :key="p.path">
              <NuxtLink :to="p.path" class="yahoo-rank-item">
                <span class="yahoo-num">{{ i + 1 }}</span>
                <h3>{{ p.title }}</h3>
              </NuxtLink>
            </li>
          </ol>
        </div>

        <!-- 최신 -->
        <div class="yahoo-section">
          <h2 class="yahoo-sec-title">최신</h2>
          <div class="yahoo-feed">
            <NuxtLink v-for="p in visiblePosts" :key="p.path" :to="p.path" class="yahoo-feed-item">
              <div class="yahoo-feed-body">
                <h3>{{ p.title }}</h3>
                <span class="yahoo-feed-meta">
                  <span :style="{ color: categoryColor(p.meta?.category) }">{{ p.meta?.category }}</span>
                  <span>·</span>
                  <span>{{ formatDate(p.meta?.date) }}</span>
                </span>
              </div>
              <div class="yahoo-feed-thumb">
                <img :src="p.meta?.image" :alt="p.title" loading="lazy" />
              </div>
            </NuxtLink>
          </div>
          <div v-if="visiblePosts.length < restPosts.length" class="load-more-wrap">
            <button class="load-more" type="button" @click="loadMore">
              더 보기 <span class="load-more-count">({{ restPosts.length - visiblePosts.length }}개 남음)</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 右：widgets -->
      <aside class="yahoo-right">
        <!-- 환율 widget -->
        <section class="widget">
          <h3 class="widget-title">환율</h3>
          <div class="widget-rate">
            <span>1 CNY</span>
            <span class="widget-eq">=</span>
            <strong>{{ cnyToKrw }} KRW</strong>
          </div>
          <NuxtLink to="/tools" class="widget-link">환율·관세 계산기 →</NuxtLink>
        </section>

        <!-- 인기 글 widget -->
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

        <!-- 카테고리 widget -->
        <section class="widget">
          <h3 class="widget-title">카테고리</h3>
          <ul class="widget-list">
            <li v-for="cat in CATEGORIES" :key="cat.slug">
              <NuxtLink :to="`/category/${cat.slug}`">{{ cat.name }}</NuxtLink>
            </li>
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

// 헤드라인 = 前 5 篇；최신 = 其余
const topPosts = computed(() => sortedPosts.value.slice(0, 5))
const restPosts = computed(() => sortedPosts.value.slice(5))

const popularPosts = computed(() => sortedPosts.value.slice(0, 8))

// 汇率（约 1 CNY ≈ 190 KRW）
const cnyToKrw = 190

const visibleCount = ref(15)
const visiblePosts = computed(() => restPosts.value.slice(0, visibleCount.value))

function loadMore() {
  visibleCount.value += 15
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
