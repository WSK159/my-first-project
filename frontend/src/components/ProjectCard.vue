<template>
  <div class="project-card glass" @click="$router.push(`/projects/${project.id}`)">
    <div class="project-title">
      {{ project.title || `项目 #${project.id}` }}
      <span class="chip" :class="project.status">{{ statusText }}</span>
    </div>
    <div class="project-meta">
      {{ project.genre || "未分类" }} · {{ project.episode_count }} 集 ·
      {{ project.seconds_per_episode }}s/集 · {{ tierText }}
    </div>
    <div class="progress-track" style="margin: 10px 0 0;">
      <div class="progress-fill" :style="{ width: Math.round(project.progress * 100) + '%' }"></div>
    </div>
    <div class="project-meta" style="margin-top: 6px;">{{ project.stage }}</div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ project: { type: Object, required: true } });

const statusText = computed(() => ({ done: "已完成", running: "生成中", pending: "排队中", failed: "失败" }[props.project.status] || props.project.status));
const tierText = computed(() => ({ mock: "免费试跑", fast: "低成本", quality: "高质量" }[props.project.video_tier] || props.project.video_tier));
</script>

