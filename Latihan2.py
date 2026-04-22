import streamlit as st
import pandas as pd
import numpy as np
import math
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Polygon
import pyproj

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Survey Lot - PUO", layout="wide")

# --- CUSTOM CSS UNTUK BACKGROUND DOODLE GEOMATIK ---
st.markdown("""
    <style>
    .stApp {
        background-image: url("https://www.transparenttextures.com/patterns/cubes.png");
        background-color: #f4f7f6;
    }
    
    .login-bg {
        background-image: url("https://img.freepik.com/free-vector/geology-doodle-set-study-earth-composition-structure_107791-10323.jpg"); 
        background-size: cover;
        background-blend-mode: overlay;
        opacity: 0.1;
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        z-index: -1;
    }

    .stTextInput>div>div>input { border-radius: 10px; }
    .stButton>button { border-radius: 10px; transition: 0.3s; }
    .profile-card:hover { transform: scale(1.02); transition: 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# --- PENGURUSAN LOG MASUK ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def logout():
    st.session_state['logged_in'] = False
    st.rerun()

# --- MUKA DEPAN ---
if not st.session_state['logged_in']:
    st.markdown('<div class="login-bg"></div>', unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.5, 1])
    
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><img src='https://cdn-icons-png.flaticon.com/512/1862/1862654.png' width='80'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #2c3e50;'>🔐 Sistem Survey Lot PUO</h1>", unsafe_allow_html=True)
        
        with st.container(border=True):
            user_id = st.text_input("👤 Masukkan ID:", placeholder="ID Pengguna")
            password = st.text_input("🔑 Masukkan Kata Laluan:", type="password", placeholder="Kata Laluan")
            
            if st.button("🚀 Log Masuk", use_container_width=True):
                if user_id.lower() == "aisyahnajmi" and password == "admin123":
                    st.session_state['logged_in'] = True
                    st.session_state['user_display'] = "AISYAH NAJMI"
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan salah!")

# --- TAMBAHAN: PAPARAN LUPA KATA LALUAN ---
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True) # Jarak sedikit
            
            # Menggunakan st.button dengan gaya 'secondary' atau 'ghost' untuk nampak macam pautan
            if st.button("❓ Lupa Kata Laluan?", use_container_width=True):
                st.info("Sila hubungi pentadbir sistem atau pensyarah kursus untuk set semula kata laluan anda.")                    

# --- SISTEM UTAMA ---
else:
    with st.sidebar:
        st.markdown(f"""
            <div class="profile-card" style="background: linear-gradient(135deg, #00b4ff, #0047ff); padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px;">
                <img src="https://cdn-icons-png.flaticon.com/512/6997/6997662.png" width="80" style="margin-bottom:10px; border-radius: 50%; background: white; padding: 5px;">
                <h3 style="margin:0;">Hai, AISYAH!</h3>
                <p style="font-size: 0.9rem; opacity: 0.8;">{st.session_state.get('user_display', 'USER')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        saiz_stn = st.slider("Saiz Marker Stesen", 10, 40, 22)
        saiz_teks = st.slider("Saiz Bearing/Jarak", 6, 16, 12)
        # Tahap zoom awal saya set ke 20 supaya nampak besar terus bila load
        tahap_zoom = st.slider("Tahap Zoom Awal", 10, 25, 20)
        warna_lot = st.color_picker("Warna Poligon", "#FFFF00")
        export_container = st.empty()
        if st.button("🚪 Log Keluar", use_container_width=True): logout()

    # --- HEADER ---
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        try: st.image("logo_poli.png", width=130)
        except: st.error("Logo tiada")
    with col_title:
        st.markdown("<h1>SISTEM SURVEY LOT</h1><p>Politeknik Ungku Omar</p>", unsafe_allow_html=True)

    st.divider()

    def kira_sudut_visual(e1, n1, e2, n2):
        de, dn = e2 - e1, n2 - n1
        angle_survey = math.degrees(math.atan2(de, dn)) % 360
        angle_rad = math.atan2(dn, de)
        angle_deg = -math.degrees(angle_rad) 
        if angle_deg > 90: angle_deg -= 180
        elif angle_deg < -90: angle_deg += 180
        d = int(angle_survey); m = int((angle_survey - d) * 60); s = int((((angle_survey - d) * 60) - m) * 60)
        return f"{d}°{m:02d}'{s:02d}\"", angle_deg

    def tukar_ke_wgs84(x, y, epsg_asal):
        try:
            transformer = pyproj.Transformer.from_crs(f"EPSG:{epsg_asal}", "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(x, y)
            return lat, lon
        except: return None, None

    # --- INPUT ---
    with st.container(border=True):
        col_in1, col_in2 = st.columns(2)
        with col_in1: epsg_input = st.text_input("🌍 Kod EPSG:", value="4390")
        with col_in2: uploaded_file = st.file_uploader("📂 Muat naik fail CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if all(col in df.columns for col in ['STN', 'E', 'N']):
            x, y, stns = df['E'].values, df['N'].values, df['STN'].values
            lats, lons = tukar_ke_wgs84(x, y, epsg_input)
            
            # --- PENGIRAAN GEOMETRI LOT ---
            poly_geom = Polygon(zip(x, y))
            luas_lot = poly_geom.area
            perimeter_lot = poly_geom.length
            surveyor_name = "AISYAH" 

            # Create Map - max_zoom diset ke 25 untuk "zoom in besar gila"
            m = folium.Map(location=[np.mean(lats), np.mean(lons)], zoom_start=tahap_zoom, max_zoom=25, tiles=None)
            
            # --- TAMBAH BASE LAYERS DENGAN SETTING OVER-ZOOM ---
            # max_native_zoom memastikan peta tak hilang bila zoom terlalu dekat
            folium.TileLayer(
                'openstreetmap', 
                name='OpenStreetMap (Peta Jalan)',
                max_native_zoom=19,
                max_zoom=25
            ).add_to(m)
            
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                attr='Google', 
                name='Google Hybrid (Satelit)',
                max_native_zoom=20,
                max_zoom=25
            ).add_to(m)

            # --- TAMBAH DATA SURVEY (Checkbox Overlay) ---
            fg = folium.FeatureGroup(name="Data Survey", overlay=True, control=True)

            # --- POPUP INFO LOT ---
            popup_lot_content = f"""
            <div style="font-family: 'Arial', sans-serif; padding: 5px; min-width: 180px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">
                    <span style="font-size: 20px;">📍</span>
                    <span style="font-size: 18px; color: #1a73e8; font-weight: bold;">Info Lot</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <tr><td style="padding: 2px 0;"><b>Surveyor:</b></td><td style="padding: 2px 0;">{surveyor_name}</td></tr>
                    <tr><td style="padding: 2px 0;"><b>Luas:</b></td><td style="padding: 2px 0;">{luas_lot:,.3f} m²</td></tr>
                    <tr><td style="padding: 2px 0;"><b>Perimeter:</b></td><td style="padding: 2px 0;">{perimeter_lot:,.3f} m</td></tr>
                </table>
            </div>
            """

            # Poligon Lot
            folium.Polygon(
                locations=list(zip(lats, lons)), 
                color=warna_lot, 
                fill=True, 
                fill_opacity=0.3,
                popup=folium.Popup(popup_lot_content, max_width=300)
            ).add_to(fg)

            for i in range(len(lats)):
                # Popup Stesen
                popup_stn_html = f"""
                <div style="font-family: 'Arial', sans-serif; min-width: 120px;">
                    <b style="font-size: 14px; color: red;">STESEN {stns[i]}</b><hr style="margin:5px 0;">
                    <b>E:</b> {x[i]:.3f}<br><b>N:</b> {y[i]:.3f}
                </div>
                """
                # Marker Stesen
                folium.Marker(
                    [lats[i], lons[i]],
                    popup=folium.Popup(popup_stn_html, max_width=200),
                    icon=folium.DivIcon(html=f"""
                        <div style="background-color: red; color: white; border-radius: 50%; width: {saiz_stn}px; height: {saiz_stn}px; 
                        display: flex; align-items: center; justify-content: center; font-size: {saiz_stn/2.5}pt; font-weight: bold; 
                        border: 2px solid white; box-shadow: 2px 2px 4px black;">{stns[i]}</div>""")
                ).add_to(fg)

                # Bering & Jarak
                next_i = (i + 1) % len(lats)
                mid_lat, mid_lon = (lats[i] + lats[next_i])/2, (lons[i] + lons[next_i])/2
                bering_txt, rot = kira_sudut_visual(x[i], y[i], x[next_i], y[next_i])
                dist = math.sqrt((x[next_i]-x[i])**2 + (y[next_i]-y[i])**2)
                folium.Marker([mid_lat, mid_lon], icon=folium.DivIcon(html=f"""
                    <div style="transform: rotate({rot}deg); width: 150px; margin-left: -75px; text-align: center;">
                        <div style="color: #00FF00; font-size: {saiz_teks}pt; font-weight: bold; text-shadow: 1px 1px black;">{bering_txt}</div>
                        <div style="color: #FFFF00; font-size: {saiz_teks}pt; font-weight: bold; text-shadow: 1px 1px black;">{dist:.3f}m</div>
                    </div>""")).add_to(fg)

            fg.add_to(m)
            folium.LayerControl(position='topright', collapsed=False).add_to(m)

            # --- PROSES PENYEDIAAN DATA UNTUK EKSPORT (QGIS FRIENDLY) ---
            # 1. Bina senarai garisan antara stesen
            lines = []
            bearings = []
            distances = []
            line_names = []

            for i in range(len(x)):
                next_i = (i + 1) % len(x)
                # Cipta geometri garisan
                from shapely.geometry import LineString
                line_geom = LineString([(x[i], y[i]), (x[next_i], y[next_i])])
                lines.append(line_geom)
                
                # Kira data bering dan jarak untuk atribut
                b_txt, _ = kira_sudut_visual(x[i], y[i], x[next_i], y[next_i])
                d_val = math.sqrt((x[next_i]-x[i])**2 + (y[next_i]-y[i])**2)
                
                line_names.append(f"STN {stns[i]} - {stns[next_i]}")
                bearings.append(b_txt)
                distances.append(round(d_val, 3))

            # 2. Tukar kepada GeoDataFrame (LineString)
            gdf_lines = gpd.GeoDataFrame({
                'Label': line_names,
                'Bering': bearings,
                'Jarak': distances
            }, geometry=lines, crs=f"EPSG:{epsg_input}")

            # 3. Butang Download yang telah dikemaskini
            export_container.download_button(
                label="🚀 Export Lot & Data ke QGIS (.geojson)",
                data=gdf_lines.to_json().encode('utf-8'),
                file_name="lot_survey_lengkap.geojson",
                mime="application/json",
                use_container_width=True
            )

            # --- PAPAR MAP ---
            st_folium(m, width="100%", height=700, returned_objects=[])

            # --- BAHAGIAN TAMBAHAN: JADUAL DATA SURVEY ---
            st.markdown("### 📊 Jadual Data Ukuran Lot")
            
            # Bina senarai data untuk jadual
            data_jadual = []
            for i in range(len(stns)):
                next_i = (i + 1) % len(stns)
                
                # Ambil bering dan jarak yang telah dikira sebelum ini
                b_txt, _ = kira_sudut_visual(x[i], y[i], x[next_i], y[next_i])
                d_val = math.sqrt((x[next_i]-x[i])**2 + (y[next_i]-y[i])**2)
                
                data_jadual.append({
                    "Dari Stesen": stns[i],
                    "Ke Stesen": stns[next_i],
                    "Bering": b_txt,
                    "Jarak (m)": f"{d_val:.3f}"
                })

            # Tukar senarai ke DataFrame untuk paparan Streamlit
            df_display = pd.DataFrame(data_jadual)
            
            # Paparkan jadual
            st.table(df_display) 
            
            # --- INFO TAMBAHAN BAWAH JADUAL ---
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.info(f"📐 **Jumlah Perimeter:** {perimeter_lot:.3f} m")
            with col_info2:
                st.success(f"🌍 **Luas Lot:** {luas_lot:.3f} m²")

            # Butang Export asal (Dikekalkan)
            gdf = gpd.GeoDataFrame({'STN': stns, 'E': x, 'N': y}, geometry=gpd.points_from_xy(x, y), crs=f"EPSG:{epsg_input}")
            export_container.download_button("🚀 Export (.geojson)", data=gdf.to_json().encode('utf-8'), file_name="survey.geojson", use_container_width=True)

            