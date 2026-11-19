import {ThemeToggle} from '../security/ui'
import {label} from '../labels'
import { BarChart3, ClipboardCheck, FolderKanban, LayoutDashboard, LogOut, Menu, ShieldCheck, UserCircle, Users, X } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
// The sidebar contains the daily QA workflow.  Less common tools still have routes,
// but do not make the navigation tall enough to hide the logout control.
// Операційні сутності (вимоги, тести, виконання, дефекти та AI) відкриваються
// всередині конкретного проєкту. У глобальному меню лишаються лише системні екрани.
const items=[['/dashboard',"Огляд",LayoutDashboard],['/projects',"Проєкти",FolderKanban],['/analytics',"Загальна аналітика",BarChart3],['/profile',"Профіль",UserCircle],['/security','Безпека',ShieldCheck]] as const
export function Layout(){const {user,logout}=useAuth();const [open,setOpen]=useState(false);const links=user?.role==='ADMIN'?[...items.slice(0,8),['/admin/users',"Користувачі",Users] as const,...items.slice(8),['/security/overview','Огляд безпеки',ShieldCheck] as const,['/security/users','Безпека користувачів',Users] as const,['/security/events','Журнал входів',ClipboardCheck] as const]:items;return <div className="app-shell"><aside className={open?'sidebar open':'sidebar'}><div className="brand"><ShieldCheck/> <span>WebTestCase</span><button className="icon-button mobile-only" onClick={()=>setOpen(false)}><X/></button></div><nav>{links.map(([to,label,Icon])=><NavLink key={to} to={to} onClick={()=>setOpen(false)}><Icon size={18}/>{label}</NavLink>)}</nav><div className="sidebar-user"><strong>{user?.full_name}</strong><small>{label(user?.role||'')}</small><button onClick={logout}><LogOut size={16}/>Вийти</button></div></aside><main><header className="topbar"><button className="icon-button mobile-only" onClick={()=>setOpen(true)} title="Відкрити навігацію"><Menu/></button><div><strong>Робочий простір тестування</strong><span>{user?.role === 'TESTER' ? "Призначені перевірки" : "Керування тестуванням команди"}</span></div><ThemeToggle/><div className="avatar">{user?.first_name?.[0] || user?.username?.[0]}</div></header><div className="page"><Outlet/></div></main></div>}
