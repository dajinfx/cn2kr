<template>
  <button
    class="like-btn"
    :class="{ 'is-liked': liked }"
    type="button"
    :aria-pressed="liked"
    aria-label="좋아요"
    @click="toggle"
  >
    <svg viewBox="0 0 24 24" class="like-icon" aria-hidden="true">
      <path
        d="M12 21s-6.7-4.35-9.33-8.11C.9 10.2 1.6 6.6 4.4 5.4c2.1-.9 4.5.1 5.6 1.9 1.1-1.8 3.5-2.8 5.6-1.9 2.8 1.2 3.5 4.8 1.73 7.49C18.7 16.65 12 21 12 21z"
      />
    </svg>
    <span class="like-count">{{ count }}</span>
  </button>
</template>

<script setup>
const props = defineProps({
  path: { type: String, required: true },
})

const supabase = useSupabase()
const count = ref(0)
const liked = ref(false)
const clientId = ref('')

function getClientId() {
  let id = localStorage.getItem('cn2kr:client_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('cn2kr:client_id', id)
  }
  return id
}

async function load() {
  clientId.value = getClientId()
  if (!supabase) return

  // 点赞数
  const { count: c } = await supabase
    .from('likes')
    .select('id', { count: 'exact', head: true })
    .eq('path', props.path)
  count.value = c ?? 0

  // 本机是否已赞（匿名 client_id 幂等）
  const { data } = await supabase
    .from('likes')
    .select('id')
    .eq('path', props.path)
    .eq('client_id', clientId.value)
    .limit(1)
  liked.value = (data?.length ?? 0) > 0
}

async function toggle() {
  if (liked.value || !supabase) return
  const { error } = await supabase.from('likes').insert({
    path: props.path,
    client_id: clientId.value,
  })
  if (error) return
  liked.value = true
  count.value += 1
}

onMounted(load)
</script>
