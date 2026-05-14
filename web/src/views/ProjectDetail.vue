<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/projects')" :content="project?.name" />
    <el-tabs v-model="tab" style="margin-top: 20px">
      <el-tab-pane label="概览" name="overview">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目ID">{{ project?.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(project?.status)">{{ project?.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="平台">{{ project?.platforms?.join(", ") }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ project?.created_at }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
      <el-tab-pane label="文档" name="docs">
        <el-button @click="showAddDoc = true" size="small">添加文档</el-button>
        <el-table :data="documents" style="margin-top: 10px">
          <el-table-column prop="url" label="URL" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <el-button @click="handleParse" type="primary" size="small" style="margin-top: 10px">解析文档</el-button>

        <el-dialog v-model="showAddDoc" title="添加文档" width="400px">
          <el-input v-model="docUrl" placeholder="文档URL" />
          <template #footer>
            <el-button @click="showAddDoc = false">取消</el-button>
            <el-button type="primary" @click="handleAddDoc">添加</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
      <el-tab-pane label="执行" name="runs">
        <el-button @click="handleRun" type="primary" size="small">启动执行</el-button>
        <el-table :data="runs" style="margin-top: 10px" @row-click="goRun">
          <el-table-column prop="name" label="执行名称" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="total_cases" label="用例数" width="80" />
          <el-table-column prop="created_at" label="执行时间" width="180" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { projectApi, documentApi, runApi } from "../api";

const route = useRoute();
const router = useRouter();
const pid = route.params.id as string;
const loading = ref(false);
const tab = ref("overview");
const project = ref<any>({});
const documents = ref<any[]>([]);
const runs = ref<any[]>([]);
const showAddDoc = ref(false);
const docUrl = ref("");

const statusType = (s: string) => {
  const map: Record<string, string> = { completed: "success", running: "warning", failed: "danger" };
  return map[s] || "info";
};
const goRun = (row: any) => router.push(`/runs/${row.id}`);

const handleAddDoc = async () => {
  await documentApi.add(pid, { url: docUrl.value, type: "prd" });
  showAddDoc.value = false;
  docUrl.value = "";
  ElMessage.success("文档已添加");
  const resp = await documentApi.list(pid);
  documents.value = resp.data.data.items;
};

const handleParse = async () => {
  await documentApi.parse(pid);
  ElMessage.success("解析已触发");
};

const handleRun = async () => {
  const resp = await runApi.create(pid, { platforms: ["web"] });
  ElMessage.success("执行已创建");
  const runsResp = await runApi.progress(resp.data.data.id);
  const listResp = await projectApi.list();
  runs.value = listResp.data.data.items;
};

onMounted(async () => {
  loading.value = true;
  const pResp = await projectApi.get(pid);
  project.value = pResp.data.data;
  const dResp = await documentApi.list(pid);
  documents.value = dResp.data.data.items;
  loading.value = false;
});
</script>
