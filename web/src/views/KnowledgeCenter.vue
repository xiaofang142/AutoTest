<template>
  <div>
    <h3 style="margin-bottom: 16px;">知识/文档中心</h3>
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card>
          <template #header><span>文档列表</span></template>
          <el-table :data="documents" v-loading="loading" empty-text="暂无文档">
            <el-table-column prop="id" label="ID" width="120" />
            <el-table-column prop="url" label="来源" min-width="200" show-overflow-tooltip />
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }"><el-tag size="small">{{ row.type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }"><el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="rule_count" label="规则数" width="80" align="center" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><span>知识库概览</span></template>
          <div v-if="kb">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="版本">{{ kb.version }}</el-descriptions-item>
              <el-descriptions-item label="质量评级"><el-tag :type="kb.quality_grade === 'A' ? 'success' : 'warning'">{{ kb.quality_grade }}</el-tag></el-descriptions-item>
              <el-descriptions-item label="规则总数">{{ kb.total_rules }}</el-descriptions-item>
              <el-descriptions-item label="已确认">{{ kb.confirmed_rules }}</el-descriptions-item>
              <el-descriptions-item label="冲突数">{{ kb.conflicts_count }}</el-descriptions-item>
            </el-descriptions>
          </div>
          <el-empty v-else description="暂无知识库" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

const loading = ref(false);
const documents = ref<any[]>([]);
const kb = ref<any>(null);

onMounted(async () => {
  loading.value = true;
  try {
    const resp = await fetch('/api/v1/projects').then(r => r.json());
    const projects = resp?.data?.items || [];
    if (projects.length > 0) {
      const pid = projects[0].id;
      const [docResp, kbResp] = await Promise.all([
        fetch(`/api/v1/projects/${pid}/documents`).then(r => r.json()).catch(() => ({ data: { items: [] } })),
        fetch(`/api/v1/projects/${pid}/knowledge`).then(r => r.json()).catch(() => ({ data: null })),
      ]);
      documents.value = docResp?.data?.items || [];
      kb.value = kbResp?.data || null;
    }
  } catch { /* silent */ }
  loading.value = false;
});
</script>
