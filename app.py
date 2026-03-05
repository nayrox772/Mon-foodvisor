"""
NutriScan — Application de suivi nutritionnel Streamlit
Inspirée de Foodvisor, propulsée par Claude Vision (Anthropic)

Colle ce fichier dans app.py et déploie sur Streamlit Cloud.
"""

import streamlit as st
import anthropic
import base64
import json
import csv
import datetime
import io
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image

# ─────────────────────────────────────────────
#  CONFIG & STYLE
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="NutriScan",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 800 !important;
}

/* Dark background */
.stApp {
    background: #0A0F0D;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #111A14 !important;
    border-right: 1px solid #1E2E22;
}

/* Cards */
.nutri-card {
    background: #111A14;
    border: 1px solid #1E2E22;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
}

/* Metric big */
.metric-big {
    font-family: 'Syne', sans-serif;
    font-size: 3.2rem;
    font-weight: 800;
    line-height: 1;
}

.cal-color   { color: #F0C55A; }
.prot-color  { color: #5AB4F0; }
.carb-color  { color: #4ADE80; }
.fat-color   { color: #F87171; }
.fiber-color { color: #C084FC; }

/* Food tag */
.food-tag {
    display: inline-block;
    background: #1E2E22;
    border: 1px solid #2D4A33;
    border-radius: 8px;
    padding: 6px 14px;
    margin: 4px;
    font-size: 0.85rem;
    color: #A3C9A8;
}

/* Health score badge */
.score-badge {
    display: inline-block;
    border-radius: 50px;
    padding: 4px 16px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.9rem;
}
.score-good  { background: #0D2818; color: #4ADE80; border: 1px solid #166534; }
.score-ok    { background: #2A1F00; color: #F0C55A; border: 1px solid #854D0E; }
.score-bad   { background: #2A0A0A; color: #F87171; border: 1px solid #7F1D1D; }

/* Progress bar custom */
.macro-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}
.macro-label { width: 90px; color: #6B8F72; font-size: 0.85rem; }
.macro-bar-bg {
    flex: 1;
    height: 8px;
    background: #1E2E22;
    border-radius: 4px;
    overflow: hidden;
}
.macro-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s ease;
}
.macro-val { width: 60px; text-align: right; font-size: 0.9rem; color: #E0EDE2; font-weight: 500; }

/* Meal row */
.meal-row {
    background: #111A14;
    border: 1px solid #1E2E22;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Button overrides */
.stButton > button {
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
}

/* Divider */
hr { border-color: #1E2E22 !important; }

/* Hide default streamlit elements */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CONSTANTES
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es NutriScan, expert en nutrition. Analyse le repas et réponds UNIQUEMENT en JSON valide (sans markdown) :
{
  "meal_name": "Nom du repas",
  "confidence": 85,
  "foods": [
    {"name": "Aliment", "quantity_g": 150, "calories": 200, "protein_g": 10, "carbs_g": 25, "fat_g": 8, "fiber_g": 3}
  ],
  "total": {"calories": 200, "protein_g": 10, "carbs_g": 25, "fat_g": 8, "fiber_g": 3},
  "health_score": 7,
  "notes": "Commentaire court sur l'équilibre nutritionnel"
}"""

DEFAULT_GOALS = {"calories": 2000, "protein_g": 150, "carbs_g": 250, "fat_g": 65}

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────

def init_state():
    if "meals" not in st.session_state:
        st.session_state.meals = []
    if "goals" not in st.session_state:
        st.session_state.goals = DEFAULT_GOALS.copy()
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

init_state()

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.environ.get("ANTHROPIC_API_KEY", "")

def get_today_meals():
    today = datetime.date.today().isoformat()
    return [m for m in st.session_state.meals if m.get("date") == today]

def get_daily_totals(meals=None):
    if meals is None:
        meals = get_today_meals()
    totals = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0}
    for meal in meals:
        t = meal.get("total", {})
        for k in totals:
            totals[k] += t.get(k, 0)
    return totals

def health_score_badge(score):
    if score >= 7:
        cls = "score-good"
        emoji = "🟢"
    elif score >= 5:
        cls = "score-ok"
        emoji = "🟡"
    else:
        cls = "score-bad"
        emoji = "🔴"
    return f'<span class="score-badge {cls}">{emoji} {score}/10</span>'

def macro_bar_html(label, value, goal, color):
    pct = min(int(value / max(goal, 1) * 100), 100)
    return f"""
    <div class="macro-row">
        <span class="macro-label">{label}</span>
        <div class="macro-bar-bg">
            <div class="macro-bar-fill" style="width:{pct}%; background:{color};"></div>
        </div>
        <span class="macro-val">{value:.0f}g</span>
    </div>"""

def analyze_image(image_bytes, media_type="image/jpeg"):
    key = get_api_key()
    if not key:
        st.error("⚠️ Clé API Anthropic manquante. Configure-la dans les paramètres.")
        return None
    client = anthropic.Anthropic(api_key=key)
    b64 = base64.standard_b64encode(image_bytes).decode()
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analyse ce repas."}
        ]}]
    )
    raw = msg.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    return json.loads(raw)

def analyze_text(description):
    key = get_api_key()
    if not key:
        st.error("⚠️ Clé API Anthropic manquante. Configure-la dans les paramètres.")
        return None
    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Analyse ce repas : {description}"}]
    )
    raw = msg.content[0].text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    return json.loads(raw)

def add_meal(result):
    result["id"] = datetime.datetime.now().isoformat()
    result["date"] = datetime.date.today().isoformat()
    result["time"] = datetime.datetime.now().strftime("%H:%M")
    st.session_state.meals.append(result)

def export_json():
    return json.dumps(st.session_state.meals, ensure_ascii=False, indent=2).encode("utf-8")

def export_csv():
    buf = io.StringIO()
    fields = ["id","date","time","meal_name","calories","protein_g","carbs_g","fat_g","fiber_g","health_score","notes"]
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for meal in st.session_state.meals:
        t = meal.get("total", {})
        w.writerow({
            "id": meal.get("id",""), "date": meal.get("date",""),
            "time": meal.get("time",""), "meal_name": meal.get("meal_name",""),
            "calories": t.get("calories",0), "protein_g": t.get("protein_g",0),
            "carbs_g": t.get("carbs_g",0), "fat_g": t.get("fat_g",0),
            "fiber_g": t.get("fiber_g",0), "health_score": meal.get("health_score",0),
            "notes": meal.get("notes",""),
        })
    return buf.getvalue().encode("utf-8")

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='padding: 12px 0 24px 0'>
        <span style='font-family:Syne;font-size:1.8rem;font-weight:800;color:#4ADE80'>🥗 NutriScan</span>
    </div>
    """, unsafe_allow_html=True)

    pages = {
        "dashboard": "🏠  Tableau de bord",
        "analyze":   "📸  Analyser un repas",
        "history":   "📋  Historique",
        "settings":  "⚙️  Paramètres",
    }
    for key, label in pages.items():
        active = st.session_state.page == key
        if st.button(label, key=f"nav_{key}",
                     use_container_width=True,
                     type="primary" if active else "secondary"):
            st.session_state.page = key
            st.rerun()

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📤 JSON", export_json(),
                           file_name="nutriscan_export.json",
                           mime="application/json",
                           use_container_width=True)
    with col2:
        st.download_button("📤 CSV", export_csv(),
                           file_name="nutriscan_export.csv",
                           mime="text/csv",
                           use_container_width=True)

    uploaded_import = st.file_uploader("📥 Importer JSON", type=["json"],
                                        label_visibility="collapsed")
    if uploaded_import:
        try:
            imported = json.load(uploaded_import)
            existing_ids = {m.get("id") for m in st.session_state.meals}
            added = 0
            for meal in imported:
                if meal.get("id") not in existing_ids:
                    st.session_state.meals.append(meal)
                    added += 1
            st.success(f"✅ {added} repas importés")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur import : {e}")

# ─────────────────────────────────────────────
#  PAGE : DASHBOARD
# ─────────────────────────────────────────────

if st.session_state.page == "dashboard":
    today_meals = get_today_meals()
    totals = get_daily_totals(today_meals)
    goals = st.session_state.goals

    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown(f"<h1 style='color:#E0EDE2;margin-bottom:4px'>Aujourd'hui</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#6B8F72;margin-top:0'>{datetime.date.today().strftime('%A %d %B %Y').capitalize()}</p>", unsafe_allow_html=True)
    with col_btn:
        st.write("")
        if st.button("＋ Ajouter un repas", type="primary", use_container_width=True):
            st.session_state.page = "analyze"
            st.rerun()

    # ── Calories + Macros ──
    col_cal, col_macros = st.columns([1, 2])

    with col_cal:
        st.markdown('<div class="nutri-card">', unsafe_allow_html=True)
        cals = totals["calories"]
        goal_cal = goals["calories"]
        remaining = max(goal_cal - cals, 0)
        pct = min(cals / max(goal_cal, 1), 1.0)

        fig = go.Figure(go.Pie(
            values=[cals, max(goal_cal - cals, 0)],
            hole=0.75,
            marker_colors=["#F0C55A", "#1E2E22"],
            textinfo="none",
            hoverinfo="skip",
        ))
        fig.update_layout(
            showlegend=False, margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=200,
            annotations=[dict(
                text=f"<b>{cals:.0f}</b>",
                x=0.5, y=0.5, font=dict(size=30, color="#F0C55A", family="Syne"),
                showarrow=False
            )]
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f"<p style='text-align:center;color:#6B8F72;margin-top:-16px'>/ {goal_cal} kcal &nbsp;•&nbsp; <b style='color:#F0C55A'>{remaining:.0f}</b> restantes</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_macros:
        st.markdown('<div class="nutri-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='color:#E0EDE2;font-size:1rem;margin-bottom:16px'>Macronutriments</h3>", unsafe_allow_html=True)
        html = ""
        html += macro_bar_html("Protéines", totals["protein_g"], goals["protein_g"], "#5AB4F0")
        html += macro_bar_html("Glucides",  totals["carbs_g"],   goals["carbs_g"],   "#4ADE80")
        html += macro_bar_html("Lipides",   totals["fat_g"],     goals["fat_g"],     "#F87171")
        html += macro_bar_html("Fibres",    totals["fiber_g"],   30,                  "#C084FC")
        st.markdown(html, unsafe_allow_html=True)

        # Mini macros row
        c1, c2, c3 = st.columns(3)
        c1.metric("Protéines", f"{totals['protein_g']:.0f}g", f"/{goals['protein_g']}g")
        c2.metric("Glucides",  f"{totals['carbs_g']:.0f}g",   f"/{goals['carbs_g']}g")
        c3.metric("Lipides",   f"{totals['fat_g']:.0f}g",     f"/{goals['fat_g']}g")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Repas du jour ──
    st.markdown("<h2 style='color:#E0EDE2;margin-top:8px'>Repas du jour</h2>", unsafe_allow_html=True)

    if not today_meals:
        st.markdown('<div class="nutri-card" style="text-align:center;padding:40px"><p style="color:#6B8F72;font-size:1.1rem">Aucun repas enregistré aujourd\'hui.<br>Cliquez sur <b style="color:#4ADE80">+ Ajouter un repas</b> pour commencer.</p></div>', unsafe_allow_html=True)
    else:
        for i, meal in enumerate(reversed(today_meals)):
            total = meal.get("total", {})
            score = meal.get("health_score", 5)
            col_info, col_score, col_del = st.columns([4, 1, 1])
            with col_info:
                st.markdown(f"""
                <div class="meal-row">
                    <div>
                        <div style="font-family:Syne;font-weight:700;color:#E0EDE2;font-size:1.05rem">🍽 {meal.get('meal_name','Repas')}</div>
                        <div style="color:#6B8F72;font-size:0.85rem;margin-top:4px">
                            {meal.get('time','')} &nbsp;•&nbsp;
                            <span class="cal-color">{total.get('calories',0):.0f} kcal</span> &nbsp;•&nbsp;
                            P: {total.get('protein_g',0):.0f}g &nbsp;•&nbsp;
                            G: {total.get('carbs_g',0):.0f}g &nbsp;•&nbsp;
                            L: {total.get('fat_g',0):.0f}g
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
            with col_score:
                st.markdown(f"<div style='padding-top:10px'>{health_score_badge(score)}</div>", unsafe_allow_html=True)
            with col_del:
                if st.button("🗑", key=f"del_today_{i}"):
                    meal_id = meal.get("id")
                    st.session_state.meals = [m for m in st.session_state.meals if m.get("id") != meal_id]
                    st.rerun()

# ─────────────────────────────────────────────
#  PAGE : ANALYSER UN REPAS
# ─────────────────────────────────────────────

elif st.session_state.page == "analyze":
    st.markdown("<h1 style='color:#E0EDE2'>📸 Analyser un repas</h1>", unsafe_allow_html=True)

    col_input, col_result = st.columns(2)

    with col_input:
        st.markdown('<div class="nutri-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='color:#E0EDE2'>Photo ou description</h3>", unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Choisir une photo de repas",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed"
        )

        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, use_container_width=True, caption="Photo sélectionnée")

        st.markdown("<p style='color:#6B8F72;text-align:center;margin:8px 0'>── ou décrivez votre repas ──</p>", unsafe_allow_html=True)

        description = st.text_area(
            "Description",
            placeholder="Ex: 150g de poulet grillé avec 200g de riz basmati et une salade verte",
            height=100,
            label_visibility="collapsed"
        )

        analyze_clicked = st.button("🔍 Analyser avec l'IA", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_result:
        if analyze_clicked:
            if not uploaded_file and not description.strip():
                st.warning("Ajoutez une photo ou une description de votre repas.")
            else:
                with st.spinner("🤖 Analyse en cours..."):
                    try:
                        if uploaded_file:
                            ext = uploaded_file.name.split(".")[-1].lower()
                            mt = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                                  "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                            result = analyze_image(uploaded_file.getvalue(), mt)
                        else:
                            result = analyze_text(description)

                        if result:
                            st.session_state["last_result"] = result
                    except json.JSONDecodeError:
                        st.error("L'IA n'a pas renvoyé un format valide. Réessayez.")
                    except Exception as e:
                        st.error(f"Erreur : {e}")

        result = st.session_state.get("last_result")
        if result:
            total = result.get("total", {})
            score = result.get("health_score", 5)
            confidence = result.get("confidence", 80)

            st.markdown('<div class="nutri-card">', unsafe_allow_html=True)
            st.markdown(f"<h2 style='color:#E0EDE2;margin-bottom:4px'>{result.get('meal_name','Repas')}</h2>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            c1.markdown(f"Confiance : **{confidence}%**")
            c2.markdown(health_score_badge(score), unsafe_allow_html=True)

            st.markdown(f"<div class='metric-big cal-color' style='margin:16px 0'>{total.get('calories',0):.0f} <span style='font-size:1.4rem;color:#6B8F72'>kcal</span></div>", unsafe_allow_html=True)

            # Macros
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("🔵 Protéines", f"{total.get('protein_g',0):.0f}g")
            mc2.metric("🟢 Glucides",  f"{total.get('carbs_g',0):.0f}g")
            mc3.metric("🔴 Lipides",   f"{total.get('fat_g',0):.0f}g")

            st.divider()

            # Foods
            st.markdown("<b style='color:#E0EDE2'>Aliments détectés</b>", unsafe_allow_html=True)
            foods_html = ""
            for food in result.get("foods", []):
                foods_html += f'<span class="food-tag">🍴 {food["name"]} — {food["quantity_g"]}g — {food["calories"]:.0f} kcal</span>'
            st.markdown(foods_html, unsafe_allow_html=True)

            if result.get("notes"):
                st.info(f"💡 {result['notes']}")

            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("💾 Enregistrer ce repas", type="primary", use_container_width=True):
                add_meal(result)
                del st.session_state["last_result"]
                st.success(f"✅ '{result.get('meal_name')}' enregistré !")
                st.balloons()
                st.session_state.page = "dashboard"
                st.rerun()
        else:
            st.markdown('<div class="nutri-card" style="text-align:center;padding:60px 20px"><p style="color:#6B8F72;font-size:1rem">Les résultats<br>apparaîtront ici</p></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  PAGE : HISTORIQUE
# ─────────────────────────────────────────────

elif st.session_state.page == "history":
    st.markdown("<h1 style='color:#E0EDE2'>📋 Historique</h1>", unsafe_allow_html=True)

    all_meals = list(reversed(st.session_state.meals))

    if not all_meals:
        st.markdown('<div class="nutri-card" style="text-align:center;padding:60px"><p style="color:#6B8F72;font-size:1.1rem">Aucun repas enregistré.<br>Commencez par analyser votre premier repas !</p></div>', unsafe_allow_html=True)
    else:
        # Chart calories par jour (7 derniers jours)
        if len(all_meals) >= 2:
            daily = {}
            for meal in all_meals:
                d = meal.get("date", "")
                if d:
                    daily[d] = daily.get(d, 0) + meal.get("total", {}).get("calories", 0)
            dates = sorted(daily.keys())[-14:]
            vals = [daily[d] for d in dates]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=dates, y=vals,
                marker_color="#4ADE80",
                marker_line_width=0,
                hovertemplate="%{y:.0f} kcal<extra></extra>"
            ))
            fig.add_hline(y=st.session_state.goals["calories"],
                          line_dash="dash", line_color="#F0C55A",
                          annotation_text="Objectif", annotation_font_color="#F0C55A")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=16, b=0), height=220,
                xaxis=dict(showgrid=False, color="#6B8F72"),
                yaxis=dict(showgrid=True, gridcolor="#1E2E22", color="#6B8F72"),
                font=dict(family="DM Sans"),
            )
            st.markdown('<div class="nutri-card">', unsafe_allow_html=True)
            st.markdown("<b style='color:#E0EDE2'>Calories par jour</b>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        # Grouper par date
        from collections import defaultdict
        by_date = defaultdict(list)
        for meal in all_meals:
            by_date[meal.get("date", "Inconnu")].append(meal)

        for date_str in sorted(by_date.keys(), reverse=True):
            meals_day = by_date[date_str]
            day_cal = sum(m.get("total", {}).get("calories", 0) for m in meals_day)
            try:
                d = datetime.date.fromisoformat(date_str)
                label = d.strftime("%A %d %B %Y").capitalize()
            except Exception:
                label = date_str

            col_d, col_t = st.columns([3, 1])
            col_d.markdown(f"<h3 style='color:#E0EDE2;margin-bottom:4px'>{label}</h3>", unsafe_allow_html=True)
            col_t.markdown(f"<p style='color:#F0C55A;text-align:right;margin-top:12px'>{day_cal:.0f} kcal</p>", unsafe_allow_html=True)

            for i, meal in enumerate(meals_day):
                total = meal.get("total", {})
                score = meal.get("health_score", 5)
                col_m, col_s, col_del = st.columns([4, 1, 1])
                with col_m:
                    st.markdown(f"""
                    <div class="meal-row">
                        <div>
                            <div style="font-family:Syne;font-weight:700;color:#E0EDE2">🍽 {meal.get('meal_name','Repas')}</div>
                            <div style="color:#6B8F72;font-size:0.82rem;margin-top:3px">
                                {meal.get('time','')} &nbsp;•&nbsp;
                                <span class="cal-color">{total.get('calories',0):.0f} kcal</span> &nbsp;•&nbsp;
                                P:{total.get('protein_g',0):.0f}g G:{total.get('carbs_g',0):.0f}g L:{total.get('fat_g',0):.0f}g
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)
                with col_s:
                    st.markdown(f"<div style='padding-top:10px'>{health_score_badge(score)}</div>", unsafe_allow_html=True)
                with col_del:
                    if st.button("🗑", key=f"del_hist_{date_str}_{i}"):
                        meal_id = meal.get("id")
                        st.session_state.meals = [m for m in st.session_state.meals if m.get("id") != meal_id]
                        st.rerun()

            st.divider()

# ─────────────────────────────────────────────
#  PAGE : PARAMÈTRES
# ─────────────────────────────────────────────

elif st.session_state.page == "settings":
    st.markdown("<h1 style='color:#E0EDE2'>⚙️ Paramètres</h1>", unsafe_allow_html=True)

    # API Key
    st.markdown('<div class="nutri-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='color:#E0EDE2'>🔑 Clé API Anthropic</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6B8F72'>Obtenez votre clé sur <a href='https://console.anthropic.com' target='_blank' style='color:#4ADE80'>console.anthropic.com</a></p>", unsafe_allow_html=True)

    current_key = get_api_key()
    key_display = current_key[:12] + "..." if current_key else ""
    if current_key:
        st.success(f"✅ Clé configurée : `{key_display}`")
    else:
        st.warning("⚠️ Aucune clé API configurée. Ajoutez-la dans `.streamlit/secrets.toml`")

    st.code("""# .streamlit/secrets.toml
ANTHROPIC_API_KEY = "sk-ant-votre-clé-ici"
""", language="toml")
    st.markdown('</div>', unsafe_allow_html=True)

    # Objectifs
    st.markdown('<div class="nutri-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='color:#E0EDE2'>🎯 Objectifs journaliers</h3>", unsafe_allow_html=True)

    g = st.session_state.goals
    c1, c2, c3, c4 = st.columns(4)
    new_cal  = c1.number_input("Calories (kcal)", value=int(g["calories"]),  min_value=500, max_value=5000, step=50)
    new_prot = c2.number_input("Protéines (g)",   value=int(g["protein_g"]), min_value=10,  max_value=400,  step=5)
    new_carb = c3.number_input("Glucides (g)",    value=int(g["carbs_g"]),   min_value=10,  max_value=600,  step=5)
    new_fat  = c4.number_input("Lipides (g)",     value=int(g["fat_g"]),     min_value=10,  max_value=300,  step=5)

    if st.button("💾 Sauvegarder les objectifs", type="primary"):
        st.session_state.goals = {
            "calories": new_cal, "protein_g": new_prot,
            "carbs_g": new_carb, "fat_g": new_fat
        }
        st.success("✅ Objectifs mis à jour !")

    st.markdown('</div>', unsafe_allow_html=True)

    # Données
    st.markdown('<div class="nutri-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='color:#E0EDE2'>💾 Gestion des données</h3>", unsafe_allow_html=True)

    col_e1, col_e2, col_danger = st.columns([1, 1, 2])
    col_e1.download_button("📤 Export JSON", export_json(),
                            file_name="nutriscan_export.json", mime="application/json",
                            use_container_width=True)
    col_e2.download_button("📤 Export CSV", export_csv(),
                            file_name="nutriscan_export.csv", mime="text/csv",
                            use_container_width=True)

    st.markdown("<p style='color:#6B8F72;font-size:0.85rem;margin-top:12px'>Total : <b style='color:#E0EDE2'>{} repas</b> enregistrés</p>".format(len(st.session_state.meals)), unsafe_allow_html=True)

    with col_danger:
        if st.button("🗑 Effacer TOUS les repas", use_container_width=True):
            st.session_state["confirm_clear"] = True

    if st.session_state.get("confirm_clear"):
        st.warning("⚠️ Êtes-vous sûr ? Cette action est irréversible.")
        c_yes, c_no = st.columns(2)
        if c_yes.button("Oui, tout effacer", type="primary"):
            st.session_state.meals = []
            st.session_state["confirm_clear"] = False
            st.success("Données effacées.")
            st.rerun()
        if c_no.button("Annuler"):
            st.session_state["confirm_clear"] = False
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
