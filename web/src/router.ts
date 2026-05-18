import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", component: () => import("./views/Dashboard.vue") },
  { path: "/tasks", component: () => import("./views/TaskList.vue") },
  { path: "/tasks/:id", component: () => import("./views/TaskDetail.vue") },
  { path: "/projects", component: () => import("./views/ProjectList.vue") },
  { path: "/projects/:id", component: () => import("./views/ProjectDetail.vue") },
  { path: "/runs/:id", component: () => import("./views/RunDetail.vue") },
  { path: "/defects/:id", component: () => import("./views/DefectDetail.vue") },
  { path: "/knowledge", component: () => import("./views/KnowledgeCenter.vue") },
  { path: "/settings", component: () => import("./views/Settings.vue") },
];

export default createRouter({ history: createWebHistory(), routes });
