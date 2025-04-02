# Import necessary modules
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
import pandas as pd
import os
import sys
import requests

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Database setup using SQLite (stored in Render-compatible directory)
DB_DIR = "/opt/render/db/"
os.makedirs(DB_DIR, exist_ok=True)  # Ensure directory exists
DB_PATH = os.path.join(DB_DIR, "users.db")
DATABASE_URL = f'sqlite:///{DB_PATH}'

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
    if not all(col in movies.columns for col in required_columns):
        print("❌ Error: Missing required columns in movies.csv")
        sys.exit()

    movies['genres'] = movies['genres'].astype(str)
    print("Available genres:", movies['genres'].unique())

    # Extract all unique sub-genres from the dataset
    all_genres = set()
    for genre_list in movies['genres'].dropna():
        for genre in genre_list.split(";"):  # Split multi-genre rows
            all_genres.add(genre.strip().lower())  # Standardize genres

    emotion_to_genres = {
        "happy": ["comedy", "animation", "music", "romance", "fantasy"],
        "sad": ["drama", "biography", "history", "war"],
        "angry": ["action", "thriller", "crime"],
        "mixed": list(all_genres)  # Use all extracted sub-genres
    }
except FileNotFoundError:
    print("❌ Error: movies.csv file not found. Please ensure it is in the same directory.")
    sys.exit()
except Exception as e:
    print(f"❌ Error loading movies.csv: {e}")
    sys.exit()

# OMDb API Key and Base URL
OMDB_API_KEY = "d8eec40d"
OMDB_BASE_URL = "http://www.omdbapi.com/"

def fetch_movie_poster(movie_name):
    """Fetch movie poster from OMDb API"""
    try:
        params = {"t": movie_name, "apikey": OMDB_API_KEY}
        response = requests.get(OMDB_BASE_URL, params=params)
        data = response.json()
        
        if data.get("Response") == "True":
            return data.get("Poster", "https://via.placeholder.com/200?text=No+Image")
        else:
            return "https://via.placeholder.com/200?text=No+Image"
    except Exception as e:
        print(f"Error fetching poster for {movie_name}: {e}")
        return "https://via.placeholder.com/200?text=No+Image"

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
        genres = emotion_to_genres.get(emotion, [])

        if not genres:
            return jsonify({"message": "Invalid emotion"}), 400

        print(f"Genres for emotion '{emotion}': {genres}")

        # Filter movies based on genres (handling multiple genres per movie)
        filtered_movies = movies[movies['genres'].apply(
            lambda x: any(genre.lower().strip() in x.lower() for genre in genres)
        )]

        print(f"Number of matched movies: {len(filtered_movies)}")

        if filtered_movies.empty:
            return jsonify([])

        movie_samples = filtered_movies.sample(min(3, len(filtered_movies)), replace=False)
        recommendations = []
        
        for _, row in movie_samples.iterrows():
            poster_url = fetch_movie_poster(row['name'])  # Fetch real movie poster

            recommendations.append({
                "name": row['name'],
                "year": row['year'],
                "movie_rated": row['movie_rated'],
                "run_length": row['run_length'],
                "genres": row['genres'],
                "release_date": row['release_date'],
                "rating": row['rating'],
                "image_url": poster_url  # Use real poster URL
            })

        print(f"Recommendations: {recommendations}")
        return jsonify(recommendations)
    except Exception as e:
        print(f"Error in recommend_movies: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

# Start Waitress server (Render will handle exposing ports)
if __name__ == '__main__':
    from waitress import serve
    print("\n🚀 Starting Waitress server...")
    serve(app, host='0.0.0.0', port=10000)  # Use Render-assigned port
