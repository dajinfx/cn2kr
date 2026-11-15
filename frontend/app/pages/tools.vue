<template>
  <div class="container">
    <div class="tools-hero">
      <h1>실용 도구</h1>
      <p>중국 직구·여행에 필요한 계산기를 모았습니다</p>
    </div>

    <div class="tools-grid">
      <!-- 汇率计算器 -->
      <section class="tool-card">
        <h2 class="tool-title">환율 계산기</h2>
        <p class="tool-note">
          환율은 자동 갱신됩니다. 실제 결제 환율과 다를 수 있습니다.
        </p>

        <!-- 币种切换 -->
        <div class="rate-tabs" role="tablist">
          <button
            v-for="c in CURRENCIES"
            :key="c.code"
            type="button"
            class="rate-tab"
            :class="{ active: active === c.code }"
            @click="switchCurrency(c.code)"
          >
            {{ c.name }} <span class="rate-tab-code">{{ c.code }}</span>
          </button>
        </div>

        <label class="tool-field">
          <span>{{ cur.name }} ({{ cur.code }})</span>
          <input v-model.number="amount" type="number" min="0" step="1" :placeholder="`예: ${cur.example}`" />
        </label>
        <div class="tool-swap" aria-hidden="true">⇅</div>
        <label class="tool-field">
          <span>원 (KRW)</span>
          <input v-model.number="krw" type="number" min="0" step="100" placeholder="예: 19000" />
        </label>

        <p class="tool-result">
          기준 환율:
          <strong>{{ scaleLabel }} {{ cur.name }}</strong>
          ≈ <strong>{{ scaledRate.toLocaleString() }}</strong> 원
          <button class="tool-rate-edit" type="button" @click="showRateEdit = !showRateEdit">
            환율 수정
          </button>
        </p>
        <label v-if="showRateEdit" class="tool-field">
          <span>{{ scaleLabel }} {{ cur.name }} = ? KRW</span>
          <input v-model.number="scaledRateEdit" type="number" min="0.0001" step="any" />
        </label>

        <p v-if="liveTime" class="tool-live">🔄 {{ liveTime }} 기준 (자동 갱신)</p>
      </section>

      <!-- 关税估算器 -->
      <section class="tool-card">
        <h2 class="tool-title">직구 관세 간편 계산</h2>
        <p class="tool-note">간단한 추정용입니다. 정확한 세액은 관세청을 확인하세요.</p>
        <label class="tool-field">
          <span>상품 금액 (USD)</span>
          <input v-model.number="usd" type="number" min="0" step="1" placeholder="예: 80" />
        </label>
        <label class="tool-field">
          <span>배송 국가</span>
          <select v-model="origin">
            <option value="us">미국발</option>
            <option value="other">그 외 국가(중국 등)</option>
          </select>
        </label>
        <div class="tool-duty" :class="dutyStatus">
          <p v-if="isFree" class="duty-free">✅ 면세 범위 내입니다 ({{ limit }}$ 이하)</p>
          <p v-else class="duty-pay">⚠️ 면세 한도 초과 — 예상 관세 약 <strong>{{ duty }}원</strong></p>
        </div>
        <p class="tool-note">면세 한도: 미국발 200$ · 그 외 150$ (물품가 기준, 단순화)</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

// ===== 汇率计算器 =====
// rate = 1 单位货币对应的韩元（KRW）
// scale = 展示/编辑时使用的数量级（越南盾用 1000，其余用 1）
const CURRENCIES = [
  { code: 'CNY', name: '위안', scale: 1, rate: 200, example: 100 },
  { code: 'USD', name: '달러', scale: 1, rate: 1337, example: 100 },
  { code: 'JPY', name: '엔', scale: 1, rate: 8.36, example: 1000 },
  { code: 'VND', name: '동', scale: 1000, rate: 0.052, example: 100000 },
]

const active = ref('CNY')
const amount = ref(100)
const krw = ref(20000)
const showRateEdit = ref(false)
const liveTime = ref('')

const cur = computed(() => CURRENCIES.find((c) => c.code === active.value))
const scaleLabel = computed(() => (cur.value.scale === 1 ? '1' : cur.value.scale.toLocaleString()))
const scaledRate = computed(() => cur.value.rate * cur.value.scale)

// 编辑框绑定到「展示数量级」的汇率（如 1,000 동 = 52 원）
const scaledRateEdit = computed({
  get: () => Math.round(cur.value.rate * cur.value.scale * 10000) / 10000,
  set: (v) => {
    if (v > 0) {
      cur.value.rate = v / cur.value.scale
      if (amount.value != null) krw.value = Math.round(amount.value * cur.value.rate)
    }
  },
})

function switchCurrency(code) {
  if (active.value === code) return
  active.value = code
  showRateEdit.value = false
  krw.value = Math.round((amount.value || 0) * cur.value.rate)
}

watch(amount, (v) => {
  if (v !== null && v !== undefined) krw.value = Math.round(v * cur.value.rate)
})
watch(krw, (v) => {
  if (v !== null && v !== undefined) amount.value = Math.round((v / cur.value.rate) * 100) / 100
})

// 拉取实时汇率（免费 API，带 localStorage 缓存 + 硬编码兜底）
const RATE_CACHE_KEY = 'cn2kr_rates_v1'
const RATE_TTL = 6 * 60 * 60 * 1000 // 6 小时

async function loadRates() {
  try {
    const cached = localStorage.getItem(RATE_CACHE_KEY)
    if (cached) {
      const parsed = JSON.parse(cached)
      if (Date.now() - parsed.t < RATE_TTL) {
        applyRates(parsed.rates)
        liveTime.value = parsed.time
        return
      }
    }
    const res = await fetch('https://open.er-api.com/v6/latest/KRW')
    if (!res.ok) return
    const data = await res.json()
    if (data.result !== 'success' || !data.rates) return
    // base = KRW，rates[X] = 1 KRW 能换多少 X；取倒数得 1 X = ? KRW
    const rates = {}
    for (const c of CURRENCIES) {
      if (data.rates[c.code]) rates[c.code] = 1 / data.rates[c.code]
    }
    applyRates(rates)
    liveTime.value = (data.time_last_update_utc || '').slice(0, 16).replace('T', ' ')
    localStorage.setItem(
      RATE_CACHE_KEY,
      JSON.stringify({ t: Date.now(), time: liveTime.value, rates })
    )
  } catch {
    /* 保留硬编码默认值 */
  }
}

function applyRates(rates) {
  for (const c of CURRENCIES) {
    if (rates[c.code]) c.rate = rates[c.code]
  }
  krw.value = Math.round((amount.value || 0) * cur.value.rate)
}

onMounted(loadRates)

// ===== 关税计算器 =====
const usd = ref(80)
const origin = ref('other')
const limit = computed(() => (origin.value === 'us' ? 200 : 150))
const isFree = computed(() => (usd.value || 0) <= limit.value)
const dutyStatus = computed(() => (isFree.value ? 'free' : 'pay'))
// 简化估算：超免税部分按 20% 关税 + 10% 附加税 ≈ 简单 20% 估算
const duty = computed(() => {
  const over = (usd.value || 0) - limit.value
  if (over <= 0) return 0
  const overKrw = over * 1400 // 1 USD ≈ 1400 KRW
  return Math.round(overKrw * 0.2)
})

useSeoMeta({
  title: '실용 도구 — cn2kr',
  description: '중국 직구·여행에 필요한 환율 계산기와 관세 계산기.',
})
</script>
