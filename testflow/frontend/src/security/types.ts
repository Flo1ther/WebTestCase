export interface User {username:string;full_name:string;is_active:boolean;created_at:string;id:number;email:string;first_name:string;last_name:string;role:'TESTER'|'MANAGER'|'ADMIN';email_verified:boolean;manual_blocked:boolean;auto_blocked_until:string|null;date_joined:string;last_login:string|null;two_factor_enabled:boolean;providers:string[];has_password:boolean}
export interface Config {turnstile_site_key:string;turnstile_test_mode:boolean;google_enabled:boolean;email_verification_required:boolean}
export interface SecurityEvent {id:number;user_id:number|null;user_email:string|null;actor_email:string|null;created_at:string;ip:string;event_type:string;success:boolean;reason:string}
export interface Paginated<T>{count:number;next:string|null;previous:string|null;results:T[]}
export interface Timeline{date:string;registrations:number;success:number;failed:number;auto_blocks:number}
export interface Dashboard {counts:{users:number;verified:number;pending:number;blocked:number;failed_logins:number;two_factor:number};timeline:Timeline[];statuses:{name:string;value:number}[]}
