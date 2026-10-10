export async function api<T=any>(path:string,options?:RequestInit):Promise<T>{
 const res=await fetch('/api'+path,{...options,headers:options?.body instanceof FormData?undefined:{'Content-Type':'application/json',...options?.headers}});
 if(!res.ok){let d;try{d=await res.json()}catch{throw Error(`Request failed (${res.status})`)}throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail))}
 return res.json();
}
export const post=(path:string,data:any={})=>api(path,{method:'POST',body:JSON.stringify(data)});
export const put=(path:string,data:any)=>api(path,{method:'PUT',body:JSON.stringify(data)});
export const percent=(n:number|null)=>n===null?'—':`${Math.round(n)}%`;
export const date=(t:number)=>new Date(t*1000).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
