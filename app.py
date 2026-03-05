import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

# --- CONFIGURATION DU DESIGN ---
st.set_page_config(page_title="NutriTrack Pro", page_icon="🍎", layout="centered")

st.markdown("""
    <style>
    /* Global Style */
    .main { background-color: #F2F2F7; }
    .stApp { max-width: 480px; margin: 0 auto; background-color: #F2F2F7; }
    
    /* Cards Style */
    .meal-card {
        background: white; border-radius: 20px; padding: 15px; margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #E5E5EA;
    }
    .macro-tag {
        font-size: 0.75rem; color: #8E8E93; margin-right: 8px;
    }
    
    /* Bottom Nav */
    .nav-bar {
        position: fixed; bottom: 0; left: 0; width: 100%; background: white;
        display: flex; justify-content: space-around; padding: 10px;
        border-top: 1px solid #E5E5EA; z-index: 1000;
    }
    
    /* Progress Bars */
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #FF9500, #FFCC00); }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE DE CALCUL ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["Date", "Repas", "Nom", "Cal", "P", "G", "L", "Fi"])

# Sidebar pour le profil (comme dans l'onglet Profil de la vidéo)
st.sidebar.header("👤 Mon Profil")
poids = st.sidebar.number_input("Poids actuel (kg)", 40.0, 150.0, 80.0)
obj_type = st.sidebar.selectbox("Objectif", ["Prise de muscle", "Perte de graisse", "Maintien"])

# Cibles basées sur la vidéo
if obj_type == "Prise de muscle":
    c_cal, c_p, c_g, c_l, c_fi = 3168, 158, 456, 79, 35
elif obj_type == "Perte de graisse":
    c_cal, c_p, c_g, c_l, c_fi = 2405, 174, 286, 63, 35
else:
    c_cal, c_p, c_g, c_l, c_fi = 2829, 126, 404, 79, 35

# --- INTERFACE PRINCIPALE ---
st.markdown(f"<h3 style='text-align:center;'>NutriTrack <span style='font-size:0.8rem; color:orange;'>💪 {obj_type}</span></h3>", unsafe_allow_html=True)

# Données du jour
df_jour = st.session_state.db[st.session_state.db['Date'] == date.today()]
t_cal, t_p, t_g, t_l, t_f = df_jour['Cal'].sum(), df_jour['P'].sum(), df_jour['G'].sum(), df_jour['L'].sum(), df_jour['Fi'].sum()

# Dashboard Circulaire (Inspiré de la vidéo)
fig = go.Figure(go.Pie(
    values=[t_cal, max(0, c_cal - t_cal)], hole=.8,
    marker_colors=['#FF9500', '#E5E5EA'], showlegend=False, textinfo='none'
))
fig.update_layout(
    annotations=[dict(text=f"<b>{int(c_cal - t_cal)}</b><br><span style='font-size:12px; color:gray;'>kcal restantes</span>", x=0.5, y=0.5, font_size=24, showarrow=False)],
    margin=dict(t=0, b=0, l=0, r=0), height=200, paper_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig, use_container_width=True)

# Macros Horizontal Bars
def macro_row(label, val, target, color):
    col1, col2 = st.columns([1, 4])
    col1.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
    col2.progress(min(val/target, 1.0))
    st.markdown(f"<p style='text-align:right; font-size:0.7rem; margin-top:-15px;'>{int(val)}/{target}g</p>", unsafe_allow_html=True)

macro_row("Prot", t_p, c_p, "orange")
macro_row("Gluc", t_g, c_g, "blue")
macro_row("Lip", t_l, c_l, "red")

st.markdown("---")

# --- AJOUT DE REPAS ---
with st.expander("➕ Ajouter un aliment (Magic Scan)"):
    repas_cat = st.selectbox("Repas", ["Petit-déjeuner", "Déjeuner", "Dîner", "Collation"])
    magic_input = st.text_input("Nom | Cal | P | G | L | Fi")
    if st.button("Enregistrer"):
        try:
            p = [x.strip() for x in magic_input.split("|")]
            new_data = pd.DataFrame([{"Date": date.today(), "Repas": repas_cat, "Nom": p[0], "Cal": float(p[1]), "P": float(p[2]), "G": float(p[3]), "L": float(p[4]), "Fi": float(p[5])}])
            st.session_state.db = pd.concat([st.session_state.db, new_data], ignore_index=True)
            st.rerun()
        except:
            st.error("Format : Poulet | 200 | 30 | 0 | 5 | 0")

# --- LISTE DES REPAS (Design Vidéo) ---
for cat, icon in zip(["Petit-déjeuner", "Déjeuner", "Dîner", "Collation"], ["🌆", "☀️", "🌙", "🍎"]):
    st.markdown(f"#### {icon} {cat}")
    items = df_jour[df_jour['Repas'] == cat]
    if items.empty:
        st.markdown("<p style='color:gray; font-size:0.8rem;'>Aucun aliment ajouté</p>", unsafe_allow_html=True)
    for _, row in items.iterrows():
        st.markdown(f"""
        <div class="meal-card">
            <span style="float:right; color:#FF9500; font-weight:bold;">{int(row['Cal'])} kcal</span>
            <b>{row['Nom']}</b><br>
            <span class="macro-tag">P: {row['P']}g</span>
            <span class="macro-tag">G: {row['G']}g</span>
            <span class="macro-tag">L: {row['L']}g</span>
        </div>
        """, unsafe_allow_html=True)

# Barre de navigation fictive (pour le design)
st.markdown("""
    <div class="nav-bar">
        <span style="color:#FF9500;">🏠<br><small>Accueil</small></span>
        <span style="color:gray;">🎯<br><small>Objectifs</small></span>
        <span style="color:gray;">📊<br><small>Stats</small></span>
        <span style="color:gray;">👤<br><small>Profil</small></span>
    </div>
    <br><br>
    """, unsafe_allow_html=True)
