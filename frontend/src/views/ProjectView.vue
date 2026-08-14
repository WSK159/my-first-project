<template>
  <main>
    <router-link to="/" class="back-link">← 返回项目列表</router-link>
    <div v-if="!project" class="skeleton">加载中…</div>
    <template v-else>
      <div class="panel glass">
        <h2>{{ project.title || `项目 #${project.id}` }}</h2>
        <p style="color: var(--text-dim); margin-bottom: 8px;">
          {{ project.genre || "未分类" }} · {{ project.episode_count }} 集 ·
          {{ project.seconds_per_episode }}s/集 · {{ project.idea || "随机生成" }}
        </p>
        <ProgressTimeline :project="project" />
        <DeliveryPanel v-if="project.status === 'done'" :project="project" />
      </div>
    </template>
  </main>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import DeliveryPanel from "../components/DeliveryPanel.vue";
import ProgressTimeline from "../components/ProgressTimeline.vue";

const route = useRoute();
const project = ref(null);
let timer = null;

async function load() {
  try {
    project.value = await api.getProject(route.params.id);
    if (!["done", "failed"].includes(project.value.status)) {
      timer = setTimeout(load, 2500);
    }
  } catch {
    project.value = null;
  }
}

onMounted(load);
onUnmounted(() => clearTimeout(timer));
</script>

