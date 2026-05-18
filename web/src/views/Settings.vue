<template>
  <div>
    <h3>系统设置</h3>

    <!-- 后端连接状态 -->
    <el-alert
      v-if="!healthy"
      title="后端服务未连接"
      type="error"
      :closable="false"
      show-icon
      description="前端无法连接到后端 API (localhost:8000)，请确认后端已启动：source .venv311/bin/activate && uvicorn app.main:app --reload --port 8000"
      style="margin-bottom: 16px"
    />

    <el-row :gutter="16">
      <!-- LLM 配置 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>🤖 AI 模型配置</span>
              <el-tag :type="statusTag" size="small" effect="dark">{{ statusText }}</el-tag>
            </div>
          </template>

          <el-form label-position="top" size="default">
            <el-form-item label="API Key">
              <el-input
                v-model="form.api_key"
                placeholder="sk-... 留空则使用规则引擎"
                :clearable="true"
              />
              <div style="font-size: 12px; color: #909399; margin-top: 4px">
                留空则使用规则引擎，无需任何外部服务，所有核心功能正常
              </div>
            </el-form-item>

            <el-form-item label="API Base URL">
              <el-input v-model="form.api_base" placeholder="https://api.openai.com/v1" />
            </el-form-item>

            <el-form-item label="模型名称">
              <el-input v-model="form.model" placeholder="gpt-4o / deepseek-v4-flash / ..." />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="handleSave" :loading="saving" style="margin-right: 8px">
                保存
              </el-button>
              <el-button @click="handleTest" :loading="testing" style="margin-right: 8px">
                测试连接
              </el-button>
              <el-button @click="handleReset">清空 Key（切回规则引擎）</el-button>
            </el-form-item>

            <div v-if="testResult" :style="{ color: testResultColor, marginTop: '8px', fontSize: '13px' }">
              {{ testResult }}
            </div>
          </el-form>
        </el-card>
      </el-col>

      <!-- 状态 -->
      <el-col :span="8">
        <el-card>
          <template #header><span>📊 系统状态</span></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="API 服务">
              <el-tag :type="healthy ? 'success' : 'danger'" size="small">{{ healthy ? '运行中' : '异常' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="AI 引擎">
              <el-tag :type="llmAcked ? 'success' : 'info'" size="small">{{ llmAcked ? '已配置' : '规则引擎' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="数据存储">
              <el-tag size="small">SQLite</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="执行器">
              <el-tag size="small">Web (Playwright)</el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="form.api_key" label="当前 Key">
              <span style="font-size:12px;word-break:break-all">{{ form.api_key }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";

const healthy = ref(false);
const testing = ref(false);
const saving = ref(false);
const testResult = ref("");
const testResultColor = ref("#909399");
const llmStatus = ref("disconnected");

const form = reactive({
  api_key: "",
  api_base: "https://api.deepseek.com",
  model: "deepseek-v4-flash",
});

const statusTag = computed(() => {
  const m: Record<string, string> = { connected: "success", disconnected: "info", error: "danger" };
  return m[llmStatus.value] || "info";
});
const statusText = computed(() => {
  const m: Record<string, string> = { connected: "已连接", disconnected: "未配置", error: "连接失败" };
  return m[llmStatus.value] || "未知";
});
const llmAcked = computed(() => llmStatus.value === "connected");

const handleSave = async () => {
  saving.value = true;
  try {
    const api_base = form.api_base || "";
    const model = form.model || "";
    await axios.put("/api/v1/settings/llm", {
      api_key: form.api_key,
      api_base,
      extraction_model: model,
      analysis_model: model,
    });
    ElMessage.success("配置已保存");
  } catch (e: any) {
    ElMessage.error("保存失败: " + (e.response?.data?.message || e.message));
  }
  saving.value = false;
};

const handleTest = async () => {
  testing.value = true;
  testResult.value = "测试中...";
  testResultColor.value = "#909399";
  try {
    const resp = await axios.post("/api/v1/settings/llm/test");
    const data = resp.data.data;
    testResult.value = data.message;
    testResultColor.value = data.status === "connected" ? "#67c23a" : "#f56c6c";
    llmStatus.value = data.status;
  } catch (e: any) {
    testResult.value = "请求失败: " + e.message;
    testResultColor.value = "#f56c6c";
  }
  testing.value = false;
};

const handleReset = () => {
  form.api_key = "";
  form.api_base = "https://api.deepseek.com";
  form.model = "deepseek-v4-flash";
  llmStatus.value = "disconnected";
  testResult.value = "";
  ElMessage.info("已清空 Key，系统将使用规则引擎");
};

onMounted(async () => {
  try {
    const [hlth, cfgResp] = await Promise.all([
      axios.get("/health").catch(() => null),
      axios.get("/api/v1/settings/llm").catch(() => null),
    ]);

    healthy.value = hlth?.data?.status === "ok";

    if (cfgResp?.data?.data) {
      const c = cfgResp.data.data;
      form.api_key = c.api_key || "";
      form.api_base = c.api_base || "https://api.deepseek.com";
      form.model = c.extraction_model || "deepseek-v4-flash";
      llmStatus.value = c.status || "disconnected";
    }
  } catch { /* */ }
});
</script>
