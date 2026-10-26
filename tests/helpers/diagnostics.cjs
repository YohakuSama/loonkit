'use strict';
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const ROOT=path.resolve(__dirname,'../..');
const rows=JSON.parse(fs.readFileSync(path.join(ROOT,'build/runtime.lock.json'),'utf8')).resources;

function asset(uri,kind){
  const row=rows.find(r=>r.uri===uri && r.kind===kind);
  if(!row)throw Error('Published diagnostics dependency is absent from runtime.lock.json: '+uri);
  const filename=path.resolve(ROOT,row.local_path);
  if(!filename.startsWith(ROOT+path.sep))throw Error('Asset path escapes checkout');
  const raw=fs.readFileSync(filename);
  if(crypto.createHash('sha256').update(raw).digest('hex')!==row.sha256)throw Error('Published diagnostics digest differs: '+filename);
  return {filename,source:raw.toString('utf8')};
}

const profile=fs.readFileSync(path.join(ROOT,'LoonKit.lcf'),'utf8');
const section=profile.split('[Plugin]\n')[1]?.split(/\n\[/)[0];
const declarations=(section||'').split('\n').filter(line=>line.startsWith('https://'));
if(declarations.length!==1)throw Error('Expected one published diagnostic plugin');
const plugin=asset(declarations[0].split(',')[0],'plugin');
const scripts={};
for(const match of plugin.source.matchAll(/\bscript\("([^"]+)"/g)){
  const name=match[1].split('/').pop();
  if(scripts[name])throw Error('Duplicate published diagnostic entry');
  scripts[name]=asset(match[1],'script');
}
const expected=['media-unlock.js','network-diagnostics.js','node-intelligence.js'];
if(JSON.stringify(Object.keys(scripts).sort())!==JSON.stringify(expected))throw Error('Published diagnostics inventory differs');

module.exports={scripts,plugin,source(name){
  const row=scripts[name];
  if(!row)throw Error('Unknown published script: '+name);
  return row.source;
}};
