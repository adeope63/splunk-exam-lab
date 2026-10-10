import {describe,it,expect,vi,afterEach} from 'vitest';
import {api,post,put,percent} from './api';
afterEach(()=>vi.unstubAllGlobals());
describe('local API contract',()=>{
 it('uses the same-origin proxy and JSON for mutations',async()=>{const fetch=vi.fn().mockResolvedValue(new Response('{"saved":true}'));vi.stubGlobal('fetch',fetch);await put('/revision/Q1',{note:'Remember this'});expect(fetch).toHaveBeenCalledWith('/api/revision/Q1',expect.objectContaining({method:'PUT',body:'{"note":"Remember this"}',headers:{'Content-Type':'application/json'}}));});
 it('shows backend validation errors instead of reporting success',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('{"detail":"Only 6 matching questions"}',{status:409})));await expect(post('/exams',{count:10})).rejects.toThrow('Only 6 matching questions');});
 it('lets the browser supply multipart boundaries',async()=>{const fetch=vi.fn().mockResolvedValue(new Response('{"imported":1}'));vi.stubGlobal('fetch',fetch);await api('/import',{method:'POST',body:new FormData()});expect(fetch.mock.calls[0][1].headers).toBeUndefined();});
 it('distinguishes unattempted domain accuracy from zero',()=>{expect(percent(null)).toBe('—');expect(percent(0)).toBe('0%');expect(percent(66.67)).toBe('67%');});
});
