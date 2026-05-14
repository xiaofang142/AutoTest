<template>
  <div>
    <h3>仪表盘</h3>
    <el-row :gutter="20">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 32px; font-weight: bold; color: #409eff">{{ stat.value }}</div>
            <div style="font-size: 14px; color: #999; margin-top: 8px">{{ stat.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-table :data="projects" style="margin-top: 20px" @row-click="goProject">
      <el-table-column prop="name" label="项目名称" />
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { projectApi } from "../api";

const router = useRouter();
const projects = ref<any[]>([]);
const stats = ref([
  { label: "项目数", value: 0 },
  { label: "今日执行", value: 0 },
  { label: "缺陷数", value: 0 },
  { label: "通过率", value: "0%" },
]);

const statusType = (s: string) => {
  const map: Record<string, string> = { completed: "success", running: "warning", failed: "danger", ready: "info" };
  return map[s] || "info";
};

const goProject = (row: any) => router.push(`/projects/${row.id}`);

onMounted(async () => {
  const resp = await projectApi.list();
  projects.value = resp.data.data.items;
  stats.value[0].value = projects.value.length;
});
</script>
