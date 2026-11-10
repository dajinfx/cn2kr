<template>
  <div class="container">
    <div class="tools-hero">
      <h1>실용 도구</h1>
      <p>중국 직구·여행에 필요한 계산기를 모았습니다</p>
    </div>

    <div class="tools-grid">
      <!-- 汇率计算器 -->
      <section class="tool-card">
        <h2 class="tool-title">위안(CNY) ↔ 원(KRW) 환율</h2>
        <p class="tool-note">환율은 대략적인 값입니다. 실제 결제 환율과 다를 수 있습니다.</p>
        <label class="tool-field">
          <span>위안 (CNY)</span>
          <input v-model.number="cny" type="number" min="0" step="1" placeholder="예: 100" />
        </label>
        <div class="tool-swap" aria-hidden="true">⇅</div>
        <label class="tool-field">
          <span>원 (KRW)</span>
          <input v-model.number="krw" type="number" min="0" step="100" placeholder="예: 19000" />
        </label>
        <p class="tool-result">
          기준 환율: 1 위안 ≈ <strong>{{ rate.toLocaleString() }}</strong> 원
          <button class="tool-rate-edit" type="button" @click="showRateEdit = !showRateEdit">환율 수정</button>
        </p>
        <label v-if="showRateEdit" class="tool-field">
          <span>환율 (1 CNY = ? KRW)</span>
          <input v-model.number="rate" type="number" min="1" step="1" />
        </label>
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
import { ref, computed, watch } from 'vue'

// 汇率计算器
const rate = ref(190) // 1 CNY ≈ 190 KRW
const cny = ref(100)
const krw = ref(19000)
const showRateEdit = ref(false)

watch(cny, (v) => {
  if (v !== null && v !== undefined) krw.value = Math.round(v * rate.value)
})
watch(krw, (v) => {
  if (v !== null && v !== undefined) cny.value = Math.round((v / rate.value) * 100) / 100
})
watch(rate, (v) => {
  if (cny.value !== null) krw.value = Math.round(cny.value * v)
})

// 关税计算器
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
