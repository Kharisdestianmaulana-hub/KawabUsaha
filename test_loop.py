import asyncio
try:
    asyncio.get_event_loop()
    print("Loop found")
except Exception as e:
    print(f"Error: {e}")
    
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
asyncio.get_event_loop()
print("Loop set successfully")
