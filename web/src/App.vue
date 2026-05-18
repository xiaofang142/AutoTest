<template>
  <el-container style="min-height: 100vh">
    <el-aside width="220px" style="background: #1a1a2e; color: #fff">
      <div style="padding: 20px; font-size: 18px; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.1)">
        AutoTest
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#1a1a2e"
        text-color="rgba(255,255,255,0.7)"
        active-text-color="#409eff"
        style="border: none"
      >
        <el-menu-item index="/">
          <span>🏠 新建自动测试</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <span>📋 测试任务</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <span>📖 知识/文档</span>
        </el-menu-item>
        <el-menu-item index="/projects">
          <span>📁 项目管理</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <span>⚙️ 设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="background: #fff; border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between">
        <h2 style="margin: 0; font-size: 16px; color: #333">AI 自动化测试平台</h2>
        <el-tag type="success" size="small" v-if="healthy">系统正常</el-tag>
        <el-tag type="danger" size="small" v-else>系统异常</el-tag>
      </el-header>
      <el-main style="background: #f5f7fa">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import axios from "axios";

const healthy = ref(false);
onMounted(async () => {
  try {
    const resp = await axios.get("/health");
    healthy.value = resp.data.status === "ok";
  } catch {
    healthy.value = false;
  }
});
</script>
