from __future__ import annotations

import hashlib
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(REPO_ROOT, "evidence", "index.json")
DATASHEET_DIR = os.path.join(REPO_ROOT, "evidence", "datasheets")

#: Every document a claim in this repository rests on. `url` is where the file
#: came from; `document_id` is the revision the file itself states, which is
#: what a later reader has to match to know they are reading the same thing.
SOURCES = {
    "fan_4wire_intel": {
        "file": "datasheets/fan_4wire_pwm_intel.pdf",
        "url": "https://glkinst.com/cables/cable_pics/4_Wire_PWM_Spec.pdf",
        "retrieved": "2026-09-02",
        "document_id": "4-Wire Pulse Width Modulation (PWM) Controlled Fans "
                       "Specification, Revision 1.3, September 2005",
        "applies_to": ["4-wire fan interface"],
    },
    "stm32g030_st": {
        "file": "datasheets/stm32g030_st.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "753f35401d4598e355b1dd55569495e1.pdf",
        "retrieved": "2026-09-02",
        "document_id": "STM32G030x6/x8 datasheet DS12991 Rev 3",
        "applies_to": ["STM32G030K8T6TR"],
    },
    "ht75rxx_holtek": {
        "file": "datasheets/ht75rxx_holtek.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "59abfa7ca0c1b0cd081d8e8f60c28ed0.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Holtek HT75Rxx-1 30V 150mA LDO, Rev. 1.01, 2025-12-03",
        "applies_to": ["HT75R33-1A"],
    },
    "ao4407a_aos": {
        "file": "datasheets/ao4407a_aos.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "6bf17916e7274c4fb32122c6ec48f2db.pdf",
        "retrieved": "2026-09-02",
        "document_id": "AO4407A Rev3, Jan 2008",
        "applies_to": ["AO4407A"],
    },
    "ao3401a_aos": {
        "file": "datasheets/ao3401a_aos.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "fee353dd1e9e0bc90b295f14f381aa4c.pdf",
        "retrieved": "2026-09-02",
        "document_id": "AO3401A Rev 3.1, December 2023",
        "applies_to": ["AO3401A"],
    },
    "ao3400a_aos": {
        "file": "datasheets/ao3400a_aos.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "130876b936da464599428c58fd8de8f6.pdf",
        "retrieved": "2026-09-02",
        "document_id": "AO3400A Rev 3, December 2011",
        "applies_to": ["AO3400A"],
    },
    "pptc_jk_msmd200_jinrui": {
        "file": "datasheets/pptc_jk_msmd200_jinrui.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "14df65c86fb650ee5ee4c7432d762291.pdf",
        "retrieved": "2026-09-02",
        "document_id": "JinRui JK-mSMD200 PPTC devices, Edition A0",
        "applies_to": ["JK-MSMD200-24V"],
    },
    "pptc_jk_msmd_series_jinrui": {
        "file": "datasheets/pptc_jk_msmd_series_jinrui.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "bf3f0b74de54755047f1f9ac46a3e07e.pdf",
        "retrieved": "2026-09-02",
        "document_id": "JinRui JK-mSMD Series 1812 PPTC specification",
        "applies_to": ["JK-mSMD200 thermal derating and pad layout"],
    },
    "smaj_littelfuse": {
        "file": "datasheets/smaj_littelfuse.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "bf298e2c0542e0172af23908598fa548.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Littelfuse SMAJ series 400 W TVS datasheet",
        "applies_to": ["SMAJ16A"],
    },
    "smf16a_jingdao": {
        "file": "datasheets/smf16a_jingdao.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "e2079ce6902d97aebf17ffdc9542d2e7.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Jingdao SMF series 200 W SOD-123FL TVS datasheet",
        "applies_to": ["SMF16A"],
    },
    "b5819w_jscj": {
        "file": "datasheets/b5819w_jscj.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "4ac2c059be7c462694ab0715ce987a85.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Jiangsu Changjing B5819W SOD-123 Schottky datasheet",
        "applies_to": ["B5819W SL"],
    },
    "tpd1e10b06_ti": {
        "file": "datasheets/tpd1e10b06_ti.pdf",
        "url": "https://www.ti.com/lit/ds/symlink/tpd1e10b06.pdf",
        "retrieved": "2026-09-02",
        "document_id": "SLLSEB1G, revised August 2024",
        "applies_to": ["TPD1E10B06DPYR"],
    },
    "kt0603r_kento": {
        "file": "datasheets/kt0603r_kento.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "011ec3e8cb1e825f6961d29bc4db4c7a.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Hubei KENTO KT-0603R specification",
        "applies_to": ["KT-0603R"],
    },
    "res_0603_uniroyal": {
        "file": "datasheets/res_0603_uniroyal.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "0a975aaa49b7c97f38a963127be4a823.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Uniroyal 0603W chip resistor series specification",
        "applies_to": ["0603WAF470JT5E", "0603WAF1000T5E", "0603WAF1501T5E",
                       "0603WAF2201T5E", "0603WAF4701T5E", "0603WAF1002T5E",
                       "0603WAF3302T5E", "0603WAF1003T5E"],
    },
    "res_0603_zero_uniroyal": {
        "file": "datasheets/res_0603_zero_uniroyal.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "f42da6c80a0747bae77c2f98f4e46d1d.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Uniroyal 0603 zero-ohm jumper specification",
        "applies_to": ["0603WAF0000T5E"],
    },
    "mlcc_yageo_cc0603": {
        "file": "datasheets/mlcc_yageo_cc0603.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "23ccee80ee542e7cf156a772bb589942.pdf",
        "retrieved": "2026-09-02",
        "document_id": "YAGEO CC series 0603 MLCC specification",
        "applies_to": ["CC0603KRX7R9BB104", "CC0603KRX7R9BB102"],
    },
    "mlcc_10uf_samsung": {
        "file": "datasheets/mlcc_10uf_samsung.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "02336ea48ea44ca18c72517dd3cb7b47.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Samsung CL21A106KAYNNNE specification",
        "applies_to": ["CL21A106KAYNNNE"],
    },
    "elcap_knscha_rvt": {
        "file": "datasheets/elcap_knscha_rvt.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "e7e9594ab11f940fdef4c48584211b89.pdf",
        "retrieved": "2026-09-02",
        "document_id": "KNSCHA RVT series SMD aluminium electrolytic "
                       "specification",
        "applies_to": ["RVT100UF25V67RV0011"],
    },
    "kf128_cixikefa": {
        "file": "datasheets/kf128_cixikefa.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "29da5b9f86f95d4ff856cbb6af0595a9.pdf",
        "retrieved": "2026-09-02",
        "document_id": "Cixi Kefa KF128-5.08 drawing",
        "applies_to": ["KF128-5.08-2P-AA"],
    },
    "fanheader_2510_cax": {
        "file": "datasheets/fanheader_2510_cax.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "ca7b10a9292dd87d34a6a79c45e2045c.pdf",
        "retrieved": "2026-09-02",
        "document_id": "2510 wire-to-board connector specification PB131 "
                       "version 17",
        "applies_to": ["KF2510-4AGW-GW"],
    },
    "header1x3_kinghelm": {
        "file": "datasheets/header1x3_kinghelm.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "d6b219f8eaec54d3e4d25f61d08e45ba.pdf",
        "retrieved": "2026-09-02",
        "applies_to": ["KH-2.54PH180-1X3P-L11.5"],
    },
    "header1x5_kinghelm": {
        "file": "datasheets/header1x5_kinghelm.pdf",
        "url": "https://datasheet.lcsc.com/datasheet/pdf/"
               "543df74cc4da0256c46d4113479c5bcc.pdf",
        "retrieved": "2026-09-02",
        "applies_to": ["KH-2.54PH180-1X5P-L11.5"],
    },
}


def digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_index():
    entries = {}
    for name in sorted(SOURCES):
        source = SOURCES[name]
        path = os.path.join(REPO_ROOT, "evidence", source["file"])
        entry = dict(source)
        entry["sha256"] = digest(path)
        entry["bytes"] = os.path.getsize(path)
        entries[name] = entry
    return {"schema_version": 1, "documents": entries}


def load_index():
    with open(INDEX_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_index():
    with open(INDEX_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(compute_index(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return INDEX_PATH


def verify():
    """Every recorded document present and unchanged, and nothing unrecorded."""
    recorded = load_index()["documents"]
    present = {name for name in os.listdir(DATASHEET_DIR)
               if name.endswith((".pdf", ".json"))}
    referenced = {os.path.basename(entry["file"])
                  for entry in recorded.values()}
    problems = []
    for name in sorted(referenced - present):
        problems.append(("missing_file", name))
    for name in sorted(present - referenced):
        problems.append(("unreferenced_file", name))
    for name in sorted(recorded):
        entry = recorded[name]
        path = os.path.join(REPO_ROOT, "evidence", entry["file"])
        if not os.path.isfile(path):
            continue
        if digest(path) != entry["sha256"]:
            problems.append(("digest_mismatch", name))
    return problems


if __name__ == "__main__":
    sys.stdout.write(write_index() + "\n")
