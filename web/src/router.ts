import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", component: () => import("./views/Dashboard.vue") },
  { path: "/projects", component: () => import("./views/ProjectList.vue") },
  { path: "/projects/:id", component: () => import("./views/ProjectDetail.vue") },
  { path: "/runs/:id", component: () => import("./views/RunDetail.vue") },
  { path: "/defects/:id", component: () => import("./views/DefectDetail.vue") },
];

export default createRouter({ history: createWebHistory(), routes });
