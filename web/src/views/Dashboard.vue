<template>
  <div>
    <el-card shadow="never" style="margin-bottom: 20px; border: 2px dashed #409eff;">
      <div style="text-align: center; padding: 30px 0;">
        <h2 style="margin-bottom: 16px;">新建自动测试任务</h2>
        <p style="color: #909399; margin-bottom: 24px;">输入网址即可自动完成测试，产出可直接修复的缺陷报告</p>
        <el-form @submit.prevent="quickStart">
          <el-form-item>
            <el-input
              v-model="quickUrl"
              placeholder="输入被测网址，例如 https://example.com"
              style="width: 440px"
              clearable
            />
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="codeDir"
              placeholder="可选: 项目源码目录路径 (如 /path/to/project)"
              style="width: 440px"
              clearable
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" native-type="submit" :loading="creating" size="large">一键开始</el-button>
          </el-form-item>
        </el-form>
        <div style="margin-top: 8px;">
          <el-tag type="success" style="margin-right: 8px;">零脚本</el-tag>
          <el-tag type="warning" style="margin-right: 8px;">零维护</el-tag>
          <el-tag type="info">零配置</el-tag>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card shadow="hover" :body-style="{ padding: '20px' }">
          <div style="text-align: center">
            <div :style="{ fontSize: '28px', fontWeight: 'bold', color: stat.color }">{{ stat.value }}</div>
            <div style="font-size: 13px; color: #909399; margin-top: 6px">{{ stat.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card>
          <template #header><span>任务状态分布</span></template>
          <div ref="statusChartRef" style="height: 260px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>AI 引擎状态</span></template>
          <div style="padding: 20px; text-align: center;">
            <el-tag :type="aiStatus.tag" size="large" style="font-size: 16px; padding: 8px 20px;">
              {{ aiStatus.text }}
            </el-tag>
            <p style="margin-top: 12px; color: #909399; font-size: 13px;">
              {{ aiConfigured ? 'AI 引擎已就绪，支持全自动分析' : '未配置 API Key，使用规则引擎降级运行' }}
            </p>
            <el-button size="small" @click="$router.push('/settings')" style="margin-top: 8px;">配置</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between;">
          <span>近期任务</span>
          <el-button text type="primary" @click="$router.push('/tasks')">查看全部</el-button>
        </div>
      </template>
      <el-table :data="recentTasks" v-loading="loadingTasks" @row-click="(r: any) => $router.push(`/tasks/${r.id}`)">
        <el-table-column prop="name" label="任务名称" min-width="160" />
        <el-table-column prop="input.target_url" label="目标地址" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="defect_count" label="缺陷" width="60" align="center" />
        <el-table-column label="进度" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.progress_percent || 0" :status="row.progress_percent >= 100 ? 'success' : ''" />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="150" />
      </el-table>
      <div v-if="!recentTasks.length && !loadingTasks" style="padding: 40px 0; text-align: center; color: #909399;">
        暂无任务，在上方输入网址一键开始
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { createTask, listTasks } from '../api/taskApi';
import * as echarts from 'echarts';

const router = useRouter();
const quickUrl = ref('');
const codeDir = ref('');
const creating = ref(false);
const recentTasks = ref<any[]>([]);
const loadingTasks = ref(false);
const statusChartRef = ref<HTMLDivElement>();
const aiConfigured = ref(false);
const aiStatus = ref({ tag: 'info', text: '规则引擎' });

const stats = ref([
  { label: '任务数', value: 0, color: '#409eff' },
  { label: '已完成', value: 0, color: '#67c23a' },
  { label: '有缺陷', value: 0, color: '#f56c6c' },
  { label: '阻塞', value: 0, color: '#e6a23c' },
]);

function statusTag(s: string) {
  const map: Record<string, string> = {
    draft: 'info', prechecking: 'warning', running: 'primary',
    completed: 'success', completed_with_defects: 'danger',
    blocked: 'danger', cancelled: 'info', error: 'danger',
  };
  return map[s] || 'info';
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    draft: '草稿', prechecking: '预检', understanding: '理解',
    planning: '规划', running: '执行', analyzing: '分析',
    completed: '完成', completed_with_defects: '有缺陷',
    blocked: '阻塞', cancelled: '已取消', error: '错误',
  };
  return map[s] || s;
}

async function quickStart() {
  if (!quickUrl.value) {
    ElMessage.warning('请输入被测网址');
    return;
  }
  creating.value = true;
  try {
    const resp: any = await createTask({
      name: `Quick test - ${quickUrl.value}`,
      target_url: quickUrl.value,
      code_dir: codeDir.value || undefined,
      mode: 'quick',
    });
    if (resp?.code === 0) {
      const taskId = resp.data.task.id;
      ElMessage.success('任务创建成功');
      router.push(`/tasks/${taskId}`);
    } else {
      ElMessage.error(resp?.message || '创建失败');
    }
  } catch (e: any) {
    ElMessage.error('网络错误: ' + (e.message || '未知'));
  } finally {
    creating.value = false;
  }
}

async function loadRecent() {
  loadingTasks.value = true;
  try {
    const resp: any = await listTasks({ page: 1 });
    if (resp?.code === 0) {
      recentTasks.value = resp.data.items.slice(0, 10);
      stats.value[0].value = resp.data.total;
      stats.value[1].value = resp.data.items.filter((t: any) => t.status === 'completed').length;
      stats.value[2].value = resp.data.items.filter((t: any) => t.status === 'completed_with_defects').length;
      stats.value[3].value = resp.data.items.filter((t: any) => t.status === 'blocked').length;
      nextTick(() => renderChart(resp.data.items));
    }
  } finally {
    loadingTasks.value = false;
  }
}

function renderChart(tasks: any[]) {
  if (!statusChartRef.value) return;
  const chart = echarts.init(statusChartRef.value);
  const counts: Record<string, number> = {};
  for (const t of tasks) counts[t.status] = (counts[t.status] || 0) + 1;
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: Object.entries(counts).map(([k, v]) => ({
        name: statusLabel(k), value: v,
        itemStyle: { color: k === 'completed' ? '#67c23a' : k === 'running' ? '#e6a23c' : k === 'completed_with_defects' ? '#f56c6c' : '#909399' },
      })),
      label: { show: true, formatter: '{b}: {c}' },
    }],
  });
}

onMounted(async () => {
  await loadRecent();
  try {
    const llmResp = await fetch('/api/v1/settings/llm').then(r => r.json()).catch(() => null);
    if (llmResp?.data?.status === 'connected') {
      aiConfigured.value = true;
      aiStatus.value = { tag: 'success', text: '已配置 (API Key 就绪)' };
    }
  } catch { /* silent */ }
});
</script>
