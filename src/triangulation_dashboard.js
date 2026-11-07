// Embedded by export_diagnostics. No server or Python kernel is needed.
(() => {
  const rows = __ROWS__;
  const defaults = __THRESHOLDS__;
  const plot = document.getElementById('sfm-quality');
  const el = id => document.getElementById(id);
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  const fields = ['x','y','z','effective_angle_deg','depth_a','depth_b','max_error_px','depth_baselines'];
  let accepted = [], shown = [];
  const scatter = document.createElement('div');
  scatter.id = 'geometry-plot';
  plot.after(scatter);
  Plotly.newPlot(scatter, [
    {x:[], y:[], type:'scatter', mode:'markers', name:'Aceptados', marker:{color:'#21b6a8'}},
    {x:[], y:[], type:'scatter', mode:'markers', name:'Rechazados', marker:{color:'#f06a73'}}
  ], {template:'plotly_dark', paper_bgcolor:'#111827', plot_bgcolor:'#111827', font:{color:'#e5e7eb'},
      height:340, margin:{t:45}, title:{text:'Ángulo frente a profundidad: investigar geometría débil'},
      xaxis:{title:{text:'Ángulo efectivo (°)'}}, yaxis:{title:{text:'Profundidad / baseline'}}});
  function reasons(r, a, e, d) {
    const why = [];
    if (!fields.every(f=>finite(r[f]))) why.push('nonfinite');
    if (!(r.depth_a>0 && r.depth_b>0)) why.push('cheirality');
    if (r.effective_angle_deg<a) why.push('angle');
    if (r.max_error_px>e) why.push('reprojection');
    if (r.depth_baselines>d) why.push('depth');
    if (el('associations').checked && !(r.associated_observations>=2 &&
        finite(r.associated_max_error_px) && r.associated_max_error_px<=e &&
        r.associated_min_depth>0)) why.push('associations');
    return why;
  }
  function percentile(data, q) {
    if (!data.length) return '—';
    const v = data.slice().sort((a,b)=>a-b), i=(v.length-1)*q, lo=Math.floor(i), hi=Math.ceil(i);
    return (v[lo]+(v[hi]-v[lo])*(i-lo)).toFixed(3);
  }
  function metrics(data, field) {
    const values=data.map(r=>r[field]).filter(finite);
    return [0,.5,.95,1].map(q=>percentile(values,q));
  }
  function hover(r, why) {
    return `ID ${r.point_id} · ${r.origin} · Views ${r.view_a}/${r.view_b}`+
      `<br>θ=${r.angle_deg?.toFixed(3)}° · efectivo=${r.effective_angle_deg?.toFixed(3)}°`+
      `<br>Profundidad A/B: ${r.depth_a?.toFixed(3)} / ${r.depth_b?.toFixed(3)}`+
      `<br>Profundidad/baseline: ${r.depth_baselines?.toFixed(3)}`+
      `<br>Error A/B: ${r.error_a_px?.toFixed(3)} / ${r.error_b_px?.toFixed(3)} px`+
      `<br>Asociaciones: ${r.associated_observations}, error máx. ${r.associated_max_error_px?.toFixed(3)} px`+
      `<br>${why.length ? 'Rechazo: '+why.join(', ') : 'Aceptado con estos umbrales'}`;
  }
  function update() {
    const a=+el('angle').value, e=+el('error').value, d=+el('depth').value;
    if (![el('angle'),el('error'),el('depth')].every(x=>x.value!=='' && x.checkValidity())) return;
    shown=rows.filter(r=>el('origin').value==='all'||r.origin===el('origin').value);
    const why=new Map(shown.map(r=>[r.point_id,reasons(r,a,e,d)]));
    accepted=shown.filter(r=>!why.get(r.point_id).length);
    const rejected=shown.filter(r=>why.get(r.point_id).length);
    [accepted,rejected].forEach((group,i)=>{
      // Nonfinite coordinates cannot be drawn; they remain in statistics and CSV.
      const visible=group.filter(r=>['x','y','z'].every(f=>finite(r[f])));
      const text=visible.map(r=>hover(r,why.get(r.point_id)));
      Plotly.restyle(plot, {x:[visible.map(r=>r.x)],y:[visible.map(r=>r.y)],
        z:[visible.map(r=>r.z)],text:[text]}, [i]);
      Plotly.restyle(scatter, {x:[visible.map(r=>r.effective_angle_deg)],
        y:[visible.map(r=>r.depth_baselines)],text:[text],hovertemplate:'%{text}<extra></extra>'},[i]);
    });
    const unplottable=shown.filter(r=>!['x','y','z'].every(f=>finite(r[f]))).length;
    el('counts').textContent=`Antes: ${shown.length} · Aceptados: ${accepted.length} · Rechazados: ${rejected.length} · No dibujables: ${unplottable}`;
    let html='<table><thead><tr><th>Métrica</th><th>Antes min / mediana / p95 / máx.</th><th>Después min / mediana / p95 / máx.</th></tr></thead><tbody>';
    [['z','Z del mundo'],['max_depth','Profundidad máxima (pareja)'],['depth_baselines','Profundidad / baseline'],
     ['effective_angle_deg','Ángulo efectivo (°)'],['max_error_px','Error máximo (px)'],
     ['associated_max_error_px','Error máx. asociaciones (px)']].forEach(([f,label])=>{
      html+=`<tr><td>${label}</td><td>${metrics(shown,f).join(' / ')}</td><td>${metrics(accepted,f).join(' / ')}</td></tr>`;
    });
    el('stats').innerHTML=html+'</tbody></table>';
    el('origins').innerHTML='<table><tr><th>Origen</th><th>Antes</th><th>Aceptados</th><th>Rechazados</th></tr>'+['Seed 03-04','View 05','View 06'].map(o=>
      `<tr><td>${o}</td><td>${shown.filter(r=>r.origin===o).length}</td><td>${accepted.filter(r=>r.origin===o).length}</td><td>${rejected.filter(r=>r.origin===o).length}</td></tr>`).join('')+'</table>';
    el('reasons').textContent='Motivos de rechazo (pueden solaparse): '+
      ['nonfinite','cheirality','angle','reprojection','depth','associations'].map(s=>
        `${s}: ${[...why.values()].filter(v=>v.includes(s)).length}`).join(' · ');
  }
  function reset() {
    el('angle').value=defaults.min_angle; el('error').value=defaults.max_error;
    el('depth').value=defaults.max_depth_baselines;
    el('associations').checked=defaults.check_associations; el('origin').value='all';
    update();
  }
  ['angle','error','depth','origin','associations'].forEach(id=>el(id).addEventListener('input',update));
  el('reset').onclick=reset;
  el('focus').onclick=()=>{
    if (!accepted.length) return;
    const layout={};
    ['x','y','z'].forEach(f=>{
      const v=accepted.map(r=>r[f]).filter(finite), lo=Math.min(...v), hi=Math.max(...v);
      const padding=Math.max((hi-lo)*.08,1e-3);
      layout[`scene.${f}axis.range`]=[lo-padding,hi+padding];
      layout[`scene.${f}axis.autorange`]=false;
    });
    Plotly.relayout(plot,layout);
  };
  el('allpoints').onclick=()=>Plotly.relayout(plot,{
    'scene.xaxis.autorange':true,'scene.yaxis.autorange':true,'scene.zaxis.autorange':true});
  reset();
})();
