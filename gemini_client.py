import google.generativeai as genai

class GeminiClient:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def chat(self, messages):
        """
        Chuyển đổi format messages từ Gemini sang format chat history
        và gọi API Gemini để nhận phản hồi
        """
        try:
            # Chuyển đổi messages thành chat history cho Gemini
            chat_history = []
            
            for message in messages[:-1]:  # Tất cả messages trừ message cuối cùng
                if message['role'] == 'user':
                    chat_history.append({
                        'role': 'user',
                        'parts': [{'text': message['parts'][0]['text']}]
                    })
                elif message['role'] == 'model':
                    chat_history.append({
                        'role': 'model',
                        'parts': [{'text': message['parts'][0]['text']}]
                    })
            
            # Bắt đầu chat session với history
            chat = self.model.start_chat(history=chat_history)
            
            # Gửi message cuối cùng (current message)
            current_message = messages[-1]
            if current_message['role'] == 'user':
                response = chat.send_message(current_message['parts'][0]['text'])
                return response.text
            else:
                raise ValueError("Message cuối cùng phải có role là 'user'")
                
        except Exception as e:
            raise Exception(f"Lỗi khi gọi Gemini API: {str(e)}")