const BASE=(import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
export async function api<T>(token:string,path:string,method="GET",payload?:unknown):Promise<T>{
 let response:Response;
 try {response=await fetch(BASE+path,{method,headers:{Authorization:`Bearer ${token}`,Accept:"application/json",...(payload!==undefined?{"Content-Type":"application/json"}:{})},...(payload!==undefined?{body:JSON.stringify(payload)}:{})});}
 catch{throw new Error("Unable to connect to the API.");}
 if(!response.ok){let msg=`Request failed (${response.status})`;try{const data=await response.json();if(typeof data.detail==="string")msg=data.detail;else if(Array.isArray(data.detail))msg=data.detail.map((x:{msg?:string})=>x.msg||"Invalid input").join("; ");}catch{}throw new Error(msg);}
 return response.json() as Promise<T>;
}
export interface ExpenseLine{ id:string;category:string;line_amount:string;receipt_hash:string|null }
export interface Expense{ id:string;employee_id:string;cost_center_id:string|null;currency:string;total_amount:string;status:string;anomaly_flags:string[];lines:ExpenseLine[] }
export interface Approval{ id:string;expense_claim_id:string|null;leave_request_id:string|null;step_number:number;approver_employee_id:string|null;status:string }
export interface Reimbursement{ id:string;claim_id:string;amount:string;currency:string;status:string;payment_reference:string|null;failure_reason:string|null;created_at:string }
export interface EmployeeInfo{ id:string;currency:string;cost_center_id:string|null }
