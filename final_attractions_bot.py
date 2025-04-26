import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from difflib import SequenceMatcher

# Load the model once
model = SentenceTransformer('all-MiniLM-L6-v2')

# step 1
def load_data(filepath, sheet_name):
    return pd.read_excel(filepath, sheet_name=sheet_name)

# step 2
def preprocess_text(df):
    subcats = ['Subcategories 0', 'Subcategories 1', 'Subcategories 2', 'Subcategories 3']
    subcats = [col for col in subcats if col in df.columns]
    text_cols = ['Category'] + subcats + ['Description']
    df[text_cols] = df[text_cols].astype(str)
    df['search_text'] = df[text_cols].agg(' '.join, axis=1).str.lower()
    df['Attraction Name'] = df['Attraction Name'].astype(str).str.lower()
    return df

# step 3
def create_embeddings(df):
    return model.encode(df['search_text'].values, convert_to_numpy=True, normalize_embeddings=True)

# step 4
def create_faiss_index(embeddings):
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index

# step 5
def find_relevant_rows(query, df, index, embeddings):
    query_lower = query.lower().strip()

    name_matches = df[df['Attraction Name'].apply(
        lambda x: SequenceMatcher(None, x, query_lower).ratio() > 0.8
    )]
    if not name_matches.empty:
        return name_matches

    query_embedding = model.encode([query_lower], normalize_embeddings=True)
    distances, indices = index.search(query_embedding, k=5)
    return df.iloc[indices[0]]

# step 6
def get_relevant_info(df):
    cols = ['Attraction Name', 'Address', 'State', 'Country',
            'Description', 'Category', 'Reviews', 'Website', 'Number of Likes']
    return df[[c for c in cols if c in df.columns]]

# step 7
def update_likes(df, liked, path=None, sheet=None):
    df['Number of Likes'] = pd.to_numeric(df['Number of Likes'], errors='coerce').fillna(0).astype(int)
    for name in liked:
        name = name.lower()
        df.loc[df['Attraction Name'] == name, 'Number of Likes'] += 1

    if path and sheet:
        try:
            with pd.ExcelFile(path, engine='openpyxl') as reader:
                sheets = {s: pd.read_excel(reader, sheet_name=s) for s in reader.sheet_names}
            sheets[sheet] = df
            with pd.ExcelWriter(path, engine='openpyxl') as writer:
                for s, data in sheets.items():
                    data.to_excel(writer, sheet_name=s, index=False)
        except Exception as e:
            print(f"Bot: Failed to write likes to Excel. Error: {e}")
    return df

# for ui linking
def handle_request(city, query, liked, sheet_name, filepath, name_col, offset=0, limit=3):
    try:
        
        if query.lower().strip() in ['hi', 'hello', 'hey']:
            return {
                "response": "Hello! How can I help you find attractions?",
                "suggestions": [],
                "total_results": 0,
                "offset": offset,
                "limit": limit
            }


        # Handle exits
        if any(query.lower().startswith(g) for g in ['bye', 'goodbye']) or query.lower() in ['exit', 'quit']:
            return {
                "response": "Goodbye! Thank you for using the attractions guide! Have a great trip.",
                "suggestions": [],
                "total_results": 0,
                "offset": offset,
                "limit": limit
            }
        
        # Load and process data
        df = load_data(filepath, sheet_name)
        df = preprocess_text(df)
        
        # Create embeddings and search index
        embeddings = create_embeddings(df)
        index = create_faiss_index(embeddings)
        
        # Find relevant results
        results = find_relevant_rows(query, df, index, embeddings)
        output = get_relevant_info(results)
        
        # Update likes if needed
        if liked:
            df = update_likes(df, [item.lower() for item in liked], filepath, sheet_name)
        
        if output.empty:
            return {"response": "No results found", "suggestions": []}
        
        # Calculate relevance scores for the requested subset
        query_embedding = model.encode([query.lower()], normalize_embeddings=True)
        output = output.sort_values('Number of Likes', ascending=False)
        
        # Apply offset and limit
        subset = output.iloc[offset:offset+limit]
        
        suggestions = []
        for _, row in subset.iterrows():
            try:
                # Calculate relevance score
                attr_text = row.get('search_text', '')
                attr_embedding = model.encode([attr_text], normalize_embeddings=True)
                faiss_score = float(np.dot(query_embedding, attr_embedding.T)[0][0])
                name_similarity = SequenceMatcher(None, query.lower(), row[name_col].lower()).ratio()
                relevance_score = round((faiss_score + name_similarity) / 2, 2)
            except Exception:
                relevance_score = 0.0

            suggestions.append({
                "name": row[name_col].title(),
                "description": row.get("Description", "No description available"),
                "address": f"{row.get('Address', '')}, {row.get('State', '')}, {row.get('Country', '')}".strip(', '),
                "reviews": row.get("Reviews", "Not available"),
                "website": row.get("Website", "Not available"),
                "likes": int(row.get("Number of Likes", 0)),
                "category": row.get("Category", "Not specified"),
                "relevance": relevance_score
            })
        
        return {
            "suggestions": suggestions,
            "total_results": len(output),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        return {"error": str(e), "suggestions": []}

# to run in terminal
def search_engine(api_mode=False, city=None, query=None):
    file_path = "final_attractions.xlsx"
    
    if not api_mode:
        print("Welcome to the Malaysia Travel Guide!")
        print("Type 'exit' to quit.\n")

    while True:
        liked_attractions = []

        if api_mode:
            location_input = city.lower()
        else:
            location_input = input("Bot: Which location are you exploring? ").lower().strip()

        # Handle greetings
        if any(location_input.startswith(g) for g in ['hi', 'hello', 'hey']):
            if api_mode:
                return {"response": "Hello! Please specify a location."}
            print("Bot: Hello! Please tell me which location you're exploring.")
            continue

        # Handle exits
        if any(location_input.startswith(g) for g in ['bye', 'byee', 'byeee', 'goodbye', 'see ya']) or location_input in ['exit', 'quit', 'bye']:
            if api_mode:
                return {"response": "Goodbye! Enjoy your adventure!"}
            print("Bot: Goodbye! Enjoy your adventure!")
            break

        # Location mapping
        location_map = {
            'kl': 'kl_attractions',
            'kuala lumpur': 'kl_attractions',
            'langkawi': 'Langkawi_attractions',
            'sabah': 'sabah_attractions',
            'putrajaya': 'putrajaya_attractions',
            'johorbahru': 'jb_attractions',
            'Penang': 'Penang_attractions',
            'ipoh': 'Ipoh_attractions',
            'melaka': 'melaka_attractions',
            'selangor': 'selangor_attractions',
            'sarawak': 'sarawak_attractions',
            'pahang': 'pahang_attractions'
        }

        sheet_name = None
        for loc_pattern, sheet in location_map.items():
            if loc_pattern in location_input:
                sheet_name = sheet
                location_name = loc_pattern.title()
                break

        if not sheet_name:
            if api_mode:
                return {"error": "Please enter a valid location."}
            print("Bot: Please enter a valid location.")
            continue

        try:
            data = load_data(file_path, sheet_name)
            data = preprocess_text(data)
            embeddings = create_embeddings(data)
            index = create_faiss_index(embeddings)
        except Exception as e:
            if api_mode:
                return {"error": f"Failed to load {location_name} data. Error: {e}"}
            print(f"Bot: Failed to load {location_name} data. Error: {e}")
            continue

        if not api_mode:
            print(f"Bot: Great! You can now ask about attractions in {location_name}.\n")

        while True:
            if api_mode:
                user_query = query
            else:
                user_query = input("You: ").strip()

            # Handle greetings in query
            if any(user_query.lower().startswith(g) for g in ['hi', 'hello', 'hey']):
                if api_mode:
                    return {"response": "Hello! How can I help you?"}
                print("Bot: Hello! I'm ready to help you find great attractions. 🏝")
                continue

            # Handle exits in query
            if any(user_query.lower().startswith(g) for g in ['bye', 'byee', 'byeee', 'goodbye', 'see ya']) or user_query.lower() in ['exit', 'quit', 'bye', 'back']:
                if liked_attractions:
                    data = update_likes(data, liked_attractions, file_path, sheet_name)
                if api_mode:
                    return {"response": "Goodbye! Happy travels!"}
                print("Bot: Bye! Let me know if you want to search again later. 👋")
                break

            # Process query
            results = find_relevant_rows(user_query, data, index, embeddings)
            output = get_relevant_info(results)

            if output.empty:
                if api_mode:
                    return {"response": "No results found"}
                print("Bot: I couldn't find any matches. Try using different keywords.")
                continue

            output = output.sort_values('Number of Likes', ascending=False).reset_index(drop=True)
            query_embedding = model.encode([user_query.lower()], normalize_embeddings=True)

            suggestions = []
            for _, row in output.head(3).iterrows():
                try:
                    attr_text = row.get('search_text', '')
                    attr_embedding = model.encode([attr_text], normalize_embeddings=True)
                    faiss_score = np.dot(query_embedding, attr_embedding.T)[0][0]
                    name_similarity = SequenceMatcher(None, user_query.lower(), row['Attraction Name'].lower()).ratio()
                    relevance_score = round((faiss_score + name_similarity) / 2, 2)
                except Exception:
                    relevance_score = 0.0

                suggestion = {
                    "name": row['Attraction Name'].title(),
                    "description": row.get('Description', 'No description available'),
                    "address": f"{row.get('Address', '')}, {row.get('State', '')}, {row.get('Country', '')}".strip(', '),
                    "reviews": row.get('Reviews', 'Not available'),
                    "website": row.get('Website', 'Not available'),
                    "likes": int(row.get('Number of Likes', 0)),
                    "category": row.get('Category', 'Not specified'),
                    "relevance": relevance_score
                }
                
                if api_mode:
                    suggestions.append(suggestion)
                else:
                    print(f"\n🏝 {suggestion['name']}")
                    print(f"🔍 Relevance Score: {suggestion['relevance']:.2f}")
                    print(f"{suggestion['description']}")
                    print(f"📍 {suggestion['address']}")
                    print(f"⭐ Reviews: {suggestion['reviews']}")
                    print(f"🌐 Website: {suggestion['website']}")
                    print(f"👍 Number of Likes: {suggestion['likes']}")

                    feedback = input("Bot: Like (.), Dislike (/), or skip: ").strip()
                    if feedback == '.':
                        liked_attractions.append(row['Attraction Name'])
                        print("Bot: Thanks for the like! ❤️")
                    elif feedback == '/':
                        print("Bot: Got it 👎")
                    else:
                        print("Bot: No feedback recorded. ➡️")

            if api_mode:
                return {"suggestions": suggestions}

            shown = 3
            while shown < len(output):
                more = input("\nBot: Would you like to see more attractions? (yes/no): ").strip().lower()
                if more in ['yes', 'y']:
                    for _, row in output.iloc[shown:shown+2].iterrows():
                        print(f"\n🏝 {row['Attraction Name'].title()}")
                        print(f"📝 {row.get('Description', 'No description available')}")
                        print(f"📍 {row.get('Address', '')}, {row.get('State', '')}, {row.get('Country', '')}")
                    shown += 2
                else:
                    print("Bot: Alright! Let me know if you want to search again. 🌟")
                    break

        if api_mode:
            break

        another = input("\nBot: Would you like to explore another location? (yes/no): ").strip().lower()
        if another not in ['yes', 'y']:
            print("Bot: Thank you for using the Attraction Guide. Have a great trip! ✈️")
            break

if __name__ == "__main__":
    search_engine()