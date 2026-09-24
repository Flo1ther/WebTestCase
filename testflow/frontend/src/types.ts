export type Role = 'ADMIN' | 'MANAGER' | 'TESTER'
export type Status = 'PASSED' | 'FAILED' | 'BLOCKED' | 'NOT_RUN'
export interface User { id:number; username:string; email:string; first_name:string; last_name:string; full_name:string; role:Role; is_active:boolean }
export interface Project { id:number; name:string; description:string; created_by:number; created_by_name?:string; created_at:string; test_case_count?:number; progress?:number }
export interface Step { id?:number; step_number:number; action:string; expected_result:string }
export interface TestCase { id:number; project:number; project_name:string; title:string; description:string; preconditions:string; expected_result:string; priority:string; status:Status; assigned_to:number|null; assigned_to_name?:string|null; created_by_name:string; created_at:string; updated_at:string; steps:Step[] }
export interface Execution { id:number; test_case:number; test_case_title:string; tester_name:string; status:Status; actual_result:string; comment:string; executed_at:string }
export interface Defect { id:number; test_case:number; test_case_title:string; reported_by_name:string; title:string; description:string; status:string; created_at:string }
export interface ListResponse<T> { count:number; next:string|null; previous:string|null; results:T[] }
