import asyncio
import base64
import logging
import os
from pathlib import Path
from agents import Agent, Runner
from agents.model_settings import ModelSettings
from openai import AsyncOpenAI
from contextlib import AsyncExitStack
from e2b_code_interpreter import AsyncSandbox
from agents import FunctionTool

class MyAgent: 

    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.path = None
        self.session = None
        self.client = AsyncOpenAI()
        self.sbx = None
        self.error_logger = logging.getLogger("agentv2")
        if not self.error_logger.handlers:
            self.error_logger.setLevel(logging.INFO)
            handler = logging.FileHandler("error.log")
            handler.setLevel(logging.ERROR)
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            self.error_logger.addHandler(handler)

    async def create_session(self):
        conversation = await self.client.conversations.create()
        conversation_id = conversation.id

        return conversation_id
    

    async def run_agent(self, conversation_id):
        
        #Let the user define the path 
        valid_extensions = {".csv", ".xlsx"}
        while True:
            self.path = input("Enter the path to the file you want to analyze: ")
            path = self.path.strip()
            if path == "quit":
                print("Goodbye!")
                return
            if not path:
                print("Please provide a non-empty file path.")
                continue
            if not Path(path).is_file():
                print(f"File not found: {path}")
                continue
            if Path(path).suffix.lower() not in valid_extensions:
                print(
                    f"Unsupported file type: {Path(path).suffix}. "
                    "Please provide a .csv or .xlsx file."
                )
                continue
            print(f"\nUsing file path: {path} \n")
            break
        
        self.sbx = await AsyncSandbox.create(timeout=0)
        
        print("Sandbox initialised successfully \n")

        #Available libraries in the sandbox 

        libraries = '''
    "jupyter-server", "ipykernel", "ipython", "orjson", "pandas", "matplotlib",
    "pillow", "e2b_charts", "aiohttp", "beautifulsoup4", "bokeh", "gensim", "imageio",
    "joblib", "librosa", "nltk", "numpy", "numba", "opencv-python", "openpyxl",
    "plotly", "kaleido", "pytest", "python-docx", "pytz", "requests", "scikit-image", "scikit-learn",
    "scipy", "seaborn", "soundfile", "spacy", "textblob", "tornado", "urllib3", "xarray", "xlrd", "sympy"
        '''

        # upload the file to the sandbox using original filename
        filename = os.path.basename(path)
        with open(path, "rb") as f:
            sbx_info = await self.sbx.files.write(filename, f)
        sbx_path = sbx_info.path
        print(f"File uploaded to sandbox at: {sbx_path}")
        
        # Define tool function and tool 
        async def analyse_data(ctx, args: str):
            import json
            params = json.loads(args)
            code = params.get("code", "")
            analysis_output = await self.sbx.run_code(code,
                  on_error=lambda error: self.error_logger.error("Sandbox execution error: %s", error)
                  )

            saved_files: list[str] = []
            charts_dir = Path("charts")
            charts_dir.mkdir(parents=True, exist_ok=True)

            for i, result in enumerate(getattr(analysis_output, "results", []) or []):
                try:
                    png_b64 = result._repr_png_()
                except Exception:
                    png_b64 = None

                if png_b64:
                    out_path = charts_dir / f"chart_{i + 1}.png"
                    out_path.write_bytes(base64.b64decode(png_b64))
                    saved_files.append(str(out_path))
                    continue

                try:
                    svg_text = result._repr_svg_()
                except Exception:
                    svg_text = None

                if svg_text:
                    out_path = charts_dir / f"chart_{i + 1}.svg"
                    out_path.write_text(svg_text, encoding="utf-8")
                    saved_files.append(str(out_path))

            if saved_files:
                return f"Saved {len(saved_files)} chart(s): " + ", ".join(saved_files)

            available_formats: list[str] = []
            for result in getattr(analysis_output, "results", []) or []:
                try:
                    available_formats.extend(list(result.formats()))
                except Exception:
                    continue
            if available_formats:
                return (
                    "No chart artifacts were found to save. Available result formats: "
                    + ", ".join(sorted(set(available_formats)))
                    + ""
                )

            return str(analysis_output)

        tool = FunctionTool(
            name = "python_code_execution",
            description="Execute Python code in a sandbox environment to analyze data. If the code produces static charts, save them under charts/ as chart_#.png or chart_#.svg and return a message listing saved files.",
            params_json_schema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    }
                },
                "required": ["code"]
            },
            on_invoke_tool=analyse_data
        )

        agent = Agent(
            name="Assistant",
            instructions=f"""
                You are an expert data scientist and analyst with access to a Python code execution environment that
                has the following libraries pre-installed: {libraries}. Your job is to ONLY analyze the file under {sbx_path}
                
                DATA LOCATION:
                The dataset is available at: {sbx_path}

                YOUR WORKFLOW:
                1. Use your code execution tool to run Python code
                2. Always start by loading the data with pandas: `pd.read_csv('{sbx_path}')` or `pd.read_excel('{sbx_path}')` depending on the file type
                3. Explore, analyze, and extract insights from the data
                4. Present findings clearly with supporting evidence from your analysis

                GUIDELINES:
                - Import the required libraries at the start of each code block
                - Use the pre-installed libraries: {libraries} to analyse the data or create visualizations where requested
                - Handle errors gracefully and adjust your approach if needed  
                - Provide actionable, data-driven insights
                - Show relevant statistics, patterns, and visualizations when appropriate
                - Only create visualizations when specifically asked
            """,
            model="gpt-4.1-mini",
            tools=[tool],
            model_settings=ModelSettings(tool_choice="auto"),
        )
        #server stop & cleanup 

        # initial run to initialise the loop 
        initial_prompt = f"Understand the data in {sbx_path} and give me a 200 word summary of its structure and 3 key insight worth exploring with you."
        result = await Runner.run(agent, initial_prompt, conversation_id=conversation_id)
        print(f"Agent: {result.final_output}")

        while True:
            user_input = input("\nEnter your message (or 'quit' to exit): ")
            if user_input.lower() == 'quit':
                break
            result = await Runner.run(agent, user_input, conversation_id=conversation_id)
            print(f"\nAgent: {result.final_output}\n")
    
    async def cleanup(self):
        """\nClean up resources\n"""
        await self.exit_stack.aclose()
        if self.sbx:
            await self.sbx.kill()

async def main():
    agent = MyAgent()
    
    try:
        conversation_id = await agent.create_session()
        print(f"Conversation created with ID: {conversation_id} \n")
        await agent.run_agent(conversation_id)

    except Exception as e:
        print(f"Error running agent: {e}")
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())





