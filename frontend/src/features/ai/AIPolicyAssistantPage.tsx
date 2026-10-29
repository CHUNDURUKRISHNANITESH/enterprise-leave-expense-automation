import {useState,type FormEvent} from "react";
import {api} from "../../services/workflow";
import "../../css/AIPolicyAssistantPage.css";
interface Answer{answer:string;sources:{title:string;section:string}[];mode:string}
export default function AIPolicyAssistantPage({accessToken}:{accessToken:string}){
 const [question,setQuestion]=useState(""),[history,setHistory]=useState<{question:string;result:Answer}[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState("");
 async function ask(e:FormEvent){e.preventDefault();if(!question.trim())return;setBusy(true);setError("");try{const result=await api<Answer>(accessToken,"/api/v1/ai/ask","POST",{question:question.trim()});setHistory(h=>[...h,{question,result}]);setQuestion("");}catch(e){setError(String(e));}finally{setBusy(false);}}
 return <section className="workflow-page"><header><div><h1>AI Policy Assistant</h1><p>Ask questions about leave and expense policies. Answers include source references.</p></div></header>{history.map((item,i)=><article key={i} className="workflow-detail"><h3>{item.question}</h3><p>{item.result.answer}</p><small>Mode: {item.result.mode}</small><ul>{item.result.sources.map((s,j)=><li key={j}>{s.title} — {s.section}</li>)}</ul></article>)}{error&&<p className="workflow-error" role="alert">{error}</p>}<form className="workflow-form" onSubmit={ask}><label>Policy question<textarea required value={question} onChange={e=>setQuestion(e.target.value)} placeholder="What is the annual leave entitlement?"/></label><button disabled={busy}>{busy?"Checking policies...":"Ask Assistant"}</button></form></section>;
}
