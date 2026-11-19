import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({plugins:[react()],build:{rollupOptions:{output:{manualChunks:{charts:['recharts'],forms:['react-hook-form','zod','@hookform/resolvers/zod'],router:['react-router-dom']}}}},server:{host:'127.0.0.1',port:5173,strictPort:true,proxy:{'^/api(?:/|$)':{target:'http://127.0.0.1:8000',changeOrigin:false}}}})
