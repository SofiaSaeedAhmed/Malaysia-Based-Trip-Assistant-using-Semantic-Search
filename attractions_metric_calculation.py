import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# --- Load dataset ---
df = pd.read_excel('final_attractions.xlsx', sheet_name='jb_attractions')

# --- Combine subcategories ---
subcats = [col for col in df.columns if col.lower().startswith('subcategories')]
df['Full Category'] = df[subcats].astype(str).agg(' '.join, axis=1).str.lower()

# --- Prepare text for embedding ---
df['Attraction Name'] = df['Attraction Name'].astype(str)
df['Description'] = df['Description'].astype(str)
df['search_text'] = (df['Attraction Name'] + ' ' + df['Description']).str.lower()

# --- Load model ---
model = SentenceTransformer('all-MiniLM-L6-v2')

# --- Build FAISS index ---
vectors = model.encode(df['search_text'].tolist(), show_progress_bar=True, normalize_embeddings=True)
index = faiss.IndexFlatIP(vectors.shape[1])
index.add(np.array(vectors).astype(np.float32))

# --- Semantic search function ---
def semantic_search(query, vectorizer, index, df, top_k=10):
    query_vec = vectorizer.encode([query], normalize_embeddings=True)
    D, I = index.search(np.array(query_vec).astype(np.float32), top_k)
    return df.iloc[I[0]]['Attraction Name'].str.lower().tolist()

# --- Evaluation ---
K = 6
category_queries = ['Shopping', 'Museums', 'Nightlife', 'Zoos', 'Sights & Landmarks', 'Fun & Games']
results_attr = []

for cat in category_queries:
    relevant_items = df[df['Full Category'].str.contains(cat, case=False, na=False)]
    if relevant_items.empty:
        print(f"No relevant items found for '{cat}'\n")
        continue

    relevant_names = set(relevant_items['Attraction Name'].str.lower())
    retrieved_names = semantic_search(cat + " attraction", model, index, df, top_k=K)

    hits = sum(1 for r in retrieved_names if r in relevant_names)
    recall = hits / len(relevant_names) if relevant_names else 0
    precision = hits / len(retrieved_names) if retrieved_names else 0

    print(f"Category: {cat}")
    print(f"Total relevant: {len(relevant_names)}, Retrieved: {len(retrieved_names)}, Hits: {hits}")
    print(f"Recall@{K}: {recall:.2f} | Precision@{K}: {precision:.2f}\n")

    results_attr.append({'Category': cat, 'Recall': recall, 'Precision': precision})

# --- Plotting ---
df_attr_eval = pd.DataFrame(results_attr)
df_attr_long = df_attr_eval.melt(id_vars='Category', value_vars=['Recall', 'Precision'],
                                 var_name='Metric', value_name='Score')

plt.figure(figsize=(10, 6))
sns.barplot(data=df_attr_long, x='Category', y='Score', hue='Metric')
plt.title('Recall and Precision per Attraction Category')
plt.ylabel('Score')
plt.ylim(0, 1.0)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
