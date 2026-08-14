<template>
  <main>
    <router-link to="/" class="back-link">← 返回项目列表</router-link>
    <div v-if="!project" class="skeleton">加载中…</div>
    <template v-else>
      <div class="panel glass">
        <h2>{{ project.title || `项目 #${project.id}` }}</h2>
        <p style="color: var(--text-dim); margin-bottom: 8px;">
          {{ project.genre || "未分类" }} · {{ project.episode_count }} 集 ·
          {{ project.seconds_per_episode }}s/集 · 预计正片 {{ totalMinutes }} 分钟 ·
          {{ project.idea || "随机生成" }}
        </p>
        <ProgressTimeline :project="project" :last-event="lastEvent" />

        <div v-if="project.status === 'partial' || project.status === 'failed'" class="resume-bar">
          <span>有 {{ failedCount }} 集未完成，可继续生成（已完成部分自动跳过）。</span>
          <button class="btn-primary" :disabled="resuming" @click="resume">
            {{ resuming ? "继续中…" : "▶ 继续生成" }}
          </button>
        </div>

        <EpisodeGrid
          v-if="project.video_ready || project.status === 'running' || project.status === 'partial'"
          :project="project"
          :episodes="episodeRows"
        />

        <DeliveryPanel v-if="project.status === 'done' || project.status === 'partial'" :project="project" :metadata="metadata" />
      </div>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import DeliveryPanel from "../components/DeliveryPanel.vue";
import EpisodeGrid from "../components/EpisodeGrid.vue";
import ProgressTimeline from "../components/ProgressTimeline.vue";

const route = useRoute();
const project = ref(null);
const episodeRows = ref([]);
const metadata = ref(null);
const lastEvent = ref("");
const resuming = ref(false);
let timer = null;
let es = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let stopped = false;

const totalMinutes = computed(() => {
  if (!project.value) return 0;
  return Math.round((project.value.episode_count * project.value.seconds_per_episode) / 60);
});

const failedCount = computed(() => episodeRows.value.filter((e) => e.failed.length).length);

async function load() {
  try {
    project.value = await api.getProject(route.params.id);
    try {
      const data = await api.episodesStatus(route.params.id);
      episodeRows.value = data.episodes || [];
    } catch {
      /* 分集状态不可用时忽略 */
    }
    if (["done", "partial"].includes(project.value.status)) {
      try {
        metadata.value = await api.metadata(route.params.id);
      } catch {
        metadata.value = null;
      }
    }
    if (["done", "failed"].includes(project.value.status)) {
      stopped = true;
      closeSSE();
      return;
    }
    if (project.value.status === "partial") {
      stopped = true;
      closeSSE();
    }
    schedulePoll();
  } catch {
    project.value = null;
  }
}

function schedulePoll() {
  if (stopped) return;
  timer = setTimeout(load, 5000);
}

function openSSE() {
  closeSSE();
  if (stopped) return;
  try {
    es = new EventSource(api.eventsUrl(route.params.id));
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.message) lastEvent.value = data.message;
        if (data.type === "done" || (data.status && ["done", "failed"].includes(data.status))) {
          stopped = true;
          closeSSE();
          load();
        }
      } catch {
        /* 忽略坏事件 */
      }
    };
    es.onerror = () => {
      closeSSE();
      if (stopped) return;
      reconnectAttempts += 1;
      const delay = Math.min(1000 * 2 ** Math.min(reconnectAttempts, 5), 30000);
      reconnectTimer = setTimeout(openSSE, delay);
    };
  } catch {
    schedulePoll();
  }
}

function closeSSE() {
  if (es) {
    es.close();
    es = null;
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

async function resume() {
  resuming.value = true;
  try {
    await api.resume(route.params.id);
    stopped = false;
    lastEvent.value = "已重新启动生成…";
    openSSE();
    load();
  } catch (e) {
    lastEvent.value = `继续生成失败：${e.message}`;
  } finally {
    resuming.value = false;
  }
}

onMounted(() => {
  load();
  openSSE();
});

onUnmounted(() => {
  stopped = true;
  closeSSE();
  if (timer) clearTimeout(timer);
});
</script>
