<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <h3>项目管理</h3>
      <el-button type="primary" @click="showCreate = true">新建项目</el-button>
    </div>

    <el-table :data="projects" @row-click="goDetail">
      <el-table-column prop="name" label="项目名称" />
      <el-table-column prop="platforms" label="平台" width="200">
        <template #default="{ row }">
          <el-tag v-for="p in row.platforms" :key="p" size="small" style="margin-right: 4px">{{ p }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" type="danger" @click.stop="handleDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="新建项目" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="项目名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="平台">
          <el-checkbox-group v-model="form.platforms">
            <el-checkbox value="web">Web</el-checkbox>
            <el-checkbox value="android">Android</el-checkbox>
            <el-checkbox value="ios">iOS</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="入口地址">
          <el-input v-model="form.url" placeholder="https://example.com" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { projectApi } from "../api";

const router = useRouter();
const projects = ref<any[]>([]);
const showCreate = ref(false);
const form = ref({ name: "", platforms: ["web"], url: "" });
const statusType = (s: string) => {
  const map: Record<string, string> = { completed: "success", running: "warning", failed: "danger", ready: "info" };
  return map[s] || "info";
};

const goDetail = (row: any) => router.push(`/projects/${row.id}`);

const handleCreate = async () => {
  await projectApi.create({
    name: form.value.name,
    platforms: form.value.platforms,
    entries: [{ platform: "web", url: form.value.url }],
  });
  showCreate.value = false;
  ElMessage.success("项目创建成功");
  const resp = await projectApi.list();
  projects.value = resp.data.data.items;
};

const handleDelete = async (id: string) => {
  await projectApi.delete(id);
  ElMessage.success("已删除");
  const resp = await projectApi.list();
  projects.value = resp.data.data.items;
};

onMounted(async () => {
  const resp = await projectApi.list();
  projects.value = resp.data.data.items;
});
</script>
