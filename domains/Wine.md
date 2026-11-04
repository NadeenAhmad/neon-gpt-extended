# Wine Ontology: NeOn-GPT configuration

Inputs used for the **Wine** runs of Extended NeOn-GPT. Script key: `Wine` (set `SELECTED_ONTOLOGY = "Wine"` in `neon-gpt/neon_gpt_ontology_generation.py`). The same content as data: [`Wine.json`](Wine.json).

## Ontology brief

**Domain name:** Wine Ontology

**Keywords:** Wine, GrapeVariety, WineType, WineColor, WineRegion, Winery, Vintage, TastingNote, FoodPairing

**Size of the reference ontology** (`ontology_metrics`, given to the model as a size target): 77 classes, 657 logical axioms, 13 object properties, 1 data property, 161 individuals

**Domain description** (`domain_description`):

```text
Wine Ontology – Domain Description
The Wine Ontology encompasses a rich and multifaceted domain that captures the intricate world of viticulture and oenology. This domain includes:​

Wine Types and Classifications: Detailed categorization of wines based on characteristics such as color (red, white, rosé), effervescence (still, sparkling), sweetness levels (dry, semi-dry, sweet), and fortification (e.g., fortified wines like Port and Sherry).​

Grape Varieties: Comprehensive representation of grape cultivars used in winemaking, including their genetic lineage, flavor profiles, and suitability to specific climates and soils.​

Viticultural Practices: Information on vineyard management techniques, including planting, pruning, pest control, and harvesting methods that influence grape quality.​

Winemaking Processes: Detailed modeling of enological processes such as crushing, fermentation (primary and malolactic), aging (in various vessels like oak barrels or stainless steel tanks), clarification, and bottling.​

Wine Attributes: Representation of sensory characteristics (aroma, flavor, body, tannin levels), chemical properties (alcohol content, acidity, residual sugar), and quality indicators.​

Geographical Indications: Inclusion of appellations and regions of origin, reflecting legal designations and terroir influences on wine styles and quality.​

Wineries and Producers: Information about wine producers, including their history, production volumes, and signature styles.​

Vintages: Data on specific harvest years, including climatic conditions that affect grape development and wine characteristics.​

Wine Pairings: Guidelines for matching wines with various foods, considering factors like flavor compatibility and cultural traditions.​

Regulatory Aspects: Inclusion of labeling requirements, classification systems, and legal standards governing wine production and marketing.
```

## Persona (`persona`)

```text
You are an expert in wine ontology development and knowledge engineering, specializing in the structured representation of viticulture and oenology knowledge. Holding a PhD in Agricultural Sciences with a focus on Viticulture and Enology, along with formal training in semantic web technologies and data modeling, you bring a unique blend of domain expertise and technical acumen.

You have extensive experience in analyzing the complex interplay between grape varieties, terroir, winemaking practices, and wine characteristics. Your work bridges traditional wine knowledge with modern computational approaches, enabling standardized and interoperable representations of wine-related data.

Your core strength lies in identifying and modeling the key concepts within the wine domain—such as grape varieties, wine styles, production regions, vintages, alcohol content, fermentation methods, and food pairings—and articulating the relationships between them. You excel in designing domain ontologies using RDF and Turtle, creating structured vocabularies that serve both producers and researchers in wine science, trade, and sensory analysis.

With a meticulous, user-centered approach to ontology design, you ensure that the ontologies you build support data integration, semantic search, and automated reasoning across diverse wine databases and applications. You are adept at aligning wine ontologies with broader food and agriculture standards, facilitating data sharing between stakeholders in the wine industry, gastronomy, and regulatory bodies.

Your ultimate goal is to elevate raw and fragmented wine knowledge into coherent, machine-readable frameworks that support advanced analysis, decision-making, and cultural storytelling in the world of wine.

You are tasked with generating an ontology about the following domain.


Domain Name: Wine Ontology
Domain Description: The Wine Ontology encompasses a rich and multifaceted domain that captures the intricate world of viticulture and oenology. This domain includes:​

Wine Types and Classifications: Detailed categorization of wines based on characteristics such as color (red, white, rosé), effervescence (still, sparkling), sweetness levels (dry, semi-dry, sweet), and fortification (e.g., fortified wines like Port and Sherry).​

Grape Varieties: Comprehensive representation of grape cultivars used in winemaking, including their genetic lineage, flavor profiles, and suitability to specific climates and soils.​

Viticultural Practices: Information on vineyard management techniques, including planting, pruning, pest control, and harvesting methods that influence grape quality.​

Winemaking Processes: Detailed modeling of enological processes such as crushing, fermentation (primary and malolactic), aging (in various vessels like oak barrels or stainless steel tanks), clarification, and bottling.​

Wine Attributes: Representation of sensory characteristics (aroma, flavor, body, tannin levels), chemical properties (alcohol content, acidity, residual sugar), and quality indicators.​

Geographical Indications: Inclusion of appellations and regions of origin, reflecting legal designations and terroir influences on wine styles and quality.​

Wineries and Producers: Information about wine producers, including their history, production volumes, and signature styles.​

Vintages: Data on specific harvest years, including climatic conditions that affect grape development and wine characteristics.​

Wine Pairings: Guidelines for matching wines with various foods, considering factors like flavor compatibility and cultural traditions.​

Regulatory Aspects: Inclusion of labeling requirements, classification systems, and legal standards governing wine production and marketing.
```

## Ontology reuse

**What to reuse** (`reuse_example_desc`): FoodOn ontology's classes and properties related to beverages, ingredients, and food pairings

**Reuse snippets** (`few_shot_reuse`):

```text
 (Wine - hasIngredient - GrapeVariety)
(GrapeVariety - isA - agrovoc:Grape)
(Wine - classifiedAs - eurovoc:PDO_ProtectedDesignationOfOrigin)
(Wine - containsCompound - mesh:Ethanol)
(WineLabel - compliesWith - eurovoc:WineLabelingDirective)
(Wine - hasComponent - mesh:TartaricAcid)
(Wine - soldUnder - unspsc:50202201)  # UNSPSC code for Wine
(Vineyard - partOf - agrovoc:Viticulture)
(Wine - hasPreservative - mesh:SulfurDioxide)
(Wine - hasAdditive - mesh:AscorbicAcid)
(Wine - hasAcidity - mesh:MalicAcid)
(Wine - hasAcidity - mesh:LacticAcid)
(Wine - hasColor - agrovoc:Anthocyanin)
(Wine - hasFlavor - agrovoc:Terpene)
(Wine - hasAroma - agrovoc:Esters)
(Wine - hasBody - agrovoc:Glycerol)
(Wine - hasSweetness - agrovoc:Glucose)
(Wine - hasBitterness - agrovoc:Tannin)
(Wine - hasViscosity - agrovoc:Polysaccharides)
(Wine - hasAlcoholContent - agrovoc:Ethanol)
```

## Few-shot examples

### Competency questions (`few_shot_cqs`)

```text
 
Q: What grape varieties are used in a wine? 
Q: Where is this wine produced? 
Q: What food does this wine pair well with? 
Q: What is the color of this wine?
Q: Who is the producer of this wine? 
Q: What is the vintage of this wine? 
Q: What is the tasting note of this wine? 
```

### Entity and relation extraction (`few_shot_entity_extraction`)

```text
Q: What grape varieties are used in a wine? → Entities: Wine, GrapeVariety | Property: hasGrapeVariety
Q: Where is this wine produced? → Entities: Wine, WineRegion | Property: producedIn
Q: What food does this wine pair well with? → Entities: Wine, Food | Property: pairsWith
Q: What is the color of this wine? → Entities: Wine, WineColor | Property: hasColor
Q: Who is the producer of this wine? → Entities: Wine, Winery | Property: producedBy
Q: What is the vintage of this wine? → Entities: Wine, Vintage | Property: hasVintage
Q: What is the tasting note of this wine? → Entities: Wine, TastingNote | Property: hasTastingNote
```

### Data properties (`few_shot_data_properties`)

```text
:Chardonnay a :GrapeVariety ;
    rdfs:comment "A popular white grape variety used in wine production, especially in regions like Burgundy and California." .

:Red a :WineColor ;
    rdfs:comment "Represents the color classification of wine as red, typically made from dark-skinned grape varieties." .

:France a :WineRegion ;
    rdfs:comment "A prominent wine-producing country, known for its diverse and historic wine regions such as Bordeaux and Burgundy." .

:13Percent a :AlcoholContent ;
    rdfs:comment "Represents a wine's alcohol content level of 13%, a common value for many table wines." .

:2020Vintage a :VintageYear ;
    rdfs:comment "Refers to the year in which the grapes were harvested for a particular wine – in this case, 2020." .
```

### Individuals (`few_shot_individuals`)

```text
:Chardonnay a :GrapeVariety ;
    rdfs:comment "An individual grape variety known for producing dry white wines, widely grown around the world." .

:Red a :WineColor ;
    rdfs:comment "An individual color classification of wine, typically associated with wines made from red or black grapes." .

:France a :WineRegion ;
    rdfs:comment "An individual wine-producing region or country, representing France, known for its rich viticultural heritage." .

:CabernetSauvignon a :GrapeVariety ;
    rdfs:comment "A full-bodied red grape variety, widely cultivated and known for aging potential and strong tannins." .

:Cheeseboard a :Food ;
    rdfs:comment "A food pairing option commonly served with wine, typically consisting of assorted cheeses and accompaniments." .
```
