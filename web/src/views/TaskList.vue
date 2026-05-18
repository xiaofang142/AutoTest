<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
      <h3>测试任务</h3>
      <el-button type="primary" @click="$router.push('/')">+ 新建任务</el-button>
    </div>

    <el-card shadow="never" style="margin-bottom: 16px;">
      <el-form :inline="true">
        <el-form-item label="状态">
          <el-select v-model="filter.status" clearable placeholder="全部" style="width: 140px">
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="loadTasks(1)">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-table :data="tasks" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="任务名称" min-width="160" />
      <el-table-column prop="input.target_url" label="目标地址" min-width="200" show-overflow-tooltip />
      <el-table-column prop="mode" label="模式" width="100" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="tagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="自动化等级" width="100">
        <template #default="{ row }">{{ row.auto_level || 'A0' }}</template>
      </el-table-column>
      <el-table-column prop="defect_count" label="缺陷" width="60" align="center" />
      <el-table-column label="进度" width="140">
        <template #default="{ row }">
          <el-progress :percentage="row.progress_percent || 0" :status="row.progress_percent >= 100 ? 'success' : ''" />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button text @click="$router.push(`/tasks/${row.id}`)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > pageSize"
      :total="total" :page-size="pageSize"
      @current-change="loadTasks"
      background layout="prev, pager, next"
      style="margin-top: 16px; justify-content: center;" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { listTasks } from '../api/taskApi';

const tasks = ref<any[]>([]);
const loading = ref(false);
const total = ref(0);
const pageSize = 20;
const filter = ref({ status: '' });

const statusOptions = [
  { value: '', label: '全部' },
  { value: 'draft', label: '草稿' },
  { value: 'running', label: '运行中' },
  { value: 'completed', label: '已完成' },
  { value: 'completed_with_defects', label: '有缺陷' },
  { value: 'blocked', label: '阻塞' },
  { value: 'error', label: '错误' },
];

function tagType(s: string) {
  const map: Record<string, string> = {
    draft: 'info', prechecking: 'warning', understanding: 'warning',
    planning: 'warning', running: 'primary', analyzing: 'warning',
    completed: 'success', completed_with_defects: 'danger',
    blocked: 'danger', cancelled: 'info', error: 'danger',
  };
  return map[s] || 'info';
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    draft: '草稿', prechecking: '预检中', understanding: '理解中',
    planning: '规划中', running: '执行中', analyzing: '分析中',
    completed: '已完成', completed_with_defects: '有缺陷',
    blocked: '阻塞', cancelled: '已取消', error: '错误',
  };
  return map[s] || s;
}

async function loadTasks(page = 1) {
  loading.value = true;
  try {
    const resp: any = await listTasks({ status: filter.value.status, page });
    if (resp?.code === 0) {
      tasks.value = resp.data.items;
      total.value = resp.data.total;
    }
  } finally {
    loading.value = false;
  }
}

onMounted(() => loadTasks());
</script>
