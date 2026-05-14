<template>
  <div v-loading="loading">
    <el-page-header @back="$router.back()" :content="`缺陷: ${defect?.id}`" />
    <el-card style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between">
          <span><el-tag :type="severityType">{{ defect?.severity }}</el-tag> {{ defect?.title }}</span>
        </div>
      </template>
      <el-descriptions :column="2">
        <el-descriptions-item label="类型">{{ defect?.type }}</el-descriptions-item>
        <el-descriptions-item label="发现时间">{{ defect?.created_at }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header><span>AI 根因分析</span></template>
      <div v-if="defect?.ai_analysis?.root_cause">
        <p><strong>根因：</strong>{{ defect.ai_analysis.root_cause }}</p>
        <p><strong>置信度：</strong>{{ defect.ai_analysis.confidence }}</p>
      </div>
      <div v-else style="color: #999">暂无 AI 分析数据</div>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header><span>证据链</span></template>
      <div v-if="defect?.evidence_chains?.length">
        <div v-for="chain in defect.evidence_chains" :key="chain.chain_id" style="margin-bottom: 16px">
          <el-timeline>
            <el-timeline-item v-for="(ev, i) in chain.propagation" :key="i" :type="i === 0 ? 'danger' : 'primary'">
              <p>{{ ev.dimension }}: {{ ev.event }}</p>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
      <div v-else style="color: #999">暂无证据链</div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { defectApi } from "../api";

const route = useRoute();
const did = route.params.id as string;
const loading = ref(false);
const defect = ref<any>({});
const severityType = computed(() => {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "info" };
  return map[defect.value?.severity] || "info";
});

onMounted(async () => {
  loading.value = true;
  const resp = await defectApi.get(did);
  defect.value = resp.data.data;
  loading.value = false;
});
</script>
