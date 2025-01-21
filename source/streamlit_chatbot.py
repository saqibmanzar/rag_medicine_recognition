import snowflake.snowpark as snowpark
import streamlit as st
import os
import pandas as pd
import pdb
from dotenv import load_dotenv

load_dotenv()
pd.set_option("max_colwidth", None)

NUM_CHUNKS = 3  
slide_window = 7

SNOWFLAKE_USER = st.secrets["SNOWFLAKE_USER"]
SNOWFLAKE_PASSWORD = st.secrets["SNOWFLAKE_PASSWORD"]
SNOWFLAKE_ACCOUNT = st.secrets["SNOWFLAKE_ACCOUNT"]
SNOWFLAKE_DATABASE = st.secrets["SNOWFLAKE_DATABASE"]
SNOWFLAKE_SCHEMA = st.secrets["SNOWFLAKE_SCHEMA"]
SNOWFLAKE_WAREHOUSE = st.secrets["SNOWFLAKE_WAREHOUSE"]

def create_snowpark_session():
    try:
        session = snowpark.Session.builder.configs({
            "user": SNOWFLAKE_USER,
            "password": SNOWFLAKE_PASSWORD,
            "account": SNOWFLAKE_ACCOUNT,
            "warehouse": SNOWFLAKE_WAREHOUSE,
            "database": SNOWFLAKE_DATABASE,
            "schema": SNOWFLAKE_SCHEMA
        }).create()
        return session
    except Exception as e:
        st.error(f"Failed to create Snowpark session: {e}")
        raise

print("account: ", SNOWFLAKE_ACCOUNT)
session = create_snowpark_session()

CORTEX_SEARCH_DATABASE = SNOWFLAKE_DATABASE
CORTEX_SEARCH_SCHEMA = SNOWFLAKE_SCHEMA
CORTEX_SEARCH_SERVICE = "drug_data_search_service" 
svc = session.sql(f"SELECT * FROM {CORTEX_SEARCH_DATABASE}.{CORTEX_SEARCH_SCHEMA}.drug_data_search_service")


COLUMNS = [
    "chunk",
    "category",
    "record_title"
]

def init_messages():
    if st.session_state.clear_conversation or "messages" not in st.session_state:
        st.session_state.messages = []

def config_options():
    st.sidebar.selectbox('Select your model:', ('mixtral-8x7b', 'snowflake-arctic', 'mistral-large2', 'mistral-7b', 'mistral-large'), key="model_name")

    categories = session.sql("SELECT DISTINCT category FROM drug_data").collect()
    cat_list = ['ALL'] + [cat.CATEGORY for cat in categories]

    st.sidebar.selectbox('Select the drug category:', cat_list, key="category_value")
    st.sidebar.checkbox('Do you want that I remember the chat history?', key="use_chat_history", value = True)
    st.sidebar.button("Start Over", key="clear_conversation", on_click=init_messages)
    st.sidebar.expander("Session State").write(st.session_state)

def get_similar_chunks_search_service(query):
    if st.session_state.category_value == "ALL":
        response = svc.search(query, COLUMNS, limit=NUM_CHUNKS)
    else: 
        filter_obj = {"@eq": {"category": st.session_state.category_value}}
        response = svc.search(query, COLUMNS, filter=filter_obj, limit=NUM_CHUNKS)

    if not response.json():
            return "Sorry, I don't have data for that category."

    return response.json()

def get_chat_history():
    chat_history = []
    
    start_index = max(0, len(st.session_state.messages) - slide_window)
    for i in range (start_index , len(st.session_state.messages) -1):
         chat_history.append(st.session_state.messages[i])

    return chat_history

def summarize_question_with_history(chat_history, question):
# To get the right context, use the LLM to first summarize the previous conversation
# This will be used to get embeddings and find similar chunks in the docs for context

    prompt = f"""
        Based on the chat history below and the question, generate a query that extend the question
        with the chat history provided. The query should be in natual language. 
        Answer with only the query. Do not add any explanation.
        
        <chat_history>
        {chat_history}
        </chat_history>
        <question>
        {question}
        </question>
        """
    
    query = session.sql(f"""
        SELECT TRIM(SNOWFLAKE.CORTEX.COMPLETE(
            $${st.session_state.model_name}$$,
            $${prompt}$$
        ), '\\n') AS summary
    """)
    result = query.collect()

    if result:
        summary = result[0]["SUMMARY"]
        if st.session_state.debug:
            st.sidebar.text("Summary to be used to find similar chunks in the docs:")
            st.sidebar.caption(summary)
        return summary
    else:
        return "Unable to generate summary"


def create_prompt(myquestion):
    if st.session_state.use_chat_history:
        chat_history = get_chat_history()

        if chat_history != []: 
                question_summary = summarize_question_with_history(chat_history, myquestion)
                prompt_context =  get_similar_chunks_search_service(question_summary)
        else:
            prompt_context = get_similar_chunks_search_service(myquestion) 
    else:
        prompt_context = get_similar_chunks_search_service(myquestion)
        chat_history = ""
        
    prompt = f"""
           You are an expert chat assistance that extracs information from the CONTEXT provided
           between <context> and </context> tags.
           You offer a chat experience considering the information included in the CHAT HISTORY
           provided between <chat_history> and </chat_history> tags..
           When ansering the question contained between <question> and </question> tags
           be concise and do not hallucinate. 
           If you don´t have the information just say so.
           
           Do not mention the CONTEXT used in your answer.
           Do not mention the CHAT HISTORY used in your asnwer.

           Only anwer the question if you can extract it from the CONTEXT provideed.
           
           <chat_history>
           {chat_history}
           </chat_history>
           <context>          
           {prompt_context}
           </context>
           <question>  
           {myquestion}
           </question>
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
    init_messages()
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if question := st.chat_input("Message MediScope:"):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
    
            question = question.replace("'","")
    
            with st.spinner(f"{st.session_state.model_name} thinking..."):
                response= complete(question)            
                response = response.replace("'", "")
                message_placeholder.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
