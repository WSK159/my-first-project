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

    <AuthPanel v-if="!state.token" @authed="load" />

    <template v-else>
      <GeneratePanel />

      <section class="panel glass" style="margin-top: 22px;">
        <h2>🗂️ 我的项目</h2>
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
import { onMounted, ref } from "vue";
import { api, state } from "../api";
import AuthPanel from "../components/AuthPanel.vue";
import GeneratePanel from "../components/GeneratePanel.vue";
import ProjectCard from "../components/ProjectCard.vue";

const projects = ref([]);
const loading = ref(false);

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

onMounted(load);
</script>

