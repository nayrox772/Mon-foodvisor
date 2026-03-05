import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# --- CONFIGURATION STYLE FOODVISOR ---
st.set_page_config(page_title="Gemini-Visor Pro", page_icon="🥗", layout="centered")

# Injection de CSS pour le look "App Mobile"
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        background-color: #4CAF50;
        color: white;
        border: none;
        height: 3em;
        font-weight: bold;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stTextInput>div>div>input { border-radius: 15px; }
    div[data-testid="stMetricValue"] { color: #4CAF50; font-size: 1.8rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION ---
if 'historique_repas' not in st.session_state:
    st.session_state.historique_repas = pd.DataFrame(columns=["Date", "Aliment", "Calories", "Protéines", "Glucides", "Lipides"])

# --- HEADER TYPE APP ---
st.markdown("<h1 style='text-align: center; color: #2E7D32;'>🥗 Mon Foodvisor</h1>", unsafe_allow_html=True)

# --- CALCUL DES OBJECTIFS ---
poids = st.sidebar.slider("Poids actuel (kg)", 40, 150, 75)
objectif = st.sidebar.selectbox("Mon Objectif", ["Prise de masse", "Sèche", "Maintenance"])

if objectif == "Prise de masse":
    c_cal, c_prot, color = int(poids * 38), int(poids * 2.2), "#2196F3"
elif objectif == "Sèche":
    c_cal, c_prot, color = int(poids * 25), int(poids * 2.4), "#FF9800"
else:
    c_cal, c_prot, color = int(poids * 30), int(poids * 2.0), "#4CAF50"

# --- DASHBOARD PRINCIPAL ---
df_repas = st.session_state.historique_repas
df_repas['Date'] = pd.to_datetime(df_repas['Date']).dt.date
df_jour = df_repas[df_repas['Date'] == date.today()]

tot_cal = df_jour['Calories'].sum()
tot_prot = df_jour['Protéines'].sum()

# Cercles de progression (Layout interactif)
col1, col2 = st.columns(2)
with col1:
    st.metric("Énergie (kcal)", f"{int(tot_cal)}", f"{int(c_cal - tot_cal)} restant")
    st.progress(min(tot_cal / c_cal, 1.0))
with col2:
    st.metric("Protéines (g)", f"{tot_prot:.1f}g", f"{int(c_prot - tot_prot)}g restant")
    st.progress(min(tot_prot / c_prot, 1.0))

st.divider()

# --- NAVIGATION ---
tab1, tab2, tab3 = st.tabs(["⚡ Magic Paste", "📊 Historique", "⚖️ Poids"])

with tab1:
    st.markdown("### 🪄 Ajouter un repas")
    magic_input = st.text_input("", placeholder="Colle la ligne de Gemini ici...")
    
    if st.button("Ajouter au journal"):
        if magic_input:
            try:
                parts = magic_input.split("|")
                new_row = pd.DataFrame([{
                    "Date": date.today(),
                    "Aliment": parts[0].strip(),
                    "Calories": float(parts[1]),
                    "Protéines": float(parts[2]),
                    "Glucides": float(parts[3]),
                    "Lipides": float(parts[4])
                }])
                st.session_state.historique_repas = pd.concat([st.session_state.historique_repas, new_row], ignore_index=True)
                st.balloons() # Petit effet de fête !
                st.rerun()
            except:
                st.error("Oups ! Le format n'est pas bon.")

    # Liste des repas du jour avec style
    for i, row in df_jour.iterrows():
        with st.container():
            st.markdown(f"""
            <div style="background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid {color};">
                <span style="float: right; font-weight: bold;">{row['Calories']} kcal</span>
                <div style="font-weight: bold;">{row['Aliment']}</div>
                <div style="font-size: 0.8rem; color: gray;">P: {row['Protéines']}g | G: {row['Glucides']}g | L: {row['Lipides']}g</div>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.subheader("Ta semaine en un coup d'œil")
    if not df_repas.empty:
        fig = px.bar(df_repas.groupby("Date")["Calories"].sum().reset_index(), 
                     x="Date", y="Calories", color_discrete_sequence=[color])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.info("Cette section est prête pour tes imports CSV Santé !")
