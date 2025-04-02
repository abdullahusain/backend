# Install required packages
# Run these commands in your terminal before starting:
# pip install flask flask-cors pandas sqlalchemy pyngrok waitress

# Import necessary modules
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from pyngrok import ngrok
import pandas as pd
import sys

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Database setup using SQLite
DATABASE_URL = 'sqlite:///users.db'
engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()

# User table definition
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

# Create tables
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Load movies data
try:
    movies = pd.read_csv('movies.csv')
    print("\n✅ Movies data loaded successfully!")
    print("Columns in dataset:", movies.columns)

    required_columns = ['name', 'year', 'movie_rated', 'run_length', 'genres', 'release_date', 'rating']
    # Ensure all required columns are present
    if not all(col in movies.columns for col in required_columns):
        print("❌ Error: Missing required columns in movies.csv")
        sys.exit()

    # Ensure 'genres' column values are string
    movies['genres'] = movies['genres'].astype(str)
    print("Available genres:", movies['genres'].unique())

    # Emotion-to-genres mapping
    emotion_to_genres = {
        "happy": ["comedy", "animation", "music", "romance", "fantasy"],
        "sad": ["drama", "biography", "history", "war"],
        "angry": ["action", "thriller", "crime"],
        "mixed": list(movies['genres'].unique())  # Use all genres for mixed emotions
    }
except FileNotFoundError:
    print("❌ Error: movies.csv file not found. Please ensure it is in the same directory.")
    sys.exit()
except Exception as e:
    print(f"❌ Error loading movies.csv: {e}")
    sys.exit()

# Flask routes
@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        email = data['email']
        password = data['password']

        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            return jsonify({"message": "User already exists"}), 400

        new_user = User(email=email, password=password)
        session.add(new_user)
        session.commit()
        return jsonify({"message": "User registered successfully"}), 200
    except Exception as e:
        print(f"❌ Error in signup: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data['email']
        password = data['password']

        user = session.query(User).filter_by(email=email, password=password).first()
        if user:
            return jsonify({"message": "Login successful"}), 200
        return jsonify({"message": "Invalid email or password"}), 401
    except Exception as e:
        print(f"❌ Error in login: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

@app.route('/recommend/<emotion>', methods=['GET'])
def recommend_movies(emotion):
    try:
        print(f"Emotion received: {emotion}")

        # Get genres for the given emotion
        genres = emotion_to_genres.get(emotion, [])
        if not genres:
            return jsonify({"message": "Invalid emotion"}), 400

        print(f"Genres for emotion '{emotion}': {genres}")

        # Filter movies based on genres, accounting for multiple genres
        filtered_movies = movies[movies['genres'].apply(
            lambda x: any(genre.lower().strip() in [g.lower().strip() for g in x.split(";")] for genre in genres)
        )]

        print(f"Number of matched movies: {len(filtered_movies)}")

        if filtered_movies.empty:
            print("No movies match the given emotion.")
            return jsonify([])  # Return an empty list if no matches found

        # Sample up to 3 movies
        movie_samples = filtered_movies.sample(min(3, len(filtered_movies)), replace=False)
        recommendations = []
        for _, row in movie_samples.iterrows():
            recommendations.append({
                "name": row['name'],
                "year": row['year'],
                "movie_rated": row['movie_rated'],
                "run_length": row['run_length'],
                "genres": row['genres'],
                "release_date": row['release_date'],
                "rating": row['rating'],
                "image_url": f"https://via.placeholder.com/200?text={row['name']}"
            })

        print(f"Recommendations: {recommendations}")
        return jsonify(recommendations)
    except Exception as e:
        print(f"Error in recommend_movies: {e}")
        return jsonify({"message": "Internal Server Error"}), 500



# Function to start Waitress and Ngrok
def start_server():
    try:
        # Set Ngrok authtoken
        ngrok.set_auth_token("2t41BULWDTjpJKB62VVGwv5bXgZ_3g5j5aSmoqaBy5m1juRMC")  # Replace with your actual token

        # Start Ngrok tunnel
        public_url = ngrok.connect(5000)
        print("\n🌐 Ngrok Public URL:", public_url.public_url)

        # Start Waitress server
        from waitress import serve
        print("\n🚀 Starting Waitress server...")
        serve(app, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit()

if __name__ == '__main__':
    start_server()
