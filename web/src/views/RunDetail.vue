<template>
  <div v-loading="loading">
    <el-page-header @back="$router.back()" :content="`执行: ${run?.id?.slice(0,16)}...`" />
    
    <el-descriptions :column="4" border style="margin-top:16px">
      <el-descriptions-item label="状态">
        <el-tag :type="run?.status === 'completed' ? 'success' : 'warning'">{{ run?.status }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="总步骤">{{ summary?.total }}</el-descriptions-item>
      <el-descriptions-item label="通过">
        <span style="color:#67c23a;font-weight:bold">{{ summary?.passed }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="失败">
        <span style="color:#f56c6c;font-weight:bold">{{ summary?.failed }}</span>
      </el-descriptions-item>
    </el-descriptions>

    <el-card v-if="defects.length" style="margin-top:16px">
      <template #header><span style="color:#f56c6c">🐛 缺陷 ({{ defects.length }})</span></template>
      <div v-for="d in defects" :key="d.id" style="margin-bottom:8px;cursor:pointer" @click="goDefect(d.id)">
        <el-tag :type="d.severity === 'high' ? 'danger' : 'warning'" size="small">{{ d.severity }}</el-tag>
        <span style="margin-left:8px">{{ d.title }}</span>
      </div>
    </el-card>

    <el-card style="margin-top:16px">
      <template #header><span>执行步骤</span></template>
      <el-timeline>
        <el-timeline-item v-for="s in steps" :key="s.step_index"
          :type="s.status === 'passed' ? 'success' : 'danger'"
          :timestamp="s.status">
          <div style="display:flex;justify-content:space-between;align-items:start">
            <div>
              <p><strong>步骤 {{ s.step_index }}:</strong> {{ s.action }}</p>
              <p v-if="s.console_errors" style="color:#e6a23c;font-size:12px">
                ⚠️ {{ s.console_errors }} 控制台错误
              </p>
              <p v-if="s.defect" style="color:#f56c6c;font-size:12px">🐛 产生缺陷</p>
            </div>
            <div v-if="s.screenshot" style="margin-left:16px">
              <el-image :src="s.screenshot" style="width:120px;height:80px;border-radius:4px;border:1px solid #eee"
                :preview-src-list="[s.screenshot]" preview-teleported />
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
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

const goDefect = (id: string) => router.push(`/defects/${id}`);

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
      total: run.value.total_cases,
      passed: run.value.passed_count,
      failed: run.value.failed_count,
    };

    const repResp = await reportApi.get(rid).catch(() => ({ data: { data: { steps: [] } } }));
    steps.value = (repResp.data.data.steps || []).map((s: any) => ({
      ...s,
      screenshot: s.screenshots?.after || s.screenshotAfter || "",
    }));
  } catch { /* silently handle */ }
  loading.value = false;
});
</script>
