import snowflake.snowpark as snowpark
import streamlit as st
import os
from snowflake.core import Root
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
pd.set_option("max_colwidth", None)

NUM_CHUNKS = 3  

SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER')
SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')
SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE')
SNOWFLAKE_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA')
WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")

def create_snowpark_session():
    try:
        session = snowpark.Session.builder.configs({
            "user": SNOWFLAKE_USER,
            "password": SNOWFLAKE_PASSWORD,
            "account": SNOWFLAKE_ACCOUNT,
            "warehouse": WAREHOUSE,
            "database": SNOWFLAKE_DATABASE,
            "schema": SNOWFLAKE_SCHEMA
        }).create()
        return session
    except Exception as e:
        st.error(f"Failed to create Snowpark session: {e}")
        raise

session = create_snowpark_session()
root = Root(session)

CORTEX_SEARCH_DATABASE = SNOWFLAKE_DATABASE
CORTEX_SEARCH_SCHEMA = SNOWFLAKE_SCHEMA
CORTEX_SEARCH_SERVICE = "drug_data_search_service" 
svc = root.databases[CORTEX_SEARCH_DATABASE].schemas[CORTEX_SEARCH_SCHEMA].cortex_search_services[CORTEX_SEARCH_SERVICE]

COLUMNS = [
    "chunk",
    "category",
    "record_title"
]

def config_options():
    st.sidebar.selectbox('Select your model:', (
        'mixtral-8x7b', 'snowflake-arctic', 'mistral-large',
        'llama3-8b', 'llama3-70b', 'reka-flash', 
        'mistral-7b', 'llama2-70b-chat', 'gemma-7b'), key="model_name")

    categories = session.sql("SELECT DISTINCT category FROM drug_data").collect()
    cat_list = ['ALL'] + [cat.CATEGORY for cat in categories]

    st.sidebar.selectbox('Select the drug category:', cat_list, key="category_value")

def get_similar_chunks_search_service(query):
    if st.session_state.category_value == "ALL":
        response = svc.search(query, COLUMNS, limit=NUM_CHUNKS)
    else: 
        filter_obj = {"@eq": {"category": st.session_state.category_value}}
        response = svc.search(query, COLUMNS, filter=filter_obj, limit=NUM_CHUNKS)

    if not response.json():
            return "Sorry, I don't have data for that category."

    return response.json()

def create_prompt(myquestion):
    if "history" not in st.session_state:
        st.session_state.history = []  

    slide_window = 7

    history_context = "\n".join(
        [f"User: {entry['question']}\nAssistant: {entry['response']}" for entry in st.session_state.history[-slide_window:]]
    )

    if st.session_state.rag:
        prompt_context = get_similar_chunks_search_service(myquestion)
        prompt = f"""
            You are an expert chat assistant that extracts information from the context provided
            between <context> and </context> tags.
            When answering the question contained between <question> and </question> tags,
            be concise and do not hallucinate. If you don't have the information, just say so.
            Only answer the question if you can extract it from the context provided.

            <history>
            {history_context}
            </history>

            <context>          
            {prompt_context}
            </context>
            <question>  
            {myquestion}
            </question>
            Answer: 
        """
    else:
        prompt = f"""
            [Conversation History]
            {history_context}

            Question:  
            {myquestion} 
            Answer:
        """
    return prompt


def complete(myquestion):
    prompt = create_prompt(myquestion)
    cmd = """
        SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS response
    """
    df_response = session.sql(cmd, params=[st.session_state.model_name, prompt]).collect()
    return df_response[0].RESPONSE

def main():
    st.title(":speech_balloon: MediScope Chatbot")
    config_options()
    st.session_state.rag = st.sidebar.checkbox('Use your own dataset as context?')

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg["content"])

    if question := st.chat_input("Ask your question about drugs or products:"):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            response = complete(question)
            message_placeholder.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
