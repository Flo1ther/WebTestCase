import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, csrf } from './api'
import type { User, Config } from './types'
const AuthContext=createContext<{user:User|null;loading:boolean;config:Config|null;refresh:()=>Promise<User|null>;signout:()=>Promise<void>;logout:()=>Promise<void>}>({user:null,loading:true,config:null,refresh:async()=>null,signout:async()=>{},logout:async()=>{}})
export function AuthProvider({children}:{children:ReactNode}) {
  const [user,setUser]=useState<User|null>(null), [loading,setLoading]=useState(true),[config,setConfig]=useState<Config|null>(null)
  useEffect(()=>{localStorage.removeItem('access');localStorage.removeItem('refresh')},[])
  const refresh=useCallback(async()=>{try{const {data}=await api.get<User>('/me/');setUser(data);return data}catch{setUser(null);return null}},[])
  useEffect(()=>{Promise.all([csrf(),api.get<Config>('/config/').then(r=>setConfig(r.data)),refresh()]).catch(()=>setConfig(null)).finally(()=>setLoading(false))},[refresh])
  const signout=async()=>{await api.post('/auth/logout/');setUser(null);window.location.assign('/login');await csrf()}
  return <AuthContext.Provider value={{user,loading,config,refresh,signout,logout:signout}}>{children}</AuthContext.Provider>
}
export const useAuth=()=>useContext(AuthContext)
const ToastContext=createContext<(text:string,bad?:boolean)=>void>(()=>{})
export function ToastProvider({children}:{children:ReactNode}){
  const [toast,setToast]=useState<{text:string;bad:boolean}|null>(null)
  useEffect(()=>{if(toast){const timer=setTimeout(()=>setToast(null),7000);return()=>clearTimeout(timer)}},[toast])
  return <ToastContext.Provider value={(text,bad=false)=>setToast({text,bad})}>{children}{toast&&<div role="status" className={`toast ${toast.bad?'bad':''}`}>{toast.text}<button aria-label="Закрити повідомлення" onClick={()=>setToast(null)}>×</button></div>}</ToastContext.Provider>
}
export const useToast=()=>useContext(ToastContext)
