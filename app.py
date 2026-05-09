import streamlit as st
import pandas as pd
import random
import os
import json
import re
from difflib import SequenceMatcher
import google.generativeai as genai

st.set_page_config(page_title="Symulator Chemiczny", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# --- STYLE CSS ---
JASNY_CSS = """
<style>
    .stApp { background-color: #F5F7FA; color: #1E293B; }
    h1, h2, h3 { color: #0F172A !important; font-family: 'Segoe UI', sans-serif; }
    .karta-ui { background-color: #FFFFFF; padding: 30px; border-radius: 16px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #E2E8F0; }
    .stButton > button { background-color: #2563EB !important; color: white !important; border-radius: 12px !important; padding: 10px 24px !important; font-weight: 600 !important; border: none !important; transition: all 0.2s; }
    .stButton > button:hover { background-color: #1D4ED8 !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }
    .stTextInput > div > div > input { border-radius: 8px; border: 2px solid #E2E8F0; background-color: #F8FAFC; color: #0F172A; }
    div[data-baseweb="notification"] { border-radius: 12px; }
    .kat-label { color: #64748B; font-size: 13px; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px; text-transform: uppercase; }
</style>
"""

CIEMNY_CSS = """
<style>
    .stApp { background-color: #0A092D; color: #FFFFFF; }
    h1, h2, h3, p, label { color: #FFFFFF !important; font-family: 'Segoe UI', sans-serif; }
    .karta-ui { background-color: #2E3856; padding: 30px; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px; border: 1px solid #3F4A70; }
    .stButton > button { background-color: #4255FF !important; color: white !important; border-radius: 12px !important; padding: 10px 24px !important; font-weight: bold !important; border: none !important; transition: all 0.2s; }
    .stButton > button:hover { background-color: #3B4CE6 !important; box-shadow: 0 0 10px rgba(66, 85, 255, 0.5); }
    [data-testid="stSidebar"] { background-color: #0A092D; border-right: 1px solid #2E3856; }
    .stTextInput > div > div > input { border-radius: 8px; border: 2px solid #3F4A70; background-color: #2E3856; color: #FFFFFF; }
    .stTextInput > div > div > input:focus { border-color: #4255FF; }
    div[data-baseweb="notification"] { background-color: #2E3856; color: white; border: 1px solid #3F4A70; border-radius: 12px; }
    .kat-label { color: #94A3B8; font-size: 13px; font-weight: 700; letter-spacing: 1px; margin-bottom: 5px; text-transform: uppercase; }
</style>
"""

# --- FUNKCJE POMOCNICZE ---
def formatuj_latex(tekst):
    """Magiczny Regex: zamienia zwykłe liczby we wzorach na indeksy dolne (np. H2O -> H_2O)"""
    tekst = str(tekst)
    # Znajduje cyfrę poprzedzoną literą lub nawiasem zamykającym i robi z niej indeks dolny
    tekst_sformatowany = re.sub(r'([a-zA-Z\]\)])(\d+)', r'\1_{\2}', tekst)
    return tekst_sformatowany

def oblicz_podobienstwo(a, b):
    return SequenceMatcher(None, a, b).ratio()

def renderuj_grafike(stan, hex_color, is_dark):
    stan = str(stan).strip().lower()
    hex_color = str(hex_color).strip()
    if not hex_color or hex_color == 'nan': hex_color = '#FFFFFF'
    stroke_kolor = "#939BB4" if is_dark else "#CBD5E1"
    
    # Inteligentne rozpoznawanie stanu (łapie polskie znaki i nowe słowa z Excela)
    if "roztwor" in stan or "roztwór" in stan:
        return f'''<svg width="120" height="180" viewBox="0 0 100 150"><path d="M35 10 L35 120 A 15 15 0 0 0 65 120 L65 10" fill="none" stroke="{stroke_kolor}" stroke-width="4"/><path d="M37 50 L37 120 A 13 13 0 0 0 63 120 L63 50 Z" fill="{hex_color}" opacity="0.9"/><ellipse cx="50" cy="50" rx="13" ry="4" fill="{hex_color}" opacity="1"/><path d="M40 60 L40 100" stroke="white" stroke-width="2" opacity="0.4" stroke-linecap="round"/></svg>'''
    elif "osad" in stan:
        tlo_wody = "#1E293B" if is_dark else "#F1F5F9"
        return f'''<svg width="120" height="180" viewBox="0 0 100 150"><path d="M35 10 L35 120 A 15 15 0 0 0 65 120 L65 10" fill="none" stroke="{stroke_kolor}" stroke-width="4"/><path d="M37 50 L37 120 A 13 13 0 0 0 63 120 L63 50 Z" fill="{tlo_wody}" opacity="0.5"/><path d="M37 95 L37 120 A 13 13 0 0 0 63 120 L63 105 Z" fill="{hex_color}" opacity="0.95"/></svg>'''
    elif "gaz" in stan or "par" in stan:
        return f'''<svg width="120" height="180" viewBox="0 0 100 150"><path d="M40 10 L40 40 L20 120 A 15 15 0 0 0 35 140 L65 140 A 15 15 0 0 0 80 120 L60 40 L60 10 Z" fill="{hex_color}" opacity="0.5" stroke="{stroke_kolor}" stroke-width="3"/><rect x="35" y="5" width="30" height="12" fill="#475569" rx="2"/></svg>'''
    elif "plomien" in stan or "płomień" in stan:
        return f'''<svg width="120" height="180" viewBox="0 0 100 150"><path d="M50 20 Q70 60 70 90 A 20 20 0 0 1 30 90 Q30 60 50 20 Z" fill="{hex_color}" opacity="0.85"/><path d="M50 50 Q60 80 60 100 A 10 10 0 0 1 40 100 Q40 80 50 50 Z" fill="#FFF" opacity="0.5"/></svg>'''
    elif "stale" in stan or "stałe" in stan or "pierwiastek" in stan or "proszek" in stan:
        return f'''<svg width="120" height="180" viewBox="0 0 100 150"><path d="M20 110 Q50 130 80 110" fill="none" stroke="{stroke_kolor}" stroke-width="4" stroke-linecap="round"/><path d="M30 106 Q50 75 70 106 Z" fill="{hex_color}" opacity="0.95"/><circle cx="45" cy="95" r="2" fill="#000" opacity="0.2"/></svg>'''
    return ""

def wczytaj_wagi(plik_json):
    if os.path.exists(plik_json):
        try:
            with open(plik_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def zapisz_wagi(plik_json, slownik_wag):
    with open(plik_json, 'w', encoding='utf-8') as f:
        json.dump(slownik_wag, f, ensure_ascii=False, indent=4)

@st.cache_data
def wczytaj_dane():
    plik_z = "związki.csv" if os.path.exists("związki.csv") else "zwiazki.csv"
    try: 
        df_zwiazki = pd.read_csv(plik_z, sep=";", encoding="utf-8-sig").fillna('')
        # Tarcza ochronna - odrzuca przypadkowe puste wiersze (np. ;;;;;;) z Excela
        df_zwiazki = df_zwiazki[df_zwiazki['Wzor'] != ''] 
    except: 
        df_zwiazki = pd.DataFrame()
    
    try: 
        df_reakcje = pd.read_csv("reakcje.csv", sep=";", encoding="utf-8-sig").fillna('')
        df_reakcje = df_reakcje[df_reakcje['Substrat'] != '']
    except: 
        df_reakcje = pd.DataFrame()
    
    return df_zwiazki, df_reakcje

def przygotuj_pytania_testowe(df_z, df_r, n):
    pytania = []
    for _, row in df_z.iterrows():
        d = row.to_dict()
        d['typ'] = 'zwiazek'
        pytania.append(d)
    for _, row in df_r.iterrows():
        d = row.to_dict()
        d['typ'] = 'reakcja'
        pytania.append(d)
    
    if n > len(pytania): n = len(pytania)
    return random.sample(pytania, n)

# --- GŁÓWNA APLIKACJA ---
def main():
    df_zwiazki, df_reakcje = wczytaj_dane()
    
    st.sidebar.title("🎓 Kurs Chemiczny")
    tryb = st.sidebar.radio("Wybierz moduł:", ["Klasyczne Fiszki", "Tryb Kameleona (Reakcje)", "Test (Egzamin)", "Biblioteka Związków (AI)"])
    st.sidebar.markdown("---")
    motyw = st.sidebar.radio("Motyw wizualny:", ["Ciemny", "Jasny"])
    is_dark = (motyw == "Ciemny")
    st.markdown(CIEMNY_CSS if is_dark else JASNY_CSS, unsafe_allow_html=True)

    if df_zwiazki.empty:
        st.warning("Brak danych! Upewnij się, że plik csv jest poprawny.")
        return

    # === TRYB 1: FISZKI ===
    if tryb == "Klasyczne Fiszki":
        st.title("📚 Klasyczne Fiszki")
        wagi_z = wczytaj_wagi("postepy_zwiazki_web.json")
        df_zwiazki['Waga'] = df_zwiazki['Wzor'].apply(lambda x: wagi_z.get(x, 3))
        
        wszystkie_kategorie = sorted([k for k in df_zwiazki['Kategoria'].unique() if k])
        wybrane_kategorie = st.multiselect("Filtruj kategorie (zostaw puste dla wszystkich):", wszystkie_kategorie)
        df_aktywne = df_zwiazki[df_zwiazki['Kategoria'].isin(wybrane_kategorie)] if wybrane_kategorie else df_zwiazki

        if 'aktualne_pytanie_f' not in st.session_state or st.session_state.get('losuj_nowe_f', False):
            prawdopodobienstwa = df_aktywne['Waga'] ** 3
            st.session_state.aktualne_pytanie_f = df_aktywne.sample(1, weights=prawdopodobienstwa).iloc[0]
            st.session_state.losuj_nowe_f = False; st.session_state.pokaz_wynik_f = False; st.session_state.ost_odpowiedz_f = ""
        if 'combo_f' not in st.session_state: st.session_state.combo_f = 0
            
        pytanie = st.session_state.aktualne_pytanie_f
        wzor_latex = formatuj_latex(pytanie['Wzor'])
        
        st.markdown('<div class="karta-ui">', unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"<div class='kat-label'>📁 Kategoria: {str(pytanie['Kategoria'])}</div>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='margin-top:0px;'>{pytanie['Nazwa']}</h2>", unsafe_allow_html=True)
            st.latex(wzor_latex)
            
            with st.form(key="form_f", clear_on_submit=True):
                odpowiedz_input = st.text_input("Podaj barwę (lub wpisz '?'):").strip().lower()
                if st.form_submit_button("Sprawdź"):
                    st.session_state.ost_odpowiedz_f = odpowiedz_input
                    st.session_state.pokaz_wynik_f = True
                    
            if st.session_state.get('pokaz_wynik_f'):
                odp = st.session_state.ost_odpowiedz_f
                barwa_glowna = str(pytanie['Barwa_glowna']).strip().lower()
                synonimy = [s.strip().lower() for s in str(pytanie['Synonimy']).split(",")] if pytanie['Synonimy'] else []
                aktualna_waga = wagi_z.get(pytanie['Wzor'], 3)
                
                if odp == "?": 
                    st.info(f"💡 Prawidłowa barwa to: **{barwa_glowna.upper()}**")
                    st.session_state.combo_f = 0; wagi_z[pytanie['Wzor']] = aktualna_waga + 2
                elif odp == barwa_glowna or odp in synonimy: 
                    st.success(f"✅ Dobrze! Główna barwa to: **{barwa_glowna.upper()}**")
                    if not st.session_state.get('punkt_f'): st.session_state.combo_f += 1; st.session_state.punkt_f = True
                    wagi_z[pytanie['Wzor']] = 1
                else:
                    dopasowania = [oblicz_podobienstwo(odp, a) for a in [barwa_glowna]+synonimy]
                    if dopasowania and max(dopasowania) >= 0.8:
                        st.warning(f"✅ Zaliczone (literówka). Chodziło Ci o: **{barwa_glowna.upper()}**?")
                        if not st.session_state.get('punkt_f'): st.session_state.combo_f += 1; st.session_state.punkt_f = True
                        wagi_z[pytanie['Wzor']] = 1
                    else:
                        st.error(f"❌ Źle. Prawidłowa barwa to: **{barwa_glowna.upper()}**")
                        st.session_state.combo_f = 0; st.session_state.punkt_f = True
                        wagi_z[pytanie['Wzor']] = aktualna_waga + 2
                
                zapisz_wagi("postepy_zwiazki_web.json", wagi_z)
                if st.button("Następne pytanie", key="btn_next_f"): st.session_state.losuj_nowe_f = True; st.session_state.punkt_f = False; st.rerun()
                    
        with col2:
            st.markdown(f"<div style='text-align:right; font-size:18px; color:#F59E0B; font-weight:bold;'>🔥 Combo: {st.session_state.combo_f}</div>", unsafe_allow_html=True)
            if st.session_state.get('pokaz_wynik_f'):
                st.markdown(f"<div style='text-align:center; margin-top:20px;'>{renderuj_grafike(pytanie['Stan'], pytanie['HEX'], is_dark)}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # === TRYB 2: KAMELEON ===
    elif tryb == "Tryb Kameleona (Reakcje)":
        st.title("🦎 Tryb Kameleona (Reakcje)")
        if df_reakcje.empty: st.warning("Brak pliku reakcje.csv!"); return
        
        wagi_r = wczytaj_wagi("postepy_reakcje_web.json")
        df_reakcje['Waga'] = df_reakcje['Substrat'].apply(lambda x: wagi_r.get(x, 3))
        
        if 'akt_reakcja' not in st.session_state or st.session_state.get('losuj_nowe_r', False):
            prawdopodobienstwa = df_reakcje['Waga'] ** 3
            st.session_state.akt_reakcja = df_reakcje.sample(1, weights=prawdopodobienstwa).iloc[0]
            st.session_state.losuj_nowe_r = False; st.session_state.pokaz_wynik_r = False; st.session_state.ost_odp_r = ""
        if 'combo_r' not in st.session_state: st.session_state.combo_r = 0
        
        reakcja = st.session_state.akt_reakcja
        sub_latex = formatuj_latex(reakcja['Substrat'])
        prod_latex = formatuj_latex(reakcja['Produkt'])
        
        st.markdown('<div class="karta-ui">', unsafe_allow_html=True)
        st.info(f"🧪 **Stan początkowy:** {reakcja['Stan_Substratu']} ${sub_latex}$")
        st.warning(f"⚡ **Działanie:** Dodano {reakcja['Odczynnik']}")
        st.markdown(f"### 🎯 Podaj barwę powstającego produktu: **${prod_latex}$**")
        
        with st.form(key="form_r", clear_on_submit=True):
            odp_r = st.text_input("Twoja odpowiedź (lub '?'):").strip().lower()
            if st.form_submit_button("Rozwiąż reakcję"):
                st.session_state.ost_odp_r = odp_r
                st.session_state.pokaz_wynik_r = True
                
        if st.session_state.get('pokaz_wynik_r'):
            odp = st.session_state.ost_odp_r
            b_glowna = str(reakcja['Barwa_Produktu']).strip().lower()
            syn = [s.strip().lower() for s in str(reakcja['Synonimy']).split(",")] if reakcja['Synonimy'] else []
            akt_waga = wagi_r.get(reakcja['Substrat'], 3)
            
            if odp == "?":
                st.info(f"💡 Prawidłowa barwa produktu to **{b_glowna}**.")
                st.session_state.combo_r = 0; st.session_state.punkt_r = True
                wagi_r[reakcja['Substrat']] = akt_waga + 2
            elif odp == b_glowna or odp in syn: 
                st.success(f"✅ Świetnie! Produkt ${prod_latex}$ jest **{b_glowna}**.")
                if not st.session_state.get('punkt_r'): st.session_state.combo_r += 1; st.session_state.punkt_r = True
                wagi_r[reakcja['Substrat']] = 1
            else: 
                st.error(f"❌ Niestety. Prawidłowa barwa produktu ${prod_latex}$ to **{b_glowna}**.")
                st.session_state.combo_r = 0; st.session_state.punkt_r = True
                wagi_r[reakcja['Substrat']] = akt_waga + 2
                
            zapisz_wagi("postepy_reakcje_web.json", wagi_r)
            if st.button("Nowa reakcja"): st.session_state.losuj_nowe_r = True; st.session_state.punkt_r = False; st.rerun()
            
        st.markdown(f"<div style='text-align:right; font-size:18px; color:#F59E0B; font-weight:bold;'>🔥 Combo: {st.session_state.combo_r}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # === TRYB 3: TEST (EGZAMIN) ===
    elif tryb == "Test (Egzamin)":
        st.title("📝 Test Sprawdzający")
        
        if 'test_active' not in st.session_state: st.session_state.test_active = False
        if 'test_finished' not in st.session_state: st.session_state.test_finished = False

        if not st.session_state.test_active and not st.session_state.test_finished:
            st.markdown('<div class="karta-ui">', unsafe_allow_html=True)
            st.markdown("Sprawdź swoją wiedzę w warunkach przypominających maturę. Program wylosuje miks związków i reakcji.")
            ile_zadan = st.slider("Wybierz liczbę zadań:", min_value=5, max_value=30, value=15, step=1)
            
            if st.button("Rozpocznij Test", type="primary"):
                st.session_state.test_questions = przygotuj_pytania_testowe(df_zwiazki, df_reakcje, ile_zadan)
                st.session_state.test_active = True
                st.session_state.test_finished = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
                
        elif st.session_state.test_active:
            st.markdown(f"**Rozwiązujesz test:** {len(st.session_state.test_questions)} zadań.")
            
            with st.form("test_form"):
                ans_dict = {}
                for i, q in enumerate(st.session_state.test_questions):
                    st.markdown('<div class="karta-ui" style="padding: 20px; margin-bottom: 15px;">', unsafe_allow_html=True)
                    if q['typ'] == 'zwiazek':
                        q_latex = formatuj_latex(q['Wzor'])
                        st.markdown(f"<h4 style='margin-bottom: 5px;'>Zadanie {i+1}</h4>", unsafe_allow_html=True)
                        st.markdown(f"Podaj barwę dla: **{q['Nazwa']}** (${q_latex}$)")
                    else:
                        sub_latex = formatuj_latex(q['Substrat'])
                        prod_latex = formatuj_latex(q['Produkt'])
                        st.markdown(f"<h4 style='margin-bottom: 5px;'>Zadanie {i+1}</h4>", unsafe_allow_html=True)
                        st.markdown(f"Mamy {q['Stan_Substratu']} ${sub_latex}$. Dodano {q['Odczynnik']}.")
                        st.markdown(f"Podaj barwę produktu: **${prod_latex}$**")
                        
                    # Label_visibility="collapsed" chowa napis nad inputem by było schludniej
                    ans_dict[i] = st.text_input("Odpowiedź:", key=f"t_ans_{i}", label_visibility="collapsed", placeholder="Wpisz barwę...").strip().lower()
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                if st.form_submit_button("Zakończ Test i Oceń", type="primary"):
                    st.session_state.test_answers = [ans_dict[i] for i in range(len(st.session_state.test_questions))]
                    st.session_state.test_active = False
                    st.session_state.test_finished = True
                    st.rerun()
                    
        elif st.session_state.test_finished:
            st.markdown('<div class="karta-ui">', unsafe_allow_html=True)
            wynik = 0
            bledy = []
            
            for i, (q, ans) in enumerate(zip(st.session_state.test_questions, st.session_state.test_answers)):
                if q['typ'] == 'zwiazek':
                    bg = str(q['Barwa_glowna']).strip().lower()
                    syn = [s.strip().lower() for s in str(q['Synonimy']).split(",")] if q['Synonimy'] else []
                    q_latex = formatuj_latex(q['Wzor'])
                    tytul = f"{q['Nazwa']} (${q_latex}$)"
                    hex_color = q.get('HEX', '#ccc')
                else:
                    bg = str(q['Barwa_Produktu']).strip().lower()
                    syn = [s.strip().lower() for s in str(q['Synonimy']).split(",")] if q['Synonimy'] else []
                    sub_latex = formatuj_latex(q['Substrat'])
                    prod_latex = formatuj_latex(q['Produkt'])
                    tytul = f"Produkt: ${prod_latex}$ (od ${sub_latex}$)"
                    hex_color = "#ccc" # Domyślnie brak dla reakcji w starym csv
                    
                akceptowane = [bg] + syn
                dopasowania = [oblicz_podobienstwo(ans, a) for a in akceptowane]
                
                if ans == bg or ans in syn or (dopasowania and max(dopasowania) >= 0.8):
                    wynik += 1
                else:
                    bledy.append({'tytul': tytul, 'twoja': ans, 'poprawna': bg, 'hex': hex_color})

            max_pkt = len(st.session_state.test_questions)
            procent = round((wynik / max_pkt) * 100)
            
            ocena = 1
            if procent >= 30: ocena = 2
            if procent >= 50: ocena = 3
            if procent >= 75: ocena = 4
            if procent >= 90: ocena = 5
            if procent == 100: ocena = 6
            
            st.header(f"Wynik: {wynik}/{max_pkt} ({procent}%)")
            st.subheader(f"Ocena: {ocena}")
            
            if bledy:
                st.error("❌ Twoje błędy do poprawy:")
                for b in bledy:
                    color_box = f"<span style='display:inline-block; width:14px; height:14px; background-color:{b['hex']}; border-radius:3px; margin-right:5px; vertical-align:middle; border:1px solid #777;'></span>"
                    st.markdown(f"- **{b['tytul']}** | Twoja odp: `{b['twoja']}` ➡️ Poprawna: {color_box} **{b['poprawna']}**", unsafe_allow_html=True)
            else:
                st.success("🏆 PERFEKCJA! Jesteś gotowy na maturę z kolorów!")
                
            if st.button("Rozwiąż nowy test", type="primary"):
                st.session_state.test_finished = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # === TRYB 4: AI ===
    elif tryb == "Biblioteka Związków (AI)":
        st.title("🧠 Biblioteka i AI Korepetytor")
        st.sidebar.markdown("---")
        klucz_api = st.sidebar.text_input("🔑 Wklej klucz Gemini API:", type="password")
        lista_nazw = [n for n in df_zwiazki['Nazwa'].tolist() if n]
        wybrany_zwiazek = st.selectbox("Wyszukaj związek z bazy:", lista_nazw)
        dane_zwiazku = df_zwiazki[df_zwiazki['Nazwa'] == wybrany_zwiazek].iloc[0]
        
        wzor_latex = formatuj_latex(dane_zwiazku['Wzor'])
        
        st.markdown('<div class="karta-ui">', unsafe_allow_html=True)
        col_info, col_img = st.columns([3, 1])
        with col_info:
            st.markdown(f"<div class='kat-label'>📁 Kategoria: {dane_zwiazku['Kategoria']}</div>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='margin-top:0px;'>{dane_zwiazku['Nazwa']}</h2>", unsafe_allow_html=True)
            st.latex(wzor_latex)
            st.markdown(f"**Barwa:** {dane_zwiazku['Barwa_glowna']}<br>**Stan:** {dane_zwiazku['Stan']}", unsafe_allow_html=True)
        with col_img:
            st.markdown(f"<div style='text-align:center;'>{renderuj_grafike(dane_zwiazku['Stan'], dane_zwiazku['HEX'], is_dark)}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown("### 🤖 Zapytaj AI")
        if klucz_api:
            genai.configure(api_key=klucz_api)
            model = genai.GenerativeModel('gemini-pro')
            with st.form(key="ai_form"):
                pytanie_ucznia = st.text_area("O co zapytać AI?")
                if st.form_submit_button("Wyślij") and pytanie_ucznia:
                    with st.spinner("AI analizuje..."):
                        try:
                            st.info(model.generate_content(f"Jako ekspert krótko odpowiedz na pytanie ucznia dotyczące {dane_zwiazku['Nazwa']} ({dane_zwiazku['Wzor']}). Pytanie: {pytanie_ucznia}").text)
                        except Exception as e: st.error(f"Błąd API: {e}")
        else:
            st.info("💡 Wklej klucz API w bocznym panelu, aby rozmawiać z korepetytorem AI.")

if __name__ == "__main__":
    main()
