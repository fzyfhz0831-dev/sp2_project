import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import JsonGuidePage from '../views/JsonGuidePage.vue'
import NotFound from '../views/NotFound.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
    },
    {
      path: '/json-guide',
      name: 'json-guide',
      component: JsonGuidePage,
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFound,
    },
  ],
  scrollBehavior(to) {
    if (to.hash) {
      return {
        el: to.hash,
        top: 96,
        behavior: 'smooth',
      }
    }

    return { top: 0 }
  },
})

export default router
