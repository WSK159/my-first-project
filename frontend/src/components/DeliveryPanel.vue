<template>
  <div>
    <div v-if="project.video_ready" class="video-wrap">
      <video :src="api.videoUrl(project.id, 1)" controls playsinline></video>
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
        <h4>成片视频</h4>
        <p>第 1 集成片（含配音/音乐/字幕）</p>
        <a class="dl-btn" :href="api.videoUrl(project.id, 1)" target="_blank" rel="noopener">下载</a>
      </div>
      <div class="delivery-card glass">
        <div class="icon">📦</div>
        <h4>全量交付包</h4>
        <p>视频+小说+剧本+角色图+封面+元数据</p>
        <a class="dl-btn" :href="api.archiveUrl(project.id)" target="_blank" rel="noopener">下载 zip</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { api } from "../api";
defineProps({ project: { type: Object, required: true } });
</script>

