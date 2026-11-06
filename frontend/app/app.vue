<template>
  <div>
    <NuxtRouteAnnouncer />

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
</script>
