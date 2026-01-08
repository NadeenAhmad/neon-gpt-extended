import sys
import requests
from rdflib import Graph, Namespace, URIRef, BNode, Literal
from rdflib.namespace import RDF, RDFS, OWL
import os
import re

# =========================
# CONFIGURATION
# =========================
#ONTOLOGY_TTL_PATH =  "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/gpt-4o-ontologies/gpt4_aquadiva_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/gpt-4o-ontologies/gpt4_cheminf_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH ="/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/gpt-4o-ontologies/gpt4_sewernet_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/gpt-4o-ontologies/gpt4_wine_syntax_logic_consist_fixed.ttl"

   
#ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/deepseek-ontologies/AquaDiva_deepseek_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/deepseek-ontologies/CHEMINF_deepseek_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/deepseek-ontologies/SEWERNET_deepseek_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/deepseek-ontologies/WINE_deepseek_syntax_logic_consist_fixed.ttl"
   
    
#ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/llama4-ontologies/AquaDiva_llama_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH =  "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/llama4-ontologies/cheminf_llama_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/llama4-ontologies/sewernet_llama_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/llama4-ontologies/wine_llama_syntax_logic_consist_fixed.ttl"
  
#ONTOLOGY_TTL_PATH ="/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/mistral-ontologies/aquaDivaMistral_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH ="/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/mistral-ontologies/cheminfMistral_syntax_logic_consist_fixed.ttl"
ONTOLOGY_TTL_PATH ="/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/mistral-ontologies/sewerNetMistral_syntax_logic_consist_fixed.ttl"
#ONTOLOGY_TTL_PATH ="/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/mistral-ontologies/wineMistral_syntax_logic_consist_fixed.ttl"


OOPS_ENDPOINT = "https://oops.linkeddata.es/rest"
OUTPUT_FORMAT = "TURTLE"
PITFALLS = ""

MAX_AFFECTED_TO_SHOW = 25
TRIPLES_PER_ELEMENT_LIMIT = 250

OUTFILE = os.path.splitext(os.path.basename(ONTOLOGY_TTL_PATH))[0] + "_oops_snippets.txt"

OOPS = Namespace("http://oops.linkeddata.es/def#")
URI_RE = re.compile(r"https?://[^\s<>\"]+")


# =========================
# OOPS request helpers
# =========================
def build_request_xml(rdfxml: str) -> str:
    safe = rdfxml.replace("]]>", "]]]]><![CDATA[>")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<OOPSRequest>
  <OntologyUrl></OntologyUrl>
  <OntologyContent><![CDATA[{safe}]]></OntologyContent>
  <Pitfalls>{PITFALLS}</Pitfalls>
  <OutputFormat>{OUTPUT_FORMAT}</OutputFormat>
</OOPSRequest>
"""


def call_oops(xml_request: str) -> str:
    headers = {
        "Content-Type": "application/xml",
        "Accept": "text/turtle, application/rdf+xml;q=0.9, text/plain;q=0.8, */*;q=0.1",
    }
    r = requests.post(
        OOPS_ENDPOINT,
        data=xml_request.encode("utf-8"),
        headers=headers,
        timeout=280,
    )
    if not r.ok:
        raise RuntimeError(f"OOPS HTTP {r.status_code}: {r.text[:2000]}")
    return r.text


def parse_oops_graph(response_text: str) -> Graph:
    g = Graph()
    try:
        g.parse(data=response_text, format="turtle")
        return g
    except Exception:
        g = Graph()
        g.parse(data=response_text, format="xml")
        return g


def first_literal(g: Graph, s, p) -> str:
    for o in g.objects(s, p):
        return str(o)
    return ""


# =========================
# ENHANCED Affected elements extraction
# =========================
def get_affected_elements(oops_graph: Graph, pitfall_node):
    """
    Enhanced version that tries multiple strategies to extract affected elements
    """
    elems = []

    def add_from_value(v):
        if isinstance(v, URIRef):
            elems.append(v)
            return

        if isinstance(v, Literal):
            txt = str(v)
            for u in URI_RE.findall(txt):
                elems.append(URIRef(u))
            return

        if isinstance(v, BNode):
            for _, _, o2 in oops_graph.triples((v, None, None)):
                add_from_value(o2)
            return

    # Strategy 1: Standard hasAffectedElement property
    for o in oops_graph.objects(pitfall_node, OOPS.hasAffectedElement):
        add_from_value(o)

    # Strategy 2: Check for description property (sometimes used for P05 and others)
    for o in oops_graph.objects(pitfall_node, OOPS.hasDescription):
        if isinstance(o, Literal):
            txt = str(o)
            for u in URI_RE.findall(txt):
                elems.append(URIRef(u))

    # Strategy 3: Look at all literal values connected to the pitfall
    # This catches cases where URIs are embedded in various text fields
    for _, _, o in oops_graph.triples((pitfall_node, None, None)):
        if isinstance(o, Literal):
            txt = str(o)
            for u in URI_RE.findall(txt):
                elems.append(URIRef(u))

    # De-duplicate while preserving order
    seen = set()
    uniq = []
    for e in elems:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    
    return uniq


# =========================
# VALIDATION AND INFERENCE for problematic critical pitfalls only (P05, P31, P39)
# =========================
def validate_inverse_relationship(ontology_graph: Graph, prop: URIRef) -> tuple[bool, str]:
    """
    Check if an inverse relationship is correctly defined.
    Returns (is_problematic, reason)
    """
    inverses = list(ontology_graph.objects(prop, OWL.inverseOf))
    
    if not inverses:
        return False, ""  # No inverse declared, not a P05 issue
    
    for inverse_prop in inverses:
        if not isinstance(inverse_prop, URIRef):
            return True, "Inverse is not a proper URI"
        
        # Check 1: Is it self-inverse? (Usually wrong unless symmetric)
        if inverse_prop == prop:
            is_symmetric = (prop, RDF.type, OWL.SymmetricProperty) in ontology_graph
            if not is_symmetric:
                return True, "Property is inverse of itself but not symmetric"
        
        # Check 2: Does the inverse reciprocate?
        reciprocal_inverses = list(ontology_graph.objects(inverse_prop, OWL.inverseOf))
        if prop not in reciprocal_inverses:
            return True, f"Inverse relationship not reciprocated"
        
        # Check 3: Is the property transitive? (Transitive properties shouldn't have inverses)
        if (prop, RDF.type, OWL.TransitiveProperty) in ontology_graph:
            return True, "Transitive property has an inverse (logical conflict)"
        
        # Check 4: Are domain and range compatible?
        prop_domains = set(ontology_graph.objects(prop, RDFS.domain))
        prop_ranges = set(ontology_graph.objects(prop, RDFS.range))
        inv_domains = set(ontology_graph.objects(inverse_prop, RDFS.domain))
        inv_ranges = set(ontology_graph.objects(inverse_prop, RDFS.range))
        
        if prop_domains and inv_ranges and prop_domains != inv_ranges:
            return True, "Domain of property doesn't match range of inverse"
        if prop_ranges and inv_domains and prop_ranges != inv_domains:
            return True, "Range of property doesn't match domain of inverse"
    
    return False, ""


def validate_equivalent_class(ontology_graph: Graph, cls: URIRef) -> tuple[bool, str]:
    """
    Check if an equivalent class relationship is correctly defined.
    Returns (is_problematic, reason)
    """
    equivalents = list(ontology_graph.objects(cls, OWL.equivalentClass))
    
    if not equivalents:
        return False, ""
    
    for equiv_cls in equivalents:
        if not isinstance(equiv_cls, URIRef):
            continue  # Blank nodes might be restrictions
        
        # Check 1: Self-equivalence
        if equiv_cls == cls:
            return True, "Class is equivalent to itself (redundant)"
        
        # Check 2: Is the equivalence reciprocated?
        reciprocal = list(ontology_graph.objects(equiv_cls, OWL.equivalentClass))
        if cls not in reciprocal:
            return True, f"Equivalence not reciprocated"
        
        # Check 3: Are they also in a subclass relationship? (contradiction)
        if (cls, RDFS.subClassOf, equiv_cls) in ontology_graph:
            return True, "Class is both subclass and equivalent (contradiction)"
        if (equiv_cls, RDFS.subClassOf, cls) in ontology_graph:
            return True, "Class is both superclass and equivalent (contradiction)"
    
    return False, ""


def extract_namespace_from_uri(uri: str) -> str:
    """Extract the namespace from a URI"""
    if '#' in uri:
        return uri.rsplit('#', 1)[0] + '#'
    elif '/' in uri:
        return uri.rsplit('/', 1)[0] + '/'
    return uri


def detect_ambiguous_namespaces(ontology_graph: Graph) -> list:
    """
    Detect P39: Ambiguous namespace issues
    Returns list of problematic URIs/namespaces
    """
    affected = []
    namespace_patterns = {}
    
    # Collect all URIs and group by similar namespace patterns
    all_uris = set()
    for s, p, o in ontology_graph:
        if isinstance(s, URIRef):
            all_uris.add(str(s))
        if isinstance(p, URIRef):
            all_uris.add(str(p))
        if isinstance(o, URIRef):
            all_uris.add(str(o))
    
    # Group URIs by base domain
    from urllib.parse import urlparse
    domain_groups = {}
    
    for uri in all_uris:
        try:
            parsed = urlparse(uri)
            domain = parsed.netloc
            if domain:
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(uri)
        except:
            continue
    
    # Check for ambiguous patterns within same domain
    for domain, uris in domain_groups.items():
        namespaces = set()
        for uri in uris:
            ns = extract_namespace_from_uri(uri)
            namespaces.add(ns)
        
        # If same domain has multiple different namespace patterns, it's ambiguous
        if len(namespaces) > 1:
            # Check if they differ only by trailing slash or hash
            patterns = set()
            for ns in namespaces:
                base = ns.rstrip('/#')
                patterns.add(base)
            
            if len(patterns) == 1 and len(namespaces) > 1:
                # Same base but different separators (# vs /) - this is P39
                affected.extend(namespaces)
    
    # Also check for very similar namespace URIs (common typo source)
    namespace_list = list(set(extract_namespace_from_uri(uri) for uri in all_uris))
    for i, ns1 in enumerate(namespace_list):
        for ns2 in namespace_list[i+1:]:
            # Check if they're very similar (e.g., differ by one character)
            if ns1.rstrip('/#') == ns2.rstrip('/#'):
                affected.extend([ns1, ns2])
    
    return list(set(affected))


def infer_affected_elements_by_pitfall(ontology_graph: Graph, pitfall_code: str):
    affected = []
    reasons_by_elem = {}

    if pitfall_code == "P05":
        print("      Validating inverse relationships...")
        all_props_with_inverses = set()
        for s in ontology_graph.subjects(OWL.inverseOf, None):
            if isinstance(s, URIRef):
                all_props_with_inverses.add(s)
        for o in ontology_graph.objects(None, OWL.inverseOf):
            if isinstance(o, URIRef):
                all_props_with_inverses.add(o)

        for prop in all_props_with_inverses:
            is_problematic, reason = validate_inverse_relationship(ontology_graph, prop)
            if is_problematic:
                affected.append(prop)
                reasons_by_elem[prop] = reason

    elif pitfall_code == "P31":
        print("      Validating equivalent classes...")
        all_classes_with_equiv = set()
        for s in ontology_graph.subjects(OWL.equivalentClass, None):
            if isinstance(s, URIRef):
                all_classes_with_equiv.add(s)
        for o in ontology_graph.objects(None, OWL.equivalentClass):
            if isinstance(o, URIRef):
                all_classes_with_equiv.add(o)

        for cls in all_classes_with_equiv:
            is_problematic, reason = validate_equivalent_class(ontology_graph, cls)
            if is_problematic:
                affected.append(cls)
                reasons_by_elem[cls] = reason

    elif pitfall_code == "P39":
        print("      Detecting ambiguous namespaces...")
        # NOTE: these are strings (namespaces), not URIRefs
        affected = detect_ambiguous_namespaces(ontology_graph)

    # ✅ ALWAYS dedup safely, regardless of branch
    seen = set()
    uniq = []
    for a in affected:
        if a not in seen:
            seen.add(a)
            uniq.append(a)

    return uniq, reasons_by_elem


# =========================
# Snippet extraction
# =========================
def add_resource_neighborhood(src: Graph, out: Graph, node, max_triples: int):
    count = 0

    def is_empty_rdf_list(n) -> bool:
        return isinstance(n, BNode) and \
               (not any(src.triples((n, RDF.first, None)))) and \
               (not any(src.triples((n, RDF.rest, None))))

    def skip_object(p, o) -> bool:
        if isinstance(o, BNode) and not any(src.triples((o, None, None))):
            return True
        if p == OWL.unionOf and is_empty_rdf_list(o):
            return True
        if is_empty_rdf_list(o):
            return True
        return False

    # Outgoing
    for s, p, o in src.triples((node, None, None)):
        if skip_object(p, o):
            continue

        out.add((s, p, o))
        count += 1
        if count >= max_triples:
            return

        if isinstance(o, BNode):
            bnode_triples = list(src.triples((o, None, None)))
            if not bnode_triples:
                continue
            for s2, p2, o2 in bnode_triples:
                if skip_object(p2, o2):
                    continue
                out.add((s2, p2, o2))
                count += 1
                if count >= max_triples:
                    return

    # Incoming
    allowed_incoming = {
        RDF.type, RDFS.subClassOf, RDFS.domain, RDFS.range,
        OWL.inverseOf, OWL.disjointWith, OWL.equivalentClass, OWL.equivalentProperty
    }
    for s, p, o in src.triples((None, None, node)):
        if p not in allowed_incoming:
            continue

        if isinstance(s, BNode):
            s_triples = list(src.triples((s, None, None)))
            if len(s_triples) == 1 and s_triples[0] == (s, p, o):
                continue

        out.add((s, p, o))
        count += 1
        if count >= max_triples:
            return


def build_snippet_for_affected(src: Graph, affected: list[URIRef]) -> Graph:
    out = Graph()
    out.namespace_manager = src.namespace_manager
    for node in affected[:MAX_AFFECTED_TO_SHOW]:
        add_resource_neighborhood(src, out, node, TRIPLES_PER_ELEMENT_LIMIT)
    return out


# =========================
# Output helpers
# =========================
def write_block(f, title: str, text: str):
    f.write("\n" + "=" * 120 + "\n")
    f.write(title + "\n")
    f.write("=" * 120 + "\n\n")
    f.write(text)
    if not text.endswith("\n"):
        f.write("\n")


# =========================
# ENHANCED Main reporting
# =========================
def print_and_save_pitfalls(oops_graph: Graph, ontology_graph: Graph):
    pitfalls = list(oops_graph.subjects(RDF.type, OOPS.pitfall))
    if not pitfalls:
        print("✅ No pitfalls detected (or the response did not contain oops:pitfall nodes).")
        return

    with open(OUTFILE, "w", encoding="utf-8") as f:
        f.write(f"Ontology: {ONTOLOGY_TTL_PATH}\n")
        f.write(f"OOPS endpoint: {OOPS_ENDPOINT}\n")
        f.write("NOTE: Minor & Important pitfalls are ignored.\n\n")

        for node in sorted(pitfalls, key=str):
            reasons_by_elem = {} 
            code = first_literal(oops_graph, node, OOPS.hasCode).strip()
            name = first_literal(oops_graph, node, OOPS.hasName).strip()
            level = first_literal(oops_graph, node, OOPS.hasImportanceLevel).strip()
            affected_n = first_literal(oops_graph, node, OOPS.hasNumberAffectedElements).strip()

            
            desc = first_literal(oops_graph, node, OOPS.hasDescription).strip()
            sugg = first_literal(oops_graph, node, OOPS.hasSuggestion).strip()  # only if present



            # Skip minor and important pitfalls
            if level.lower() in ["minor", "important"]:
                continue

            header = f"{code or '(no code)'}: {name or '(no name)'}"
            meta_lines = []
            if level:
                meta_lines.append(f"importance: {level}")
            if desc:
                meta_lines.append(f"description: {desc}")
            if sugg:
                meta_lines.append(f"suggestion: {sugg}")
            if affected_n:
                meta_lines.append(f"affected elements (count): {affected_n}")
        
            meta = "\n".join(meta_lines) + ("\n" if meta_lines else "")

            print(f"- {header}")
            if meta_lines:
                for ml in meta_lines:
                    print(f"  {ml}")

            write_block(f, f"PITFALL {header}", meta)
            if desc:
                write_block(f, "OOPS description", desc + "\n")
            if sugg:
                write_block(f, "OOPS suggestion", sugg + "\n")

            # Special: for P10 output the WHOLE ontology
            if (code or "").strip() == "P10":
                ttl_all = ontology_graph.serialize(format="turtle")
                print("  P10: writing full ontology to output file (no truncation).")
                write_block(f, "P10 FULL ONTOLOGY (Turtle serialization)", ttl_all)
                continue

            # ENHANCED: Try to get affected elements from OOPS
            affected = get_affected_elements(oops_graph, node)
            
            # ENHANCED: If no affected elements found AND this is a problematic critical pitfall, try inference
            PROBLEMATIC_CRITICAL_PITFALLS = ["P05", "P31", "P39"]
            
            if not affected and code in PROBLEMATIC_CRITICAL_PITFALLS:
                print(f"  ⚠️  No affected elements returned by OOPS for {code}. Attempting inference...")
                affected, reasons_by_elem = infer_affected_elements_by_pitfall(ontology_graph, code)
                if affected:
                    print(f"  ✓ Inferred {len(affected)} affected elements from ontology structure")
                else:
                    print(f"  ✗ Could not infer affected elements for {code}")
            elif not affected:
                # For other critical pitfalls, this is unexpected - OOPS should provide them
                print(f"  ⚠️  WARNING: No affected elements returned by OOPS for {code} (unexpected)")
            else:
                print(f"  ✓ Found {len(affected)} affected element URIs from OOPS")

            # Write affected elements (even if empty, for debugging)
            if affected:
                title = "Affected elements" if code == "P39" else "Affected element URIs"
                write_block(f, title, "\n".join(map(str, affected)) + "\n")
            else:
                write_block(f, "Affected element URIs", "(No affected elements found or inferred)\n")

            # Only create snippet if we have affected elements
            if affected:
                snippet = build_snippet_for_affected(ontology_graph, affected)
                ttl_snip = snippet.serialize(format="turtle")
                
                if ttl_snip.strip():
                    print(f"  ✓ Generated snippet with {len(snippet)} triples")
                    write_block(f, f"{code} SNIPPET (local subgraph around affected elements)", ttl_snip)
                else:
                    print(f"  ⚠️  Snippet is empty (affected elements may not exist in ontology)")
                    write_block(f, f"{code} SNIPPET", "(Empty - affected elements not found in ontology)\n")
            else:
                print(f"  ⚠️  Skipping snippet generation (no affected elements)")

            print()

            if reasons_by_elem:
                for elem, reason in reasons_by_elem.items():
                    write_block(f, f"Reason for {elem}", reason + "\n")

    print(f"\n✅ Saved full output to: {OUTFILE}")


if __name__ == "__main__":
    print("🔍 Loading ontology (Turtle) locally...")
    ontology_graph = Graph()
    ontology_graph.parse(ONTOLOGY_TTL_PATH, format="turtle")

    print("🔍 Converting Turtle → RDF/XML for OOPS request...")
    rdfxml = ontology_graph.serialize(format="xml")

    print("📡 Sending ontology to OOPS!...")
    xml_request = build_request_xml(rdfxml)
    response_text = call_oops(xml_request)

    print("📋 Parsing OOPS response...\n")
    oops_graph = parse_oops_graph(response_text)

    print_and_save_pitfalls(oops_graph, ontology_graph)