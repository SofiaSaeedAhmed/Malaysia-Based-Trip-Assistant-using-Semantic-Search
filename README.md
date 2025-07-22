# Travel Search Engine - Malaysia

## Description

This project presents a **travel search engine** designed to assist users in planning trips across Malaysia by recommending attractions, hotels, and restaurants.  
The system integrates **semantic search** using **Sentence Transformers** and **FAISS**, enhanced with **fuzzy string matching** for robust query handling.  
Additionally, a **feedback mechanism** using user likes supports **preference-based re-ranking**, fostering a more personalised and adaptive recommendation experience.

The core objective is for the model to **understand user queries** and return the **most relevant answers** from the provided database.

• Built a semantic travel recommendation engine for 11 Malaysian cities, covering 100+ attractions, hotels, and 
restaurants using Sentence Transformers (all-MiniLM-L6-v2) and FAISS for dense vector search.

• Engineered a backend pipeline to load, preprocess, and index regional CSV datasets, supporting typo-tolerant fuzzy 
matching and personalised result re-ranking based on user feedback.

• Conducted a usability study with 30 participants, collecting real user queries and feedback via a structured 
questionnaire to evaluate accuracy, relevance, and satisfaction, informing iterative improvements.

---

## Project Structure

| File / Folder | Description |
| :------------ | :---------- |
| `trip-malaysia/` | Contains the React frontend UI setup for the travel chatbot. |
| `final_attractions.xlsx` | Database of attractions across 11 Malaysian cities (organized by sheets). |
| `final_hotels.xlsx` | Database of hotels across 11 Malaysian cities (organized by sheets). |
| `final_restaurants.xlsx` | Database of restaurants across 11 Malaysian cities (organized by sheets). |
| `Questionnaire (Responses).xlsx` | Survey form responses collected from users. |
| `chatbot_server.py` | Backend server connecting the React UI with the chatbot models. Routes user queries to the respective chatbot based on selected city and category. |
| `final_attractions_bot.py` | Handles attraction-related queries using semantic search and fuzzy matching. |
| `final_hotel_bot.py` | Handles hotel-related queries using semantic search and fuzzy matching. |
| `final_restaurant_bot.py` | Handles restaurant-related queries using semantic search and fuzzy matching. |
| `README.md` | Project overview and documentation. |
| `restaurant_metric_calculation.py`| Evaluation metrics for restaurant search engine
| `attractions_metric_calculation.py`| Evaluation metrics for attractions search engine
| `Data Pre-processing/` | Folder which contains pre-processing for all cities

---

## Setup and Usage

### Backend Setup
```bash
# Run the Flask server
python chatbot_server.py

---


