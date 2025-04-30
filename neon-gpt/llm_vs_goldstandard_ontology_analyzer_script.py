#!/usr/bin/env python3
"""
Ontology Analyzer and Comparator

This module provides tools for analyzing and comparing ontologies represented as TTL files.
It performs structural, lexical, and semantic analysis, generating comprehensive reports and visualizations.

Author: [Your Name]
License: [License Type]
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import numpy as np
from datetime import datetime
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import jellyfish
from matplotlib_venn import venn2
import nltk
import re
import warnings
import argparse

# Optional imports - the script will handle cases when these are not available
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False
    print("Warning: sentence_transformers not available. Semantic analysis will be limited.")

try:
    import Levenshtein
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False
    print("Warning: Levenshtein not available. Using alternative string similarity measures.")

# Suppress warnings
warnings.filterwarnings('ignore')

# Try downloading NLTK resources
try:
    nltk.download('wordnet', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('omw-1.4', quiet=True)
except:
    print("Warning: NLTK download failed. Some lexical features may be limited.")

# Visualization aesthetics configuration
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 16

# Color palette
COLORS = {
    'ont1': '#1f77b4',  # blue
    'ont2': '#2ca02c',  # green
    'overlap': '#9467bd',  # purple
    'highlight': '#d62728',  # red
    'background': '#f5f5f5'  # light gray
}


class OntologyAnalyzer:
    """
    Enhanced class for analyzing ontologies

    This class loads an ontology from a TTL file and analyzes its structure,
    extracting classes, properties, instances, and their relationships.
    
    Attributes:
        ttl_file_path (str): Path to the TTL file
        name (str): Name of the ontology
        graph (Graph): RDFLib graph containing the ontology
        prefixes (dict): Prefix mappings from the TTL file
        classes (list): List of class URIs
        properties (list): List of property URIs
        instances (list): List of instance URIs
        class_hierarchy (DataFrame): Hierarchical relationships between classes
        labels (dict): URI to label mappings
        comments (dict): URI to comment mappings
        entities (dict): Comprehensive information about entities
    """
    
    def __init__(self, ttl_file_path, name="Ontology"):
        """
        Initialize with a TTL file path
        
        Args:
            ttl_file_path (str): Path to the TTL file containing the ontology
            name (str, optional): Name to identify the ontology. Defaults to "Ontology".
        """
        self.ttl_file_path = ttl_file_path
        self.name = name
        self.graph = None
        self.prefixes = {}
        self.classes = []
        self.properties = []
        self.instances = []
        self.class_hierarchy = None
        self.labels = {}
        self.comments = {}
        self.entities = {}  # URI -> text and embedding info
        
        # Load the graph and extract basic components
        self.load_graph()
        self.extract_prefixes()
        self.extract_components()
        self.extract_text_annotations()
    
    def load_graph(self):
        """
        Load TTL file into RDFLib graph
        
        Loads the ontology from the specified TTL file into an RDFLib graph
        and reports the number of triples loaded.
        """
        print(f"Loading ontology from {self.ttl_file_path}")
        self.graph = Graph()
        try:
            self.graph.parse(self.ttl_file_path, format="ttl")
            print(f"Loaded {len(self.graph)} triples")
        except Exception as e:
            print(f"Error loading TTL file: {str(e)}")
    
    def extract_prefixes(self):
        """
        Extract prefix mappings from the TTL file
        
        Parses the prefix declarations in the TTL file and stores them
        for later use in shortening URIs.
        """
        with open(self.ttl_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('@prefix'):
                    try:
                        parts = line.split(' ', 2)
                        prefix = parts[1].rstrip(':')
                        uri = parts[2].strip()
                        if uri.startswith('<') and uri.endswith('> .'):
                            uri = uri[1:-3]  # Remove < > and the trailing dot
                            self.prefixes[uri] = prefix
                    except:
                        continue
    
    def get_shortened_uri(self, uri):
        """
        Convert a full URI to a shortened form using prefixes
        
        Args:
            uri (str): The full URI to shorten
            
        Returns:
            str: The shortened URI using prefixes if available,
                 or a truncated form of the original URI
        """
        if not isinstance(uri, str):
            uri = str(uri)
        
        for uri_base, prefix in self.prefixes.items():
            if uri.startswith(uri_base):
                return f"{prefix}:{uri[len(uri_base):]}"
        
        # If no prefix matches, return the original URI but truncate if too long
        if len(uri) > 50:
            return uri[:25] + "..." + uri[-22:]
        return uri
    
    def extract_components(self):
        """
        Extract basic ontology components
        
        Identifies classes, properties, and instances in the ontology,
        and extracts the class hierarchy structure.
        """
        # Extract classes
        self.classes = list(self.graph.subjects(RDF.type, RDFS.Class)) + list(self.graph.subjects(RDF.type, OWL.Class))
        
        # Extract properties
        self.properties = list(self.graph.subjects(RDF.type, RDF.Property)) + \
                         list(self.graph.subjects(RDF.type, OWL.ObjectProperty)) + \
                         list(self.graph.subjects(RDF.type, OWL.DatatypeProperty))
        
        # Extract subclass relations
        subclass_relations = [(str(s), str(o)) for s, o in self.graph.subject_objects(RDFS.subClassOf) 
                              if isinstance(s, URIRef) and isinstance(o, URIRef)]
        
        # Create hierarchy dataframe
        self.class_hierarchy = pd.DataFrame(subclass_relations, columns=['subclass', 'superclass'])
        
        # Extract instances
        self.instances = set()
        for s, o in self.graph.subject_objects(RDF.type):
            if o not in [RDFS.Class, OWL.Class, RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty]:
                self.instances.add(s)
    
    def extract_text_annotations(self):
        """
        Extract labels and comments for semantic analysis
        
        Collects rdfs:label and rdfs:comment annotations for entities
        to enable semantic comparison between ontologies.
        """
        # Extract rdfs:label
        for s, o in self.graph.subject_objects(RDFS.label):
            if isinstance(o, Literal):
                # Only include English labels or labels without language tag
                if o.language is None or o.language == 'en':
                    self.labels[str(s)] = str(o)
        
        # Extract rdfs:comment
        for s, o in self.graph.subject_objects(RDFS.comment):
            if isinstance(o, Literal):
                # Only include English comments or comments without language tag
                if o.language is None or o.language == 'en':
                    self.comments[str(s)] = str(o)
        
        # Prepare entities dictionary for semantic analysis
        for uri in set(list(self.labels.keys()) + list(self.comments.keys())):
            label = self.labels.get(uri, "")
            comment = self.comments.get(uri, "")
            
            # Determine entity type
            entity_type = "unknown"
            uri_ref = URIRef(uri)
            if uri_ref in self.classes:
                entity_type = "class"
            elif uri_ref in self.properties:
                entity_type = "property"
            elif uri_ref in self.instances:
                entity_type = "instance"
            
            # Extract local name
            local_name = self._extract_local_name(uri)
            
            self.entities[uri] = {
                'uri': uri,
                'local_name': local_name,
                'short_uri': self.get_shortened_uri(uri),
                'label': label,
                'comment': comment,
                'type': entity_type,
                'embedding': None,
                'combined_text': f"{label} {comment}".strip() if (label or comment) else local_name
            }
    
    def _extract_local_name(self, uri):
        """
        Extract the local name from a URI (the part after # or last / or :)
        
        Args:
            uri (str): The URI to extract the local name from
            
        Returns:
            str: The local name extracted from the URI
        """
        if not uri:
            return ""
        
        uri_str = str(uri)
        
        # Try to extract after #
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        
        # Try to extract after last /
        if '/' in uri_str:
            return uri_str.split('/')[-1]
        
        # Try to extract after :
        if ':' in uri_str:
            return uri_str.split(':')[-1]
        
        return uri_str
    
    def analyze_structure(self):
        """
        Generate structural statistics for the ontology
        
        Returns:
            dict: Dictionary containing metrics about the ontology structure
        """
        # Count basic components
        class_count = len(self.classes)
        property_count = len(self.properties)
        instance_count = len(self.instances)
        
        # Analyze property types
        object_properties = len(list(self.graph.subjects(RDF.type, OWL.ObjectProperty)))
        datatype_properties = len(list(self.graph.subjects(RDF.type, OWL.DatatypeProperty)))
        annotation_properties = len(list(self.graph.subjects(RDF.type, OWL.AnnotationProperty)))
        
        # Count axioms
        subclass_relations = len(self.class_hierarchy)
        
        # Calculate hierarchy depth
        hierarchy_depths = []
        for cls in self.classes:
            depth = 0
            current = cls
            visited = set()  # Prevent cycles
            
            while True:
                if current in visited:
                    break
                visited.add(current)
                
                super_classes = list(self.graph.objects(current, RDFS.subClassOf))
                if not super_classes or not isinstance(super_classes[0], URIRef):
                    break
                current = super_classes[0]
                depth += 1
            
            hierarchy_depths.append(depth)
        
        max_depth = max(hierarchy_depths) if hierarchy_depths else 0
        avg_depth = np.mean(hierarchy_depths) if hierarchy_depths else 0
        
        # Count domain and range assertions
        domain_assertions = sum(1 for _ in self.graph.subject_objects(RDFS.domain))
        range_assertions = sum(1 for _ in self.graph.subject_objects(RDFS.range))
        
        # Count disjoint assertions
        disjoint_assertions = sum(1 for _ in self.graph.subject_objects(OWL.disjointWith))
        
        # Analyze the presence of labels and comments
        entities_with_labels = len(self.labels)
        entities_with_comments = len(self.comments)
        
        # Compile all metrics into a dictionary
        metrics = {
            "total_triples": len(self.graph),
            "class_count": class_count,
            "property_count": property_count,
            "object_properties": object_properties,
            "datatype_properties": datatype_properties,
            "annotation_properties": annotation_properties,
            "instance_count": instance_count,
            "subclass_relations": subclass_relations,
            "avg_hierarchy_depth": avg_depth,
            "max_hierarchy_depth": max_depth,
            "domain_assertions": domain_assertions,
            "range_assertions": range_assertions,
            "disjoint_assertions": disjoint_assertions,
            "entities_with_labels": entities_with_labels,
            "entities_with_comments": entities_with_comments
        }
        
        return metrics
    
    def generate_class_hierarchy_graph(self):
        """
        Generate a NetworkX graph representation of the class hierarchy
        
        Returns:
            NetworkX.DiGraph: Directed graph representing the class hierarchy
        """
        G = nx.DiGraph()
        
        for _, row in self.class_hierarchy.iterrows():
            subclass = self.get_shortened_uri(row['subclass'])
            superclass = self.get_shortened_uri(row['superclass'])
            G.add_edge(subclass, superclass)
        
        return G
    
    def get_entity_names(self):
        """
        Get clean names of all entities for lexical analysis
        
        Returns:
            dict: Dictionary mapping entity URIs to their local names
        """
        entity_names = {}
        
        # Process classes
        for cls in self.classes:
            short_uri = self.get_shortened_uri(str(cls))
            entity_names[str(cls)] = short_uri.split(':')[-1] if ':' in short_uri else short_uri
        
        # Process properties
        for prop in self.properties:
            short_uri = self.get_shortened_uri(str(prop))
            entity_names[str(prop)] = short_uri.split(':')[-1] if ':' in short_uri else short_uri
        
        return entity_names
    
    def create_embeddings(self, model):
        """
        Create embeddings for all entities with text annotations
        
        Args:
            model: Sentence transformer model for creating embeddings
        """
        print(f"Creating embeddings for {self.name}...")
        
        # Prepare entities with text
        entities_with_text = [(uri, entity) for uri, entity in self.entities.items() 
                             if entity['combined_text']]
        
        if not entities_with_text:
            print(f"Warning: No entities with text found in {self.name}")
            return
        
        # Generate embeddings in batches to avoid memory issues
        batch_size = 128
        texts = [entity['combined_text'] for _, entity in entities_with_text]
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_embeddings = model.encode(batch_texts, show_progress_bar=False)
            
            # Assign embeddings to entities
            for j, embedding in enumerate(batch_embeddings):
                if i + j < len(entities_with_text):
                    uri, _ = entities_with_text[i + j]
                    self.entities[uri]['embedding'] = embedding
        
        entities_with_embeddings = sum(1 for e in self.entities.values() if e['embedding'] is not None)
        print(f"Created embeddings for {entities_with_embeddings} entities in {self.name}")


class OntologyComparator:
    """
    Enhanced class for comprehensive ontology comparison
    
    This class compares two ontologies across structural, lexical, and semantic dimensions,
    generating visualizations and reports of the comparison results.
    
    Attributes:
        ont1 (OntologyAnalyzer): First ontology to compare
        ont2 (OntologyAnalyzer): Second ontology to compare
        output_dir (str): Directory where comparison results are saved
        sentence_model: Model for generating sentence embeddings
        similarity_scores (dict): Cached similarity scores between entities
    """
    
    def __init__(self, ontology1, ontology2):
        """
        Initialize with two OntologyAnalyzer objects
        
        Args:
            ontology1 (OntologyAnalyzer): First ontology to compare
            ontology2 (OntologyAnalyzer): Second ontology to compare
        """
        self.ont1 = ontology1
        self.ont2 = ontology2
        self.output_dir = None
        self.sentence_model = None  # Will hold the sentence transformer model
        self.similarity_scores = {}  # Will hold semantic similarity scores
        
    def set_output_directory(self, output_dir):
        """
        Set and create the output directory for results
        
        Args:
            output_dir (str): Path to the directory where results will be saved
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Create subdirectories for better organization
        os.makedirs(os.path.join(output_dir, "structural"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "lexical"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "semantic"), exist_ok=True)
    
    def compare_structure(self):
        """
        Compare structural aspects of the two ontologies
        
        Analyzes and compares metrics like class counts, property types, 
        hierarchy depth, etc. between the two ontologies.
        
        Returns:
            dict: Comparison metrics between the two ontologies
        """
        print("Performing structural comparison...")
        
        # Get metrics for both ontologies
        metrics1 = self.ont1.analyze_structure()
        metrics2 = self.ont2.analyze_structure()
        
        # Calculate differences and ratios
        comparison = {}
        for key in metrics1:
            if isinstance(metrics1[key], dict):
                comparison[key] = {
                    "ontology1": metrics1[key],
                    "ontology2": metrics2[key]
                }
            else:
                comparison[key] = {
                    "ontology1": metrics1[key],
                    "ontology2": metrics2[key],
                    "difference": metrics2[key] - metrics1[key],
                    "ratio": metrics2[key] / metrics1[key] if metrics1[key] != 0 else float('inf')
                }
        
        # Create visuals
        self._create_structural_bar_chart(metrics1, metrics2)
        self._create_hierarchy_depth_distribution(metrics1, metrics2)
        self._create_property_usage_comparison()
        self._create_class_hierarchy_visualization()
        
        # Save numerical results
        self._save_structural_metrics_table(comparison)
        
        return comparison
    
    def _create_structural_bar_chart(self, metrics1, metrics2):
        """
        Create a bar chart comparing key structural metrics
        
        Args:
            metrics1 (dict): Metrics from the first ontology
            metrics2 (dict): Metrics from the second ontology
        """
        # Select key metrics for visualization
        metrics_to_plot = [
            'class_count', 'property_count', 'object_properties', 
            'datatype_properties', 'instance_count', 'subclass_relations'
        ]
        
        labels = [
            'Classes', 'All Properties', 'Object Props', 
            'Datatype Props', 'Instances', 'Subclass Relations'
        ]
        
        # Prepare data
        ont1_values = [metrics1[m] for m in metrics_to_plot]
        ont2_values = [metrics2[m] for m in metrics_to_plot]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Set position of bars on X axis
        x = np.arange(len(labels))
        width = 0.35
        
        # Create bars
        ax.bar(x - width/2, ont1_values, width, label=f'{self.ont1.name}', color=COLORS['ont1'])
        ax.bar(x + width/2, ont2_values, width, label=f'{self.ont2.name}', color=COLORS['ont2'])
        
        # Add labels and title
        ax.set_ylabel('Count', fontweight='bold')
        ax.set_title('Structural Metrics Comparison', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha='right')
        ax.legend()
        
        # Add value labels on top of each bar
        for i, v in enumerate(ont1_values):
            ax.text(i - width/2, v + 1, str(v), ha='center', va='bottom', fontsize=9)
        
        for i, v in enumerate(ont2_values):
            ax.text(i + width/2, v + 1, str(v), ha='center', va='bottom', fontsize=9)
        
        # Set background color
        ax.set_facecolor(COLORS['background'])
        fig.patch.set_facecolor('white')
        
        # Add grid for better readability
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Set y limit to add some space above the highest bar
        ax.set_ylim(0, max(max(ont1_values), max(ont2_values)) * 1.15)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "structural", "basic_metrics_comparison.png"), dpi=300)
        plt.close()
    
    def _create_hierarchy_depth_distribution(self, metrics1, metrics2):
        """
        Create a visualization of hierarchy depth distribution
        
        Args:
            metrics1 (dict): Metrics from the first ontology
            metrics2 (dict): Metrics from the second ontology
        """
        # Create depth comparison chart showing max and average depths
        metrics_to_plot = ['avg_hierarchy_depth', 'max_hierarchy_depth']
        labels = ['Average Depth', 'Maximum Depth']
        
        ont1_values = [metrics1[m] for m in metrics_to_plot]
        ont2_values = [metrics2[m] for m in metrics_to_plot]
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        x = np.arange(len(labels))
        width = 0.35
        
        ax.bar(x - width/2, ont1_values, width, label=f'{self.ont1.name}', color=COLORS['ont1'])
        ax.bar(x + width/2, ont2_values, width, label=f'{self.ont2.name}', color=COLORS['ont2'])
        
        ax.set_ylabel('Depth', fontweight='bold')
        ax.set_title('Class Hierarchy Depth Comparison', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.legend()
        
        # Add value labels
        for i, v in enumerate(ont1_values):
            ax.text(i - width/2, v + 0.1, f"{v:.2f}", ha='center', va='bottom', fontsize=9)
        
        for i, v in enumerate(ont2_values):
            ax.text(i + width/2, v + 0.1, f"{v:.2f}", ha='center', va='bottom', fontsize=9)
        
        ax.set_facecolor(COLORS['background'])
        fig.patch.set_facecolor('white')
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "structural", "hierarchy_depth_comparison.png"), dpi=300)
        plt.close()
    
    def _create_property_usage_comparison(self):
        """
        Create a visualization comparing property types
        
        Generates pie charts showing the distribution of property types
        in each ontology.
        """
        # Prepare data for property type comparison - ensure all values are non-negative
        property_types_ont1 = {
            'Object': max(0, sum(1 for _ in self.ont1.graph.subjects(RDF.type, OWL.ObjectProperty))),
            'Datatype': max(0, sum(1 for _ in self.ont1.graph.subjects(RDF.type, OWL.DatatypeProperty))),
            'Annotation': max(0, sum(1 for _ in self.ont1.graph.subjects(RDF.type, OWL.AnnotationProperty))),
        }
        
        # Calculate 'Other' separately to ensure it's non-negative
        total_properties = max(0, len(self.ont1.properties))
        known_properties = sum(property_types_ont1.values())
        property_types_ont1['Other'] = max(0, total_properties - known_properties)
        
        property_types_ont2 = {
            'Object': max(0, sum(1 for _ in self.ont2.graph.subjects(RDF.type, OWL.ObjectProperty))),
            'Datatype': max(0, sum(1 for _ in self.ont2.graph.subjects(RDF.type, OWL.DatatypeProperty))),
            'Annotation': max(0, sum(1 for _ in self.ont2.graph.subjects(RDF.type, OWL.AnnotationProperty))),
        }
        
        # Calculate 'Other' separately to ensure it's non-negative
        total_properties2 = max(0, len(self.ont2.properties))
        known_properties2 = sum(property_types_ont2.values())
        property_types_ont2['Other'] = max(0, total_properties2 - known_properties2)
        
        # Check if we have any properties to display
        if sum(property_types_ont1.values()) == 0 and sum(property_types_ont2.values()) == 0:
            # No properties to show, create a simple bar chart instead
            plt.figure(figsize=(10, 6))
            plt.title('No property types found in either ontology', fontweight='bold')
            plt.text(0.5, 0.5, 'No properties with type information available', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=plt.gca().transAxes, fontsize=14)
            plt.axis('off')
            plt.savefig(os.path.join(self.output_dir, "structural", "property_types_comparison.png"), dpi=300)
            plt.close()
            return
            
        # For ontologies with zero properties of some types, we need to handle that case
        # by adding a small positive value to avoid ValueError in pie chart
        for prop_type in property_types_ont1:
            if property_types_ont1[prop_type] == 0:
                property_types_ont1[prop_type] = 0.0001  # Very small non-zero value
                
        for prop_type in property_types_ont2:
            if property_types_ont2[prop_type] == 0:
                property_types_ont2[prop_type] = 0.0001  # Very small non-zero value
        
        # Create pie charts for property types
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
        
        # Custom colors
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        
        # Plot for ontology 1
        wedges1, texts1, autotexts1 = ax1.pie(
            property_types_ont1.values(), 
            labels=None,  # We'll add a legend instead
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            wedgeprops={'edgecolor': 'w', 'linewidth': 1}
        )
        
        # Plot for ontology 2
        wedges2, texts2, autotexts2 = ax2.pie(
            property_types_ont2.values(), 
            labels=None,  # We'll add a legend instead
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            wedgeprops={'edgecolor': 'w', 'linewidth': 1}
        )
        
        # Set font properties for percentages
        for autotext in autotexts1 + autotexts2:
            autotext.set_fontsize(9)
            autotext.set_fontweight('bold')
        
        # Add titles
        ax1.set_title(f'{self.ont1.name} Property Types', fontweight='bold')
        ax2.set_title(f'{self.ont2.name} Property Types', fontweight='bold')
        
        # Add legend
        fig.legend(
            wedges1, 
            property_types_ont1.keys(), 
            title="Property Types", 
            loc="center", 
            bbox_to_anchor=(0.5, 0)
        )
        
        # Equal aspect ratio ensures pie is circular
        ax1.set_aspect('equal')
        ax2.set_aspect('equal')
        
        fig.patch.set_facecolor('white')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "structural", "property_types_comparison.png"), dpi=300, bbox_inches='tight')
        plt.close()
    
    def _create_class_hierarchy_visualization(self):
        """
        Create a visualization of class hierarchies
        
        Generates a graph visualization showing the top levels of
        the class hierarchies in both ontologies.
        """
        # Generate hierarchy graphs
        G1 = self.ont1.generate_class_hierarchy_graph()
        G2 = self.ont2.generate_class_hierarchy_graph()
        
        # Extract top levels of hierarchies (limited to make visualization readable)
        # Find root nodes (no incoming edges)
        roots1 = [node for node in G1.nodes() if G1.in_degree(node) == 0]
        roots2 = [node for node in G2.nodes() if G2.in_degree(node) == 0]
        
        # Create subgraphs with limited depth
        depth_limit = 2  # Limit depth to make visualization readable
        
        # Function to extract nodes up to a certain depth
        def get_nodes_up_to_depth(G, roots, depth_limit):
            nodes = set(roots)
            for _ in range(depth_limit):
                descendants = set()
                for node in nodes:
                    descendants.update(G.predecessors(node))
                nodes.update(descendants)
            return nodes
        
        # Get all nodes within depth limit
        included_nodes1 = get_nodes_up_to_depth(G1, roots1, depth_limit)
        included_nodes2 = get_nodes_up_to_depth(G2, roots2, depth_limit)
        
        # Create subgraphs
        subgraph1 = G1.subgraph(included_nodes1)
        subgraph2 = G2.subgraph(included_nodes2)
        
        # Create visualization
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 10))
        
        # Draw first ontology
        pos1 = nx.spring_layout(subgraph1, seed=42, k=0.5)
        nx.draw_networkx_nodes(subgraph1, pos1, ax=ax1, node_size=300, node_color=COLORS['ont1'], alpha=0.8)
        nx.draw_networkx_edges(subgraph1, pos1, ax=ax1, arrows=True, arrowstyle='->', arrowsize=15)
        
        # Add labels with smaller font and white background for better readability
        labels1 = {}
        for node in subgraph1.nodes():
            # Get shorter name for label
            if ':' in node:
                labels1[node] = node.split(':')[-1]
            else:
                labels1[node] = node
        
        nx.draw_networkx_labels(
            subgraph1, pos1, labels=labels1, ax=ax1, 
            font_size=8, font_weight='bold',
            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2')
        )
        
        # Draw second ontology
        pos2 = nx.spring_layout(subgraph2, seed=42, k=0.5)
        nx.draw_networkx_nodes(subgraph2, pos2, ax=ax2, node_size=300, node_color=COLORS['ont2'], alpha=0.8)
        nx.draw_networkx_edges(subgraph2, pos2, ax=ax2, arrows=True, arrowstyle='->', arrowsize=15)
        
        # Add labels with smaller font
        labels2 = {}
        for node in subgraph2.nodes():
            if ':' in node:
                labels2[node] = node.split(':')[-1]
            else:
                labels2[node] = node
        
        nx.draw_networkx_labels(
            subgraph2, pos2, labels=labels2, ax=ax2, 
            font_size=8, font_weight='bold',
            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2')
        )
        
        # Set titles
        ax1.set_title(f'{self.ont1.name} Class Hierarchy (Top {depth_limit+1} Levels)', fontweight='bold')
        ax2.set_title(f'{self.ont2.name} Class Hierarchy (Top {depth_limit+1} Levels)', fontweight='bold')
        
        # Remove axes
        ax1.axis('off')
        ax2.axis('off')
        
        # Set background
        ax1.set_facecolor('white')
        ax2.set_facecolor('white')
        fig.patch.set_facecolor('white')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "structural", "class_hierarchy_visualization.png"), dpi=300, bbox_inches='tight')
        plt.close()
    
    def _save_structural_metrics_table(self, comparison):
        """
        Save structural metrics comparison to files
        
        Args:
            comparison (dict): Comparison metrics between the two ontologies
        """
        # Create a table of all metrics
        table_data = []
        for metric, values in comparison.items():
            if isinstance(values, dict) and 'ontology1' in values and 'ontology2' in values:
                # Only include numerical metrics with ontology1 and ontology2 keys
                if isinstance(values['ontology1'], (int, float)) and isinstance(values['ontology2'], (int, float)):
                    row = {
                        'Metric': metric,
                        self.ont1.name: values['ontology1'],
                        self.ont2.name: values['ontology2'],
                        'Difference': values.get('difference', 'N/A'),
                        'Ratio': values.get('ratio', 'N/A')
                    }
                    table_data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(table_data)
        
        # Save to CSV
        df.to_csv(os.path.join(self.output_dir, "structural", "metrics_comparison.csv"), index=False)
        
        # Save to text file for the report
        with open(os.path.join(self.output_dir, "structural", "metrics_comparison.txt"), 'w') as f:
            f.write("# Structural Metrics Comparison\n\n")
            f.write(f"{'Metric':<25} | {self.ont1.name:<15} | {self.ont2.name:<15} | {'Difference':<15} | {'Ratio':<10}\n")
            f.write("-" * 80 + "\n")
            
            for row in table_data:
                metric = row['Metric']
                val1 = row[self.ont1.name]
                val2 = row[self.ont2.name]
                diff = row['Difference']
                ratio = row['Ratio']
                
                if isinstance(val1, float):
                    val1 = f"{val1:.2f}"
                if isinstance(val2, float):
                    val2 = f"{val2:.2f}"
                if isinstance(diff, float):
                    diff = f"{diff:.2f}"
                if isinstance(ratio, float):
                    ratio = f"{ratio:.2f}"
                
                f.write(f"{metric:<25} | {val1:<15} | {val2:<15} | {diff:<15} | {ratio:<10}\n")

    def load_embedding_model(self):
        """
        Load embedding model for semantic similarity
        
        Returns:
            bool: True if the model was loaded successfully, False otherwise
        """
        print("Loading embedding model...")
        if not SENTENCE_TRANSFORMER_AVAILABLE:
            print("sentence_transformers package not available, semantic analysis will be limited")
            return False
            
        try:
            # Load sentence transformer model for semantic text similarity
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Sentence transformer model loaded successfully")
            return True
        except Exception as e:
            print(f"Error loading embedding model: {str(e)}")
            return False
    
    def prepare_semantic_analysis(self):
        """
        Prepare for semantic analysis by loading model and creating embeddings
        
        Returns:
            bool: True if preparation was successful, False otherwise
        """
        if not self.load_embedding_model():
            return False
            
        # Create embeddings for both ontologies
        self.ont1.create_embeddings(self.sentence_model)
        self.ont2.create_embeddings(self.sentence_model)
        
        return True
    
    def calculate_semantic_similarity(self, entity1, entity2):
        """
        Calculate semantic similarity between two entities based on their embeddings
        
        Args:
            entity1 (dict): First entity with embedding
            entity2 (dict): Second entity with embedding
            
        Returns:
            float: Cosine similarity between the entities' embeddings, in [0, 1]
        """
        # If either entity has no embedding, return 0
        if (entity1['embedding'] is None or entity2['embedding'] is None):
            return 0.0
        
        # Calculate cosine similarity between embeddings
        sim = cosine_similarity([entity1['embedding']], [entity2['embedding']])[0][0]
        return max(0.0, min(1.0, sim))  # Ensure value is between 0 and 1
    
    def compare_semantic(self):
        """
        Compare semantic content using text annotations (labels and comments)
        
        Analyzes and compares the semantic similarity between entities in the two ontologies
        based on their text annotations.
        
        Returns:
            dict: Results of the semantic comparison
        """
        print("Performing semantic comparison...")
        
        if not self.sentence_model:
            success = self.prepare_semantic_analysis()
            if not success:
                print("Could not load embedding model, semantic analysis will be limited")
                self._create_semantic_fallback_visualization()
                return {
                    'error': "Failed to load embedding model",
                    'common_entities': len(set(self.ont1.labels.keys()).intersection(set(self.ont2.labels.keys())))
                }
        
        try:
            # Extract entities with text content
            entities1 = {uri: entity for uri, entity in self.ont1.entities.items() 
                       if entity['combined_text'] and entity['embedding'] is not None}
            entities2 = {uri: entity for uri, entity in self.ont2.entities.items() 
                       if entity['combined_text'] and entity['embedding'] is not None}
            
            # Calculate overlapping entities (by URI)
            common_uris = set(entities1.keys()).intersection(set(entities2.keys()))
            
            # Compare text annotations for common entities
            common_entity_similarities = []
            
            for uri in common_uris:
                sim = self.calculate_semantic_similarity(entities1[uri], entities2[uri])
                common_entity_similarities.append((uri, sim))
            
            # Sort by similarity
            common_entity_similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Cross-ontology semantic similarity (for differently named entities)
            cross_similarities = []
            
            # Find semantically similar entities across ontologies
            # This is potentially O(n²), so we'll sample or limit the comparisons
            # for very large ontologies
            max_comparisons = 10000  # Set a reasonable limit
            
            # Filter by entity type for more meaningful comparisons
            for entity_type in ['class', 'property']:
                # Get entities of this type
                entities1_of_type = {uri: entity for uri, entity in entities1.items() 
                                    if entity['type'] == entity_type}
                entities2_of_type = {uri: entity for uri, entity in entities2.items() 
                                    if entity['type'] == entity_type}
                
                # Skip if either ontology has no entities of this type
                if not entities1_of_type or not entities2_of_type:
                    continue
                
                # If the product is too large, take samples
                if len(entities1_of_type) * len(entities2_of_type) > max_comparisons:
                    # Limit each set
                    limit1 = int(np.sqrt(max_comparisons))
                    limit2 = max_comparisons // limit1
                    
                    # Convert to lists and limit size
                    entities1_list = list(entities1_of_type.items())[:limit1]
                    entities2_list = list(entities2_of_type.items())[:limit2]
                else:
                    entities1_list = list(entities1_of_type.items())
                    entities2_list = list(entities2_of_type.items())
                
                # Compare all pairs in our limited sets
                for (uri1, entity1), (uri2, entity2) in [(a, b) for a in entities1_list for b in entities2_list]:
                    # Skip common entities as they're already compared
                    if uri1 in common_uris and uri2 in common_uris:
                        continue
                    
                    # Calculate similarity
                    sim = self.calculate_semantic_similarity(entity1, entity2)
                    
                    # Only keep relatively high similarities
                    if sim > 0.5:
                        cross_similarities.append((uri1, uri2, sim))
            
            # Sort by similarity
            cross_similarities.sort(key=lambda x: x[2], reverse=True)
            
            # Keep top N
            cross_similarities = cross_similarities[:20]
            
            # Create visualizations
            self._create_semantic_visualizations(common_entity_similarities, cross_similarities)
            
            # Save results
            self._save_semantic_results(common_entity_similarities, cross_similarities)
            
            return {
                'common_entities': len(common_uris),
                'entities_with_text_ont1': len(entities1),
                'entities_with_text_ont2': len(entities2),
                'common_similarities': common_entity_similarities,
                'cross_similarities': cross_similarities
            }
        
        except Exception as e:
            print(f"Error in semantic comparison: {str(e)}")
            # Create a fallback visualization
            self._create_semantic_fallback_visualization()
            
            return {
                'error': str(e),
                'common_entities': len(set(self.ont1.labels.keys()).intersection(set(self.ont2.labels.keys())))
            }
    
    def _create_semantic_visualizations(self, common_similarities, cross_similarities):
        """
        Create visualizations for semantic comparison
        
        Args:
            common_similarities (list): List of (uri, similarity) tuples for common entities
            cross_similarities (list): List of (uri1, uri2, similarity) tuples for cross-ontology comparisons
        """
        # Distribution of semantic similarities for common entities
        if common_similarities:
            similarities = [s[1] for s in common_similarities]
            
            plt.figure(figsize=(10, 6))
            plt.hist(similarities, bins=20, color=COLORS['overlap'], alpha=0.7)
            plt.axvline(np.mean(similarities), color='red', linestyle='dashed', 
                      linewidth=1, label=f'Mean: {np.mean(similarities):.4f}')
            
            plt.title('Distribution of Semantic Similarities for Common Entities', fontweight='bold')
            plt.xlabel('Semantic Similarity')
            plt.ylabel('Frequency')
            plt.legend()
            
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            plt.gca().set_facecolor(COLORS['background'])
            plt.gcf().patch.set_facecolor('white')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, "semantic", "common_entity_similarity_distribution.png"), dpi=300)
            plt.close()
            
            # Bar chart of top and bottom common entity similarities
            # Top 10
            top_n = min(10, len(common_similarities))
            top_entities = [(self.ont1.get_shortened_uri(e), s) for e, s in common_similarities[:top_n]]
            
            plt.figure(figsize=(12, 6))
            bars = plt.barh([t[0] for t in top_entities][::-1], [t[1] for t in top_entities][::-1], color=COLORS['overlap'])
            
            plt.title('Top 10 Entities with Highest Semantic Similarity', fontweight='bold')
            plt.xlabel('Semantic Similarity')
            plt.xlim(0, 1.05)
            
            # Add value labels
            for i, v in enumerate([t[1] for t in top_entities][::-1]):
                plt.text(v + 0.02, i, f"{v:.3f}", va='center')
            
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            plt.gca().set_facecolor(COLORS['background'])
            plt.gcf().patch.set_facecolor('white')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, "semantic", "top_common_entity_similarities.png"), dpi=300)
            plt.close()
            
            # Bottom 10
            bottom_n = min(10, len(common_similarities))
            bottom_entities = [(self.ont1.get_shortened_uri(e), s) for e, s in common_similarities[-bottom_n:]]
            
            plt.figure(figsize=(12, 6))
            bars = plt.barh([t[0] for t in bottom_entities][::-1], [t[1] for t in bottom_entities][::-1], color='lightcoral')
            
            plt.title('Bottom 10 Entities with Lowest Semantic Similarity', fontweight='bold')
            plt.xlabel('Semantic Similarity')
            plt.xlim(0, 1.05)
            
            # Add value labels
            for i, v in enumerate([t[1] for t in bottom_entities][::-1]):
                plt.text(v + 0.02, i, f"{v:.3f}", va='center')
            
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            plt.gca().set_facecolor(COLORS['background'])
            plt.gcf().patch.set_facecolor('white')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, "semantic", "bottom_common_entity_similarities.png"), dpi=300)
            plt.close()
        
        # Visualize cross-ontology semantic similarities
        if cross_similarities:
            top_n = min(10, len(cross_similarities))
            
            plt.figure(figsize=(12, 6))
            
            pairs = [f"{self.ont1.get_shortened_uri(e1)} - {self.ont2.get_shortened_uri(e2)}" for e1, e2, _ in cross_similarities[:top_n]]
            similarities = [s for _, _, s in cross_similarities[:top_n]]
            
            bars = plt.barh(pairs[::-1], similarities[::-1], color=COLORS['ont1'])
            
            plt.title('Top Cross-Ontology Semantic Similarities', fontweight='bold')
            plt.xlabel('Semantic Similarity')
            plt.xlim(0, 1.05)
            
            # Add value labels
            for i, v in enumerate(similarities[::-1]):
                plt.text(v + 0.02, i, f"{v:.3f}", va='center')
            
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            plt.gca().set_facecolor(COLORS['background'])
            plt.gcf().patch.set_facecolor('white')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, "semantic", "cross_ontology_similarities.png"), dpi=300)
            plt.close()
            
        # Create semantic similarity heatmap for top entities
        self._create_semantic_similarity_heatmap(cross_similarities)
    
    def _create_semantic_similarity_heatmap(self, cross_similarities, max_entities=15):
        """
        Create a heatmap of semantic similarities between top entities
        
        Args:
            cross_similarities (list): List of (uri1, uri2, similarity) tuples
            max_entities (int, optional): Maximum number of entities to include. Defaults to 15.
        """
        if not cross_similarities or len(cross_similarities) < 3:
            return
            
        # Get top entities from each ontology based on cross-similarity scores
        top_entities1 = set()
        top_entities2 = set()
        
        for e1, e2, _ in cross_similarities[:max_entities]:
            top_entities1.add(e1)
            top_entities2.add(e2)
            
            if len(top_entities1) >= max_entities or len(top_entities2) >= max_entities:
                break
        
        # Convert to lists for indexing
        entities1 = list(top_entities1)
        entities2 = list(top_entities2)
        
        # Create similarity matrix
        similarity_matrix = np.zeros((len(entities1), len(entities2)))
        
        # Fill similarity matrix
        for e1, e2, sim in cross_similarities:
            if e1 in entities1 and e2 in entities2:
                i = entities1.index(e1)
                j = entities2.index(e2)
                similarity_matrix[i, j] = sim
        
        # Create heatmap
        plt.figure(figsize=(12, 10))
        
        # Create mask for values below threshold
        min_threshold = 0.45  # Minimum threshold for visualization
        mask = similarity_matrix < min_threshold
        
        # Create heatmap with mask
        ax = sns.heatmap(
            similarity_matrix,
            xticklabels=[self.ont2.get_shortened_uri(e) for e in entities2],
            yticklabels=[self.ont1.get_shortened_uri(e) for e in entities1],
            cmap='YlOrRd',
            mask=mask,
            annot=True,
            fmt='.2f',
            vmin=min_threshold,
            vmax=1.0,
            linewidths=0.5
        )
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        
        plt.title('Cross-Ontology Semantic Similarity Heatmap', fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "semantic", "cross_similarity_heatmap.png"), dpi=300, bbox_inches='tight')
        plt.close()
    
    def _create_semantic_fallback_visualization(self):
        """
        Create a fallback visualization when semantic analysis fails
        
        Generates a basic visualization of text annotation coverage when
        the full semantic analysis is not possible.
        """
        # Create simple bar chart of text annotation coverage
        labels1_count = len(self.ont1.labels)
        comments1_count = len(self.ont1.comments)
        labels2_count = len(self.ont2.labels)
        comments2_count = len(self.ont2.comments)
        
        plt.figure(figsize=(10, 6))
        width = 0.35
        
        x = np.arange(2)
        plt.bar(x - width/2, [labels1_count, comments1_count], width, label=self.ont1.name, color=COLORS['ont1'])
        plt.bar(x + width/2, [labels2_count, comments2_count], width, label=self.ont2.name, color=COLORS['ont2'])
        
        plt.title('Text Annotation Coverage', fontweight='bold')
        plt.xticks(x, ['Labels', 'Comments'])
        plt.ylabel('Count')
        plt.legend()
        
        # Add value labels
        for i, v in enumerate([labels1_count, comments1_count]):
            plt.text(i - width/2, v + 1, str(v), ha='center')
        
        for i, v in enumerate([labels2_count, comments2_count]):
            plt.text(i + width/2, v + 1, str(v), ha='center')
        
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.gca().set_facecolor(COLORS['background'])
        plt.gcf().patch.set_facecolor('white')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "semantic", "text_annotation_coverage.png"), dpi=300)
        plt.close()

    def compare_lexical(self):
        """
        Compare lexical features of the two ontologies
        
        Analyzes naming patterns and similarities between entity names
        in the two ontologies.
        
        Returns:
            dict: Results of the lexical comparison
        """
        print("Performing lexical comparison...")
        
        # Get entity names from both ontologies
        names1 = self.ont1.get_entity_names()
        names2 = self.ont2.get_entity_names()
        
        # Calculate overlap statistics
        names1_set = set(names1.values())
        names2_set = set(names2.values())
        
        exact_matches = names1_set.intersection(names2_set)
        only_in_ont1 = names1_set - names2_set
        only_in_ont2 = names2_set - names1_set
        
        # Create Venn diagram for exact name matches
        plt.figure(figsize=(10, 6))
        venn2(
            subsets=(len(only_in_ont1), len(only_in_ont2), len(exact_matches)),
            set_labels=(f'{self.ont1.name} Entities', f'{self.ont2.name} Entities'),
            set_colors=(COLORS['ont1'], COLORS['ont2'])
        )
        plt.title('Entity Name Overlap Between Ontologies', fontweight='bold')
        plt.savefig(os.path.join(self.output_dir, "lexical", "name_overlap_venn.png"), dpi=300)
        plt.close()
        
        # Calculate string similarities for non-exact matches
        # This helps identify similar but not identical names
        name_similarities = []
        
        # Convert values to lists for easier indexing
        names1_values = list(names1.values())
        names2_values = list(names2.values())
        
        # Only consider names not exactly matching
        for name1 in names1_values:
            if name1 not in exact_matches:
                for name2 in names2_values:
                    if name2 not in exact_matches:
                        # Calculate Jaro-Winkler similarity (good for short strings like names)
                        similarity = jellyfish.jaro_winkler_similarity(name1.lower(), name2.lower())
                        if similarity > 0.8:  # Only keep high-similarity pairs
                            name_similarities.append((name1, name2, similarity))
        
        # Sort by similarity
        name_similarities.sort(key=lambda x: x[2], reverse=True)
        
        # Create heatmap for top similar names
        if name_similarities:
            # Take top N for visualization
            top_n = min(15, len(name_similarities))
            top_similarities = name_similarities[:top_n]
            
            # Create unique name lists
            unique_names1 = []
            unique_names2 = []
            for n1, n2, _ in top_similarities:
                if n1 not in unique_names1:
                    unique_names1.append(n1)
                if n2 not in unique_names2:
                    unique_names2.append(n2)
            
            # Create similarity matrix for heatmap
            similarity_matrix = np.zeros((len(unique_names1), len(unique_names2)))
            
            for n1, n2, sim in top_similarities:
                if n1 in unique_names1 and n2 in unique_names2:
                    i = unique_names1.index(n1)
                    j = unique_names2.index(n2)
                    similarity_matrix[i, j] = sim
            
            # Create heatmap
            plt.figure(figsize=(14, 10))
            ax = sns.heatmap(
                similarity_matrix, 
                annot=True, 
                fmt=".2f", 
                cmap="YlGnBu",
                xticklabels=unique_names2, 
                yticklabels=unique_names1,
                linewidths=0.5
            )
            
            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            
            # Set title and labels
            plt.title('Lexical Similarity Between Entity Names', fontweight='bold')
            plt.tight_layout()
            
            plt.savefig(os.path.join(self.output_dir, "lexical", "name_similarity_heatmap.png"), dpi=300, bbox_inches='tight')
            plt.close()
        
        # Create bar chart of top string similarity matches
        if name_similarities:
            top_n = min(10, len(name_similarities))
            top_pairs = name_similarities[:top_n]
            
            pair_labels = [f"{p[0]} - {p[1]}" for p in top_pairs]
            pair_values = [p[2] for p in top_pairs]
            
            plt.figure(figsize=(12, 6))
            bars = plt.barh(range(len(pair_labels)), pair_values, color=COLORS['ont1'])
            
            # Highlight the highest similarity
            max_idx = pair_values.index(max(pair_values))
            bars[max_idx].set_color(COLORS['highlight'])
            
            plt.yticks(range(len(pair_labels)), pair_labels)
            plt.xlim(0.8, 1.0)  # Typically similarities are in this range
            plt.xlabel('Jaro-Winkler Similarity')
            plt.title('Top Similar Entity Names Between Ontologies', fontweight='bold')
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            
            # Set background
            plt.gca().set_facecolor(COLORS['background'])
            plt.gcf().patch.set_facecolor('white')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, "lexical", "top_name_similarities.png"), dpi=300)
            plt.close()
        
        # Save lexical comparison results
        self._save_lexical_results(exact_matches, only_in_ont1, only_in_ont2, name_similarities)
        
        return {
            'exact_matches': len(exact_matches),
            'only_in_ont1': len(only_in_ont1),
            'only_in_ont2': len(only_in_ont2),
            'similar_pairs': name_similarities[:20] if name_similarities else []
        }
    
    def _save_lexical_results(self, exact_matches, only_in_ont1, only_in_ont2, name_similarities):
        """
        Save lexical comparison results to files
        
        Args:
            exact_matches (set): Set of entity names appearing in both ontologies
            only_in_ont1 (set): Set of entity names only in the first ontology
            only_in_ont2 (set): Set of entity names only in the second ontology
            name_similarities (list): List of (name1, name2, similarity) tuples
        """
        # Save exact matches
        with open(os.path.join(self.output_dir, "lexical", "exact_name_matches.txt"), 'w') as f:
            f.write(f"Exact Matches ({len(exact_matches)}):\n")
            for name in sorted(exact_matches):
                f.write(f"  - {name}\n")
        
        # Save unique names
        with open(os.path.join(self.output_dir, "lexical", "unique_names.txt"), 'w') as f:
            f.write(f"Names only in {self.ont1.name} ({len(only_in_ont1)}):\n")
            for name in sorted(only_in_ont1)[:100]:  # Limit to first 100
                f.write(f"  - {name}\n")
            
            if len(only_in_ont1) > 100:
                f.write(f"  ... and {len(only_in_ont1) - 100} more\n")
            
            f.write(f"\nNames only in {self.ont2.name} ({len(only_in_ont2)}):\n")
            for name in sorted(only_in_ont2)[:100]:  # Limit to first 100
                f.write(f"  - {name}\n")
            
            if len(only_in_ont2) > 100:
                f.write(f"  ... and {len(only_in_ont2) - 100} more\n")
        
        # Save similar pairs
        if name_similarities:
            with open(os.path.join(self.output_dir, "lexical", "similar_names.txt"), 'w') as f:
                f.write(f"Similar Name Pairs (Jaro-Winkler similarity > 0.8):\n")
                for i, (name1, name2, sim) in enumerate(name_similarities[:50]):  # Limit to top 50
                    f.write(f"{i+1}. {name1} <-> {name2} (similarity: {sim:.4f})\n")
                
                if len(name_similarities) > 50:
                    f.write(f"... and {len(name_similarities) - 50} more\n")
            
            # Save as CSV for further analysis
            df = pd.DataFrame(name_similarities, columns=['Name in ' + self.ont1.name, 
                                                         'Name in ' + self.ont2.name, 
                                                         'Similarity'])
            df.to_csv(os.path.join(self.output_dir, "lexical", "name_similarities.csv"), index=False)
    
    def _save_semantic_results(self, common_similarities, cross_similarities):
        """
        Save semantic comparison results to files
        
        Args:
            common_similarities (list): List of (uri, similarity) tuples for common entities
            cross_similarities (list): List of (uri1, uri2, similarity) tuples for cross-ontology comparisons
        """
        # Save common entity similarities
        if common_similarities:
            with open(os.path.join(self.output_dir, "semantic", "common_entity_similarities.txt"), 'w') as f:
                f.write(f"Semantic Similarities for Common Entities ({len(common_similarities)}):\n\n")
                
                f.write("Top 20 most similar:\n")
                for i, (entity, sim) in enumerate(common_similarities[:20]):
                    entity_short = self.ont1.get_shortened_uri(entity)
                    f.write(f"{i+1}. {entity_short}: {sim:.4f}\n")
                
                f.write("\nBottom 20 least similar:\n")
                for i, (entity, sim) in enumerate(common_similarities[-20:]):
                    entity_short = self.ont1.get_shortened_uri(entity)
                    f.write(f"{i+1}. {entity_short}: {sim:.4f}\n")
            
            # Save as CSV
            df = pd.DataFrame([(self.ont1.get_shortened_uri(e), e, s) for e, s in common_similarities], 
                             columns=['Entity', 'URI', 'Similarity'])
            df.to_csv(os.path.join(self.output_dir, "semantic", "common_entity_similarities.csv"), index=False)
        
        # Save cross-ontology similarities
        if cross_similarities:
            with open(os.path.join(self.output_dir, "semantic", "cross_ontology_similarities.txt"), 'w') as f:
                f.write(f"Cross-Ontology Semantic Similarities (Top {len(cross_similarities)}):\n\n")
                
                for i, (e1, e2, sim) in enumerate(cross_similarities):
                    e1_short = self.ont1.get_shortened_uri(e1)
                    e2_short = self.ont2.get_shortened_uri(e2)
                    
                    # Add text content when available
                    text1 = self.ont1.entities[e1]['combined_text'][:100] + "..." if len(self.ont1.entities[e1]['combined_text']) > 100 else self.ont1.entities[e1]['combined_text']
                    text2 = self.ont2.entities[e2]['combined_text'][:100] + "..." if len(self.ont2.entities[e2]['combined_text']) > 100 else self.ont2.entities[e2]['combined_text']
                    
                    f.write(f"{i+1}. {e1_short} <-> {e2_short}: {sim:.4f}\n")
                    f.write(f"   {self.ont1.name}: \"{text1}\"\n")
                    f.write(f"   {self.ont2.name}: \"{text2}\"\n\n")
            
            # Save as CSV
            df = pd.DataFrame([
                (self.ont1.get_shortened_uri(e1), 
                 self.ont2.get_shortened_uri(e2), 
                 sim,
                 self.ont1.entities[e1]['combined_text'][:100] + "..." if len(self.ont1.entities[e1]['combined_text']) > 100 else self.ont1.entities[e1]['combined_text'],
                 self.ont2.entities[e2]['combined_text'][:100] + "..." if len(self.ont2.entities[e2]['combined_text']) > 100 else self.ont2.entities[e2]['combined_text']
                ) for e1, e2, sim in cross_similarities],
                columns=['Entity in ' + self.ont1.name, 
                         'Entity in ' + self.ont2.name, 
                         'Similarity',
                         'Text in ' + self.ont1.name,
                         'Text in ' + self.ont2.name])
            df.to_csv(os.path.join(self.output_dir, "semantic", "cross_ontology_similarities.csv"), index=False)

    def generate_comprehensive_report(self):
        """
        Generate a comprehensive markdown report of the comparison
        
        Creates a structured report containing all analysis results and
        visualizations for easy interpretation.
        
        Returns:
            str: Path to the generated report file
        """
        report_path = os.path.join(self.output_dir, "comprehensive_report.md")
        
        with open(report_path, 'w') as f:
            # Report header
            f.write("# Ontology Comparison Report\n\n")
            f.write(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Ontologies Compared\n\n")
            f.write(f"1. **{self.ont1.name}:** {self.ont1.ttl_file_path}\n")
            f.write(f"2. **{self.ont2.name}:** {self.ont2.ttl_file_path}\n\n")
            
            # Structural comparison section
            f.write("## 1. Structural Analysis\n\n")
            f.write("This section compares the structural elements of the ontologies, including classes, properties, and hierarchical organization.\n\n")
            
            f.write("### 1.1 Basic Metrics\n\n")
            f.write("![Basic Structural Metrics](structural/basic_metrics_comparison.png)\n\n")
            
            # Include table from file if it exists
            metrics_file = os.path.join(self.output_dir, "structural", "metrics_comparison.txt")
            if os.path.exists(metrics_file):
                with open(metrics_file, 'r') as mf:
                    metrics_content = mf.read()
                    f.write("```\n")
                    f.write(metrics_content)
                    f.write("```\n\n")
            
            f.write("### 1.2 Class Hierarchy\n\n")
            f.write("Class hierarchy depth comparison:\n\n")
            f.write("![Hierarchy Depth](structural/hierarchy_depth_comparison.png)\n\n")
            
            f.write("Visualization of top levels of class hierarchies:\n\n")
            f.write("![Class Hierarchy Visualization](structural/class_hierarchy_visualization.png)\n\n")
            
            f.write("### 1.3 Property Analysis\n\n")
            f.write("Distribution of property types in each ontology:\n\n")
            f.write("![Property Types](structural/property_types_comparison.png)\n\n")
            
            # Lexical comparison section
            f.write("## 2. Lexical Analysis\n\n")
            f.write("This section analyzes the similarities and differences in entity naming between the ontologies.\n\n")
            
            f.write("### 2.1 Name Overlap\n\n")
            f.write("Venn diagram showing the overlap of entity names between ontologies:\n\n")
            f.write("![Name Overlap](lexical/name_overlap_venn.png)\n\n")
            
            # Include heatmap if it exists
            heatmap_file = os.path.join(self.output_dir, "lexical", "name_similarity_heatmap.png")
            if os.path.exists(heatmap_file):
                f.write("### 2.2 Name Similarity Analysis\n\n")
                f.write("Heatmap showing lexical similarities between entity names:\n\n")
                f.write("![Name Similarity Heatmap](lexical/name_similarity_heatmap.png)\n\n")
            
            # Include bar chart if it exists
            bar_chart_file = os.path.join(self.output_dir, "lexical", "top_name_similarities.png")
            if os.path.exists(bar_chart_file):
                f.write("Top similar entity names between ontologies:\n\n")
                f.write("![Top Similar Names](lexical/top_name_similarities.png)\n\n")
            
            # Semantic comparison section
            f.write("## 3. Semantic Analysis\n\n")
            f.write("This section compares the meaning and context of entities based on their labels and comments.\n\n")
            
            # Check which semantic visualization files exist
            distribution_file = os.path.join(self.output_dir, "semantic", "common_entity_similarity_distribution.png")
            top_similarities_file = os.path.join(self.output_dir, "semantic", "top_common_entity_similarities.png")
            bottom_similarities_file = os.path.join(self.output_dir, "semantic", "bottom_common_entity_similarities.png")
            cross_similarities_file = os.path.join(self.output_dir, "semantic", "cross_ontology_similarities.png")
            cross_heatmap_file = os.path.join(self.output_dir, "semantic", "cross_similarity_heatmap.png")
            fallback_file = os.path.join(self.output_dir, "semantic", "text_annotation_coverage.png")
            
            if os.path.exists(distribution_file):
                f.write("### 3.1 Common Entity Semantic Similarity\n\n")
                f.write("Distribution of semantic similarities for entities that exist in both ontologies:\n\n")
                f.write("![Semantic Similarity Distribution](semantic/common_entity_similarity_distribution.png)\n\n")
            
            if os.path.exists(top_similarities_file):
                f.write("Entities with highest semantic similarity between ontologies:\n\n")
                f.write("![Top Semantic Similarities](semantic/top_common_entity_similarities.png)\n\n")
            
            if os.path.exists(bottom_similarities_file):
                f.write("Entities with lowest semantic similarity between ontologies:\n\n")
                f.write("![Bottom Semantic Similarities](semantic/bottom_common_entity_similarities.png)\n\n")
            
            if os.path.exists(cross_similarities_file):
                f.write("### 3.2 Cross-Ontology Semantic Analysis\n\n")
                f.write("Semantic similarities between different entities across ontologies:\n\n")
                f.write("![Cross-Ontology Similarities](semantic/cross_ontology_similarities.png)\n\n")
            
            if os.path.exists(cross_heatmap_file):
                f.write("Heatmap of semantic similarities between top entities across ontologies:\n\n")
                f.write("![Cross-Ontology Similarity Heatmap](semantic/cross_similarity_heatmap.png)\n\n")
                
            if os.path.exists(fallback_file):
                f.write("### 3.3 Text Annotation Coverage\n\n")
                f.write("Comparison of label and comment availability in both ontologies:\n\n")
                f.write("![Text Annotation Coverage](semantic/text_annotation_coverage.png)\n\n")
            
            # Conclusion
            f.write("## Conclusion\n\n")
            f.write("This report provides a comprehensive comparison of the two ontologies across structural, lexical, and semantic dimensions. ")
            f.write("The visualizations and analysis show the similarities and differences between the ontologies in terms of their structure, naming conventions, and semantic content.\n\n")
            
            f.write("Key findings:\n\n")
            f.write("- **Structural Analysis**: Quantitative comparison of classes, properties, and hierarchical organization.\n")
            f.write("- **Lexical Analysis**: Identification of naming patterns and similarities.\n")
            f.write("- **Semantic Analysis**: Evaluation of conceptual alignment based on textual descriptions.\n\n")
            
            f.write("For detailed metrics and further analysis, please refer to the CSV files and other outputs in the corresponding directories.\n")
        
        print(f"Comprehensive report generated: {report_path}")
        return report_path


def compare_ontologies(ttl_file_path1, ttl_file_path2, output_dir=None, ont1_name="Ontology 1", ont2_name="Ontology 2"):
    """
    Compare two TTL files representing ontologies
    
    This function orchestrates the process of analyzing and comparing two ontologies,
    generating comprehensive reports and visualizations of the results.
    
    Args:
        ttl_file_path1 (str): Path to the first TTL file
        ttl_file_path2 (str): Path to the second TTL file
        output_dir (str, optional): Directory to save results. If None, creates a timestamped directory.
        ont1_name (str, optional): Name for the first ontology. Defaults to "Ontology 1".
        ont2_name (str, optional): Name for the second ontology. Defaults to "Ontology 2".
        
    Returns:
        tuple: (output_dir, report_path) - Paths to the output directory and report file
    """
    print(f"Comparing ontologies:\n1: {ttl_file_path1}\n2: {ttl_file_path2}")
    
    # Create output directory if not provided
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create the output directory in the same location as the first input file
        base_dir = os.path.dirname(ttl_file_path1)
        output_dir = os.path.join(base_dir, f"ontology_comparison_{timestamp}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize analyzers for each ontology
    print("Loading and analyzing first ontology...")
    ont1 = OntologyAnalyzer(ttl_file_path1, name=ont1_name)
    
    print("Loading and analyzing second ontology...")
    ont2 = OntologyAnalyzer(ttl_file_path2, name=ont2_name)
    
    # Initialize comparator
    print("Initializing comparator...")
    comparator = OntologyComparator(ont1, ont2)
    comparator.set_output_directory(output_dir)
    
    # Run structural comparison
    print("Comparing structural features...")
    structural_results = comparator.compare_structure()
    
    # Run lexical comparison
    print("Comparing lexical features...")
    lexical_results = comparator.compare_lexical()
    
    # Prepare for semantic comparison by loading embedding model
    comparator.prepare_semantic_analysis()
    
    # Run semantic comparison
    print("Comparing semantic features...")
    semantic_results = comparator.compare_semantic()
    
    # Generate comprehensive report
    print("Generating comprehensive report...")
    report_path = comparator.generate_comprehensive_report()
    
    print(f"Comparison complete! Results saved to {output_dir}")
    print(f"Comprehensive report: {report_path}")
    
    return output_dir, report_path


def main():
    """
    Main function to run the ontology comparison from command line
    
    Parses command line arguments and runs the comparison.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Compare two ontologies in TTL format')
    
    parser.add_argument('ttl_file1', help='Path to the first TTL file')
    parser.add_argument('ttl_file2', help='Path to the second TTL file')
    parser.add_argument('--output', '-o', help='Output directory (optional)')
    parser.add_argument('--name1', default='Ontology 1', help='Name for the first ontology (default: "Ontology 1")')
    parser.add_argument('--name2', default='Ontology 2', help='Name for the second ontology (default: "Ontology 2")')
    
    args = parser.parse_args()
    
    # Run comparison
    output_dir, report_path = compare_ontologies(
        args.ttl_file1, 
        args.ttl_file2,
        output_dir=args.output,
        ont1_name=args.name1,
        ont2_name=args.name2
    )
    
    # Print results location
    print(f"Results saved to: {output_dir}")
    print(f"Report available at: {report_path}")


if __name__ == "__main__":
    main()