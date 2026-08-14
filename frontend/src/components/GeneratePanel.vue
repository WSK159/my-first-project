<template>
  <div class="panel glass">
    <h2>⚡ 一键生成短剧</h2>
    <p class="hint">不会写剧情？选一个热门模板，或点「完全随机」，剩下的交给 AI。</p>
    <div v-if="templates.length" class="tpl-grid">
      <button
        v-for="t in templates"
        :key="t.name"
        class="tpl-chip"
        :class="{ active: selected === t.name }"
        @click="applyTemplate(t)"
      >
        {{ t.name }}
      </button>
    </div>
    <div class="field">
      <label>一句话灵感（留空则点击随机）</label>
      <textarea
        v-model="idea"
        placeholder="例如：被退婚的豪门千金十年后带着天才儿子回国复仇…"
      ></textarea>
    </div>
    <div class="row">
      <div class="field">
        <label>集数</label>
        <input v-model.number="episodes" type="number" min="1" max="60" />
      </div>
      <div class="field">
        <label>单集秒数</label>
        <input v-model.number="seconds" type="number" min="90" max="180" step="30" />
      </div>
      <div class="field">
        <label>生成档位</label>
        <select v-model="tier">
          <option value="mock">mock · 免费试跑</option>
          <option value="fast">fast · 低成本</option>
          <option value="quality">quality · 高质量</option>
        </select>
      </div>
    </div>
    <div class="row" style="justify-content: space-between; align-items: center; margin: 6px 0 16px;">
      <button class="btn-random" @click="randomize">🎲 完全随机</button>
      <button class="ghost-btn" :disabled="busy" @click="estimate">估算成本</button>
    </div>
    <div v-if="cost" class="cost-line">
      <span>预估费用</span>
      <b>¥{{ (cost / 100).toFixed(2) }}</b>
      <span v-if="cost > 0" class="cost-extra">
        约 {{ estimateMinutes }} 分钟出片 · 共 {{ totalMinutes }} 分钟正片
      </span>
      <span v-if="cost && cost > state.balance" class="cost-warn">⚠ 余额不足，请充值或改选 mock 档</span>
      <span v-if="quota && quota.available === true && quota.ok === false" class="cost-warn">
        ⚠ 火山 Seedance 套餐余量不足（缺 {{ Math.round(quota.deficit_tokens) }} tokens）
      </span>
    </div>
    <button class="btn-primary" :disabled="busy" @click="create">
      {{ busy ? "创建中…" : "🎬 开始一键生成" }}
    </button>
    <div v-if="error" class="error-box">{{ error }}</div>
    <p class="hint" style="margin-top: 10px;">
      小白提示：先选「mock · 免费试跑」验证全流程，满意后再用真实档生成可投稿成片。
    </p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api, state } from "../api";

const router = useRouter();
const idea = ref("");
const episodes = ref(1);
const seconds = ref(120);
const tier = ref("mock");
const cost = ref(0);
const error = ref("");
const busy = ref(false);
const templates = ref([]);
const selected = ref("");
const quota = ref(null);

const totalMinutes = computed(() => Math.round((episodes.value * seconds.value) / 60));
const estimateMinutes = computed(() => {
  if (!episodes.value || !seconds.value) return 0;
  const totalSeconds = episodes.value * seconds.value;
  const factor = tier.value === "mock" ? 0.4 : 4;
  return Math.max(1, Math.round((totalSeconds * factor) / 60));
});

function payload() {
  return {
    idea: idea.value,
    random_mode: !idea.value.trim(),
    genre: "",
    episode_count: episodes.value,
    seconds_per_episode: seconds.value,
    video_tier: tier.value,
  };
}

function randomize() {
  idea.value = "";
  selected.value = "";
  cost.value = 0;
  quota.value = null;
}

function applyTemplate(t) {
  selected.value = t.name;
  idea.value = t.idea;
  episodes.value = t.episode_count;
  seconds.value = t.seconds_per_episode;
  tier.value = t.tier || "fast";
  cost.value = 0;
  quota.value = null;
}

async function estimate() {
  error.value = "";
  try {
    const data = await api.estimate(payload());
    cost.value = data.frozen_cents;
    quota.value = data.quota || null;
  } catch (e) {
    error.value = e.message;
  }
}

async function create() {
  error.value = "";
  busy.value = true;
  try {
    if (!state.token) throw new Error("请先登录/注册");
    const project = await api.createProject(payload());
    router.push(`/projects/${project.id}`);
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

onMounted(async () => {
  try {
    templates.value = (await api.templates()).templates || [];
  } catch {
    /* 模板加载失败不影响生成 */
  }
});
</script>
