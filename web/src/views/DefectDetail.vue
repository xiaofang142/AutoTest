<template>
  <div v-loading="loading" class="defect-detail">
    <el-page-header @back="router.back()" :content="defect?.title || `缺陷 ${defect?.id || ''}`" />

    <el-card class="section-card">
      <template #header><span class="section-title">缺陷概览</span></template>
      <el-descriptions v-if="defect" :column="2" border>
        <el-descriptions-item label="严重级别">
          <el-tag :type="severityType">{{ defect.severity || '-' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="缺陷类型">{{ defect.type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ defect.title || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusType">{{ defect.status || 'open' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="发现时间">{{ defect.created_at || '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="暂无缺陷数据" />
    </el-card>

    <el-card class="section-card">
      <template #header><span class="section-title">复现步骤</span></template>
      <template v-if="defect?.step_context">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="操作">{{ defect.step_context.action || '-' }}</el-descriptions-item>
          <el-descriptions-item label="平台">{{ defect.step_context.platform || '-' }}</el-descriptions-item>
          <el-descriptions-item label="当前URL" :span="2">{{ defect.page_state?.current_url || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <el-empty v-else description="暂无步骤信息" />
    </el-card>

    <el-card class="section-card">
      <template #header><span class="section-title">页面证据</span></template>
      <el-collapse v-if="hasScreenshots" v-model="activeCollapse">
        <el-collapse-item title="截图对比" name="screenshots">
          <div class="screenshot-row">
            <div v-if="defect.screenshots?.before" class="screenshot-col">
              <p class="screenshot-label">操作前</p>
              <img :src="imgSrc(defect.screenshots.before)" alt="before" class="screenshot-img" />
            </div>
            <div v-if="defect.screenshots?.after" class="screenshot-col">
              <p class="screenshot-label">操作后</p>
              <img :src="imgSrc(defect.screenshots.after)" alt="after" class="screenshot-img" />
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
      <el-empty v-else description="暂无页面截图" />
    </el-card>

    <el-card class="section-card">
      <template #header><span class="section-title">控制台证据</span></template>
      <el-collapse v-if="hasConsoleLogs" v-model="activeCollapse">
        <el-collapse-item title="错误日志" name="console-errors">
          <el-table v-if="defect.console_logs?.errors?.length" :data="defect.console_logs.errors" border size="small">
            <el-table-column prop="message" label="错误信息" min-width="300" />
          </el-table>
          <el-empty v-else description="无错误日志" :image-size="60" />
        </el-collapse-item>
        <el-collapse-item title="警告日志" name="console-warnings">
          <el-table v-if="defect.console_logs?.warnings?.length" :data="defect.console_logs.warnings" border size="small">
            <el-table-column prop="message" label="警告信息" min-width="300" />
          </el-table>
          <el-empty v-else description="无警告日志" :image-size="60" />
        </el-collapse-item>
      </el-collapse>
      <el-empty v-else description="暂无控制台日志" />
    </el-card>

    <el-card class="section-card">
      <template #header><span class="section-title">网络证据</span></template>
      <el-table v-if="defect?.api_calls?.length" :data="defect.api_calls" border size="small">
        <el-table-column prop="method" label="方法" width="100" />
        <el-table-column prop="url" label="URL" min-width="250" />
        <el-table-column prop="status" label="状态码" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status >= 400 ? 'danger' : 'success'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无网络请求记录" />
    </el-card>

    <el-card class="section-card">
      <template #header><span class="section-title">根因分析</span></template>
      <template v-if="defect?.ai_analysis">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="摘要">{{ defect.ai_analysis.summary || '-' }}</el-descriptions-item>
          <el-descriptions-item label="根因">{{ defect.ai_analysis.root_cause || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <el-empty v-else description="暂无 AI 分析数据" />
    </el-card>

    <el-card class="section-card">
      <template #header><span class="section-title">修复建议</span></template>
      <template v-if="defect?.fix_suggestion">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="修复目标">{{ defect.fix_suggestion.target || '-' }}</el-descriptions-item>
          <el-descriptions-item label="修复描述">{{ defect.fix_suggestion.description || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <el-empty v-else description="暂无修复建议" />
    </el-card>

    <el-card class="section-card">
      <template #header><span class="section-title">回归建议</span></template>
      <template v-if="defect?.synthesis">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="缺陷数量">{{ defect.synthesis.bug_count ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="综合摘要">{{ defect.synthesis.summary || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <el-empty v-else description="暂无回归建议" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { defectApi } from "../api";

const route = useRoute();
const router = useRouter();
const did = route.params.id as string;
const loading = ref(false);
const defect = ref<any>(null);
const activeCollapse = ref<string[]>([]);

const severityType = computed(() => {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "info", critical: "danger" };
  return map[defect.value?.severity] || "info";
});

const statusType = computed(() => {
  const map: Record<string, string> = { open: "danger", fixed: "success", confirmed: "warning", closed: "info" };
  return map[defect.value?.status] || "info";
});

const hasScreenshots = computed(() => defect.value?.screenshots?.before || defect.value?.screenshots?.after);
const hasConsoleLogs = computed(() => {
  const cl = defect.value?.console_logs;
  return cl && (cl.errors?.length || cl.warnings?.length);
});

function imgSrc(data: string) {
  if (!data) return "";
  if (data.startsWith("data:")) return data;
  return `data:image/png;base64,${data}`;
}

onMounted(async () => {
  loading.value = true;
  try {
    const resp = await defectApi.get(did);
    defect.value = resp.data?.data ?? resp.data;
  } catch {
    defect.value = null;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.defect-detail {
  padding: 20px;
}
.section-card {
  margin-top: 16px;
}
.section-title {
  font-weight: 600;
  font-size: 15px;
}
.screenshot-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.screenshot-col {
  flex: 1;
  min-width: 200px;
}
.screenshot-label {
  font-weight: 600;
  margin-bottom: 8px;
  color: #606266;
}
.screenshot-img {
  max-width: 100%;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
</style>