import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agent import tatai_agent

async def main():
    session_service = InMemorySessionService()
    
    session = await session_service.create_session(
        app_name="tatai_app",
        user_id="user_001",
    )

    runner = Runner(
        agent=tatai_agent,
        app_name="tatai_app",
        session_service=session_service,
    )

    print("TATAI: สวัสดีครับ! ท้าทายพร้อมช่วยวางแผนเที่ยวไทยแล้วครับ (พิมพ์ 'exit' เพื่อจบ)")

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("TATAI: ขอบคุณครับ แล้วพบกันใหม่!")
            break

        message = types.Content(
            role="user",
            parts=[types.Part(text=user_input)]
        )

        async for event in runner.run_async(
            user_id="user_001",
            session_id=session.id,
            new_message=message,
        ):
            if event.is_final_response():
                print(f"\nTATAI: {event.content.parts[0].text}")

if __name__ == "__main__":
    asyncio.run(main())