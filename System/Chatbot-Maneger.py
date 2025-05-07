import os
import asyncio
import aiohttp
from telethon import TelegramClient, events
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Validate required environment variables
required_vars = ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'GROQ_API_KEY']
for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

# Initialize Telegram client
client = TelegramClient(
    'STORAGE/session_name',
    os.getenv('TELEGRAM_API_ID'),
    os.getenv('TELEGRAM_API_HASH')
)

# Track pending response tasks
pending_tasks = {}

# Groq API Configuration
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_HEADERS = {
    'Authorization': f'Bearer {os.getenv("GROQ_API_KEY")}',
    'Content-Type': 'application/json'
}

async def generate_groq_response(prompt):
    """Generate AI response using Groq API with required message format"""
    data = {
        'model': 'llama3-70b-8192',  # Update model as needed
        'messages': [
            {'role': 'system', 'content': 'You are Nexor AI assistant. Reply to the user\'s message and always end your response with: "Sir is now busy. I will remind him of this message.And you are NEXOR AI my Personal assistant like tony stark jarvis.you do not reply about third party identities like elon musk and any other just tell me about me and you.you are my private ai you just reply"'}, 
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 200
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_URL, headers=GROQ_HEADERS, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    ai_response = result['choices'][0]['message']['content']
                    
                    # Ensure required ending is present
                    ending = "\n\nSir is now busy. I will remind him of this message."
                    if not ai_response.endswith(ending):
                        ai_response += ending
                        
                    return ai_response
                else:
                    error_text = await response.text()
                    print(f"Groq API Error [{response.status}]: {error_text}")
                    return f"I'm currently unavailable. {ending}"
    except Exception as e:
        print(f"Network error: {e}")
        return f"Connection failed. {ending}"

@client.on(events.NewMessage)
async def incoming_message_handler(event):
    """Handle new incoming messages"""
    if event.is_private and not event.out:
        chat = await event.get_chat()
        chat_id = chat.id

        # Cancel existing task if exists
        if chat_id in pending_tasks:
            pending_tasks[chat_id].cancel()
        
        # Schedule new AI response task
        task = asyncio.create_task(schedule_ai_response(event))
        pending_tasks[chat_id] = task

async def schedule_ai_response(event):
    """Wait 30 seconds before sending AI response"""
    try:
        await asyncio.sleep(15)
        ai_response = await generate_groq_response(event.text)
        await event.reply(ai_response)
    except asyncio.CancelledError:
        pass  # Task was cancelled by user response

@client.on(events.NewMessage(outgoing=True))
async def outgoing_message_handler(event):
    """Cancel AI response when user sends a message"""
    chat = await event.get_chat()
    chat_id = chat.id
    
    if chat_id in pending_tasks:
        pending_tasks[chat_id].cancel()
        del pending_tasks[chat_id]

async def main():
    await client.start()
    print("✅ Bot is running. Waiting for messages...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Stopping bot...")