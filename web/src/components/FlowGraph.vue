<template>
  <div style="width: 100%">
    <!-- 业务线概览图 -->
    <el-card v-if="chains.length" style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>📊 业务线全景</span>
          <el-tag size="small">{{ chains.length }} 条业务线</el-tag>
        </div>
      </template>
      <div ref="graphRef" style="height: 400px; width: 100%" />
    </el-card>

    <!-- 业务流程详情（一条业务线一张卡片） -->
    <el-card v-for="(chain, ci) in chains" :key="ci" style="margin-bottom: 12px">
      <template #header>
        <div style="display: flex; justify-content: space-between">
          <span>
            <el-tag :type="chain.source === 'derived' ? 'warning' : 'success'" size="small" style="margin-right: 8px">
              {{ chain.source === 'derived' ? 'AI 推断' : '文档抽取' }}
            </el-tag>
            <strong>{{ chain.name }}</strong>
          </span>
          <span>
            <el-tag v-for="r in chain.roles" :key="r" size="small" style="margin-left: 4px">{{ r }}</el-tag>
          </span>
        </div>
      </template>

      <!-- 流程步骤可视化 -->
      <div class="flow-steps">
        <div v-for="(step, si) in chain.steps" :key="si" class="flow-step-item">
          <div class="flow-step-card" :class="{ 'is-active': step.active }">
            <div class="step-index">{{ si + 1 }}</div>
            <div class="step-content">
              <div class="step-action">{{ step.action }}</div>
              <div class="step-page" v-if="step.page">{{ step.page }}</div>
              <div class="step-expected" v-if="step.expected">{{ step.expected }}</div>
            </div>
          </div>
          <div v-if="si < chain.steps.length - 1" class="flow-arrow">▶</div>
        </div>
      </div>

      <!-- 路径类型矩阵 -->
      <div style="margin-top: 12px">
        <el-tag
          v-for="pt in chain.pathTypes"
          :key="pt.type"
          :type="pt.tagType"
          size="small"
          style="margin-right: 6px; cursor: pointer"
          @click="pt.callback"
        >
          {{ pt.label }} ({{ pt.count }} 用例)
        </el-tag>
      </div>
    </el-card>

    <!-- 空状态 -->
    <el-empty v-if="!chains.length" description="暂无业务线数据，请先生成测试场景" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from "vue";
import * as echarts from "echarts";

const props = defineProps<{
  chains: any[];
}>();

const graphRef = ref<HTMLDivElement>();

// ---- ECharts 关系图 ----
function renderGraph() {
  if (!graphRef.value || !props.chains.length) return;

  const chart = echarts.init(graphRef.value);
  const nodes: any[] = [];
  const links: any[] = [];
  const categories = [
    { name: "业务起点", itemStyle: { color: "#409eff" } },
    { name: "流程步骤", itemStyle: { color: "#67c23a" } },
    { name: "路径类型", itemStyle: { color: "#e6a23c" } },
  ];

  let nodeId = 0;
  const added = new Set<string>();

  for (const chain of props.chains) {
    const steps = chain.steps || [];
    if (!steps.length) continue;

    // 每个 chain 的步骤节点
    const chainNodes = steps.map((s: any) => {
      const id = `n_${nodeId++}`;
      nodes.push({
        id,
        name: s.action.slice(0, 12) + (s.action.length > 12 ? "…" : ""),
        category: 0,
        symbolSize: 40,
        tooltip: { formatter: `<b>${s.action}</b><br/>页面: ${s.page || "-"}<br/>预期: ${s.expected || "-"}` },
      });
      return id;
    });

    // 步骤之间的连线
    for (let i = 0; i < chainNodes.length - 1; i++) {
      links.push({ source: chainNodes[i], target: chainNodes[i + 1] });
    }

    // 路径类型节点
    const pathTypes = chain.pathTypes || [];
    for (const pt of pathTypes) {
      const ptId = `pt_${nodeId++}`;
      nodes.push({
        id: ptId,
        name: pt.label,
        category: 2,
        symbolSize: 25,
      });
      if (chainNodes.length > 0) {
        links.push({ source: chainNodes[chainNodes.length - 1], target: ptId, lineStyle: { type: "dashed" } });
      }
    }
  }

  chart.setOption({
    title: { show: false },
    tooltip: { trigger: "item", formatter: (p: any) => p.data?.tooltip?.formatter?.() || p.name },
    series: [{
      type: "graph",
      layout: "force",
      force: { repulsion: 300, edgeLength: [80, 150], gravity: 0.1 },
      roam: true,
      draggable: true,
      categories,
      data: nodes,
      links,
      label: { show: true, position: "bottom", fontSize: 11 },
      lineStyle: { color: "source", curveness: 0.3, width: 2 },
      edgeSymbol: ["none", "arrow"],
      edgeSymbolSize: [0, 10],
    }],
  });
}

watch(() => props.chains, () => nextTick(renderGraph), { deep: true });
onMounted(() => nextTick(renderGraph));
</script>

<style scoped>
.flow-steps {
  display: flex;
  align-items: flex-start;
  overflow-x: auto;
  padding: 8px 0;
  gap: 4px;
}
.flow-step-item {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.flow-step-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  min-width: 120px;
  transition: all 0.2s;
}
.flow-step-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.15);
}
.flow-step-card.is-active {
  border-color: #67c23a;
  background: #f0f9eb;
}
.step-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  flex-shrink: 0;
}
.step-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.step-action {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
}
.step-page {
  font-size: 11px;
  color: #909399;
}
.step-expected {
  font-size: 11px;
  color: #67c23a;
}
.flow-arrow {
  color: #c0c4cc;
  font-size: 14px;
  padding: 0 4px;
}
</style>
