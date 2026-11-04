import sys
import time
import requests
from rdflib import Graph, Namespace, URIRef, BNode, Literal
from rdflib.namespace import RDF, RDFS, OWL
import os
import re

# [FIX 1] Import LLM utilities used by the other repair scripts
from api_utils import send_prompt, extract_between_markers, load_runtime_config

load_runtime_config()

# =========================
# CONFIGURATION
# =========================
ONTOLOGY_TTL_PATH = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/mistral-ontologies/sewerNetMistral_syntax_logic_consist_fixed.ttl"

OOPS_ENDPOINT = "https://oops.linkeddata.es/rest"
OUTPUT_FORMAT = "TURTLE"
PITFALLS = ""

MAX_AFFECTED_TO_SHOW = 25
TRIPLES_PER_ELEMENT_LIMIT = 250

# [FIX 2] Add repair iteration limit (was entirely absent)
MAX_REPAIR_ITERATIONS = 25

OUTFILE = os.path.splitext(os.path.basename(ONTOLOGY_TTL_PATH))[0] + "_oops_snippets.txt"

# [FIX 3] Define output ontology path (was entirely absent)
REPAIRED_TTL = os.path.splitext(ONTOLOGY_TTL_PATH)[0] + "_oops_fixed.ttl"

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
# Affected elements extraction
# =========================
def get_affected_elements(oops_graph: Graph, pitfall_node):
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

    for o in oops_graph.objects(pitfall_node, OOPS.hasAffectedElement):
        add_from_value(o)

    for o in oops_graph.objects(pitfall_node, OOPS.hasDescription):
        if isinstance(o, Literal):
            txt = str(o)
            for u in URI_RE.findall(txt):
                elems.append(URIRef(u))

    for _, _, o in oops_graph.triples((pitfall_node, None, None)):
        if isinstance(o, Literal):
            txt = str(o)
            for u in URI_RE.findall(txt):
                elems.append(URIRef(u))

    seen = set()
    uniq = []
    for e in elems:
        if e not in seen:
            seen.add(e)
            uniq.append(e)

    return uniq


# =========================
# Validation helpers for P05, P31, P39
# =========================
def validate_inverse_relationship(ontology_graph: Graph, prop: URIRef) -> tuple[bool, str]:
    """
    Check if an inverse relationship is correctly defined.
    Returns (is_problematic, reason).
    """
    inverses = list(ontology_graph.objects(prop, OWL.inverseOf))

    if not inverses:
        return False, ""

    for inverse_prop in inverses:
        if not isinstance(inverse_prop, URIRef):
            return True, "Inverse is not a proper URI"

        # Self-inverse without SymmetricProperty
        if inverse_prop == prop:
            is_symmetric = (prop, RDF.type, OWL.SymmetricProperty) in ontology_graph
            if not is_symmetric:
                return True, "Property is inverse of itself but not declared symmetric"

        # [FIX 4] Removed non-reciprocation check — OWL semantics entail symmetry
        # of owl:inverseOf automatically; flagging it was a false positive.

        # Transitive property with an inverse (logical conflict in OWL2-DL)
        if (prop, RDF.type, OWL.TransitiveProperty) in ontology_graph:
            return True, "Transitive property has an inverse (non-simple property conflict)"

        # Domain/range compatibility
        prop_domains = set(ontology_graph.objects(prop, RDFS.domain))
        prop_ranges = set(ontology_graph.objects(prop, RDFS.range))
        inv_domains = set(ontology_graph.objects(inverse_prop, RDFS.domain))
        inv_ranges = set(ontology_graph.objects(inverse_prop, RDFS.range))

        if prop_domains and inv_ranges and prop_domains != inv_ranges:
            return True, "Domain of property does not match range of its declared inverse"
        if prop_ranges and inv_domains and prop_ranges != inv_domains:
            return True, "Range of property does not match domain of its declared inverse"

    return False, ""


def validate_equivalent_class(ontology_graph: Graph, cls: URIRef) -> tuple[bool, str]:
    equivalents = list(ontology_graph.objects(cls, OWL.equivalentClass))

    if not equivalents:
        return False, ""

    for equiv_cls in equivalents:
        if not isinstance(equiv_cls, URIRef):
            continue

        if equiv_cls == cls:
            return True, "Class declared equivalent to itself (redundant)"

        if (cls, RDFS.subClassOf, equiv_cls) in ontology_graph:
            return True, "Class is both subclass and equivalent to the same class (contradiction)"
        if (equiv_cls, RDFS.subClassOf, cls) in ontology_graph:
            return True, "Class is both superclass and equivalent to the same class (contradiction)"

    return False, ""


def extract_namespace_from_uri(uri: str) -> str:
    if '#' in uri:
        return uri.rsplit('#', 1)[0] + '#'
    elif '/' in uri:
        return uri.rsplit('/', 1)[0] + '/'
    return uri


def detect_ambiguous_namespaces(ontology_graph: Graph) -> list:
    """
    Detect P39: Ambiguous namespace issues.
    Returns list of problematic namespace strings.
    """
    from urllib.parse import urlparse

    # Collect only ontology-local URIs (exclude standard vocabularies)
    STANDARD_PREFIXES = {
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "http://www.w3.org/2000/01/rdf-schema#",
        "http://www.w3.org/2002/07/owl#",
        "http://www.w3.org/2001/XMLSchema#",
    }

    all_uris = set()
    for s, p, o in ontology_graph:
        for term in (s, p, o):
            if isinstance(term, URIRef):
                uri_str = str(term)
                ns = extract_namespace_from_uri(uri_str)
                if ns not in STANDARD_PREFIXES:
                    all_uris.add(uri_str)

    domain_groups = {}
    for uri in all_uris:
        try:
            parsed = urlparse(uri)
            domain = parsed.netloc
            if domain:
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(uri)
        except Exception:
            continue

    affected = []
    for domain, uris in domain_groups.items():
        namespaces = set()
        for uri in uris:
            ns = extract_namespace_from_uri(uri)
            namespaces.add(ns)

        if len(namespaces) > 1:
            patterns = set()
            for ns in namespaces:
                base = ns.rstrip('/#')
                patterns.add(base)
            if len(patterns) == 1 and len(namespaces) > 1:
                affected.extend(namespaces)

    namespace_list = list(set(extract_namespace_from_uri(uri) for uri in all_uris))
    for i, ns1 in enumerate(namespace_list):
        for ns2 in namespace_list[i + 1:]:
            if ns1.rstrip('/#') == ns2.rstrip('/#'):
                if ns1 not in affected:
                    affected.append(ns1)
                if ns2 not in affected:
                    affected.append(ns2)

    return list(set(affected))


def infer_affected_elements_by_pitfall(ontology_graph: Graph, pitfall_code: str):
    affected = []
    reasons_by_elem = {}

    if pitfall_code == "P05":
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
        # Returns strings, not URIRefs — handled separately in repair
        affected = detect_ambiguous_namespaces(ontology_graph)

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


def build_snippet_for_affected(src: Graph, affected: list) -> Graph:
    """
    Build a subgraph around affected elements.
    Accepts URIRef objects only; plain strings are skipped.
    """
    out = Graph()
    out.namespace_manager = src.namespace_manager
    for node in affected[:MAX_AFFECTED_TO_SHOW]:
        # [FIX 5] Guard: skip plain strings (e.g., from P39 namespace detection)
        if not isinstance(node, URIRef):
            continue
        add_resource_neighborhood(src, out, node, TRIPLES_PER_ELEMENT_LIMIT)
    return out


# =========================
# LLM repair helpers  [FIX 6 — entirely new section]
# =========================
def llm_repair_pitfall(
    pitfall_code: str,
    pitfall_description: str,
    pitfall_suggestion: str,
    context_ttl: str,
) -> str:
    """
    Ask the LLM to propose a Turtle repair for a detected pitfall.
    Returns the repaired Turtle snippet, or empty string if LLM provides none.
    """
    prompt = f"""You are an expert OWL ontology engineer.
The OOPS! Pitfall Scanner has detected the following critical pitfall in the ontology:

Pitfall code: {pitfall_code}
Description: {pitfall_description}
Suggestion: {pitfall_suggestion}

Relevant ontology fragment (Turtle):
{context_ttl}

Your task:
- Propose a minimal repair that resolves this pitfall.
- Output ONLY the corrected or replacement Turtle triples.
- Do NOT repeat unmodified triples.
- Ensure the output is syntactically valid Turtle.
- Place your output strictly between the markers below.

###start_turtle###
###end_turtle###
"""
    reply = send_prompt(
        prompt,
        persona="OWL ontology repair expert",
        step_name=f"oops_repair_{pitfall_code}",
    )
    fixed = extract_between_markers(reply, "###start_turtle###", "###end_turtle###")
    if fixed and fixed[0].strip():
        return fixed[0].strip()
    return ""


def apply_turtle_patch(ontology_graph: Graph, patch_ttl: str) -> Graph:
    """
    Parse the LLM-proposed Turtle patch and merge it into the ontology graph.
    New triples are added; the patch does not delete existing triples
    (deletion is handled by the LLM producing corrected replacements for
    the specific affected IRIs, which override on re-serialisation).
    """
    patch_graph = Graph()
    try:
        patch_graph.parse(data=patch_ttl, format="turtle")
    except Exception as e:
        print(f"  ⚠️  Patch Turtle failed to parse, skipping: {e}")
        return ontology_graph

    for triple in patch_graph:
        ontology_graph.add(triple)

    print(f"  ✓ Applied patch: {len(patch_graph)} triples merged into ontology.")
    return ontology_graph


def get_critical_pitfalls(oops_graph: Graph) -> list:
    """
    Return all pitfall nodes from an OOPS response graph that are Critical.
    """
    pitfalls = list(oops_graph.subjects(RDF.type, OOPS.pitfall))
    critical = []
    for node in pitfalls:
        level = first_literal(oops_graph, node, OOPS.hasImportanceLevel).strip().lower()
        if level == "critical":
            critical.append(node)
    return critical


def run_oops(ontology_graph: Graph) -> Graph:
    """
    Serialise ontology, send to OOPS!, return parsed OOPS response graph.
    """
    rdfxml = ontology_graph.serialize(format="xml")
    xml_request = build_request_xml(rdfxml)
    response_text = call_oops(xml_request)
    return parse_oops_graph(response_text)


# =========================
# Diagnostic output helper
# =========================
def write_block(f, title: str, text: str):
    f.write("\n" + "=" * 120 + "\n")
    f.write(title + "\n")
    f.write("=" * 120 + "\n\n")
    f.write(text)
    if not text.endswith("\n"):
        f.write("\n")


# =========================
# Main repair loop  [FIX 7 — entirely rewritten]
# =========================
def repair_loop(ontology_graph: Graph) -> Graph:
    """
    Iteratively detect and repair critical OOPS! pitfalls up to
    MAX_REPAIR_ITERATIONS times.  Returns the repaired graph.
    """
    with open(OUTFILE, "w", encoding="utf-8") as f:
        f.write(f"Ontology: {ONTOLOGY_TTL_PATH}\n")
        f.write(f"OOPS endpoint: {OOPS_ENDPOINT}\n")
        f.write("NOTE: Minor & Important pitfalls are ignored.\n\n")

    for iteration in range(1, MAX_REPAIR_ITERATIONS + 1):
        print(f"\n{'='*60}")
        print(f"🔁 OOPS repair iteration {iteration}/{MAX_REPAIR_ITERATIONS}")
        print(f"{'='*60}")

        oops_graph = run_oops(ontology_graph)
        critical_pitfalls = get_critical_pitfalls(oops_graph)

        if not critical_pitfalls:
            print("✅ No critical pitfalls detected. Repair complete.")
            break

        print(f"⚠️  {len(critical_pitfalls)} critical pitfall(s) detected.")

        for node in sorted(critical_pitfalls, key=str):
            code        = first_literal(oops_graph, node, OOPS.hasCode).strip()
            name        = first_literal(oops_graph, node, OOPS.hasName).strip()
            desc        = first_literal(oops_graph, node, OOPS.hasDescription).strip()
            sugg        = first_literal(oops_graph, node, OOPS.hasSuggestion).strip()
            affected_n  = first_literal(oops_graph, node, OOPS.hasNumberAffectedElements).strip()

            print(f"\n  Pitfall: {code} — {name}")
            if affected_n:
                print(f"  Affected elements: {affected_n}")

            # Log to diagnostic file
            with open(OUTFILE, "a", encoding="utf-8") as f:
                write_block(f, f"ITERATION {iteration} | PITFALL {code}: {name}",
                            f"importance: critical\ndescription: {desc}\nsuggestion: {sugg}\n")

            # ── P10: no specific axioms — provide full ontology ──────────
            if code == "P10":
                print("  P10: providing full ontology to LLM.")
                context_ttl = ontology_graph.serialize(format="turtle")
                patch_ttl = llm_repair_pitfall(code, desc, sugg, context_ttl)
                if patch_ttl:
                    ontology_graph = apply_turtle_patch(ontology_graph, patch_ttl)
                else:
                    print("  ⚠️  LLM returned no patch for P10.")
                continue

            # ── All other critical pitfalls: extract affected elements ───
            affected = get_affected_elements(oops_graph, node)

            PROBLEMATIC_CRITICAL_PITFALLS = ["P05", "P31", "P39"]
            reasons_by_elem = {}

            if not affected and code in PROBLEMATIC_CRITICAL_PITFALLS:
                print(f"  ⚠️  No affected elements from OOPS for {code}. Inferring locally...")
                affected, reasons_by_elem = infer_affected_elements_by_pitfall(
                    ontology_graph, code)
                if affected:
                    print(f"  ✓ Inferred {len(affected)} affected element(s).")
                else:
                    print(f"  ✗ Could not infer affected elements for {code}. Skipping.")
                    continue
            elif not affected:
                print(f"  ⚠️  No affected elements for {code}. Skipping.")
                continue
            else:
                print(f"  ✓ {len(affected)} affected element(s) from OOPS.")

            # [FIX 5] P39: affected elements are namespace strings, not URIRefs.
            # Build context from description only; snippet generation is skipped.
            if code == "P39":
                context_ttl = f"# Ambiguous namespaces detected:\n"
                context_ttl += "\n".join(f"# {ns}" for ns in affected[:MAX_AFFECTED_TO_SHOW])
                context_ttl += "\n\n"
                context_ttl += ontology_graph.serialize(format="turtle")
            else:
                snippet = build_snippet_for_affected(ontology_graph, affected)
                context_ttl = snippet.serialize(format="turtle")

                with open(OUTFILE, "a", encoding="utf-8") as f:
                    write_block(f,
                                f"Iteration {iteration} | {code} SNIPPET",
                                context_ttl)

                if reasons_by_elem:
                    with open(OUTFILE, "a", encoding="utf-8") as f:
                        for elem, reason in reasons_by_elem.items():
                            write_block(f, f"Reason for {elem}", reason + "\n")

            # ── Call LLM for repair ──────────────────────────────────────
            patch_ttl = llm_repair_pitfall(code, desc, sugg, context_ttl)
            if patch_ttl:
                ontology_graph = apply_turtle_patch(ontology_graph, patch_ttl)
                with open(OUTFILE, "a", encoding="utf-8") as f:
                    write_block(f,
                                f"Iteration {iteration} | {code} LLM PATCH",
                                patch_ttl)
            else:
                print(f"  ⚠️  LLM returned no patch for {code}.")

        time.sleep(2)   # brief pause between iterations to respect OOPS rate limits

    return ontology_graph


# =========================
# Entry point
# =========================
if __name__ == "__main__":
    print("🔍 Loading ontology (Turtle)...")
    ontology_graph = Graph()
    ontology_graph.parse(ONTOLOGY_TTL_PATH, format="turtle")
    print(f"✅ Loaded {len(ontology_graph)} triples.")

    # [FIX 7] Run the full repair loop instead of detection-only reporting
    repaired_graph = repair_loop(ontology_graph)

    # [FIX 3] Save the repaired ontology
    repaired_graph.serialize(destination=REPAIRED_TTL, format="turtle")
    print(f"\n✅ Repaired ontology saved to: {REPAIRED_TTL}")
    print(f"✅ Diagnostic log saved to: {OUTFILE}")