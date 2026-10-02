"""Build index.html from app.template.html (inlines MapLibre CSS). Run: python3 build.py [--test]
--test also writes a copy that loads ml.js/h3.js/d3.js from the same folder first, for offline headless tests."""
import sys, os
here = os.path.dirname(os.path.abspath(__file__))
t = open(os.path.join(here, 'app.template.html')).read()
T = t.replace('__MLCSS__', open(os.path.join(here, 'mlcss.txt')).read())
open(os.path.join(here, 'index.html'), 'w').write(T)
if '--test' in sys.argv:
    s = T.replace("ml: ['https://cdnjs", "ml: ['ml.js','https://cdnjs").replace("h3: ['https://cdn.jsdelivr", "h3: ['h3.js','https://cdn.jsdelivr").replace("d3: ['https://cdnjs", "d3: ['d3.js','https://cdnjs")
    open(os.path.join(here, 'index.test.html'), 'w').write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>[hidden]{display:none!important}</style></head><body>' + s + '</body></html>')
print('built index.html', len(T))
