import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from difflib import SequenceMatcher

# load the model
model = SentenceTransformer('all-MiniLM-L6-v2')

# step 1
def load_data(filepath, sheet_name):
    try:
        return pd.read_excel(filepath, sheet_name=sheet_name)
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        raise

# step 2
def preprocess_text(df):
    text_cols = ['Hotel Name', 'Description', 'Category', 'Address']
    for col in text_cols:
        df[col] = df[col].fillna('').astype(str).str.strip()
    df['search_text'] = df[text_cols].agg(' | '.join, axis=1).str.lower()
    
    if 'Number of Likes' not in df.columns:
        df['Number of Likes'] = 0
    
    return df

# step 3
def create_embeddings(df):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return model.encode(df['search_text'].tolist(), convert_to_tensor=True)

# step 4
def create_faiss_index(embeddings):
    embeddings_np = embeddings.cpu().numpy().astype('float32')
    faiss.normalize_L2(embeddings_np)
    index = faiss.IndexFlatIP(embeddings_np.shape[1])
    index.add(embeddings_np)
    return index

# step 5
def find_relevant_rows(query, df, index, embeddings):
    query_lower = query.lower().strip()
    
    # 1. Exact name matches
    exact_matches = df[df['Hotel Name'].str.lower() == query_lower]
    if not exact_matches.empty:
        return exact_matches
    
    # 2. Address matches
    address_matches = df[df['Address'].str.lower().str.contains(query_lower)]
    if not address_matches.empty:
        return address_matches.head(3)
    
    # 3. Partial name matches
    partial_matches = df[df['Hotel Name'].str.lower().str.contains(query_lower)]
    if not partial_matches.empty:
        return partial_matches.head(3)
    
    # 4. Semantic search
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode([query_lower])
    distances, indices = index.search(query_embedding, k=5)
    mask = distances[0] > 0.3
    if np.any(mask):
        return df.iloc[indices[0][mask]]
    
    # 5. Fuzzy matching
    df['name_similarity'] = df['Hotel Name'].str.lower().apply(
        lambda x: SequenceMatcher(None, query_lower, x).ratio()
    )
    return df.nlargest(3, 'name_similarity')

# step 6
def get_relevant_info(df):
    required_cols = ['Hotel Name', 'Address', 'State', 'Country', 
                     'Description', 'Category', 'Reviews', 'Website', 'Number of Likes']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ''
    info = df[required_cols].copy()
    info['Hotel Name'] = info['Hotel Name'].str.title()
    info['Address'] = info['Address'].replace('', 'Address not available')
    return info

# step 7
def update_likes(df, liked_hotels, file_path=None, sheet_name=None):
    df['Hotel Name'] = df['Hotel Name'].astype(str).str.lower()
    df['Number of Likes'] = pd.to_numeric(df['Number of Likes'], errors='coerce').fillna(0).astype(int)

    for hotel in liked_hotels:
        hotel = hotel.lower().strip()
        if hotel in df['Hotel Name'].values:
            df.loc[df['Hotel Name'] == hotel, 'Number of Likes'] += 1

    if file_path and sheet_name:
        try:
            with pd.ExcelFile(file_path, engine='openpyxl') as reader:
                sheets_dict = {sheet: pd.read_excel(reader, sheet_name=sheet) for sheet in reader.sheet_names}

            sheets_dict[sheet_name] = df

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for sheet_name, sheet_data in sheets_dict.items():
                    sheet_data.to_excel(writer, sheet_name=sheet_name, index=False)

        except Exception as e:
            print(f"Bot: Failed to write likes to Excel. Error: {e}")

    return df

# for ui linking
def handle_request(city, query, liked, sheet_name, filepath, name_col, offset=0, limit=3):
    try:
        if query.lower().strip() in ['hi', 'hello', 'hey']:
            return {
                "response": "Hello! How can I help you find hotels?",
                "suggestions": [],
                "total_results": 0,
                "offset": offset,
                "limit": limit
            }

        # Handle exits
        if any(query.lower().startswith(g) for g in ['bye', 'goodbye']) or query.lower() in ['exit', 'quit']:
            return {
                "response": "Goodbye! Hope you enjoy your trip!",
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
            df = update_likes(df, liked, filepath, sheet_name)
        
        if output.empty:
            return {"response": "No results found", "suggestions": []}
        
        # Calculate relevance scores
        query_embedding = model.encode([query.lower()], normalize_embeddings=True)
        output = output.sort_values('Number of Likes', ascending=False)

        # Apply offset and limit
        subset = output.iloc[offset:offset+limit]
        
        suggestions = []
        for _, row in subset.iterrows():
            try:
                # Calculate relevance score
                hotel_text = row.get('search_text', '')
                hotel_embedding = model.encode([hotel_text], normalize_embeddings=True)
                faiss_score = float(np.dot(query_embedding, hotel_embedding.T)[0][0])
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
def search_engine(api_mode=False, city=None, query=None, liked=None):
    file_path = "final_hotels.xlsx"
    location_map = {
        "kl": "kl_hotels", "kuala lumpur": "kl_hotels",
        "langkawi": "Langkawi_hotels", "sabah": "sabah_hotels",
        "putrajaya": "putrajaya_hotels", "johorbahru": "jb_hotels",
        "Penang": "Penang_hotels", "ipoh": "Ipoh_hotels",
        "melaka": "melaka_hotels", "selangor": "selangor_hotels",
        "sarawak": "sarawak_hotels", "pahang": "pahang_hotels"
    }

    if not api_mode:
        print("Welcome to the Malaysia Hotel Guide!")
        print("Type 'exit' to quit.\n")

    while True:
        liked_hotels = liked if api_mode else []

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
                return {"response": "Goodbye! Enjoy your stay!"}
            print("Bot: Goodbye! Enjoy your stay!")
            break

        sheet_name = location_map.get(location_input)
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
                return {"error": f"Failed to load data. Error: {e}"}
            print(f"Bot: Failed to load data. Error: {e}")
            continue

        if not api_mode:
            print(f"Bot: Great! You can now ask about hotels in {location_input.title()}.\n")

        while True:
            if api_mode:
                user_query = query
            else:
                user_query = input("You: ").strip()

            # Handle greetings in query
            if any(user_query.lower().startswith(g) for g in ['hi', 'hello', 'hey']):
                if api_mode:
                    return {"response": "Hello! How can I help you?"}
                print("Bot: Hello! I'm ready to help you find great hotels. 🏨")
                continue

            # Handle exits in query
            if any(user_query.lower().startswith(g) for g in ['bye', 'byee', 'byeee', 'goodbye', 'see ya']) or user_query.lower() in ['exit', 'quit', 'bye', 'back']:
                if liked_hotels:
                    data = update_likes(data, liked_hotels, file_path, sheet_name)
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
                print("Bot: No matches found. Try different keywords.")
                continue

            output = output.sort_values('Number of Likes', ascending=False).reset_index(drop=True)
            query_embedding = model.encode([user_query.lower()], normalize_embeddings=True)

            suggestions = []
            for _, row in output.head(3).iterrows():
                try:
                    hotel_text = row.get('search_text', '')
                    hotel_embedding = model.encode([hotel_text], normalize_embeddings=True)
                    faiss_score = np.dot(query_embedding, hotel_embedding.T)[0][0]
                    name_similarity = SequenceMatcher(None, user_query.lower(), row['Hotel Name'].lower()).ratio()
                    relevance_score = round((faiss_score + name_similarity) / 2, 2)
                except Exception:
                    relevance_score = 0.0

                suggestion = {
                    "name": row['Hotel Name'].title(),
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
                    print(f"\n🏨 {suggestion['name']}")
                    print(f"🔍 Relevance Score: {suggestion['relevance']:.2f}")
                    print(f"{suggestion['description']}")
                    print(f"📍 {suggestion['address']}")
                    print(f"⭐ Reviews: {suggestion['reviews']}")
                    print(f"🌐 Website: {suggestion['website']}")
                    print(f"👍 Number of Likes: {suggestion['likes']}")

                    feedback = input("Bot: Like (.), Dislike (/), or skip: ").strip()
                    if feedback == '.':
                        liked_hotels.append(row['Hotel Name'])
                        print("Bot: Thanks for the like! ❤️")
                    elif feedback == '/':
                        print("Bot: Got it 👎")
                    else:
                        print("Bot: No feedback recorded. ➡️")

            if api_mode:
                return {"suggestions": suggestions}

            shown = 3
            while shown < len(output):
                more = input("\nBot: Would you like to see more hotels? (yes/no): ").strip().lower()
                if more in ['yes', 'y']:
                    for _, row in output.iloc[shown:shown+2].iterrows():
                        print(f"\n🏨 {row['Hotel Name'].title()}")
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
            print("Bot: Thank you for using the Hotel Guide. Have a pleasant stay! 🛎️")
            break

if __name__ == "__main__":
    search_engine()
