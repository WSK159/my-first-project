<template>
  <div class="auth-box glass">
    <h2>{{ mode === "login" ? "欢迎回来" : "创建账号" }}</h2>
    <p style="color: var(--text-dim); font-size: 14px; text-align: center; margin: 8px 0 20px;">
      注册即送 ¥{{ (1000 / 100).toFixed(2) }} 体验余额
    </p>
    <div class="field">
      <label>用户名</label>
      <input v-model="username" placeholder="2-64 个字符" />
    </div>
    <div class="field">
      <label>密码</label>
      <input v-model="password" type="password" placeholder="至少 6 位" />
    </div>
    <button class="btn-primary" :disabled="busy" @click="submit">
      {{ busy ? "处理中…" : mode === "login" ? "登录" : "注册并登录" }}
    </button>
    <div class="row" style="justify-content: center; margin-top: 14px;">
      <button class="ghost-btn" @click="mode = mode === 'login' ? 'register' : 'login'">
        {{ mode === "login" ? "没有账号？去注册" : "已有账号？去登录" }}
      </button>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { api, setToken, state } from "../api";

const emit = defineEmits(["authed"]);
const mode = ref("register");
const username = ref("");
const password = ref("");
const error = ref("");
const busy = ref(false);

async function submit() {
  error.value = "";
  busy.value = true;
  try {
    const data = mode.value === "login"
      ? await api.login(username.value, password.value)
      : await api.register(username.value, password.value);
    setToken(data.access_token);
    state.balance = data.balance_cents;
    emit("authed");
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
</script>

