const {readFileSync}=require('fs');
const vm=require('vm');
const path=require('path');
const assets=path.resolve(__dirname,'../assets');
const resources=process.argv[2] && path.resolve(process.argv[2]);
const contentPath=resources ? path.join(resources,'dist/contentScripts/safari-fetch.js') : path.join(assets,'safari-fetch.js');
const backgroundText=readFileSync(resources ? path.join(resources,'dist/background/index.js') : path.join(assets,'safari-background-helper.js'),'utf8');
const helperStart=backgroundText.indexOf('async function bewlySafariFetch(');
if(helperStart < 0) throw new Error('Safari helper not found');
// Verified baseline appends the standalone helper at EOF.
const helperText=backgroundText.slice(helperStart);
const assert=require('assert/strict');
(async()=>{
 let connect,requests=0;
 const top={};top.top=top;
 const context={window:top,location:{hostname:'www.bilibili.com'},URL,AbortSignal,
  browser:{runtime:{id:'test-extension',onConnect:{addListener:f=>connect=f}}},
  fetch:async(url,opts)=>{requests++;assert.equal(new URL(url).origin,'https://api.bilibili.com');assert.equal(opts.credentials,'include');assert.equal(opts.method,'GET');return new Response('{"code":0}',{headers:{'content-type':'application/json'}})}};
 vm.runInNewContext(readFileSync(contentPath,'utf8'),context);
 const url='https://api.bilibili.com/x/web-interface/nav';
 let listener,received;
 const port={name:'bewly:safari:authenticated-get',sender:{id:'test-extension'},onMessage:{addListener:f=>listener=f},postMessage:x=>received=x};
 connect({...port,sender:{id:'different-extension'}});assert.equal(listener,undefined);
 connect({...port,name:'other'});assert.equal(listener,undefined);
 connect(port);
 for(const bad of ['https://example.com/','https://api.bilibili.com.evil.test/','http://api.bilibili.com/','https://user@api.bilibili.com/'])listener({url:bad});
 assert.equal(requests,0);listener({url});await new Promise(r=>setImmediate(r));
 assert.equal(received.status,200);assert.equal(received.body,'{"code":0}');assert.equal(requests,1);
 let fallback=0,tabCalls=0,mode='success';
 const ctx={URL,Response,setTimeout,clearTimeout,fetch:async()=>{fallback++;return new Response('fallback')},browser:{tabs:{connect:(id,opts)=>{
  tabCalls++;assert.equal(id,37);assert.equal(opts.frameId,0);
  let message,disconnect;
  return {onMessage:{addListener:f=>message=f},onDisconnect:{addListener:f=>disconnect=f},disconnect:()=>{},postMessage:()=>queueMicrotask(()=>mode==='success'?message(received):disconnect())};
 }}}};
 vm.runInNewContext(helperText,ctx);
 const options={method:'get',credentials:'include'};
 assert.equal(await(await ctx.bewlySafariFetch(url,options,37)).text(),'{"code":0}');
 for(const opt of [{method:'post',credentials:'include'},{method:'get',credentials:'omit'}])await ctx.bewlySafariFetch(url,opt,37);
 await ctx.bewlySafariFetch(url,options,undefined);
 await ctx.bewlySafariFetch('https://example.com/',options,37);
 assert.equal(tabCalls,1);assert.equal(fallback,4);
 mode='disconnected';assert.equal(await(await ctx.bewlySafariFetch(url,options,37)).text(),'fallback');
 const abort=new AbortController();abort.abort();
 await assert.rejects(ctx.bewlySafariFetch(url,{...options,signal:abort.signal},37));assert.equal(fallback,5);
 console.log('PASS: sender/origin restrictions, authenticated GET routing, originating tab, fallback, disconnection, and cancellation');
})().catch(e=>{console.error(e);process.exitCode=1});
