export function registerStudyTools(go:(page:string)=>void,read:()=>Promise<unknown>){
 const context=(document as Document & {modelContext?:{registerTool:(tool:any,options:any)=>unknown}}).modelContext;
 if(!context?.registerTool)return;
 const lifecycle=new AbortController();
 const register=(tool:any)=>{try{void Promise.resolve(context.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{})}catch{/* unsupported implementation */}};
 register({name:'read_study_metrics',title:'Read local study metrics',description:'Read performance metrics from this personal local SQLite study lab.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:true},execute:async(input:any)=>{if(!input||Object.keys(input).length)throw Error('No arguments accepted');return read()}});
 const pages=['Dashboard','Full Mock Exam','Quick Practice','Topic-Based Practice','SPL Challenges','Wrong Answers','Bookmarks','Exam History','Performance Analytics','Question Bank','Settings'];
 register({name:'navigate_study_page',title:'Open a study page',description:'Navigate the visible study workspace to a named page. Does not start or submit an examination.',inputSchema:{type:'object',properties:{page:{type:'string',enum:pages}},required:['page'],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:false},execute:async(input:any)=>{if(!input||Object.keys(input).length!==1||!pages.includes(input.page))throw Error('Unknown study page');go(input.page);return {page:input.page}}});
 return()=>lifecycle.abort();
}
