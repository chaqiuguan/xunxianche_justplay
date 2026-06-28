import { createRouter, createWebHistory } from 'vue-router'
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/SystemCheck.vue'),
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue'),
    },
  

  {
    path:'/execute',
    name:'taskExecute',
    component:() => import('../views/taskExecute.vue'),
  },

    {
    path:'/execute_example',
    name:'taskExecute_example',
    component:() => import('../views/taskExecute_example.vue'),
  },

  {
    path:'/cam-control',
    name:'camControl',
    component:() => import('../views/CamControl.vue'),
  },

  {
    path:'/cam-test',
    name:'cam-test',
    component:() => import('../views/camer_test_vue_version.vue'),
  },

  {
    path:'/taskList',
    name:'taskList',
    component:() => import('../views/tasklist_example.vue'),
  },

  {
    path:'/picture-test',
    name:'pictureTest',
    component:() => import('../views/picture_test.vue'),
  },

  {
    path:'/test',
    name:'test',
    component:() => import('../views/test.vue'),
  },

  {
    path:'/task-history',
    name:'taskHistory',
    component:() => import('../views/TaskHistory.vue'),
  },
],

})

export default router
