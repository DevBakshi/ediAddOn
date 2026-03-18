import streamlit as st
import os, re
from pathlib import Path

st.set_page_config(page_title="EDI Editor", page_icon="📋", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: #0b0d14; }
section[data-testid="stSidebar"] { background: #0f111a; border-right: 1px solid #1c1f2e; }
.seg-block {
    background: #111420;
    border: 1px solid #1c1f2e;
    border-left: 5px solid var(--c, #4a90d9);
    border-radius: 8px;
    padding: 14px 18px 10px;
    margin: 10px 0;
}
.seg-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px; font-weight: 700;
    color: var(--c, #4a90d9);
}
.seg-desc { color: #4b5563; font-size: 12px; margin-left: 10px; }
.field-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.field-table th {
    font-size: 10px; text-transform: uppercase; letter-spacing: .06em;
    color: #374151; text-align: left; padding: 3px 8px 6px;
    border-bottom: 1px solid #1c1f2e;
}
.field-table td { padding: 5px 8px; border-bottom: 1px solid #0f111a; font-size: 13px; vertical-align: top; }
.td-num  { font-family: 'JetBrains Mono', monospace; color: #374151; font-size: 10px; width: 28px; }
.td-name { color: #6b7280; width: 210px; }
.td-val  { font-family: 'JetBrains Mono', monospace; color: #e5e7eb; }
.td-empty{ font-family: 'JetBrains Mono', monospace; color: #ef4444; font-style: italic; }
.badge   { display:inline-block; padding:1px 8px; border-radius:10px; font-size:10px; margin-left:6px; }
.b-empty { background:#7f1d1d; color:#fca5a5; }
.b-issue { background:#78350f; color:#fcd34d; }
.b-ok    { background:#14532d; color:#86efac; }
.raw-box {
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
    background: #080a10; border: 1px solid #1c1f2e; border-radius: 5px;
    padding: 8px 12px; color: #6b7280; word-break: break-all; margin: 6px 0;
}
.raw-new {
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
    background: #052010; border: 1px solid #166534; border-radius: 5px;
    padding: 8px 12px; color: #4ade80; word-break: break-all; margin: 6px 0;
}
.search-match {
    background: #1a1000; border: 1px solid #854d0e;
    border-left: 4px solid #f59e0b; border-radius: 6px;
    padding: 10px 14px; margin: 4px 0; cursor: pointer;
}
.search-match:hover { background: #211500; }
.metric-card {
    background: #111420; border: 1px solid #1c1f2e; border-radius: 8px;
    padding: 12px 16px; text-align: center;
}
.metric-num { font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 700; color: #e5e7eb; }
.metric-lbl { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: #4b5563; margin-top: 2px; }
.txn-banner {
    background: linear-gradient(135deg,#0c1929,#0f2235);
    border: 1px solid #1e3a5f; border-radius: 10px; padding: 14px 20px; margin-bottom: 14px;
}
.issue-row { background:#1a0900; border-left:3px solid #f97316; border-radius:4px; padding:6px 12px;
             font-family:'JetBrains Mono',monospace; font-size:12px; color:#fdba74; margin:3px 0; }
.missing-row { background:#150000; border-left:3px solid #ef4444; border-radius:4px; padding:6px 12px;
               font-family:'JetBrains Mono',monospace; font-size:12px; color:#fca5a5; margin:3px 0; }
.divider { border:none; border-top:1px solid #1c1f2e; margin:10px 0; }
</style>
""", unsafe_allow_html=True)

# SEGMENT KNOWLEDGE BASE
SEG_ELEMENTS = {
    "ISA":["Authorization Info Qualifier","Authorization Information","Security Info Qualifier",
           "Security Information","Interchange ID Qualifier (Sender)","Interchange Sender ID",
           "Interchange ID Qualifier (Receiver)","Interchange Receiver ID","Interchange Date (YYMMDD)",
           "Interchange Time (HHMM)","Repetition Separator","Interchange Control Version",
           "Interchange Control Number","Acknowledgment Requested","Usage Indicator (T=Test P=Prod)",
           "Component Element Separator"],
    "IEA":["Number of Functional Groups","Interchange Control Number"],
    "GS": ["Functional Identifier Code","Application Sender Code","Application Receiver Code",
           "Date (CCYYMMDD)","Time (HHMM)","Group Control Number","Responsible Agency Code","Version / Release"],
    "GE": ["Number of Transaction Sets","Group Control Number"],
    "ST": ["Transaction Set Identifier Code","Transaction Set Control Number","Implementation Convention Reference"],
    "SE": ["Number of Included Segments","Transaction Set Control Number"],
    # 850
    "BEG":["Transaction Set Purpose Code","Purchase Order Type Code","Purchase Order Number",
           "Release Number","Date","Contract Number"],
    "PO1":["Assigned ID","Quantity Ordered","Unit of Measure","Unit Price","Basis of Unit Price Code",
           "Product ID Qualifier","Product ID","Product ID Qualifier 2","Product ID 2"],
    "PID":["Item Description Type","Product Characteristic Code","Agency Qualifier Code",
           "Product Description Code","Description"],
    "PO4":["Pack","Size","Unit of Measure","Packaging Code","Weight Qualifier","Gross Weight Per Pack",
           "Weight Unit","Gross Volume Per Pack","Volume Unit"],
    "CTT":["Number of Line Items","Hash Total","Weight","Weight Unit","Volume","Volume Unit","Description"],
    "SCH":["Quantity","Unit of Measure","Entity Identifier Code","Name","Date/Time Qualifier","Date",
           "Date/Time Qualifier 2","Date 2"],
    # 810
    "BIG":["Invoice Date","Invoice Number","Purchase Order Date","Purchase Order Number",
           "Release Number","Change Order Sequence","Transaction Type Code"],
    "IT1":["Assigned ID","Quantity Invoiced","Unit of Measure","Unit Price","Basis of Unit Price Code",
           "Product ID Qualifier","Product ID","Product ID Qualifier 2","Product ID 2"],
    "TDS":["Total Invoice Amount","Amount Subject to Terms Discount","Terms Discount Amount","Total Before Taxes"],
    "ITD":["Terms Type Code","Terms Basis Date Code","Terms Discount Percent","Terms Discount Due Date",
           "Terms Discount Days Due","Terms Net Due Date","Terms Net Days","Terms Discount Amount",
           "Deferred Due Date","Deferred Amount Due","Percent of Invoice Payable","Description"],
    "TXI":["Tax Type Code","Monetary Amount","Percent","Tax Jurisdiction Code","Tax Exempt Code","Relationship Code"],
    "SAC":["Allowance or Charge Indicator","Service/Promo/Allowance/Charge Code","Agency Qualifier Code",
           "Agency Service Code","Amount","Percent","Rate"],
    "CAD":["Transportation Method","Equipment Initial","Equipment Number","Standard Carrier Alpha Code",
           "Routing","Shipment/Order Status Code","Reference ID Qualifier","Reference ID","Service Level Code"],
    # 856
    "BSN":["Transaction Set Purpose Code","Shipment ID","Date","Time","Hierarchical Structure Code"],
    "HL": ["Hierarchical ID Number","Parent Hierarchical ID Number","Hierarchical Level Code","Hierarchical Child Code"],
    "TD1":["Packaging Code","Lading Quantity","Commodity Code","Lading Description","Weight Qualifier",
           "Weight","Weight Unit","Volume","Volume Unit"],
    "TD5":["Routing Sequence Code","ID Code Qualifier","ID Code","Transportation Method","Routing"],
    "MAN":["Marks and Numbers Qualifier","Marks and Numbers","Marks and Numbers Qualifier 2","Marks and Numbers 2"],
    "SHP":["Quantity","Unit of Measure","Shipped Date","Scheduled Delivery Date"],
    # 820
    "BPR":["Transaction Handling Code","Monetary Amount","Credit/Debit Flag","Payment Method Code",
           "Payment Format Code","Data Application Identifier","Routing Number Qualifier","Routing Number",
           "Account Number Qualifier","Account Number","Originating Company ID","Originating Company Supplemental",
           "Routing Number Qualifier 2","Routing Number 2","Account Number Qualifier 2","Account Number 2","Effective Date"],
    "TRN":["Trace Type Code","Reference ID","Originating Company ID","Reference ID 2"],
    "RMR":["Reference ID Qualifier","Reference ID","Payment Action Code","Monetary Amount","Monetary Amount 2","Adjustment Reason Code"],
    "ENT":["Assigned Number","Entity Identifier Code","ID Code Qualifier","ID Code"],
    # 997
    "AK1":["Functional Identifier Code","Group Control Number","Version / Release"],
    "AK2":["Transaction Set ID Code","Transaction Set Control Number"],
    "AK3":["Segment ID Code","Segment Position","Loop ID Code","Segment Syntax Error Code"],
    "AK4":["Position in Segment","Data Element Reference Number","Data Element Syntax Error Code","Copy of Bad Data Element"],
    "AK5":["Transaction Set Acknowledgment Code","Error Code 1","Error Code 2","Error Code 3"],
    "AK9":["Functional Group Acknowledge Code","Number of Transaction Sets Included",
           "Number of Received Transaction Sets","Number of Accepted Transaction Sets"],
    # Common
    "NM1":["Entity Identifier Code","Entity Type Qualifier","Last/Org Name","First Name","Middle Name",
           "Name Prefix","Name Suffix","ID Code Qualifier","ID Code"],
    "N2": ["Additional Name","Additional Name 2"],
    "N3": ["Address Line 1","Address Line 2"],
    "N4": ["City","State / Province","Postal Code","Country Code"],
    "REF":["Reference ID Qualifier","Reference ID","Description"],
    "DTM":["Date/Time Qualifier","Date (CCYYMMDD)","Time","Time Code"],
    "PER":["Contact Function Code","Name","Communication Number Qualifier","Communication Number",
           "Qualifier 2","Communication Number 2"],
    "NTE":["Note Reference Code","Description"],
    "CUR":["Entity Identifier Code","Currency Code","Exchange Rate"],
    "AMT":["Amount Qualifier Code","Monetary Amount","Credit/Debit Flag"],
    "LX": ["Assigned Number"],
    "PKG":["Item Description Type","Packaging Characteristic Code","Agency Qualifier Code",
           "Packaging Description Code","Description"],
}

SEG_DESC = {
    "ISA":"Interchange Control Header",    "IEA":"Interchange Control Trailer",
    "GS": "Functional Group Header",       "GE": "Functional Group Trailer",
    "ST": "Transaction Set Header",        "SE": "Transaction Set Trailer",
    "BEG":"Beginning Segment — Purchase Order","BIG":"Beginning Segment — Invoice",
    "BSN":"Beginning Segment — Ship Notice","BPR":"Beginning Segment — Payment Order",
    "PO1":"PO Line Item",                  "IT1":"Invoice Line Item",
    "PID":"Product / Item Description",    "PO4":"Item Physical Details",
    "CTT":"Transaction Totals",            "TDS":"Total Invoice Amount",
    "ITD":"Terms of Sale",                 "TXI":"Tax Information",
    "SAC":"Allowance / Charge",            "CAD":"Carrier Detail",
    "NM1":"Name",                          "N2": "Additional Name",
    "N3": "Address",                       "N4": "Geographic Location",
    "REF":"Reference Identification",      "DTM":"Date / Time Reference",
    "PER":"Administrative Contact",        "NTE":"Note / Special Instruction",
    "CUR":"Currency",                      "AMT":"Monetary Amount",
    "LX": "Assigned Number",              "PKG":"Marking / Packaging",
    "HL": "Hierarchical Level",           "TD1":"Carrier Details — Weight",
    "TD5":"Carrier Details — Routing",    "MAN":"Marks and Numbers",
    "TRN":"Trace Number",                 "RMR":"Remittance Open Item",
    "ENT":"Entity",                       "SCH":"Line Item Schedule",
    "SHP":"Shipment",                     "AK1":"Functional Group Response",
    "AK2":"Transaction Set Response",     "AK3":"Segment Note",
    "AK4":"Element Note",                 "AK5":"Transaction Set Response Trailer",
    "AK9":"Functional Group Response Trailer",
}

SEG_COLOR = {
    "ISA":"#38bdf8","IEA":"#38bdf8","GS":"#7dd3fc","GE":"#7dd3fc",
    "ST":"#67e8f9","SE":"#67e8f9",
    "BEG":"#6ee7b7","BIG":"#6ee7b7","BSN":"#6ee7b7","BPR":"#6ee7b7",
    "NM1":"#5eead4","N2":"#5eead4","N3":"#5eead4","N4":"#5eead4",
    "PO1":"#f87171","IT1":"#f87171","PID":"#fb923c","PO4":"#fb923c",
    "REF":"#c084fc","DTM":"#fbbf24","CTT":"#94a3b8","TDS":"#fb923c",
    "ITD":"#fbbf24","TXI":"#fbbf24","SAC":"#fbbf24","AMT":"#fb923c",
    "HL":"#a78bfa","LX":"#818cf8","TD1":"#60a5fa","TD5":"#60a5fa",
    "MAN":"#60a5fa","CAD":"#94a3b8","PKG":"#94a3b8","TRN":"#34d399",
    "RMR":"#34d399","ENT":"#34d399","AK1":"#fde68a","AK2":"#fde68a",
    "AK3":"#f97316","AK4":"#f97316","AK5":"#fde68a","AK9":"#fde68a",
    "PER":"#c084fc","NTE":"#94a3b8","CUR":"#34d399","SCH":"#60a5fa",
    "SHP":"#60a5fa","BSN":"#6ee7b7",
}

REQUIRED_SEGS = {
    "850":["ISA","GS","ST","BEG","PO1","CTT","SE","GE","IEA"],
    "810":["ISA","GS","ST","BIG","IT1","TDS","SE","GE","IEA"],
    "856":["ISA","GS","ST","BSN","HL","TD1","SE","GE","IEA"],
    "820":["ISA","GS","ST","BPR","TRN","SE","GE","IEA"],
    "997":["ISA","GS","ST","AK1","AK9","SE","GE","IEA"],
}

TXN_NAMES = {
    "850":"Purchase Order","810":"Invoice","856":"Advance Ship Notice",
    "820":"Remittance Advice","997":"Functional Acknowledgment",
    "855":"PO Acknowledgment","860":"PO Change","832":"Price / Sales Catalog",
}

EDI_EXTS = {".edi",".int",".txt",".x12",".dat",".810",".850",".856",".820",".997",""}

# CORE FUNCTIONS
def detect_delimiters(content):
    """
    X12 ISA is always exactly 106 characters:
      pos  3        = element separator
      pos 104       = component element separator
      pos 105       = segment terminator
    Reading these from fixed positions is the only reliable method —
    splitting on the element separator first (as we did before) incorrectly
    treated the component separator as the segment terminator.
    """
    c = content.strip()
    if c.startswith("ISA") and len(c) >= 106:
        elem_sep = c[3]    # always the 4th character
        comp_sep = c[104]  # always position 104
        seg_term = c[105]  # always position 105
        return elem_sep, seg_term, comp_sep
    # fallback for non-standard / short files
    if c.startswith("ISA") and len(c) > 3:
        elem_sep = c[3]
        parts    = c.split(elem_sep)
        seg_term = "~"
        comp_sep = parts[16][0] if len(parts) > 16 and parts[16] else ":"
        return elem_sep, seg_term, comp_sep
    return "*", "~", ":"

def parse_edi(content):
    elem_sep, seg_term, comp_sep = detect_delimiters(content)
    segments, buf = [], ""
    for ch in content:
        if ch == seg_term:
            s = buf.strip()
            if s:
                elems  = s.split(elem_sep)
                seg_id = elems[0].strip().upper()
                segments.append({"id": seg_id, "elements": elems[1:], "raw": s})
            buf = ""
        else:
            buf += ch
    return segments, elem_sep, seg_term, comp_sep

def segments_to_edi(segments, elem_sep, seg_term):
    return "\n".join(
        elem_sep.join([s["id"]] + s["elements"]) + seg_term
        for s in segments
    ) + "\n"

def validate(segments):
    issues, missing = [], []
    ids    = [s["id"] for s in segments]
    txn_id = next((s["elements"][0].strip() for s in segments
                   if s["id"] == "ST" and s["elements"]), None)
    isa_ctrl = gs_ctrl = st_ctrl = None
    for seg in segments:
        sid, el = seg["id"], seg["elements"]
        if sid == "ISA":
            if len(el) < 16:
                issues.append("ISA must have exactly 16 elements")
            else:
                isa_ctrl = el[12].strip()
                if not el[5].strip(): issues.append("ISA06 — Interchange Sender ID is empty")
                if not el[7].strip(): issues.append("ISA08 — Interchange Receiver ID is empty")
        if sid == "IEA" and isa_ctrl and len(el) >= 2:
            if el[1].strip() != isa_ctrl:
                issues.append(f"ISA/IEA control number mismatch ({isa_ctrl} ≠ {el[1].strip()})")
        if sid == "GS"  and len(el) >= 6: gs_ctrl = el[5].strip()
        if sid == "GE"  and gs_ctrl and len(el) >= 2:
            if el[1].strip() != gs_ctrl:
                issues.append(f"GS/GE control number mismatch ({gs_ctrl} ≠ {el[1].strip()})")
        if sid == "ST"  and len(el) >= 2: st_ctrl = el[1].strip()
        if sid == "SE"  and st_ctrl and len(el) >= 2:
            if el[1].strip() != st_ctrl:
                issues.append(f"ST/SE control number mismatch ({st_ctrl} ≠ {el[1].strip()})")
        if sid == "DTM" and len(el) >= 2:
            d = el[1].strip()
            if d and not re.match(r"^\d{8}$", d):
                issues.append(f"DTM date '{d}' should be 8 digits CCYYMMDD")
    for opener, closer in [("ISA","IEA"),("GS","GE"),("ST","SE")]:
        o, c = ids.count(opener), ids.count(closer)
        if o != c: issues.append(f"{opener}/{closer} pair mismatch — {o} open, {c} close")
    if txn_id and txn_id in REQUIRED_SEGS:
        for req in REQUIRED_SEGS[txn_id]:
            if req not in ids:
                missing.append(f"<{req}> missing — required for EDI {txn_id} ({TXN_NAMES.get(txn_id,'')})")
    return issues, missing, txn_id

# FOLDER SEARCH
def search_folder(folder, txn_filter, invoice_num, po_num):
    """
    Walk folder for EDI files, parse each, and return matches.
    Returns list of dicts: {path, file_name, txn_id, invoice_num, po_num, segments, elem_sep, seg_term, comp_sep}
    """
    results = []
    try:
        all_files = [
            f for f in Path(folder).rglob("*")
            if f.is_file()
        ]
    except Exception:
        return results

    for fp in all_files:
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if not content.strip().startswith("ISA"):
            continue
        segs, es, st_ch, cs = parse_edi(content)
        ids = [s["id"] for s in segs]

        # Transaction filter
        file_txn = next((s["elements"][0].strip() for s in segs
                         if s["id"] == "ST" and s["elements"]), None)
        if txn_filter != "Any" and file_txn != txn_filter:
            continue

        # Extract key identifiers depending on transaction type
        file_inv = ""
        file_po  = ""
        for s in segs:
            if s["id"] == "BIG":                    # 810 invoice number & PO ref
                el = s["elements"]
                file_inv = el[1].strip() if len(el) > 1 else ""
                file_po  = el[3].strip() if len(el) > 3 else ""
            if s["id"] == "BEG":                    # 850 PO number
                el = s["elements"]
                if not file_po:
                    file_po = el[2].strip() if len(el) > 2 else ""
            if s["id"] == "AK1":                    # 997 — group being acknowledged
                el = s["elements"]
                # AK102 = group control number of the file being acknowledged
                if not file_po:
                    file_po = el[1].strip() if len(el) > 1 else ""
            if s["id"] == "AK2":                    # 997 — transaction set being acknowledged
                el = s["elements"]
                # AK201 = transaction set type (850, 810 etc.)
                if not file_inv:
                    file_inv = f"ACK of {el[0].strip()}" if el else ""

        # Apply search filters
        inv_match = (not invoice_num) or (invoice_num.lower() in file_inv.lower())
        po_match  = (not po_num)      or (po_num.lower()      in file_po.lower())
        if not (inv_match and po_match):
            continue

        results.append({
            "path":       str(fp),
            "file_name":  fp.name,
            "txn_id":     file_txn,
            "invoice_num":file_inv,
            "po_num":     file_po,
            "segments":   segs,
            "elem_sep":   es,
            "seg_term":   st_ch,
            "comp_sep":   cs,
        })

    return results

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def init_state():
    for k, v in {
        "segments":    [], "elem_sep": "*", "seg_term": "~", "comp_sep": ":",
        "file_path":   None, "file_name": None, "modified": False,
        "active_seg":  None, "browse_dir": str(Path.home()),
        "search_results": [], "show_search": False,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def load_file_data(content, name, path=None):
    segs, es, st_ch, cs = parse_edi(content)
    st.session_state.segments   = segs
    st.session_state.elem_sep   = es
    st.session_state.seg_term   = st_ch
    st.session_state.comp_sep   = cs
    st.session_state.file_path  = path
    st.session_state.file_name  = name
    st.session_state.modified   = False
    st.session_state.active_seg = None

def open_any_file(path):
    """Try to open any file regardless of extension, decoding as best we can."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                return f.read()
        except Exception:
            continue
    # Last resort — read as bytes and decode
    with open(path, "rb") as f:
        return f.read().decode("latin-1", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# EDIT DIALOG
# ─────────────────────────────────────────────────────────────────────────────
@st.dialog("Edit Segment", width="large")
def edit_dialog(idx):
    seg      = st.session_state.segments[idx]
    sid      = seg["id"]
    elems    = seg["elements"]
    color    = SEG_COLOR.get(sid, "#6b7280")
    desc     = SEG_DESC.get(sid, "")
    el_names = SEG_ELEMENTS.get(sid, [])
    elem_sep = st.session_state.elem_sep
    seg_term = st.session_state.seg_term

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:22px;font-weight:700;color:{color}">{sid}</span>'
        f'<span style="color:#6b7280;font-size:13px">{desc}</span>'
        f'<span style="margin-left:auto;color:#374151;font-size:11px">segment {idx+1} of {len(st.session_state.segments)}</span>'
        f'</div>', unsafe_allow_html=True)

    st.markdown("**Original raw:**")
    st.markdown(f'<div class="raw-box">{elem_sep.join([sid]+elems)}{seg_term}</div>',
                unsafe_allow_html=True)
    st.divider()
    st.markdown("**Edit fields:**")

    max_f = max(len(elems), len(el_names))
    vals  = list(elems) + [""] * (max_f - len(elems))
    updated = []

    for i in range(0, max_f, 2):
        c1, c2 = st.columns(2)
        for j, col in enumerate([c1, c2]):
            fi = i + j
            if fi >= max_f: break
            name  = el_names[fi] if fi < len(el_names) else f"Element {fi+1}"
            value = vals[fi]
            with col:
                edited = st.text_input(
                    f"{fi+1:02}  {name}" + ("  ⚠" if not value.strip() else ""),
                    value=value, key=f"dlg_{idx}_{fi}", placeholder="(empty)")
                updated.append(edited)

    while len(updated) < len(elems):
        updated.append(elems[len(updated)])

    preview = elem_sep.join([sid] + updated) + seg_term
    st.divider()
    st.markdown("**Reconstructed segment (what will be saved):**")
    st.markdown(f'<div class="raw-new">{preview}</div>', unsafe_allow_html=True)
    st.divider()

    b1, b2 = st.columns(2)
    with b1:
        if st.button("Save segment", type="primary", use_container_width=True, key=f"dlg_sv_{idx}"):
            st.session_state.segments[idx]["elements"] = updated
            st.session_state.segments[idx]["raw"]      = elem_sep.join([sid] + updated)
            st.session_state.modified   = True
            st.session_state.active_seg = None
            st.rerun()
    with b2:
        if st.button("Cancel", use_container_width=True, key=f"dlg_cl_{idx}"):
            st.session_state.active_seg = None
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📋 EDI Editor")
    st.markdown("---")

    tab_load, tab_search = st.tabs(["Load File", "Search Folder"])

    # ── Load tab ──────────────────────────────────────────────────────────────
    with tab_load:
        pick = st.radio("Source", ["Browse folder", "Upload file"], horizontal=True,
                        label_visibility="collapsed")

        if pick == "Upload file":
            up = st.file_uploader("Drop EDI file", label_visibility="collapsed")
            if up:
                load_file_data(up.read().decode("utf-8", errors="replace"), up.name)
                st.success(f"Loaded: {up.name}")
                st.rerun()
        else:
            dir_in = st.text_input("Folder", value=st.session_state.browse_dir,
                                   label_visibility="collapsed")
            if dir_in != st.session_state.browse_dir and os.path.isdir(dir_in):
                st.session_state.browse_dir = dir_in

            browse = st.session_state.browse_dir
            parent = str(Path(browse).parent)
            if parent != browse:
                if st.button("⬆ Up one folder", use_container_width=True):
                    st.session_state.browse_dir = parent
                    st.rerun()
            st.caption(f"`{browse}`")

            try:
                entries = sorted(os.scandir(browse),
                                 key=lambda e: (not e.is_dir(), e.name.lower()))
            except PermissionError:
                st.error("Permission denied")
                entries = []

            for entry in entries:
                if entry.is_dir():
                    if st.button(f"📁  {entry.name}", key=f"d_{entry.path}",
                                 use_container_width=True):
                        st.session_state.browse_dir = entry.path
                        st.rerun()
                else:
                    ext = Path(entry.name).suffix.lower()
                    label = ("▶ " if st.session_state.file_path == entry.path else "") + entry.name
                    if st.button(label, key=f"f_{entry.path}", use_container_width=True):
                            try:
                                load_file_data(open_any_file(entry.path), entry.name, entry.path)
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

    # ── Search tab ────────────────────────────────────────────────────────────
    with tab_search:
        st.markdown("**Search folder for EDI files**")

        search_dir = st.text_input("Folder to search", value=st.session_state.browse_dir,
                                   key="search_dir_input")
        txn_filter = st.selectbox("Transaction type", ["Any","850","810","856","820","997"],
                                  key="search_txn")
        invoice_num = st.text_input("Invoice Number (BIG02)", placeholder="e.g. INV-001",
                                    key="search_inv")
        po_num      = st.text_input("PO Number (BIG04 / BEG03)", placeholder="e.g. PO-12345",
                                    key="search_po")

        if st.button("Search", type="primary", use_container_width=True):
            with st.spinner("Scanning files…"):
                results = search_folder(search_dir, txn_filter, invoice_num, po_num)
            st.session_state.search_results = results
            st.session_state.show_search    = True
            st.rerun()

        if st.session_state.show_search:
            results = st.session_state.search_results
            st.markdown(f"**{len(results)} match{'es' if len(results)!=1 else ''} found**")
            if not results:
                st.info("No files matched.")
            else:
                for r in results:
                    inv_tag = f"  INV: {r['invoice_num']}" if r["invoice_num"] else ""
                    po_tag  = f"  PO: {r['po_num']}"      if r["po_num"]      else ""
                    label   = f"EDI {r['txn_id'] or '???'} — {r['file_name']}"
                    caption = (inv_tag + po_tag).strip()
                    st.markdown(
                        f'<div class="search-match">'
                        f'<div style="font-size:13px;font-weight:600;color:#fbbf24">{label}</div>'
                        f'<div style="font-size:11px;color:#92400e;margin-top:3px;font-family:\'JetBrains Mono\',monospace">{caption}</div>'
                        f'<div style="font-size:10px;color:#374151;margin-top:4px">{r["path"]}</div>'
                        f'</div>', unsafe_allow_html=True)
                    if st.button("Open", key=f"open_{r['path']}", use_container_width=True):
                        st.session_state.segments   = r["segments"]
                        st.session_state.elem_sep   = r["elem_sep"]
                        st.session_state.seg_term   = r["seg_term"]
                        st.session_state.comp_sep   = r["comp_sep"]
                        st.session_state.file_path  = r["path"]
                        st.session_state.file_name  = r["file_name"]
                        st.session_state.modified   = False
                        st.session_state.active_seg = None
                        st.rerun()

    if st.session_state.file_name:
        st.markdown("---")
        st.markdown(f"**Open:** `{st.session_state.file_name}`")
        if st.session_state.modified:
            st.warning("Unsaved changes")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.segments:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
    height:65vh;gap:14px">
        <div style="font-size:60px">📋</div>
        <div style="font-size:22px;font-weight:600;color:#e5e7eb">EDI Editor</div>
        <div style="color:#4b5563;font-size:14px;text-align:center;max-width:420px;line-height:1.7">
            Load a file from the <b>Load File</b> tab, or use the <b>Search Folder</b> tab
            to find an invoice or purchase order by number.
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

segs     = st.session_state.segments
elem_sep = st.session_state.elem_sep
seg_term = st.session_state.seg_term
issues, missing, txn_id = validate(segs)

# ── Search bar ────────────────────────────────────────────────────────────────────────────
with st.expander("🔍  Search folder for EDI files", expanded=False):
    sr1, sr2, sr3, sr4, sr5 = st.columns([3, 1.2, 1.5, 1.5, 1])
    with sr1:
        sb_dir = st.text_input("Folder", value=st.session_state.browse_dir,
                               key="sb_dir", label_visibility="collapsed",
                               placeholder="Folder path to search…")
    with sr2:
        sb_txn = st.selectbox("Type", ["Any","850","810","856","820","997"],
                              key="sb_txn", label_visibility="collapsed")
    with sr3:
        sb_inv = st.text_input("Invoice # (BIG02)", key="sb_inv",
                               label_visibility="collapsed", placeholder="Invoice number…")
    with sr4:
        sb_po  = st.text_input("PO # (BIG04)", key="sb_po",
                               label_visibility="collapsed", placeholder="PO number…")
    with sr5:
        do_search = st.button("Search", type="primary", use_container_width=True, key="sb_go")

    if do_search:
        with st.spinner("Scanning folder…"):
            res = search_folder(sb_dir, sb_txn, sb_inv, sb_po)
        st.session_state.search_results = res

    results = st.session_state.get("search_results", [])
    if isinstance(results, list) and results:
        st.markdown(f"**{len(results)} file{'s' if len(results)!=1 else ''} found:**")
        for r in results:
            rc1, rc2 = st.columns([10, 1])
            with rc1:
                inv_tag = f"Invoice: {r['invoice_num']}" if r["invoice_num"] else ""
                po_tag  = f"PO: {r['po_num']}"          if r["po_num"]      else ""
                mid     = "  ·  " if inv_tag and po_tag else ""
                st.markdown(
                    f'<div class="search-match">'
                    f'<span style="font-size:13px;font-weight:600;color:#fbbf24">'
                    f'EDI {r["txn_id"] or "???"} — {r["file_name"]}</span>'
                    f'<span style="color:#92400e;font-size:11px;margin-left:10px">{inv_tag}{mid}{po_tag}</span>'
                    f'<div style="font-size:10px;color:#374151;margin-top:3px">{r["path"]}</div>'
                    f'</div>', unsafe_allow_html=True)
            with rc2:
                if st.button("Open", key=f"sb_open_{r['path']}", use_container_width=True):
                    st.session_state.segments   = r["segments"]
                    st.session_state.elem_sep   = r["elem_sep"]
                    st.session_state.seg_term   = r["seg_term"]
                    st.session_state.comp_sep   = r["comp_sep"]
                    st.session_state.file_path  = r["path"]
                    st.session_state.file_name  = r["file_name"]
                    st.session_state.modified   = False
                    st.session_state.active_seg = None
                    st.rerun()
    elif isinstance(results, list) and do_search:
        st.info("No files matched. Try broadening your search.")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Transaction banner + metrics ─────────────────────────────────────────────
b_col, m_col = st.columns([5, 3])
with b_col:
    txn_name = TXN_NAMES.get(txn_id, "Unknown") if txn_id else "Unknown"
    # pull key identifiers for the banner
    inv_num = po_num_val = ""
    for s in segs:
        if s["id"] == "BIG" and len(s["elements"]) > 1:
            inv_num     = s["elements"][1].strip()
            po_num_val  = s["elements"][3].strip() if len(s["elements"]) > 3 else ""
        if s["id"] == "BEG" and len(s["elements"]) > 2 and not po_num_val:
            po_num_val  = s["elements"][2].strip()
    extras = ""
    if inv_num:    extras += f'<span style="color:#6b7280;font-size:12px;margin-left:20px">Invoice: <b style="color:#e5e7eb">{inv_num}</b></span>'
    if po_num_val: extras += f'<span style="color:#6b7280;font-size:12px;margin-left:16px">PO: <b style="color:#e5e7eb">{po_num_val}</b></span>'
    st.markdown(
        f'<div class="txn-banner">'
        f'<div style="font-size:10px;color:#60a5fa;text-transform:uppercase;letter-spacing:.1em;font-weight:600">Transaction</div>'
        f'<div style="margin-top:4px">'
        f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:22px;font-weight:700;color:#e5e7eb">EDI {txn_id or "???"}</span>'
        f'<span style="color:#4b5563;font-size:13px;margin-left:12px">{txn_name}</span>'
        f'{extras}'
        f'</div>'
        f'<div style="margin-top:6px;font-family:\'JetBrains Mono\',monospace;font-size:10px;color:#1e3a5f">'
        f'elem sep: <b style="color:#374151">{elem_sep}</b> &nbsp; seg term: <b style="color:#374151">{seg_term}</b>'
        f'</div></div>', unsafe_allow_html=True)

with m_col:
    mc1, mc2, mc3 = st.columns(3)
    mc1.markdown(f'<div class="metric-card"><div class="metric-num">{len(segs)}</div><div class="metric-lbl">Segments</div></div>', unsafe_allow_html=True)
    ic = "#ef4444" if issues  else "#4ade80"
    mc = "#ef4444" if missing else "#4ade80"
    mc2.markdown(f'<div class="metric-card"><div class="metric-num" style="color:{ic}">{len(issues)}</div><div class="metric-lbl">Issues</div></div>', unsafe_allow_html=True)
    mc3.markdown(f'<div class="metric-card"><div class="metric-num" style="color:{mc}">{len(missing)}</div><div class="metric-lbl">Missing</div></div>', unsafe_allow_html=True)

# ── Issues panel ──────────────────────────────────────────────────────────────
if issues or missing:
    with st.expander(f"⚠️  {len(issues)} issue(s)    ❌  {len(missing)} missing segment(s)", expanded=True):
        for iss in issues:
            st.markdown(f'<div class="issue-row">⚠️  {iss}</div>', unsafe_allow_html=True)
        for m in missing:
            st.markdown(f'<div class="missing-row">❌  {m}</div>', unsafe_allow_html=True)

# ── Save bar ──────────────────────────────────────────────────────────────────
if st.session_state.modified:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    sv1, sv2, sv3, _ = st.columns([2, 2, 2, 4])
    with sv1:
        st.markdown('<span style="color:#fbbf24;font-size:13px">● Unsaved changes</span>', unsafe_allow_html=True)
    with sv2:
        if st.button("💾 Overwrite original", type="primary", use_container_width=True,
                     disabled=not st.session_state.file_path):
            with open(st.session_state.file_path, "w", encoding="utf-8") as f:
                f.write(segments_to_edi(segs, elem_sep, seg_term))
            st.session_state.modified = False
            st.success("Saved — file overwritten.")
            st.rerun()
    with sv3:
        if st.button("📄 Save as new file", use_container_width=True):
            st.session_state["show_saveas"] = True

    if st.session_state.get("show_saveas"):
        p1, p2, p3 = st.columns([4, 1, 1])
        with p1:
            npath = st.text_input("Path", value=st.session_state.file_path or "",
                                  key="saveas_path", label_visibility="collapsed",
                                  placeholder="Full path including filename")
        with p2:
            if st.button("Confirm", type="primary", use_container_width=True):
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(npath)) or ".", exist_ok=True)
                    with open(npath, "w", encoding="utf-8") as f:
                        f.write(segments_to_edi(segs, elem_sep, seg_term))
                    st.session_state.file_path = npath
                    st.session_state.file_name = Path(npath).name
                    st.session_state.modified  = False
                    st.session_state["show_saveas"] = False
                    st.success(f"Saved to `{npath}`")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with p3:
            if st.button("Cancel", use_container_width=True):
                st.session_state["show_saveas"] = False
                st.rerun()

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Full readable file ────────────────────────────────────────────────────────
st.markdown("### File Contents")
st.caption("The entire EDI file — every segment fully expanded with all named fields. Click **Edit** on any segment to change its values in a popup.")

issue_seg_ids = set()
for iss in issues:
    for seg in segs:
        if seg["id"] in iss:
            issue_seg_ids.add(seg["id"])

for idx, seg in enumerate(segs):
    sid      = seg["id"]
    elems    = seg["elements"]
    color    = SEG_COLOR.get(sid, "#6b7280")
    desc     = SEG_DESC.get(sid, "")
    el_names = SEG_ELEMENTS.get(sid, [])
    empties  = sum(1 for e in elems if not e.strip())
    has_issue = sid in issue_seg_ids

    border_color = "#f97316" if has_issue else ("#b91c1c" if empties else "#1c1f2e")
    empty_badge  = (f'<span class="badge b-empty">{empties} empty</span>') if empties else ""
    issue_badge  = '<span class="badge b-issue">⚠ issue</span>' if has_issue else ""

    # Build full field table rows
    max_f  = max(len(elems), len(el_names))
    rows   = ""
    for fi in range(max_f):
        name  = el_names[fi] if fi < len(el_names) else f"Element {fi+1}"
        value = elems[fi].strip() if fi < len(elems) else ""
        vc    = "td-empty" if not value else "td-val"
        vdisp = "(empty)" if not value else value
        rows += (f'<tr>'
                 f'<td class="td-num">{fi+1:02}</td>'
                 f'<td class="td-name">{name}</td>'
                 f'<td class="{vc}">{vdisp}</td>'
                 f'</tr>')

    block = (
        f'<div class="seg-block" style="--c:{color};border-color:{border_color}">'
        f'<div style="display:flex;align-items:center;margin-bottom:10px">'
        f'<span class="seg-title" style="color:{color}">{sid}</span>'
        f'<span class="seg-desc">{desc}</span>'
        f'{empty_badge}{issue_badge}'
        f'</div>'
        f'<table class="field-table">'
        f'<thead><tr>'
        f'<th style="width:28px">#</th>'
        f'<th style="width:210px">Field Name</th>'
        f'<th>Value</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
        f'</div>'
    )

    body_col, btn_col = st.columns([13, 1])
    with body_col:
        st.markdown(block, unsafe_allow_html=True)
    with btn_col:
        st.markdown("<div style='margin-top:36px'></div>", unsafe_allow_html=True)
        if st.button("Edit", key=f"seg_btn_{idx}", use_container_width=True):
            st.session_state.active_seg = idx
            st.rerun()

    st.markdown('<hr style="border:none;border-top:1px solid #0b0d14;margin:0">', unsafe_allow_html=True)

# Trigger dialog
if st.session_state.active_seg is not None:
    edit_dialog(st.session_state.active_seg)