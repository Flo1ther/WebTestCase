import { LoaderCircle, X } from 'lucide-react'
import {label} from '../labels'
import type { ReactNode } from 'react'
export const Loader=()=> <div className="loader"><LoaderCircle size={22}/> Завантаження даних…</div>
export const Empty=({children="Поки нічого не знайдено."}:{children?:ReactNode})=><div className="empty">{children}</div>
export const Badge=({value}:{value:string})=><span className={`badge ${value.toLowerCase().replace('_','-')}`}>{label(value)}</span>
export const Notice=({text}:{text:string})=><div className="notice">{text}</div>
export function Modal({title,children,onClose}:{title:string;children:ReactNode;onClose:()=>void}) {return <div className="modal-backdrop" role="dialog"><div className="modal"><header><h2>{title}</h2><button className="icon-button" onClick={onClose} title="Закрити"><X size={18}/></button></header>{children}</div></div>}
export function Pagination({count,page,setPage}:{count:number;page:number;setPage:(n:number)=>void}) {const pages=Math.ceil(count/10);if(pages<2)return null;return <div className="pagination"><button disabled={page===1} onClick={()=>setPage(page-1)}>Назад</button><span>Сторінка {page} з {pages}</span><button disabled={page===pages} onClick={()=>setPage(page+1)}>Далі</button></div>}
