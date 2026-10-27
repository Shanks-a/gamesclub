import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
const router=createRouter({history:createWebHashHistory(),routes:[{path:'/:section?',component:{template:'<span />'}}]})
createApp(App).use(createPinia()).use(router).use(ElementPlus, { locale: zhCn }).mount('#app')
