import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

# --- CONFIGURATION STYLE ÉLITE ---
st.set_page_config(page_title="MyFoodvisor Pro", page_icon="🍏", layout="centered")

# CSS pour simuler une application mobile moderne
st.markdown("""
    <style>
    .main { background-color: #F7F8FA; }
    .stApp { max-width: 450px; margin: 0 auto; border-radius: 30px; }
    .macro-container {
        background: white; padding: 15px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 10px;
    }
    .stat-label { font-size: 0.8rem; color: #8E8E93; font-weight: 600; }
    .stat-value { font-size: 1.1rem; font-weight: 700; color: #1C1C1E; }
    .stProgress > div > div > div > div { background-color: #2DCC70; }
    /* Style Bouton Foodvisor */
    .stButton>button {
        border-radius: 25px; background: #2DCC70; border: none;
        color: white; font-weight: 700; width: 100%; height: 50px;
        transition: 0.3s;
    }
    .stButton>button:hover { background: #27ae60; transform: scale(1.02); }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION ---
if 'historique_repas' not in st.session_state:
    st.session_state.historique_repas = pd.DataFrame(columns=["Date", "Aliment", "Calories", "P", "G", "L", "Fi"])

# --- CALCUL DES OBJECTIFS MUSCULATION ---
st.sidebar.markdown("### ⚙️ Coach Personnel")
poids = st.sidebar.number_input("Poids (kg)", 40, 150, 75)
objectif = st.sidebar.select_slider("Objectif", options=["Sèche Extreme", "Sèche", "Maintenance", "Prise de Masse", "Prise de Masse Pro"])

# Logique de nutrition sportive (Protéines élevées pour le muscle)
multiplicateurs = {
    "Sèche Extreme": {"cal": 24, "p": 2.6, "l": 0.7, "fi": 0.5},
    "Sèche": {"cal": 27, "p": 2.4, "l": 0.8, "fi": 0.5},
    "Maintenance": {"cal": 32, "p": 2.0, "l": 0.9, "fi": 0.4},
    "Prise de Masse": {"cal": 37, "p": 2.1, "l": 1.0, "fi": 0.4},
    "Prise de Masse Pro": {"cal": 42, "p": 2.2, "l": 1.1, "fi": 0.4}
}

m = multiplicateurs[objectif]
c_cal = int(poids * m['cal'])
c_p, c_l, c_fi = int(poids * m['p']), int(poids * m['l']), int(poids * m['fi'])
c_g = int((c_cal - (c_p * 4) - (c_l * 9)) / 4)

# --- DASHBOARD VISUEL ---
df_jour = st.session_state.historique_repas[st.session_state.historique_repas['Date'] == date.today()]
tot_c, tot_p, tot_g, tot_l, tot_f = df_jour['Calories'].sum(), df_jour['P'].sum(), df_jour['G'].sum(), df_jour['L'].sum(), df_jour['Fi'].sum()

# Anneau de Calories central
fig = go.Figure(go.Pie(
    values=[tot_c, max(0, c_cal - tot_c)], hole=.85,
    marker_colors=['#2DCC70', '#E5E5EA'], showlegend=False, hoverinfo='none'
))
fig.update_layout(
    annotations=[dict(text=f'<b>{int(tot_c)}</b><br><span style="font-size:12px; color:gray;">kcal / {c_cal}</span>', 
                 x=0.5, y=0.5, font_size=28, showarrow=False)],
    margin=dict(t=10, b=10, l=10, r=10), height=220
)
st.plotly_chart(fig, use_container_width=True)

# Grille des Macronutriments (Design Cards)
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

def draw_card(col, label, current, target, unit="g"):
    percent = min(current/target, 1.0) if target > 0 else 0
    with col:
        st.markdown(f"""
        <div class="macro-container">
            <div class="stat-label">{label.upper()}</div>
            <div class="stat-value">{int(current)}{unit} <span style="font-size:0.7rem; color:gray;">/ {target}{unit}</span></div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(percent)

draw_card(col1, "Protéines 🥩", tot_p, c_p)
draw_card(col2, "Glucides 🍝", tot_g, c_g)
draw_card(col3, "Lipides 🥑", tot_l, c_l)
draw_card(col4, "Fibres 🥬", tot_f, c_fi)

st.markdown("---")

# --- ACTIONS ---
tab_add, tab_history = st.tabs(["➕ Ajouter", "📜 Journal"])

with tab_add:
    st.markdown("### 🪄 Magic Scan Gemini")
    magic = st.text_input("", placeholder="Aliment | Cal | P | G | L | Fibres")
    if st.button("Synchroniser le repas"):
        if magic:
            try:
                p = [i.strip() for i in magic.split("|")]
                new_row = pd.DataFrame([{"Date": date.today(), "Aliment": p[0], "Calories": float(p[1]), "P": float(p[2]), "G": float(p[3]), "L": float(p[4]), "Fi": float(p[5])}])
                st.session_state.historique_repas = pd.concat([st.session_state.historique_repas, new_row], ignore_index=True)
                st.success("C'est dans la boîte !")
                st.rerun()
            except:
                st.error("Format requis : Nom | Cal | P | G | L | Fi")

with tab_history:
    if df_jour.empty:
        st.info("Aucun repas aujourd'hui.")
    for i, row in df_jour.iterrows():
        st.markdown(f"""
        <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left: 4px solid #2DCC70;">
            <b>{row['Aliment']}</b> <span style="float:right; color:#2DCC70;">{int(row['Calories'])} kcal</span><br>
            <small style="color:gray;">P: {row['P']}g · G: {row['G']}g · L: {row['L']}g · F: {row['Fi']}g</small>
        </div>
        """, unsafe_allow_html=True)
