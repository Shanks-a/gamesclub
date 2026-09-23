import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
const router=createRouter({history:createWebHashHistory(),routes:[{path:'/:section?',component:{template:'<span />'}}]})
createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app')
