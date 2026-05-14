<template>
  <div v-loading="loading">
    <el-page-header @back="$router.back()" :content="`执行: ${run?.id}`" />
    <el-descriptions :column="3" border style="margin-top: 20px">
      <el-descriptions-item label="状态">
        <el-tag :type="run?.status === 'completed' ? 'success' : 'warning'">{{ run?.status }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="总用例">{{ run?.total_cases }}</el-descriptions-item>
      <el-descriptions-item label="通过率">{{ passRate }}%</el-descriptions-item>
    </el-descriptions>

    <h4 style="margin-top: 20px">缺陷列表</h4>
    <el-table :data="defects" @row-click="goDefect">
      <el-table-column prop="severity" label="严重程度" width="100">
        <template #default="{ row }">
          <el-tag :type="row.severity === 'high' ? 'danger' : 'warning'">{{ row.severity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="type" label="类型" width="120" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { runApi, defectApi } from "../api";

const route = useRoute();
const router = useRouter();
const rid = route.params.id as string;
const loading = ref(false);
const run = ref<any>({});
const defects = ref<any[]>([]);
const passRate = computed(() => run.value?.summary?.pass_rate != null ? (run.value.summary.pass_rate * 100).toFixed(1) : "0.0");
const goDefect = (row: any) => router.push(`/defects/${row.id}`);

onMounted(async () => {
  loading.value = true;
  const rResp = await runApi.get(rid);
  run.value = rResp.data.data;
  const dResp = await defectApi.list(rid);
  defects.value = dResp.data.data.items;
  loading.value = false;
});
</script>
