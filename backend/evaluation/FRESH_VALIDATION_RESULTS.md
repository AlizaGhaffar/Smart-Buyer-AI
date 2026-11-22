# Fresh validation: new companies, system frozen at git tag v2-tuned

58 companies from live searches were labelled by blind AI annotators, without seeing the system's answer (55 buyer / not_buyer, 3 unsure; unsure rows are left out of the metrics).

Positive = the system says Confirmed / Strong / Possible. Baseline = the original keyword rule.

## All products (n=55)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 68% | 90% |
| Recall | 55% | 43% |
| F1 | 61% | 58% |
| False-positive rate | 85% (11/13) | 15% (2/13) |

## Raw Sheep Wool (n=11)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 0% | 100% |
| Recall | 0% | 50% |
| F1 | 0% | 67% |
| False-positive rate | 100% (3/3) | 0% (0/3) |

## Duck Down (n=26)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 86% | 89% |
| Recall | 52% | 35% |
| F1 | 65% | 50% |
| False-positive rate | 67% (2/3) | 33% (1/3) |

## Cashmere (n=18)

| Metric | Old keyword baseline | KRR system |
|---|---|---|
| Precision | 65% | 86% |
| Recall | 100% | 55% |
| F1 | 79% | 67% |
| False-positive rate | 86% (6/7) | 14% (1/7) |

Of the 42 real buyers, the system marked 10 as *Insufficient Evidence* (mostly non-English or unreachable sites). These count as missed buyers in the recall above.

## Disagreements (26)

| ID | Company | Your label | System | Rules | Notes |
|---|---|---|---|---|---|
| FW04 | Filatura Papi Fabio, filati cardati e pettinati di alta gamma | buyer | not_relevant | - | Italian spinning mill (woollen and worsted spinning) producing superfine wool yarns at about 1M kg/year. |
| FW05 | filaturac4.it | buyer | insufficient_evidence | - | Spinning mill whose raw materials page lists natural fibres such as wool, plus linen, silk and synthetics. |
| FW07 | lanificio bottoli | buyer | not_relevant | - | Vertically integrated wool mill since 1861 weaving fabrics from selected wool fleeces in natural shades. |
| FW08 | Marcoliani Milano | buyer | not_relevant | G-ROLE2, SW-N1 | Sock manufacturer knitting socks from fine yarns (e.g. extrafine merino) bought from Italian yarn producers; buys yarn rather than raw fibre. |
| FD03 | Aura Down Bedding | buyer | not_relevant | - | Hand-sewn duvets and pillows filled with Hungarian goose and duck down in its own atelier in Mezőkovácsháza. |
| FD04 | BekesTex Trade LTD. | buyer | insufficient_evidence | G-R1, DD-N3 | Hungarian OEM/ODM sewing plant specialised in down jackets (tollkabát) and outerwear. |
| FD05 | Downright | buyer | not_relevant | G6-MIX, DD-N2 | Down comforters and pillows handcrafted in New York for 50 years. |
| FD06 | Eiderdown & Z Land Bedding | buyer | not_relevant | - | RDS-certified New Zealand-made comforters and pillows filled with Hungarian goose and duck down. |
| FD07 | Elfenbein Bedding | buyer | not_relevant | DD-N2 | Hand-made Hungarian goose down comforters and pillows since 1957; goose only. |
| FD08 | en.puhslowinscy.pl | buyer | not_relevant | - | Processes and trades Polish and imported goose and duck down and feather (washing and sorting). |
| FD09 | en.pyzynski.pl | buyer | insufficient_evidence | - | en. subdomain failed but pyzynski.pl loaded: feather processing plant (Zakład Pierzarski), RDS-certified down. |
| FD10 | Fashion Coats & Jackets | buyer | insufficient_evidence | G-R1, DD-N3 | Chinese OEM apparel manufacturer whose product lines include down jackets and parkas. |
| FD11 | FBZ Group | buyer | insufficient_evidence | - | Describes itself as the largest down and feather manufacturer in Central Europe processing Hungarian goose and duck down. |
| FD14 | Federacja Eksporterów Polskiego Puchu i Pierza | not_buyer | possible_potential_buyer | G-R1, DD-P3, DD-N2 | Trade federation of Polish down and feather exporters. |
| FD17 | Hamvay-Láng | buyer | not_relevant | G-ROLE1, DD-N2, DD-N4 | Family company making Hungarian goose down bedding and cleaning the down itself; goose only. |
| FD20 | Luxury Sweet Dreams | buyer | not_relevant | G-ROLE1, DD-N4 | Supplier and processor of Polish goose down and goose/duck down-feather blends that also makes duvets. |
| FD21 | Minatex - Külkereskedelmi tanácsadás; lakástextil export-import | buyer | not_relevant | G-R2 | Hungarian trading/agency firm that exports and imports raw and washed down and feather fillings. |
| FD22 | Naturtex Wool Feather and Down Processing Ltd. | buyer | not_relevant | DD-N2 | Wool feather and down processing company making quilts and pillows and wholesaling raw material. |
| FD26 | Poldaun - producent najlepszych kołder i poduszek | buyer | insufficient_evidence | - | Polish duvet and pillow producer offering goose and duck down filled products. |
| FD28 | TATRA DUVET | buyer | not_relevant | DD-N2 | Polish producer of goose down duvets/pillows with RDS-certified down plant; goose only. |
| FC02 | Crafty Fibres | buyer | not_relevant | G6-MIX | Bradford supplier of natural crafting fibres that stocks and resells cashmere fibre for hand crafters (fibre trader; small scale). |
| FC03 | Croft Mill | not_buyer | possible_potential_buyer | G-R1, G6-MIX, CA-P4 | Online fabric retailer selling dress fabrics including cashmere fabric made by others; no own production. |
| FC07 | innowearcashmere.com | buyer | insufficient_evidence | - | Mauritius cashmere knitwear manufacturer with own factory, custom production and custom-created yarn. |
| FC14 | Scottish Cashmere Collection | buyer | insufficient_evidence | G-R1, G6-MIX, CA-P4 | Small Hawick family business that hand-makes cashmere gloves, scarves and accessories, buying yarn in small batches (yarn only; small scale). |
| FC16 | Velora Cashmere | buyer | insufficient_evidence | - | Supplier of Afghan dehaired carded cashmere sliver (200 MT capacity) to mills and spinners; raw-fibre trader/processor (page title/meta only). |
| FC19 | Z. Hinchliffe & Sons | buyer | insufficient_evidence | G-R1, G6-MIX, CA-P2b | Huddersfield spinner since 1766 that sources dehaired cashmere from China/Inner Mongolia and dyes, cards and spins it into yarn. |
