<template>
  <div v-loading="loading">
    <el-page-header @back="$router.push('/tasks')" :content="task?.name || '任务详情'" style="margin-bottom: 16px;" />

    <el-steps :active="activeStep" finish-status="success" align-center style="margin-bottom: 24px; padding: 0 40px;">
      <el-step title="入口" />
      <el-step title="预检" />
      <el-step title="理解" />
      <el-step title="蓝图" />
      <el-step title="执行" />
      <el-step title="归因" />
      <el-step title="交付" />
    </el-steps>

    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="6">
        <el-statistic title="自动化等级" :value="task?.auto_level || 'A0'" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="缺陷数" :value="task?.defect_count || 0" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="进度" :value="task?.progress_percent || 0" suffix="%" />
      </el-col>
      <el-col :span="6">
        <el-button v-if="task?.status === 'draft'" type="primary" @click="startTask">启动任务</el-button>
        <el-button v-else-if="task?.status === 'blocked'" type="warning" @click="startTask">重试</el-button>
        <el-tag v-else :type="tagType(task?.status)" size="large">{{ statusLabel(task?.status) }}</el-tag>
      </el-col>
    </el-row>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="概览" name="overview">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务名称">{{ task?.name }}</el-descriptions-item>
          <el-descriptions-item label="阶段状态">
            <el-tag :type="tagType(task?.status)" size="small">{{ statusLabel(task?.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="目标地址">{{ task?.input?.target_url || '-' }}</el-descriptions-item>
          <el-descriptions-item label="模式">{{ task?.mode }}</el-descriptions-item>
          <el-descriptions-item label="目标类型">{{ task?.input?.target_type }}</el-descriptions-item>
          <el-descriptions-item label="环境">{{ task?.input?.environment }}</el-descriptions-item>
          <el-descriptions-item label="自动化等级"><el-tag>{{ task?.auto_level }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="缺陷数">{{ task?.defect_count }} (高风险: {{ task?.high_risk_count }})</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ task?.description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ task?.created_at }}</el-descriptions-item>
          <el-descriptions-item v-if="task?.summary" label="执行摘要" :span="2">{{ task.summary }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>

      <el-tab-pane label="预检结果" name="precheck">
        <pre v-if="task?.environment_check" style="background: #f5f7fa; padding: 16px; border-radius: 4px;">{{ JSON.stringify(task.environment_check, null, 2) }}</pre>
        <el-empty v-else description="预检尚未完成" />
      </el-tab-pane>

      <el-tab-pane label="理解结果" name="understanding">
        <pre v-if="task?.understanding" style="background: #f5f7fa; padding: 16px; border-radius: 4px;">{{ JSON.stringify(task.understanding, null, 2) }}</pre>
        <el-empty v-else description="理解尚未完成" />
      </el-tab-pane>

      <el-tab-pane label="测试蓝图" name="blueprint">
        <pre v-if="task?.blueprint" style="background: #f5f7fa; padding: 16px; border-radius: 4px;">{{ JSON.stringify(task.blueprint, null, 2) }}</pre>
        <el-empty v-else description="蓝图尚未生成" />
      </el-tab-pane>

      <el-tab-pane label="执行过程" name="execution">
        <div v-if="task?.run_id">
          <el-button text @click="$router.push(`/runs/${task.run_id}`)">查看执行详情 →</el-button>
        </div>
        <el-empty v-else description="尚未执行" />
      </el-tab-pane>

      <el-tab-pane label="缺陷与交付" name="defects">
        <div v-if="task?.delivery">
          <el-collapse>
            <el-collapse-item title="测试人员视图" name="tester">
              <pre style="background: #f5f7fa; padding: 12px; border-radius: 4px;">{{ JSON.stringify(task.delivery.tester_view, null, 2) }}</pre>
            </el-collapse-item>
            <el-collapse-item title="开发者视图" name="developer">
              <pre style="background: #f5f7fa; padding: 12px; border-radius: 4px;">{{ JSON.stringify(task.delivery.developer_view, null, 2) }}</pre>
            </el-collapse-item>
            <el-collapse-item title="AI 助手视图" name="ai">
              <pre style="background: #f5f7fa; padding: 12px; border-radius: 4px;">{{ JSON.stringify(task.delivery.ai_assistant_view, null, 2) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>
        <el-empty v-else description="交付尚未就绪" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { getTask, startTask as apiStartTask } from '../api/taskApi';

let ws: WebSocket | null = null;
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null;

function connectWebSocket(taskId: string) {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${location.host}/api/v1/ws/tasks/${taskId}`;
  ws = new WebSocket(wsUrl);
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'task_stage_change' || msg.type === 'task_completed' || msg.type === 'task_error') {
        loadTask();
      }
    } catch { /* ignore */ }
  };
  ws.onclose = () => {
    ws = null;
    wsReconnectTimer = setTimeout(() => {
      if (taskId) connectWebSocket(taskId);
    }, 3000);
  };
}

function disconnectWebSocket() {
  if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
  if (ws) { ws.close(); ws = null; }
}

const route = useRoute();
const router = useRouter();
const task = ref<any>(null);
const loading = ref(false);
const activeTab = ref('overview');

const stageMap: Record<string, number> = {
  draft: 0, prechecking: 1, understanding: 2, planning: 3,
  running: 4, analyzing: 5, completed: 6, completed_with_defects: 6,
  blocked: 0, cancelled: 0, error: 0,
};
const activeStep = computed(() => stageMap[task.value?.status] ?? 0);

function tagType(s: string) {
  const map: Record<string, string> = {
    draft: 'info', prechecking: 'warning', running: 'primary',
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

async function loadTask() {
  loading.value = true;
  try {
    const resp: any = await getTask(route.params.id as string);
    if (resp?.code === 0) task.value = resp.data.task;
    else ElMessage.error(resp?.message || '加载任务失败');
  } catch (e: any) {
    ElMessage.error('网络错误: ' + (e.message || '未知'));
  } finally {
    loading.value = false;
  }
}

async function startTask() {
  loading.value = true;
  try {
    const resp: any = await apiStartTask(route.params.id as string);
    if (resp?.code === 0) {
      ElMessage.success('任务已启动');
      await loadTask();
    } else {
      ElMessage.error(resp?.message || '启动失败');
    }
  } catch (e: any) {
    ElMessage.error('启动失败: ' + (e.message || '未知'));
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadTask();
  connectWebSocket(route.params.id as string);
});

onUnmounted(() => {
  disconnectWebSocket();
});
</script>
