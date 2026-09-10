'use strict';
const $ = id => document.getElementById(id);
let source = null, result = null, busy = false;
function invalidate(clearMapping = false) {
  result = null; $('results').hidden = true; $('error').textContent = ''; $('notice').textContent = '';
  if (clearMapping) { $('mapping').replaceChildren(); $('empty').hidden = false; $('normalize').disabled = true; }
}
function setBusy(value) {
  busy = value;
  for (const id of ['analyze','demo','normalize','json','csv','file','schemaFile','schema','sheet','encoding','delimiter']) $(id).disabled = value || (id === 'normalize' && !$('mapping').children.length);
  for (const select of $('mapping').querySelectorAll('select')) select.disabled = value;
}
function readSchema() {
  const schema = JSON.parse($('schema').value);
  if (!Array.isArray(schema) || !schema.length || schema.some(r => !r || typeof r.name !== 'string')) throw new Error('Le schéma doit contenir des champs nommés.');
  return schema;
}
function form(manual, output = 'json') {
  if (!source) throw new Error('Choisissez un fichier source.');
  if (source.size > 10 * 1024 * 1024) throw new Error('Le fichier dépasse 10 Mio.');
  const data = new FormData(); data.set('file', source); data.set('schema', JSON.stringify(readSchema()));
  for (const id of ['sheet','encoding','delimiter']) if ($(id).value) data.set(id, $(id).value === 'tab' ? '\t' : $(id).value);
  data.set('output', output);
  if (manual) {
    const mapping = Object.create(null);
    for (const select of $('mapping').querySelectorAll('select')) mapping[select.dataset.target] = select.value || null;
    data.set('mapping', JSON.stringify(mapping));
  }
  return data;
}
async function request(data) {
  const response = await fetch('/api/import', {method:'POST', headers:{'X-Importer-Client':'local-ui'}, body:data});
  if (!response.ok) {
    let message = 'Lecture impossible. Vérifiez le fichier et les règles.';
    try { const error = await response.json(); message = typeof error.detail === 'string' ? error.detail : message; } catch (_) {}
    throw new Error(message);
  }
  return response;
}
function mappings(data) {
  $('mapping').replaceChildren(); $('empty').hidden = true;
  for (const [target, selected] of Object.entries(data.mapping)) {
    const row = document.createElement('div'); row.className = 'mapping-row';
    const label = document.createElement('label'), select = document.createElement('select');
    select.id = 'map-' + $('mapping').children.length; select.dataset.target = target;
    label.htmlFor = select.id; label.textContent = target;
    select.add(new Option('Non associé', ''));
    for (const header of data.headers) select.add(new Option(header, header));
    select.value = selected || ''; select.addEventListener('change', () => { invalidate(); $('notice').textContent = 'Correspondance modifiée : appliquez pour recalculer.'; });
    row.append(label, select); $('mapping').append(row);
  }
}
function render(data) {
  result = data; $('results').hidden = false;
  $('counts').textContent = `${data.total} lignes · ${data.invalid} à corriger · ${data.total - data.invalid} sans erreur détectée`;
  $('notes').replaceChildren();
  for (const note of data.notes) { const li = document.createElement('li'); li.textContent = note; $('notes').append(li); }
  const names = Object.keys(data.mapping), head = document.createElement('tr');
  for (const name of ['Ligne source', ...names, 'Contrôle']) { const th = document.createElement('th'); th.textContent = name; th.scope = 'col'; head.append(th); }
  $('head').replaceChildren(head); $('body').replaceChildren();
  for (const row of data.rows.slice(0,100)) {
    const tr = document.createElement('tr'); if (row.errors.length) tr.className = 'invalid';
    const values = [row.row, ...names.map(n => row.normalized[n] ?? '—'), row.errors.map(e => `${e.field} : ${e.message}`).join('\n') || 'OK'];
    values.forEach((value, i) => { const td = document.createElement('td'); td.textContent = String(value); if (i === values.length - 1) td.className = 'issues'; tr.append(td); });
    $('body').append(tr);
  }
  $('notice').textContent = 'Contrôle terminé. Les lignes à corriger sont conservées.';
}
async function run(manual) {
  if (busy) return;
  try { const payload = form(manual); invalidate(); setBusy(true); $('notice').textContent = 'Lecture et contrôle…'; const data = await (await request(payload)).json(); if (!manual) mappings(data); render(data); }
  catch (error) { $('notice').textContent = ''; $('error').textContent = error.message; }
  finally { setBusy(false); }
}
function download(blob, filename) { const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
$('file').addEventListener('change', () => { source = $('file').files[0] || null; $('filename').textContent = source?.name || 'Aucun fichier sélectionné'; invalidate(true); });
for (const id of ['schema','sheet','encoding','delimiter']) $(id).addEventListener('input', () => invalidate(true));
$('schemaFile').addEventListener('change', async () => {
  const file = $('schemaFile').files[0]; if (!file) return;
  try { if (file.size > 65536) throw new Error('Schéma limité à 64 Kio.'); $('schema').value = await file.text(); readSchema(); invalidate(true); }
  catch (error) { invalidate(true); $('error').textContent = error.message; }
});
$('analyze').addEventListener('click', () => run(false)); $('normalize').addEventListener('click', () => run(true));
$('json').addEventListener('click', () => { if (result) download(new Blob([JSON.stringify(result,null,2)], {type:'application/json'}), 'normalized.json'); });
$('csv').addEventListener('click', async () => {
  if (!result || busy) return;
  try { const payload = form(true,'csv'); setBusy(true); download(await (await request(payload)).blob(), 'normalized.csv'); }
  catch (error) { $('error').textContent = error.message; } finally { setBusy(false); }
});
$('demo').addEventListener('click', async () => {
  if (busy) return; setBusy(true);
  try { const [schema,file] = await Promise.all([fetch('/example/schema.json'),fetch('/example/synthetic.csv')]);
    if (!schema.ok || !file.ok) throw new Error('Exemple indisponible.');
    $('schema').value = JSON.stringify(await schema.json(),null,2); source = new File([await file.blob()], 'exemple-fictif.csv', {type:'text/csv'}); $('file').value = ''; $('filename').textContent = source.name; $('sheet').value=''; $('encoding').value='utf-8-sig'; $('delimiter').value=';'; invalidate(true);
  } catch (error) { $('error').textContent = error.message; } finally { setBusy(false); }
  if (source?.name === 'exemple-fictif.csv') await run(false);
});
$('schema').value = JSON.stringify([{name:'id',type:'text',required:true},{name:'amount',type:'decimal'}],null,2);
