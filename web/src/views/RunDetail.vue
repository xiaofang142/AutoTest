<template>
  <div v-loading="loading">
    <el-page-header @back="$router.back()" :content="`执行: ${run?.id?.slice(0,16)}`" />

    <el-descriptions :column="5" border style="margin-top:16px">
      <el-descriptions-item label="状态">
        <el-tag :type="run?.status === 'completed' ? 'success' : 'warning'">{{ run?.status }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="总步骤">{{ summary.total }}</el-descriptions-item>
      <el-descriptions-item label="通过"><span style="color:#67c23a;font-weight:bold">{{ summary.passed }}</span></el-descriptions-item>
      <el-descriptions-item label="失败"><span style="color:#f56c6c;font-weight:bold">{{ summary.failed }}</span></el-descriptions-item>
      <el-descriptions-item label="缺陷"><el-tag type="danger" size="small">{{ defects.length }}</el-tag></el-descriptions-item>
    </el-descriptions>

    <!-- 缺陷概览 -->
    <el-card v-if="defects.length" style="margin-top:16px">
      <template #header><span style="color:#f56c6c">🐛 缺陷 ({{ defects.length }})</span></template>
      <div v-for="d in defects" :key="d.id" style="margin-bottom:8px;cursor:pointer" @click="goDefect(d.id)">
        <el-tag :type="d.severity === 'high' ? 'danger' : 'warning'" size="small">{{ d.severity }}</el-tag>
        <span style="margin-left:8px">{{ d.title }}</span>
      </div>
    </el-card>

    <!-- 步骤时间线 -->
    <el-card style="margin-top:16px">
      <template #header><span>📋 执行步骤详情</span></template>
      <el-timeline>
        <el-timeline-item v-for="s in steps" :key="s.step_index"
          :type="s.status === 'passed' ? 'success' : 'danger'"
          :timestamp="s.status === 'passed' ? '✅ 通过' : '❌ 失败'">
          <div>
            <strong>步骤 {{ s.step_index }}:</strong> {{ s.action }}
            <el-tag v-if="s.defect" type="danger" size="small" style="margin-left:8px">产生缺陷</el-tag>
            
            <!-- 截图 -->
            <div v-if="s.screenshots?.after" style="margin-top:8px">
              <el-image :src="s.screenshots.after" style="max-width:300px;border-radius:4px;border:1px solid #ddd;cursor:pointer"
                :preview-src-list="[s.screenshots.after]" preview-teleported />
            </div>

            <!-- 控制台日志 -->
            <div v-if="s.console_errors" style="margin-top:8px">
              <el-tag type="warning" size="small">⚠️ {{ s.console_errors }} 控制台异常</el-tag>
            </div>

            <!-- API 请求 -->
            <div v-if="s.api_calls" style="margin-top:4px">
              <el-tag type="info" size="small">📡 {{ s.api_calls }} 网络请求</el-tag>
            </div>

            <!-- 目标 URL -->
            <div v-if="s.target" style="margin-top:4px;font-size:12px;color:#999">
              URL: {{ s.target.slice(0,60) }}
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- LLM 配置 -->
    <el-card style="margin-top:16px">
      <template #header><span>⚙️ LLM 配置</span></template>
      <el-form :inline="true" size="small">
        <el-form-item label="状态">
          <el-tag :type="llmStatus === 'connected' ? 'success' : 'danger'" size="small">
            {{ llmStatus === 'connected' ? '已连接' : '未连接' }}
          </el-tag>
        </el-form-item>
        <el-form-item label="Provider">
          <el-select v-model="llmProvider" style="width:120px">
            <el-option value="openai" label="OpenAI" />
            <el-option value="anthropic" label="Anthropic" />
            <el-option value="glm" label="GLM" />
            <el-option value="custom" label="自定义" />
          </el-select>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="llmKey" type="password" show-password style="width:200px" placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="模型">
          <el-select v-model="llmModel" style="width:150px">
            <el-option value="gpt-4o" label="GPT-4o" />
            <el-option value="gpt-4o-mini" label="GPT-4o-mini" />
            <el-option value="claude-3-sonnet" label="Claude 3" />
            <el-option value="glm-4" label="GLM-4" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveLLM">保存</el-button>
          <el-button @click="testLLM">测试连接</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { runApi, reportApi, defectApi } from "../api";

const route = useRoute();
const router = useRouter();
const rid = route.params.id as string;
const loading = ref(false);
const run = ref<any>({});
const summary = ref<any>({});
const defects = ref<any[]>([]);
const steps = ref<any[]>([]);

const llmStatus = ref("disconnected");
const llmProvider = ref("openai");
const llmKey = ref("");
const llmModel = ref("gpt-4o");

const goDefect = (id: string) => router.push(`/defects/${id}`);

const saveLLM = async () => {
  try {
    const resp = await fetch("/api/v1/settings/llm", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: llmProvider.value,
        api_key: llmKey.value,
        extraction_model: llmModel.value,
      }),
    });
    const data = await resp.json();
    llmStatus.value = data.data?.status || "disconnected";
  } catch { /* */ }
};

const testLLM = async () => {
  try {
    const resp = await fetch("/api/v1/settings/llm/test", { method: "POST" });
    const data = await resp.json();
    llmStatus.value = data.data?.status || "error";
  } catch { llmStatus.value = "error"; }
};

onMounted(async () => {
  loading.value = true;
  try {
    const [rResp, dResp] = await Promise.all([
      runApi.get(rid).catch(() => ({ data: { data: {} } })),
      defectApi.list(rid).catch(() => ({ data: { data: { items: [] } } })),
    ]);
    run.value = rResp.data.data;
    defects.value = dResp.data.data.items;
    summary.value = {
      total: run.value.total_cases || 0,
      passed: run.value.passed_count || 0,
      failed: run.value.failed_count || 0,
    };

    const repResp = await reportApi.get(rid).catch(() => ({ data: { data: {} } }));
    const report = repResp.data.data;
    if (report.steps) {
      steps.value = report.steps;
    }
    summary.value = report.summary || summary.value;
  } catch { /* */ }
  loading.value = false;
});
</script>
