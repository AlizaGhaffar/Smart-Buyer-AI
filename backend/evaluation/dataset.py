"""Manually labelled evaluation dataset (fictional companies, hand-written pages).

Written BEFORE the extractor was implemented. Split:
  dev  - may be looked at while developing the extractor
  test - held out; the extractor must not be tuned on these cases

`expected` is the manual label (one of the five classes). For the binary
metrics the classes confirmed/strong/possible count as "positive".

Each case:
  id, product, split, category, expected, note,
  title, snippet       - what DuckDuckGo would have shown
  pages                - fetched own-site pages [(url, page_type, text)];
                         empty list = website unreachable
"""

CONFIRMED = "confirmed_purchaser"
STRONG = "strong_potential_buyer"
POSSIBLE = "possible_potential_buyer"
INSUFFICIENT = "insufficient_evidence"
NOT_RELEVANT = "not_relevant"


def page(host, path, page_type, text):
    return (f"https://{host}/{path}", page_type, " ".join(text.split()))


CASES = [
    # ======================================================== DUCK DOWN ====
    dict(id="DD01", product="duck_down", split="dev", category="relevant", expected=STRONG,
         note="Duvet maker, duck down named on products page",
         title="Northwind Bedding - Duvets and Pillows", snippet="Duvet and pillow manufacturer supplying hotels.",
         pages=[
             page("northwind-bedding.test", "about", "about", """
                Founded in 1994, Northwind Bedding manufactures duvets, pillows and mattress toppers in
                our own factory near Gdansk, Poland. We supply hotels, retailers and distributors across
                Europe and employ 120 skilled people in cutting, filling and quilting."""),
             page("northwind-bedding.test", "products", "products", """
                Our Premium duvet is filled with 90% white duck down and 10% duck feather. Each duvet is
                box-stitched to keep the filling evenly spread. Our Hotel pillow uses the same duck down
                and feather blend and is available in soft and firm versions."""),
         ]),
    dict(id="DD02", product="duck_down", split="dev", category="relevant", expected=CONFIRMED,
         note="Down processor with explicit sourcing statement",
         title="Pannonia Down Processing", snippet="Washing and sorting of down and feather.",
         pages=[
             page("pannonia-down.test", "about", "about", """
                Pannonia Down operates a processing plant in Hungary where we wash, sort and grade down and
                feather for the bedding industry. Our laboratory tests fill power, cleanliness and oxygen
                number for every lot."""),
             page("pannonia-down.test", "sourcing", "sourcing", """
                We source raw duck down directly from farms in Hungary and Poland. All suppliers are audited
                for animal welfare. After processing we deliver graded down to bedding manufacturers
                in Germany and Austria."""),
         ]),
    dict(id="DD03", product="duck_down", split="dev", category="alternative_material", expected=NOT_RELEVANT,
         note="Synthetic-only bedding maker",
         title="PureSleep Hypoallergenic Bedding", snippet="Bedding manufacturer, distributors welcome.",
         pages=[
             page("puresleep.test", "about", "about", """
                PureSleep is a duvet manufacturer based in Leeds. All our duvets and pillows are filled with
                100% polyester hollow fibre, which is fully washable and suitable for allergy sufferers.
                We do not use any animal products. Distributors and wholesalers are welcome to contact us."""),
         ]),
    dict(id="DD04", product="duck_down", split="dev", category="related_material", expected=POSSIBLE,
         note="Goose down only",
         title="Danube Goose Down Duvets", snippet="Luxury duvet manufacturer.",
         pages=[
             page("danube-duvets.test", "about", "about", """
                At our workshop in Szeged we manufacture luxury duvets and pillows by hand. Our duvets are
                filled with Hungarian white goose down with a fill power of 750. We have been making
                bedding for four generations and sell to hotels and boutiques."""),
         ]),
    dict(id="DD05", product="duck_down", split="dev", category="insufficient", expected=INSUFFICIENT,
         note="Pillow maker, no filling material stated",
         title="Comfort Cushions Ltd", snippet="Pillow manufacturer for hospitality.",
         pages=[
             page("comfort-cushions.test", "about", "about", """
                Comfort Cushions manufactures pillows and seat cushions for the hospitality sector. Our
                factory in Porto produces more than 2,000 pillows per day in standard and custom sizes.
                We offer private label packaging and fast delivery across Europe."""),
         ]),
    dict(id="DD06", product="duck_down", split="dev", category="retailer", expected=NOT_RELEVANT,
         note="Online retailer of finished duck down products",
         title="Sleepwell Store - Duck Down Duvets", snippet="Buy duck down duvets online.",
         pages=[
             page("sleepwell-store.test", "", "homepage", """
                Shop our collection of duck down duvets and pillows. Free delivery on orders over 50 euros
                and free returns within 30 days. Our online shop offers the best brands at great prices.
                Sign up to our newsletter for exclusive offers on bedding."""),
         ]),
    dict(id="DD07", product="duck_down", split="dev", category="irrelevant", expected=NOT_RELEVANT,
         note="Restaurant with buyer-like words (the original false-positive example)",
         title="Osaka Duck House Restaurant", snippet="Roast duck restaurant. Purchasing and wholesale inquiries.",
         pages=[
             page("osaka-duck-house.test", "", "homepage", """
                Welcome to Osaka Duck House. Our restaurant serves roast duck, duck ramen and seasonal
                dishes made with local vegetables. We are open every day; the kitchen shuts down at 10pm.
                For catering and wholesale inquiries please contact our purchasing team."""),
         ]),
    dict(id="DD08", product="duck_down", split="dev", category="unreachable", expected=INSUFFICIENT,
         note="Website could not be fetched; only the search snippet exists",
         title="Duck Down Importer Japan", snippet="Duck down duvet manufacturer and importer.",
         pages=[]),
    dict(id="DD09", product="duck_down", split="dev", category="conflicting", expected=INSUFFICIENT,
         note="Duck down on one page, polyester-only on another",
         title="Softrest Home Duvets", snippet="Duvet manufacturer.",
         pages=[
             page("softrest.test", "products", "products", """
                Luxury duck down duvets for a perfect night. Our duvets are made in our own factory in
                Lithuania and come in three warmth ratings, from summer to winter."""),
             page("softrest.test", "about", "about", """
                Softrest manufactures duvets for the European market. All our duvets use hypoallergenic
                polyester fill, because we believe in easy care bedding for everyone."""),
         ]),
    dict(id="DD10", product="duck_down", split="dev", category="relevant_partial", expected=POSSIBLE,
         note="Down jacket maker, species not stated",
         title="Saigon Outerwear Co.", snippet="Down jacket OEM factory.",
         pages=[
             page("saigon-outerwear.test", "about", "about", """
                Saigon Outerwear manufactures down jackets, parkas and vests for international brands in
                our factory in Ho Chi Minh City. Our jackets are insulated with responsibly sourced natural
                down. We offer OEM and ODM services with a minimum order of 500 pieces."""),
         ]),
    dict(id="DD11", product="duck_down", split="test", category="relevant", expected=STRONG,
         note="Sleeping bag workshop, grey duck down",
         title="Alpine Loft Sleeping Bags", snippet="Handmade expedition sleeping bags.",
         pages=[
             page("alpine-loft.test", "about", "about", """
                Our workshop in Kranj, Slovenia, hand-builds sleeping bags for mountaineers and polar
                expeditions. Every bag is filled with grey duck down with 650 fill power and sewn by our
                own team of twelve. We also repair and refill older bags."""),
         ]),
    dict(id="DD12", product="duck_down", split="test", category="non_english", expected=INSUFFICIENT,
         note="German-only website",
         title="Daunen Bettdecken GmbH", snippet="Duck Down Bettdecken Hersteller.",
         pages=[
             page("daunen-bettdecken.test", "", "homepage", """
                Wir stellen seit 1980 hochwertige Bettdecken und Kopfkissen in unserer eigenen Manufaktur
                her. Unsere Daunendecken sind mit Entendaunen gefüllt und werden in Deutschland genäht.
                Wir beliefern Hotels und den Fachhandel in ganz Europa."""),
         ]),
    dict(id="DD13", product="duck_down", split="test", category="relevant_mixed", expected=STRONG,
         note="Duck down range plus a separate synthetic range",
         title="Nordic Nights Bedding", snippet="Duvets and pillows manufacturer.",
         pages=[
             page("nordic-nights.test", "about", "about", """
                Nordic Nights manufactures duvets and pillows at our factory in Aarhus, Denmark. Our Classic
                range is filled with white duck down, while our Allergy range uses a down-alternative
                microfibre fill. Both ranges are certified to Oeko-Tex standards."""),
         ]),
    dict(id="DD14", product="duck_down", split="test", category="relevant", expected=CONFIRMED,
         note="Down & feather trader who buys duck down",
         title="Pacific Feather Trading", snippet="Importers and distributors of down and feather.",
         pages=[
             page("pacific-feather.test", "about", "about", """
                Pacific Feather Trading is an importer and distributor of down and feather for the bedding
                and outdoor industries. We buy washed duck down from processors in China and Vietnam and
                supply it to duvet and jacket manufacturers in Japan and Korea. Every shipment is tested
                by an independent laboratory."""),
         ]),
    dict(id="DD15", product="duck_down", split="test", category="retailer", expected=NOT_RELEVANT,
         note="Importer of finished bedding (no manufacturing)",
         title="Tokyo Home Imports", snippet="Importer and distributor of bedding.",
         pages=[
             page("tokyo-home-imports.test", "about", "about", """
                Tokyo Home Imports is an importer and distributor of finished bedding products. We bring
                duvets, pillows and blankets from European brands to department stores and our online shop
                in Japan. Our catalogue includes more than 300 products."""),
         ]),
    dict(id="DD16", product="duck_down", split="test", category="supplier", expected=NOT_RELEVANT,
         note="Duck farm selling its down",
         title="Green Valley Duck Farm", snippet="Pekin duck farm.",
         pages=[
             page("greenvalley-duck.test", "about", "about", """
                Green Valley is a family duck farm raising Pekin ducks in Anhui province. We sell duck down
                and feathers to processing plants after every season and also supply fresh meat to local
                markets. Visitors are welcome by appointment."""),
         ]),

    # =================================================== RAW SHEEP WOOL ====
    dict(id="SW01", product="raw_sheep_wool", split="dev", category="relevant", expected=STRONG,
         note="Wool scourer",
         title="Bradford Wool Scourers", snippet="Wool scouring since 1952.",
         pages=[
             page("bradford-scourers.test", "about", "about", """
                Since 1952 Bradford Wool Scourers has operated a scouring plant in West Yorkshire. Our
                plant scours greasy wool and produces clean scoured wool and wool tops for spinners in the
                UK and Italy. We handle more than 15,000 tonnes per year."""),
         ]),
    dict(id="SW02", product="raw_sheep_wool", split="dev", category="relevant", expected=CONFIRMED,
         note="Spinner that buys greasy wool from growers",
         title="Highland Spinners", snippet="Worsted yarn spinning mill in Scotland.",
         pages=[
             page("highland-spinners.test", "about", "about", """
                Highland Spinners operates a spinning mill in Inverness producing worsted yarns for
                weavers and knitters. Our spinning mill uses scoured wool from our own scouring line."""),
             page("highland-spinners.test", "sourcing", "sourcing", """
                We buy greasy wool directly from growers in New Zealand and Australia every season and
                ship it to Scotland. Long-term relationships with growers give us consistent fibre quality
                and full traceability."""),
         ]),
    dict(id="SW03", product="raw_sheep_wool", split="dev", category="retailer", expected=NOT_RELEVANT,
         note="Online retailer of wool garments",
         title="Woolly Wardrobe", snippet="Merino wool jumpers and socks.",
         pages=[
             page("woolly-wardrobe.test", "", "homepage", """
                Discover our range of merino wool jumpers, scarves and socks. Shop online with free
                returns and next day delivery. Our online shop is updated every week with new colours.
                Join our newsletter and get 10% off your first order."""),
         ]),
    dict(id="SW04", product="raw_sheep_wool", split="dev", category="alternative_material", expected=NOT_RELEVANT,
         note="Wool-look synthetic carpets",
         title="Budget Carpets Ltd", snippet="Carpet manufacturer, wholesalers and distributors.",
         pages=[
             page("budget-carpets.test", "about", "about", """
                Budget Carpets manufactures wool-look carpets for homes and offices at our mill in Kidderminster.
                Our carpets are made from 100% polypropylene and acrylic fibres, which are stain resistant
                and affordable. We supply wholesalers and distributors nationwide."""),
         ]),
    dict(id="SW05", product="raw_sheep_wool", split="dev", category="supplier", expected=NOT_RELEVANT,
         note="Sheep station selling its wool clip",
         title="Canterbury Merino Station", snippet="Merino sheep station.",
         pages=[
             page("canterbury-merino.test", "about", "about", """
                Our sheep station in Canterbury, New Zealand, runs 5,000 Merino ewes on hill country. We
                sell our wool clip through brokers each season and take part in the national ram sales.
                The station has been in our family since 1921."""),
         ]),
    dict(id="SW06", product="raw_sheep_wool", split="dev", category="irrelevant", expected=NOT_RELEVANT,
         note="Hotel with a purchasing department",
         title="Kyoto Garden Hotel", snippet="Hotel. Purchasing department and buyers contact.",
         pages=[
             page("kyoto-garden-hotel.test", "", "homepage", """
                Kyoto Garden Hotel offers 80 rooms, a traditional tea garden and a restaurant serving
                seasonal kaiseki. Suppliers who wish to work with us can contact our purchasing department.
                Our buyers review new proposals every quarter."""),
         ]),
    dict(id="SW07", product="raw_sheep_wool", split="dev", category="relevant", expected=STRONG,
         note="Carpet mill using wool fibre",
         title="Flanders Rug Mill", snippet="Hand-tufted rugs and carpets.",
         pages=[
             page("flanders-rugs.test", "about", "about", """
                Flanders Rug Mill manufactures hand-tufted carpets and rugs at our mill in Kortrijk,
                Belgium. We manufacture our carpets from New Zealand wool fibre that is spun to our own
                specification. Our designs are sold to architects and interior designers."""),
         ]),
    dict(id="SW08", product="raw_sheep_wool", split="dev", category="relevant_partial", expected=POSSIBLE,
         note="Weaving mill, only 'pure wool' products",
         title="Lanificio Monte", snippet="Italian woollen fabrics.",
         pages=[
             page("lanificio-monte.test", "about", "about", """
                Lanificio Monte is a weaving mill in Biella that produces woollen fabric for tailoring and
                fashion houses. Our fabrics are made from pure wool and are finished in our own dyehouse.
                We present two collections each year."""),
         ]),
    dict(id="SW09", product="raw_sheep_wool", split="dev", category="unreachable", expected=INSUFFICIENT,
         note="Website unreachable",
         title="Raw Sheep Wool Buyers International", snippet="Raw sheep wool importer and buyer.",
         pages=[]),
    dict(id="SW10", product="raw_sheep_wool", split="dev", category="distractor", expected=NOT_RELEVANT,
         note="Tannery making sheepskin goods",
         title="Valley Tannery", snippet="Sheepskin rugs and slippers.",
         pages=[
             page("valley-tannery.test", "about", "about", """
                Valley Tannery is a tannery in Somerset that turns sheepskins into rugs, slippers and
                car seat covers. We work with hides from local abattoirs and use traditional tanning
                methods. Our products are sold through gift shops."""),
         ]),
    dict(id="SW11", product="raw_sheep_wool", split="test", category="relevant", expected=STRONG,
         note="Wool insulation manufacturer",
         title="Cambrian Wool Insulation", snippet="Sheep wool insulation for buildings.",
         pages=[
             page("cambrian-insulation.test", "about", "about", """
                We produce thermal and acoustic insulation batts from sheep's wool at our factory in Powys,
                Wales. The raw wool is washed, treated against moths and bonded into rolls and slabs for
                lofts and walls. Our products are used by self-builders and contractors."""),
         ]),
    dict(id="SW12", product="raw_sheep_wool", split="test", category="relevant_partial", expected=POSSIBLE,
         note="Felt maker, wool form not stated",
         title="Feltworks Germany", snippet="Industrial wool felt manufacturer.",
         pages=[
             page("feltworks.test", "products", "products", """
                Feltworks manufactures industrial and decorative felt in Saxony. Our felt is needle-punched
                from 100% natural wool and is used for gaskets, polishing wheels and acoustic panels. We cut
                felt to size for customers all over Europe."""),
         ]),
    dict(id="SW13", product="raw_sheep_wool", split="test", category="irrelevant", expected=NOT_RELEVANT,
         note="Cotton garment manufacturer",
         title="Dhaka Garments", snippet="Garment manufacturer and exporter.",
         pages=[
             page("dhaka-garments.test", "about", "about", """
                Dhaka Garments is a garment manufacturer producing cotton T-shirts, polo shirts and
                hoodies for European buyers. Our factory employs 1,200 workers and is certified for social
                compliance. We ship to importers in Germany and the UK."""),
         ]),
    dict(id="SW14", product="raw_sheep_wool", split="test", category="relevant", expected=CONFIRMED,
         note="Wool merchant buying greasy wool at auction",
         title="Southern Cross Wool Merchants", snippet="Wool exporters.",
         pages=[
             page("southern-cross-wool.test", "about", "about", """
                As wool merchants, Southern Cross purchases greasy wool at auction in Melbourne and
                Fremantle. We export scoured wool and greasy wool to mills in China, India and Italy and
                arrange testing, baling and shipping for every lot."""),
         ]),
    dict(id="SW15", product="raw_sheep_wool", split="test", category="conflicting", expected=INSUFFICIENT,
         note="Wool fibre carpets vs. all synthetic carpets",
         title="Hearth Carpets", snippet="Carpet manufacturer.",
         pages=[
             page("hearth-carpets.test", "products", "products", """
                Our carpets are made from pure New Zealand wool fibre for a soft and natural feel. Hearth
                Carpets has manufactured carpets in Ireland since 1968."""),
             page("hearth-carpets.test", "about", "about", """
                Hearth Carpets manufactures carpets for busy homes. All our carpets are 100% synthetic
                nylon, which makes them easy to clean and very durable."""),
         ]),
    dict(id="SW16", product="raw_sheep_wool", split="test", category="insufficient", expected=INSUFFICIENT,
         note="JavaScript-only website, almost no text",
         title="Wool Tops Trading", snippet="Raw sheep wool tops trader.",
         pages=[page("wooltops-trading.test", "", "homepage", "Loading... Please enable JavaScript.")]),

    # ========================================================= CASHMERE ====
    dict(id="CA01", product="cashmere", split="dev", category="relevant", expected=STRONG,
         note="Dehairing plant",
         title="Gobi Fibre Processing", snippet="Cashmere dehairing in Mongolia.",
         pages=[
             page("gobi-fibre.test", "about", "about", """
                Gobi Fibre operates a dehairing plant in Ulaanbaatar. We scour and dehair raw cashmere
                collected from herders across the Gobi region and supply dehaired cashmere fibre to
                spinners in Italy, Japan and the UK."""),
         ]),
    dict(id="CA02", product="cashmere", split="dev", category="relevant_partial", expected=POSSIBLE,
         note="Knitwear factory working from cashmere yarn only",
         title="Maglificio Rossi", snippet="Cashmere knitwear manufacturer.",
         pages=[
             page("maglificio-rossi.test", "about", "about", """
                Maglificio Rossi is a knitwear manufacturer in Perugia. Our knitting factory produces
                sweaters and cardigans for luxury brands from cashmere yarn spun in Biella. We offer
                sampling, production and quality control under one roof."""),
         ]),
    dict(id="CA03", product="cashmere", split="dev", category="retailer", expected=NOT_RELEVANT,
         note="Fashion brand selling cashmere sweaters",
         title="Aurelia London - Cashmere Knitwear", snippet="Luxury cashmere sweaters.",
         pages=[
             page("aurelia-london.test", "", "homepage", """
                Aurelia is a London fashion brand. Our cashmere sweaters are designed in London and
                crafted by trusted partners. Shop the new autumn collection online and enjoy free shipping
                on all orders. Discover our scarves, beanies and gloves."""),
         ]),
    dict(id="CA04", product="cashmere", split="dev", category="alternative_material", expected=NOT_RELEVANT,
         note="Cashmere-feel acrylic knitwear",
         title="SoftTouch Knits", snippet="Knitwear factory, cashmere feel.",
         pages=[
             page("softtouch-knits.test", "about", "about", """
                SoftTouch is a knitwear factory in Guangzhou. We manufacture sweaters in a cashmere-feel
                acrylic yarn that is soft, affordable and machine washable. Wholesalers and distributors can
                order from 300 pieces per colour."""),
         ]),
    dict(id="CA05", product="cashmere", split="dev", category="relevant", expected=CONFIRMED,
         note="Spinner purchasing dehaired fibre",
         title="Filatura Alpina", snippet="Cashmere yarn spinning mill.",
         pages=[
             page("filatura-alpina.test", "about", "about", """
                Filatura Alpina is a cashmere spinner in Biella. Our mill spins cashmere yarn for knitwear
                manufacturers in Europe and Japan."""),
             page("filatura-alpina.test", "sourcing", "sourcing", """
                We purchase dehaired cashmere fibre from Inner Mongolia and Afghanistan and test every
                lot for micron and length before spinning. Our sourcing team visits suppliers each year."""),
         ]),
    dict(id="CA06", product="cashmere", split="dev", category="alternative_material", expected=NOT_RELEVANT,
         note="Merino knitwear only",
         title="Highland Knitwear", snippet="Knitwear manufacturer.",
         pages=[
             page("highland-knitwear.test", "about", "about", """
                Highland Knitwear is a knitwear manufacturer in the Scottish Borders. Our factory knits
                sweaters and cardigans from merino wool and lambswool for heritage brands. We have been
                knitting in Hawick since 1920."""),
         ]),
    dict(id="CA07", product="cashmere", split="dev", category="irrelevant", expected=NOT_RELEVANT,
         note="Cafe named 'Cashmere'",
         title="Cashmere Cafe Kobe", snippet="Cashmere Cafe - coffee and cakes. Buyers welcome.",
         pages=[
             page("cashmere-cafe.test", "", "homepage", """
                Cashmere Cafe is a small coffee shop in Kobe serving hand-drip coffee, cheesecake and
                seasonal sweets. We roast our beans every morning. Coffee bean buyers and wholesalers can
                contact us for our blend."""),
         ]),
    dict(id="CA08", product="cashmere", split="dev", category="unreachable", expected=INSUFFICIENT,
         note="Website unreachable",
         title="Cashmere Importers Japan", snippet="Cashmere importer and wholesaler.",
         pages=[]),
    dict(id="CA09", product="cashmere", split="dev", category="supplier", expected=NOT_RELEVANT,
         note="Herder cooperative selling raw cashmere",
         title="Khangai Herders", snippet="Cashmere goat herders.",
         pages=[
             page("khangai-herders.test", "about", "about", """
                Khangai Herders is a herding cooperative of 140 families raising cashmere goats in central
                Mongolia. Each spring we comb our goats and sell raw cashmere to traders and processors.
                The cooperative also supports local schools."""),
         ]),
    dict(id="CA10", product="cashmere", split="dev", category="relevant_partial", expected=POSSIBLE,
         note="Shawl manufacturer, fibre/yarn input not stated",
         title="Kathmandu Shawl Works", snippet="Cashmere shawls manufacturer.",
         pages=[
             page("kathmandu-shawls.test", "about", "about", """
                Kathmandu Shawl Works is a shawl manufacturer with our own weaving workshop. We weave
                cashmere shawls, scarves and blankets on hand looms and export them to boutiques in Europe
                and the United States."""),
         ]),
    dict(id="CA11", product="cashmere", split="test", category="relevant", expected=STRONG,
         note="Cashmere fibre trader",
         title="Steppe Fibre Trading", snippet="Cashmere trading company.",
         pages=[
             page("steppe-fibre.test", "about", "about", """
                Steppe Fibre is a cashmere trading company based in Beijing and Milan. We trade dehaired
                cashmere and cashmere tops between producers in Mongolia and mills in Europe, and we handle
                inspection, finance and logistics for each contract."""),
         ]),
    dict(id="CA12", product="cashmere", split="test", category="relevant", expected=STRONG,
         note="Weaving mill blending dehaired cashmere fibre",
         title="Tessitura Lago", snippet="Luxury coat fabrics.",
         pages=[
             page("tessitura-lago.test", "about", "about", """
                Tessitura Lago is a weaving mill near Como that produces coat and jacket fabrics. Our mill
                blends dehaired cashmere fibre with fine wool to weave fabrics for fashion houses. Every
                piece is finished in our own finishing department."""),
         ]),
    dict(id="CA13", product="cashmere", split="test", category="alternative_material", expected=NOT_RELEVANT,
         note="Synthetic textile producer",
         title="Polytex Fabrics", snippet="Textile manufacturer, polyester and nylon.",
         pages=[
             page("polytex.test", "about", "about", """
                Polytex is a textile manufacturer producing polyester and nylon fabrics for sportswear and
                bags. Our plant in Surat runs 200 looms and a dyeing unit. We export to distributors and
                importers in 30 countries."""),
         ]),
    dict(id="CA14", product="cashmere", split="test", category="conflicting", expected=INSUFFICIENT,
         note="'Pure cashmere' vs. all products cashmere-like acrylic",
         title="Mongolia Dream Knitwear", snippet="Knitwear factory.",
         pages=[
             page("mongolia-dream.test", "products", "products", """
                Our sweaters are knitted from 100% pure cashmere in our own knitting factory. Choose from
                twelve colours and three styles."""),
             page("mongolia-dream.test", "about", "about", """
                Mongolia Dream is a knitwear factory. All our products are made from a cashmere-like acrylic
                that offers luxury at an affordable price."""),
         ]),
    dict(id="CA15", product="cashmere", split="test", category="non_english", expected=INSUFFICIENT,
         note="Italian-only website",
         title="Lanificio Cashmere Italia", snippet="Cashmere filati.",
         pages=[
             page("lanificio-cashmere.test", "", "homepage", """
                Il nostro lanificio produce filati di cashmere di alta qualità dal 1950. Selezioniamo le
                migliori fibre e le lavoriamo nel nostro stabilimento in provincia di Biella per i marchi
                della moda italiana e internazionale."""),
         ]),
    dict(id="CA16", product="cashmere", split="test", category="retailer", expected=NOT_RELEVANT,
         note="Brand that 'buys the finest cashmere' but outsources all making",
         title="Maison Cashmere", snippet="We buy the finest cashmere.",
         pages=[
             page("maison-cashmere.test", "", "homepage", """
                Maison Cashmere is a fashion brand from Paris. Our brand buys the finest cashmere sweaters
                and scarves from partner workshops and sells them in our boutiques and online shop. Discover
                the new collection and enjoy free returns."""),
         ]),
]

PRODUCT_NAMES = {"duck_down": "Duck Down", "raw_sheep_wool": "Raw Sheep Wool", "cashmere": "Cashmere"}
