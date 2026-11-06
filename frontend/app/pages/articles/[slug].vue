<template>
  <div class="container">
    <article v-if="post" class="article">
      <h1>{{ post.title }}</h1>
      <div class="meta">
        {{ post.meta?.category }} · {{ date }}
      </div>
      <img v-if="post.meta?.image" :src="post.meta.image" :alt="post.title" style="width:100%; border-radius:12px; margin: 8px 0 20px;" />
      <div class="content">
        <ContentRenderer :value="post" />
      </div>
    </article>

    <div v-if="post" class="article-engagement">
      <LikeButton :path="post.path" />
    </div>

    <Comments v-if="post" :path="post.path" />

    <div v-else class="empty">
      <h2>글을 찾을 수 없어요</h2>
      <p>
        <NuxtLink to="/" style="color: var(--accent);">홈으로 돌아가기</NuxtLink>
      </p>
    </div>
  </div>
</template>

<script setup>
const route = useRoute()

const { data: allPosts } = await useAsyncData('all-posts-for-single', () =>
  queryCollection('articles').all()
)

// 按 path 精确匹配
const post = computed(() =>
  (allPosts.value || []).find((p) => p.path === '/articles/' + route.params.slug)
)

const date = computed(() => {
  const d = post.value?.meta?.date
  if (!d) return ''
  try {
    return new Date(d).toLocaleDateString('ko-KR')
  } catch {
    return d
  }
})
</script>
