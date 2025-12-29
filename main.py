import asyncio
import os
import uuid
from dotenv import load_dotenv
from modules.core.orchestrator import create_research_system

load_dotenv()


async def main():
    print("--- 🧠 Gemini 3.0 Deep Research Agent Initializing ---")

    # 1. Generate a Thread ID to keep VFS alive across the loop
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    tier = os.getenv("RESEARCH_TIER", "free")
    agent = create_research_system(tier=tier)

    print(f"Status: Online | Tier: {tier.upper()} | Thread ID: {thread_id}")
    print("-" * 50)

    while True:
        user_input = input("\nResearch Objective: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        print(f"\n[Gemini 3 {tier.upper()} is reasoning and planning...]")

        try:
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config
            )

            final_response = result["messages"][-1].content

            # Visual check: If the agent is asking a question, use a different color/header
            if "?" in final_response and "plan" in final_response.lower():
                print("\n" + "=" * 15 + " PLAN APPROVAL REQUIRED " + "=" * 15)
                print(final_response)
                print("=" * 56)
                print("(Type 'yes' to proceed or describe changes)")
            else:
                print("\n" + "=" * 20 + " FINAL REPORT " + "=" * 20)
                print(final_response)
                print("=" * 54)

        except Exception as e:
            print(f"\n[!] Research Error: {str(e)}")


if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: Missing GOOGLE_API_KEY. Check .env")
    else:
        asyncio.run(main())