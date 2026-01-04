"""
ontology_repair_pipeline.py

One-script pipeline to:
  A) Run deterministic “make it OWL2-DL reasoner friendly” repairs (HermiT-driven)
  B) Diagnose incoherence with ROBOT (reason/explain)
  C) Extract “problem slices” from ROBOT explanations
  D) Iteratively apply LLM-proposed minimal RDF triple patches until ROBOT reports COHERENT

Designed to run locally in VS Code (no Colab-only commands).
Requirements:
  - Python 3.9+
  - pip install rdflib requests
  - Java installed (java on PATH)
  - HermiT jar (download once)
  - ROBOT jar (download once or auto-download if enabled)
  - OpenRouter API key (env var OPENROUTER_API_KEY or config)

Usage:
  1) Edit CONFIG at the bottom (paths + model + options)
  2) Run: python ontology_repair_pipeline.py

Notes:
  - Deterministic fixes are conservative and aim to eliminate OWL2-DL “non-simple property” eligibility errors,
    plus common parsing blockers (imports, rdf reification triples, unsupported datatypes, etc.).
  - LLM loop uses ROBOT `reason` exit code (0 => coherent) as the stopping condition.
  - ROBOT `explain` is used only to generate evidence for the LLM and to slice the ontology.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import json
import api_utils
import requests
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

# =============================================================================
# CONFIG (edit these values)
# =============================================================================

CONFIG: Dict[str, Any] = {
    # --- Input / output ---
    "INPUT_TTL": r"/Users/nadeen/neon-gpt/neon-gpt-extended-main/results/gpt-4o-ontologies/CHEMINF_gpt_4o.ttl",
    "OUT_DIR": r"/Users/nadeen/Downloads/ontology_repair_out",

    # --- Deterministic fix (HermiT) ---
    "JAVA_EXE": "java",
    "HERMIT_JAR": r"/Users/nadeen/neon-gpt/neon-gpt-extended-main/neon-gpt/jars/HermiT.jar",
    "DISABLE_IMPORTS": True,
    "HERMIT_TIMEOUT_SEC": 240,
    "HERMIT_MAX_LOOPS": 30,

    # --- ROBOT ---
    "ROBOT_JAR": r"/Users/nadeen/neon-gpt/neon-gpt-extended-main/neon-gpt/jars/robot.jar",
    "AUTO_DOWNLOAD_ROBOT_JAR": True,  # downloads robot.jar if missing
    "ROBOT_REASONER": "HermiT",
    "ROBOT_MAX_EXPLANATIONS": 25,

    # --- Slicing ---
    "SLICE_BNODE_DEPTH": 2,

    # --- LLM (OpenRouter) ---
    "OPENROUTER_API_KEY": None,  # if None, will use env var OPENROUTER_API_KEY
    "OPENROUTER_MODEL": "deepseek/deepseek-v3.2-exp",
    "LLM_MAX_ITERATIONS": 25,
    "EVIDENCE_MAX_TRIPLES": 1200,

    # --- Run plan ---
    "RUN_DETERMINISTIC_FIXES": True,
    "RUN_ROBOT_SLICES": True,
    "RUN_LLM_FIXES": True,
}

# Derived paths created under OUT_DIR:
#  - deterministic_fixed.ttl
#  - problem_slices/ (explanation.md, slices, report.json)
#  - llm_fixes/ (patch_*.json, iter_*.ttl, result.json)


# =============================================================================
# Logging
# =============================================================================

def log(msg: str) -> None:
    print(msg, flush=True)


def short(s: str, n: int = 2000) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n] + "\n... [truncated] ..."


# =============================================================================
# Subprocess helper
# =============================================================================

def run_cmd(cmd: List[str], *, timeout_sec: Optional[int] = None) -> Tuple[int, str, str]:
    """Run command and return (rc, stdout, stderr)."""
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    return p.returncode, (p.stdout or ""), (p.stderr or "")


# =============================================================================
# RDF I/O helpers
# =============================================================================

def load_turtle_graph(ttl_path: Path) -> Graph:
    g = Graph()
    g.parse(ttl_path.as_posix(), format="turtle")
    return g


def write_graph_as_turtle(g: Graph, ttl_path: Path) -> None:
    ttl_path.parent.mkdir(parents=True, exist_ok=True)
    ttl_path.write_text(g.serialize(format="turtle"), encoding="utf-8")


def write_graph_as_owlxml(g: Graph, owl_path: Path) -> None:
    owl_path.parent.mkdir(parents=True, exist_ok=True)
    owl_path.write_text(g.serialize(format="xml"), encoding="utf-8")


def clone_graph(g: Graph) -> Graph:
    g2 = Graph()
    for t in g:
        g2.add(t)
    return g2


def strip_owl_imports(g: Graph) -> Tuple[Graph, int]:
    """Remove owl:imports triples (useful for local debugging without fetching imports)."""
    g2 = clone_graph(g)
    removed = 0
    for s, o in list(g2.subject_objects(OWL.imports)):
        g2.remove((s, OWL.imports, o))
        removed += 1
    return g2, removed


# =============================================================================
# Deterministic repairs
# =============================================================================

DATE_LEX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([zZ]|[+-]\d{2}:\d{2})?$")

def deterministic_fix_xsd_date_to_datetime(g: Graph) -> Tuple[int, str]:
    """
    Deterministically converts:
      - any object URIRef == xsd:date  --> xsd:dateTime
      - any Literal with datatype xsd:date --> xsd:dateTime, lexical normalized to YYYY-MM-DDT00:00:00(+/-TZ|Z)
    """
    changed = 0

    # 1) Replace URI object xsd:date with xsd:dateTime everywhere
    triples_to_replace = [(s, p, o) for (s, p, o) in g if isinstance(o, URIRef) and o == XSD.date]
    for s, p, o in triples_to_replace:
        g.remove((s, p, o))
        g.add((s, p, XSD.dateTime))
        changed += 1

    # 2) Replace literals typed as xsd:date -> xsd:dateTime
    lit_triples: List[Tuple[Any, Any, Literal]] = []
    for s, p, o in g:
        if isinstance(o, Literal) and o.datatype == XSD.date:
            lit_triples.append((s, p, o))

    for s, p, lit in lit_triples:
        lex = str(lit)

        if DATE_LEX_RE.match(lex):
            tz = ""
            if lex.endswith(("Z", "z")):
                base = lex[:-1]
                tz = "Z"
            elif len(lex) > 10 and (lex[10] in "+-"):
                base = lex[:10]
                tz = lex[10:]
            else:
                base = lex[:10]

            new_lex = f"{base}T00:00:00{tz}"
            new_lit = Literal(new_lex, datatype=XSD.dateTime)
        else:
            new_lit = Literal(lex, datatype=XSD.dateTime)

        g.remove((s, p, lit))
        g.add((s, p, new_lit))
        changed += 1

    return changed, f"Converted {changed} xsd:date occurrences to xsd:dateTime (URIs + literals)"


def deterministic_remove_rdf_reification_triples(g: Graph) -> Tuple[int, str]:
    """
    Removes rdf:subject / rdf:predicate / rdf:object triples (RDF reification vocabulary).
    These often cause OWL tools to choke when present as 'junk' in ontology exports.
    """
    changed = 0
    for pred in (RDF.subject, RDF.predicate, RDF.object):
        triples = list(g.triples((None, pred, None)))
        for t in triples:
            g.remove(t)
            changed += 1
    return changed, f"Removed {changed} rdf:subject/rdf:predicate/rdf:object triples"


OWL2_DATATYPE_URIS = {
    str(XSD.string), str(XSD.boolean), str(XSD.decimal), str(XSD.float), str(XSD.double),
    str(XSD.duration), str(XSD.dateTime), str(XSD.time), str(XSD.date),
    str(XSD.gYearMonth), str(XSD.gYear), str(XSD.gMonthDay), str(XSD.gDay), str(XSD.gMonth),
    str(XSD.hexBinary), str(XSD.base64Binary),
    str(XSD.anyURI), str(XSD.QName), str(XSD.NOTATION),
    str(XSD.normalizedString), str(XSD.token), str(XSD.language),
    str(XSD.NMTOKEN), str(XSD.Name), str(XSD.NCName),
    str(XSD.integer), str(XSD.nonPositiveInteger), str(XSD.negativeInteger),
    str(XSD.long), str(XSD.int), str(XSD.short), str(XSD.byte),
    str(XSD.nonNegativeInteger), str(XSD.unsignedLong), str(XSD.unsignedInt),
    str(XSD.unsignedShort), str(XSD.unsignedByte),
    str(XSD.positiveInteger),
}

def deterministic_fix_unsupported_datatypes_to_string(g: Graph) -> Tuple[int, str]:
    """
    Rewrites literals with non-OWL2 datatypes to xsd:string (keeps lexical form).
    Pragmatic "make DL reasoners parse" fix; datatype semantics are lost.
    """
    changed = 0
    bad_examples: List[str] = []
    to_change: List[Tuple[Any, Any, Literal]] = []

    for s, p, o in g:
        if isinstance(o, Literal) and o.datatype is not None:
            dt = str(o.datatype)
            if dt not in OWL2_DATATYPE_URIS:
                to_change.append((s, p, o))

    for s, p, lit in to_change:
        new_lit = Literal(str(lit), datatype=XSD.string)
        g.remove((s, p, lit))
        g.add((s, p, new_lit))
        changed += 1
        if len(bad_examples) < 5 and lit.datatype:
            bad_examples.append(str(lit.datatype))

    if changed == 0:
        return 0, "No unsupported literal datatypes found."

    ex = ", ".join(sorted(set(bad_examples)))
    return changed, f"Rewrote {changed} literals with unsupported datatypes to xsd:string (examples: {ex})"


def deterministic_fix_objectprop_literals_to_annotation(g: Graph) -> Tuple[int, str]:
    """
    If a predicate is used with literal objects but is modeled as an ObjectProperty (or has object-property-only constructs),
    convert it to owl:AnnotationProperty and remove object-only constructs.
    """
    changed = 0

    literal_preds: Set[URIRef] = set()
    for _, p, o in g:
        if isinstance(p, URIRef) and isinstance(o, Literal):
            literal_preds.add(p)

    if not literal_preds:
        return 0, "No predicates used with literals found."

    to_convert: Set[URIRef] = set()
    for p in literal_preds:
        if (p, RDF.type, OWL.ObjectProperty) in g:
            to_convert.add(p)
            continue
        if any(True for _ in g.objects(p, OWL.inverseOf)) or any(True for _ in g.subjects(OWL.inverseOf, p)):
            to_convert.add(p)
            continue
        if any(True for _ in g.objects(p, OWL.propertyChainAxiom)):
            to_convert.add(p)
            continue
        if (p, RDF.type, OWL.TransitiveProperty) in g:
            to_convert.add(p)
            continue

    if not to_convert:
        return 0, "No literal-used predicates appear to be ObjectProperties."

    # Convert
    for p in sorted(to_convert, key=lambda x: str(x)):
        for t in (
            OWL.ObjectProperty, OWL.DatatypeProperty, OWL.FunctionalProperty,
            OWL.InverseFunctionalProperty, OWL.TransitiveProperty,
            OWL.SymmetricProperty, OWL.AsymmetricProperty,
            OWL.ReflexiveProperty, OWL.IrreflexiveProperty,
        ):
            if (p, RDF.type, t) in g:
                g.remove((p, RDF.type, t))
                changed += 1

        if (p, RDF.type, OWL.AnnotationProperty) not in g:
            g.add((p, RDF.type, OWL.AnnotationProperty))
            changed += 1

        for o in list(g.objects(p, OWL.inverseOf)):
            g.remove((p, OWL.inverseOf, o))
            changed += 1
        for s in list(g.subjects(OWL.inverseOf, p)):
            g.remove((s, OWL.inverseOf, p))
            changed += 1

        for chain in list(g.objects(p, OWL.propertyChainAxiom)):
            g.remove((p, OWL.propertyChainAxiom, chain))
            changed += 1

    return changed, f"Converted {len(to_convert)} ObjectProperty-like metadata predicates used with literals to owl:AnnotationProperty; edits={changed}"


# =============================================================================
# HermiT reasoning + non-simple-property deterministic fix loop
# =============================================================================

def hermit_cmd(java_exe: str, hermit_jar: Path, ontology_owl_path: Path) -> List[str]:
    """
    HermiT CLI main class run from the jar as a classpath.
    The flags used here match your original script.
    """
    main_class = "org.semanticweb.HermiT.cli.CommandLine"
    return [
        java_exe,
        "-cp", hermit_jar.as_posix(),
        main_class,
        "--ignoreUnsupportedDatatypes",
        "-k", ontology_owl_path.as_posix(),
    ]


def run_hermit(java_exe: str, hermit_jar: Path, owl_path: Path, *, timeout_sec: int = 240) -> Tuple[Optional[bool], str, str, int]:
    """
    Returns:
      ok=True  => HermiT indicates satisfiable / consistent
      ok=False => HermiT indicates inconsistent / unsatisfiable
      ok=None  => unknown (parse error, other failure, or can't interpret output)
    """
    cmd = hermit_cmd(java_exe, hermit_jar, owl_path)
    rc, out, err = run_cmd(cmd, timeout_sec=timeout_sec)
    blob = (out + "\n" + err).lower()

    if "inconsistentontologyexception" in blob or "inconsistent ontology" in blob:
        return False, out, err, rc
    if "is satisfiable" in blob:
        return True, out, err, rc
    if "unsatisfiable" in blob or "is not satisfiable" in blob:
        return False, out, err, rc

    if rc != 0:
        return None, out, err, rc

    return None, out, err, rc


@dataclass
class HermitIssue:
    kind: str
    details: Dict[str, str]


NON_SIMPLE_IN_CARD_RE = re.compile(
    r"Non-simple property '(<[^>]+>|[^']+)'(?: or its inverse)? appears in the cardinality restriction",
    re.IGNORECASE,
)
NON_SIMPLE_IN_IRREFLEXIVE_RE = re.compile(
    r"Non-simple property '(<[^>]+>|[^']+)'(?: or its inverse)? appears in irreflexive object property axiom",
    re.IGNORECASE,
)

def classify_non_simple_issue(stderr_or_combined: str) -> Optional[HermitIssue]:
    if not stderr_or_combined:
        return None

    m = NON_SIMPLE_IN_CARD_RE.search(stderr_or_combined)
    if m:
        iri = m.group(1).strip()
        iri = iri[1:-1] if iri.startswith("<") and iri.endswith(">") else iri
        return HermitIssue("NON_SIMPLE_PROPERTY_IN_CARDINALITY", {"property_iri": iri})

    m = NON_SIMPLE_IN_IRREFLEXIVE_RE.search(stderr_or_combined)
    if m:
        iri = m.group(1).strip()
        iri = iri[1:-1] if iri.startswith("<") and iri.endswith(">") else iri
        return HermitIssue("NON_SIMPLE_PROPERTY_IN_IRREFLEXIVE", {"property_iri": iri})

    return None


def inverse_props(g: Graph, p: URIRef) -> Set[URIRef]:
    invs: Set[URIRef] = set()
    for o in g.objects(p, OWL.inverseOf):
        if isinstance(o, URIRef):
            invs.add(o)
    for s in g.subjects(OWL.inverseOf, p):
        if isinstance(s, URIRef):
            invs.add(s)
    return invs


def super_props(g: Graph, p: URIRef) -> Set[URIRef]:
    return {o for o in g.objects(p, RDFS.subPropertyOf) if isinstance(o, URIRef)}


def sub_props(g: Graph, p: URIRef) -> Set[URIRef]:
    return {s for s in g.subjects(RDFS.subPropertyOf, p) if isinstance(s, URIRef)}


def related_property_closure(g: Graph, root: URIRef, *, depth: int = 2, limit: int = 500) -> Set[URIRef]:
    """Small closure around root across inverse/sub/super relationships."""
    seen: Set[URIRef] = set()
    frontier: Set[URIRef] = {root}

    for _ in range(depth + 1):
        nxt: Set[URIRef] = set()
        for p in frontier:
            if p in seen:
                continue
            seen.add(p)

            for q in inverse_props(g, p) | super_props(g, p) | sub_props(g, p):
                if q not in seen:
                    nxt.add(q)

            if len(seen) + len(nxt) >= limit:
                return seen.union(nxt)

        frontier = nxt
        if not frontier:
            break

    return seen


def remove_non_simple_causes(g: Graph, props: Set[URIRef]) -> int:
    """
    Remove causes that make a property non-simple:
      - owl:TransitiveProperty type
      - owl:propertyChainAxiom
    """
    removed = 0
    for p in props:
        if (p, RDF.type, OWL.TransitiveProperty) in g:
            g.remove((p, RDF.type, OWL.TransitiveProperty))
            removed += 1

        for chain in list(g.objects(p, OWL.propertyChainAxiom)):
            g.remove((p, OWL.propertyChainAxiom, chain))
            removed += 1

    return removed


def deterministic_fix_non_simple(g: Graph, issue: HermitIssue) -> Tuple[int, str]:
    prop_iri = issue.details["property_iri"]
    root = URIRef(prop_iri)
    props = related_property_closure(g, root, depth=2, limit=500)
    n = remove_non_simple_causes(g, props)
    return n, f"Removed {n} transitive/propertyChain triples across {len(props)} related properties for {prop_iri}"


def run_deterministic_pipeline(
    input_ttl: Path,
    output_ttl: Path,
    *,
    java_exe: str,
    hermit_jar: Path,
    work_dir: Path,
    disable_imports: bool,
    timeout_sec: int,
    max_loops: int,
) -> None:
    """
    Apply deterministic graph edits and run a HermiT loop that removes non-simple-property causes
    when HermiT reports that specific eligibility error pattern.
    """
    log(f"📂 Loading Turtle: {input_ttl}")
    g = load_turtle_graph(input_ttl)
    log(f"✅ Loaded {len(g)} triples")

    if disable_imports:
        g, removed = strip_owl_imports(g)
        log(f"🚫 Removed {removed} owl:imports (reasoning without imports)")

    n_date, desc_date = deterministic_fix_xsd_date_to_datetime(g)
    log(f"🗓️ Date fix: {desc_date}")

    n_meta, desc_meta = deterministic_fix_objectprop_literals_to_annotation(g)
    log(f"🏷️ Metadata property fix: {desc_meta}")

    n_reif, desc_reif = deterministic_remove_rdf_reification_triples(g)
    log(f"🧹 Reification cleanup: {desc_reif}")

    n_dt, desc_dt = deterministic_fix_unsupported_datatypes_to_string(g)
    log(f"🧪 Datatype fix: {desc_dt}")

    work_dir.mkdir(parents=True, exist_ok=True)
    owl_path = work_dir / "ontology_for_hermit.owl"

    for loop in range(1, max_loops + 1):
        write_graph_as_owlxml(g, owl_path)
        ok, out, err, rc = run_hermit(java_exe, hermit_jar, owl_path, timeout_sec=timeout_sec)

        log("\n" + "=" * 70)
        log(f"🔎 HermiT run {loop}/{max_loops} -> ok={ok} rc={rc}")

        if out.strip():
            log("--- HermiT STDOUT (preview) ---")
            log(short(out))
        if err.strip():
            log("--- HermiT STDERR (preview) ---")
            log(short(err))

        if ok is True:
            log("✅ HermiT indicates satisfiable/consistent (for this check).")
            break

        if ok is False:
            log("❌ HermiT reports INCONSISTENT/UNSAT. Deterministic pipeline stops here (by design).")
            break

        issue = classify_non_simple_issue((err or "") + "\n" + (out or ""))
        if not issue:
            log("🛑 HermiT failed for a reason NOT matching 'non-simple property' patterns. Stopping.")
            break

        changed2, desc2 = deterministic_fix_non_simple(g, issue)
        log(f"🛠️ Deterministic fix: {desc2}")
        if changed2 <= 0:
            log("🛑 No triples removed by deterministic non-simple fix. Stopping.")
            break

    write_graph_as_turtle(g, output_ttl)
    log("\n💾 Saved ontology after deterministic fixes:")
    log(f"   {output_ttl}")
    log(f"   triples now: {len(g)}")


# =============================================================================
# ROBOT helpers (download/reason/explain)
# =============================================================================

def ensure_robot_jar(robot_jar: Path, *, auto_download: bool = True) -> Path:
    """
    Ensure ROBOT jar exists locally. Optionally downloads it from GitHub releases.
    """
    robot_jar.parent.mkdir(parents=True, exist_ok=True)
    if robot_jar.exists():
        return robot_jar

    if not auto_download:
        raise FileNotFoundError(f"ROBOT jar not found: {robot_jar}")

    url = "https://github.com/ontodev/robot/releases/latest/download/robot.jar"
    log(f"⬇️ Downloading ROBOT jar to: {robot_jar}")
    rc, out, err = run_cmd(["curl", "-L", url, "-o", robot_jar.as_posix()])
    if rc != 0 or not robot_jar.exists():
        raise RuntimeError(f"Failed to download robot.jar\nstdout:\n{out}\nstderr:\n{err}")
    return robot_jar


def robot_reason_status(
    ontology_path: Path,
    robot_jar: Path,
    *,
    reasoner: str,
) -> Tuple[str, str]:
    """
    Returns (status, diagnostics)
      status ∈ {"coherent", "incoherent", "error"}

    Notes:
      - ROBOT logs may include 'ERROR' even for normal incoherence reporting.
      - Do NOT treat the log level word 'ERROR' as a tool failure.
    """
    with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as tmp:
        out_path = tmp.name

    cmd = [
        "java", "-jar", robot_jar.as_posix(),
        "reason",
        "--input", ontology_path.as_posix(),
        "--reasoner", reasoner,
        "--output", out_path,
    ]
    rc, out, err = run_cmd(cmd)

    try:
        if os.path.exists(out_path):
            os.remove(out_path)
    except OSError:
        pass

    # Keep BOTH streams (sometimes important info is in one or the other)
    diag = (out + "\n" + err).strip()
    lower = diag.lower()

    # Primary truth
    if rc == 0:
        return "coherent", diag

    # First: detect real incoherence messages (these are NOT tool failures)
    incoherent_signals = [
        "the ontology is inconsistent",
        "ontology is inconsistent",
        "unsatisfiable",
        "incoherent",
    ]
    if any(s in lower for s in incoherent_signals):
        return "incoherent", diag

    # Then: detect real tool/runtime failures
    error_signals = [
        "exception",
        "stacktrace",
        "parse",
        "owlapi",
        "failed to",
        "could not",
        "illegalargument",
        "nullpointer",
        "not found",
        "no such file",
        "unsupported",
    ]
    if any(s in lower for s in error_signals):
        return "error", diag

    # If rc!=0 but no clear text, treat as error (safer than claiming incoherent)
    return "error", diag



def robot_explain_markdown(
    ontology_path: Path,
    robot_jar: Path,
    *,
    reasoner: str,
    max_explanations: int,
    unsat_mode: str = "root",
) -> Tuple[str, str]:
    """
    Produce explanation markdown for current incoherence.
    Returns (mode, md) where mode in {"inconsistency","unsatisfiability"}.

    Raises RuntimeError if no markdown produced.
    """
    def explain(mode: str) -> Tuple[bool, str, str]:
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp_md:
            out_md = tmp_md.name
        cmd = [
            "java", "-jar", robot_jar.as_posix(),
            "explain",
            "--input", ontology_path.as_posix(),
            "--reasoner", reasoner,
            "--mode", mode,
            "--max", str(max_explanations),
            "--explanation", out_md,
        ]
        if mode == "unsatisfiability":
            cmd.extend(["--unsatisfiable", unsat_mode])

        rc, out, err = run_cmd(cmd)
        produced = (rc == 0) and os.path.exists(out_md) and os.path.getsize(out_md) > 0
        md = pathlib_read_text(out_md) if produced else ""
        diag = textwrap.dedent(f"""
        Command:
          {' '.join(cmd)}
        Return code: {rc}
        STDOUT:
        {out.strip()}
        STDERR:
        {err.strip()}
        """).strip()

        try:
            if os.path.exists(out_md):
                os.remove(out_md)
        except OSError:
            pass

        return produced, md, diag

    produced, md, d1 = explain("inconsistency")
    if produced:
        return "inconsistency", md

    produced2, md2, d2 = explain("unsatisfiability")
    if produced2:
        return "unsatisfiability", md2

    msg = f"""
❌ ROBOT could not produce explanation markdown.

--- inconsistency attempt ---
{d1}

--- unsatisfiability attempt ---
{d2}
"""
    raise RuntimeError(textwrap.dedent(msg))


def pathlib_read_text(path_str: str) -> str:
    return Path(path_str).read_text(encoding="utf-8")


# =============================================================================
# Slice extraction from ROBOT explanations
# =============================================================================

@dataclass
class JustificationBlock:
    title: str
    axiom_lines: List[str]
    iris: Set[str]


_IRI_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

def parse_justification_blocks(md: str) -> List[JustificationBlock]:
    """
    Extract blocks:
      ## ... ##
        - axiom...
        - axiom...
    """
    cut = md.split("\n# Axiom Impact", 1)[0]
    lines = cut.splitlines()

    blocks: List[JustificationBlock] = []
    current_title: Optional[str] = None
    current_axioms: List[str] = []

    def flush() -> None:
        nonlocal current_title, current_axioms
        if current_title and current_axioms:
            iris: Set[str] = set()
            for ax in current_axioms:
                for iri in _IRI_LINK_RE.findall(ax):
                    iris.add(iri)
            blocks.append(JustificationBlock(current_title.strip(), current_axioms[:], iris))
        current_title = None
        current_axioms = []

    for ln in lines:
        if ln.startswith("## ") and ln.endswith(" ##"):
            flush()
            current_title = ln.strip("# ").strip()
        elif ln.strip().startswith("- "):
            current_axioms.append(ln.strip()[2:].strip())

    flush()
    return blocks


def slice_graph(
    g: Graph,
    seed_iris: Set[str],
    *,
    bnode_depth: int = 2,
    include_schema_about_seeds: bool = True,
) -> Graph:
    """
    Create a subgraph around IRIs from a justification:
      - add triples where subject or object is a seed IRI
      - expand connected blank nodes up to depth
      - optionally add a few schema-level predicates around seeds
    """
    seeds = {URIRef(u) for u in seed_iris if u.startswith(("http://", "https://"))}

    out = Graph()
    out.namespace_manager = g.namespace_manager

    frontier: Set[Any] = set(seeds)
    seen: Set[Any] = set()

    def add_triple(t: Tuple[Any, Any, Any]) -> None:
        out.add(t)

    for s, p, o in g:
        if s in seeds or o in seeds:
            add_triple((s, p, o))
            if isinstance(s, BNode):
                frontier.add(s)
            if isinstance(o, BNode):
                frontier.add(o)

    depth = 0
    while depth < bnode_depth:
        new_frontier: Set[Any] = set()
        for node in list(frontier):
            if node in seen:
                continue
            seen.add(node)

            for s, p, o in g.triples((node, None, None)):
                add_triple((s, p, o))
                if isinstance(o, BNode) and o not in seen:
                    new_frontier.add(o)

            for s, p, o in g.triples((None, None, node)):
                add_triple((s, p, o))
                if isinstance(s, BNode) and s not in seen:
                    new_frontier.add(s)

        frontier = new_frontier
        depth += 1

    if include_schema_about_seeds:
        schema_preds = {
            RDF.type, RDFS.subClassOf, RDFS.domain, RDFS.range,
            OWL.disjointWith, OWL.equivalentClass, OWL.equivalentProperty,
            OWL.inverseOf, OWL.propertyChainAxiom,
        }
        for u in seeds:
            for p in schema_preds:
                for t in g.triples((u, p, None)):
                    add_triple(t)
                for t in g.triples((None, p, u)):
                    add_triple(t)

    return out


def extract_problem_slices(
    ontology_path: Path,
    robot_jar: Path,
    *,
    output_dir: Path,
    reasoner: str,
    max_explanations: int,
    bnode_depth: int,
) -> Dict[str, Any]:
    """
    Produces:
      - explanation.md
      - slice_001.ttl ... slice_NNN.ttl
      - report.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    mode, md = robot_explain_markdown(
        ontology_path,
        robot_jar,
        reasoner=reasoner,
        max_explanations=max_explanations,
        unsat_mode="root",
    )

    md_path = output_dir / "explanation.md"
    md_path.write_text(md, encoding="utf-8")

    blocks = parse_justification_blocks(md)
    g = load_turtle_graph(ontology_path)

    slice_files: List[str] = []
    for i, blk in enumerate(blocks, start=1):
        sg = slice_graph(g, blk.iris, bnode_depth=bnode_depth)
        out_path = output_dir / f"slice_{i:03d}.ttl"
        write_graph_as_turtle(sg, out_path)
        slice_files.append(str(out_path.resolve()))

    all_iris: Set[str] = set()
    all_axioms: List[str] = []
    for blk in blocks:
        all_iris |= blk.iris
        all_axioms.extend(blk.axiom_lines)

    report = {
        "mode": mode,
        "num_justification_blocks": len(blocks),
        "max_explanations_requested": max_explanations,
        "unique_iris_mentioned": len(all_iris),
        "axiom_lines_total": len(all_axioms),
        "axiom_lines_unique": len(set(all_axioms)),
        "output_dir": str(output_dir.resolve()),
        "explanation_markdown": str(md_path.resolve()),
        "slice_files": slice_files,
        "blocks": [
            {
                "index": i + 1,
                "title": blk.title,
                "num_axioms": len(blk.axiom_lines),
                "num_iris": len(blk.iris),
                "iris": sorted(list(blk.iris))[:30],
            }
            for i, blk in enumerate(blocks)
        ],
    }

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    log(f"✅ ROBOT explain mode: {mode}")
    log(f"✅ Justification blocks extracted: {len(blocks)}")
    log(f"✅ Unique IRIs mentioned: {len(all_iris)}")
    log(f"✅ Wrote slices to: {output_dir.resolve()}")
    return report


def load_problem_iris(report_json_path: Path) -> Set[str]:
    report = json.loads(report_json_path.read_text(encoding="utf-8"))
    iris: Set[str] = set()
    for blk in report.get("blocks", []):
        for iri in blk.get("iris", []):
            iris.add(iri)
    return iris


# =============================================================================
# LLM patch loop (OpenRouter)
# =============================================================================

def build_targeted_evidence(
    ontology_path: Path,
    target_iris: Set[str],
    *,
    max_triples: int,
) -> str:
    g = load_turtle_graph(ontology_path)
    targets = {URIRef(u) for u in target_iris if u.startswith(("http://", "https://"))}

    hits: List[Tuple[Any, Any, Any]] = []
    for s, p, o in g:
        if (s in targets) or (p in targets) or (o in targets):
            hits.append((s, p, o))
            if len(hits) >= max_triples:
                break

    def term(t: Any) -> str:
        if isinstance(t, URIRef):
            return f"<{str(t)}>"
        if isinstance(t, BNode):
            return f"_:{str(t)}"
        if isinstance(t, Literal):
            if t.datatype:
                return f"\"{t}\"^^<{t.datatype}>"
            if t.language:
                return f"\"{t}\"@{t.language}"
            return f"\"{t}\""
        return str(t)

    return "\n".join(f"{term(s)} {term(p)} {term(o)} ." for (s, p, o) in hits)



_JSON_OBJ_RE = re.compile(r"(\{.*\})", re.DOTALL)

def openrouter_chat_json(*, prompt: str, step_name: str) -> dict:
    """
    Uses api_utils.send_prompt() (unchanged) to call OpenRouter and returns parsed JSON dict.

    api_utils.send_prompt() returns the extracted content between markers if present,
    otherwise it returns the full reply. We parse JSON from that string.
    """
    # IMPORTANT: persona must force output markers and JSON-only content.
    persona = (
        "You are an ontology debugging assistant.\n"
        "Output ONLY JSON between ###start_output### and ###end_output###.\n"
        "No text outside markers. No markdown fences."
    )

    text = api_utils.send_prompt(
        prompt=prompt,
        persona=persona,
        step_name=step_name,
        max_retries=3,
        wait_time=20,
    )

    if text is None:
        raise RuntimeError("api_utils.send_prompt returned None (request failed).")

    text = text.strip()

    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: try to find a JSON object inside the text
        m = _JSON_OBJ_RE.search(text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Model output wasn't valid JSON even after extraction. step={step_name}\n"
                    f"Parse error: {e}\n"
                    f"Preview:\n{text[:1500]}"
                )
        raise ValueError(
            f"Model output did not contain a JSON object. step={step_name}\n"
            f"Preview:\n{text[:1500]}"
        )


def _to_node(x: Any):
    if isinstance(x, dict) and "literal" in x:
        lit = x["literal"]
        dt = x.get("datatype")
        lang = x.get("lang")
        if dt:
            return Literal(lit, datatype=URIRef(dt))
        if lang:
            return Literal(lit, lang=lang)
        return Literal(lit)

    if isinstance(x, str):
        if x.startswith("_:"):
            return BNode(x[2:])
        if x.startswith(("http://", "https://")):
            return URIRef(x)
        return Literal(x)

    raise ValueError(f"Unsupported node: {x}")


def validate_patch_one_op(patch: Dict[str, Any]) -> None:
    if not isinstance(patch, dict):
        raise ValueError("Patch must be a JSON object.")
    ops = patch.get("operations")
    if not isinstance(ops, list) or len(ops) != 1:
        raise ValueError("Patch must contain exactly 1 operation.")

    op = ops[0]
    if not isinstance(op, dict):
        raise ValueError("Operation must be an object.")
    typ = op.get("op")
    if typ not in ("delete_triple", "add_triple", "replace_triple"):
        raise ValueError(f"Unsupported operation: {typ}")

    if typ in ("delete_triple", "add_triple"):
        t = op.get("triple")
        if not isinstance(t, dict):
            raise ValueError("Missing 'triple' for add/delete.")
        for k in ("s", "p", "o"):
            if k not in t:
                raise ValueError(f"Triple missing key: {k}")

    if typ == "replace_triple":
        oldt = op.get("old")
        newt = op.get("new")
        if not isinstance(oldt, dict) or not isinstance(newt, dict):
            raise ValueError("replace_triple requires 'old' and 'new'.")
        for side, t in [("old", oldt), ("new", newt)]:
            for k in ("s", "p", "o"):
                if k not in t:
                    raise ValueError(f"{side} triple missing key: {k}")


def apply_patch_to_ttl(in_ttl: Path, out_ttl: Path, patch: Dict[str, Any]) -> None:
    validate_patch_one_op(patch)
    g = load_turtle_graph(in_ttl)

    op = patch["operations"][0]
    typ = op["op"]

    if typ in ("delete_triple", "add_triple"):
        t = op["triple"]
        s = _to_node(t["s"])
        p = _to_node(t["p"])
        o = _to_node(t["o"])
        if typ == "delete_triple":
            g.remove((s, p, o))
        else:
            g.add((s, p, o))

    elif typ == "replace_triple":
        oldt = op["old"]
        newt = op["new"]
        os_ = _to_node(oldt["s"]); op_ = _to_node(oldt["p"]); oo_ = _to_node(oldt["o"])
        ns_ = _to_node(newt["s"]); np_ = _to_node(newt["p"]); no_ = _to_node(newt["o"])
        g.remove((os_, op_, oo_))
        g.add((ns_, np_, no_))

    write_graph_as_turtle(g, out_ttl)





def make_prompt(*, explanation_md: str, evidence: str, target_iris: Set[str]) -> str:
    iris_list = "\n".join(sorted(list(target_iris))[:200])
    return f"""
You are fixing an OWL ontology that is logically incoherent (inconsistent and/or has unsatisfiable classes).

You MUST propose EXACTLY ONE minimal patch edit (1 operation) that improves coherence.
You are ONLY allowed to edit axioms/triples that mention one of the "Target IRIs" below.
Do NOT propose broad deletions. Prefer removing a problematic property characteristic, or adjusting a domain/range/disjointness,
or changing one assertion that triggers the proof.

Return STRICT JSON ONLY, matching this schema:

###start_output###
{{
  "operations": [
    {{
      "op": "delete_triple" | "add_triple" | "replace_triple",
      "triple": {{"s": "...", "p": "...", "o": "..."}}
      // if replace_triple:
      // "old": {{"s":"...","p":"...","o":"..."}},
      // "new": {{"s":"...","p":"...","o":"..."}}
    }}
  ],
  "rationale": "1-3 sentences"
}}
###end_output###

ROBOT explanation:
{explanation_md}

Target IRIs (only edit these):
{iris_list}

Evidence triples touching Target IRIs:
{evidence}
""".strip()

def llm_fix_by_target_iris(
    *,
    ontology_path: Path,
    report_json_path: Path,
    robot_jar: Path,
    out_dir: Path,
    reasoner: str,
    max_robot_explanations: int,
    max_iterations: int,
    evidence_max_triples: int,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    target_iris = load_problem_iris(report_json_path)
    history: List[Dict[str, Any]] = []
    current_onto = ontology_path

    system = "You are an ontology debugging assistant. Output STRICT JSON only."

    for it in range(1, max_iterations + 1):
        status, diag = robot_reason_status(current_onto, robot_jar, reasoner=reasoner)
        if status == "coherent":
            result = {
                "status": "coherent",
                "iterations": it - 1,
                "final_ontology": str(current_onto.resolve()),
                "history": history,
                "latest_robot_diagnostics": diag,
                "target_iris_count": len(target_iris),
            }
            return result

        if status == "error":
            result = {
                "status": "robot_reason_error",
                "iterations": it - 1,
                "final_ontology": str(current_onto.resolve()),
                "history": history,
                "latest_robot_diagnostics": diag,
                "target_iris_count": len(target_iris),
            }
            return result

        mode, md = robot_explain_markdown(
            current_onto, robot_jar,
            reasoner=reasoner,
            max_explanations=max_robot_explanations,
        )

        evidence = build_targeted_evidence(current_onto, target_iris, max_triples=evidence_max_triples)
        prompt = make_prompt(explanation_md=md, evidence=evidence, target_iris=target_iris)

        patch = openrouter_chat_json(
            prompt=prompt,
            step_name=f"patch_{it:03d}"
            )
        patch_path = out_dir / f"patch_{it:03d}.json"
        patch_path.write_text(json.dumps(patch, indent=2), encoding="utf-8")

        next_onto = out_dir / f"iter_{it:03d}.ttl"
        apply_patch_to_ttl(current_onto, next_onto, patch)

        history.append({
            "iteration": it,
            "robot_explain_mode": mode,
            "patch_path": str(patch_path.resolve()),
            "ontology_path": str(next_onto.resolve()),
            "rationale": patch.get("rationale", ""),
            "operations": patch.get("operations", []),
            "robot_reason_diagnostics_before": diag,
        })

        current_onto = next_onto

    status, diag = robot_reason_status(current_onto, robot_jar, reasoner=reasoner)

    return {
        "status": "coherent" if status == "coherent" else ("robot_reason_error" if status == "error" else "max_iterations_reached"),
        "iterations": max_iterations,
        "final_ontology": str(current_onto.resolve()),
        "history": history,
        "latest_robot_diagnostics": diag,
        "target_iris_count": len(target_iris),
    }



# =============================================================================
# Main orchestration
# =============================================================================

def main() -> None:
    out_dir = Path(CONFIG["OUT_DIR"]).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    input_ttl = Path(CONFIG["INPUT_TTL"]).expanduser().resolve()
    if not input_ttl.exists():
        raise FileNotFoundError(f"INPUT_TTL not found: {input_ttl}")

    java_exe = str(CONFIG["JAVA_EXE"])
    hermit_jar = Path(CONFIG["HERMIT_JAR"]).expanduser().resolve()
    robot_jar = Path(CONFIG["ROBOT_JAR"]).expanduser().resolve()

    if CONFIG["RUN_DETERMINISTIC_FIXES"]:
        if not hermit_jar.exists():
            raise FileNotFoundError(f"HERMIT_JAR not found: {hermit_jar}")

        deterministic_out = out_dir / "deterministic_fixed.ttl"
        work_dir = out_dir / ".work_hermit"

        run_deterministic_pipeline(
            input_ttl=input_ttl,
            output_ttl=deterministic_out,
            java_exe=java_exe,
            hermit_jar=hermit_jar,
            work_dir=work_dir,
            disable_imports=bool(CONFIG["DISABLE_IMPORTS"]),
            timeout_sec=int(CONFIG["HERMIT_TIMEOUT_SEC"]),
            max_loops=int(CONFIG["HERMIT_MAX_LOOPS"]),
        )
        current_for_robot = deterministic_out
    else:
        current_for_robot = input_ttl

    # ROBOT jar
    robot_jar = ensure_robot_jar(robot_jar, auto_download=bool(CONFIG["AUTO_DOWNLOAD_ROBOT_JAR"]))
    log(f"🤖 ROBOT jar: {robot_jar}")

    # If coherent already, stop early
    status, diag = robot_reason_status(current_for_robot, robot_jar, reasoner=str(CONFIG["ROBOT_REASONER"]))
    if status == "coherent":
        log("✅ Ontology is already COHERENT after deterministic stage.")
        return
    elif status == "error":
        log("⚠️ ROBOT failed to reason over the ontology (tool/runtime issue).")
        if diag:
            log("\n--- ROBOT diagnostics (reason) ---\n")
            log(short(diag))
        # At this point, 'explain' may also fail. Better to stop early.
        return
    else:
        log("❌ Ontology is INCOHERENT after deterministic stage.")
        if diag:
            log("\n--- ROBOT diagnostics (reason) ---\n")
            log(short(diag))


    # Slice extraction
    slices_dir = out_dir / "problem_slices"
    report = None
    if CONFIG["RUN_ROBOT_SLICES"]:
        report = extract_problem_slices(
            ontology_path=current_for_robot,
            robot_jar=robot_jar,
            output_dir=slices_dir,
            reasoner=str(CONFIG["ROBOT_REASONER"]),
            max_explanations=int(CONFIG["ROBOT_MAX_EXPLANATIONS"]),
            bnode_depth=int(CONFIG["SLICE_BNODE_DEPTH"]),
        )
    report_json = slices_dir / "report.json"
    if not report_json.exists():
        raise FileNotFoundError(f"Expected report.json at {report_json} (set RUN_ROBOT_SLICES=True)")

    # LLM fix loop
    if CONFIG["RUN_LLM_FIXES"]:
        # If using api_utils, the key is managed there (hardcoded in api_utils.py).
        # We still allow CONFIG/env override, but we don't require it.
        api_key = CONFIG["OPENROUTER_API_KEY"] or os.environ.get("OPENROUTER_API_KEY")
        if api_key:
            log("🔑 Using OpenRouter API key from CONFIG/env (but api_utils will still use its own API_KEY unless you change api_utils).")
        else:
            log("🔑 No OPENROUTER_API_KEY provided to pipeline. Using api_utils.API_KEY as-is.")

        llm_dir = out_dir / "llm_fixes"
        result = llm_fix_by_target_iris(
            ontology_path=current_for_robot,
            report_json_path=report_json,
            robot_jar=robot_jar,
            out_dir=llm_dir,
            reasoner=str(CONFIG["ROBOT_REASONER"]),
            max_robot_explanations=int(CONFIG["ROBOT_MAX_EXPLANATIONS"]),
            max_iterations=int(CONFIG["LLM_MAX_ITERATIONS"]),
            evidence_max_triples=int(CONFIG["EVIDENCE_MAX_TRIPLES"]),
        )
        (llm_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        log("\n✅ LLM loop finished. Result saved to llm_fixes/result.json")
        log(json.dumps(result, indent=2))
    else:
        log("ℹ️ RUN_LLM_FIXES=False; skipping LLM repair loop.")


if __name__ == "__main__":
    main()