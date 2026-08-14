<template>
  <div>
    <div v-if="project.video_ready" class="video-wrap">
      <video :src="api.videoUrl(project.id, 1)" controls playsinline></video>
      <div class="video-caption">
        第 1 集预览（含配音/音乐/字幕）{{ metadata ? `· 全剧共 ${metadata.total_minutes} 分钟` : "" }}
      </div>
    </div>
    <div class="delivery">
      <div class="delivery-card glass">
        <div class="icon">📖</div>
        <h4>完整小说</h4>
        <p>可投稿的完整中文小说</p>
        <a class="dl-btn" :href="api.novelUrl(project.id)" target="_blank" rel="noopener">下载</a>
      </div>
      <div class="delivery-card glass">
        <div class="icon">🎬</div>
        <h4>全剧合集</h4>
        <p>{{ project.episode_count }} 集连续成片（约 {{ totalMinutes }} 分钟）</p>
        <a
          v-if="project.episode_count >= 2"
          class="dl-btn"
          :href="api.collectionUrl(project.id)"
          target="_blank"
          rel="noopener"
        >下载合集</a>
        <span v-else class="dl-btn disabled">不足 2 集</span>
      </div>
      <div class="delivery-card glass">
        <div class="icon">📦</div>
        <h4>全量交付包</h4>
        <p>视频+小说+剧本+角色图+封面+投稿规范</p>
        <a class="dl-btn" :href="api.archiveUrl(project.id)" target="_blank" rel="noopener">下载 zip</a>
      </div>
    </div>
    <div v-if="metadata" class="meta-line">
      <span>AI 生成内容 · 投稿前请勾选平台 AI 标识</span>
      <span v-if="metadata.total_minutes">全剧 {{ metadata.total_minutes }} 分钟 · {{ metadata.episode_count }} 集</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { api } from "../api";

const props = defineProps({
  project: { type: Object, required: true },
  metadata: { type: Object, default: null },
});

const totalMinutes = computed(() =>
  Math.round((props.project.episode_count * props.project.seconds_per_episode) / 60)
);
</script>
