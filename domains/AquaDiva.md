# AquaDiva Ontology: NeOn-GPT configuration

Inputs used for the **AquaDiva** runs of Extended NeOn-GPT. Script key: `AquaDiva` (set `SELECTED_ONTOLOGY = "AquaDiva"` in `neon-gpt/neon_gpt_ontology_generation.py`). The same content as data: [`AquaDiva.json`](AquaDiva.json).

## Ontology brief

**Domain name:** AquaDiva Ontology

**Keywords:** MicrobialTaxon, SamplingSite, Habitat, BiogeochemicalProcess, EnvironmentalParameter, SequencingTechnique, MicrobialFunction, Abundance, TimePoint, SubsurfaceZone

**Size of the reference ontology** (`ontology_metrics`, given to the model as a size target): 802 classes, 11,270 axioms, 108 properties, 240 individuals

**Domain description** (`domain_description`):

```text
AquaDiva Ontology – Domain Description
The AquaDiva Ontology formalizes knowledge in the domain of subsurface environmental microbiology, focusing on interactions between microbial life and the geological environment. Key subdomains include:

Microbial Taxonomy and Function: Representing microbial clades, functional roles (e.g., methanogenesis, denitrification), and metabolic pathways in subsurface ecosystems.

Sampling Environments: Modeling environments such as aquifers, karst systems, and boreholes, with spatio-temporal descriptors and geochemical conditions.

Measurement and Instrumentation: Capturing techniques such as 16S rRNA gene sequencing, stable isotope probing, and flow cytometry, along with associated metadata.

Environmental Variables: Encoding parameters such as pH, oxygen levels, temperature, pressure, and nutrient concentrations that define habitat niches.

Biogeochemical Processes: Representing transformations like sulfur cycling, iron reduction, and carbon turnover mediated by microbial activity.

Spatial and Temporal Context: Modeling location metadata (e.g., coordinates, depth, geological layer) and time-series sampling.

Organisms and Populations: Describing taxa, strain-level distinctions, abundance data, and genomic traits relevant to ecological dynamics.

Ecosystem Interactions: Capturing trophic relationships, symbioses, and perturbation responses such as anthropogenic disturbance or drought.

This ontology supports cross-study integration of microbial ecological data and environmental measurements across sites and experiments in projects like the Collaborative Research Centre AquaDiva.
```

## Persona (`persona`)

```text
 You are an expert in environmental microbiology and subsurface ecosystem modeling, with a focus on formalizing knowledge about microbial communities, geochemical processes, and environmental interactions. Holding a PhD in Environmental Microbiology and trained in knowledge representation and semantic web technologies, you specialize in translating complex, multidisciplinary research into interoperable ontological structures.

Your work spans the integration of microbiological, hydrological, and geochemical data to understand subterranean ecosystems. You are skilled at identifying core domain entities—such as microbial taxa, biogeochemical cycles, sampling environments, and measurement techniques—and modeling their interrelations using OWL ontologies.

You have contributed to the design of ontologies used in ecological monitoring and microbial community profiling, ensuring logical consistency and alignment with FAIR data principles. You also focus on interoperability with broader environmental ontologies such as ENVO, MIxS, and the Environment Ontology, promoting data reuse across research infrastructures.

Your ontologies support researchers in querying microbial function, tracking ecosystem responses, and integrating multi-omics data in large-scale ecological studies. Your goal is to create structured, computable frameworks that bridge environmental microbiology and data science to enable advanced ecosystem analysis and policy-relevant insights.
You are tasked with generating an ontology about the following domain.


Domain Name: AquaDiva Ontology
Domain Description: 
The AquaDiva Ontology formalizes knowledge in the domain of subsurface environmental microbiology, focusing on interactions between microbial life and the geological environment. Key subdomains include:

Microbial Taxonomy and Function: Representing microbial clades, functional roles (e.g., methanogenesis, denitrification), and metabolic pathways in subsurface ecosystems.

Sampling Environments: Modeling environments such as aquifers, karst systems, and boreholes, with spatio-temporal descriptors and geochemical conditions.

Measurement and Instrumentation: Capturing techniques such as 16S rRNA gene sequencing, stable isotope probing, and flow cytometry, along with associated metadata.

Environmental Variables: Encoding parameters such as pH, oxygen levels, temperature, pressure, and nutrient concentrations that define habitat niches.

Biogeochemical Processes: Representing transformations like sulfur cycling, iron reduction, and carbon turnover mediated by microbial activity.

Spatial and Temporal Context: Modeling location metadata (e.g., coordinates, depth, geological layer) and time-series sampling.

Organisms and Populations: Describing taxa, strain-level distinctions, abundance data, and genomic traits relevant to ecological dynamics.

Ecosystem Interactions: Capturing trophic relationships, symbioses, and perturbation responses such as anthropogenic disturbance or drought.

This ontology supports cross-study integration of microbial ecological data and environmental measurements across sites and experiments in projects like the Collaborative Research Centre AquaDiva.
```

## Ontology reuse

**What to reuse** (`reuse_example_desc`): ENVO terms for environmental conditions and MIxS descriptors for microbial sampling metadata

**Reuse snippets** (`few_shot_reuse`):

```text
 (MicrobialTaxon - inhabits - envo:Aquifer)
(SamplingSite - locatedIn - envo:KarstSystem)
(MicrobialTaxon - performs - obo:GO_0019641)  # GO term for aerobic respiration
(Sample - collectedUsing - mixs:Filtration)
(MicrobialCommunity - hasFunction - eco:EcosystemFunction)
(Sample - hasEnvironmentalCondition - envo:LowOxygen)
(Process - mediatedBy - MicrobialTaxon)
(Habitat - hasDepth - obo:PATO_0001595)
(MicrobialTaxon - partOf - MicrobialCommunity)
(MicrobialTaxon - associatedWith - BiogeochemicalProcess)
```

## Few-shot examples

### Competency questions (`few_shot_cqs`)

```text
 
Q: What microbial taxa were found in the sample?
Q: What habitat was the microbial community isolated from?
Q: What function does this taxon perform? 
Q: Where was the sample taken?
Q: What technique was used to sequence the sample?
Q: What is the oxygen level of the sample site? 
```

### Entity and relation extraction (`few_shot_entity_extraction`)

```text
Q: What microbial taxa were found in the sample? → Entities: Sample, MicrobialTaxon | Property: containsTaxon
Q: What habitat was the microbial community isolated from? → Entities: MicrobialCommunity, Habitat | Property: isolatedFrom
Q: What function does this taxon perform? → Entities: MicrobialTaxon, MicrobialFunction | Property: performsFunction
Q: Where was the sample taken? → Entities: Sample, SamplingSite | Property: collectedFrom
Q: What technique was used to sequence the sample? → Entities: Sample, SequencingTechnique | Property: sequencedUsing
Q: What is the oxygen level of the sample site? → Entities: SamplingSite, EnvironmentalParameter | Property: hasOxygenLevel
```

### Data properties (`few_shot_data_properties`)

```text
:Sample1 a :Sample ;
    rdfs:comment "A water sample collected from a borehole at 12m depth during the March 2021 campaign." .

:LowOxygen a :EnvironmentalParameter ;
    rdfs:comment "An environmental condition indicating hypoxic or anoxic levels within the sampled habitat." .

:AquiferLayer2 a :Habitat ;
    rdfs:comment "A geologically distinct subsurface layer acting as a habitat for microbial communities." .

:SequencerX a :SequencingTechnique ;
    rdfs:comment "A high-throughput sequencing platform used for amplicon-based microbial community profiling." .

:2021_03_15 a :TimePoint ;
    rdfs:comment "The date of sample collection used for time-series tracking of microbial abundance." .
```

### Individuals (`few_shot_individuals`)

```text
:Desulfovibrio a :MicrobialTaxon ;
    rdfs:comment "A sulfate-reducing bacterium commonly found in anaerobic subsurface environments." .

:KarstCaveB1 a :SamplingSite ;
    rdfs:comment "A subterranean karst cave chamber designated as site B1 for AquaDiva sampling campaigns." .

:SulfateReduction a :BiogeochemicalProcess ;
    rdfs:comment "A microbial-mediated chemical process that converts sulfate to hydrogen sulfide." .

:SampleD23 a :Sample ;
    rdfs:comment "A filtered water sample taken from borehole D23, 30 meters below ground surface." .

:TimeSeries2021 a :TemporalCollection ;
    rdfs:comment "A sequence of sampling events conducted monthly over the course of 2021 to observe microbial dynamics." .
```
