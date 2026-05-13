import os
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# =========================
# LOAD ENVIRONMENT VARIABLES
# =========================

BASE_DIR = Path(__file__).resolve().parent

# Load .env explicitly
load_dotenv(BASE_DIR / ".env")

# Debug prints
print("ENV FILE:", BASE_DIR / ".env")
print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))

# =========================
# LANGCHAIN IMPORTS
# =========================

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

# =========================
# CUSTOM TOOL
# =========================

from drive_tool import drive_search_tool

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
You are TailorTalk, a smart AI assistant that helps users search files in Google Drive.

You have access to a tool called `drive_search_tool`.

The tool accepts a Google Drive API query string (`q` parameter).

Examples:

Find PDFs:
mimeType = 'application/pdf'

Find files containing budget:
name contains 'budget'

Find documents mentioning AI:
fullText contains 'AI'

Find recent reports:
name contains 'report' and modifiedTime > '2024-01-01T00:00:00'

Guidelines:
1. Always use the tool.
2. Never make up file results.
3. Return clean and concise responses.
4. Include file names and links when available.
"""

# =========================
# DRIVE AGENT CLASS
# =========================

class DriveAgent:

    def __init__(self):

        # Get Gemini API Key
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set."
            )

        # Initialize Gemini Model
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.1,
        )

        # Register tools
        self.tools = [drive_search_tool]

        # Prompt Template
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),

            MessagesPlaceholder(
                variable_name="chat_history",
                optional=True
            ),

            ("human", "{input}"),

            MessagesPlaceholder(
                variable_name="agent_scratchpad"
            ),
        ])

        # Create Agent
        agent = create_tool_calling_agent(
            self.llm,
            self.tools,
            prompt
        )

        # Create Executor
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
        )

    # =========================
    # CHAT METHOD
    # =========================

    async def chat(self, message: str, history: list):

        # Convert history into LangChain format
        lc_history = []

        for msg in history:

            if msg["role"] == "user":
                lc_history.append(
                    HumanMessage(content=msg["content"])
                )

            elif msg["role"] == "assistant":
                lc_history.append(
                    AIMessage(content=msg["content"])
                )

        # Run Agent
        result = await self.executor.ainvoke({
            "input": message,
            "chat_history": lc_history,
        })

        # Get AI Reply
        reply = result.get(
            "output",
            "Sorry, I couldn't process that request."
        )

        # =========================
        # Extract File Data
        # =========================

        files = []

        for step in result.get("intermediate_steps", []):

            if len(step) >= 2:

                tool_output = step[1]

                try:
                    parsed = json.loads(tool_output)

                    if (
                        "files" in parsed
                        and parsed["files"]
                    ):
                        files.extend(parsed["files"])

                except (
                    json.JSONDecodeError,
                    TypeError
                ):
                    pass

        # Remove duplicate files
        unique_files = []
        seen = set()

        for file in files:

            file_id = file.get("id")

            if file_id not in seen:
                seen.add(file_id)
                unique_files.append(file)

        # Final Response
        return {
            "reply": reply,
            "files": unique_files
        }