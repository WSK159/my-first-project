<template>
  <div class="app-shell">
    <header class="topbar glass">
      <router-link to="/" class="brand">
        <span class="brand-icon">🎬</span>
        <span class="brand-text">AI短剧工坊</span>
      </router-link>
      <div class="topbar-right">
        <span v-if="state.token" class="balance">余额 ¥{{ (state.balance / 100).toFixed(2) }}</span>
        <button v-if="state.token" class="ghost-btn" @click="logout">退出</button>
        <router-link v-else to="/" class="ghost-btn">登录 / 注册</router-link>
      </div>
    </header>
    <router-view />
    <footer class="footer">AI 生成内容仅供创作参考 · 投稿请遵守平台内容规范</footer>
  </div>
</template>

<script setup>
import { onMounted } from "vue";
import { api, clearToken, state } from "./api";

async function refreshBalance() {
  if (!state.token) return;
  try {
    const data = await api.balance();
    state.balance = data.balance_cents;
  } catch {
    /* token 失效时静默 */
  }
}

function logout() {
  clearToken();
  window.location.href = "/";
}

onMounted(refreshBalance);
</script>

