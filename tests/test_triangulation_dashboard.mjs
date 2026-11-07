// Unit-test the embedded control logic with a DOM/Plotly test double.
// This checks Python/JavaScript agreement, not visual rendering or WebGL.
// Run after the Python notebook runner: node tests/test_triangulation_dashboard.mjs
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const folder = root+'results/triangulation_diagnostics/';
const html = fs.readFileSync(folder+'diagnostics.html','utf8');
const cases = JSON.parse(fs.readFileSync(folder+'control_cases.json','utf8'));
const start = html.indexOf('// Embedded by export_diagnostics.');
const end = html.indexOf('})();',start)+5;
assert.ok(start>=0 && end>start, 'Embedded script is present');
const source = html.slice(start,end);
const elements = new Map();
const plots = new Map();
function get(id) {
  if (!elements.has(id)) elements.set(id, {id, value:'', checked:false, innerHTML:'', textContent:'',
    handlers:{}, addEventListener(event, fn){this.handlers[event]=fn;},
    checkValidity(){return true;}, after(){} });
  return elements.get(id);
}
const context = vm.createContext({console, document:{getElementById:get, createElement:()=>get('geometry-plot')},
  Plotly:{newPlot(){}, restyle(plot, update, ids){
    for (const id of ids) plots.set(plot.id+':'+id, update);
  }, relayout(plot,layout){plot.layout=layout;}} });
vm.runInContext(source,context);
for (const test of cases) {
  const t=test.thresholds;
  get('angle').value=String(t.min_angle); get('error').value=String(t.max_error);
  get('depth').value=String(t.max_depth_baselines); get('associations').checked=t.check_associations;
  get('origin').value='all'; get('angle').handlers.input();
  const text=plots.get('sfm-quality:0').text[0];
  const ids=Array.from(text,s=>Number(s.match(/^ID (\d+)/)[1]));
  assert.deepEqual(ids,test.accepted_ids,JSON.stringify(t));
  const counts=get('counts').textContent;
  assert.ok(counts.includes(`Aceptados: ${ids.length} ·`));
  get('focus').onclick(); get('allpoints').onclick();
}
get('reset').onclick();
assert.ok(get('counts').textContent.includes('Aceptados: 376 · Rechazados: 10'));
get('origin').value='View 05'; get('origin').handlers.input();
assert.ok(get('counts').textContent.includes('Antes: 113 · Aceptados: 103 · Rechazados: 10'));
get('origin').value='missing'; get('origin').handlers.input();
assert.ok(get('counts').textContent.includes('Antes: 0 · Aceptados: 0 · Rechazados: 0'));
assert.ok(!get('stats').innerHTML.includes('NaN'));
console.log(`Passed ${cases.length} Python/JavaScript classification comparisons, reset, origin, focus and empty-subset checks.`);
