import {useEffect,useState} from "react";
import {api,type Approval} from "../../services/workflow";
import "../../css/ApprovalsPage.css";
export default function ApprovalsPage({accessToken}:{accessToken:string}){
 const [items,setItems]=useState<Approval[]>([]),[error,setError]=useState(""),[busy,setBusy]=useState(false),[reason,setReason]=useState<Record<string,string>>({});
 async function load(){try{setItems(await api<Approval[]>(accessToken,"/api/v1/approvals/inbox"));}catch(e){setError(String(e));}}
 useEffect(()=>{void load();},[accessToken]);
 async function decide(item:Approval,decision:"approve"|"reject"){
 const why=(reason[item.id]||"").trim();if(!why){setError("Enter a decision reason first.");return;}if(!window.confirm(`${decision} this request?`))return;
 setBusy(true);setError("");try{if(item.expense_claim_id){await api(accessToken,`/api/v1/approvals/expenses/${encodeURIComponent(item.expense_claim_id)}/${decision}`,"POST",{reason:why});}else if(item.leave_request_id){await api(accessToken,`/api/v1/leaves/${encodeURIComponent(item.leave_request_id)}/${decision=== "approve"?"approve":"reject"}`,"POST",decision==="reject"?{reason:why}:undefined);}await load();}catch(e){setError(String(e));}finally{setBusy(false);}}
 return <section className="workflow-page"><header><div><h1>Approval Inbox</h1><p>Only approval steps assigned to your account are shown.</p></div><button onClick={()=>void load()}>Refresh</button></header>{error&&<p role="alert" className="workflow-error">{error}</p>}{items.length===0&&<p>No actionable approvals assigned.</p>}{items.map(item=><article className="workflow-detail" key={item.id}><h3>{item.expense_claim_id?"Expense":"Leave"}: {item.expense_claim_id||item.leave_request_id}</h3><p>Step {item.step_number} · {item.status}</p><label>Decision reason<input value={reason[item.id]||""} onChange={e=>setReason({...reason,[item.id]:e.target.value})}/></label><div className="workflow-actions"><button disabled={busy} onClick={()=>void decide(item,"approve")}>Approve</button><button disabled={busy} onClick={()=>void decide(item,"reject")}>Reject</button></div></article>)}</section>;
}
