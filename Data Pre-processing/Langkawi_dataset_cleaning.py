import pandas as pd

# Load the Excel file
file_path = "C:/Users/Atifa/Downloads/DIA/Langkawi_api.xlsx"

# Load each sheet
hotels_df = pd.read_excel(file_path, "Langkawi_cleanedhotels_api")
restaurants_df = pd.read_excel(file_path, "Langkawi_cleanedrestaurants_api")
attractions_df = pd.read_excel(file_path, "Langkawi_cleanedattractions_api")

# Rule-Based Imputation for Hotels
def fill_hotel_description(row):
    if pd.isna(row["Description"]):
        return f"{row['Hotel Name']} located in {row['Address']} is a comfortable and well-equipped hotel offering excellent services."
    return row["Description"]

def fill_hotel_website(row):
    return "No link available" if pd.isna(row["Website"]) else row["Website"]

hotels_df["Description"] = hotels_df.apply(fill_hotel_description, axis=1)
hotels_df["Website"] = hotels_df.apply(fill_hotel_website, axis=1)

# Rule-Based Imputation for Restaurants
def fill_restaurant_description(row):
    # Extract cuisines and dietary restrictions safely
    cuisines = ", ".join([row[f"Cuisines {i}"] for i in range(7) if pd.notna(row.get(f"Cuisines {i}"))])
    dietary_list = [row[f"Dietary Restrictions {i}"] for i in range(4) if pd.notna(row.get(f"Dietary Restrictions {i}"))]

    # Separate "Halal" from other dietary options
    halal = "Halal" if "Halal" in dietary_list else ""
    dietary = ", ".join([d for d in dietary_list if d != "Halal"])

    # Build the description
    if cuisines:
        desc = f"{row['Restaurant Name']} offers a variety of cuisines including {cuisines}."
        if dietary:
            desc += f" It also provides {dietary}"
        if halal:
            desc += " and it is Halal."
    else:
        desc = "No Description available"

    return desc
def fill_restaurant_website(row):               
    return "No link available" if pd.isna(row["Website"]) else row["Website"]

def fill_restaurant_menu_url(row):               
    return "No link available" if pd.isna(row["Menu Url"]) else row["Menu Url"]

restaurants_df["Description"] = restaurants_df.apply(fill_restaurant_description, axis=1)
restaurants_df["Website"] = restaurants_df.apply(fill_restaurant_website, axis=1)
restaurants_df["Menu Url"] = restaurants_df.apply(fill_restaurant_menu_url, axis=1)

# Rule-Based Imputation for Attractions
def fill_attraction_description(row):
    subcategories = ", ".join(filter(pd.notna, [row[f"Subcategories {i}"] for i in range(4)]))
    return f"{row['Attraction Name']} is a popular attraction featuring {subcategories}." if pd.isna(row["Description"]) and subcategories else row["Description"]

def fill_attraction_website(row):
    return "No link available" if pd.isna(row["Website"]) else row["Website"]

attractions_df["Description"] = attractions_df.apply(fill_attraction_description, axis=1)
attractions_df["Website"] = attractions_df.apply(fill_attraction_website, axis=1)

# Save updated data back to Excel
with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
    hotels_df.to_excel(writer, sheet_name="Langkawi_cleanedhotels_api", index=False)
    restaurants_df.to_excel(writer, sheet_name="Langkawi_cleanedrestaurants_api", index=False)
    attractions_df.to_excel(writer, sheet_name="Langkawi_cleanedattractions_api", index=False)

print("Missing values imputed and file saved!")


