"""
Generate DC-1: Medicine Master CSV
Based on Section DC-1 in MedTrace_Research_and_Execution_Plan.md:
12 essential medicines spanning OPD staples and programme commodities.
"""

import os
import csv

MEDICINES = [
    {
        "medicine_id": "MED-001",
        "generic_name": "paracetamol",
        "strength": "500mg",
        "form": "tablet",
        "atc_code": "N02BE01",
        "level_min": "PHC",
        "shelf_life_months": 36,
        "demand_group": "N02BE",
        "supply_group": "OPD_STAPLE",
        "source_url": "https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.02"
    },
    {
        "medicine_id": "MED-002",
        "generic_name": "ibuprofen",
        "strength": "400mg",
        "form": "tablet",
        "atc_code": "M01AE01",
        "level_min": "PHC",
        "shelf_life_months": 36,
        "demand_group": "M01AE",
        "supply_group": "OPD_STAPLE",
        "source_url": "https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.02"
    },
    {
        "medicine_id": "MED-003",
        "generic_name": "diclofenac",
        "strength": "50mg",
        "form": "tablet",
        "atc_code": "M01AB05",
        "level_min": "CHC",
        "shelf_life_months": 36,
        "demand_group": "M01AB",
        "supply_group": "OPD_STAPLE",
        "source_url": "https://cdsco.gov.in/opencms/opencms/en/Drugs/NLEM/"
    },
    {
        "medicine_id": "MED-004",
        "generic_name": "amoxicillin",
        "strength": "500mg",
        "form": "capsule",
        "atc_code": "J01CA04",
        "level_min": "PHC",
        "shelf_life_months": 24,
        "demand_group": "TEMPLATE_ANTIBIOTIC",
        "supply_group": "OPD_STAPLE",
        "source_url": "https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.02"
    },
    {
        "medicine_id": "MED-005",
        "generic_name": "cetirizine",
        "strength": "10mg",
        "form": "tablet",
        "atc_code": "R06AE07",
        "level_min": "PHC",
        "shelf_life_months": 36,
        "demand_group": "R06",
        "supply_group": "OPD_STAPLE",
        "source_url": "https://cdsco.gov.in/opencms/opencms/en/Drugs/NLEM/"
    },
    {
        "medicine_id": "MED-006",
        "generic_name": "salbutamol",
        "strength": "4mg",
        "form": "tablet",
        "atc_code": "R03CC02",
        "level_min": "PHC",
        "shelf_life_months": 24,
        "demand_group": "R03",
        "supply_group": "OPD_STAPLE",
        "source_url": "https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.02"
    },
    {
        "medicine_id": "MED-007",
        "generic_name": "metformin",
        "strength": "500mg",
        "form": "tablet",
        "atc_code": "A10BA02",
        "level_min": "PHC",
        "shelf_life_months": 36,
        "demand_group": "TEMPLATE_CHRONIC",
        "supply_group": "OPD_STAPLE",
        "source_url": "https://cdsco.gov.in/opencms/opencms/en/Drugs/NLEM/"
    },
    {
        "medicine_id": "MED-008",
        "generic_name": "amlodipine",
        "strength": "5mg",
        "form": "tablet",
        "atc_code": "C08CA01",
        "level_min": "PHC",
        "shelf_life_months": 36,
        "demand_group": "TEMPLATE_CHRONIC",
        "supply_group": "OPD_STAPLE",
        "source_url": "https://cdsco.gov.in/opencms/opencms/en/Drugs/NLEM/"
    },
    {
        "medicine_id": "MED-009",
        "generic_name": "artemether + lumefantrine",
        "strength": "20mg + 120mg",
        "form": "tablet",
        "atc_code": "P01BF01",
        "level_min": "PHC",
        "shelf_life_months": 24,
        "demand_group": "TEMPLATE_SEASONAL",
        "supply_group": "PROGRAMME_MALARIA",
        "source_url": "https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.02"
    },
    {
        "medicine_id": "MED-010",
        "generic_name": "efavirenz",
        "strength": "600mg",
        "form": "tablet",
        "atc_code": "J05AG03",
        "level_min": "District Hospital",
        "shelf_life_months": 36,
        "demand_group": "TEMPLATE_PROGRAMME",
        "supply_group": "PROGRAMME_HIV",
        "source_url": "https://data.usaid.gov"
    },
    {
        "medicine_id": "MED-011",
        "generic_name": "lamivudine + zidovudine",
        "strength": "150mg + 300mg",
        "form": "tablet",
        "atc_code": "J05AR01",
        "level_min": "CHC",
        "shelf_life_months": 36,
        "demand_group": "TEMPLATE_PROGRAMME",
        "supply_group": "PROGRAMME_HIV",
        "source_url": "https://data.usaid.gov"
    },
    {
        "medicine_id": "MED-012",
        "generic_name": "levonorgestrel + ethinylestradiol",
        "strength": "0.15mg + 0.03mg",
        "form": "tablet",
        "atc_code": "G03AA07",
        "level_min": "PHC",
        "shelf_life_months": 36,
        "demand_group": "TEMPLATE_PROGRAMME",
        "supply_group": "PROGRAMME_FAMILY_PLANNING",
        "source_url": "https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.02"
    }
]

def main():
    os.makedirs(os.path.join("data", "real"), exist_ok=True)
    out_file = os.path.join("data", "real", "medicine_master.csv")
    fieldnames = list(MEDICINES[0].keys())
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(MEDICINES)
    print(f"[+] Created {out_file} with {len(MEDICINES)} essential medicines.")

if __name__ == "__main__":
    main()
