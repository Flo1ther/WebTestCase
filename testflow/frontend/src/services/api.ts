import axios from 'axios'
const api=axios.create({baseURL:'/api',withCredentials:true,xsrfCookieName:'csrftoken',xsrfHeaderName:'X-CSRFToken',timeout:30000})
export async function csrf(){await api.get('/csrf/')}
api.interceptors.request.use(async config=>{if(!['get','head','options'].includes(config.method||'get')&&!document.cookie.split(';').some(v=>v.trim().startsWith('csrftoken=')))await csrf();return config})
export function errorText(error:unknown){const e=error as any;if(!e.response)return 'Немає з’єднання із сервером. Перевірте запуск застосунку.';const flatten=(v:any):string[]=>typeof v==='string'?[v]:Array.isArray(v)?v.flatMap(flatten):v&&typeof v==='object'?Object.values(v).flatMap(flatten):[];return flatten(e.response.data?.errors||e.response.data?.error||e.response.data).join(' ')||`Запит відхилено (${e.response.status}).`}
export default api
