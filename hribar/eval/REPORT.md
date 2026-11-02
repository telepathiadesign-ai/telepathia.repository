# Hribar weekly report — 2026-11-02

Finds scored: iNaturalist records in Romania, 2023-12-01 to 2026-11-02; 66 species with 15+ finds. Weather: hist_forecast.json. Each year is scored with habitat preferences fitted on the other years (cross-fitted hold-out).

| Term | Median AUC | Weighted AUC |
| --- | --- | --- |
| Habitat | 0.706 | 0.718 |
| Season | 0.649 | 0.627 |
| Habitat × season | 0.768 | 0.763 |
| Weather | 0.573 | 0.570 |
| Full forecast | 0.750 | 0.740 |

Reliability: 33 good, 27 useful, 6 weak. Learned habitat shipped for 250 species (250 Romanian models, 174 climate-niche models from finds across Europe).

| Species | Finds | Habitat | Weather | Full | Level |
| --- | --- | --- | --- | --- | --- |
| Amanita regalis | 71 | 0.88 | 0.67 | 0.92 | good |
| Morchella esculenta | 22 | 0.83 | 0.58 | 0.92 | good |
| Panaeolus papilionaceus | 17 | 0.84 | 0.74 | 0.91 | good |
| Sarcodon imbricatus | 22 | 0.83 | 0.47 | 0.89 | good |
| Amanita citrina | 19 | 0.81 | 0.59 | 0.85 | good |
| Fistulina hepatica | 27 | 0.81 | 0.47 | 0.85 | good |
| Agrocybe praecox | 25 | 0.57 | 0.72 | 0.85 | good |
| Macrolepiota mastoidea | 29 | 0.69 | 0.70 | 0.84 | good |
| Amanita excelsa | 51 | 0.83 | 0.62 | 0.84 | good |
| Imleria badia | 18 | 0.81 | 0.53 | 0.83 | good |
| Russula integra | 20 | 0.83 | 0.45 | 0.83 | good |
| Coprinopsis picacea | 89 | 0.79 | 0.71 | 0.83 | good |
| Suillellus luridus | 24 | 0.68 | 0.67 | 0.83 | good |
| Agaricus arvensis | 17 | 0.76 | 0.70 | 0.82 | good |
| Russula virescens | 28 | 0.74 | 0.58 | 0.81 | good |
| Chalciporus piperatus | 25 | 0.86 | 0.55 | 0.81 | good |
| Amanita muscaria | 223 | 0.84 | 0.53 | 0.81 | good |
| Infundibulicybe geotropa | 25 | 0.64 | 0.68 | 0.81 | good |
| Neoboletus erythropus | 57 | 0.76 | 0.65 | 0.81 | good |
| Russula cyanoxantha | 41 | 0.71 | 0.65 | 0.80 | good |
| Lactifluus piperatus | 40 | 0.80 | 0.48 | 0.80 | good |
| Megacollybia platyphylla | 38 | 0.70 | 0.72 | 0.79 | good |
| Hypholoma lateritium | 23 | 0.67 | 0.58 | 0.79 | good |
| Boletus edulis | 71 | 0.82 | 0.49 | 0.79 | good |
| Caloboletus calopus | 31 | 0.81 | 0.51 | 0.79 | good |
| Cantharellus cibarius | 57 | 0.77 | 0.55 | 0.78 | good |
| Leccinellum pseudoscabrum | 17 | 0.70 | 0.60 | 0.78 | good |
| Boletus reticulatus | 66 | 0.73 | 0.57 | 0.78 | good |
| Marasmius oreades | 86 | 0.74 | 0.69 | 0.77 | good |
| Coprinellus micaceus | 118 | 0.77 | 0.62 | 0.76 | good |
| Agaricus campestris | 51 | 0.80 | 0.66 | 0.76 | good |
| Coprinopsis atramentaria | 21 | 0.69 | 0.64 | 0.76 | good |
| Clitocybe nebularis | 24 | 0.64 | 0.50 | 0.75 | good |
| Amanita rubescens | 145 | 0.66 | 0.60 | 0.75 | useful |
| Lactarius deterrimus | 38 | 0.81 | 0.48 | 0.74 | useful |
| Phallus impudicus | 38 | 0.61 | 0.61 | 0.73 | useful |
| Clitopilus prunulus | 20 | 0.72 | 0.58 | 0.73 | useful |
| Amanita pantherina | 44 | 0.66 | 0.66 | 0.73 | useful |
| Chlorophyllum rhacodes | 21 | 0.71 | 0.59 | 0.72 | useful |
| Hericium coralloides | 34 | 0.64 | 0.57 | 0.72 | useful |
| Mycena pura | 40 | 0.71 | 0.60 | 0.72 | useful |
| Pleurotus ostreatus | 92 | 0.70 | 0.54 | 0.72 | useful |
| Omphalotus olearius | 35 | 0.77 | 0.58 | 0.71 | useful |
| Armillaria mellea | 29 | 0.64 | 0.55 | 0.70 | useful |
| Volvariella bombycina | 26 | 0.80 | 0.39 | 0.70 | useful |
| Russula vesca | 40 | 0.58 | 0.59 | 0.70 | useful |
| Lycoperdon perlatum | 111 | 0.65 | 0.54 | 0.70 | useful |
| Coprinus comatus | 98 | 0.71 | 0.55 | 0.70 | useful |
| Russula foetens | 18 | 0.70 | 0.46 | 0.69 | useful |
| Macrolepiota procera | 137 | 0.63 | 0.51 | 0.69 | useful |
| Meripilus giganteus | 15 | 0.70 | 0.45 | 0.69 | useful |
| Lactifluus volemus | 29 | 0.67 | 0.53 | 0.69 | useful |
| Pleurotus pulmonarius | 21 | 0.75 | 0.50 | 0.69 | useful |
| Laccaria laccata | 20 | 0.74 | 0.51 | 0.69 | useful |
| Pholiota squarrosa | 15 | 0.63 | 0.53 | 0.68 | useful |
| Hypholoma fasciculare | 111 | 0.62 | 0.61 | 0.68 | useful |
| Laetiporus sulphureus | 139 | 0.67 | 0.53 | 0.66 | useful |
| Lepiota cristata | 16 | 0.65 | 0.46 | 0.66 | useful |
| Paxillus involutus | 26 | 0.53 | 0.63 | 0.65 | useful |
| Cerioporus squamosus | 86 | 0.68 | 0.51 | 0.65 | useful |
| Xerocomellus chrysenteron | 31 | 0.52 | 0.66 | 0.64 | weak |
| Apioperdon pyriforme | 32 | 0.67 | 0.47 | 0.63 | weak |
| Auricularia auricula-judae | 145 | 0.69 | 0.48 | 0.60 | weak |
| Pluteus cervinus | 54 | 0.64 | 0.52 | 0.59 | weak |
| Xerocomus subtomentosus | 31 | 0.59 | 0.43 | 0.57 | weak |
| Agaricus sylvaticus | 18 | 0.53 | 0.57 | 0.55 | weak |
