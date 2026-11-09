#!/usr/bin/env python3
"""
Automatic Publication Updater for Robin Burchard (rburchard.github.io)
Fetches and merges works from:
1. ORCID Public API (0000-0002-4130-5287)
2. OpenAlex API (Author ID: A5084607935)
3. CrossRef API (for full author lists / venue enrichment when needed)

Writes static JSON to `data/publications.json` so the website loads with
zero external tracking requests (100% GDPR compliant).
"""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ORCID_ID = "0000-0002-4130-5287"
OPENALEX_AUTHOR_ID = "A5084607935"
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "publications.json")
PINNED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "pinned.json")

HEADERS = {
    "User-Agent": "RobinBurchardAcademicSite/1.0 (https://rburchard.github.io; mailto:robin.burchard@uni-siegen.de)",
    "Accept": "application/json",
}


def fetch_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_title(title: str) -> str:
    if not title:
        return ""
    # Replace non-alphanumeric with empty string for fuzzy deduplication
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def clean_text(text: str) -> str:
    if not text:
        return ""
    # Replace non-breaking spaces and collapse whitespace
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_doi(doi: str) -> str:
    if not doi:
        return ""
    doi = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi.strip()


def make_bibtex_key(authors: list, year, title: str) -> str:
    first_author = "burchard"
    if authors:
        parts = authors[0].strip().split()
        if parts:
            first_author = re.sub(r"[^a-z]", "", parts[-1].lower()) or "burchard"
    words = [w for w in re.findall(r"[a-zA-Z]+", (title or "").lower()) if len(w) > 3 and w not in {"with", "from", "using", "through", "into", "over", "under"}]
    first_word = words[0] if words else "paper"
    return f"{first_author}{year}{first_word}"


def generate_bibtex(work: dict) -> str:
    if work.get("bibtex"):
        return work["bibtex"]
    wtype = work.get("type", "conference-paper")
    entry_type = "article" if wtype in ("journal-article", "preprint") else ("incollection" if wtype == "book-chapter" else "inproceedings")
    key = make_bibtex_key(work.get("authors", []), work.get("year", ""), work.get("title", ""))
    authors_str = " and ".join(work.get("authors") or ["Robin Burchard"])
    lines = [
        f"@{entry_type}{{{key},",
        f"  title = {{{work.get('title', '')}}},",
        f"  author = {{{authors_str}}},",
        f"  year = {{{work.get('year', '')}}},",
    ]
    venue = work.get("venue")
    if venue:
        field = "journal" if entry_type == "article" else "booktitle"
        lines.append(f"  {field} = {{{venue}}},")
    if work.get("doi"):
        lines.append(f"  doi = {{{work['doi']}}},")
    elif work.get("url"):
        lines.append(f"  url = {{{work['url']}}},")
    lines.append("}")
    return "\n".join(lines)


def map_work_type(raw_type: str, venue: str = "") -> str:
    raw = (raw_type or "").lower()
    v_low = (venue or "").lower()
    if "preprint" in raw or "arxiv" in v_low or "corr" in v_low:
        return "preprint"
    if "journal" in raw or "article" in raw:
        if "proceedings" in v_low or "conference" in v_low or "workshop" in v_low or "ubicomp" in v_low or "iwoar" in v_low:
            return "conference-paper"
        return "journal-article"
    if "book-chapter" in raw or "chapter" in raw:
        return "book-chapter"
    return "conference-paper"


def fetch_openalex_works() -> list:
    url = f"https://api.openalex.org/works?filter=author.id:{OPENALEX_AUTHOR_ID}&per-page=100&sort=publication_year:desc"
    try:
        data = fetch_json(url)
    except Exception as e:
        print(f"[WARN] OpenAlex fetch failed: {e}")
        return []

    works = []
    for item in data.get("results", []):
        title = clean_text(item.get("title") or item.get("display_name") or "")
        if not title:
            continue
        year = item.get("publication_year") or 0
        doi = normalize_doi(item.get("doi") or "")
        authors = []
        for auth in item.get("authorships", []):
            name = (auth.get("author") or {}).get("display_name") or auth.get("raw_author_name")
            if name:
                authors.append(clean_text(name))
        loc = item.get("primary_location") or {}
        src = loc.get("source") or {}
        venue = clean_text(src.get("display_name") or "")
        raw_type = item.get("type") or item.get("type_crossref") or ""
        wtype = map_work_type(raw_type, venue)

        landing_url = loc.get("landing_page_url") or (f"https://doi.org/{doi}" if doi else "")
        pdf_url = loc.get("pdf_url") or ((item.get("open_access") or {}).get("oa_url") or "")

        works.append({
            "title": title,
            "year": int(year) if year else 0,
            "authors": authors,
            "venue": venue,
            "type": wtype,
            "doi": doi,
            "url": landing_url,
            "pdf_url": pdf_url,
            "source": "openalex",
            "openalex_id": item.get("id", ""),
        })
    return works


def fetch_orcid_works() -> list:
    url = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"
    try:
        data = fetch_json(url)
    except Exception as e:
        print(f"[WARN] ORCID summary fetch failed: {e}")
        return []

    works = []
    for group in data.get("group", []):
        summaries = group.get("work-summary", [])
        if not summaries:
            continue
        summary = summaries[0]
        put_code = summary.get("put-code")
        title = clean_text(((summary.get("title") or {}).get("title") or {}).get("value") or "")
        year_str = (((summary.get("publication-date") or {}).get("year") or {}).get("value")) or "0"
        year = int(year_str) if str(year_str).isdigit() else 0
        raw_type = summary.get("type") or "conference-paper"
        venue = clean_text((summary.get("journal-title") or {}).get("value") or "")

        doi = ""
        ext_url = ((summary.get("url") or {}).get("value")) or ""
        for ext in ((summary.get("external-ids") or {}).get("external-id") or []):
            if ext.get("external-id-type") == "doi":
                doi = normalize_doi(ext.get("external-id-value") or "")
                break

        authors = []
        # Fetch full work details from ORCID for contributors & citation
        if put_code:
            try:
                detail = fetch_json(f"https://pub.orcid.org/v3.0/{ORCID_ID}/work/{put_code}")
                contributors = ((detail.get("contributors") or {}).get("contributor") or [])
                for c in contributors:
                    cname = ((c.get("credit-name") or {}).get("value"))
                    if cname:
                        authors.append(clean_text(cname))
                if not venue:
                    venue = clean_text((detail.get("journal-title") or {}).get("value") or "")
            except Exception as e:
                print(f"[WARN] ORCID detail fetch failed for {put_code}: {e}")

        wtype = map_work_type(raw_type, venue)
        works.append({
            "title": title,
            "year": year,
            "authors": authors,
            "venue": venue,
            "type": wtype,
            "doi": doi,
            "url": f"https://doi.org/{doi}" if doi else ext_url,
            "pdf_url": "",
            "source": "orcid",
            "put_code": put_code,
        })
    return works


def enrich_from_crossref(work: dict):
    doi = work.get("doi")
    if not doi or (work.get("authors") and work.get("venue")):
        return
    try:
        url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
        data = fetch_json(url).get("message", {})
        if not work.get("authors"):
            authors = []
            for a in data.get("author", []):
                given = a.get("given", "")
                family = a.get("family", "")
                full = f"{given} {family}".strip()
                if full:
                    authors.append(clean_text(full))
            if authors:
                work["authors"] = authors
        if not work.get("venue"):
            containers = data.get("container-title") or []
            if containers:
                work["venue"] = clean_text(containers[0])
    except Exception:
        pass


def merge_publications(orcid_works: list, openalex_works: list, pinned_list: list) -> list:
    merged_by_key = {}

    def add_or_merge(item: dict):
        title_norm = normalize_title(item.get("title", ""))
        doi = normalize_doi(item.get("doi", ""))

        # Find existing match by DOI or normalized title
        existing_key = None
        for k, v in merged_by_key.items():
            if doi and v.get("doi") and doi == v.get("doi"):
                existing_key = k
                break
            if title_norm and normalize_title(v.get("title", "")) == title_norm:
                existing_key = k
                break

        if not existing_key:
            key = doi or title_norm
            if key:
                merged_by_key[key] = dict(item)
            return

        target = merged_by_key[existing_key]
        # Prefer richer fields
        if (item.get("year") or 0) > (target.get("year") or 0):
            target["year"] = item["year"]
        if len(item.get("authors") or []) > len(target.get("authors") or []):
            target["authors"] = item["authors"]
        if item.get("venue") and (not target.get("venue") or len(item["venue"]) < len(target["venue"]) or "corr" in target["venue"].lower()):
            target["venue"] = item["venue"]
        if item.get("doi") and not target.get("doi"):
            target["doi"] = item["doi"]
        if item.get("url") and not target.get("url"):
            target["url"] = item["url"]
        if item.get("pdf_url") and not target.get("pdf_url"):
            target["pdf_url"] = item["pdf_url"]
        if item.get("put_code"):
            target["put_code"] = item["put_code"]
        if item.get("type") and target.get("type") == "preprint" and item["type"] != "preprint":
            if "arxiv" not in (target.get("venue") or "").lower():
                target["type"] = item["type"]

    # First add ORCID (authoritative user-curated record)
    for w in orcid_works:
        add_or_merge(w)

    # Next merge OpenAlex (adds full author lists, open access links, and preprints like HARMES)
    for w in openalex_works:
        add_or_merge(w)

    # Ensure all pinned items exist and enrich them
    for p in pinned_list:
        add_or_merge({
            "title": p.get("title"),
            "year": p.get("year"),
            "authors": p.get("authors", []),
            "venue": p.get("venue", ""),
            "type": p.get("type", "journal-article"),
            "doi": normalize_doi(p.get("doi", "")),
            "url": (p.get("links") or [{}])[0].get("url", ""),
            "bibtex": p.get("bibtex", ""),
        })

    results = list(merged_by_key.values())

    # CrossRef fallback enrichment and BibTeX generation
    for idx, work in enumerate(results):
        enrich_from_crossref(work)
        if not work.get("authors"):
            work["authors"] = ["Robin Burchard"]
        # Fix common OpenAlex typo in Jürgen Gall
        work["authors"] = [a.replace("Jüergen Gall", "Jürgen Gall") for a in work["authors"]]
        # Clean up venue capitalization and verbose strings
        if work.get("venue"):
            if "Lecture Notes in Computer Science Including Subseries" in work["venue"] or work["venue"].lower() == "lecture notes in computer science":
                work["venue"] = "Lecture Notes in Computer Science (Springer)"
            elif "Ubicomp Iswc 2022 Adjunct Proceedings" in work["venue"]:
                work["venue"] = "ACM UbiComp / ISWC 2022 Adjunct Proceedings"
            elif "arxiv" in work["venue"].lower():
                work["venue"] = "arXiv Preprint"
                work["type"] = "preprint"
        work["bibtex"] = generate_bibtex(work)

    # Sort by year descending, then title
    results.sort(key=lambda x: (-(x.get("year") or 0), x.get("title", "")))
    return results


def main():
    print("Fetching ORCID works...")
    orcid_works = fetch_orcid_works()
    print(f" -> Found {len(orcid_works)} works on ORCID")

    print("Fetching OpenAlex works...")
    openalex_works = fetch_openalex_works()
    print(f" -> Found {len(openalex_works)} works on OpenAlex")

    pinned_list = []
    if os.path.exists(PINNED_PATH):
        with open(PINNED_PATH, "r", encoding="utf-8") as f:
            pinned_list = json.load(f)

    merged = merge_publications(orcid_works, openalex_works, pinned_list)

    # Back-populate pinned.json enriched fields (authors, doi, bibtex, links) if missing
    if pinned_list:
        for p in pinned_list:
            p_norm = normalize_title(p.get("match_title") or p.get("title", ""))
            for m in merged:
                if normalize_title(m.get("title", "")) == p_norm:
                    if not p.get("authors") and m.get("authors"):
                        p["authors"] = m["authors"]
                    if not p.get("doi") and m.get("doi"):
                        p["doi"] = m["doi"]
                    if not p.get("bibtex") and m.get("bibtex"):
                        p["bibtex"] = m["bibtex"]
                    if not p.get("links"):
                        links = []
                        if m.get("doi"):
                            links.append({"label": "DOI / Paper", "url": f"https://doi.org/{m['doi']}", "icon": "doi", "primary": True})
                        elif m.get("url"):
                            links.append({"label": "Paper", "url": m["url"], "icon": "external", "primary": True})
                        if m.get("pdf_url") and m.get("pdf_url") != (f"https://doi.org/{m.get('doi')}" if m.get("doi") else ""):
                            links.append({"label": "PDF", "url": m["pdf_url"], "icon": "pdf"})
                        p["links"] = links
                    break
        with open(PINNED_PATH, "w", encoding="utf-8") as f:
            json.dump(pinned_list, f, indent=2, ensure_ascii=False)

    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "orcid": ORCID_ID,
        "openalex_id": OPENALEX_AUTHOR_ID,
        "count": len(merged),
        "publications": merged,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Successfully wrote {len(merged)} merged publications to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
