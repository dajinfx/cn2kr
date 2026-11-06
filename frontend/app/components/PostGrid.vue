<template>
  <div v-if="posts.length" class="magazine">
    <PostCard
      v-for="(post, i) in posts"
      :key="post.path"
      :post="post"
      :class="cardClass(i)"
    />
  </div>
  <div v-else class="empty">
    <h2>{{ emptyTitle }}</h2>
    <p>{{ emptyText }}</p>
  </div>
</template>

<script setup>
defineProps({
  posts: { type: Array, required: true },
  emptyTitle: { type: String, default: '아직 글이 없어요' },
  emptyText: { type: String, default: 'pipeline 을 실행하면 채워집니다.' },
})

// 大小混排模式：每 7 篇一个循环（大卡/宽卡/高卡错落）
function cardClass(i) {
  if (i % 7 === 0) return 'card--large'
  if (i % 7 === 3) return 'card--wide'
  if (i % 7 === 5) return 'card--tall'
  return ''
}
</script>
