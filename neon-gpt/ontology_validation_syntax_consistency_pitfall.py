!pip install rdflib
from rdflib import Graph
!pip install owlready2 --upgrade
from owlready2 import *
# Install Java
!apt-get update
!apt-get install openjdk-11-jdk-headless -qq > /dev/null
import os
from rdflib import Graph

turtle_ontology_path = "/content/wine_gpt_4o.ttl"
ontology_path = "/content/wine_gpt_4o"

"""# Syntax Check"""

#Syntax Check
def read_turtle_file_as_string(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        print(file_path)
        turtle_content = file.read()
    return turtle_content


file_path = turtle_ontology_path
turtle_data = read_turtle_file_as_string(file_path)

#turtle_data = """ """
g = Graph()

try:
    g.parse(data=turtle_data, format="turtle")
    print("Turtle syntax is correct.")
except Exception as e:  # This catches any exception, including BadSyntax and ParserError
    print(f"Error parsing Turtle file: {e}")

"""# Consistency Check with HermiT and Pellet reasoner

https://owlready2.readthedocs.io/en/latest/reasoning.html
"""

#Helper Convert .ttl to .xml OWL/XML ontology
def convert_ttl_to_xml(ttl_file_path, xml_file_path):
    # Create an empty Graph
    g = Graph()

    # Parse the .ttl file
    g.parse(ttl_file_path, format='turtle')

    # Serialize the Graph to .xml format
    g.serialize(destination=xml_file_path, format='xml')

from rdflib import Graph

# Define the input and output file paths
input_file = turtle_ontology_path # This is a Turtle file
output_file = ontology_path+ ".rdf"  # Use .rdf or .owl for RDF/XML

# Create an RDF graph
g = Graph()

# Parse the Turtle file correctly
g.parse(input_file, format="turtle")

# Serialize the graph into RDF/XML
g.serialize(destination=output_file, format="xml")

print(f"Conversion complete! RDF/XML saved to {output_file}")

#Loading XML ontology
#from owlready2 import *

#def load_ontology(file_path):
 #   try:
  #      onto = get_ontology(file_path).load()
   #     print("Ontology loaded successfully.")
   # except OwlReadyOntologyParsingError as e:
    #    print(f"Failed to load ontology due to parsing error: {str(e)}")

#def main():
 #   file_path = "/content/example3.xml"  # Update this to your actual file path
  #  load_ontology(file_path)

#if __name__ == "__main__":
 #   main()

#Consistency Check with HermiT reasoner using HermiT.jar file download from: http://www.hermit-reasoner.com/
#Change jar_path
import subprocess
import os
xml_file_path = output_file
# Verify the existence of Hermit.jar file
jar_path = '/content/HermiT.jar'
if not os.path.exists(jar_path):
    print(f"Error: The file {jar_path} does not exist.")
else:
    # If the file exists, run the subprocess
    hermit = subprocess.run(
        ["java", "-jar", jar_path, '-k', xml_file_path],
        capture_output=True,
        text=True
    )
    print(hermit.stdout)
    print(hermit.stderr)

# Set the path to the Java executable directly
java_path = "/usr/lib/jvm/java-11-openjdk-amd64/bin/java"
os.environ["JAVA_HOME"] = java_path
os.environ["PATH"] += os.pathsep + java_path

# Verify the Java version to ensure it's correctly set
!{java_path} -version

def load_ontology(file_path):
    try:
        onto = get_ontology(file_path).load()
        print("Ontology loaded successfully.")
        return onto
    except Exception as e:  # Broadened the exception catching to see any error
        print(f"Failed to load ontology due to parsing error: {str(e)}")
        return None

def check_for_inconsistencies(onto):
    if onto is None:
        print("No ontology loaded, skipping consistency check.")
        return

    with onto:
        try:
            sync_reasoner()  # This invokes the reasoner and checks consistency
            print("The ontology is consistent.")
        except OwlReadyInconsistentOntologyError:
            print("The ontology has inconsistencies.")
        except Exception as e:  # Catching other possible exceptions
            print(f"An error occurred during reasoning: {str(e)}")

def main():
    file_path = xml_file_path # Make sure this is the correct path
    onto = load_ontology(file_path)
    check_for_inconsistencies(onto)

if __name__ == "__main__":
    main()

#Pellet Reasoner
def load_ontology(file_path):
    try:
        onto = get_ontology(file_path).load()
        print("Ontology loaded successfully.")
        return onto
    except Exception as e:
        print(f"Failed to load ontology due to parsing error: {str(e)}")
        return None

def check_for_inconsistencies(onto):
    if onto is None:
        print("No ontology loaded, skipping consistency check.")
        return

    with onto:
        try:
            # Using Pellet reasoner to check consistency and infer knowledge
            # Set debug level to 2 for detailed explanations
            sync_reasoner_pellet(infer_property_values=True, infer_data_property_values=True, debug=2)
            print("The ontology is consistent.")
        except OwlReadyInconsistentOntologyError:
            print("The ontology has inconsistencies.")
            # Additional explanations will be output due to debug=2
        except Exception as e:
            print(f"An error occurred during reasoning with Pellet: {str(e)}")

def main():
    file_path = output_file  # Update this path to your file
    onto = load_ontology(file_path)
    check_for_inconsistencies(onto)

if __name__ == "__main__":
    main()

"""# Common Pitfall Check (Custom-built Module)"""

# Common Pitfall check

from rdflib import Graph, URIRef, RDF, RDFS, OWL
import rdflib

class OntologyPitfallDetector:
    def __init__(self, turtle_file):
        self.graph = Graph()
        self.graph.parse(turtle_file, format="turtle")
        self.pitfalls = []

    def detect_missing_labels(self):
        # Check for classes and properties without rdfs:label
        for s in self.graph.subjects(RDF.type, RDFS.Class):
            if not (s, RDFS.label, None) in self.graph:
                self.pitfalls.append(f"Class {s} is missing an rdfs:label.")

        for s in self.graph.subjects(RDF.type, RDF.Property):
            if not (s, RDFS.label, None) in self.graph:
                self.pitfalls.append(f"Property {s} is missing an rdfs:label.")

    def detect_unconnected_classes(self):
        # Check for classes not used in any triple
        for s in self.graph.subjects(RDF.type, RDFS.Class):
            if not (None, None, s) in self.graph and not (s, None, None) in self.graph:
                self.pitfalls.append(f"Class {s} is not connected to any other resources.")

    def detect_cyclic_subclassing(self):
        # Detect cyclic subclassing
        def detect_cycle(start, graph, visited, stack):
            visited.add(start)
            stack.add(start)
            for subclass in graph.objects(start, RDFS.subClassOf):
                if subclass not in visited:
                    if detect_cycle(subclass, graph, visited, stack):
                        return True
                elif subclass in stack:
                    return True
            stack.remove(start)
            return False

        visited = set()
        stack = set()
        for cls in self.graph.subjects(RDF.type, RDFS.Class):
            if cls not in visited:
                if detect_cycle(cls, self.graph, visited, stack):
                    self.pitfalls.append(f"Cyclic subclassing detected involving {cls}.")

    def detect_missing_disjointness(self):
        # Check for classes that are not explicitly disjoint
        classes = list(self.graph.subjects(RDF.type, RDFS.Class))
        for i, cls1 in enumerate(classes):
            for cls2 in classes[i+1:]:
                if (cls1, OWL.disjointWith, cls2) not in self.graph and (cls2, OWL.disjointWith, cls1) not in self.graph:
                    # Check if the two classes have any intersection instances
                    instances_cls1 = set(self.graph.subjects(RDF.type, cls1))
                    instances_cls2 = set(self.graph.subjects(RDF.type, cls2))
                    if instances_cls1 & instances_cls2:
                        self.pitfalls.append(f"Classes {cls1} and {cls2} are missing disjointness and have overlapping instances.")

    def detect_all_pitfalls(self):
        self.detect_missing_labels()
        self.detect_unconnected_classes()
        self.detect_cyclic_subclassing()
        self.detect_missing_disjointness()
        return self.pitfalls

# Usage example
if __name__ == "__main__":
    turtle_ontology_path = turtle_ontology_path  # Update this path to your Turtle file
    detector = OntologyPitfallDetector(turtle_ontology_path)

    pitfalls = detector.detect_all_pitfalls()
    print(len(pitfalls))
    for pitfall in pitfalls:
        print(pitfall)

#import rdflib

#def merge_ontologies(file1, file2, output_file):
    # Create an RDF graph
 #   g = rdflib.Graph()

    # Parse the first ontology file
  #  g.parse(file1, format='turtle')

    # Parse the second ontology file
   # g.parse(file2, format='turtle')

    # Serialize and write the merged graph to a new file
    #g.serialize(destination=output_file, format='turtle')
    #print(f"Merged ontology saved to {output_file}")

# Example usage:
#merge_ontologies('/content/AquaDiva2.ttl', '/content/AquaDiva4.ttl', '/content/AquaDivaMergedNew.ttl')

"""
Ontology Validation Script
--------------------------
This script performs the following validations on a Turtle-based OWL ontology:
1. Syntax checking using RDFLib
2. Conversion to RDF/XML format
3. Logical consistency checking with HermiT and Pellet reasoners
4. Custom pitfall detection (missing labels, cyclic subclassing, etc.)
"""

import os
import subprocess
from rdflib import Graph, RDF, RDFS, OWL, URIRef
from owlready2 import get_ontology, sync_reasoner, sync_reasoner_pellet, OwlReadyInconsistentOntologyError

# ========== CONFIGURATION ==========
TURTLE_FILE = "/content/wine_gpt_4o.ttl"
RDF_XML_FILE = "/content/wine_gpt_4o.rdf"
HERMIT_JAR_PATH = "/content/HermiT.jar"
JAVA_PATH = "/usr/lib/jvm/java-11-openjdk-amd64/bin/java"

# ========== STEP 1: Syntax Check ==========
def check_syntax(file_path):
    g = Graph()
    try:
        g.parse(file_path, format="turtle")
        print("Syntax is valid.")
    except Exception as e:
        print(f"Syntax error: {e}")

# ========== STEP 2: Convert TTL to RDF/XML ==========
def convert_to_rdfxml(ttl_path, xml_path):
    g = Graph()
    g.parse(ttl_path, format='turtle')
    g.serialize(destination=xml_path, format='xml')
    print(f"Converted to RDF/XML: {xml_path}")

# ========== STEP 3: Consistency Check with HermiT ==========
def check_with_hermit(xml_file):
    if not os.path.exists(HERMIT_JAR_PATH):
        print(f"HermiT jar not found at {HERMIT_JAR_PATH}")
        return
    result = subprocess.run(
        ["java", "-jar", HERMIT_JAR_PATH, '-k', xml_file],
        capture_output=True, text=True
    )
    print("HermiT output:")
    print(result.stdout)
    print(result.stderr)

# ========== STEP 4: Consistency Check with Pellet ==========
def check_with_pellet(file_path):
    try:
        onto = get_ontology(f"file://{file_path}").load()
        with onto:
            sync_reasoner_pellet(infer_property_values=True, infer_data_property_values=True, debug=2)
            # Check for unsatisfiable classes
            unsat = [cls for cls in onto.classes() if cls.equivalent_to and any(isinstance(eq, Nothing) for eq in cls.equivalent_to)]
            if unsat:
                print("Ontology contains unsatisfiable classes:")
                for cls in unsat:
                    print(f" - {cls.name}")
            else:
                print("Ontology is consistent with Pellet.")
    except OwlReadyInconsistentOntologyError:
        print("Ontology is inconsistent (Pellet).")
    except Exception as e:
        print(f"Pellet error: {e}")

# ========== STEP 5: Pitfall Detection ==========
class OntologyPitfallDetector:
    def __init__(self, turtle_file):
        self.graph = Graph()
        self.graph.parse(turtle_file, format="turtle")
        self.pitfalls = []

    def detect_missing_labels(self):
        for s in self.graph.subjects(RDF.type, RDFS.Class):
            if not (s, RDFS.label, None) in self.graph:
                self.pitfalls.append(f"Class {s} is missing rdfs:label.")
        for s in self.graph.subjects(RDF.type, RDF.Property):
            if not (s, RDFS.label, None) in self.graph:
                self.pitfalls.append(f"Property {s} is missing rdfs:label.")

    def detect_unconnected_classes(self):
        for s in self.graph.subjects(RDF.type, RDFS.Class):
            if not (None, None, s) in self.graph and not (s, None, None) in self.graph:
                self.pitfalls.append(f"Class {s} is unconnected to any triples.")

    def detect_cyclic_subclassing(self):
        def detect_cycle(start, graph, visited, stack):
            visited.add(start)
            stack.add(start)
            for subclass in graph.objects(start, RDFS.subClassOf):
                if subclass not in visited:
                    if detect_cycle(subclass, graph, visited, stack):
                        return True
                elif subclass in stack:
                    return True
            stack.remove(start)
            return False

        visited = set()
        stack = set()
        for cls in self.graph.subjects(RDF.type, RDFS.Class):
            if cls not in visited:
                if detect_cycle(cls, self.graph, visited, stack):
                    self.pitfalls.append(f"Cyclic subclassing detected involving {cls}.")

    def detect_missing_disjointness(self):
        classes = list(self.graph.subjects(RDF.type, RDFS.Class))
        for i, cls1 in enumerate(classes):
            for cls2 in classes[i+1:]:
                if (cls1, OWL.disjointWith, cls2) not in self.graph and (cls2, OWL.disjointWith, cls1) not in self.graph:
                    instances1 = set(self.graph.subjects(RDF.type, cls1))
                    instances2 = set(self.graph.subjects(RDF.type, cls2))
                    if instances1 & instances2:
                        self.pitfalls.append(f"Classes {cls1} and {cls2} share instances but lack disjointness.")

    def detect_all(self):
        self.detect_missing_labels()
        self.detect_unconnected_classes()
        self.detect_cyclic_subclassing()
        self.detect_missing_disjointness()
        return self.pitfalls

# ========== MAIN ==========
if __name__ == "__main__":
    check_syntax(TURTLE_FILE)
    convert_to_rdfxml(TURTLE_FILE, RDF_XML_FILE)
    check_with_hermit(RDF_XML_FILE)
    check_with_pellet(RDF_XML_FILE)

    print("\n--- Pitfall Detection ---")
    detector = OntologyPitfallDetector(TURTLE_FILE)
    pitfalls = detector.detect_all()
    pit = "--- Number of Pitfalls = " + str(len(pitfalls))+"---"
    print(pit)
    for p in pitfalls:
        print(f"⚠ {p}")

import requests
from rdflib import Graph

#  Provide the path to your .ttl ontology file
turtle_file_path = "/content/wine_gpt_4o.ttl"  # Change this to your actual path

# Convert Turtle to RDF/XML string
g = Graph()
g.parse(turtle_file_path, format="turtle")
rdfxml_data = g.serialize(format="xml")

# Wrap RDF/XML in OOPS request format
xml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<OOPSRequest>
  <OntologyUrl></OntologyUrl>
  <OntologyContent><![CDATA[
{rdfxml_data}
  ]]></OntologyContent>
  <Pitfalls>10</Pitfalls>
  <OutputFormat>RDF/XML</OutputFormat>
</OOPSRequest>"""

# Submit to OOPS! REST API
response = requests.post(
    "https://oops.linkeddata.es/rest",
    headers={"Content-Type": "application/xml"},
    data=xml_request.encode("utf-8")
)

# Print response
print(f"\nStatus Code: {response.status_code}")
print("\n--- OOPS! Response ---")
print(response.text)

