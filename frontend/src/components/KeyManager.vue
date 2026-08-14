<template>
  <section class="panel glass" style="margin-top: 22px;">
    <h2>🔑 密钥管理（BYOK · 可选）</h2>
    <p class="hint">
      有 API Key 时填在这里，你的项目会优先使用你自己的密钥（加密保存，仅你可见）。
      不填则使用平台配置的密钥；mock 档无需任何密钥。
    </p>
    <div class="key-grid">
      <div v-for="k in keys" :key="k.provider" class="key-row">
        <div class="key-info">
          <b>{{ k.label }}</b>
          <span class="key-state" :class="{ on: k.configured }">
            {{ k.configured ? `已配置 ${k.api_key_masked}` : "未配置" }}
          </span>
        </div>
        <div class="key-actions">
          <input
            v-model="inputs[k.provider]"
            type="password"
            :placeholder="k.configured ? '输入新 Key 覆盖' : '粘贴 API Key'"
            autocomplete="off"
          />
          <button class="ghost-btn" :disabled="busy" @click="save(k.provider)">保存</button>
          <button v-if="k.configured" class="ghost-btn danger" :disabled="busy" @click="remove(k.provider)">清除</button>
        </div>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { api } from "../api";

const keys = ref([]);
const inputs = reactive({});
const busy = ref(false);
const error = ref("");

async function load() {
  try {
    keys.value = await api.keysList();
  } catch {
    keys.value = [];
  }
}

async function save(provider) {
  const value = (inputs[provider] || "").trim();
  if (!value) return;
  busy.value = true;
  error.value = "";
  try {
    await api.saveKey(provider, value);
    inputs[provider] = "";
    await load();
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

async function remove(provider) {
  busy.value = true;
  error.value = "";
  try {
    await api.deleteKey(provider);
    await load();
  } catch (e) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}

onMounted(load);
</script>
