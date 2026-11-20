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

import html
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ORCID_ID = "0000-0002-4130-5287"
OPENALEX_AUTHOR_ID = "A5084607935"
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "publications.json")
PINNED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "pinned.json")
EQUAL_FIRST_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "equal_first_author.json")

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


def author_list_quality(authors: list) -> int:
    score = 0
    for a in (authors or []):
        s = (a or "").strip()
        if not s or "," in s:
            continue
        first_tok = s.split()[0].rstrip(".")
        if len(first_tok) > 1:
            score += 1
    return score


def normalize_author_key(name: str) -> str:
    n = (name or "").replace("Jüergen Gall", "Jürgen Gall").strip()
    if "," in n:
        parts = [p.strip() for p in n.split(",", 1)]
        n = f"{parts[1]} {parts[0]}".strip()
    n_ascii = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii").lower()
    tokens = [t.strip(".") for t in re.split(r"[\s\-]+", n_ascii) if t.strip(".")]
    if len(tokens) >= 2:
        tokens = [tokens[0]] + [t for t in tokens[1:-1] if len(t) > 1] + [tokens[-1]]
    return " ".join(tokens)


def clean_text(text: str) -> str:
    if not text:
        return ""
    # Replace non-breaking spaces and collapse whitespace
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_abstract(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    # Strip simple MathJax inline wrappers like \(82\%\) -> 82%
    text = re.sub(r"\\\((.*?)\\\)", r"\1", text)
    text = re.sub(r"\\([%&_#$])", r"\1", text)
    text = clean_text(text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    text = re.sub(r"^abstract\s*[:.]?\s*", "", text, flags=re.I)
    return text


def reconstruct_openalex_abstract(inverted_index) -> str:
    if not isinstance(inverted_index, dict) or not inverted_index:
        return ""
    words = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            words.append((pos, word))
    if not words:
        return ""
    words.sort(key=lambda x: x[0])
    return clean_abstract(" ".join(w for _, w in words))


def normalize_doi(doi: str) -> str:
    if not doi:
        return ""
    doi = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi.strip()


def short_openalex_id(raw_id: str) -> str:
    if not raw_id:
        return ""
    seg = raw_id.strip().rstrip("/").rsplit("/", 1)[-1].upper()
    return seg if re.match(r"^W\d+$", seg) else ""


def clean_venue(venue: str) -> str:
    v = clean_text(venue or "")
    if not v:
        return ""
    v_low = v.lower()
    if "lecture notes in computer science including subseries" in v_low or v_low == "lecture notes in computer science":
        return "Lecture Notes in Computer Science (Springer)"
    if "ubicomp iswc 2022 adjunct proceedings" in v_low:
        return "ACM UbiComp / ISWC 2022 Adjunct Proceedings"
    if "arxiv" in v_low:
        return "arXiv Preprint"
    if v == "Zenodo (CERN European Organization for Nuclear Research)":
        return "Zenodo"
    return v


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
        cited_by_count = int(item.get("cited_by_count") or 0)
        raw_oa_id = item.get("id", "")
        short_id = short_openalex_id(raw_oa_id)
        abstract = reconstruct_openalex_abstract(item.get("abstract_inverted_index"))

        works.append({
            "title": title,
            "year": int(year) if year else 0,
            "authors": authors,
            "venue": venue,
            "type": wtype,
            "doi": doi,
            "url": landing_url,
            "pdf_url": pdf_url,
            "abstract": abstract,
            "cited_by_count": cited_by_count,
            "source": "openalex",
            "raw_type": raw_type.lower(),
            "openalex_id": raw_oa_id,
            "openalex_ids": [short_id] if short_id else [],
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
    if not doi or (work.get("authors") and work.get("venue") and work.get("cited_by_count") is not None and work.get("abstract")):
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
        if work.get("cited_by_count") is None and "is-referenced-by-count" in data:
            work["cited_by_count"] = int(data.get("is-referenced-by-count") or 0)
        if not work.get("abstract") and data.get("abstract"):
            work["abstract"] = clean_abstract(data["abstract"])
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
                cloned = dict(item)
                oa_ids = []
                for oid in (cloned.get("openalex_ids") or []):
                    sid = short_openalex_id(oid)
                    if sid and sid not in oa_ids:
                        oa_ids.append(sid)
                sid_single = short_openalex_id(cloned.get("openalex_id", ""))
                if sid_single and sid_single not in oa_ids:
                    oa_ids.append(sid_single)
                cloned["openalex_ids"] = oa_ids
                merged_by_key[key] = cloned
            return

        target = merged_by_key[existing_key]
        # Prefer richer fields
        if (item.get("year") or 0) > (target.get("year") or 0):
            target["year"] = item["year"]
        item_auths = item.get("authors") or []
        target_auths = target.get("authors") or []
        if len(item_auths) > len(target_auths) or (
            len(item_auths) == len(target_auths)
            and author_list_quality(item_auths) > author_list_quality(target_auths)
        ):
            target["authors"] = item_auths
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
        item_abs = item.get("abstract") or ""
        target_abs = target.get("abstract") or ""
        item_is_dataset = item.get("raw_type") == "dataset" or "zenodo" in (item.get("venue") or "").lower()
        target_is_dataset = target.get("raw_type") == "dataset" or "zenodo" in (target.get("venue") or "").lower()
        if item_abs and (
            not target_abs
            or (target_is_dataset and not item_is_dataset)
            or (not item_is_dataset and len(item_abs) > len(target_abs))
        ):
            target["abstract"] = item_abs
            if not item_is_dataset and target_is_dataset:
                target["raw_type"] = item.get("raw_type", "")
        if item.get("openalex_id") and not target.get("openalex_id"):
            target["openalex_id"] = item["openalex_id"]
        target_oa_ids = list(target.get("openalex_ids") or [])
        for oid in list(item.get("openalex_ids") or []) + [item.get("openalex_id", "")]:
            sid = short_openalex_id(oid)
            if sid and sid not in target_oa_ids:
                target_oa_ids.append(sid)
        if target_oa_ids:
            target["openalex_ids"] = target_oa_ids
        if item.get("cited_by_count") is not None:
            target["cited_by_count"] = max(int(target.get("cited_by_count") or 0), int(item.get("cited_by_count") or 0))
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
            cleaned_v = clean_venue(work["venue"])
            work["venue"] = cleaned_v
            if cleaned_v == "arXiv Preprint":
                work["type"] = "preprint"
        if work.get("cited_by_count") is None:
            work["cited_by_count"] = 0
        work.pop("raw_type", None)
        work["bibtex"] = generate_bibtex(work)

    # Sort by year descending, then title
    results.sort(key=lambda x: (-(x.get("year") or 0), x.get("title", "")))
    return results


def lookup_openalex_by_doi(doi: str):
    if not doi:
        return None
    url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi, safe='/')}?select=id,cited_by_count,abstract_inverted_index"
    try:
        data = fetch_json(url)
        raw_id = data.get("id") or ""
        short_id = short_openalex_id(raw_id)
        if not short_id:
            return None
        return {
            "openalex_id": raw_id,
            "short_id": short_id,
            "cited_by_count": int(data.get("cited_by_count") or 0),
            "abstract": reconstruct_openalex_abstract(data.get("abstract_inverted_index")),
        }
    except Exception as e:
        print(f"[WARN] OpenAlex DOI lookup failed for {doi}: {e}")
        return None


def extract_arxiv_id(work: dict) -> str:
    for field in (work.get("doi") or "", work.get("pdf_url") or "", work.get("url") or ""):
        m = re.search(r"(?:arxiv[./:]|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5}(?:v\d+)?)", field, re.I)
        if m:
            return m.group(1)
    return ""


def fetch_arxiv_abstract(arxiv_id: str) -> str:
    if not arxiv_id:
        return ""
    url = f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(arxiv_id)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml_txt = resp.read().decode("utf-8", errors="replace")
        root = ET.fromstring(xml_txt)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        summary = root.find(".//a:entry/a:summary", ns)
        if summary is not None and summary.text:
            return clean_abstract(summary.text)
    except Exception as e:
        print(f"[WARN] arXiv abstract fetch failed for {arxiv_id}: {e}")
    return ""


def fetch_springer_abstract(doi: str) -> str:
    if not doi or not doi.startswith("10.1007/"):
        return ""
    for kind in ("chapter", "article"):
        url = f"https://link.springer.com/{kind}/{doi}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
            with urllib.request.urlopen(req, timeout=20) as resp:
                page = resp.read().decode("utf-8", errors="replace")
            m = re.search(r'<section[^>]*data-title="Abstract"[^>]*>.*?</section>', page, re.S | re.I)
            if m:
                section_html = re.sub(r"<h[1-6][^>]*>\s*Abstract\s*</h[1-6]>", "", m.group(0), flags=re.I)
                abs_txt = clean_abstract(section_html)
                if abs_txt:
                    return abs_txt
            m2 = re.search(r'<meta[^>]+name=["\']dc\.description["\'][^>]+content=["\']([^"\']+)["\']', page, re.I)
            if m2:
                abs_txt = clean_abstract(m2.group(1))
                if abs_txt:
                    return abs_txt
        except Exception:
            continue
    return ""


def enrich_abstract_fallbacks(work: dict):
    if work.get("abstract"):
        return
    arxiv_id = extract_arxiv_id(work)
    if arxiv_id:
        abs_txt = fetch_arxiv_abstract(arxiv_id)
        if abs_txt:
            work["abstract"] = abs_txt
            return
    doi = work.get("doi") or ""
    if doi.startswith("10.1007/"):
        abs_txt = fetch_springer_abstract(doi)
        if abs_txt:
            work["abstract"] = abs_txt


def fetch_citing_works_map(all_openalex_ids: list):
    unique_ids = []
    seen = set()
    for raw in all_openalex_ids:
        sid = short_openalex_id(raw)
        if sid and sid not in seen:
            seen.add(sid)
            unique_ids.append(sid)

    citations_by_target = {sid: [] for sid in unique_ids}
    had_error = False
    chunk_size = 40

    for i in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[i:i + chunk_size]
        chunk_set = set(chunk)
        cursor = "*"
        pages = 0
        while cursor and pages < 10:
            pages += 1
            url = (
                f"https://api.openalex.org/works?filter=cites:{'|'.join(chunk)}"
                "&select=id,doi,title,publication_year,authorships,primary_location,open_access,referenced_works"
                "&per-page=200&sort=publication_year:desc"
                f"&cursor={urllib.parse.quote(cursor, safe='')}"
            )
            try:
                data = fetch_json(url)
            except Exception as e:
                print(f"[WARN] OpenAlex citing works fetch failed for chunk {i // chunk_size + 1}: {e}")
                had_error = True
                break

            results = data.get("results") or []
            if not results:
                break

            for r in results:
                cid = short_openalex_id(r.get("id") or "")
                title = clean_text(r.get("title") or "")
                if not title:
                    continue
                year = int(r.get("publication_year") or 0)
                authors = []
                for auth in (r.get("authorships") or []):
                    name = (auth.get("author") or {}).get("display_name") or auth.get("raw_author_name")
                    if name:
                        authors.append(clean_text(name).replace("Jüergen Gall", "Jürgen Gall"))
                loc = r.get("primary_location") or {}
                venue = clean_venue(((loc.get("source") or {}).get("display_name")) or "")
                doi = normalize_doi(r.get("doi") or "")
                landing = (loc.get("landing_page_url") or "").strip()
                oa_url = ((r.get("open_access") or {}).get("oa_url") or "").strip()
                oa_page = (r.get("id") or "").strip()

                if landing.startswith(("http://", "https://")):
                    chosen_url = landing
                elif doi:
                    chosen_url = f"https://doi.org/{doi}"
                elif oa_url.startswith(("http://", "https://")):
                    chosen_url = oa_url
                elif oa_page.startswith(("http://", "https://")):
                    chosen_url = oa_page
                else:
                    chosen_url = ""

                entry = {
                    "_cid": cid,
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "venue": venue,
                    "doi": doi,
                    "url": chosen_url,
                }

                refs = {short_openalex_id(x) for x in (r.get("referenced_works") or [])}
                for wid in (refs & chunk_set):
                    citations_by_target[wid].append(entry)

            next_cursor = ((data.get("meta") or {}).get("next_cursor"))
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

    return citations_by_target, had_error


def compute_stats(merged: list) -> dict:
    total_publications = len(merged)
    cites_sorted = sorted((int(w.get("cited_by_count") or 0) for w in merged), reverse=True)
    total_citations = sum(cites_sorted)

    h_index = 0
    for idx, c in enumerate(cites_sorted, 1):
        if c >= idx:
            h_index = idx
        else:
            break

    first_author_count = 0
    equal_first_author_count = 0
    coauthor_keys = set()
    year_counts = {}

    for w in merged:
        authors = w.get("authors") or []
        is_listed_first = bool(authors) and "burchard" in authors[0].lower()
        is_equal_first = bool(w.get("equal_first_author"))
        if is_listed_first or is_equal_first:
            first_author_count += 1
        if is_equal_first and not is_listed_first:
            equal_first_author_count += 1

        for a in authors:
            if not a or "burchard" in a.lower():
                continue
            key = normalize_author_key(a)
            if key:
                coauthor_keys.add(key)

        for c in (w.get("citations") or []):
            cy = c.get("year")
            if isinstance(cy, int) and cy > 0:
                year_counts[cy] = year_counts.get(cy, 0) + 1

    citations_by_year = []
    if year_counts:
        min_y, max_y = min(year_counts), max(year_counts)
        for y in range(min_y, max_y + 1):
            citations_by_year.append({"year": y, "count": year_counts.get(y, 0)})

    return {
        "total_publications": total_publications,
        "total_citations": total_citations,
        "h_index": h_index,
        "first_author_count": first_author_count,
        "equal_first_author_count": equal_first_author_count,
        "unique_coauthors": len(coauthor_keys),
        "citations_by_year": citations_by_year,
    }


def main():
    prev_by_doi = {}
    prev_by_title = {}
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
            for pw in prev_data.get("publications", []):
                p_doi = normalize_doi(pw.get("doi", ""))
                p_title = normalize_title(pw.get("title", ""))
                if p_doi:
                    prev_by_doi[p_doi] = pw
                if p_title:
                    prev_by_title[p_title] = pw
        except Exception as e:
            print(f"[WARN] Could not read previous publications.json: {e}")

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

    # Resolve OpenAlex IDs via DOI for any works not already matched in author query
    for work in merged:
        if not work.get("openalex_ids") and work.get("doi"):
            found = lookup_openalex_by_doi(work["doi"])
            if found:
                work["openalex_id"] = work.get("openalex_id") or found["openalex_id"]
                work["openalex_ids"] = [found["short_id"]]
                work["cited_by_count"] = max(int(work.get("cited_by_count") or 0), found["cited_by_count"])
                if found.get("abstract") and len(found["abstract"]) > len(work.get("abstract") or ""):
                    work["abstract"] = found["abstract"]

    # Enrich missing abstracts via arXiv / Springer Link and preserve previous if transient failure
    for work in merged:
        if not work.get("abstract"):
            enrich_abstract_fallbacks(work)
        if not work.get("abstract"):
            work_doi = normalize_doi(work.get("doi", ""))
            work_title_norm = normalize_title(work.get("title", ""))
            prev_work = (prev_by_doi.get(work_doi) if work_doi else None) or prev_by_title.get(work_title_norm)
            if prev_work and prev_work.get("abstract"):
                work["abstract"] = prev_work["abstract"]
        work["abstract"] = work.get("abstract") or ""

    # Batch-fetch citing papers from OpenAlex
    all_oa_ids = []
    for work in merged:
        all_oa_ids.extend(work.get("openalex_ids") or [])

    print(f"Fetching citing papers for {len(set(all_oa_ids))} OpenAlex work IDs...")
    citations_by_target, had_error = fetch_citing_works_map(all_oa_ids)

    for work in merged:
        work_oa_ids = set(work.get("openalex_ids") or [])
        work_title_norm = normalize_title(work.get("title", ""))
        work_doi = normalize_doi(work.get("doi", ""))

        raw_citing = []
        for wid in (work.get("openalex_ids") or []):
            raw_citing.extend(citations_by_target.get(wid, []))

        dedup_citing = []
        seen_dois = set()
        seen_titles = set()
        for c in raw_citing:
            if c.get("_cid") and c["_cid"] in work_oa_ids:
                continue
            c_title_norm = normalize_title(c.get("title", ""))
            c_doi = normalize_doi(c.get("doi", ""))
            if c_title_norm and c_title_norm == work_title_norm:
                continue
            if c_doi and work_doi and c_doi == work_doi:
                continue
            if c_doi and c_doi in seen_dois:
                continue
            if c_title_norm and c_title_norm in seen_titles:
                continue
            if c_doi:
                seen_dois.add(c_doi)
            if c_title_norm:
                seen_titles.add(c_title_norm)
            dedup_citing.append({
                "title": c["title"],
                "authors": c["authors"],
                "year": c["year"],
                "venue": c["venue"],
                "doi": c["doi"],
                "url": c["url"],
            })

        dedup_citing.sort(key=lambda x: (-(x.get("year") or 0), (x.get("title") or "").lower()))

        if had_error and not dedup_citing:
            prev_work = (prev_by_doi.get(work_doi) if work_doi else None) or prev_by_title.get(work_title_norm)
            if prev_work and prev_work.get("citations"):
                dedup_citing = prev_work["citations"]
                work["cited_by_count"] = max(int(work.get("cited_by_count") or 0), int(prev_work.get("cited_by_count") or 0))

        work["citations"] = dedup_citing
        work["cited_by_count"] = max(int(work.get("cited_by_count") or 0), len(dedup_citing))

    # Tag equal-contribution / shared first-author works from equal_first_author.json
    eq_dois = set()
    eq_titles = set()
    if os.path.exists(EQUAL_FIRST_PATH):
        try:
            with open(EQUAL_FIRST_PATH, "r", encoding="utf-8") as f:
                eq_entries = json.load(f)
            for e in eq_entries:
                if e.get("doi"):
                    eq_dois.add(normalize_doi(e["doi"]))
                if e.get("match_title"):
                    eq_titles.add(normalize_title(e["match_title"]))
        except Exception as e:
            print(f"[WARN] Could not read equal_first_author.json: {e}")

    for work in merged:
        w_doi = normalize_doi(work.get("doi", ""))
        w_title = normalize_title(work.get("title", ""))
        if (w_doi and w_doi in eq_dois) or (w_title and w_title in eq_titles):
            work["equal_first_author"] = True
        else:
            work.pop("equal_first_author", None)

    stats = compute_stats(merged)

    # Back-populate pinned.json enriched fields (authors, doi, bibtex, links, citations)
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
                    if m.get("openalex_id"):
                        p["openalex_id"] = m["openalex_id"]
                    p["abstract"] = m.get("abstract") or p.get("abstract") or ""
                    p["cited_by_count"] = int(m.get("cited_by_count") or 0)
                    p["citations"] = m.get("citations", [])
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
        "total_citations": stats["total_citations"],
        "stats": stats,
        "publications": merged,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Successfully wrote {len(merged)} merged publications (total citations: {payload['total_citations']}) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
