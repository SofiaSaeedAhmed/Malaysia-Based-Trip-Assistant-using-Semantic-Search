import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from difflib import SequenceMatcher
import openpyxl

# load model
model = SentenceTransformer('all-MiniLM-L6-v2')

# step 1
def load_data(filepath, sheet_name):
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    for col in df.select_dtypes(include=['int64', 'float64']):
        df[col] = pd.to_numeric(df[col], downcast='integer' if df[col].dtype == 'int64' else 'float')
    return df

# step 2
def preprocess_text(df):
    cuisine_cols = [col for col in df.columns if col.lower().startswith('cuisines')]
    diet_cols = [col for col in df.columns if col.lower().startswith('dietary restrictions')]
    text_cols = ['Restaurant Name', 'Description', 'Category'] + cuisine_cols + diet_cols

    for col in text_cols:
        df[col] = df[col].fillna('').astype(str).str.strip()

    df['search_text'] = df[text_cols].agg(' | '.join, axis=1).str.lower()
    df['Restaurant Name'] = df['Restaurant Name'].str.lower()
    return df, cuisine_cols, diet_cols

# step 3
def create_embeddings(df):
    return model.encode(df['search_text'].tolist(), convert_to_tensor=True, show_progress_bar=True)

# step 4
def create_faiss_index(embeddings):
    embeddings_np = embeddings.cpu().numpy().astype('float32')
    faiss.normalize_L2(embeddings_np)
    index = faiss.IndexFlatIP(embeddings_np.shape[1])
    index.add(embeddings_np)
    return index

# step 5
def find_relevant_rows(query, df, index, embeddings, cuisine_cols, diet_cols):
    query_lower = query.lower().strip()
    df = df.copy()

    # First check for exact name matches
    exact_matches = df[df['Restaurant Name'] == query_lower]
    if not exact_matches.empty:
        return exact_matches

    # Handle negative cuisine conditions (like "non-chinese")
    negative_cuisine = None
    if 'non-' in query_lower:
        for cuisine in ['chinese', 'indian', 'malay', 'western', 'arabic', 'japanese', 'thai']:
            if f'non-{cuisine}' in query_lower:
                negative_cuisine = cuisine
                break

    # Handle dietary restrictions
    diet_keywords = {'vegetarian', 'vegan', 'halal', 'gluten-free', 'kosher', 'vegetarian-friendly'}
    found_diet = next((diet for diet in diet_keywords if diet in query_lower), None)

    # Handle cuisine types
    cuisine_keywords = {
        'pakistani', 'indian', 'chinese', 'italian', 'thai',
        'japanese', 'mexican', 'western', 'arabic', 'malay',
        'spanish', 'european', 'american', 'asian', 'german', 'sri lankan'
    }
    found_cuisine = next((cuisine for cuisine in cuisine_keywords if cuisine in query_lower), None)

    # Apply filters
    filtered_df = df.copy()
    
    # If we found a dietary restriction, filter by it
    if found_diet:
        filtered_df = filtered_df[filtered_df[diet_cols].apply(
            lambda row: any(found_diet in str(cell).lower() for cell in row), axis=1)]
    
    # If we found a cuisine to exclude, filter it out
    if negative_cuisine:
        filtered_df = filtered_df[~filtered_df[cuisine_cols].apply(
            lambda row: any(negative_cuisine in str(cell).lower() for cell in row), axis=1)]
    # Otherwise if we found a positive cuisine filter, apply it
    elif found_cuisine:
        filtered_df = filtered_df[filtered_df[cuisine_cols].apply(
            lambda row: any(found_cuisine in str(cell).lower() for cell in row), axis=1)]

    # If we have any filters applied and got results, return them
    if (found_diet or negative_cuisine or found_cuisine) and not filtered_df.empty:
        return filtered_df

    # Fall back to other search methods if no filters matched
    location_phrases = ['restaurants in', 'restaurants near', 'places to eat in',
                       'restaurants around', 'eateries in']
    found_location = next((query_lower.split(phrase)[-1].strip()
                         for phrase in location_phrases if phrase in query_lower), None)
    if found_location:
        location_matches = df[df['Address'].str.contains(found_location, case=False, na=False) |
                           df['State'].str.contains(found_location, case=False, na=False)]
        if not location_matches.empty:
            return location_matches

    category_matches = df[df['Category'].str.contains(query_lower, case=False, na=False)]
    if not category_matches.empty:
        return category_matches

    # Fall back to semantic search if no direct matches
    query_embedding = model.encode([query_lower])
    distances, indices = index.search(query_embedding, k=5)
    mask = distances[0] > 0.3
    filtered_indices = indices[0][mask]

    if len(filtered_indices) > 0:
        results = df.iloc[filtered_indices].copy()
        results['name_similarity'] = results['Restaurant Name'].apply(
            lambda x: SequenceMatcher(None, query_lower, x).ratio())
        results['query_embedding'] = [query_embedding[0]] * len(results)
        return results.sort_values('name_similarity', ascending=False)

    return pd.DataFrame()

# step 6
def get_relevant_info(df, cuisine_cols, diet_cols):
    info = df.copy()

    info['Cuisines'] = info[cuisine_cols].apply(
        lambda row: ', '.join(filter(lambda x: x not in ['', 'nan'], row.astype(str))), axis=1)

    info['Dietary Info'] = info[diet_cols].apply(
        lambda row: ', '.join(filter(lambda x: x not in ['', 'nan'], row.astype(str))), axis=1)

    display_cols = ['Restaurant Name', 'Address', 'State', 'Country', 
                    'Description', 'Category', 'Reviews', 
                    'Website', 'Cuisines', 'Dietary Info', 'Number of Likes', 'search_text']

    for col in display_cols:
        if col in info.columns:
            info[col] = info[col].replace(['', 'nan'], 'Not specified')

    return info[[col for col in display_cols if col in info.columns]]

# step 7
def update_likes(df, liked_restaurants, file_path=None, sheet_name=None):
    df['Number of Likes'] = pd.to_numeric(df['Number of Likes'], errors='coerce').fillna(0).astype(int)
    for restaurant in liked_restaurants:
        df.loc[df['Restaurant Name'] == restaurant, 'Number of Likes'] += 1

    if liked_restaurants and file_path and sheet_name:
        try:
            with pd.ExcelFile(file_path, engine='openpyxl') as reader:
                sheets_dict = {sheet: pd.read_excel(reader, sheet_name=sheet) for sheet in reader.sheet_names}
            sheets_dict[sheet_name] = df

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for sheet, sheet_data in sheets_dict.items():
                    sheet_data.to_excel(writer, sheet_name=sheet, index=False)

        except Exception as e:
            print(f"Bot: Failed to write likes to Excel. Error: {e}")

    return df

# for ui linking
def handle_request(city, query, liked, sheet_name, filepath, name_col, offset=0, limit=3):
    try:
        if query.lower().strip() in ['hi', 'hello', 'hey']:
            return {
                "response": "Hello! How can I help you find restaurants?",
                "suggestions": [],
                "total_results": 0,
                "offset": offset,
                "limit": limit
            }

        # Handle exits
        if any(query.lower().startswith(g) for g in ['bye', 'goodbye']) or query.lower() in ['exit', 'quit']:
            return {
                "response": "Goodbye! Enjoy your food adventure!",
                "suggestions": [],
                "total_results": 0,
                "offset": offset,
                "limit": limit
            }
        
        # Load and process data
        df = load_data(filepath, sheet_name)
        df, cuisine_cols, diet_cols = preprocess_text(df)
        
        # Create embeddings and search index
        embeddings = create_embeddings(df)
        index = create_faiss_index(embeddings)
        
        # Find relevant results
        results = find_relevant_rows(query, df, index, embeddings, cuisine_cols, diet_cols)
        output = get_relevant_info(results, cuisine_cols, diet_cols)
        
        # Update likes if needed
        if liked:
            df = update_likes(df, liked, filepath, sheet_name)
        
        if output.empty:
            return {
                "response": "No results found",
                "suggestions": [],
                "total_results": 0,
                "offset": offset,
                "limit": limit
            }
        
        # Calculate relevance scores
        query_embedding = model.encode([query.lower()], normalize_embeddings=True)
        output = output.sort_values('Number of Likes', ascending=False)
        
        # Apply offset and limit
        subset = output.iloc[offset:offset+limit]
        
        suggestions = []
        for _, row in subset.iterrows():
            try:
                # Calculate relevance score
                rest_text = row.get('search_text', '')
                rest_embedding = model.encode([rest_text], normalize_embeddings=True)
                faiss_score = float(np.dot(query_embedding, rest_embedding.T)[0][0])
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
                "cuisines": row.get("Cuisines", "Not specified"),
                "dietary": row.get("Dietary Info", "Not specified"),
                "likes": int(row.get("Number of Likes", 0)),
                "relevance": relevance_score
            })
        
        return {
            "suggestions": suggestions,
            "total_results": len(output),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "suggestions": [],
            "total_results": 0,
            "offset": offset,
            "limit": limit
        }

# to run in terminal
def search_engine(api_mode=False, city=None, query=None, liked=None):
    file_path = "final_restaurants.xlsx"

    location_map = {
    "kl": "kl_restaurants", "kuala lumpur": "kl_restaurants",
    "langkawi": "Langkawi_restaurants", "sabah": "sabah_restaurants",
    "putrajaya": "putrajaya_restaurants", "johorbahru": "jb_restaurants",
    "Penang": "Penang_restaurants", "ipoh": "Ipoh_restaurants",
    "melaka": "melaka_restaurants", "selangor": "selangor_restaurants",
    "sarawak": "sarawak_restaurants", "pahang": "pahang_restaurants"}

    if not api_mode:
        print("Welcome to the Malaysia Restaurant Guide!")
        print("Type 'exit' to quit.\n")

    while True:
        liked_restaurants = liked if api_mode else []

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
                return {"response": "Goodbye! Enjoy your food adventure!"}
            print("Bot: Goodbye! Enjoy your food adventure!")
            break

        sheet_name = location_map.get(location_input)
        if not sheet_name:
            if api_mode:
                return {"error": "Please enter a valid location."}
            print("Bot: Please enter a valid location.")
            continue

        try:
            data = load_data(file_path, sheet_name)
            data, cuisine_cols, diet_cols = preprocess_text(data)
            embeddings = create_embeddings(data)
            index = create_faiss_index(embeddings)
        except Exception as e:
            if api_mode:
                return {"error": f"Failed to load data. Error: {e}"}
            print(f"Bot: Failed to load data. Error: {e}")
            continue

        if not api_mode:
            print(f"Bot: Great! You can now ask about restaurants in {location_input.title()}.\n")

        while True:
            if api_mode:
                user_query = query
            else:
                user_query = input("You: ").strip()

            # Handle greetings in query
            if any(user_query.lower().startswith(g) for g in ['hi', 'hello', 'hey']):
                if api_mode:
                    return {"response": "Hello! How can I help you?"}
                print("Bot: Hello! I'm ready to help you find great restaurants. 🍽️")
                continue

            # Handle exits in query
            if any(user_query.lower().startswith(g) for g in ['bye', 'byee', 'byeee', 'goodbye', 'see ya']) or user_query.lower() in ['exit', 'quit', 'bye', 'back']:
                if liked_restaurants:
                    data = update_likes(data, liked_restaurants, file_path, sheet_name)
                if api_mode:
                    return {"response": "Goodbye! Bon appétit!"}
                print("Bot: Bye! Let me know if you want to search again later. 👋")
                break

            # Process query
            results = find_relevant_rows(user_query, data, index, embeddings, cuisine_cols, diet_cols)
            output = get_relevant_info(results, cuisine_cols, diet_cols)

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
                    rest_text = row.get('search_text', '')
                    rest_embedding = model.encode([rest_text], normalize_embeddings=True)
                    faiss_score = np.dot(query_embedding, rest_embedding.T)[0][0]
                    name_similarity = SequenceMatcher(None, user_query.lower(), row['Restaurant Name'].lower()).ratio()
                    relevance_score = round((faiss_score + name_similarity) / 2, 2)
                except Exception:
                    relevance_score = 0.0

                suggestion = {
                    "name": row['Restaurant Name'].title(),
                    "description": row.get('Description', 'No description available'),
                    "address": f"{row.get('Address', '')}, {row.get('State', '')}, {row.get('Country', '')}".strip(', '),
                    "reviews": row.get('Reviews', 'Not available'),
                    "website": row.get('Website', 'Not available'),
                    "cuisines": row.get('Cuisines', 'Not specified'),
                    "dietary": row.get('Dietary Info', 'Not specified'),
                    "likes": int(row.get('Number of Likes', 0)),
                    "relevance": relevance_score
                }
                
                if api_mode:
                    suggestions.append(suggestion)
                else:
                    print(f"\n🍴 {suggestion['name']}")
                    print(f"🔍 Relevance Score: {suggestion['relevance']:.2f}")
                    print(f"{suggestion['description']}")
                    print(f"📍 {suggestion['address']}")
                    print(f"🍽️ Cuisines: {suggestion['cuisines']}")
                    print(f"🌱 Dietary: {suggestion['dietary']}")
                    print(f"⭐ Reviews: {suggestion['reviews']}")
                    print(f"🌐 Website: {suggestion['website']}")
                    print(f"👍 Number of Likes: {suggestion['likes']}")

                    feedback = input("Bot: Like (.), Dislike (/), or skip: ").strip()
                    if feedback == '.':
                        liked_restaurants.append(row['Restaurant Name'])
                        print("Bot: Thanks for the like! ❤️")
                    elif feedback == '/':
                        print("Bot: Got it, not your taste. 👎")
                    else:
                        print("Bot: No feedback recorded. ➡️")

            if api_mode:
                return {"suggestions": suggestions}

            shown = 3
            while shown < len(output):
                more = input("\nBot: Would you like to see more options? (yes/no): ").strip().lower()
                if more in ['yes', 'y']:
                    for _, row in output.iloc[shown:shown+2].iterrows():
                        print(f"\n🍴 {row['Restaurant Name'].title()}")
                        print(f"📝 {row.get('Description', 'No description available')}")
                        print(f"📍 {row.get('Address', '')}, {row.get('State', '')}, {row.get('Country', '')}")
                    shown += 2
                else:
                    print("Bot: Alright! Let me know if you want to search again. 🍽️")
                    break

        if api_mode:
            break

        another = input("\nBot: Search another location? (yes/no): ").strip().lower()
        if another not in ['yes', 'y']:
            print("Bot: Thank you for using the Restaurant Guide. Bon appétit!")
            break

if __name__ == "__main__":
    search_engine()