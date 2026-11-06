<template>
  <section class="comments">
    <h2 class="comments-title">
      댓글 <span class="comments-count">{{ comments.length }}</span>
    </h2>

    <form class="comment-form" @submit.prevent="submit">
      <div class="comment-form-row">
        <input
          v-model="author"
          class="comment-input"
          type="text"
          placeholder="닉네임 (선택)"
          maxlength="50"
        />
        <button
          class="comment-submit"
          type="submit"
          :disabled="submitting || !content.trim()"
        >
          {{ submitting ? '등록 중...' : '등록' }}
        </button>
      </div>
      <textarea
        v-model="content"
        class="comment-textarea"
        placeholder="댓글을 남겨주세요"
        maxlength="1000"
        required
      ></textarea>
      <p v-if="error" class="comment-error">{{ error }}</p>
    </form>

    <ul class="comment-list">
      <li v-for="c in comments" :key="c.id" class="comment-item">
        <div class="comment-meta">
          <strong class="comment-author">{{ c.author }}</strong>
          <time class="comment-date">{{ formatDate(c.created_at) }}</time>
        </div>
        <p class="comment-content">{{ c.content }}</p>
      </li>
      <li v-if="!comments.length" class="comment-empty">첫 댓글을 남겨보세요</li>
    </ul>
  </section>
</template>

<script setup>
const props = defineProps({
  path: { type: String, required: true },
})

const supabase = useSupabase()
const comments = ref([])
const author = ref('')
const content = ref('')
const submitting = ref(false)
const error = ref('')

async function load() {
  if (!supabase) return
  const { data } = await supabase
    .from('comments')
    .select('id, author, content, created_at')
    .eq('path', props.path)
    .eq('approved', true)
    .order('created_at', { ascending: false })
  comments.value = data || []
}

async function submit() {
  if (submitting.value || !content.value.trim() || !supabase) return
  submitting.value = true
  error.value = ''

  const { data, error: e } = await supabase
    .from('comments')
    .insert({
      path: props.path,
      author: author.value.trim().slice(0, 50) || '익명',
      content: content.value.trim(),
    })
    .select('id, author, content, created_at')

  if (e || !data?.length) {
    error.value = '등록에 실패했습니다. 다시 시도해주세요'
  } else {
    comments.value.unshift(data[0])
    content.value = ''
    author.value = ''
  }
  submitting.value = false
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return ''
  }
}

onMounted(load)
</script>
