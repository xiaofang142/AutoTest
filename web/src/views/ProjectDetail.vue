<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/projects')" :content="project?.name" />
    <el-tabs v-model="tab" style="margin-top: 20px">
      
      <!-- 概览 -->
      <el-tab-pane label="概览" name="overview">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="项目ID">{{ project?.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(project?.status)">{{ project?.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="平台">{{ project?.platforms?.join(", ") }}</el-descriptions-item>
          <el-descriptions-item label="入口地址">
            <template v-for="e in project?.entries" :key="e.platform">
              <div>{{ e.platform }}: {{ e.url || e.app_package }}</div>
            </template>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ project?.created_at?.slice(0,19) }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>

      <!-- 文档 -->
      <el-tab-pane label="文档" name="docs">
        <el-button @click="showAddDoc = true" size="small" type="primary">+ 添加文档</el-button>
        <el-button @click="handleParse" size="small" :disabled="!documents.length">解析文档</el-button>
        <el-table :data="documents" style="margin-top: 10px">
          <el-table-column prop="url" label="文档来源" min-width="200" />
          <el-table-column prop="type" label="类型" width="90" />
          <el-table-column prop="rule_count" label="规则数" width="80" align="center" />
          <el-table-column prop="status" label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="showAddDoc" title="添加文档" width="480px">
          <el-form label-width="80px">
            <el-form-item label="文档类型">
              <el-radio-group v-model="docType">
                <el-radio value="prd">需求文档</el-radio>
                <el-radio value="ui_spec">UI规范</el-radio>
                <el-radio value="api_doc">API文档</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="添加方式">
              <el-radio-group v-model="docMode">
                <el-radio value="url">URL导入</el-radio>
                <el-radio value="file">上传文件</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="docMode === 'url'" label="文档URL">
              <el-input v-model="docUrl" placeholder="https://example.com/prd.md" />
            </el-form-item>
            <el-form-item v-if="docMode === 'file'" label="上传文件">
              <el-upload drag :auto-upload="false" :on-change="handleFileChange" :limit="1">
                <el-icon class="el-icon--upload" /><span>拖拽 .md 文件到此处</span>
              </el-upload>
              <div v-if="fileName" style="margin-top:8px;color:#409eff">📄 {{ fileName }}</div>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showAddDoc = false">取消</el-button>
            <el-button type="primary" @click="handleAddDoc">添加</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- 场景 -->
      <el-tab-pane label="场景" name="scenarios">
        <el-button @click="handleGenerate" type="primary" size="small">生成测试场景</el-button>
        <el-table :data="scenarios" style="margin-top:10px">
          <el-table-column prop="name" label="场景名称" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="business_line" label="业务线" width="120" />
          <el-table-column prop="status" label="状态" width="90" />
        </el-table>
      </el-tab-pane>

      <!-- 执行 -->
      <el-tab-pane label="执行" name="runs">
        <el-button @click="handleRun" type="primary" size="small">🚀 启动执行</el-button>
        <el-table :data="runs" style="margin-top:10px" @row-click="goRun">
          <el-table-column prop="name" label="执行名称" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="total_cases" label="用例数" width="80" align="center" />
          <el-table-column prop="created_at" label="时间" width="170">
            <template #default="{ row }">{{ row.created_at?.slice(0,19) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { projectApi, documentApi, scenarioApi, runApi } from "../api";

const route = useRoute();
const router = useRouter();
const pid = route.params.id as string;
const loading = ref(false);
const tab = ref("overview");
const project = ref<any>({});
const documents = ref<any[]>([]);
const scenarios = ref<any[]>([]);
const runs = ref<any[]>([]);
const showAddDoc = ref(false);
const docUrl = ref("");
const docType = ref("prd");
const docMode = ref("url");
const fileName = ref("");
const fileContent = ref("");

const statusTag = (s: string) => {
  const m: Record<string, string> = { completed: "success", running: "warning", failed: "danger", ready: "info" };
  return m[s] || "info";
};

const goRun = (row: any) => router.push(`/runs/${row.id}`);

const handleFileChange = (file: any) => {
  fileName.value = file.name;
  const reader = new FileReader();
  reader.onload = (e) => { fileContent.value = e.target?.result as string; };
  reader.readAsDataURL(file.raw);
};

const handleAddDoc = async () => {
  try {
    if (docMode.value === "url") {
      await documentApi.add(pid, { url: docUrl.value, type: docType.value });
    } else {
      await documentApi.add(pid, { url: fileName.value, type: docType.value });
    }
    showAddDoc.value = false;
    docUrl.value = "";
    fileName.value = "";
    ElMessage.success("文档已添加");
    const resp = await documentApi.list(pid);
    documents.value = resp.data.data.items;
  } catch (e: any) {
    ElMessage.error("添加失败: " + (e.response?.data?.message || e.message));
  }
};

const handleParse = async () => {
  try {
    await documentApi.parse(pid);
    ElMessage.success("解析已触发");
  } catch (e: any) {
    ElMessage.error("解析失败: " + (e.response?.data?.message || e.message));
  }
};

const handleGenerate = async () => {
  try {
    await scenarioApi.generate(pid, ["web"]);
    ElMessage.success("场景生成完成");
    const resp = await scenarioApi.list(pid);
    scenarios.value = resp.data.data.items;
  } catch (e: any) {
    ElMessage.error("生成失败: " + (e.response?.data?.message || e.message));
  }
};

const handleRun = async () => {
  try {
    const resp = await runApi.create(pid, { platforms: ["web"], name: "全自动回归测试" });
    ElMessage.success("执行已创建: " + resp.data.data.id.slice(0, 16));
    const hist = await runApi.list(pid);
    runs.value = hist.data.data.items;
  } catch (e: any) {
    ElMessage.error("创建失败: " + (e.response?.data?.message || e.message));
  }
};

onMounted(async () => {
  loading.value = true;
  try {
    const [pResp, dResp, sResp, rResp] = await Promise.all([
      projectApi.get(pid), documentApi.list(pid), scenarioApi.list(pid),
      runApi.list(pid).catch(() => ({ data: { data: { items: [] } } })),
    ]);
    project.value = pResp.data.data;
    documents.value = dResp.data.data.items;
    scenarios.value = sResp.data.data.items;
    runs.value = rResp.data.data.items;
  } catch (e: any) {
    ElMessage.error("加载失败: " + e.message);
  }
  loading.value = false;
});
</script>
