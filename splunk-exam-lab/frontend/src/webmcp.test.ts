import {it,expect,vi} from 'vitest';
import {registerStudyTools} from './webmcp';
it('registers real navigation and read tools, rejects invalid inputs, and cleans up',async()=>{
 const tools:any[]=[];const signals:AbortSignal[]=[];const go=vi.fn(),read=vi.fn().mockResolvedValue({attempted:7});
 vi.stubGlobal('document',{modelContext:{registerTool:(t:any,o:any)=>{tools.push(t);signals.push(o.signal)}}});
 const cleanup=registerStudyTools(go,read);
 expect(tools.map(t=>t.name)).toEqual(['read_study_metrics','navigate_study_page']);
 expect(await tools[0].execute({})).toEqual({attempted:7});
 expect(await tools[1].execute({page:'Quick Practice'})).toEqual({page:'Quick Practice'});expect(go).toHaveBeenCalledWith('Quick Practice');
 await expect(tools[1].execute({page:'Delete all data'})).rejects.toThrow('Unknown study page');
 cleanup?.();expect(signals.every(s=>s.aborted)).toBe(true);vi.unstubAllGlobals();
});
