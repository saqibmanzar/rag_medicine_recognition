# MediScope 🩺💊  
Your trusted assistant for medicine information retrieval!  

## 🌟 Inspiration  
One late night, I was unwell and couldn't stop vomiting. Unable to visit a pharmacy or hospital, I searched for medicine at home but couldn't figure out which one to take or how to use it. This experience inspired **MediScope**, a reliable system to guide users through such dilemmas.  

---

## 🤔 What is MediScope?  
**MediScope** is an intelligent medicine information retrieval system designed to:  
- **Answer your questions** about any medicine.  
- **Guide you** on proper usage and safety.  
- **Retrieve relevant information** from trusted datasets using advanced AI techniques.  

---

## 🔧 How it Works  
### 1. Data Collection  
- Leveraged the **PubChem API** to gather medicine data (names, usage, safety, etc.).  
- Preprocessed the data using chunking with `RecursiveCharacterTextSplitter`.  

### 2. Data Storage  
- Bulk-inserted data into **Snowflake** using multiprocessing for efficiency.  

### 3. Classification  
- Categorized drugs (e.g., Antiseptics, Analgesics) using **Mistral Large 2** models.  

### 4. Search and Retrieval  
- Used **Cortex Search** in Snowflake to find relevant chunks of data.  
- Integrated it with **Mistral LLMs** to generate natural-language responses.  

### 5. User Interface  
- Built and deployed a **Streamlit** app to enable users to query the system seamlessly.  

---

## 🚧 Challenges We Faced  
- Finding a suitable open-source dataset.  
- Debugging issues while integrating APIs.  
- Learning new technologies like **Snowflake Cortex** and **Mistral LLMs** from scratch.  

---

## 🏆 Accomplishments  
- Successfully integrated **RAG (Retrieval-Augmented Generation)** with cutting-edge tools.  
- Persisted through 2 months of learning and building the system.  
- Designed a functional and user-friendly solution.  

---

## 📖 What We Learned  
- Advanced tech like **Snowflake Cortex**, **Mistral LLMs**, and **TruLens**.  
- Teamwork, perseverance, and self-belief.  
- The importance of user-centric design in solving real-world problems.  

---

## 🚀 What's Next for MediScope?  
- **Expand the dataset** to enhance accuracy and reliability.  
- Explore **voice-assisted search** for accessibility.  
- Build partnerships with healthcare organizations to scale its impact.  

---

## 💻 How to Use MediScope  
1. **Visit our Streamlit app**: [MediScope on Streamlit](#).  
2. Enter your **medicine-related query** or upload a **photo** of the medicine.  
3. Receive detailed, accurate, and context-aware responses instantly!  

---

## 📂 Directory Structure  
```plaintext
.
├── source/
│   ├── streamlit_chatbot.py      # Main Streamlit app
│   ├── data_collection.py        # Script for data collection and preprocessing
│   ├── drug_classifier.py        # Script for classification with Mistral
│   ├── initiate_cortex.py        # to turn on the cortex search service
│   ├── disable_cortex.py         # to turn off the cortex search service
├── README.md                     # Project documentation
├── requirements.txt              # Required libraries
└── .env                          # Snowflake and API credentials
