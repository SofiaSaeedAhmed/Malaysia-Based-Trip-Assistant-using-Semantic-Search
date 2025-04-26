from flask import Flask, request, jsonify
from flask_cors import CORS
import final_attractions_bot
import final_hotel_bot
import final_restaurant_bot
import numpy as np

app = Flask(__name__)
CORS(app)

BOT_CONFIG = {
    'attractions': {
        'module': final_attractions_bot,
        'sheet': {
            'kl': 'kl_attractions',
            'langkawi': 'Langkawi_attractions',
            'sabah': 'sabah_attractions',
            'putrajaya': 'putrajaya_attractions',
            'johorbahru': 'jb_attractions',
            'penang': 'Penang_attractions',
            'ipoh': 'Ipoh_attractions',
            'melaka': 'melaka_attractions',
            'selangor': 'selangor_attractions',
            'sarawak': 'sarawak_attractions',
            'pahang': 'pahang_attractions'
        },
        'name_col': 'Attraction Name',
        'filepath': 'final_attractions.xlsx'
    },
    'hotels': {
        'module': final_hotel_bot,
        'sheet': {
            'kl': 'kl_hotels',
            'langkawi': 'Langkawi_hotels',
            'sabah': 'sabah_hotels',
            'putrajaya': 'putrajaya_hotels',
            'johorbahru': 'jb_hotels',
            'penang': 'Penang_hotels',
            'ipoh': 'Ipoh_hotels',
            'melaka': 'melaka_hotels',
            'selangor': 'selangor_hotels',
            'sarawak': 'sarawak_hotels',
            'pahang': 'pahang_hotels'
        },
        'name_col': 'Hotel Name',
        'filepath': 'final_hotels.xlsx'
    },
    'restaurants': {
        'module': final_restaurant_bot,
       'sheet': {
            'kl': 'kl_restaurants',
            'langkawi': 'Langkawi_restaurants',
            'sabah': 'sabah_restaurants',
            'putrajaya': 'putrajaya_restaurants',
            'johorbahru': 'jb_restaurants',
            'penang': 'Penang_restaurants',
            'ipoh': 'Ipoh_restaurants',
            'melaka': 'melaka_restaurants',
            'selangor': 'selangor_restaurants',
            'sarawak': 'sarawak_restaurants',
            'pahang': 'pahang_restaurants'
        },
        'name_col': 'Restaurant Name',
        'filepath': 'final_restaurants.xlsx'
    }
}

# connection with bot for incoming stuff
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    city = data.get("city", "").lower()
    category = data.get("category", "").lower()
    query = data.get("query", "").strip()
    liked = data.get("liked", [])

    if not all([city, category, query]):
        return jsonify({"error": "Please provide city, category, and query."}), 400

    if category not in BOT_CONFIG:
        return jsonify({"error": f"Unsupported category: {category}"}), 400

    config = BOT_CONFIG[category]
    sheet_name = config["sheet"].get(city)

    if not sheet_name:
        return jsonify({"error": f"No data available for {city.title()} {category}."}), 404

    try:
        # Use handle_request for API calls
        response = config["module"].handle_request(
            city=city,
            query=query,
            liked=liked,
            sheet_name=sheet_name,
            filepath=config["filepath"],
            name_col=config["name_col"]
        )
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# show more button  
@app.route("/show_more", methods=["POST"])
def show_more():
    data = request.get_json()
    city = data.get("city", "").lower()
    category = data.get("category", "").lower()
    query = data.get("query", "").strip()
    offset = data.get("offset", 0)  # Number of results already shown
    limit = data.get("limit", 2)    # Number of additional results to show

    if not all([city, category, query]):
        return jsonify({"error": "Please provide city, category, and query."}), 400

    if category not in BOT_CONFIG:
        return jsonify({"error": f"Unsupported category: {category}"}), 400

    config = BOT_CONFIG[category]
    sheet_name = config["sheet"].get(city)

    if not sheet_name:
        return jsonify({"error": f"No data available for {city.title()} {category}."}), 404

    try:
        # Use handle_request with offset and limit
        response = config["module"].handle_request(
            city=city,
            query=query,
            liked=[],
            sheet_name=sheet_name,
            filepath=config["filepath"],
            name_col=config["name_col"],
            offset=offset,
            limit=limit
        )
        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    
# Add endpoint to track likes
@app.route("/like", methods=["POST"])
def like_item():
    data = request.get_json()
    city = data.get("city", "").lower()
    category = data.get("category", "").lower()
    item_name = data.get("name", "").lower()

    if not all([city, category, item_name]):
        return jsonify({"error": "Please provide city, category, and item name."}), 400

    if category not in BOT_CONFIG:
        return jsonify({"error": f"Unsupported category: {category}"}), 400

    config = BOT_CONFIG[category]
    sheet_name = config["sheet"].get(city)
    
    if not sheet_name:
        return jsonify({"error": f"No data available for {city.title()} {category}."}), 404

    try:
        bot = config["module"]
        filepath = config["filepath"]
        
        # Load data
        df = bot.load_data(filepath, sheet_name)
        
        # Update likes
        df = bot.update_likes(df, [item_name], filepath, sheet_name)
        
        return jsonify({"success": True, "message": f"Successfully liked {item_name.title()}"})
    
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

    
if __name__ == "__main__":
    app.run(debug=True)