<template>
  <div class="panel glass">
    <h2>⚡ 一键生成短剧</h2>
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
        <input v-model.number="episodes" type="number" min="1" max="20" />
      </div>
      <div class="field">
        <label>单集秒数</label>
        <input v-model.number="seconds" type="number" min="15" max="180" step="15" />
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
    </div>
    <button class="btn-primary" :disabled="busy" @click="create">
      {{ busy ? "创建中…" : "🎬 开始一键生成" }}
    </button>
    <div v-if="error" class="error-box">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api, state } from "../api";

const router = useRouter();
const idea = ref("");
const episodes = ref(1);
const seconds = ref(60);
const tier = ref("mock");
const cost = ref(0);
const error = ref("");
const busy = ref(false);

function payload() {
  return {
    idea: idea.value,
    random_mode: !idea.value.trim(),
    episode_count: episodes.value,
    seconds_per_episode: seconds.value,
    video_tier: tier.value,
  };
}

function randomize() {
  idea.value = "";
  cost.value = 0;
}

async function estimate() {
  error.value = "";
  try {
    const data = await api.estimate(payload());
    cost.value = data.frozen_cents;
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
</script>

