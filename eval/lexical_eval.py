#!/usr/bin/env python3

import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from rdflib import Graph, RDF, RDFS, OWL, Namespace
import jellyfish


# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
BASE = "/Users/nadeen/neon-gpt/neon-gpt-extended-main/results"

SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")


# -------------------------------------------------------------------
# Local name extraction
# -------------------------------------------------------------------
def get_local_name(uri: str) -> str:
    uri = str(uri)
    if "#" in uri:
        return uri.split("#")[-1]
    if "/" in uri:
        return uri.split("/")[-1]
    if ":" in uri:
        return uri.split(":")[-1]
    return uri

def make_unique(labels):
    seen = {}
    result = []
    for lbl in labels:
        if lbl not in seen:
            seen[lbl] = 1
            result.append(lbl)
        else:
            seen[lbl] += 1
            result.append(f"{lbl} ({seen[lbl]})")
    return result

# -------------------------------------------------------------------
# Text normalization
# -------------------------------------------------------------------
def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[_\-]', ' ', text)
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return " ".join(text.split())

def truncate_label(label, max_words=3):
    words = label.split()
    return " ".join(words[:max_words])
# -------------------------------------------------------------------
# Detect meaningful vs code-like local names
# -------------------------------------------------------------------
def is_meaningful_local_name(name: str) -> bool:
    pure = re.sub(r'[\d_]', '', name)

    if len(pure) < 3:
        return False

    # CHEMINF_000373, GO:0001234 etc.
    if re.match(r'^[A-Za-z]+[_:]\d+$', name):
        return False

    # All caps or code-like
    if re.match(r'^[A-Z_0-9]+$', name):
        return False

    # A23, B1003...
    if re.match(r'^[A-Za-z]+\d+$', name):
        return False

    return True


# -------------------------------------------------------------------
# BEST lexical representation selector
# -------------------------------------------------------------------
def extract_label(g: Graph, entity):
    local = get_local_name(entity)

    # 1. If local name is meaningful → use it
    if is_meaningful_local_name(local):
        return normalize(local)

    # 2. rdfs:label
    for _, _, lbl in g.triples((entity, RDFS.label, None)):
        return normalize(str(lbl))

    # 3. skos:prefLabel
    for _, _, lbl in g.triples((entity, SKOS.prefLabel, None)):
        return normalize(str(lbl))

    # 4. exact synonyms
    for _, _, lbl in g.triples((entity, OBOINOWL.hasExactSynonym, None)):
        return normalize(str(lbl))

    # 5. fallback → normalized ID
    return normalize(local)

def dedupe_keep_first(labels):
    seen = set()
    out = []
    for lbl in labels:
        if lbl in seen:
            out.append(lbl)  # keep identical label WITHOUT numbering
        else:
            seen.add(lbl)
            out.append(lbl)
    return out


# -------------------------------------------------------------------
# Load ontology entities
# -------------------------------------------------------------------
def load_ontology_entities(path):
    g = Graph()

    ext = path.lower().split('.')[-1]
    format_map = {
        "ttl": "turtle", "rdf": "xml", "owl": "xml", "xml": "xml",
        "nt": "nt", "n3": "n3", "jsonld": "json-ld"
    }

    fmt = format_map.get(ext, None)
    print(f"Loading ontology: {path} (format={fmt or 'auto'})")

    try:
        g.parse(path, format=fmt or "xml")
    except Exception:
        print("⚠️ Format detection failed, trying RDF/XML…")
        g.parse(path, format="xml")

    print(f"Loaded {len(g)} triples.")

    classes = list(g.subjects(RDF.type, RDFS.Class)) + list(g.subjects(RDF.type, OWL.Class))
    props = (
        list(g.subjects(RDF.type, RDF.Property)) +
        list(g.subjects(RDF.type, OWL.ObjectProperty)) +
        list(g.subjects(RDF.type, OWL.DatatypeProperty))
    )

    entities = set(classes + props)

    # BEST lexical names
    labels = {str(e): extract_label(g, e) for e in entities}
    ids = {str(e): get_local_name(e) for e in entities}

    return labels, ids


# -------------------------------------------------------------------
# Main lexical analysis
# -------------------------------------------------------------------
def lexical_analysis(ont1_path, ont2_path, output_dir,
                     ont1_name="Ont1", ont2_name="Ont2",
                     similarity_threshold=0.80):

    os.makedirs(output_dir, exist_ok=True)

    print("\n=== Loading Ontologies ===")

    labels1, ids1 = load_ontology_entities(ont1_path)
    labels2, ids2 = load_ontology_entities(ont2_path)

    gold_labels = set(labels1.values())
    llm_labels = set(labels2.values())

    print(f"{ont1_name}: {len(gold_labels)} entity names")
    print(f"{ont2_name}: {len(llm_labels)} entity names")

    # ---------------- Exact matches ----------------
    exact_label_matches = sorted(list(gold_labels.intersection(llm_labels)))
    print(f"Exact LABEL matches: {len(exact_label_matches)}")

    exact_id_matches = sorted(list(set(ids1.values()).intersection(ids2.values())))
    print(f"Exact ID matches: {len(exact_id_matches)}")

    # ---------------- Hybrid Similarity (Label + Local) ----------------
    gold_map = {}
    for e, lbl in labels1.items():
        gold_map.setdefault(lbl, []).append(e)

    llm_map = {}
    for e, lbl in labels2.items():
        llm_map.setdefault(lbl, []).append(e)

    def all_strings(entity, labels_dict, ids_dict):
        return {
            normalize(labels_dict[entity]),
            normalize(ids_dict[entity])
        }

    similar_pairs = []
    matched_llm_entities = set()

    for llm_label in llm_labels:
        for gold_label in gold_labels:

            best_sim = 0

            for llm_entity in llm_map[llm_label]:
                for gold_entity in gold_map[gold_label]:

                    llm_strings = all_strings(llm_entity, labels2, ids2)
                    gold_strings = all_strings(gold_entity, labels1, ids1)

                    for s2 in llm_strings:
                        for s1 in gold_strings:
                            sim = jellyfish.jaro_winkler_similarity(s1, s2)
                            best_sim = max(best_sim, sim)

            if best_sim >= similarity_threshold:
                similar_pairs.append((gold_label, llm_label, best_sim))
                matched_llm_entities.add(llm_label)

    similar_pairs = sorted(similar_pairs, key=lambda x: x[2], reverse=True)
    print(f"High-similarity (≥{similarity_threshold}) pairs: {len(similar_pairs)}")

    gold_total = len(gold_labels)
    llm_total = len(llm_labels)
    matched_count = len(matched_llm_entities)
    match_pct = (matched_count / llm_total * 100) if llm_total else 0

    print(f"LLM entities with similarity ≥ {similarity_threshold}: "
          f"{matched_count} ({match_pct:.1f}% of LLM entities)")

    # ---------------- Save outputs ----------------
    pd.Series(exact_label_matches).to_csv(
        os.path.join(output_dir, "exact_label_matches.csv"), index=False)

    pd.Series(exact_id_matches).to_csv(
        os.path.join(output_dir, "exact_id_matches.csv"), index=False)

    pd.DataFrame(similar_pairs,
                 columns=[f"{ont1_name}_name", f"{ont2_name}_name", "similarity"]
                 ).to_csv(os.path.join(output_dir, "similarity_pairs.csv"), index=False)

    # ---------------- Heatmap (top 20 non-exact) ----------------
# ---------------- Heatmap (top 20 non-exact) ----------------
    heatmap_pairs = [p for p in similar_pairs if p[2] < 1.0]

    if heatmap_pairs:

        # take EXACT top 20 rows (gold,llm,sim) — keep duplicates
        top = heatmap_pairs[:20]

        # keep all 20 entries even if they duplicate
        raw_gold = dedupe_keep_first([p[0] for p in top])
        raw_llm  = dedupe_keep_first([p[1] for p in top])

        names1_top = [truncate_label(x) for x in raw_gold]
        names2_top = [truncate_label(x) for x in raw_llm]

        #names1_top = make_unique([truncate_label(p[0]) for p in top])    # gold labels (20)
        #names2_top = make_unique([truncate_label(p[1]) for p in top])    # llm labels  (20)

        # build 20 × 20 matrix
        matrix = np.zeros((20, 20))
        for idx, (n1, n2, sim) in enumerate(top):
            matrix[idx][idx] = sim     # diagonal placement

        # annotation matrix (0.0 for empty cells)
        annot = np.array(
            [["0.0" if v == 0 else f"{v:.2f}" for v in row] for row in matrix]
        )


        plt.figure(figsize=(16, 14))

        ax = sns.heatmap(
            matrix,
            annot=annot,
            fmt="",
            cmap="YlGnBu",
            xticklabels=names2_top,
            yticklabels=names1_top,
            cbar=False,
            annot_kws={"fontsize": 15}
        )



        plt.title(f"Top Lexical Similarities:\n{ont1_name} vs {ont2_name}", fontsize=21)
        plt.xticks(rotation=45, ha='right', fontsize=18)
        plt.yticks(rotation=0, fontsize=18)

        fname = f"lexical_{ont2_name}.pdf".replace(" ", "_")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, fname))
        plt.close()


    return {
        "exact_label_matches": exact_label_matches,
        "exact_id_matches": exact_id_matches,
        "similar_pairs": similar_pairs,
        "gold_total": gold_total,
        "llm_total": llm_total,
        "matched_count": matched_count,
        "match_pct": match_pct
    }

# -------------------------------------------------------------------
# DOMAIN / MODEL CONFIG
# -------------------------------------------------------------------
def main():

    domain_config = {
        "Wine": {
            "gold_path": os.path.join(BASE, "gold/wine_gold.rdf"),
            "gold_name": "Wine Gold Standard Ontology",
            "models": {
                "GPT-4o": {
                    "llm_path": os.path.join(BASE, "gpt-4o-ontologies/wine_gpt_4o.ttl"),
                    "llm_name": "Wine GPT-4o",
                    "outdir":  os.path.join(BASE, "lexical/wine_gpt4o"),
                },
                "Mistral": {
                    "llm_path": os.path.join(BASE, "mistral-ontologies/wineMistral.ttl"),
                    "llm_name": "Wine Mistral",
                    "outdir":  os.path.join(BASE, "lexical/wine_mistral"),
                },
                "Llama-4": {
                    "llm_path": os.path.join(BASE, "llama4-ontologies/Wine_llama.ttl"),
                    "llm_name": "Wine Llama4",
                    "outdir":  os.path.join(BASE, "lexical/wine_llama"),
                },
                "DeepSeek": {
                    "llm_path": os.path.join(BASE, "deepseek-ontologies/Wine_deepseek.ttl"),
                    "llm_name": "Wine DeepSeek",
                    "outdir":  os.path.join(BASE, "lexical/wine_deepseek"),
                },
            },
        },

        "Cheminformatics": {
            "gold_path": os.path.join(BASE, "gold/cheminf.owl"),
            "gold_name": "CHEMINF Gold Standard Ontology",
            "models": {
                "GPT-4o": {
                    "llm_path": os.path.join(BASE, "gpt-4o-ontologies/CHEMINF_gpt_4o.ttl"),
                    "llm_name": "Cheminformatics GPT-4o",
                    "outdir":  os.path.join(BASE, "lexical/cheminf_gpt4o"),
                },
                "Mistral": {
                    "llm_path": os.path.join(BASE, "mistral-ontologies/cheminfMistral.ttl"),
                    "llm_name": "Cheminformatics Mistral",
                    "outdir":  os.path.join(BASE, "lexical/cheminf_mistral"),
                },
                "Llama-4": {
                    "llm_path": os.path.join(BASE, "llama4-ontologies/cheminf_llama.ttl"),
                    "llm_name": "Cheminformatics Llama4",
                    "outdir":  os.path.join(BASE, "lexical/cheminf_llama"),
                },
                "DeepSeek": {
                    "llm_path": os.path.join(BASE, "deepseek-ontologies/cheminf_deepseek.ttl"),
                    "llm_name": "Cheminformatics DeepSeek",
                    "outdir":  os.path.join(BASE, "lexical/cheminf_deepseek"),
                },
            },
        },

        # "Environmental Microbiology": {
        #     "gold_path": os.path.join(BASE, "gold/ad-ontology-merged-updated.owl"),
        #     "gold_name": "AquaDiva Gold",
        #     "models": {
        #         "GPT-4o": {
        #             "llm_path": os.path.join(BASE, "gpt-4o-ontologies/AquaDiva.ttl"),
        #             "llm_name": "Environmental Microbiology GPT-4o",
        #             "outdir":  os.path.join(BASE, "lexical/aquadiva_gpt4o"),
        #         },
        #         "Mistral": {
        #             "llm_path": os.path.join(BASE, "mistral-ontologies/aquaDivaMistral.ttl"),
        #             "llm_name": "Environmental Microbiology Mistral",
        #             "outdir":  os.path.join(BASE, "lexical/aquadiva_mistral"),
        #         },
        #         "Llama-4": {
        #             "llm_path": os.path.join(BASE, "llama4-ontologies/aquadiva_llama.ttl"),
        #             "llm_name": "Environmental Microbiology Llama4",
        #             "outdir":  os.path.join(BASE, "lexical/aquadiva_llama"),
        #         },
        #         "DeepSeek": {
        #             "llm_path": os.path.join(BASE, "deepseek-ontologies/aquadiva_deepseek.ttl"),
        #             "llm_name": "Environmental Microbiology DeepSeek",
        #             "outdir":  os.path.join(BASE, "lexical/aquadiva_deepseek"),
        #         },
        #     },
        # },

        # "Sewer Network": {
        #     "gold_path": os.path.join(BASE, "gold/sewernet.owl"),
        #     "gold_name": "SewerNet Gold Standard Ontology",
        #     "models": {
        #         "GPT-4o": {
        #             "llm_path": os.path.join(BASE, "gpt-4o-ontologies/SewerNet_gpt_4o.ttl"),
        #             "llm_name": "Sewer Networks GPT-4o",
        #             "outdir":  os.path.join(BASE, "lexical/sewernet_gpt4o"),
        #         },
        #         "Mistral": {
        #             "llm_path": os.path.join(BASE, "mistral-ontologies/sewerNetMistral.ttl"),
        #             "llm_name": "Sewer Networks Mistral",
        #             "outdir":  os.path.join(BASE, "lexical/sewernet_mistral"),
        #         },
        #         "Llama-4": {
        #             "llm_path": os.path.join(BASE, "llama4-ontologies/sewernet_llama.ttl"),
        #             "llm_name": "Sewer Networks Llama4",
        #             "outdir":  os.path.join(BASE, "lexical/sewernet_llama"),
        #         },
        #         "DeepSeek": {
        #             "llm_path": os.path.join(BASE, "deepseek-ontologies/sewernet_deepseek.ttl"),
        #             "llm_name": "Sewer Networks DeepSeek",
        #             "outdir":  os.path.join(BASE, "lexical/sewernet_deepseek"),
        #         },
        #     },
        # },
    }

    # ---------------------------------------------------------------
    # Run lexical_analysis for all domain/model pairs
    # ---------------------------------------------------------------
    summary = {}
    for domain, cfg in domain_config.items():
        summary[domain] = {}
        gold_path = cfg["gold_path"]
        gold_name = cfg["gold_name"]

        for model, m_cfg in cfg["models"].items():
            res = lexical_analysis(
                gold_path,
                m_cfg["llm_path"],
                m_cfg["outdir"],
                gold_name,
                m_cfg["llm_name"],
                similarity_threshold=0.8
            )
            summary[domain][model] = res

    # ---------------------------------------------------------------
    # Build data matrix for bar chart from summary["..."]["..."]["match_pct"]
    # ---------------------------------------------------------------
    models = ["GPT-4o", "Mistral", "Llama-4", "DeepSeek"]
    domains = list(summary.keys())

    data = np.array([
        [summary[dom][model]["match_pct"] for model in models]
        for dom in domains
    ])

    # ---------------------------------------------------------------
    # Plot grouped bar chart
    # ---------------------------------------------------------------
    plt.figure(figsize=(13, 7))
    x = np.arange(len(domains))
    width = 0.18

    colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B2"]

    for i, model in enumerate(models):
        plt.bar(
            x + (i - 1.5) * width,
            data[:, i],
            width,
            label=model,
            color=colors[i]
        )

    plt.ylabel(
        "Percentage of LLM Entities with ≥ 0.8\nLexical Similarity to Gold Standard Ontology",
        fontsize=16
    )
    plt.xlabel("Domain", fontsize=16)
    plt.title("Lexical Alignment Across LLM-Generated Ontologies", fontsize=22)

    plt.xticks(x, domains, rotation=15, fontsize=18)
    plt.yticks(fontsize=14)
    plt.legend(title="Model", fontsize=18, title_fontsize=22)

    # Add value labels
    for i, model in enumerate(models):
        for xi, yi in zip(x + (i - 1.5) * width, data[:, i]):
            plt.text(
                xi, yi + 1, f"{yi:.1f}%",
                ha='center', va='bottom',
                fontsize=12
            )

    plt.tight_layout()
    bar_out = os.path.join(BASE, "lexical/lexical_alignment.pdf")
    os.makedirs(os.path.dirname(bar_out), exist_ok=True)
    plt.savefig(bar_out, format="pdf", bbox_inches="tight")
    plt.show()

    print("\nSaved bar chart to:", bar_out)


if __name__ == "__main__":
    main()
