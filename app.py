import streamlit as st
import numpy as np
import re
import pickle
import joblib
import torch
import os
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from transformers import BertTokenizer, BertForSequenceClassification, AutoTokenizer, AutoModelForSequenceClassification

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Analisis Emosi Lirik Lagu", page_icon="🎵", layout="wide")

# --- FUNGSI PEMBERSIH TEKS ---
def clean_text(text):
    text = text.lower()
    text = re.sub(r'\[.*?\]|\(.*?\)', ' ', text)
    text = re.sub(r'[^a-z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- LOAD ESENSIAL ---
@st.cache_resource
def load_essentials():
    base_path = 'models'
    le = joblib.load(os.path.join(base_path, 'label_encoder.pkl'))
    return le

# --- LOAD MODEL (Lazy Loading) ---
@st.cache_resource
def load_lstm():
    m = load_model('models/lstm/lstm_model.h5')
    with open('models/lstm/tokenizer.pickle', 'rb') as h:
        t = pickle.load(h)
    return m, t

@st.cache_resource
def load_indobert():
    m = BertForSequenceClassification.from_pretrained('models/indobert')
    t = BertTokenizer.from_pretrained('models/indobert')
    return m, t

@st.cache_resource
def load_indoroberta():
    m = AutoModelForSequenceClassification.from_pretrained('models/indoroberta')
    t = AutoTokenizer.from_pretrained('models/indoroberta')
    return m, t

# --- FUNGSI TAMPILAN LABEL (FIX DI SINI) ---
def get_emo_label(emo_string):
    icons = {
        "bahagia": "✨ 😊", 
        "sedih": "😭 💙", 
        "marah": "😡 🔥", 
        "takut": "😨 🌪️"
    }
    icon = icons.get(emo_string.lower(), "🎭")
    # Mengembalikan Gabungan Emoji dan Nama Emosinya
    return f"{icon} {emo_string.upper()}"

# --- SIDEBAR ---
st.sidebar.title("⚙️ Model Setting")
option = st.sidebar.selectbox(
    'Pilih Model:',
    ('Semua Model (Perbandingan)', 'LSTM (Scratch)', 'IndoBERT (Pre-trained)', 'IndoRoBERTa (Pre-trained)')
)

# --- UI UTAMA ---
st.title("🎶 Lyrics Emotion Classifier")
st.write(f"Model Aktif: **{option}**")

lirik_input = st.text_area("Masukkan potongan lirik lagu Indonesia:", height=150)

if st.button("🚀 Prediksi Emosi"):
    if not lirik_input:
        st.warning("Input lirik dulu!")
    else:
        le = load_essentials()
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        results = {}

        with st.spinner('Menghitung prediksi...'):
            # 1. Logika LSTM
            if option in ['Semua Model (Perbandingan)', 'LSTM (Scratch)']:
                m_lstm, t_lstm = load_lstm()
                lirik_bersih = clean_text(lirik_input)
                seq = t_lstm.texts_to_sequences([lirik_bersih])
                padded = pad_sequences(seq, maxlen=150)
                p_lstm = np.argmax(m_lstm.predict(padded, verbose=0))
                results['LSTM'] = le.inverse_transform([p_lstm])[0]

            # 2. Logika IndoBERT
            if option in ['Semua Model (Perbandingan)', 'IndoBERT (Pre-trained)']:
                m_bert, t_bert = load_indobert()
                m_bert.to(device)
                in_bert = t_bert(lirik_input, return_tensors="pt", truncation=True, max_length=128, padding=True).to(device)
                with torch.no_grad():
                    out_bert = m_bert(**in_bert)
                    p_bert = torch.argmax(out_bert.logits, dim=1).item()
                results['IndoBERT'] = le.inverse_transform([p_bert])[0]

            # 3. Logika IndoRoBERTa
            if option in ['Semua Model (Perbandingan)', 'IndoRoBERTa (Pre-trained)']:
                m_ro, t_ro = load_indoroberta()
                m_ro.to(device)
                in_ro = t_ro(lirik_input, return_tensors="pt", truncation=True, max_length=128, padding=True).to(device)
                with torch.no_grad():
                    out_ro = m_ro(**in_ro)
                    p_ro = torch.argmax(out_ro.logits, dim=1).item()
                results['IndoRoBERTa'] = le.inverse_transform([p_ro])[0]

        # --- TAMPILKAN HASIL ---
        st.divider()
        cols = st.columns(len(results))
        
        for i, (m_name, res_text) in enumerate(results.items()):
            with cols[i]:
                st.markdown(f"### {m_name}")
                # Memanggil fungsi fix yang baru
                st.success(get_emo_label(res_text))
                
                # Info Akurasi
                acc = {"LSTM": "64%", "IndoBERT": "85%", "IndoRoBERTa": "75%"}
                st.caption(f"Akurasi: {acc[m_name]}")

st.divider()
st.caption("UAP Machine Learning - PDM Environment")