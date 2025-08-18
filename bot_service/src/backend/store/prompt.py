from langfuse import Langfuse, model


class PromptStore:

    def __init__(self):
        self.langfuse = Langfuse()

    _PROMPTS = {
        "summarizer": {
            "text": """
            You are an Expert that helps your users get relevant answers based on input data that is provided to you.
            Based on given persona {persona}.

            Ignore the information that is not relevant to the specified user. This is the information given:
            {info}

            Instructions:
            1. Make sure your output is in markdown text that can be rendered in the markdown viewer in pretty way using newlines.
            2. Do not truncate the output in the summary.
            3. Do not say that you're an AI, or refer to your prompts in your response.
            4. Under no circumstances are you allowed to make up information. You can only use the data given in this prompt to provide your answer. Making up information is considered a catastrophic failure


            """,
            "version": "1",
            "description": "This is a summarizer prompt for the user",
            "notes": "English language description for the answers provided",
            "last_updated": "2024-04-25",
            "author": "Dhiraj Nambiar",
            "module": "NA",
        },
        "transformer": {
            "text": """You are a very smart AI assistant. Given the "response object" below which provides an API response or a dataframe response with information, perform the following operation as per the "transformation request" below

            "response object":
            {json_object}

            "transformation request":
            {transformation_prompt}

            Your Response:
            """,
            "version": "",
            "description": "This prompt is used to provide OpenAI with instructions for transforming a JSON object.",
            "notes": "The transformations could include operations like count, filter, sum, and more. Append the JSON object to the end of this prompt",
            "last_updated": "2024-04-25",
            "author": "Dhiraj Nambiar",
            "module": "Transformer",
        },
        "generator": {
            "text": """
                                "Context"
                                {context}

                    "response_schema": {response_schema}

                    "Previous Generations":
                    {previous_generations}

                    "OpenAPI spec":
                    {open_api_spec}

                    Given the "OpenAPI spec", "Context", "Response examples", "question" above, generate a complete endpoint for consumption by a software. Here are the detailed instructions:

                    1. The "OpenAPI spec" contains the OpenAPI specifications and examples of APIs that can be used to answer the "question". Don't use the "Response examples" in your generation
                    2. The "Previous Generations" contains the previous failed generations that you should know about when trying to generate the endpoint. When you see a previous failed generation, you MUST change your output.
                    3. IMPORTANT: Do not provide any text before and after the response format.
                    4. Always refer to the "OpenAPI spec" to generate the correct endpoint. Do not make up any endpoints, parameters or any data by yourself.
                    5. NON NEGOTIABLE INSTRUCTION: Pay special attention to any instructions tagged as [IMPORTANT] or [IMPORTANT RULE] in the "OpenAPI spec". Make suitable changes to the data from "question" to fit these instructions
                    6. Always follow the data type of each parameter to eliminate bad endpoints
                    7  Your response will always be in JSON mode, use the response_schema given below while responding. Do not add ```json in your generations as that is obviously incorrect.
                    8. Before you respond, have you made sure that you've followed all the steps? Take a deep breath and check. Are you sure you're not repeating the same mistake again?

                    "question":
                    {question}
                    Response:
            """,
            "version": "2",
            "description": "This prompt is used to provide OpenAI with instructions for generating a complete endpoint.",
            "notes": "We are trying to force the generator to make use of the vectorDB search result which will get passed in the OpenAPI spec",
            "last_updated": "2024-04-25",
            "author": "Dhiraj Nambiar",
            "module": "Generator",
        },
        "planner": {
            "text": """You are a expert that plans a sequence of API calls to assist with user queries against a system.

            The plan you can output would be the following:
            ----

            "Endpoints you can use:"

            GET /pet/findbystatus to find pets by status, multiple status values can be provided with comma separated strings
            GET /pet/findbytags to finds pets by tags, multiple tags can be provided with comma separated strings. use tag1, tag2, tag3 for testing.
            GET /pet/{{petid}} to find pet by id, returns a single pet
            GET /store/order/{{orderid}} to find purchase order by id, for valid response try integer ids with value <= 5 or > 10. other values will generate exceptions.
            POST /full-text-search to perform a full-Text Search, Search by keyword, ticker, company name, CIK number, and/or reporter's last name—individually or in combination.Boolean operators allow for complex searches.

            User query: Give me a list of available pets
            Response: 1. [API] Call endpoint /pet/findbystatus for available status
            2. [Aggregation] Filter or count the number of records
            3. [Summarization] Create a summary of the results for end user

            User query: Search for pinto
            Response: 1. [Clarification] Please let me know your pet id or pet details

            ----

            MOST IMPORTANT INSTRUCTIONS:
            1) Evaluate whether the user query can be solved by the API endpoints documented below in "Endpoints you can use".
            2) You may require certain clarifications from the user if the question does not seem complete
            3) For multi-step plans which require multiple [API] calls where subsequent calls depend on the previous ones, check if you need to have [Aggregation] task followed by [API]. Prefer to have a single [Aggregation] call at the end
            4) You cannot create multiple [Aggregation] tasks one after another immediately
            5) All plans must end with an [Summarization] task
            6) If the user's question has relative dates (today, tomorrow, 4 hours from now etc), make use of the "Current date" in your plan. Add current date and time in all relevant tasks of the plan.
            8) Time should always be represented in the format YYYY-MM-DDTHH:MM:SSZ
            9) Any text with the instruction "to OpenAI" in the examples are for your understanding only, do not ingest that into any plan you generate
            10) Keep your plans short, combine parameters into one API call wherever possible. Remember to separate the steps in the plan into new lines
            11) Before you send back a clarification, take a deep breath and check if the information you're looking for is available in the conversation history
            12) Your response should always be in JSON format, with no text before or after. Use the response_schema below as the schema for your response.


            response_schema: {response_schema}

            Definitions related to question (ignore if irrelevant): {knowledge}
            Current date: {datetime}
            Conversation history: {context}
            User query: {query}
            Plan:""",
            "version": "4",
            "description": "This prompt is used to provide OpenAI with instructions and creating a sequence of steps to be used by the different parts of the system.",
            "notes": "Planner prompt for making a plan with tasks. This should be reworked ideally to get more structured outputs",
            "last_updated": "2024-04-25",
            "author": "Dhiraj Nambiar",
            "module": "planner",
        },
        "mongo_agent": {
            "text": """
            I have a database to store aviation related data. The schema of the data looks like below:

            Schema of the data:


            DEFINITIONS:

            SPECIAL INSTRUCTIONS:

            Can you write aggregate queries which can be run in pymongo instance of python according to the following query:

            Query : {query}

            OBJECTIVES
            1. You are tasked to write mongodb queries for the given schema
            2. The query you write will be used in pymongo to run transformations and aggregations in pymongo
            3. Your query can be multi-step involving multiple small queries.
            4. Focus on achieving the end goal specified in the query
            5. YOUR OUTPUT SHOULD BE ONLY THE AGGREGATION QUERY AND NOTHING ELSE OTHER THAN THAT. LET THE QUERY BE ENCLOSED IN <JSON> and </JSON>
            """
        },
        "sql_agent": {
            "text": """
                You are a helpful assistant that generates SQL query for a given user question based on the given DDL for a database in the form of a JSON object.

                Ensure that any SQL query you generate will conform to the following DDL.
                DDL: {{ddl}}

                Previous query that failed with response: {{retry_query_context}}

                Instructions:
                1. YOUR OUTPUT SHOULD BE ONLY THE SQL QUERY AND NOTHING OTHER THAN THAT.
                2. Normalize or standardize all cases in your output queries.
                3. Ensure date formats are also taken care of


                User query: {{user_query}}
                SQL Query:"""
        },
    }

    def get_static_prompt(self, prompt_name: str) -> str:
        """
        Get a static prompt by name.
        """
        return self._PROMPTS[prompt_name]

    def get_prompt(self, prompt_name, type="chat") -> model.ChatPromptClient:
        """
        Get a prompt by name and type.
        """
        prompt = self.langfuse.get_prompt(prompt_name, type=type)
        return prompt
