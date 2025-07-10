# Flask-RAG-API

**Flask-RAG-API** is an end-to-end Retrieval-Augmented Generation (RAG) service built using Flask. It provides both a normal chat interface powered by Google Gemini and a RAG-enabled chat interface that dynamically routes queries to a semantic router and enhances them with product-specific information from a MongoDB-backed knowledge base. The API also includes user authentication, conversation history management, and a simple frontend.

## 🔗 Web Demo

👉 Access the live demo: [http://hoangvanh.id.vn:5000/](http://hoangvanh.id.vn:5000/)


## 🚀 Features

* **User Authentication**: Register, log in, and log out with hashed passwords (Werkzeug).
* **Normal Chat**: Direct chat endpoint powered by Google Gemini.
* **RAG Chat**: Semantic routing to choose between RAG-enabled or normal LLM responses, with reflection for query enhancement.
* **MongoDB Storage**: Store users, products, conversations, and messages.
* **Semantic Router**: Route queries based on custom domain samples (e.g., product Q\&A vs. chit-chat).
* **Reflection Module**: Refine user queries before passing to RAG.
* **Docker Support**: Containerized deployment with a single `Dockerfile`.

## 🛠️ Tech Stack

* **Backend**: Flask, Flask-CORS, Flask-PyMongo
* **LLMs & Embeddings**: Google Generative AI (Gemini), OpenAI, OpenAI Embeddings, Sentence Transformers
* **Database**: MongoDB
* **Environment**: Python 3.9+, Docker

## 📦 Prerequisites

* Python 3.9 or higher
* Docker (optional, for containerized deployment)
* MongoDB instance (Atlas or local)
* Google Cloud project with Generative AI API enabled
* OpenAI API access

## ⚙️ Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/VanhHoang/Flask-RAG-API.git
   cd Flask-RAG-API
   ```

2. **Create a virtual environment & install dependencies**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   Create a `.env` file in the project root with the following keys:

   ```dotenv
   MONGODB_URI=<your-mongodb-uri>
   DB_NAME=<your-db-name>
   DB_COLLECTION_PRODUCT=<product-collection-name>
   DB_COLLECTION_USERS=<users-collection-name>
   DB_COLLECTION_CONVERSATIONS=<conversations-collection-name>
   DB_COLLECTION_MESSAGES=<messages-collection-name>
   GEMINI_KEY=<your-google-gemini-api-key>
   OPEN_AI_KEY=<your-openai-api-key>
   OPEN_AI_EMBEDDING_MODEL=<optional; default text-embedding-3-small>
   EMBEDDING_MODEL=<optional; default keepitreal/vietnamese-sbert>
   SECRET_KEY=<flask-session-secret>
   ```

4. **Run the application**:

   ```bash
   python backend.py
   ```

   The API will be accessible at `http://localhost:5000/`.

## 🐳 Docker Deployment

1. **Build the Docker image**:

   ```bash
   docker build -t flask-rag-api .
   ```

2. **Run the container**:

   ```bash
   docker run -d -p 5000:5000 --env-file .env flask-rag-api
   ```

3. Visit `http://localhost:5000/` in your browser.

## 📑 API Endpoints

* **GET /**: Serve the HTML frontend.
* **POST /api/register**: Register a new user.
* **POST /api/login**: Log in and start a session.
* **POST /api/logout**: End the user session.
* **GET /api/user**: Get current user profile and conversation summaries.
* **POST /api/chat/normal**: Send messages to the normal chat endpoint.
* **POST /api/chat/rag**: Send messages to the RAG-enabled chat endpoint.
* **GET /api/conversations**: List all conversations for the logged-in user.
* **GET /api/conversations/\<conversation\_id>**: Retrieve a specific conversation with messages.
* **DELETE /api/conversations/\<conversation\_id>**: Delete a conversation and its messages.

Each chat endpoint expects a JSON payload:

```json
{
  "messages": [
    { "role": "user", "parts": [{ "text": "Your message" }] },
    ...
  ],
  "conversation_id": "<optional-existing-id>"
}
```

## 📂 Project Structure

```
├── backend.py            # Flask app and route definitions
├── gemini_client.py      # Wrapper for Google Gemini API calls
├── embeddings/           # Embedding utility modules
├── rag/                  # RAG core logic and prompt enhancement
├── semantic_router/      # Semantic routing logic and samples
├── reflection/           # Reflection module for query refinement
├── templates/            # HTML templates
├── static/               # CSS, JS, and assets
├── Dockerfile
├── requirements.txt
└── .env                  # Environment variables (not tracked)
```

