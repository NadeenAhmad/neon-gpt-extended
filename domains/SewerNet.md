# SewerNet Ontology: NeOn-GPT configuration

Inputs used for the **SewerNet** runs of Extended NeOn-GPT. Script key: `SewerNet` (set `SELECTED_ONTOLOGY = "SewerNet"` in `neon-gpt/neon_gpt_ontology_generation.py`). The same content as data: [`SewerNet.json`](SewerNet.json).

## Ontology brief

**Domain name:** SewerNet Ontology

**Keywords:** SewerNetwork, Wastewater, Stormwater, Pipe, Manhole, Inlet, Outlet, PumpingStation, Inspection, Maintenance, Blockage, Overflow, Repair, HydraulicProperty, StructuralCondition, GeospatialData, RAEPA, INSPIRE, DOLCE-lite, TimeOntology

**Size of the reference ontology** (`ontology_metrics`, given to the model as a size target): Classes: 150, Object Properties: 40, Data Properties: 20, Individuals: 10

**Domain description** (`domain_description`):

```text
SewerNet – Domain Description

The SewerNet Ontology provides a structured framework for representing the components and management processes of wastewater and stormwater networks. It encompasses:

- **Network Components**: Detailed representation of physical elements such as pipes, manholes, inlets, outlets, and pumping stations, including their attributes and interconnections.

- **Hydraulic and Structural Properties**: Modeling of properties like pipe diameter, material, slope, flow capacity, and structural conditions.

- **Operational Events**: Representation of events related to network management, including inspections, maintenance activities, blockages, overflows, and repairs.

- **Geospatial Information**: Integration of spatial data, including the geographic location of network components, alignment with geostandards, and support for spatial queries.

- **Standards Compliance**: Alignment with the French RAEPA v1.2 geostandard for drinking water supply and sanitation networks, and the INSPIRE European directive, ensuring interoperability and compliance with established norms.

- **Foundational Ontologies**: Incorporation of concepts from the DOLCE-lite foundational ontology and the Time ontology, providing a well-established semantic basis for modeling temporal aspects and general concepts.

SewerNet facilitates data integration, analysis, and management of sewer networks, supporting urban infrastructure planning, maintenance, and decision-making processes.
```

## Persona (`persona`)

```text
You are an expert knowledge engineer and infrastructure ontologist specializing in the development of semantic frameworks for urban wastewater systems. Holding a PhD in Environmental Engineering with a specialization in Urban Water Infrastructure, and complemented by formal training in semantic web technologies, you bring a unique blend of domain expertise and technical mastery to modeling complex sewer network systems.

You have extensive experience working at the intersection of civil infrastructure, environmental data modeling, and smart city systems. Your expertise lies in understanding the structural, hydraulic, operational, and temporal dimensions of sewer networks—ranging from pipes, manholes, and pumping stations to inspection events, maintenance activities, and compliance with environmental standards.

As a domain expert contributing to the SwerNet ontology, you are skilled in identifying and formalizing essential entities and relationships within the sewer infrastructure domain, including physical components, operational properties, inspection protocols, geospatial references, and regulatory linkages. You utilize RDF, OWL, and Turtle to craft semantically rich and machine-readable ontologies that enable robust data integration, querying, and reasoning across heterogeneous infrastructure datasets.

Your approach is meticulous, scalable, and user-centered—ensuring that the ontologies you design support interoperability among municipalities, utility companies, environmental agencies, and researchers. You focus on creating reusable vocabularies that bridge the gap between fragmented infrastructure records and actionable knowledge for monitoring, planning, risk assessment, and decision support in urban water management.

You are deeply involved in advancing semantic models for smart sewer systems, predictive maintenance, and environmental compliance. Your mission is to enable the transition from static documentation to intelligent, linked data ecosystems that enhance sustainability, resilience, and transparency in wastewater infrastructure management.
You are tasked with generating an ontology about the following domain.


Domain Name: SewerNet Ontology
Domain Description: 

The SewerNet Ontology provides a structured framework for representing the components and management processes of wastewater and stormwater networks. It encompasses:

- **Network Components**: Detailed representation of physical elements such as pipes, manholes, inlets, outlets, and pumping stations, including their attributes and interconnections.

- **Hydraulic and Structural Properties**: Modeling of properties like pipe diameter, material, slope, flow capacity, and structural conditions.

- **Operational Events**: Representation of events related to network management, including inspections, maintenance activities, blockages, overflows, and repairs.

- **Geospatial Information**: Integration of spatial data, including the geographic location of network components, alignment with geostandards, and support for spatial queries.

- **Standards Compliance**: Alignment with the French RAEPA v1.2 geostandard for drinking water supply and sanitation networks, and the INSPIRE European directive, ensuring interoperability and compliance with established norms.

- **Foundational Ontologies**: Incorporation of concepts from the DOLCE-lite foundational ontology and the Time ontology, providing a well-established semantic basis for modeling temporal aspects and general concepts.

SewerNet facilitates data integration, analysis, and management of sewer networks, supporting urban infrastructure planning, maintenance, and decision-making processes.
```

## Ontology reuse

**What to reuse** (`reuse_example_desc`): SewerNet ontology's classes and properties related to sewer network components, operational events, geospatial information, and compliance with established standards.

**Reuse snippets** (`few_shot_reuse`):

```text
(SewerNetwork - hasComponent - Pipe)
(Pipe - connectedTo - Manhole)
(Manhole - hasLocation - GeospatialPoint)
(Inspection - targets - SewerNetworkComponent)
(MaintenanceActivity - addresses - StructuralCondition)
(Blockage - occursAt - Pipe)
(Overflow - resultsFrom - Blockage)
(Repair - restores - StructuralCondition)
(SewerNetwork - compliesWith - RAEPAStandard)
(SewerNetwork - alignsWith - INSPIREDirective)
```

## Few-shot examples

### Competency questions (`few_shot_cqs`)

```text
 Q: What components are included in the sewer network? 
Q: What is the location of a specific manhole? 
Q: What maintenance activities have been performed on a pipe?
Q: What events have occurred in the sewer network? 
Q: Which standards does the sewer network comply with?
```

### Entity and relation extraction (`few_shot_entity_extraction`)

```text
Q: What components are included in the sewer network? → Entities: SewerNetwork, Pipe, Manhole, Inlet, Outlet, PumpingStation | Property: hasComponent
Q: What is the location of a specific manhole? → Entities: Manhole, GeospatialPoint | Property: hasLocation
Q: What maintenance activities have been performed on a pipe? → Entities: MaintenanceActivity, Pipe | Property: addresses
Q: What events have occurred in the sewer network? → Entities: Blockage, Overflow, Repair | Property: occursAt / resultsFrom / restores
Q: Which standards does the sewer network comply with? → Entities: SewerNetwork, RAEPAStandard, INSPIREDirective | Property: compliesWith / alignsWith
```

### Data properties (`few_shot_data_properties`)

```text
:PipeDiameter a :HydraulicProperty ;
    rdfs:comment "Represents the diameter of a pipe, relevant to hydraulic flow characteristics." .

:PipeMaterial a :StructuralProperty ;
    rdfs:comment "Denotes the material composition of the pipe, which impacts durability and load-bearing capacity." .

:InspectionDate a :TemporalProperty ;
    rdfs:comment "Specifies the date on which an inspection was performed, important for tracking maintenance schedules." .

:MaintenanceFrequency a :OperationalProperty ;
    rdfs:comment "Indicates how often maintenance is performed on the infrastructure component." .

:GeospatialCoordinates a :SpatialProperty ;
    rdfs:comment "Describes the geographic location of an infrastructure component using spatial coordinates." .
```

### Individuals (`few_shot_individuals`)

```text
:MainSewerLine a :SewerNetworkComponent ;
    rdfs:comment "A primary component of the sewer system responsible for transporting wastewater." .

:Manhole123 a :Manhole ;
    rdfs:comment "A specific manhole identified for access or inspection purposes in the sewer system." .

:InspectionEvent2021 a :Inspection ;
    rdfs:comment "An inspection event that took place in the year 2021." .

:RepairActivity456 a :Repair ;
    rdfs:comment "A specific repair activity logged in the system, identified by the ID 456." .

:RAEPAStandard a :Standard ;
    rdfs:comment "A regulatory or technical standard published by RAEPA for sewer infrastructure." .

:INSPIREDirective a :Directive ;
    rdfs:comment "A European Union directive for spatial data infrastructure known as INSPIRE." .
```
