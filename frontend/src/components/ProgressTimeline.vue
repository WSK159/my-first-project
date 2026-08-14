<template>
  <div>
    <div class="progress-track">
      <div class="progress-fill" :style="{ width: pct + '%' }"></div>
    </div>
    <div class="timeline">
      <div v-for="stage in stages" :key="stage.key" class="tl-item" :class="cls(stage.key)">
        <div class="tl-icon">{{ icon(stage.key) }}</div>
        <div>
          <div class="tl-name">{{ stage.label }}</div>
          <div class="tl-desc">{{ desc(stage.key) }}</div>
        </div>
      </div>
    </div>
    <div v-if="project.error" class="error-box">{{ project.error }}</div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ project: { type: Object, required: true } });

const stages = [
  { key: "series", label: "系列设定", icon: "📖" },
  { key: "characters", label: "角色设定", icon: "👤" },
  { key: "episodes", label: "分集剧本", icon: "📝" },
  { key: "shots", label: "分镜提示词", icon: "🎥" },
  { key: "images", label: "角色/场景图", icon: "🖼️" },
  { key: "videos", label: "视频生成", icon: "🎞️" },
  { key: "audio", label: "配音与音乐", icon: "🎵" },
  { key: "assembly", label: "合成与字幕", icon: "✂️" },
  { key: "delivery", label: "打包交付", icon: "📦" },
];

const order = stages.map((s) => s.key);
const pct = computed(() => Math.round((props.project.progress || 0) * 100));

function currentIndex() {
  const idx = order.indexOf(props.project.stage);
  return idx >= 0 ? idx : props.project.status === "done" ? order.length : 0;
}

function cls(key) {
  const idx = order.indexOf(key);
  const cur = currentIndex();
  if (props.project.status === "done") return "tl-done";
  if (idx < cur) return "tl-done";
  if (idx === cur) return "tl-active";
  return "tl-pending";
}

function icon(key) {
  return stages.find((s) => s.key === key)?.icon || "•";
}

function desc(key) {
  const map = {
    series: "一句话 → 题材/冲突引擎/季弧/视觉基调",
    characters: "角色欲望/矛盾/视觉锚点/音色",
    episodes: "每集钩子/冲突/反转/完整剧本",
    shots: "连续视频提示词（中/英）",
    images: "Seedream 角色参考图/场景/封面",
    videos: "Seedance 分段生成+尾帧衔接",
    audio: "Seed Audio 对白/旁白/环境/音乐",
    assembly: "FFmpeg 拼接+混音+字幕烧录",
    delivery: "final.mp4+小说+剧本+图集 zip",
  };
  return map[key] || "";
}
</script>

