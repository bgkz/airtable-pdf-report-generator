import pandas as pd
import math


REQUIRED_COLUMNS = [
    "Sample_ID", "Gene_Target", "Read_Count", "Coverage_Depth",
    "Quality_Score", "Mutation_Status",
]


def read_sequencing_csv(csv_path):
    data = pd.read_csv(csv_path, dtype="string", encoding="utf-8-sig")
    missing = set(REQUIRED_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"CSV-Pflichtspalten fehlen: {', '.join(sorted(missing))}")
    if data.empty:
        raise ValueError("Die CSV enthaelt keine Messungen.")
    for column in REQUIRED_COLUMNS:
        data[column] = data[column].str.strip().replace("", pd.NA)
    if data[["Sample_ID", "Gene_Target"]].isna().any().any():
        raise ValueError("Sample_ID und Gene_Target duerfen nicht leer sein.")
    for column, pattern in [
        ("Read_Count", None), ("Coverage_Depth", r"[xX]$"),
        ("Quality_Score", r"^[Qq]"),
    ]:
        values = data[column]
        if pattern:
            values = values.str.replace(pattern, "", regex=True)
        numeric = pd.to_numeric(values, errors="coerce")
        invalid = (data[column].notna() & numeric.isna()) | (numeric < 0)
        invalid |= numeric.map(lambda v: False if pd.isna(v) else not math.isfinite(v))
        if column == "Read_Count":
            invalid |= numeric.notna() & (numeric % 1 != 0)
        if invalid.any():
            raise ValueError(f"Ungueltige Zahlen in CSV-Spalte {column}.")
        data[column] = numeric
    data["Mutation_Status"] = data["Mutation_Status"].str.upper()
    return data


def merge_sequencing_data(records, csv_path, airtable_id_column="Sample_ID"):
    csv_data = read_sequencing_csv(csv_path)
    if "Sample_ID" not in csv_data.columns:
        raise ValueError("In der CSV fehlt die Spalte Sample_ID.")

    airtable_data = pd.DataFrame([record["fields"] for record in records])
    if airtable_id_column not in airtable_data.columns:
        raise ValueError(
            f"In Airtable fehlt die Spalte {airtable_id_column!r}. "
            f"Vorhandene Spalten: {', '.join(airtable_data.columns)}"
        )

    csv_data["Sample_ID"] = csv_data["Sample_ID"].str.strip()
    airtable_data[airtable_id_column] = (
        airtable_data[airtable_id_column].astype("string").str.strip()
    )
    # Leere IDs sollen nicht miteinander verknuepft werden.
    airtable_data = airtable_data.loc[
        airtable_data[airtable_id_column].notna()
        & airtable_data[airtable_id_column].ne("")
    ]

    if airtable_data[airtable_id_column].duplicated().any():
        raise ValueError("Airtable enthaelt doppelte Proben-IDs; Zuordnung ist nicht eindeutig.")
    return csv_data.merge(
        airtable_data,
        how="left",
        left_on="Sample_ID",
        right_on=airtable_id_column,
        validate="many_to_one",
        suffixes=("", "_airtable"),
        indicator="Zuordnung",
    )
