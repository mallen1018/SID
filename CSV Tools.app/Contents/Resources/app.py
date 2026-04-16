import re
import io
import csv
import zipfile
import random
import unicodedata
import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from pandas.errors import EmptyDataError

st.set_page_config(page_title="CSV Tools", layout="wide")
st.title("CSV Tools")

tab1, tab2, tab3 = st.tabs(["Indeed Cleaner", "LinkedIn Cleaner", "Row Divider"])


# =============================================================================
# SHARED UTILITIES
# =============================================================================

ENCODINGS_TO_TRY = [
    "utf-8-sig", "utf-8",
    "utf-16", "utf-16le", "utf-16be",
    "utf-32", "utf-32le", "utf-32be",
    "cp1252", "latin-1", "iso-8859-1", "mac_roman",
]
DELIMITERS_TO_TRY = [",", ";", "\t", "|"]

NON_US_NANP_AREA_CODES = {
    "204","226","236","249","250","263","289","306","343","354","365","367","368",
    "387","403","416","418","431","437","438","450","468","474","506","514","519",
    "548","579","581","584","587","604","613","639","647","672","683","705","709",
    "742","753","778","780","782","807","819","825","867","873","879","902","905",
    "242","246","264","268","284","340","345","441","473","649","664","670","671",
    "684","721","758","767","784","787","809","829","849","868","869","876","939"
}

FANCY_PUNCT_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201B": "'", "\u2032": "'", "\u00B4": "'",
    "\u201C": '"', "\u201D": '"',
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
    "\u00A0": " ",
}

def nfc(s):
    if s is None:
        return ""
    return unicodedata.normalize("NFC", str(s).replace("\u00A0", " ")).strip()

def norm_text(s, strip_accents=False):
    if s is None:
        return ""
    s = str(s)
    for k, v in FANCY_PUNCT_MAP.items():
        s = s.replace(k, v)
    s = unicodedata.normalize("NFKC", s)
    if strip_accents:
        s = "".join(
            ch for ch in unicodedata.normalize("NFKD", s)
            if not unicodedata.combining(ch)
        )
    return re.sub(r"\s+", " ", s).strip()

def smart_title(name):
    name = nfc(name)
    if not name:
        return ""
    name = re.sub(r"\s+", " ", name)
    parts = name.split(" ")
    output = []
    for p in parts:
        hyphen_parts = p.split("-")
        hyphen_out = []
        for seg in hyphen_parts:
            if not seg:
                continue
            apos = "'" if "'" in seg else ("'" if "'" in seg else None)
            if apos:
                sub = seg.split(apos)
                rebuilt = []
                for i, s in enumerate(sub):
                    if s.lower().startswith("mc") and len(s) > 2:
                        rebuilt.append("Mc" + s[2].upper() + s[3:].lower())
                    elif i == 0 and s.lower() in {"o", "de", "da", "van", "von"}:
                        rebuilt.append(s.lower())
                    else:
                        rebuilt.append(s[:1].upper() + s[1:].lower() if s else s)
                seg = apos.join(rebuilt)
            else:
                if seg.lower().startswith("mc") and len(seg) > 2:
                    seg = "Mc" + seg[2].upper() + seg[3:].lower()
                else:
                    seg = seg[:1].upper() + seg[1:].lower() if seg else seg
            hyphen_out.append(seg)
        output.append("-".join(hyphen_out))
    return " ".join(output)

def split_full_name(name):
    name = nfc(name)
    if not name:
        return "", ""
    if "," in name:
        last, rest = name.split(",", 1)
        first = rest.strip().split(" ")[0] if rest.strip() else ""
        return first, last.strip()
    parts = name.split()
    if len(parts) == 1:
        return parts[0], "Unknown"
    return parts[0], " ".join(parts[1:])

def normalize_col(col):
    return re.sub(r"[^a-z0-9]+", " ", col.lower()).strip()

def find_col(df, candidates):
    for c in df.columns:
        norm = normalize_col(str(c))
        for cand in candidates:
            if cand == norm or cand in norm:
                return c
    return None

def find_col_by_alias(cols, aliases):
    for c in cols:
        cl = c.lower().replace(" ", "")
        for a in aliases:
            if cl == a.replace(" ", ""):
                return c
    return None

def infer_position_from_filename(name):
    base = Path(name).stem
    base = re.sub(r"_candidates$", "", base, flags=re.I)
    return base.replace("_", " ").strip()

def norm_phone_indeed(raw):
    raw = nfc(raw)
    if not raw:
        return None, "no_phone"
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"+1 {digits}", ""
    if len(digits) >= 12 or (len(digits) == 11 and not digits.startswith("1")):
        return None, "international"
    return None, "invalid"

def normalize_phone_linkedin(raw):
    digits = re.sub(r"\D+", "", str(raw))
    if len(digits) == 10:
        return None if digits[:3] in NON_US_NANP_AREA_CODES else "+1 " + digits
    if len(digits) == 11 and digits.startswith("1"):
        ten = digits[-10:]
        return None if ten[:3] in NON_US_NANP_AREA_CODES else "+1 " + ten
    return None

def read_csv_robust(file_bytes):
    for enc in ENCODINGS_TO_TRY:
        try:
            text = file_bytes.decode(enc)
        except Exception:
            continue
        sniffed = None
        try:
            dialect = csv.Sniffer().sniff(text[:4000], delimiters="".join(DELIMITERS_TO_TRY))
            sniffed = dialect.delimiter
        except Exception:
            sniffed = None
        delims = ([sniffed] if sniffed else []) + DELIMITERS_TO_TRY
        for d in delims:
            try:
                df = pd.read_csv(
                    io.StringIO(text), engine="python", dtype=str,
                    keep_default_na=False, sep=d, on_bad_lines="skip",
                )
                if df.shape[1] > 1:
                    return df
            except Exception:
                continue
    text = file_bytes.decode("utf-8", errors="replace")
    for d in DELIMITERS_TO_TRY:
        try:
            df = pd.read_csv(
                io.StringIO(text), engine="python", dtype=str,
                keep_default_na=False, sep=d, on_bad_lines="skip",
            )
            if df.shape[1] > 1:
                return df
        except Exception:
            continue
    raise RuntimeError("Unable to parse CSV")

def df_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")

def safe_filename(name):
    return "".join(c if c.isalnum() or c in ["_", "-"] else "_" for c in name)


# =============================================================================
# TAB 1 — INDEED CLEANER
# =============================================================================

FIRST_CANDIDATES = ["first name", "first", "fname", "given", "given name"]
LAST_CANDIDATES  = ["last name", "last", "lname", "surname", "family name"]
FULL_CANDIDATES  = ["name", "full name", "candidate name", "applicant name"]
PHONE_CANDIDATES = ["phone", "phone number", "mobile", "mobile phone", "cell", "cell phone", "telephone", "contact number"]
POS_CANDIDATES   = ["position", "job", "job title", "role", "title"]

def clean_df_indeed(df, source, company, list_val, date_val, stage):
    df = df.copy()
    df.columns = [nfc(c) for c in df.columns]

    c_first = find_col(df, FIRST_CANDIDATES)
    c_last  = find_col(df, LAST_CANDIDATES)
    c_full  = find_col(df, FULL_CANDIDATES)
    c_phone = find_col(df, PHONE_CANDIDATES)
    c_pos   = find_col(df, POS_CANDIDATES)

    first, last = [], []
    for i in range(len(df)):
        if c_first is not None and c_last is not None:
            f = df.iloc[i][c_first]
            l = df.iloc[i][c_last]
            if (" " in str(f)) or ("," in str(f)):
                f, l = split_full_name(f)
            elif (" " in str(l)) or ("," in str(l)):
                f, l = split_full_name(l)
        elif c_full is not None:
            f, l = split_full_name(df.iloc[i][c_full])
        else:
            f, l = "", ""
        first.append(smart_title(f))
        last.append(smart_title(l))

    phones, drops = [], []
    phone_series = df[c_phone].astype(str) if c_phone is not None else pd.Series([""] * len(df))
    for v in phone_series.tolist():
        p, r = norm_phone_indeed(v)
        phones.append(p or "")
        drops.append(r or "")

    if c_pos is not None:
        pos = df[c_pos].astype(str)
    else:
        pos = pd.Series([infer_position_from_filename(source)] * len(df))
    pos = pos.astype(str).str.replace(r"\s+- Work From Home\s*$", "", regex=True)

    return pd.DataFrame({
        "First Name": first,
        "Last Name": last,
        "Phone Number": phones,
        "List": list_val,
        "Position": pos,
        "Company": company,
        "Date": date_val,
        "Stage": stage,
        "_drop": drops,
        "_src": source
    })

with tab1:
    st.header("Indeed CSV Cleaner")

    uploads_indeed = st.file_uploader(
        "Upload CSV or Excel files",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        key="indeed_uploader"
    )

    c1, c2, c3, c4 = st.columns(4)
    today = datetime.date.today()
    with c1:
        company_indeed = st.text_input("Company", value="", key="indeed_company")
    with c2:
        list_val_indeed = st.text_input("List", value="", key="indeed_list")
    with c3:
        date_val_indeed = st.text_input("Date (M/D/YYYY)", value=f"{today.month}/{today.day}/{today.year}", key="indeed_date")
    with c4:
        stage_indeed = st.text_input("Stage", value="Initial", key="indeed_stage")

    st.divider()
    default_filename_indeed = f"IndeedFBSPL{today.month}{today.day:02d}{today.year}.csv"
    out_name_indeed = st.text_input("Output file name", value=default_filename_indeed, key="indeed_outname")

    if st.button("Clean files", key="indeed_clean"):
        if not uploads_indeed:
            st.error("Upload at least one file.")
            st.stop()

        frames, per_file = [], {}
        for f in uploads_indeed:
            try:
                if f.name.lower().endswith((".xlsx", ".xls")):
                    xls = pd.ExcelFile(f)
                    for sheet in xls.sheet_names:
                        temp = xls.parse(sheet, dtype=str, keep_default_na=False)
                        if not temp.empty:
                            per_file[f.name] = len(temp)
                            frames.append(clean_df_indeed(temp, f.name, company_indeed, list_val_indeed, date_val_indeed, stage_indeed))
                            break
                    else:
                        per_file[f.name] = 0
                else:
                    df = read_csv_robust(f.read())
                    per_file[f.name] = len(df)
                    frames.append(clean_df_indeed(df, f.name, company_indeed, list_val_indeed, date_val_indeed, stage_indeed))
            except Exception as e:
                st.warning(f"Skipped {f.name}: {e}")
                per_file[f.name] = 0

        if not frames:
            st.error("No data loaded.")
            st.stop()

        combined = pd.concat(frames, ignore_index=True)
        total_before = len(combined)

        dropped_international = int((combined["_drop"] == "international").sum())
        dropped_no_phone      = int((combined["_drop"] == "no_phone").sum())
        dropped_invalid       = int((combined["_drop"] == "invalid").sum())

        kept = combined[combined["_drop"] == ""].copy()
        before_dedupe = len(kept)
        kept = kept.drop_duplicates(subset=["Phone Number"], keep="first").copy()
        dropped_dupes = before_dedupe - len(kept)

        final = kept[["First Name", "Last Name", "Phone Number", "List", "Position", "Company", "Date", "Stage"]].copy()

        st.subheader("Stats")
        st.write({
            "Rows loaded per file": per_file,
            "Total rows overall": total_before,
            "Dropped (phone dupes)": dropped_dupes,
            "Dropped (international)": dropped_international,
            "Dropped (no phone)": dropped_no_phone,
            "Dropped (invalid phone)": dropped_invalid,
            "Final total rows": len(final),
        })

        st.subheader("Preview (first 50 rows)")
        st.dataframe(final.head(50), use_container_width=True)

        st.download_button(
            "Download cleaned CSV",
            data=final.to_csv(index=False).encode("utf-8"),
            file_name=out_name_indeed,
            mime="text/csv",
            key="indeed_download"
        )


# =============================================================================
# TAB 2 — LINKEDIN CLEANER
# =============================================================================

def smart_proper_case(name, strip_accents):
    name = norm_text(name, strip_accents)
    if not name:
        return "Unknown"
    parts = []
    for p in name.split():
        if p.lower().startswith("mc") and len(p) > 2:
            parts.append("Mc" + p[2:].capitalize())
        elif "'" in p:
            segs = p.split("'")
            parts.append("'".join(s.capitalize() for s in segs))
        else:
            parts.append(p.capitalize())
    return " ".join(parts)

def pick_sheet(xls):
    for s in xls.sheet_names:
        if "job" in s.lower():
            return s
    return xls.sheet_names[0]

def read_linkedin_file(upload):
    raw = upload.getvalue()
    name = upload.name.lower()
    if name.endswith((".xlsx", ".xls")):
        xls = pd.ExcelFile(io.BytesIO(raw))
        sheet = pick_sheet(xls)
        return pd.read_excel(io.BytesIO(raw), sheet_name=sheet, dtype=str, keep_default_na=False)
    return pd.read_csv(io.BytesIO(raw), dtype=str, engine="python", sep=None, keep_default_na=False)

def clean_df_linkedin(df, company, list_val, stage, date_str, strip_accents):
    original_rows = len(df)
    df = df.copy()
    df.columns = [norm_text(c, strip_accents) for c in df.columns]
    for c in df.columns:
        df[c] = df[c].map(lambda x: norm_text(x, strip_accents))

    phone_col = next((c for c in df.columns if any(x in c.lower() for x in ["phone", "mobile", "contact"])), None)
    phones = df[phone_col].map(normalize_phone_linkedin) if phone_col else pd.Series([None] * len(df))

    valid_mask = phones.notna()
    intl_removed = original_rows - valid_mask.sum()

    df = df[valid_mask].reset_index(drop=True)
    phones = phones[valid_mask].reset_index(drop=True)

    first_col = find_col_by_alias(df.columns, ["firstname", "first", "fname", "given"])
    last_col  = find_col_by_alias(df.columns, ["lastname", "last", "lname", "surname"])
    full_col  = find_col_by_alias(df.columns, ["name", "fullname", "candidatename", "applicantname"])

    if first_col and last_col:
        first = df[first_col]
        last  = df[last_col]
    else:
        src   = df[full_col] if full_col else pd.Series([""] * len(df))
        split = src.map(lambda x: x.split(" ", 1))
        first = split.map(lambda x: x[0] if x else "")
        last  = split.map(lambda x: x[1] if len(x) > 1 else "")

    first = first.map(lambda x: smart_proper_case(x, strip_accents))
    last  = last.map(lambda x: smart_proper_case(x, strip_accents))

    pos_col  = next((c for c in df.columns if "job" in c.lower() and "title" in c.lower()), None)
    position = df[pos_col] if pos_col else "Unknown"

    cleaned = pd.DataFrame({
        "First Name": first,
        "Last Name": last,
        "Phone Number": phones,
        "List": list_val,
        "Position": position,
        "Company": company,
        "Date": date_str,
        "Stage": stage
    })

    stats = {"rows_in": original_rows, "intl_removed": intl_removed, "rows_kept": len(cleaned)}
    return cleaned, stats

with tab2:
    st.header("LinkedIn CSV Cleaner")

    with st.sidebar:
        st.subheader("LinkedIn Output Settings")
        today = datetime.date.today()
        picked_date_li = st.text_input(
            "Date", value=f"{today.month}/{today.day}/{today.year}", key="li_date"
        )
        output_filename_li = st.text_input(
            "Output File Name",
            value=f"LinkedInFBSPL{picked_date_li.replace('/', '-')}.csv",
            key="li_filename"
        )
        company_li   = st.text_input("Company", "FBSPL", key="li_company")
        list_val_li  = st.text_input("List", "", key="li_list")
        stage_li     = st.text_input("Stage", "Start", key="li_stage")
        strip_accents_li = st.checkbox("Strip accents", value=False, key="li_strip")

    uploads_li = st.file_uploader(
        "Upload LinkedIn CSV or XLSX exports",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        key="li_uploader"
    )

    if uploads_li and st.button("Run Cleaner", key="li_run"):
        all_cleaned, stat_rows = [], []

        for f in uploads_li:
            df_raw = read_linkedin_file(f)
            cleaned, stats = clean_df_linkedin(df_raw, company_li, list_val_li, stage_li, picked_date_li, strip_accents_li)
            stats["file"] = f.name
            stat_rows.append(stats)
            all_cleaned.append(cleaned)

        combined_li = pd.concat(all_cleaned, ignore_index=True)
        before_dedupe_li = len(combined_li)
        combined_li = combined_li.drop_duplicates(subset=["Phone Number"], keep="first")
        dupes_removed_li = before_dedupe_li - len(combined_li)

        st.subheader("📊 Cleaning Summary")
        stats_df = pd.DataFrame(stat_rows)[["file", "rows_in", "intl_removed", "rows_kept"]]
        stats_df.columns = ["File", "Rows In", "Intl Removed", "US Rows Kept"]
        st.dataframe(stats_df, use_container_width=True)

        st.markdown(f"""
**Totals**
- Total rows in: **{stats_df['Rows In'].sum()}**
- International removed: **{stats_df['Intl Removed'].sum()}**
- Rows before dedupe: **{before_dedupe_li}**
- Duplicates removed: **{dupes_removed_li}**
- Final total rows: **{len(combined_li)}**
""")

        st.success("Cleaning complete")

        csv_bytes_li = combined_li.to_csv(index=False).encode("utf-8-sig")
        fn_li = output_filename_li if output_filename_li.endswith(".csv") else output_filename_li + ".csv"
        st.download_button(
            "Download cleaned CSV",
            data=csv_bytes_li,
            file_name=fn_li,
            mime="text/csv",
            key="li_download"
        )


# =============================================================================
# TAB 3 — ROW DIVIDER
# =============================================================================

def normalize_counts_to_total(weights, total_rows):
    total_weight = sum(v for v in weights.values() if v > 0)
    if total_weight <= 0:
        raise ValueError("Amounts must sum to a positive number.")
    scaled  = {k: (v / total_weight) * total_rows for k, v in weights.items()}
    rounded = {k: int(round(v)) for k, v in scaled.items()}
    diff = total_rows - sum(rounded.values())
    keys = list(rounded.keys())
    i = 0
    while diff != 0:
        k = keys[i % len(keys)]
        rounded[k] += 1 if diff > 0 else -1
        diff += -1 if diff > 0 else 1
        i += 1
    return rounded

def build_account_sequence(counts, style):
    accounts = [a for a, c in counts.items() if c > 0]
    if style == "Top to bottom":
        seq = []
        for a in accounts:
            seq.extend([a] * counts[a])
        return seq
    remaining = counts.copy()
    seq, last = [], None
    while sum(remaining.values()) > 0:
        candidates = [a for a in accounts if remaining[a] > 0]
        candidates.sort(key=lambda a: remaining[a], reverse=True)
        bucket = candidates[:min(4, len(candidates))]
        if last in bucket and len(bucket) > 1:
            bucket.remove(last)
        pick = random.choice(bucket)
        seq.append(pick)
        remaining[pick] -= 1
        last = pick
    return seq

DEFAULT_ACCOUNTS = [
    ("Griffin Insurance", 275),
    ("GKM Insurance", 275),
    ("EA Insurance", 175),
    ("Spencer Financial", 175),
    ("Dilbert Financial", 150),
    ("SWAT Financial", 125),
    ("Else Agency", 125),
    ("Manzano Agency", 100),
    ("King Agency", 75),
    ("Montgomery Agency", 50),
]

with tab3:
    st.header("Row Divider")

    uploaded_rd = st.file_uploader(
        "Upload one or more CSVs",
        type=["csv"],
        accept_multiple_files=True,
        key="rd_uploader"
    )

    c1_rd, c2_rd = st.columns(2)
    with c1_rd:
        date_value_rd = st.text_input("Set Date for all rows", value="3/2/2026", key="rd_date")
    with c2_rd:
        list_template_rd = st.text_input(
            "Global list template (use {account})",
            value="3.2 - {account} - Indeed",
            key="rd_list_template"
        )

    list_mode_rd = st.radio(
        "List naming mode",
        ["Use global list template (recommended)", "Customize list per account"],
        horizontal=True,
        key="rd_list_mode"
    )

    mode_rd = st.radio(
        "Row usage mode",
        [
            "Use all rows (auto-scale)",
            "Use exact counts + export UNUSED",
            "Use exact counts + require exact match",
        ],
        horizontal=True,
        key="rd_mode"
    )

    assignment_style_rd = st.radio(
        "Assignment style",
        ["Top to bottom", "Smart-random mix"],
        horizontal=True,
        key="rd_assignment"
    )

    st.subheader("Accounts to divide into")

    if "rd_alloc_df" not in st.session_state:
        st.session_state.rd_alloc_df = pd.DataFrame(
            [(a, amt, "") for a, amt in DEFAULT_ACCOUNTS],
            columns=["Account", "Amount", "List Name"]
        )

    b1_rd, b2_rd, b3_rd = st.columns([1, 1, 2])
    with b1_rd:
        if st.button("Add account", key="rd_add"):
            st.session_state.rd_alloc_df.loc[len(st.session_state.rd_alloc_df)] = ["", 0, ""]
    with b2_rd:
        if st.button("Remove last", key="rd_remove"):
            if len(st.session_state.rd_alloc_df) > 1:
                st.session_state.rd_alloc_df = st.session_state.rd_alloc_df.iloc[:-1].reset_index(drop=True)
    with b3_rd:
        if st.button("Reset defaults", key="rd_reset"):
            st.session_state.rd_alloc_df = pd.DataFrame(
                [(a, amt, "") for a, amt in DEFAULT_ACCOUNTS],
                columns=["Account", "Amount", "List Name"]
            )

    col_config_rd = {
        "Account": st.column_config.TextColumn(),
        "Amount": st.column_config.NumberColumn(min_value=0, step=1),
    }
    if list_mode_rd == "Customize list per account":
        col_config_rd["List Name"] = st.column_config.TextColumn(
            help="Optional override. Leave blank to use global template."
        )

    edited_df_rd = st.data_editor(
        st.session_state.rd_alloc_df,
        hide_index=True,
        use_container_width=True,
        column_config=col_config_rd,
        key="rd_editor"
    )
    st.session_state.rd_alloc_df = edited_df_rd

    if not uploaded_rd:
        st.info("Upload CSVs to continue.")
    else:
        dfs_rd = []
        for f in uploaded_rd:
            try:
                f.seek(0)
                try:
                    df = pd.read_csv(f, encoding="utf-8")
                except UnicodeDecodeError:
                    f.seek(0)
                    df = pd.read_csv(f, encoding="latin-1")
                if df.empty or df.columns.size == 0:
                    st.warning(f"Skipped empty file: {f.name}")
                    continue
                dfs_rd.append(df)
            except EmptyDataError:
                st.warning(f"Skipped unreadable file: {f.name}")

        if not dfs_rd:
            st.error("All uploaded files were empty or invalid.")
        else:
            master_df_rd = pd.concat(dfs_rd, ignore_index=True)
            total_rows_rd = len(master_df_rd)
            st.markdown(f"### Total rows detected: **{total_rows_rd}**")

            alloc_rows_rd = st.session_state.rd_alloc_df.copy()
            alloc_rows_rd["Account"] = alloc_rows_rd["Account"].astype(str).str.strip()
            alloc_rows_rd = alloc_rows_rd[alloc_rows_rd["Account"] != ""]

            alloc_rd, list_map_rd = {}, {}
            for _, r in alloc_rows_rd.iterrows():
                acct = r["Account"]
                amt  = int(r["Amount"]) if not pd.isna(r["Amount"]) else 0
                alloc_rd[acct] = amt
                if list_mode_rd == "Customize list per account":
                    custom = str(r.get("List Name", "")).strip()
                    list_map_rd[acct] = custom if custom else list_template_rd.replace("{account}", acct)
                else:
                    list_map_rd[acct] = list_template_rd.replace("{account}", acct)

            if not alloc_rd or sum(alloc_rd.values()) == 0:
                st.error("Add at least one account with a positive Amount.")
            else:
                requested_total_rd = sum(alloc_rd.values())
                st.write(f"Requested total (raw): {requested_total_rd}")

                if mode_rd == "Use all rows (auto-scale)":
                    final_counts_rd = normalize_counts_to_total(alloc_rd, total_rows_rd)
                    used_rows_rd    = total_rows_rd
                    unused_rows_rd  = 0
                elif mode_rd == "Use exact counts + export UNUSED":
                    if requested_total_rd > total_rows_rd:
                        st.error(f"Requested {requested_total_rd} rows, but only {total_rows_rd} exist.")
                        st.stop()
                    final_counts_rd = alloc_rd.copy()
                    used_rows_rd    = requested_total_rd
                    unused_rows_rd  = total_rows_rd - requested_total_rd
                else:
                    if requested_total_rd != total_rows_rd:
                        st.error(f"Exact match required. Requested {requested_total_rd}, file has {total_rows_rd}.")
                        st.stop()
                    final_counts_rd = alloc_rd.copy()
                    used_rows_rd    = total_rows_rd
                    unused_rows_rd  = 0

                summary_rd = pd.DataFrame(
                    [{"Account": k, "Rows": v, "List": list_map_rd[k]} for k, v in final_counts_rd.items()]
                )
                summary_rd.loc[len(summary_rd)] = {"Account": "TOTAL USED", "Rows": sum(final_counts_rd.values()), "List": ""}
                summary_rd.loc[len(summary_rd)] = {"Account": "UNUSED",     "Rows": unused_rows_rd,               "List": ""}

                st.subheader("Final allocation counts")
                st.dataframe(summary_rd, use_container_width=True)

                sequence_rd = build_account_sequence(final_counts_rd, assignment_style_rd)
                used_df_rd   = master_df_rd.iloc[:used_rows_rd].copy()
                unused_df_rd = master_df_rd.iloc[used_rows_rd:].copy() if unused_rows_rd else master_df_rd.iloc[0:0].copy()

                if "List" not in used_df_rd.columns:
                    used_df_rd["List"] = ""
                if "Date" not in used_df_rd.columns:
                    used_df_rd["Date"] = ""

                used_df_rd["_acct"] = sequence_rd[:used_rows_rd]
                used_df_rd["List"]  = used_df_rd["_acct"].apply(lambda a: list_map_rd[a])
                used_df_rd["Date"]  = date_value_rd
                used_df_rd.drop(columns="_acct", inplace=True)

                buf_rd = io.BytesIO()
                with zipfile.ZipFile(buf_rd, "w", zipfile.ZIP_DEFLATED) as z:
                    z.writestr("MASTER_used.csv", df_to_csv_bytes(used_df_rd))
                    for acct in final_counts_rd:
                        acct_df = used_df_rd[used_df_rd["List"] == list_map_rd[acct]]
                        z.writestr(f"{safe_filename(acct)}.csv", df_to_csv_bytes(acct_df))
                    if unused_rows_rd:
                        z.writestr("UNUSED.csv", df_to_csv_bytes(unused_df_rd))

                st.download_button(
                    "Download ZIP (MASTER + per-account + UNUSED)",
                    data=buf_rd.getvalue(),
                    file_name="row_divider_output.zip",
                    mime="application/zip",
                    key="rd_download"
                )

                with st.expander("Preview first 50 rows"):
                    st.dataframe(used_df_rd.head(50), use_container_width=True)
