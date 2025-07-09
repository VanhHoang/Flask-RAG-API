from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv
import os
import openai
import google.generativeai as genai
from rag.core import RAG
from embeddings import OpenAIEmbedding
from semantic_router import SemanticRouter, Route
from semantic_router.samples import productsSample, chitchatSample
from reflection import Reflection
from gemini_client import GeminiClient
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId


load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME')
DB_COLLECTION_PRODUCT = os.getenv('DB_COLLECTION_PRODUCT')
DB_COLLECTION_USERS = os.getenv('DB_COLLECTION_USERS')
DB_COLLECTION_CONVERSATIONS = os.getenv('DB_COLLECTION_CONVERSATIONS')
DB_COLLECTION_MESSAGES = os.getenv('DB_COLLECTION_MESSAGES')
LLM_KEY = os.getenv('GEMINI_KEY')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL') or 'keepitreal/vietnamese-sbert'
OPEN_AI_KEY = os.getenv('OPEN_AI_KEY')
OPEN_AI_EMBEDDING_MODEL = os.getenv('OPEN_AI_EMBEDDING_MODEL') or 'text-embedding-3-small'
MONGODB_URI = os.getenv('MONGODB_URI')

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
users_collection = db[DB_COLLECTION_USERS]
conversations_collection = db[DB_COLLECTION_CONVERSATIONS]
messages_collection = db[DB_COLLECTION_MESSAGES]


OpenAIEmbedding(OPEN_AI_KEY)
gemini_client = GeminiClient(LLM_KEY)


# --- Semantic Router Setup --- #
PRODUCT_ROUTE_NAME = 'products'
CHITCHAT_ROUTE_NAME = 'chitchat'

openAIEmbeding = OpenAIEmbedding(apiKey=OPEN_AI_KEY, dimensions=1024, name=OPEN_AI_EMBEDDING_MODEL)
productRoute = Route(name=PRODUCT_ROUTE_NAME, samples=productsSample)
chitchatRoute = Route(name=CHITCHAT_ROUTE_NAME, samples=chitchatSample)
semanticRouter = SemanticRouter(openAIEmbeding, routes=[productRoute, chitchatRoute])

# --- Set up LLMs --- #
genai.configure(api_key=LLM_KEY)
llm = genai.GenerativeModel('gemini-2.0-flash')


# --- Relection Setup --- #
gpt = openai.OpenAI(api_key=OPEN_AI_KEY)
reflection = Reflection(llm=gpt)


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
CORS(app)


# Initialize RAG
rag = RAG(
    mongodbUri=MONGODB_URI,
    dbName=DB_NAME,
    dbCollection=DB_COLLECTION_PRODUCT,
    embeddingName='keepitreal/vietnamese-sbert',
    llm=llm,
)

def process_query(query):
    return query.lower()

@app.route("/")
def main():
    return render_template('main.html')

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        
        if not username or not password or not email:
            return jsonify({'error': 'Thiếu thông tin bắt buộc'}), 400
        
        # Kiểm tra user đã tồn tại
        if users_collection.find_one({'username': username}):
            return jsonify({'error': 'Tên đăng nhập đã tồn tại'}), 400
        
        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'Email đã được sử dụng'}), 400
        
        # Tạo user mới
        hashed_password = generate_password_hash(password)
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.utcnow()
        }
        
        result = users_collection.insert_one(user_data)
        
        return jsonify({
            'message': 'Đăng ký thành công',
            'user_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Thiếu tên đăng nhập hoặc mật khẩu'}), 400
        
        # Tìm user
        user = users_collection.find_one({'username': username})
        
        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Tên đăng nhập hoặc mật khẩu không đúng'}), 401
        
        # Tạo session
        session['user_id'] = str(user['_id'])
        session['username'] = user['username']
        
        return jsonify({
            'message': 'Đăng nhập thành công',
            'user': {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'message': 'Đăng xuất thành công'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user', methods=['GET'])
def get_user():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Chưa đăng nhập'}), 401
        
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        if not user:
            return jsonify({'error': 'Không tìm thấy user'}), 404
        
        # Thêm conversations vào response
        conversations = get_user_conversations(session['user_id'])
        
        return jsonify({
            'user': {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email']
            },
            'conversations': conversations
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Helper functions for conversation management
def create_conversation(user_id, mode="normal"):
    """Create a new conversation and return its ID"""
    try:
        conversation_data = {
            "user_id": ObjectId(user_id),
            "create_at": datetime.utcnow(),
            "mode": mode
        }
        result = conversations_collection.insert_one(conversation_data)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error creating conversation: {e}")
        return None

def save_message(conversation_id, role, content):
    """Save a message to the database"""
    try:
        message_data = {
            "conversation_id": ObjectId(conversation_id),
            "role": role,
            "parts": [content],
            "timestamp": datetime.utcnow()
        }
        result = messages_collection.insert_one(message_data)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error saving message: {e}")
        return None

def get_user_conversations(user_id):
    """Get all conversations for a user"""
    try:
        conversations = list(conversations_collection.find(
            {"user_id": ObjectId(user_id)},
            {"_id": 1, "create_at": 1, "mode": 1}
        ).sort("create_at", -1))
        
        # Convert ObjectId to string and get first message for title
        for conv in conversations:
            conv["_id"] = str(conv["_id"])
            # Get first user message for title
            first_message = messages_collection.find_one(
                {"conversation_id": ObjectId(conv["_id"]), "role": "user"},
                {"parts": 1}
            )
            if first_message and first_message.get("parts"):
                title = first_message["parts"][0]
                conv["title"] = title[:30] + "..." if len(title) > 30 else title
                conv["title"] += f" ({conv['mode'].upper()})" if conv["mode"] == "rag" else ""
            else:
                conv["title"] = f"Cuộc trò chuyện mới ({conv['mode'].upper()})" if conv["mode"] == "rag" else "Cuộc trò chuyện mới"
                
        return conversations
    except Exception as e:
        print(f"Error getting conversations: {e}")
        return []

def get_conversation_messages(conversation_id):
    """Get all messages for a conversation"""
    try:
        messages = list(messages_collection.find(
            {"conversation_id": ObjectId(conversation_id)},
            {"role": 1, "parts": 1, "timestamp": 1}
        ).sort("timestamp", 1))
        
        # Convert to frontend format
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["parts"][0] if msg["parts"] else ""
            })
        
        return formatted_messages
    except Exception as e:
        print(f"Error getting messages: {e}")
        return []

def delete_conversation_and_messages(conversation_id, user_id):
    """Delete a conversation and all its messages"""
    try:
        # Verify conversation belongs to user
        conversation = conversations_collection.find_one({
            "_id": ObjectId(conversation_id),
            "user_id": ObjectId(user_id)
        })
        
        if not conversation:
            return False
        
        # Delete all messages
        messages_collection.delete_many({"conversation_id": ObjectId(conversation_id)})
        
        # Delete conversation
        conversations_collection.delete_one({"_id": ObjectId(conversation_id)})
        
        return True
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return False

# --- Normal Chat Endpoint --- #

@app.route('/api/chat/normal', methods=['POST'])
def chat_normal():
    """Normal chat endpoint using Gemini directly"""
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        conversation_id = data.get('conversation_id')
        
        if not isinstance(messages, list) or not messages:
            return jsonify({'error': 'Invalid messages format'}), 400
        
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Create new conversation if not provided
        if not conversation_id:
            conversation_id = create_conversation(user_id, "normal")
            if not conversation_id:
                return jsonify({'error': 'Failed to create conversation'}), 500
        
        # Get the latest user message
        user_message = messages[-1]["parts"][0]["text"]
        
        # Save user message
        save_message(conversation_id, "user", user_message)
        
        # Validate message format
        for message in messages:
            if 'role' not in message or 'parts' not in message:
                return jsonify({'error': 'Invalid message format'}), 400
            if not message['parts'] or 'text' not in message['parts'][0]:
                return jsonify({'error': 'Invalid message parts format'}), 400
        
        # Call Gemini API directly
        response_text = gemini_client.chat(messages)
        
        # Save assistant message
        save_message(conversation_id, "model", response_text)
        
        return jsonify({
            'parts': [{'text': response_text}],
            'role': 'model',
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/rag', methods=['POST'])
def chat_rag():
    """RAG chat endpoint using semantic routing"""
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        conversation_id = data.get('conversation_id')
        
        if not isinstance(messages, list) or not messages:
            return jsonify({'error': 'Invalid messages format'}), 400
        
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Create new conversation if not provided
        if not conversation_id:
            conversation_id = create_conversation(user_id, "rag")
            if not conversation_id:
                return jsonify({'error': 'Failed to create conversation'}), 500
        
        # Get the latest user message
        query = messages[-1]["parts"][0]["text"]
        user_message = query
        query = process_query(query)

        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Save user message
        save_message(conversation_id, "user", user_message)
        
        # Use semantic router to decide routing
        guidedRoute = semanticRouter.guide(query)[1]

        if guidedRoute == PRODUCT_ROUTE_NAME:
            # Route to RAG system
            print("Routing to RAG system")
            
            # Apply reflection to improve query
            reflected_query = reflection(messages)
            query = reflected_query
            
            # Get enhanced prompt from RAG
            source_information = rag.enhance_prompt(query).replace('<br>', '\n')
            combined_information = f"Hãy trở thành chuyên gia tư vấn bán hàng cho một cửa hàng điện thoại. Câu hỏi của khách hàng: {query}\nTrả lời câu hỏi dựa vào các thông tin sản phẩm dưới đây: {source_information}."
            
            # Add enhanced prompt to messages
            enhanced_messages = messages.copy()
            enhanced_messages.append({
                "role": "user",
                "parts": [{"text": combined_information}]
            })
            
            # Generate response using RAG
            response = rag.generate_content(enhanced_messages)
        else:
            # Route to normal LLM
            print("Routing to normal LLM")
            response = llm.generate_content(messages)

        # Save assistant message
        save_message(conversation_id, "model", response.text)

        return jsonify({
            'parts': [{'text': response.text}],
            'role': 'model',
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Conversation management routes
@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get user's conversations"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        conversations = get_user_conversations(session['user_id'])
        return jsonify({
            'conversations': conversations
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation with its messages"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Verify conversation belongs to user
        conversation = conversations_collection.find_one({
            "_id": ObjectId(conversation_id),
            "user_id": ObjectId(session['user_id'])
        })
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        messages = get_conversation_messages(conversation_id)
        
        return jsonify({
            'conversation': {
                'id': str(conversation['_id']),
                'mode': conversation['mode'],
                'created_at': conversation['create_at'].isoformat(),
                'messages': messages
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        success = delete_conversation_and_messages(conversation_id, session['user_id'])
        
        if not success:
            return jsonify({'error': 'Failed to delete conversation or conversation not found'}), 404
        
        return jsonify({
            'message': 'Conversation deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
