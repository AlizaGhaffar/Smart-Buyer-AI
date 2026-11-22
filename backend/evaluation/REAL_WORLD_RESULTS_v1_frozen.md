# Real-world evaluation - v1 (system frozen before labelling)

90 companies from live searches were labelled by blind AI annotators (see LABEL_AGREEMENT.md for the human check), without seeing the system's answer (83 buyer / not_buyer, 7 unsure; unsure rows are left out of the metrics).

Positive = the system says Confirmed / Strong / Possible. Baseline = the original keyword rule.

## All products (n=83)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 65% | 83% |
| Recall | 55% | 57% |
| F1 | 59% | 67% |
| False-positive rate | 78% (18/23) | 30% (7/23) |

## Raw Sheep Wool (n=32)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 22% | 90% |
| Recall | 10% | 45% |
| F1 | 14% | 60% |
| False-positive rate | 58% (7/12) | 8% (1/12) |

## Duck Down (n=27)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 61% | 67% |
| Recall | 55% | 50% |
| F1 | 58% | 57% |
| False-positive rate | 100% (7/7) | 71% (5/7) |

## Cashmere (n=24)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 83% | 94% |
| Recall | 100% | 75% |
| F1 | 91% | 83% |
| False-positive rate | 100% (4/4) | 25% (1/4) |

Of the 60 real buyers, the system marked 11 as *Insufficient Evidence* (mostly non-English or unreachable sites). These count as missed buyers in the recall above.

## Disagreements (33)

| ID | Company | Your label | System | Rules | Notes |
|---|---|---|---|---|---|
| W01 | AndersonTuftex | buyer | not_relevant | G-ROLE1, G-ROLE2, SW-N1 | Shaw-owned flooring maker that crafts carpets and rugs, including wool carpet. |
| W04 | Brockway Carpets | buyer | not_relevant | G-R1, G3a, G3 | Kidderminster manufacturer calling itself 'the home of wool carpet', e.g. Herdwick wool carpets. |
| W05 | Building Renewable | not_buyer | confirmed_purchaser | G-R1, G3a, G6-MIX, SW-P1, SW-P4a, SW-P4c, SW-P5 | Informational blog about sustainable building materials (articles on sheep's wool insulation). |
| W07 | Cormar Carpets | buyer | insufficient_evidence | - | UK carpet manufacturer since 1956 producing wool twist and wool loop ranges. |
| W10 | Halifax Mill | buyer | insufficient_evidence | G-R1, G-R2 | Yorkshire woollen mill that cards and spins fleece into yarn. |
| W14 | ISOLENA Naturfaservliese GmbH | buyer | not_relevant | G-R1, G3a, G3, G6-MIX, SW-P1 | ISOLENA by Lehner Wool, an Austrian manufacturer of 100% sheep's wool insulation and acoustic felt. |
| W17 | RAMPISHAM HILL MILL | buyer | not_relevant | G-R1, G3a, G3, SW-P1, SW-P2 | Semi-worsted spinning mill that scours, cards and spins sheep wool to order. |
| W19 | Residential Carpet & Flooring Australia | buyer | not_relevant | G-R1, G-R2, G3a, G3, G6-MIX, SW-P1 | Godfrey Hirst, a carpet manufacturer in Australia and New Zealand for 160 years, offers wool carpets. |
| W24 | The Wool Spinners | buyer | not_relevant | G-R1, G6-MIX, SW-N2 | Sells wool tops and fleeces and offers custom wool processing ('your wool or ours'). |
| W26 | thenaturalfibre.co.uk | buyer | insufficient_evidence | - | Cornwall spinning mill that processes fleece into yarn and buys wool ('Selling Wool To Us'). |
| W32 | Wilton Carpets | buyer | not_relevant | G-R1, G3a, G3, SW-N2 | UK commercial carpet manufacturer weaving carpets from British wool (80/20 wool-nylon). |
| W34 | Wingham Wool | buyer | not_relevant | - | Sells spinning and felting fibres and makes carded wool batts in its own Gloucestershire mill. |
| D01 | ALLIED | buyer | not_relevant | G-R1, G3a, G3, DD-P2 | Allied Feather + Down sources down directly from farms/abattoirs and processes it (fill power, cleanliness, treatments like ExpeDRY) for brands. |
| D04 | Crescent Down Works | buyer | insufficient_evidence | - | Makes down jackets and vests in its own Seattle factory since 1974, filled with RDS-certified down. |
| D05 | Custom Outdoor Jacket Manufacturer In China | buyer | insufficient_evidence | G-R1, DD-N3 | Chinese OEM factory making custom down jackets with RDS duck or goose down filling (80/20, 90/10) done in-house. |
| D07 | Down Direct | buyer | not_relevant | G6-MIX | Direct-to-consumer store of DOWN Inc. selling down and feather pillows and comforters made in the USA in its own production. |
| D10 | DownTown Company | buyer | not_relevant | G7 | Site states "We manufacture the finest" |
| D11 | Ducko Down | buyer | not_relevant | G-R1, G3a, G3, DD-P2 | Duck processing farm in South Africa that makes and sells its own pure duck down duvets and pillows. |
| D13 | German Down Comforters and Pillows | not_buyer | strong_potential_buyer | G-R1, G6-MIX, DD-P1, DD-P2 | US retailer (European Bliss Inc.) reselling German down comforters made by OBB and other suppliers. |
| D14 | German Down Comforters in the US, cruelty free down, pillows, oeko tex certificate. Matching duvet covers in 135x200cm. Goose down comforters made in Germany from cruelty free harvested down. | not_buyer | strong_potential_buyer | G-R1, DD-P1 | European Bliss Inc. is a US distributor for Ringsted Dun, Hans Kruchen, Braendl and others; it does not manufacture. |
| D15 | German Duvet Covers | not_buyer | strong_potential_buyer | G-R1, DD-P1 | Same European Bliss Inc. distributor site selling German-made duvet covers and down comforters made by others. |
| D18 | lqfeather.com | buyer | insufficient_evidence | - | Liuqiao Group (Hangzhou Xiaoshan) produces down and feather raw material, down bedding and down apparel. |
| D19 | Norvegr | buyer | not_relevant | - | Norwegian family business that handcrafts down duvets and pillows to order in Trondheim (European white goose down seen). |
| D21 | otto-keller.de | buyer | insufficient_evidence | - | Otto Keller is a Bettfedernfabrik since 1946 making down duvets and pillows (including eiderdown) in Germany. |
| D24 | Pillows.com | not_buyer | possible_potential_buyer | G-R1, G6-MIX, DD-P3, DD-N2 | Pillows.com says it 'just retails' hotel bedding products made by others. |
| D27 | Thedowncomforterstore.com | not_buyer | strong_potential_buyer | G-R1, DD-P1 | European Bliss Inc. retail site selling down comforters manufactured in Denmark by Ringsted Dun. |
| D28 | 株式会社イワタ | buyer | insufficient_evidence | G7 | Kyoto maker of made-to-order bedding including goose down futons made in Japan, with its own down research lab (goose only seen). |
| C06 | Beijing Richman Fashion Co., Ltd | buyer | not_relevant | G-R1, G-R2, G3a, G3, G6-MIX, CA-P1, CA-P3 | China-based cashmere knitwear and outerwear manufacturer offering OEM/ODM with factory-direct production. |
| C11 | Cashmere Company | buyer | insufficient_evidence | - | Says it has produced fine cashmere knitwear for two generations using yarns of Inner Mongolian cashmere (yarn only, sells via own shop). |
| C13 | Clean Cashmere | buyer | not_relevant | G-R1, G3a, G3, CA-P1 | Aggregates cashmere from small American member farms to produce and sell its own cashmere yarn lines. |
| C17 | Italy Cashmere | buyer | insufficient_evidence | - | Small Italian firm producing cashmere knitwear on Shima machines for retail, B2B and private label (yarn only). |
| C22 | Sustainable Industries | not_buyer | possible_potential_buyer | G-R1, G-R2, G6-MIX, CA-P4 | Sustainable supplier-discovery and digital product passport platform; not a manufacturer. |
| C23 | wfscashmere.com | buyer | insufficient_evidence | - | China-based vertically integrated cashmere knitwear OEM/ODM manufacturer, 3-18 gauge. |
