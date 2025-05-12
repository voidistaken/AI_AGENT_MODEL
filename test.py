import streamlit as st
import numpy as np
from utils.user_data import store_user_data
from utils.vector_utils import search_similar_embeddings
from utils.embedding import generate_embedding  # Assuming this exists in your utils
from utils.db import retrieve_user_data

st.title("Simple DB Test")

user_id = "test-user"
data_key = "test-key"
data_value = "test-value"

# Store basic key-value
if st.button("Store Data"):
    store_user_data(user_id, data_key, data_value)
    st.success(f"Stored '{data_value}' for user '{user_id}' with key '{data_key}'")

# Retrieve it
if st.button("Retrieve Data"):
    retrieved_value = retrieve_user_data(user_id, data_key)
    if retrieved_value:
        st.info(f"Retrieved value: '{retrieved_value}'")
    else:
        st.warning("No data found for that user and key.")

# Search similar embeddings
st.subheader("Embedding Similarity Search Test")
query_text = st.text_input("Enter text to embed and search:", "What is the capital of France?")
top_k = st.slider("Top K results", min_value=1, max_value=10, value=3)

if st.button("Search Similar Embeddings"):
    embedding = generate_embedding(query_text)
    results = search_similar_embeddings(embedding, user_id="default-user", top_k=top_k)

    if results:
        st.success("Found similar entries:")
        for r in results:
            st.write(f"ID: {r[0]}, Data: {r[1]}, Distance: {r[2]:.4f}")
    else:
        st.warning("No similar embeddings found.")
