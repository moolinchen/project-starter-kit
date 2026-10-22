// 测试真实 app.js 的导入/导出、状态和取消逻辑；不代替浏览器下载验收。
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const elements=new Map();let clicks=0,blobValue=null,unload=null;
function element(){return {textContent:'',innerHTML:'',hidden:false,disabled:false,value:'',files:[],showModal(){this.open=true},close(){this.open=false},querySelectorAll(){return []},prepend(){},click(){clicks++}}}
function el(s){if(!elements.has(s))elements.set(s,element());return elements.get(s)}
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'../example-星港窗户演示/management/project.json'),'utf8'));
const sandbox={console,setTimeout:()=>0,Blob:class {constructor(parts){blobValue=parts.join('')}},URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},document:{querySelector:el,querySelectorAll:()=>[],createElement:element},window:{addEventListener:(n,f)=>{if(n==='beforeunload')unload=f}},fetch:async()=>({ok:true,json:async()=>({data:JSON.parse(JSON.stringify(fixture)),etag:'test',token:'test'})})};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(path.join(__dirname,'../template/management/app.js'),'utf8'),sandbox);
(async()=>{await new Promise(r=>setImmediate(r));let tests=0;const run=s=>vm.runInContext(s,sandbox);
run('basic(data)');tests++;
run("download(data,'project.json')");assert.deepStrictEqual(JSON.parse(blobValue),fixture);assert.equal(clicks,1);tests++;
run("data.project.next='修改';changed()");assert.match(el('#saveState').textContent,/未保存/);assert.equal(el('#save').disabled,false);let prevented=false;unload({preventDefault(){prevented=true}});assert.ok(prevented);tests++;
run('ask=async()=>false');el('#import').files=[{size:100,text:async()=>JSON.stringify(fixture)}];await el('#import').onchange({target:el('#import')});assert.equal(run('data.project.next'),'修改');tests++;
run('ask=async()=>true');el('#import').files=[{size:100,text:async()=>JSON.stringify(fixture)}];await el('#import').onchange({target:el('#import')});assert.equal(run('data.project.next'),fixture.project.next);tests++;
el('#import').files=[{size:10,text:async()=>'{bad'}];await el('#import').onchange({target:el('#import')});assert.match(el('#message').textContent,/导入失败/);tests++;
run("data=clone(data);data.tasks.push(clone(data.tasks[0]))");assert.throws(()=>run('basic(data)'),/重复/);tests++;
run("data=blank();data.tasks=[{id:'T001',title:'测试',status:'待办',blocker:'',batchId:''}];data.versions=[{id:'V001',taskId:'T001',label:'版本',paths:'../越界',note:''}]");assert.throws(()=>run('basic(data)'),/相对路径/);tests++;
run("data=blank();data.tasks=[{id:'T001',title:'保留',status:'待办',blocker:'',batchId:''}];ask=async()=>false");await run("remove('tasks',0)");assert.equal(run('data.tasks.length'),1);tests++;
// 1.1.0：图片对比与清理汇总
run('data=clone(JSON.parse(JSON.stringify(data)))');
run("data="+JSON.stringify(fixture)+";online=true");
assert.equal(run("imageOf(data.versions[1])"),'30-work/window-v002.svg');tests++;
assert.equal(run("previousVersion(data.versions[1]).id"),'V001');assert.equal(run("previousVersion(data.versions[0])"),null);tests++;
let html=run("compareHtml(data.reviews[1])");assert.match(html,/\/files\/30-work\/window-v001\.svg/);assert.match(html,/\/files\/30-work\/window-v002\.svg/);assert.match(html,/并排/);tests++;
run("compareMode['R002']='overlay'");html=run("compareHtml(data.reviews[1])");assert.match(html,/type="range"/);assert.match(html,/data-onion="R002"/);tests++;
assert.match(run("fileUrl('30-work/中 文.png')"),/^\/files\/30-work\/%E4%B8%AD%20%E6%96%87\.png$/);run('online=false');assert.match(run("compareHtml(data.reviews[1])"),/本地服务/);tests++;
html=run("summaryHtml({categories:{'90-tmp':{items:1,files:2,bytes:10,human:'10 B',eligibleFiles:2,eligibleHuman:'10 B'}},total:{items:1,files:2,bytes:10,human:'10 B',eligibleFiles:2,eligibleHuman:'10 B'}})");assert.match(html,/总计/);assert.match(html,/90-tmp/);tests++;
assert.equal(run("blank().templateVersion"),'1.1.0');run("data=blank();data.templateVersion='1.0.0'");run('basic(data)');tests++;
console.log(`${tests} 项界面逻辑测试通过（浏览器下载许可未自动接受）`);
})().catch(e=>{console.error(e);process.exit(1)});
