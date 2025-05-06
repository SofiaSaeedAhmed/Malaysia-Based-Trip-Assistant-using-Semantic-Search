import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# ----------------- Load dataset----------------
df = pd.read_excel('final_restaurants.xlsx', sheet_name='sarawak_restaurants')

# Combine all cuisine columns into one
cuisine_cols = [col for col in df.columns if col.lower().startswith('cuisines')]
df['Cuisines'] = df[cuisine_cols].apply(
    lambda row: ', '.join(filter(lambda x: x.strip().lower() not in ['', 'nan'], row.astype(str))), axis=1
)

df['Cuisines'] = df['Cuisines'].astype(str)
df['Restaurant Name'] = df['Restaurant Name'].astype(str)

# -------------- Load sentence transformer model ----------------
model = SentenceTransformer('all-MiniLM-L6-v2')

# --- Build FAISS index ---
names = df['Restaurant Name'].tolist()
vectors = model.encode(names, show_progress_bar=True, normalize_embeddings=True)
index = faiss.IndexFlatIP(vectors.shape[1])
index.add(np.array(vectors).astype(np.float32))

# --- Semantic search function ---
def semantic_search(query, vectorizer, index, names, top_k=6):
    query_vec = vectorizer.encode([query], normalize_embeddings=True)
    D, I = index.search(np.array(query_vec).astype(np.float32), top_k)
    return [names[i].lower() for i in I[0] if i < len(names)]

# --- Evaluation ---
cuisine_queries = ['indian', 'italian', 'asian', 'thai', 'malaysian', 'chinese']
K = 6
results_list = []

for cuisine in cuisine_queries:
    relevant_items = df[df['Cuisines'].str.contains(cuisine, case=False, na=False)]

    if relevant_items.empty:
        print(f"No relevant items found for '{cuisine}'\n")
        continue

    relevant_names = set(relevant_items['Restaurant Name'].str.lower())
    retrieved_names = semantic_search(f"{cuisine} restaurant", model, index, names, top_k=K)

    hits = sum(1 for r in retrieved_names if r in relevant_names)
    retrieved_count = len(retrieved_names)

    recall_at_k = hits / len(relevant_names) if len(relevant_names) > 0 else 0
    precision_at_k = hits / retrieved_count if retrieved_count > 0 else 0

    print(f"Evaluation for: '{cuisine}' restaurants")
    print(f"Total relevant items: {len(relevant_names)}")
    print(f"Retrieved@{retrieved_count}: {retrieved_count}")
    print(f"Hits: {hits}")
    print(f"Recall@{retrieved_count}: {recall_at_k:.2f}")
    print(f"Precision@{retrieved_count}: {precision_at_k:.2f}\n")

    results_list.append({'Cuisine': cuisine, 'Recall': recall_at_k, 'Precision': precision_at_k})

# --- Plotting ---
df_eval = pd.DataFrame(results_list)

df_long = df_eval.melt(id_vars='Cuisine', value_vars=['Recall', 'Precision'], 
                       var_name='Metric', value_name='Score')

plt.figure(figsize=(10, 6))
sns.barplot(data=df_long, x='Cuisine', y='Score', hue='Metric')
plt.title('Recall and Precision per Cuisine')
plt.ylabel('Score')
plt.ylim(0, 1.0)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
