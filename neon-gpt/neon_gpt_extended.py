

import requests

# Mistral AI API Setup
API_KEY = "YOUR-API-KEY"  # Replace with your actual API key
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Initialize chat history with optional system role
chat_history = [
    {"role": "system", "content": "You are a helpful assistant having a conversation with the user."}
]

def send_prompt(prompt):
    """Send a prompt to the Mistral model with chat memory."""
    # Add user message to chat
    chat_history.append({"role": "user", "content": prompt})

    # Call the API
    response = requests.post(
        MISTRAL_API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "open-mistral-7b",
            "messages": chat_history
        }
    )

    # Handle response
    if response.status_code == 200:
        reply = response.json()["choices"][0]["message"]["content"]
        chat_history.append({"role": "assistant", "content": reply})
        return reply
    else:
        return f"Error: {response.status_code} - {response.text}"

# Start the conversation
question_1 = "Name 3 American singers."
print("\nUser:", question_1)
answer_1 = send_prompt(question_1)
print("Assistant:", answer_1)

# Ask follow-up question relying on memory
question_2 = "Name 3 songs for each singer."
print("\nUser:", question_2)
answer_2 = send_prompt(question_2)
print("Assistant:", answer_2)

"""## Zero-shot NeOn-GPT Mistral"""

import requests
import re
import time


# === DYNAMIC PLACEHOLDERS === #
# Extract Using NLP techniques and RAG from Unstrucutred Text and existing ontological resources.
persona = "You are an expert knowledge and ontology engineer using the NeOn methodology. "
domain_name = "Cybersecurity Threat Intelligence"
domain_description = "concepts and relationships related to identifying, describing, and classifying cyber threats and threat actors"
keywords = "ThreatActor, Vulnerability, Exploit, Tactic, Technique, Procedure, IndicatorOfCompromise"



# Mistral AI API Setup
API_KEY = "YOUR-API-KEY"  # Replace with your actual API key
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
TURTLE_OUTPUT_FILE = domain_name + "_ontology.ttl"

chat_history = []

# Initialize chat history
chat_history = [
    {"role": "system", "content": persona}
]

def send_prompt(prompt, max_retries=3):
    """Send prompt and parse any turtle syntax between markers."""
    chat_history.append({"role": "user", "content": prompt})
    for attempt in range(1, max_retries + 1):
      response = requests.post(
        MISTRAL_API_URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": "open-mistral-7b", "messages": chat_history}
    )

      if response.status_code == 200:
          reply = response.json()["choices"][0]["message"]["content"]
          chat_history.append({"role": "assistant", "content": reply})
          print("\n--- MODEL RESPONSE ---\n", reply)
          extract_and_save_turtle(reply)
          return reply

      elif response.status_code == 429:
            if attempt < max_retries:
                wait_time =  20
                print(f" Rate limit exceeded (429). Retrying in {wait_time} seconds... (Attempt {attempt}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(" Error: Reached max retry attempts due to rate limiting.")
                return f"Error: 429, Rate limit exceeded after {max_retries} retries."

      else:
            print(f" Error: {response.status_code}, {response.text}")
            return f"Error: {response.status_code}, {response.text}"

TURTLE_OUTPUT_FILE = domain_name+"_ontology.ttl"
# Initialize the Turtle file (empty it once at the beginning of the script)
with open(TURTLE_OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("# Generated Turtle ontology\n\n")


def send_prompt_with_ontology(prompt, max_retries=3):
    """Send prompt using the Turtle ontology file as stateless context."""
    try:
        with open(TURTLE_OUTPUT_FILE, "r", encoding="utf-8") as f:
            ontology_text = f.read()
    except FileNotFoundError:
        ontology_text = "# Ontology file not found.\n"

    system_prompt = {
        "role": "system",
        "content": (
            f"{persona} The following ontology is given in Turtle format.\n"
            "Use it to answer the prompt precisely and logically.\n\n"
            "###start_turtle###\n"
            f"{ontology_text}\n"
            "###end_turtle###"
        )
    }

    user_prompt = {"role": "user", "content": prompt}

    for attempt in range(1, max_retries + 1):
        response = requests.post(
            MISTRAL_API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": "open-mistral-7b", "messages": [system_prompt, user_prompt]}
        )

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            print("\n--- MODEL RESPONSE ---\n", reply)
            extract_and_save_turtle(reply)
            return reply

        elif response.status_code == 429:
            wait_time = 20
            print(f" Rate limit exceeded. Retrying in {wait_time}s... (Attempt {attempt}/{max_retries})")
            time.sleep(wait_time)
        else:
            print(f" Error: {response.status_code}, {response.text}")
            return f"Error: {response.status_code}, {response.text}"

def extract_and_save_turtle(response_text):
    """Extract turtle code between markers and safely append to the Turtle file."""
    matches = re.findall(r"###start_turtle###(.*?)###end_turtle###", response_text, re.DOTALL)


    if not matches:
        print(" No Turtle code found in response.")
        return

    with open(TURTLE_OUTPUT_FILE, "a", encoding="utf-8") as f:
        for i, block in enumerate(matches, start=1):
            cleaned_block = block.strip()
            if cleaned_block:
                f.write(f"# --- Turtle block from prompt {len(chat_history)//2} ---\n")
                f.write(cleaned_block + "\n\n")
                print(f" Appended Turtle block {i} to {TURTLE_OUTPUT_FILE}")





# === ONTOLOGY GENERATION PROMPT PIPELINE === #

# Prompt 1 – Specification
send_prompt(f"""You are a {persona}. The {domain_name} describes {domain_description}.
Use the following keywords: {keywords}. Use all the keywords, not just a snippet, and your own knowledge and domain understanding to generate the ontology based on the NeOn methodology for ontology engineering to build the {domain_name} ontology based on the NeOn methodology.

The NeOn methodology starts by specifying the ontology requirements:

  """)

# Prompt 2 – Reuse
send_prompt(f"""The ontology should accurately represent the complexity and hierarchical structure of the domain.
It should be detailed, with well-defined hierarchy levels and interconnected relationships between concepts.
""")



# Prompt 3 – Competency Questions
send_prompt(f"""Based on the generated Specifications of Ontology Requirements, all the keywords given {keywords}, write a list of Competency Questions that the core module of the ontology should be able to answer.
Make it as complete as possible.
""")


# Prompt 4 – Extract Entities, Relations, Axioms
send_prompt(f"""For each Competency Question, extract entities, relations (properties), and axioms that must be introduced in the ontology.
A competency question can help in extracting more than one triple. Do it for all the competency questions.
""")



# Prompt 5 – Initial Conceptual Model
send_prompt(f"""Considering all the generated entities, relations (properties), and axioms, generate a conceptual model expressing the triples of the entities, properties (relations), and axioms in the format (subject-relation-object triples).
Do it for all the entities and properties (relations), and axioms, not just a snippet.

Make sure that your conceptual model is logically consistent, and free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multiple domains or ranges, and Wrong transitive relationships) .""")

# Prompt 6 – Extend Conceptual Model
send_prompt(f"""Extend the conceptual model using keywords: {keywords}, Use your own knowledge of the domain extend the previously generated conecptual model with any missing entities, relations (properties), and axioms.
Print the new triples ONLY in the format (subject-relation-object triples).
Make sure that your conceptual model is logically consistent, and free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships) .
""")

send_prompt(f"""Extend the conceptual model using keywords: {keywords},  Use your own knowledge of the domain extend the previously generated conecptual model with any missing entities, relations (properties), and axioms.
Print the new triples ONLY in the format (subject-relation-object triples).
Make sure that your conceptual model is logically consistent, and free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships) .
""")

send_prompt(f"""Extend the conceptual model using keywords: {keywords},  Use your own knowledge of the domain extend the previously generated conecptual model with any missing entities, relations (properties), and axioms.
Print the new triples ONLY in the format (subject-relation-object triples).
Make sure that your conceptual model is logically consistent, and free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships) .
""")


#Verify Concepts and Relations (Matching Pipeline to eleminate hallucinations)
# Prompt 9 – Serialize to Turtle
send_prompt(f"""Considering the full conceptual model you generated, generate a full ontology serialized in Turtle syntax.

Do it for the whole conceptual model not just a snippet.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print Turtle code between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""Considering the full conceptual model you generated, generate any missing parts of the ontology in Turtle syntax.

Do it for the whole conceptual model not just a snippet.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""Considering the full conceptual model you generated, generate any missing parts of the ontology in Turtle syntax.

Do it for the whole conceptual model not just a snippet.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")


#chat_history = []
# Formal Modeling
send_prompt(f"""For all the entities in the ontology given, introduce Data Properties when meaningful.
Modify the domain and range according to the type of value the Data Property requests.
Do it for the whole ontology, not just a snippet.

Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the inverse property.
An inverse property expresses a two-way relationship between two concepts.
If the ontology contains a property 'hasPart,' its inverse would be 'isPartOf.'
Ensure that every object property that has an inverse relationship is accounted for.
Generate the inverse property for the whole ontology, not just a snippet.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the reflexive property.
A reflexive property is one where an entity can be related to itself, such as 'isSimilarTo.'
Ensure that reflexive properties are appropriately assigned where meaningful.
Generate the reflexive property for the whole ontology, not just a snippet.

Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the symmetric property.
A symmetric property means if entity A is related to entity B, then entity B is also related to entity A, like 'isMarriedTo.'
Ensure symmetric properties are introduced where relevant.
Generate symmetric properties for the whole ontology, not just a snippet.

Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the functional property.
A functional property means an entity can only have one unique value for the property, such as 'hasBirthDate.'
Ensure functional properties are introduced for relevant object properties.
Generate functional properties for the whole ontology, not just a snippet.

Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the transitive property.
A transitive property means if entity A is related to entity B, and B is related to C, then A is also related to C, like 'isAncestorOf.'
Ensure transitive properties are introduced for relevant object properties.
Generate transitive properties for the whole ontology, not just a snippet.

Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")


# Prompt 18 – Add Individuals
send_prompt(f"""Populate the given ontology with meaningful real-world individuals.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

# Prompt 19 – Metadata
send_prompt("If not there in the given ontology, add triples about the ontology IRI, label, version, and description in natural language. Print ONLY the new triples. Use ###start_turtle### and ###end_turtle### markers.")

# Prompt 20 – Comments
send_prompt("""For all the entities and relations (properties) in the given ontology, if missing add a triple that describes its meaning in natural language, using the annotation property rdfs:comment.
Do it for the whole ontology, not just a snippet.
Print ONLY the new triples. Use ###start_turtle### and ###end_turtle### markers.
""")

send_prompt(f""" The current generated ontology lacks the necessary complexity and hierarchical structure to reflect the domain accurately.

Do it for the whole ontology, not just a snippet.
Print ONLY the new triples. Use ###start_turtle### and ###end_turtle### markers.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)

Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

# Syntax, Logic, Pitfall Validation
chat_history = []

"""# Sample Inputs"""

# === SewerNet Ontology - DYNAMIC PLACEHOLDERS === #
persona = """You are an expert knowledge engineer and infrastructure ontologist specializing in the development of semantic frameworks for urban wastewater systems. Holding a PhD in Environmental Engineering with a specialization in Urban Water Infrastructure, and complemented by formal training in semantic web technologies, you bring a unique blend of domain expertise and technical mastery to modeling complex sewer network systems.

You have extensive experience working at the intersection of civil infrastructure, environmental data modeling, and smart city systems. Your expertise lies in understanding the structural, hydraulic, operational, and temporal dimensions of sewer networks—ranging from pipes, manholes, and pumping stations to inspection events, maintenance activities, and compliance with environmental standards.

As a domain expert contributing to the SwerNet ontology, you are skilled in identifying and formalizing essential entities and relationships within the sewer infrastructure domain, including physical components, operational properties, inspection protocols, geospatial references, and regulatory linkages. You utilize RDF, OWL, and Turtle to craft semantically rich and machine-readable ontologies that enable robust data integration, querying, and reasoning across heterogeneous infrastructure datasets.

Your approach is meticulous, scalable, and user-centered—ensuring that the ontologies you design support interoperability among municipalities, utility companies, environmental agencies, and researchers. You focus on creating reusable vocabularies that bridge the gap between fragmented infrastructure records and actionable knowledge for monitoring, planning, risk assessment, and decision support in urban water management.

You are deeply involved in advancing semantic models for smart sewer systems, predictive maintenance, and environmental compliance. Your mission is to enable the transition from static documentation to intelligent, linked data ecosystems that enhance sustainability, resilience, and transparency in wastewater infrastructure management."""

domain_name = "SewerNet Ontology"

domain_description = """
SewerNet – Domain Description

The SewerNet Ontology provides a structured framework for representing the components and management processes of wastewater and stormwater networks. It encompasses:

- **Network Components**: Detailed representation of physical elements such as pipes, manholes, inlets, outlets, and pumping stations, including their attributes and interconnections.

- **Hydraulic and Structural Properties**: Modeling of properties like pipe diameter, material, slope, flow capacity, and structural conditions.

- **Operational Events**: Representation of events related to network management, including inspections, maintenance activities, blockages, overflows, and repairs.

- **Geospatial Information**: Integration of spatial data, including the geographic location of network components, alignment with geostandards, and support for spatial queries.

- **Standards Compliance**: Alignment with the French RAEPA v1.2 geostandard for drinking water supply and sanitation networks, and the INSPIRE European directive, ensuring interoperability and compliance with established norms.

- **Foundational Ontologies**: Incorporation of concepts from the DOLCE-lite foundational ontology and the Time ontology, providing a well-established semantic basis for modeling temporal aspects and general concepts.

SewerNet facilitates data integration, analysis, and management of sewer networks, supporting urban infrastructure planning, maintenance, and decision-making processes.
"""

keywords = "SewerNetwork, Wastewater, Stormwater, Pipe, Manhole, Inlet, Outlet, PumpingStation, Inspection, Maintenance, Blockage, Overflow, Repair, HydraulicProperty, StructuralCondition, GeospatialData, RAEPA, INSPIRE, DOLCE-lite, TimeOntology"

ontology_metrics = "Classes: 150, Object Properties: 40, Data Properties: 20, Individuals: 10"

reuse_example_desc = "SewerNet ontology's classes and properties related to sewer network components, operational events, geospatial information, and compliance with established standards."

few_shot_reuse = """
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
"""

few_shot_entity_extraction = """
Q: What components are included in the sewer network? → Entities: SewerNetwork, Pipe, Manhole, Inlet, Outlet, PumpingStation | Property: hasComponent
Q: What is the location of a specific manhole? → Entities: Manhole, GeospatialPoint | Property: hasLocation
Q: What maintenance activities have been performed on a pipe? → Entities: MaintenanceActivity, Pipe | Property: addresses
Q: What events have occurred in the sewer network? → Entities: Blockage, Overflow, Repair | Property: occursAt / resultsFrom / restores
Q: Which standards does the sewer network comply with? → Entities: SewerNetwork, RAEPAStandard, INSPIREDirective | Property: compliesWith / alignsWith
"""

few_shot_data_properties = """
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
"""

few_shot_individuals = """
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
"""

# === Wine Ontology - DYNAMIC PLACEHOLDERS === #
persona = """You are an expert in wine ontology development and knowledge engineering, specializing in the structured representation of viticulture and oenology knowledge. Holding a PhD in Agricultural Sciences with a focus on Viticulture and Enology, along with formal training in semantic web technologies and data modeling, you bring a unique blend of domain expertise and technical acumen.

You have extensive experience in analyzing the complex interplay between grape varieties, terroir, winemaking practices, and wine characteristics. Your work bridges traditional wine knowledge with modern computational approaches, enabling standardized and interoperable representations of wine-related data.

Your core strength lies in identifying and modeling the key concepts within the wine domain—such as grape varieties, wine styles, production regions, vintages, alcohol content, fermentation methods, and food pairings—and articulating the relationships between them. You excel in designing domain ontologies using RDF and Turtle, creating structured vocabularies that serve both producers and researchers in wine science, trade, and sensory analysis.

With a meticulous, user-centered approach to ontology design, you ensure that the ontologies you build support data integration, semantic search, and automated reasoning across diverse wine databases and applications. You are adept at aligning wine ontologies with broader food and agriculture standards, facilitating data sharing between stakeholders in the wine industry, gastronomy, and regulatory bodies.

Your ultimate goal is to elevate raw and fragmented wine knowledge into coherent, machine-readable frameworks that support advanced analysis, decision-making, and cultural storytelling in the world of wine."""

domain_name = "Wine Ontology"
domain_description = """Wine Ontology – Domain Description
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

Regulatory Aspects: Inclusion of labeling requirements, classification systems, and legal standards governing wine production and marketing."""
keywords = "Wine, GrapeVariety, WineType, WineColor, WineRegion, Winery, Vintage, TastingNote, FoodPairing"
ontology_metrics = "77 classes, 657 logical axioms, 13 object properties, 1 data property, 161 individuals"
reuse_example_desc = "FoodOn ontology's classes and properties related to beverages, ingredients, and food pairings"
few_shot_reuse = """ (Wine - hasIngredient - GrapeVariety)
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
"""

few_shot_entity_extraction = """Q: What grape varieties are used in a wine? → Entities: Wine, GrapeVariety | Property: hasGrapeVariety
Q: Where is this wine produced? → Entities: Wine, WineRegion | Property: producedIn
Q: What food does this wine pair well with? → Entities: Wine, Food | Property: pairsWith
Q: What is the color of this wine? → Entities: Wine, WineColor | Property: hasColor
Q: Who is the producer of this wine? → Entities: Wine, Winery | Property: producedBy
Q: What is the vintage of this wine? → Entities: Wine, Vintage | Property: hasVintage
Q: What is the tasting note of this wine? → Entities: Wine, TastingNote | Property: hasTastingNote"""

few_shot_data_properties = """
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

"""
few_shot_individuals = """
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
"""

# === Chemical Information Ontology (CHEMINF) - DYNAMIC PLACEHOLDERS === #
persona = """You are an expert cheminformatician and knowledge engineer specializing in the development of ontologies for chemical information systems. Holding a PhD in Chemistry with a concentration in cheminformatics and semantic technologies, you have extensive experience in both theoretical chemistry and computational representation of chemical knowledge.

Your expertise centers on the structured representation of chemical descriptors, computational algorithms, molecular formats, and experimental properties using semantic web standards. You specialize in modeling entities and relationships essential to chemical research and data interoperability—such as molecular weight, logP, SMILES and InChI formats, software implementations, and prediction algorithms.

As a core contributor to and expert user of the Chemical Information Ontology (CHEMINF) hosted on BioPortal, you ensure that your ontologies align with FAIR principles (Findable, Accessible, Interoperable, and Reusable). You use tools such as RDF, OWL, and Turtle syntax to build precise, machine-readable models that enable advanced querying, data annotation, and integration across cheminformatics platforms, chemical databases, and bioinformatics systems.

You have a meticulous and user-centric approach to ontology design, aiming to bridge the gap between raw chemical data and actionable insights for drug discovery, toxicology, materials science, and biomedical research. You are especially skilled at linking CHEMINF terms with related ontologies like ChEBI, SIO, and PROV-O to support semantic inference, provenance tracking, and data harmonization.

Your goal is to advance the semantic representation of chemical knowledge in ways that support automated reasoning, enhance scientific reproducibility, and enable powerful cross-disciplinary research. You play a key role in translating the complexity of chemical information into interoperable, structured formats that empower researchers, developers, and data scientists across the chemical and life sciences."""

domain_name = "Chemical Information Ontology (CHEMINF)"

domain_description = """
CHEMINF – Domain Description

The Chemical Information Ontology (CHEMINF) provides a structured framework for representing chemical information entities, particularly those used in cheminformatics. It encompasses:

- **Chemical Descriptors**: Quantitative and qualitative properties of chemical entities, such as molecular weight, logP, and topological polar surface area.

- **Chemical Graphs**: Representations of molecular structures, including various encoding formats like SMILES and InChI.

- **Algorithms and Software Implementations**: Computational methods and tools used to calculate chemical descriptors and process chemical information.

- **Data Formats and Specifications**: Standards for representing chemical data, including file formats like MOL and SDF.

- **Provenance and Metadata**: Information about the origin, calculation methods, and context of chemical data, ensuring reproducibility and data integration.

CHEMINF facilitates the integration, annotation, and retrieval of chemical information across databases and software applications, supporting advanced queries and semantic reasoning in chemical research.
"""

keywords = "ChemicalDescriptor, ChemicalGraph, Algorithm, SoftwareImplementation, DataFormat, Provenance, MolecularStructure, SMILES, InChI, logP, MolecularWeight, ChemicalEntity, ChemicalDescriptor, DescriptorValue, MolecularStructure, SMILES, InChI, MolecularWeight, logP, TopologicalPolarSurfaceArea, TanimotoCoefficient, SubstructureFingerprint, SimilarityScore, DescriptorCalculation, SoftwareTool, Algorithm, RDFGraph, Provenance, DataFormat, DescriptorOntology, SDF, QSAR, ToxicityPrediction, StructureRepresentation, InferenceEngine, ConfidenceScore, OntologyAlignment, ChemicalDataset"

ontology_metrics = "855 classes, 111 object properties, 7 data properties, 20 individuals"

reuse_example_desc = "CHEMINF ontology's classes and properties related to chemical descriptors, molecular representations, computational algorithms, and data formats."

few_shot_reuse = """
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
"""

few_shot_entity_extraction = """
Q: What is the molecular weight of caffeine? → Entities: Caffeine, MolecularWeight | Property: hasDescriptor
Q: Which algorithm calculates the logP value? → Entities: logP, Algorithm | Property: isCalculatedBy
Q: In which format is the chemical structure represented? → Entities: ChemicalGraph, DataFormatSpecification | Property: encodedIn
Q: What software was used to compute the topological polar surface area? → Entities: TopologicalPolarSurfaceArea, SoftwareImplementation | Property: isCalculatedBy
Q: What is the SMILES representation of aspirin? → Entities: Aspirin, SMILESFormat | Property: encodedIn
"""

few_shot_data_properties = """
:logP a :ChemicalDescriptor ;
    rdfs:comment "Represents the logarithm of the partition coefficient (logP), indicating a compound's hydrophobicity." .

:SMILESFormat a :DataFormatSpecification ;
    rdfs:comment "Specifies the SMILES (Simplified Molecular Input Line Entry System) format used to represent molecular structures as text." .

:AlgorithmX a :Algorithm ;
    rdfs:comment "A placeholder or representative algorithm used for molecular analysis or prediction." .

:SoftwareY a :SoftwareImplementation ;
    rdfs:comment "A representative software implementation used to process or analyze chemical data." .

:MolecularWeight a :ChemicalDescriptor ;
    rdfs:comment "Represents the molecular weight of a chemical compound, calculated based on atomic composition." .

"""

few_shot_individuals = """
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

"""

# === Environmental microbiology domain (AquaDiva) - DYNAMIC PLACEHOLDERS === #
persona = """You are an expert in environmental microbiology and subsurface ecosystem modeling, with a focus on formalizing knowledge about microbial communities, geochemical processes, and environmental interactions. Holding a PhD in Environmental Microbiology and trained in knowledge representation and semantic web technologies, you specialize in translating complex, multidisciplinary research into interoperable ontological structures.

Your work spans the integration of microbiological, hydrological, and geochemical data to understand subterranean ecosystems. You are skilled at identifying core domain entities—such as microbial taxa, biogeochemical cycles, sampling environments, and measurement techniques—and modeling their interrelations using OWL ontologies.

You have contributed to the design of ontologies used in ecological monitoring and microbial community profiling, ensuring logical consistency and alignment with FAIR data principles. You also focus on interoperability with broader environmental ontologies such as ENVO, MIxS, and the Environment Ontology, promoting data reuse across research infrastructures.

Your ontologies support researchers in querying microbial function, tracking ecosystem responses, and integrating multi-omics data in large-scale ecological studies. Your goal is to create structured, computable frameworks that bridge environmental microbiology and data science to enable advanced ecosystem analysis and policy-relevant insights."""

domain_name = "AquaDiva Ontology"
domain_description = """AquaDiva Ontology – Domain Description
The AquaDiva Ontology formalizes knowledge in the domain of subsurface environmental microbiology, focusing on interactions between microbial life and the geological environment. Key subdomains include:

Microbial Taxonomy and Function: Representing microbial clades, functional roles (e.g., methanogenesis, denitrification), and metabolic pathways in subsurface ecosystems.

Sampling Environments: Modeling environments such as aquifers, karst systems, and boreholes, with spatio-temporal descriptors and geochemical conditions.

Measurement and Instrumentation: Capturing techniques such as 16S rRNA gene sequencing, stable isotope probing, and flow cytometry, along with associated metadata.

Environmental Variables: Encoding parameters such as pH, oxygen levels, temperature, pressure, and nutrient concentrations that define habitat niches.

Biogeochemical Processes: Representing transformations like sulfur cycling, iron reduction, and carbon turnover mediated by microbial activity.

Spatial and Temporal Context: Modeling location metadata (e.g., coordinates, depth, geological layer) and time-series sampling.

Organisms and Populations: Describing taxa, strain-level distinctions, abundance data, and genomic traits relevant to ecological dynamics.

Ecosystem Interactions: Capturing trophic relationships, symbioses, and perturbation responses such as anthropogenic disturbance or drought.

This ontology supports cross-study integration of microbial ecological data and environmental measurements across sites and experiments in projects like the Collaborative Research Centre AquaDiva."""
keywords = "MicrobialTaxon, SamplingSite, Habitat, BiogeochemicalProcess, EnvironmentalParameter, SequencingTechnique, MicrobialFunction, Abundance, TimePoint, SubsurfaceZone"
ontology_metrics = "802 classes, 11,270 axioms, 108 properties, 240 individuals"
reuse_example_desc = "ENVO terms for environmental conditions and MIxS descriptors for microbial sampling metadata"
few_shot_reuse = """ (MicrobialTaxon - inhabits - envo:Aquifer)
(SamplingSite - locatedIn - envo:KarstSystem)
(MicrobialTaxon - performs - obo:GO_0019641)  # GO term for aerobic respiration
(Sample - collectedUsing - mixs:Filtration)
(MicrobialCommunity - hasFunction - eco:EcosystemFunction)
(Sample - hasEnvironmentalCondition - envo:LowOxygen)
(Process - mediatedBy - MicrobialTaxon)
(Habitat - hasDepth - obo:PATO_0001595)
(MicrobialTaxon - partOf - MicrobialCommunity)
(MicrobialTaxon - associatedWith - BiogeochemicalProcess)
"""

few_shot_entity_extraction = """Q: What microbial taxa were found in the sample? → Entities: Sample, MicrobialTaxon | Property: containsTaxon
Q: What habitat was the microbial community isolated from? → Entities: MicrobialCommunity, Habitat | Property: isolatedFrom
Q: What function does this taxon perform? → Entities: MicrobialTaxon, MicrobialFunction | Property: performsFunction
Q: Where was the sample taken? → Entities: Sample, SamplingSite | Property: collectedFrom
Q: What technique was used to sequence the sample? → Entities: Sample, SequencingTechnique | Property: sequencedUsing
Q: What is the oxygen level of the sample site? → Entities: SamplingSite, EnvironmentalParameter | Property: hasOxygenLevel"""

few_shot_data_properties = """
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
"""

few_shot_individuals = """
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
"""

"""## Full NeOn-GPT Pipeline Mistral"""

import requests
import re
import time


# === DYNAMIC PLACEHOLDERS === #
# Extract Using NLP techniques and RAG from Unstrucutred Text and existing ontological resources.
persona = "You are an expert knowledge and ontology engineer using the NeOn methodology. "
domain_name = "Cybersecurity Threat Intelligence"
domain_description = "concepts and relationships related to identifying, describing, and classifying cyber threats and threat actors"
keywords = "ThreatActor, Vulnerability, Exploit, Tactic, Technique, Procedure, IndicatorOfCompromise"
ontology_metrics = "35 classes, 10 object properties, 7 data properties, 3 individuals"
reuse_example_desc = "STIX ontology describing cyber threat concepts and entities"
few_shot_reuse = "(ThreatActor - uses - Tactic), (IndicatorOfCompromise - detectedBy - Tool)"
# add axioms (subclasses)
few_shot_entity_extraction = "Q: What are the tactics used by a threat actor? → Entities: ThreatActor, Tactic | Property: uses"
few_shot_data_properties = ":APT28 a :ThreatActor .\n:PhishingEmail a :Tactic ."
few_shot_individuals = ":APT28 a :ThreatActor .\n:PhishingEmail a :Tactic ."


# Mistral AI API Setup
API_KEY = "YOUR-API-KEY"  # Replace with your actual API key
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
TURTLE_OUTPUT_FILE = domain_name + "_ontology.ttl"

chat_history = []

# Initialize chat history
chat_history = [
    {"role": "system", "content": persona}
]

def send_prompt(prompt, max_retries=3):
    """Send prompt and parse any turtle syntax between markers."""
    chat_history.append({"role": "user", "content": prompt})
    for attempt in range(1, max_retries + 1):
      response = requests.post(
        MISTRAL_API_URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": "open-mistral-7b", "messages": chat_history}
    )

      if response.status_code == 200:
          reply = response.json()["choices"][0]["message"]["content"]
          chat_history.append({"role": "assistant", "content": reply})
          print("\n--- MODEL RESPONSE ---\n", reply)
          extract_and_save_turtle(reply)
          return reply

      elif response.status_code == 429:
            if attempt < max_retries:
                wait_time =  20
                print(f"Rate limit exceeded (429). Retrying in {wait_time} seconds... (Attempt {attempt}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(" Error: Reached max retry attempts due to rate limiting.")
                return f"Error: 429, Rate limit exceeded after {max_retries} retries."

      else:
            print(f" Error: {response.status_code}, {response.text}")
            return f"Error: {response.status_code}, {response.text}"

TURTLE_OUTPUT_FILE = domain_name+"_ontology.ttl"
# Initialize the Turtle file (empty it once at the beginning of the script)
with open(TURTLE_OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("# Generated Turtle ontology\n\n")


def send_prompt_with_ontology(prompt, max_retries=3):
    """Send prompt using the Turtle ontology file as stateless context."""
    try:
        with open(TURTLE_OUTPUT_FILE, "r", encoding="utf-8") as f:
            ontology_text = f.read()
    except FileNotFoundError:
        ontology_text = "# Ontology file not found.\n"

    system_prompt = {
        "role": "system",
        "content": (
            f"{persona} The following ontology is given in Turtle format.\n"
            "Use it to answer the prompt precisely and logically.\n\n"
            "###start_turtle###\n"
            f"{ontology_text}\n"
            "###end_turtle###"
        )
    }

    user_prompt = {"role": "user", "content": prompt}

    for attempt in range(1, max_retries + 1):
        response = requests.post(
            MISTRAL_API_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": "open-mistral-7b", "messages": [system_prompt, user_prompt]}
        )

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            print("\n--- MODEL RESPONSE ---\n", reply)
            extract_and_save_turtle(reply)
            return reply

        elif response.status_code == 429:
            wait_time = 20
            print(f" Rate limit exceeded. Retrying in {wait_time}s... (Attempt {attempt}/{max_retries})")
            time.sleep(wait_time)
        else:
            print(f" Error: {response.status_code}, {response.text}")
            return f"Error: {response.status_code}, {response.text}"

def extract_and_save_turtle(response_text):
    """Extract turtle code between markers and safely append to the Turtle file."""
    matches = re.findall(r"###start_turtle###(.*?)###end_turtle###", response_text, re.DOTALL)


    if not matches:
        print(" No Turtle code found in response.")
        return

    with open(TURTLE_OUTPUT_FILE, "a", encoding="utf-8") as f:
        for i, block in enumerate(matches, start=1):
            cleaned_block = block.strip()
            if cleaned_block:
                f.write(f"# --- Turtle block from prompt {len(chat_history)//2} ---\n")
                f.write(cleaned_block + "\n\n")
                print(f" Appended Turtle block {i} to {TURTLE_OUTPUT_FILE}")





# === ONTOLOGY GENERATION PROMPT PIPELINE === #

# Prompt 1 – Specification
send_prompt(f"""You are a {persona}. The {domain_name} describes {domain_description}.
Use the following keywords: {keywords}. Use all the keywords, not just a snippet, and your own knowledge and domain understanding to generate the ontology based on the NeOn methodology for ontology engineering to build the {domain_name} ontology based on the NeOn methodology.
The original ontology has {ontology_metrics}. Make sure that the generated ontology reflects the previous metrics and has a high subclass count; if the class count is n, the subclass count should at least be n-1.
The NeOn methodology starts by specifying the following ontology requirements:
  - The purpose of the ontology
  - The scope of the ontology
  - The target group of the ontology
  - The intended uses
  - The functional requirements
  - The non-functional requirements
  """)

# Prompt 2 – Reuse
send_prompt(f"""The ontology should accurately represent the complexity and hierarchical structure of the domain.
It should be detailed, with well-defined hierarchy levels and interconnected relationships between concepts.
This can be achieved with ontology reuse.
Reuse refers to utilizing existing ontological knowledge or structures as input in the development of new ontologies.
It allows for more efficient and consistent knowledge representation across applications.
Reuse the following example to improve the ontology structure from the {reuse_example_desc}. Example: {few_shot_reuse}.""")



# Prompt 3 – Competency Questions
send_prompt(f"""Based on the generated Specifications of Ontology Requirements, all the keywords given {keywords}, write a list of Competency Questions that the core module of the ontology should be able to answer.
Make it as complete as possible.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count; if the class count is n, the subclass count should at least be n-1.
""")


# Prompt 4 – Extract Entities, Relations, Axioms
send_prompt(f"""For each Competency Question, extract entities, relations (properties), and axioms that must be introduced in the ontology.
A competency question can help in extracting more than one triple. Do it for all the competency questions.
Examples: {few_shot_entity_extraction}.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count; if the class count is n, the subclass count should at least be n-1.
""")



# Prompt 5 – Initial Conceptual Model
send_prompt(f"""Considering all the generated entities, relations (properties), and axioms, generate a conceptual model expressing the triples of the entities, properties (relations), and axioms in the format (subject-relation-object triples).
Do it for all the entities and properties (relations), and axioms, not just a snippet.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count; if the class count is n, the subclass count should at least be n-1.
Make sure that your conceptual model is logically consistent, and free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multiple domains or ranges, and Wrong transitive relationships) .""")

# Prompt 6 – Extend Conceptual Model
send_prompt(f"""Extend the conceptual model using keywords: {keywords}, Reuse Example {reuse_example_desc} {few_shot_reuse}, and your own knowledge of the domain extend the previously generated conecptual model with any missing entities, relations (properties), and axioms.
Print the new triples ONLY in the format (subject-relation-object triples).
Make sure that your conceptual model is logically consistent, and free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships) .
""")

send_prompt(f"""Extend the conceptual model using keywords: {keywords}, Reuse Example {reuse_example_desc} {few_shot_reuse}, and your own knowledge of the domain extend the previously generated conecptual model with any missing entities, relations (properties), and axioms.
Print the new triples ONLY in the format (subject-relation-object triples).
Make sure that your conceptual model is logically consistent, and free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships) .
""")

send_prompt(f"""Extend the conceptual model using keywords: {keywords}, Reuse Example {reuse_example_desc} {few_shot_reuse}, and your own knowledge of the domain extend the previously generated conecptual model with any missing entities, relations (properties), and axioms.
Print the new triples ONLY in the format (subject-relation-object triples).
Make sure that your conceptual model is logically consistent, and free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships) .
""")


#Verify Concepts and Relations (Matching Pipeline to eleminate hallucinations)
# Prompt 9 – Serialize to Turtle
send_prompt(f"""Considering the full conceptual model you generated, generate a full ontology serialized in Turtle syntax.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Do it for the whole conceptual model not just a snippet.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print Turtle code between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""Considering the full conceptual model you generated, generate any missing parts of the ontology in Turtle syntax.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Do it for the whole conceptual model not just a snippet.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""Considering the full conceptual model you generated, generate any missing parts of the ontology in Turtle syntax.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Do it for the whole conceptual model not just a snippet.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")


#chat_history = []
# Formal Modeling
send_prompt(f"""For all the entities in the ontology given, introduce Data Properties when meaningful, such as: {few_shot_data_properties}.
Modify the domain and range according to the type of value the Data Property requests.
Do it for the whole ontology, not just a snippet.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the inverse property.
An inverse property expresses a two-way relationship between two concepts.
If the ontology contains a property 'hasPart,' its inverse would be 'isPartOf.'
Ensure that every object property that has an inverse relationship is accounted for.
Generate the inverse property for the whole ontology, not just a snippet.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the reflexive property.
A reflexive property is one where an entity can be related to itself, such as 'isSimilarTo.'
Ensure that reflexive properties are appropriately assigned where meaningful.
Generate the reflexive property for the whole ontology, not just a snippet.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the symmetric property.
A symmetric property means if entity A is related to entity B, then entity B is also related to entity A, like 'isMarriedTo.'
Ensure symmetric properties are introduced where relevant.
Generate symmetric properties for the whole ontology, not just a snippet.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the functional property.
A functional property means an entity can only have one unique value for the property, such as 'hasBirthDate.'
Ensure functional properties are introduced for relevant object properties.
Generate functional properties for the whole ontology, not just a snippet.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

send_prompt(f"""For all object properties in the ontology given, if lacking, generate the transitive property.
A transitive property means if entity A is related to entity B, and B is related to C, then A is also related to C, like 'isAncestorOf.'
Ensure transitive properties are introduced for relevant object properties.
Generate transitive properties for the whole ontology, not just a snippet.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")


# Prompt 18 – Add Individuals
send_prompt(f"""Populate the given ontology with meaningful real-world individuals. Examples: {few_shot_individuals}.
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

# Prompt 19 – Metadata
send_prompt("If not there in the given ontology, add triples about the ontology IRI, label, version, and description in natural language. Print ONLY the new triples. Use ###start_turtle### and ###end_turtle### markers.")

# Prompt 20 – Comments
send_prompt("""For all the entities and relations (properties) in the given ontology, if missing add a triple that describes its meaning in natural language, using the annotation property rdfs:comment.
Do it for the whole ontology, not just a snippet.
Print ONLY the new triples. Use ###start_turtle### and ###end_turtle### markers.
""")

send_prompt(f""" The current generated ontology lacks the necessary complexity and hierarchical structure to reflect the domain accurately.
Use the example below to refine the structure of the ontology: {reuse_example_desc}. Example: {few_shot_reuse}.
Do it for the whole ontology, not just a snippet.
Print ONLY the new triples. Use ###start_turtle### and ###end_turtle### markers.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
The original ontology has {ontology_metrics}.
Make sure that the generated ontology reflects the previous metrics and has a high subclass count.
Make sure to generate the necessary description in natural language for all entities and relations (properties).
Make sure the syntax is correct, all entities and properties have correct prefixes, the ontology is consistent, and free from common pitfalls.",
Make sure:
          - the turtle syntax is correct
          - all the entities and properties have the correct prefixes
          - the prefix for the ontology is declared
          - the ontology is consistent
          - the ontology is free from common pitfalls (e.g., Wrong inverse relationships, Cycles in a class hierarchy, Multipple domains or ranges, and Wrong transitive relationships)
Print the new Turtle code ONLY between ###start_turtle### and ###end_turtle###
""")

# Syntax, Logic, Pitfall Validation
chat_history = []

"""## Ontology Verification Prompts"""

send_prompt(f"Based on the error message below, correct the syntax error in the affected part of the ontology. Ensure that the revised ontology adheres to proper RDF/Turtle syntax. {RDFLib_Syntax_Error_Message} {Affected_Part_of_the_Ontology}")

send_prompt(f"Based on the error message below, fix the inconsistency in the affected part of the ontology. {HermiT_Reasoner_Error_Message} {Affected_Part_of_the_Ontology}")

send_prompt(f"Based on the error message below, fix the pitfall in the affected part of the ontology. {OOPS_API_Error_Message} {Affected_Part_of_the_Ontology}")

