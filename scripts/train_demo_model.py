import os
import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import mlflow
import mlflow.sklearn

# Ensure backend can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.app.config import settings
from ai.stylometry import stylometry_pipeline

def main():
    print("Loading synthetic training data...")
    data_path = os.path.join("data", "training", "pairs.csv")
    
    if not os.path.exists(data_path):
        print(f"Error: Training data not found at {data_path}. Run seed_database.py first.")
        return
        
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} training pairs.")
    
    # Feature extraction
    print("Extracting stylometric and semantic features... (This may take a minute)")
    features = []
    labels = df['same_actor'].values
    
    for _, row in df.iterrows():
        # In a real pipeline, we'd use the pre-computed embeddings to save time.
        # Here we re-calculate just for the demonstration of the pipeline.
        stylo = stylometry_pipeline.analyze(str(row['text1']), str(row['text2']))
        features.append([
            stylo["semantic_similarity"],
            stylo["character_similarity"],
            stylo["lexical_similarity"],
            stylo["punctuation_similarity"],
            stylo["sentence_structure_similarity"],
            stylo["diversity_similarity"]
        ])
        
    X = np.array(features)
    y = np.array(labels)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Setup MLFlow to use local sqlite DB instead of relying on a tracking server that isn't running
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("Attribution_Model_Training")
    
    with mlflow.start_run():
        print("Training Random Forest Classifier...")
        clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        clf.fit(X_train, y_train)
        
        preds = clf.predict(X_test)
        
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds)
        rec = recall_score(y_test, preds)
        f1 = f1_score(y_test, preds)
        
        print(f"\nModel Performance:")
        print(f"Accuracy:  {acc:.4f}")
        print(f"Precision: {prec:.4f}")
        print(f"Recall:    {rec:.4f}")
        print(f"F1 Score:  {f1:.4f}")
        
        mlflow.log_param("model_type", "RandomForest")
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("max_depth", 10)
        
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("precision", prec)
        mlflow.log_metric("recall", rec)
        mlflow.log_metric("f1", f1)
        
        # Save model
        model_dir = os.path.join("backend", "models")
        os.makedirs(model_dir, exist_ok=True)
        mlflow.sklearn.log_model(clf, "attribution_rf_model")
        print("Model successfully logged to MLflow.")

if __name__ == "__main__":
    main()
