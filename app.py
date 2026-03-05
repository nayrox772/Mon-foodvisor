import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import io

# Configuration
st.set_page_config(page_title="Gemini-Visor Pro", page_icon="💪", layout="wide")

# --- INITIALISATION ---
if 'historique_repas' not in st.session_state:
    st.session_state.historique_repas = pd.DataFrame(columns=["Date", "Aliment", "Calories", "Protéines", "Glucides", "Lipides"])
if 'historique_poids' not in st.session_state:
    st.session_state.historique_poids = pd.DataFrame(columns=["Date", "Poids"])

st.title("💪 Mon Coach Nutrition Intelligent")

# --- SIDEBAR : CALCULATEUR ---
st.sidebar.header("👤 Profil")
poids_actuel = st.sidebar.number_input("Poids (kg)", min_value=40.0, value=75.0)
objectif = st.sidebar.selectbox("Objectif", ["Maintenance", "Prise de masse", "Sèche"])

if objectif == "Prise de masse":
    c_cal, c_prot = int(poids_actuel * 38), int(poids_actuel * 2.2)
elif objectif == "Sèche":
    c_cal, c_prot = int(poids_actuel * 25), int(poids_actuel * 2.4)
else:
    c_cal, c_prot = int(poids_actuel * 30), int(poids_actuel * 2.0)

st.sidebar.info(f"🎯 Cibles : {c_cal} kcal | {c_prot}g Protéines")

# --- ONGLETS ---
tab1, tab2, tab3 = st.tabs(["🍽️ Journal & Magic Paste", "📈 Analyses", "⚖️ Santé & Poids"])

with tab1:
    st.subheader("🚀 Saisie Rapide (Magic Paste)")
    st.write("Colle ici la ligne que je t'ai donnée après l'analyse de ta photo :")
    magic_input = st.text_input("Format : Aliment | Cal | P | G | L", placeholder="Ex: Poulet Riz | 500 | 40 | 60 | 10")
    
    if st.button("🪄 Synchroniser le repas"):
        try:
            parts = [p.strip() for p in magic_input.split("|")]
            if len(parts) == 5:
                nouveau_repas = pd.DataFrame([{
                    "Date": date.today(),
                    "Aliment": parts[0],
                    "Calories": float(parts[1]),
                    "Protéines": float(parts[2]),
                    "Glucides": float(parts[3]),
                    "Lipides": float(parts[4])
                }])
                st.session_state.historique_repas = pd.concat([st.session_state.historique_repas, nouveau_repas], ignore_index=True)
                st.success(f"✅ {parts[0]} ajouté avec succès !")
            else:
                st.error("Format invalide. Utilise bien le séparateur '|'")
        except:
            st.error("Erreur de saisie. Vérifie les chiffres.")

    st.divider()
    
    st.subheader("📅 Récapitulatif du jour")
    df_repas = st.session_state.historique_repas
    if not df_repas.empty:
        df_repas['Date'] = pd.to_datetime(df_repas['Date']).dt.date
        df_jour = df_repas[df_repas['Date'] == date.today()]
        
        if not df_jour.empty:
            c1, c2 = st.columns(2)
            tot_c = df_jour['Calories'].sum()
            tot_p = df_jour['Protéines'].sum()
            c1.metric("Calories", f"{tot_c:.0f} / {c_cal}", delta=int(tot_c - c_cal), delta_color="inverse")
            c2.metric("Protéines", f"{tot_p:.1f}g / {c_prot}g", delta=int(tot_p - c_prot))
            st.table(df_jour[["Aliment", "Calories", "Protéines", "Glucides", "Lipides"]])
        else:
            st.info("Rien pour aujourd'hui. Utilise le Magic Paste ci-dessus !")

# --- (Le reste du code pour les graphiques et le poids reste identique à la version précédente) ---
with tab2:
    if not st.session_state.historique_repas.empty:
        df_hebdo = st.session_state.historique_repas.groupby('Date')['Calories'].sum().reset_index()
        fig_cal = px.line(df_hebdo, x='Date', y='Calories', title="Calories sur 7 jours")
        fig_cal.add_hline(y=c_cal, line_dash="dash", line_color="red")
        st.plotly_chart(fig_cal, use_container_width=True)

with tab3:
    st.subheader("⚖️ Suivi du poids & Import CSV")
    uploaded_file = st.file_uploader("Importer CSV Santé", type="csv")
    if uploaded_file:
        df_csv = pd.read_csv(uploaded_file)
        df_csv['Date'] = pd.to_datetime(df_csv['Date']).dt.date
        st.session_state.historique_poids = pd.concat([st.session_state.historique_poids, df_csv]).drop_duplicates('Date')
    
    if not st.session_state.historique_poids.empty:
        fig_p = px.area(st.session_state.historique_poids.sort_values('Date'), x='Date', y='Poids', title="Évolution du poids")
        st.plotly_chart(fig_p, use_container_width=True)
