import streamlit as st
from openai import OpenAI
import cx_Oracle
import pandas as pd

# Initialize OpenAI client
client = OpenAI(api_key='your API key')

# Function to establish database connection
def get_db_connection(username, password, host, port, sid):
    try:
        dsn_tns = cx_Oracle.makedsn(host, port, sid=sid)
        connection = cx_Oracle.connect(user=username, password=password, dsn=dsn_tns)
        return connection
    except cx_Oracle.DatabaseError as e:
        error, = e.args
        if error.code == 1017:
            st.error("Invalid username or password. Please double-check your credentials.")
        else:
            st.error(f"Database connection failed: {error.message}")
        return None
    

 #Function to fetch list of databases (schemas)
def fetch_database_list(username, password, host, port, sid):
    try:
        connection = get_db_connection(username, password, host, port, sid)
        cursor = connection.cursor()
        cursor.execute("SELECT username FROM all_users WHERE username NOT IN ('SYS', 'SYSTEM')")
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        return databases
    except cx_Oracle.DatabaseError as e:
        return []




# Function to execute SQL query and fetch result
def execute_query(connection, query):
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        if query.strip().lower().startswith("select"):
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            df = pd.DataFrame(rows, columns=columns)
            return df
        else:
            connection.commit()
            cursor.close()
            return "Query executed successfully."
    except cx_Oracle.DatabaseError as e:
        error, = e.args
        return f"Error executing query: {error.message}"

# Function to translate natural language query to SQL using GPT-3
def translate_query_to_sql(query):
    prompt = f"Translate the following natural language query to an SQL statement:\nUser Query: {query}\nSQL Query:"

    try:
        response = client.chat.completions.create(model="gpt-3.5-turbo",
                                                   messages=[{"role": "user", "content": prompt}])

        sql_query = response.choices[0].message.content.strip()
        return sql_query

    except Exception as e:
        st.error(f"Error during translation: {str(e)}")
        return None

# Streamlit app title and introduction
st.title("Oracle Database Query Chatbot")

# Initialize session state for connection details and database selection
if 'username' not in st.session_state:
    st.session_state.username = ""
    st.session_state.password = ""
    st.session_state.host = ""
    st.session_state.port = 1521  # default port
    st.session_state.sid = ""
    st.session_state.database_selected = ""
    st.session_state.databases = []

# Connection details fields
st.session_state.username = st.text_input("Username", value=st.session_state.username)
st.session_state.password = st.text_input("Password", type="password", value=st.session_state.password)
st.session_state.host = st.text_input("Host", value=st.session_state.host)
st.session_state.port = st.number_input("Port", min_value=1, max_value=65535, step=1, value=st.session_state.port)
st.session_state.sid = st.text_input("SID or Service Name", value=st.session_state.sid)

# Test database connection button
if st.button("Test Database Connection"):
    if not all([st.session_state.username, st.session_state.password, st.session_state.host, st.session_state.sid]):
        st.warning("Please fill in all connection details.")
    else:
        connection_status = get_db_connection(st.session_state.username, st.session_state.password, 
                                               st.session_state.host, st.session_state.port, st.session_state.sid)
        if connection_status:
            st.success(connection_status)

# Select database dropdown
if st.session_state.username and st.session_state.password and st.session_state.host and st.session_state.sid:
    databases = fetch_database_list(st.session_state.username, st.session_state.password,
                                    st.session_state.host, st.session_state.port, st.session_state.sid)
    if databases:
        st.session_state.database_selected = st.selectbox("Select Database:", databases)

# Input for user query
query = st.text_area("Ask your database-related question or enter an SQL query:")
# Display response if query is entered
if query and st.session_state.database_selected:
    sql_query = translate_query_to_sql(query)
    if sql_query:
        st.write(f"Translated SQL Query: {sql_query}")  # Debug output

        connection = get_db_connection(st.session_state.username, st.session_state.password, 
                                       st.session_state.host, st.session_state.port, st.session_state.sid)
        if connection:
            result = execute_query(connection, sql_query)
            if isinstance(result, pd.DataFrame):
                st.write(result)
                st.write(f"Query successful. Retrieved {len(result)} rows.")
            else:
                st.write(result)
    else:
        st.error("Failed to translate the query. Please try again.")
