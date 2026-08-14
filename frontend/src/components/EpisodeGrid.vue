<template>
  <div class="episode-grid-wrap">
    <h3>🎬 分集状态（{{ doneCount }}/{{ episodes.length }} 集完成）</h3>
    <div class="episode-grid">
      <div
        v-for="ep in episodes"
        :key="ep.episode"
        class="ep-card"
        :class="{ ok: ep.has_video, bad: ep.failed.length }"
      >
        <div class="ep-head">
          <span class="ep-no">第 {{ ep.episode }} 集</span>
          <span class="ep-state">
            {{ ep.has_video ? "✓ 成片" : ep.failed.length ? "✗ 失败" : "… 生成中" }}
          </span>
        </div>
        <div class="ep-meta">
          {{ ep.duration_seconds ? Math.round(ep.duration_seconds) + "s" : "—" }}
          <span v-if="ep.failed.length" class="ep-fail">失败步骤：{{ ep.failed.join("、") }}</span>
        </div>
        <a
          v-if="ep.has_video"
          class="dl-btn small"
          :href="api.videoUrl(project.id, ep.episode)"
          target="_blank"
          rel="noopener"
        >
          下载
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { api } from "../api";

const props = defineProps({
  project: { type: Object, required: true },
  episodes: { type: Array, default: () => [] },
});

const doneCount = computed(() => props.episodes.filter((e) => e.has_video).length);
</script>
