from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import json
import requests  # Import the requests library

app = Flask(__name__)

# MongoDB connection
client = MongoClient("mongodb+srv://pranavsutar4747:mhTgPm5wPoIFFrYB@cluster0.ej4sy.mongodb.net")  
db = client.test  # Replace with your actual database name

# Helper function to convert ObjectId to string
def parse_json(data):
    return json.loads(json.dumps(data, default=str))

# Function to get recommendations from the external API
def get_recommendations(data):
    try:
        # Validate the input data
        if not data:
            return {"status": "error", "message": "No data provided"}

        # Make a POST request to the external API
        api_url = "https://product-recommendation-system-5cm7.onrender.com/predict"
        headers = {"Content-Type": "application/json"}  # Set the content type to JSON
        response = requests.post(api_url, json=data, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Return the response from the external API
            return response.json()
        else:
            # Handle errors from the external API
            return {
                "status": "error",
                "message": "Failed to get recommendations",
                "external_api_status_code": response.status_code,
                "external_api_response": response.text
            }

    except Exception as e:
        # Handle any exceptions
        return {"status": "error", "message": str(e)}

@app.route('/')
def home():
    return 'Flask app running on render!'

@app.route('/getData', methods=['POST'])
def getData():
    try:
        # Get the user ID from the request (assuming JSON data)
        data = request.json
        user_id = data.get('id')

        if not user_id:
            return jsonify({"status": "error", "message": "User ID is required"}), 400

        # Fetch the user document by ID
        user = db.users.find_one({"_id": ObjectId(user_id)}, {"_id": 1, "likedPost": 1})

        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # Fetch full post details for each likedPost
        if "likedPost" in user and user["likedPost"]:  # Check if likedPost exists and is not empty
            post_ids = [ObjectId(post_id) for post_id in user["likedPost"]]  # Convert postId strings to ObjectId
            liked_posts = list(db.posts.find({"_id": {"$in": post_ids}}))
            user["likedPosts"] = liked_posts
        else:
            user["likedPosts"] = []  # If likedPost is empty, set it to an empty array

        # Process likedPosts
        if len(user['likedPosts']) > 0:
            # Remove unwanted fields
            user["likedPosts"] = [
                {key: value for key, value in post.items() if key not in ["updatedAt", "images", "createdAt", "__v", "description"]}
                for post in user["likedPosts"]
            ]

            # Convert categories
            category_mapping = {
                "books-stationery": "stationery",
                "study-tools-electronics": "electronics",
                "educational-accessories": "stationery",
                "uniforms-apparel": "apparel",
                "other": "other"
            }
            for post in user["likedPosts"]:
                if "category" in post and post["category"] in category_mapping:
                    post["category"] = category_mapping[post["category"]]

            # Rename fields
            field_mapping = {
                "_id": "product_id",
                "category": "cat_0",
                "title": "brand",
                "likeCount": "ts_month",
                "userId": "user_id"
            }
            for post in user["likedPosts"]:
                renamed_post = {field_mapping.get(key, key): value for key, value in post.items()}
                post.clear()
                post.update(renamed_post)

            # Convert ObjectId to strings
            for post in user["likedPosts"]:
                if "product_id" in post:
                    post["product_id"] = str(post["product_id"])
                if "user_id" in post:
                    post["user_id"] = str(post["user_id"])

            # Get recommendations for each post
            responses = []
            for post in user['likedPosts']:
                recommendation = get_recommendations(post)
                responses.append(recommendation)

        else:
            return jsonify({"status":'false','message':'No user data found','user':'No prediction'})
        # Convert responses to JSON
        responses = parse_json(responses)

        return jsonify({"status": "true", "user": responses}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, port=5001)