#!/usr/bin/env python3
"""Validate print characteristics, vector content and BPMN structure."""
import json,pathlib,csv
from PIL import Image
from pypdf import PdfReader,PdfWriter
from lxml import etree
ROOT=pathlib.Path(__file__).resolve().parents[1]
report={'files':[]}
manifest=json.loads((ROOT/'graph_manifest.json').read_text())
manifest.append({'name':'planned_pipeline','png_pixels':[14400,6000],'width_in':24,'height_in':10,'png_dpi':600})
writer=PdfWriter()
for item in manifest:
 folder=ROOT/('pipeline' if item['name']=='planned_pipeline' else 'graphs')
 png=folder/(item['name']+'.png');pdf=folder/(item['name']+'.pdf');svg=folder/(item['name']+'.svg')
 with Image.open(png) as im:
  assert list(im.size)==item['png_pixels'],(png,im.size)
  dpi=im.info.get('dpi');assert dpi and all(abs(d-600)<1 for d in dpi),(png,dpi)
  im.verify()
 reader=PdfReader(pdf);assert len(reader.pages)==1
 page=reader.pages[0];width=float(page.mediabox.width);height=float(page.mediabox.height)
 assert abs(width-item['width_in']*72)<.1 and abs(height-item['height_in']*72)<.1
 resources=page['/Resources'].get_object();fonts=resources.get('/Font',{}).get_object();embedded=[]
 for _,ref in fonts.items():
  font=ref.get_object()
  if font.get('/Subtype')=='/Type0':font=font['/DescendantFonts'][0].get_object()
  descriptor=font.get('/FontDescriptor')
  assert descriptor is not None,(pdf,'Font lacks descriptor')
  descriptor=descriptor.get_object();has_font=any(k in descriptor for k in ['/FontFile','/FontFile2','/FontFile3'])
  assert has_font,(pdf,'Font is not embedded')
  embedded.append(str(font.get('/BaseFont')))
 assert embedded
 for _,obj in resources.get('/XObject',{}).get_object().items() if hasattr(resources.get('/XObject',{}),'get_object') else resources.get('/XObject',{}).items():
  assert obj.get_object().get('/Subtype')!='/Image',(pdf,'Raster image found in vector master')
 sv=etree.parse(str(svg));assert not sv.xpath('//*[local-name()="image"]'),(svg,'Raster image in SVG')
 writer.append(str(pdf))
 report['files'].append({'name':item['name'],'png_pixels':item['png_pixels'],'png_dpi':list(dpi),
  'pdf_page_points':[width,height],'embedded_fonts':embedded,'vector_pdf':True,'vector_svg':True})
writer.write(ROOT/'all_poster_assets.pdf')
schema=etree.XMLSchema(etree.parse(str(ROOT/'source/bpmn-schema/BPMN20.xsd')))
doc=etree.parse(str(ROOT/'pipeline/planned_pipeline.bpmn'))
assert schema.validate(doc),str(schema.error_log)
NS={'b':'http://www.omg.org/spec/BPMN/20100524/MODEL','di':'http://www.omg.org/spec/BPMN/20100524/DI'}
ids=[x.get('id') for x in doc.iter() if x.get('id')];assert len(ids)==len(set(ids))
idset=set(ids)
for x in doc.xpath('//b:sequenceFlow|//b:association',namespaces=NS):
 assert x.get('sourceRef') in idset and x.get('targetRef') in idset
flows=doc.xpath('//b:sequenceFlow',namespaces=NS)
def degree(id,key):return sum(x.get(key)==id for x in flows)
assert degree('fork','sourceRef')==2 and degree('fork','targetRef')==1
assert degree('join','sourceRef')==1 and degree('join','targetRef')==2
assert doc.xpath('//b:subProcess/b:multiInstanceLoopCharacteristics[@isSequential="true"]',namespaces=NS)
assert doc.xpath('//b:boundaryEvent[@attachedToRef="trial"][@cancelActivity="true"]/b:errorEventDefinition',namespaces=NS)
assert doc.xpath('//di:BPMNShape[@bpmnElement="trial"][@isExpanded="true"]',namespaces=NS)
for x in doc.xpath('//b:startEvent',namespaces=NS):assert degree(x.get('id'),'targetRef')==0
for x in doc.xpath('//b:endEvent',namespaces=NS):assert degree(x.get('id'),'sourceRef')==0
rows=list(csv.DictReader((ROOT/'data/runs.csv').open()));assert len(rows)==32
assert all(sum(float(x['duration_s'])==d for x in rows)==8 for d in [15,30,60,120])
report.update({'bpmn_2_0_xsd_valid':True,'bpmn_structure_valid':True,'input_runs':32,'input_repetitions_per_duration':8,
 'combined_pdf_pages':len(PdfReader(ROOT/'all_poster_assets.pdf').pages)})
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: five vector PDF/SVG masters, embedded fonts, all PNGs at 600 DPI with expected dimensions, BPMN official-XSD and structural checks, 32 input runs.')
