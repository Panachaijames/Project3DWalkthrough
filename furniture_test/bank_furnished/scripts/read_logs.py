"""Parse the 3ds Max glTF exporter's .glb.log files (boost serialization XML of Autodesk's translation framework, ATF).

    python -B read_logs.py <banquet folder> <out folder>

Writes <out>/glb_logs.json: per log the events in order (by class name), every warning / error message with its severity,
the object counts per stage, the tessellation settings and the processor's options and results.
"""
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


def strs(el):
    return [s.text or '' for s in el.iter('strData')]


def pairs(el):
    """The <v1> key list and <v2> value list pairs directly under el (several pairs may follow each other)."""
    out = {}
    kids = list(el)
    for a, b in zip(kids, kids[1:]):
        if a.tag == 'v1' and b.tag == 'v2':
            keys = [i.find('strData').text if i.find('strData') is not None else (i.text or '') for i in a.findall('item')]
            vals = [i.find('strData').text if i.find('strData') is not None else (i.text or '') for i in b.findall('item')]
            out.update(dict(zip(keys, vals)))
    return out


def parse(path):
    root = ET.parse(path).getroot()
    names = {}
    events, messages, stages, counts = [], [], [], Counter()
    for e in root.findall('e'):
        cid, cref = e.get('class_id'), e.get('class_id_reference')
        if cid is not None:
            names[cid] = e.get('class_name')
        name = names.get(cid if cid is not None else cref, '?')
        events.append(name)
        counts[name] += 1
        if 'Warning' in name or 'Error' in name or e.find('message') is not None:
            sev = e.find('.//m_eventSeverity')
            role = e.find('.//m_role')
            obj = e.find('.//m_objectId/strData')
            msg = e.find('message/strData')
            messages.append({'event': name, 'severity': int(sev.text) if sev is not None else None,
                             'role': int(role.text) if role is not None else None,
                             'object': (obj.text or '') if obj is not None else '', 'message': msg.text if msg is not None else ''})
        if name in ('ObjectCountsWorkdata', 'ProcessorWorkdata'):
            comp = e.find('m_sComponentName/strData')
            svc = e.find('m_sServiceName/strData')
            wd = e.find('WorkdataEvent')
            sev = wd.find('m_severity') if wd is not None else None
            stages.append({'event': name, 'component': comp.text if comp is not None else (svc.text if svc is not None else ''),
                           'severity': int(sev.text) if sev is not None else None,
                           'workdata': pairs(wd) if wd is not None else {}, 'objects': {k: int(v) for k, v in pairs(e).items() if v.isdigit()}})
    return {'events': dict(counts), 'eventOrder': events, 'messages': messages, 'stages': stages}


def main(src, dst):
    res = {}
    for p in sorted(Path(src).glob('*.glb.log')):
        r = parse(p)
        model = p.name[:-len('.glb.log')]
        msgs = Counter((m['event'], m['severity'], m['message']) for m in r['messages'])
        proc = next((s['workdata'] for s in r['stages'] if s['event'] == 'ProcessorWorkdata'), {})
        objs = next((s['objects'] for s in r['stages'] if s['component'] == 'BuildDirectory'), {})
        res[model] = {'file': p.name, 'bytes': p.stat().st_size, 'events': r['events'],
                      'messages': [{'event': e, 'severity': s, 'message': m, 'times': n} for (e, s, m), n in msgs.items()],
                      'errors': sum(n for (e, s, m), n in msgs.items() if 'Error' in e),
                      'warnings': sum(n for (e, s, m), n in msgs.items() if 'Warning' in e),
                      'objectCounts': objs, 'processor': proc,
                      'stages': [{k: v for k, v in s.items() if k != 'event'} for s in r['stages']]}
        print(f"{model:16s} events {r['events']} | objects {objs} | messages {dict(msgs)} | succeeded {proc.get('IsProcessorSucceeded')} "
              f"{proc.get('Producer')} -> {proc.get('Consumer')} {proc.get('Duration(second)')} s, WantMaterial {proc.get('WantMaterial')}")
    Path(dst, 'glb_logs.json').write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
