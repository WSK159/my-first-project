<template>
  <main>
    <section class="hero">
      <h1>一句话，生成一部可投稿的短剧</h1>
      <p>
        完整小说 · 人物形象 · 分集剧本 · AI 视频 · 配音与音乐 · 字幕成片，
        从一句话到完整交付包，全自动。
      </p>
      <div class="steps">
        <span class="step-chip" v-for="s in ['小说', '人设图', '剧本', '视频', '配音', '成片']" :key="s">{{ s }}</span>
      </div>
    </section>

    <div v-if="!state.token" class="onboarding glass">
      <div class="onb-step" v-for="s in onboarding" :key="s.t">
        <div class="onb-icon">{{ s.icon }}</div>
        <div>
          <b>{{ s.t }}</b>
          <p>{{ s.d }}</p>
        </div>
      </div>
    </div>

    <AuthPanel v-if="!state.token" @authed="load" />

    <template v-else>
      <GeneratePanel />

      <section class="panel glass" style="margin-top: 22px;">
        <h2>🗂️ 任务中心（我的项目）</h2>
        <div v-if="loading" class="skeleton">加载中…</div>
        <div v-else-if="!projects.length" class="skeleton">还没有项目，输入一句话开始吧。</div>
        <div v-else class="grid">
          <ProjectCard v-for="p in projects" :key="p.id" :project="p" />
        </div>
      </section>
    </template>
  </main>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { api, state } from "../api";
import AuthPanel from "../components/AuthPanel.vue";
import GeneratePanel from "../components/GeneratePanel.vue";
import ProjectCard from "../components/ProjectCard.vue";

const projects = ref([]);
const loading = ref(false);
let timer = null;
const onboarding = [
  { icon: "💡", t: "第 1 步：输入一句话", d: "或点「完全随机」，AI 自动想题材、人设、剧情。" },
  { icon: "🚀", t: "第 2 步：一键生成", d: "选集数与档位，后台自动完成剧本/图片/视频/配音/合成。" },
  { icon: "📦", t: "第 3 步：下载交付包", d: "拿到的 zip 含成片、字幕、小说、封面与投稿规范。" },
];

async function load() {
  if (!state.token) return;
  loading.value = true;
  try {
    projects.value = await api.listProjects();
    const bal = await api.balance();
    state.balance = bal.balance_cents;
  } catch {
    /* 忽略 */
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  load();
  timer = setInterval(load, 8000);
});

onUnmounted(() => clearInterval(timer));
</script>
