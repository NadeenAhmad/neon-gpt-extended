# Chemical Information Ontology (CHEMINF): NeOn-GPT configuration

Inputs used for the **CHEMINF** runs of Extended NeOn-GPT. Script key: `CHEMINF` (set `SELECTED_ONTOLOGY = "CHEMINF"` in `neon-gpt/neon_gpt_ontology_generation.py`). The same content as data: [`CHEMINF.json`](CHEMINF.json).

## Ontology brief

**Domain name:** Chemical Information Ontology (CHEMINF)

**Keywords:** ChemicalDescriptor, ChemicalGraph, Algorithm, SoftwareImplementation, DataFormat, Provenance, MolecularStructure, SMILES, InChI, logP, MolecularWeight, ChemicalEntity, ChemicalDescriptor, DescriptorValue, MolecularStructure, SMILES, InChI, MolecularWeight, logP, TopologicalPolarSurfaceArea, TanimotoCoefficient, SubstructureFingerprint, SimilarityScore, DescriptorCalculation, SoftwareTool, Algorithm, RDFGraph, Provenance, DataFormat, DescriptorOntology, SDF, QSAR, ToxicityPrediction, StructureRepresentation, InferenceEngine, ConfidenceScore, OntologyAlignment, ChemicalDataset

**Size of the reference ontology** (`ontology_metrics`, given to the model as a size target): 855 classes, 111 object properties, 7 data properties, 20 individuals

**Domain description** (`domain_description`):

```text
CHEMINF – Domain Description

The Chemical Information Ontology (CHEMINF) provides a structured framework for representing chemical information entities, particularly those used in cheminformatics. It encompasses:

- **Chemical Descriptors**: Quantitative and qualitative properties of chemical entities, such as molecular weight, logP, and topological polar surface area.

- **Chemical Graphs**: Representations of molecular structures, including various encoding formats like SMILES and InChI.

- **Algorithms and Software Implementations**: Computational methods and tools used to calculate chemical descriptors and process chemical information.

- **Data Formats and Specifications**: Standards for representing chemical data, including file formats like MOL and SDF.

- **Provenance and Metadata**: Information about the origin, calculation methods, and context of chemical data, ensuring reproducibility and data integration.

CHEMINF facilitates the integration, annotation, and retrieval of chemical information across databases and software applications, supporting advanced queries and semantic reasoning in chemical research.
```

## Persona (`persona`)

```text
You are an expert cheminformatician and knowledge engineer specializing in the development of ontologies for chemical information systems. Holding a PhD in Chemistry with a concentration in cheminformatics and semantic technologies, you have extensive experience in both theoretical chemistry and computational representation of chemical knowledge.

Your expertise centers on the structured representation of chemical descriptors, computational algorithms, molecular formats, and experimental properties using semantic web standards. You specialize in modeling entities and relationships essential to chemical research and data interoperability—such as molecular weight, logP, SMILES and InChI formats, software implementations, and prediction algorithms.

As a core contributor to and expert user of the Chemical Information Ontology (CHEMINF) hosted on BioPortal, you ensure that your ontologies align with FAIR principles (Findable, Accessible, Interoperable, and Reusable). You use tools such as RDF, OWL, and Turtle syntax to build precise, machine-readable models that enable advanced querying, data annotation, and integration across cheminformatics platforms, chemical databases, and bioinformatics systems.

You have a meticulous and user-centric approach to ontology design, aiming to bridge the gap between raw chemical data and actionable insights for drug discovery, toxicology, materials science, and biomedical research. You are especially skilled at linking CHEMINF terms with related ontologies like ChEBI, SIO, and PROV-O to support semantic inference, provenance tracking, and data harmonization.

Your goal is to advance the semantic representation of chemical knowledge in ways that support automated reasoning, enhance scientific reproducibility, and enable powerful cross-disciplinary research. You play a key role in translating the complexity of chemical information into interoperable, structured formats that empower researchers, developers, and data scientists across the chemical and life sciences.
         You are tasked with generating an ontology about the following domain.


Domain Name: Chemical Information Ontology (CHEMINF)
Domain Description: 
The Chemical Information Ontology (CHEMINF) provides a structured framework for representing chemical information entities, particularly those used in cheminformatics. It encompasses:

- **Chemical Descriptors**: Quantitative and qualitative properties of chemical entities, such as molecular weight, logP, and topological polar surface area.

- **Chemical Graphs**: Representations of molecular structures, including various encoding formats like SMILES and InChI.

- **Algorithms and Software Implementations**: Computational methods and tools used to calculate chemical descriptors and process chemical information.

- **Data Formats and Specifications**: Standards for representing chemical data, including file formats like MOL and SDF.

- **Provenance and Metadata**: Information about the origin, calculation methods, and context of chemical data, ensuring reproducibility and data integration.

CHEMINF facilitates the integration, annotation, and retrieval of chemical information across databases and software applications, supporting advanced queries and semantic reasoning in chemical research.
```

## Ontology reuse

**What to reuse** (`reuse_example_desc`): CHEMINF ontology's classes and properties related to chemical descriptors, molecular representations, computational algorithms, and data formats.

**Reuse snippets** (`few_shot_reuse`):

```text
(ChemicalDescriptor - isDescriptorOf - ChemicalEntity)
(ChemicalDescriptor - hasValue - DescriptorValue)
(ChemicalDescriptor - conformsTo - DataFormatSpecification)
(ChemicalDescriptor - isCalculatedBy - Algorithm)
(Algorithm - isImplementedIn - SoftwareImplementation)
(ChemicalGraph - represents - ChemicalEntity)
(ChemicalGraph - encodedIn - SMILESFormat)
(ChemicalGraph - encodedIn - InChIFormat)
(ChemicalDescriptor - hasProvenance - ProvenanceInformation)
(SoftwareImplementation - hasVersion - SoftwareVersion)
```

## Few-shot examples

### Competency questions (`few_shot_cqs`)

```text
 
Q: What is the molecular weight of caffeine?
Q: Which algorithm calculates the logP value? 
Q: In which format is the chemical structure represented? 
Q: What software was used to compute the topological polar surface area? 
Q: What is the SMILES representation of aspirin? 
```

### Entity and relation extraction (`few_shot_entity_extraction`)

```text
Q: What is the molecular weight of caffeine? → Entities: Caffeine, MolecularWeight | Property: hasDescriptor
Q: Which algorithm calculates the logP value? → Entities: logP, Algorithm | Property: isCalculatedBy
Q: In which format is the chemical structure represented? → Entities: ChemicalGraph, DataFormatSpecification | Property: encodedIn
Q: What software was used to compute the topological polar surface area? → Entities: TopologicalPolarSurfaceArea, SoftwareImplementation | Property: isCalculatedBy
Q: What is the SMILES representation of aspirin? → Entities: Aspirin, SMILESFormat | Property: encodedIn
```

### Data properties (`few_shot_data_properties`)

```text
Q: What is the molecular weight of caffeine? → Entities: Caffeine, MolecularWeight | Property: hasDescriptor
Q: Which algorithm calculates the logP value? → Entities: logP, Algorithm | Property: isCalculatedBy
Q: In which format is the chemical structure represented? → Entities: ChemicalGraph, DataFormatSpecification | Property: encodedIn
Q: What software was used to compute the topological polar surface area? → Entities: TopologicalPolarSurfaceArea, SoftwareImplementation | Property: isCalculatedBy
Q: What is the SMILES representation of aspirin? → Entities: Aspirin, SMILESFormat | Property: encodedIn
```

### Individuals (`few_shot_individuals`)

```text
:Caffeine a :ChemicalEntity ;
    rdfs:comment "A chemical entity representing the stimulant compound commonly found in coffee and tea." .

:Aspirin a :ChemicalEntity ;
    rdfs:comment "A chemical entity representing acetylsalicylic acid, a widely used analgesic drug." .

:SMILESFormat a :DataFormatSpecification ;
    rdfs:comment "An instance of the SMILES format, used to express chemical structures in a linear text form." .

:InChIFormat a :DataFormatSpecification ;
    rdfs:comment "An instance of the IUPAC International Chemical Identifier (InChI) format for representing chemical substances." .

:AlgorithmX a :Algorithm ;
    rdfs:comment "An example algorithm, possibly used in cheminformatics applications for property prediction or analysis." .

:SoftwareY a :SoftwareImplementation ;
    rdfs:comment "An example software tool or package used in chemical data processing." .
```
