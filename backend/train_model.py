
"""
Train and evaluate a reproducible Sleep Disorder Classification model.

Expected dataset:
    sleep_health.csv

Expected target column:
    Sleep Disorder

Output:
    models/sleep_disorder_pipeline.joblib
    models/model_metrics.json

The saved artifact is a complete scikit-learn Pipeline, including
preprocessing and the trained classifier.
"""

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier


warnings.filterwarnings("ignore", category=FutureWarning)

# --------------------------------------------------
# 1. PATHS AND CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = BASE_DIR / "sleep_health.csv"
MODEL_DIR = BASE_DIR / "models"

MODEL_PATH = MODEL_DIR / "sleep_disorder_pipeline.joblib"
METRICS_PATH = MODEL_DIR / "model_metrics.json"

TARGET_COLUMN = "Sleep Disorder"
RANDOM_STATE = 42
TEST_SIZE = 0.20


# --------------------------------------------------
# 2. LOAD DATASET
# --------------------------------------------------

def load_dataset():
    """Load the dataset and validate its required columns."""

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}\n"
            "Place sleep_health.csv in the same folder as train_model.py."
        )

    df = pd.read_csv(DATASET_PATH)

    # Remove accidental spaces from column names.
    df.columns = df.columns.str.strip()

    # Remove a possible CSV index column.
    df = df.loc[
        :,
        ~df.columns.str.match(r"^Unnamed:\s*\d+$", case=False)
    ]

    if TARGET_COLUMN not in df.columns:
        raise ValueError(
            f"Target column '{TARGET_COLUMN}' is missing.\n"
            f"Available columns: {df.columns.tolist()}"
        )

    # Normalize text values.
    for column in df.select_dtypes(include=["object", "string"]).columns:
        df[column] = df[column].map(
            lambda value: value.strip()
            if isinstance(value, str)
            else value
        )

    # Empty target strings are treated as missing.
    df[TARGET_COLUMN] = df[TARGET_COLUMN].replace("", np.nan)

    # Rows without known labels cannot be used for supervised training.
    before = len(df)
    df = df.dropna(subset=[TARGET_COLUMN]).copy()
    removed = before - len(df)

    if removed:
        print(
            f"Removed {removed} rows with missing "
            f"'{TARGET_COLUMN}' labels."
        )

    if df.empty:
        raise ValueError(
            "No labeled rows remain after removing missing target values."
        )

    # Remove rows where the target is not a usable string.
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(str).str.strip()

    print("\nDataset loaded successfully.")
    print(f"Dataset shape: {df.shape}")
    print("\nTarget distribution:")
    print(df[TARGET_COLUMN].value_counts())

    return df


# --------------------------------------------------
# 3. CLEAN AND PREPARE FEATURES
# --------------------------------------------------

def prepare_features(df):
    """Clean dataset columns and engineer blood pressure features."""

    df = df.copy()

    # Remove an identifier column if present.
    identifier_columns = [
        column
        for column in df.columns
        if column.strip().lower() in {"person id", "person_id", "id"}
    ]

    df = df.drop(columns=identifier_columns, errors="ignore")

    # --------------------------------------------------
    # BMI CATEGORY NORMALIZATION
    # --------------------------------------------------
    # Preserve the distinct categories:
    # Normal, Normal Weight, Overweight, and Obese.
    if "BMI Category" in df.columns:
        df["BMI Category"] = (
            df["BMI Category"]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    # --------------------------------------------------
    # BLOOD PRESSURE FEATURE ENGINEERING
    # --------------------------------------------------
    # Expected examples: 126/83, 125/80, 120/80.
    # Extract systolic and diastolic pressure separately.

    if "Blood Pressure" in df.columns:
        bp = (
            df["Blood Pressure"]
            .astype("string")
            .str.strip()
            .str.extract(
                r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$"
            )
        )

        df["Systolic BP"] = pd.to_numeric(
            bp[0], errors="coerce"
        )

        df["Diastolic BP"] = pd.to_numeric(
            bp[1], errors="coerce"
        )

        df = df.drop(columns=["Blood Pressure"])

    # Convert numeric-looking columns into numeric data.
    numeric_candidates = [
        "Age",
        "Sleep Duration",
        "Quality of Sleep",
        "Physical Activity Level",
        "Stress Level",
        "Heart Rate",
        "Daily Steps",
        "Systolic BP",
        "Diastolic BP",
    ]

    for column in numeric_candidates:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column], errors="coerce"
            )

    # Normalize common categorical column names.
    categorical_candidates = [
        "Gender",
        "Occupation",
        "BMI Category",
    ]

    for column in categorical_candidates:
        if column in df.columns:
            df[column] = df[column].astype("string")

    return df


# --------------------------------------------------
# 4. BUILD THE MACHINE LEARNING PIPELINE
# --------------------------------------------------

def build_pipeline(X):
    """Build preprocessing and classification into one pipeline."""

    numeric_columns = X.select_dtypes(
        include=["number"]
    ).columns.tolist()

    categorical_columns = [
        column
        for column in X.columns
        if column not in numeric_columns
    ]

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
            ),
        ]
    )

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                numeric_columns,
            ),
            (
                "categorical",
                categorical_pipeline,
                categorical_columns,
            ),
        ],
        remainder="drop",
    )

    classifier = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessing),
            ("classifier", classifier),
        ]
    )

    return pipeline


# --------------------------------------------------
# 5. TRAIN AND EVALUATE
# --------------------------------------------------

def train_and_evaluate():
    """Train, evaluate, and save the complete model pipeline."""

    df = load_dataset()
    df = prepare_features(df)

    # Separate inputs and target.
    X = df.drop(columns=[TARGET_COLUMN])
    y = df[TARGET_COLUMN]

    if X.empty or X.shape[1] == 0:
        raise ValueError(
            "No usable input features remain after preprocessing."
        )

    if y.nunique() < 2:
        raise ValueError(
            "At least two target classes are required for classification."
        )

    # Stratification preserves class proportions when possible.
    class_counts = y.value_counts()
    stratify_target = (
        y
        if class_counts.min() >= 2
        and int(len(y) * TEST_SIZE) >= y.nunique()
        else None
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=stratify_target,
    )

    print("\nTraining configuration:")
    print(f"Training rows: {len(X_train)}")
    print(f"Testing rows: {len(X_test)}")
    print(f"Features: {X.shape[1]}")
    print(f"Classes: {sorted(y.unique().tolist())}")

    model = build_pipeline(X_train)

    # Fit all preprocessing steps using training data only.
    model.fit(X_train, y_train)

    # Evaluate on held-out data.
    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    macro_f1 = f1_score(
        y_test,
        predictions,
        average="macro",
        zero_division=0,
    )
    weighted_f1 = f1_score(
        y_test,
        predictions,
        average="weighted",
        zero_division=0,
    )

    labels = sorted(y.unique().tolist())

    report = classification_report(
        y_test,
        predictions,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=labels,
    )

    print("\n" + "=" * 55)
    print("SLEEP DISORDER MODEL EVALUATION")
    print("=" * 55)

    print(f"Accuracy:   {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print(f"Macro F1:   {macro_f1:.4f}")
    print(f"Weighted F1:{weighted_f1:.4f}")

    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=labels,
            zero_division=0,
        )
    )

    print("Confusion matrix:")
    print("Label order:", labels)
    print(matrix)

    # --------------------------------------------------
    # 6. SAVE MODEL AND METRICS
    # --------------------------------------------------

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_PATH)

    metrics = {
        "model_name": "RandomForestClassifier",
        "target_column": TARGET_COLUMN,
        "dataset": DATASET_PATH.name,
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "training_rows": int(len(X_train)),
        "testing_rows": int(len(X_test)),
        "feature_columns": X.columns.tolist(),
        "classes": labels,
        "accuracy": float(accuracy),
        "accuracy_percent": round(float(accuracy * 100), 2),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
    }

    with open(
        METRICS_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(metrics, file, indent=4)

    print("\nSaved files:")
    print(f"Model:   {MODEL_PATH}")
    print(f"Metrics: {METRICS_PATH}")

    print(
        "\nTraining complete. "
        "The saved pipeline includes preprocessing and the classifier."
    )

    return model, metrics


# --------------------------------------------------
# 7. ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    train_and_evaluate()
