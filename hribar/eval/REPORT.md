# Hribar weekly report — 2026-10-12

Finds scored: iNaturalist records in Romania, 2023-12-01 to 2026-10-12; 56 species with 15+ finds. Weather: era5_land.json. Each year is scored with habitat preferences fitted on the other years (cross-fitted hold-out).

| Term | Median AUC | Weighted AUC |
| --- | --- | --- |
| Habitat | 0.657 | 0.681 |
| Season | 0.652 | 0.627 |
| Habitat × season | 0.722 | 0.732 |
| Weather | 0.571 | 0.568 |
| Full forecast | 0.728 | 0.707 |

Reliability: 24 good, 16 useful, 16 weak. Learned habitat shipped for 203 species (75 Romanian models, 128 from neighbouring countries).

| Species | Finds | Habitat | Weather | Full | Level |
| --- | --- | --- | --- | --- | --- |
| Sarcodon imbricatus | 21 | 0.76 | 0.57 | 0.87 | good |
| Agrocybe praecox | 20 | 0.57 | 0.75 | 0.86 | good |
| Amanita regalis | 68 | 0.83 | 0.66 | 0.85 | good |
| Macrolepiota mastoidea | 23 | 0.65 | 0.73 | 0.84 | good |
| Coprinopsis picacea | 68 | 0.74 | 0.70 | 0.83 | good |
| Lactifluus piperatus | 29 | 0.79 | 0.57 | 0.82 | good |
| Amanita citrina | 16 | 0.76 | 0.62 | 0.82 | good |
| Imleria badia | 18 | 0.79 | 0.59 | 0.81 | good |
| Amanita excelsa | 50 | 0.79 | 0.67 | 0.81 | good |
| Russula integra | 20 | 0.78 | 0.54 | 0.80 | good |
| Amanita muscaria | 194 | 0.83 | 0.55 | 0.79 | good |
| Neoboletus erythropus | 51 | 0.73 | 0.68 | 0.78 | good |
| Suillellus luridus | 23 | 0.69 | 0.61 | 0.78 | good |
| Russula virescens | 23 | 0.73 | 0.58 | 0.77 | good |
| Infundibulicybe geotropa | 17 | 0.56 | 0.68 | 0.77 | good |
| Chalciporus piperatus | 18 | 0.66 | 0.65 | 0.77 | good |
| Caloboletus calopus | 29 | 0.81 | 0.50 | 0.77 | good |
| Agaricus campestris | 34 | 0.79 | 0.65 | 0.77 | good |
| Marasmius oreades | 65 | 0.74 | 0.67 | 0.76 | good |
| Lactarius deterrimus | 33 | 0.77 | 0.57 | 0.76 | good |
| Russula cyanoxantha | 33 | 0.64 | 0.65 | 0.75 | good |
| Clitocybe nebularis | 22 | 0.62 | 0.51 | 0.75 | good |
| Megacollybia platyphylla | 38 | 0.68 | 0.70 | 0.75 | good |
| Hypholoma lateritium | 20 | 0.55 | 0.58 | 0.75 | good |
| Coprinellus micaceus | 94 | 0.71 | 0.61 | 0.75 | useful |
| Boletus edulis | 60 | 0.80 | 0.48 | 0.74 | useful |
| Cantharellus cibarius | 49 | 0.79 | 0.56 | 0.74 | useful |
| Mycena pura | 36 | 0.71 | 0.64 | 0.73 | useful |
| Boletus reticulatus | 56 | 0.70 | 0.56 | 0.72 | useful |
| Russula vesca | 35 | 0.63 | 0.57 | 0.72 | useful |
| Amanita rubescens | 128 | 0.63 | 0.58 | 0.71 | useful |
| Lycoperdon perlatum | 92 | 0.64 | 0.56 | 0.70 | useful |
| Phallus impudicus | 34 | 0.60 | 0.59 | 0.70 | useful |
| Amanita pantherina | 37 | 0.61 | 0.64 | 0.69 | useful |
| Leccinellum pseudoscabrum | 16 | 0.65 | 0.49 | 0.69 | useful |
| Macrolepiota procera | 98 | 0.57 | 0.53 | 0.69 | useful |
| Armillaria mellea | 20 | 0.53 | 0.56 | 0.69 | useful |
| Russula foetens | 17 | 0.66 | 0.48 | 0.67 | useful |
| Omphalotus olearius | 29 | 0.74 | 0.59 | 0.67 | useful |
| Lepiota cristata | 15 | 0.52 | 0.47 | 0.67 | useful |
| Coprinus comatus | 67 | 0.67 | 0.53 | 0.64 | weak |
| Xerocomellus chrysenteron | 25 | 0.48 | 0.65 | 0.63 | weak |
| Hypholoma fasciculare | 103 | 0.59 | 0.59 | 0.63 | weak |
| Apioperdon pyriforme | 29 | 0.71 | 0.53 | 0.63 | weak |
| Paxillus involutus | 22 | 0.55 | 0.61 | 0.62 | weak |
| Pleurotus ostreatus | 62 | 0.62 | 0.48 | 0.62 | weak |
| Lactifluus volemus | 25 | 0.64 | 0.48 | 0.61 | weak |
| Hericium coralloides | 25 | 0.58 | 0.45 | 0.61 | weak |
| Laetiporus sulphureus | 98 | 0.63 | 0.49 | 0.60 | weak |
| Pluteus cervinus | 47 | 0.60 | 0.55 | 0.59 | weak |
| Laccaria laccata | 16 | 0.53 | 0.56 | 0.58 | weak |
| Auricularia auricula-judae | 116 | 0.66 | 0.44 | 0.56 | weak |
| Xerocomus subtomentosus | 26 | 0.53 | 0.49 | 0.56 | weak |
| Volvariella bombycina | 21 | 0.76 | 0.33 | 0.55 | weak |
| Agaricus sylvaticus | 16 | 0.44 | 0.52 | 0.54 | weak |
| Cerioporus squamosus | 64 | 0.59 | 0.43 | 0.52 | weak |
