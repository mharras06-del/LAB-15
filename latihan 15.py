import os
import math
import json
import html
import numpy as np
import pandas as pd
import streamlit as st
import folium

from folium.plugins import Draw
from streamlit_folium import st_folium

try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Sistem Maklumat Geomatik",
    page_icon="🗺️",
    layout="wide"
)

st.markdown("""
<style>

.user-badge {
    background-color: #E53935;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    text-align: center;
    font-weight: bold;
    margin-bottom: 15px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# PATH LOGO
# ============================================================

DIR_SEMASA = (
    os.path.dirname(os.path.abspath(__file__))
    if "__file__" in globals()
    else os.getcwd()
)

LALUAN_LOGO = os.path.join(
    DIR_SEMASA,
    "Poli_Logo1-1024x599.png"
)


# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = "harraz"


# ============================================================
# FUNGSI KIRAAN GEOMATIK
# ============================================================

def kira_kira_geomatik(df, col_e, col_n, col_stn):

    e1 = pd.to_numeric(
        df[col_e],
        errors="coerce"
    ).values

    n1 = pd.to_numeric(
        df[col_n],
        errors="coerce"
    ).values

    e2 = np.roll(e1, -1)
    n2 = np.roll(n1, -1)

    de = e2 - e1
    dn = n2 - n1

    # --------------------------------------------------------
    # JARAK
    # --------------------------------------------------------

    jarak = np.sqrt(
        de ** 2 +
        dn ** 2
    )

    # --------------------------------------------------------
    # BEARING
    # --------------------------------------------------------

    bearings_deg = (
        np.degrees(
            np.arctan2(
                de,
                dn
            )
        ) % 360
    )

    bearing_dms = []

    for b in bearings_deg:

        deg = int(b)

        min_val = int(
            (b - deg) * 60
        )

        sec_val = round(
            (
                ((b - deg) * 60)
                - min_val
            ) * 60,
            1
        )

        if sec_val >= 60:
            sec_val = 0
            min_val += 1

        if min_val >= 60:
            min_val = 0
            deg = (deg + 1) % 360

        bearing_dms.append(
            f'{deg}° {min_val:02d}\' {sec_val:04.1f}"'
        )

    # --------------------------------------------------------
    # LUAS
    # --------------------------------------------------------

    luas_m2 = 0.5 * abs(
        np.sum(
            e1 * n2 -
            e2 * n1
        )
    )

    luas_hektar = (
        luas_m2 / 10000
    )

    luas_ekar = (
        luas_m2 / 4046.8564224
    )

    # --------------------------------------------------------
    # STATION
    # --------------------------------------------------------

    stn_from = list(
        df[col_stn]
    )

    stn_to = (
        list(
            df[col_stn].iloc[1:]
        )
        +
        [df[col_stn].iloc[0]]
    )

    # --------------------------------------------------------
    # HASIL
    # --------------------------------------------------------

    df_hasil = pd.DataFrame({

        "Dari STN":
            stn_from,

        "Ke STN":
            stn_to,

        "Jarak (m)":
            np.round(
                jarak,
                3
            ),

        'Bearing (° \' ")':
            bearing_dms,

        "Bearing (Perpuluhan °)":
            np.round(
                bearings_deg,
                4
            ),

        "Mid_E":
            (e1 + e2) / 2,

        "Mid_N":
            (n1 + n2) / 2
    })

    return (
        df_hasil,
        luas_m2,
        luas_hektar,
        luas_ekar
    )


# ============================================================
# GEOJSON
# ============================================================

def jana_geojson(
    df,
    col_e,
    col_n,
    no_lot,
    nama_pemilik
):

    coords = []

    for _, row in df.iterrows():

        coords.append([
            float(row[col_e]),
            float(row[col_n])
        ])

    if coords:
        coords.append(coords[0])

    data = {

        "type":
            "FeatureCollection",

        "features": [

            {
                "type":
                    "Feature",

                "properties": {

                    "No_Lot":
                        no_lot,

                    "Pemilik":
                        nama_pemilik
                },

                "geometry": {

                    "type":
                        "Polygon",

                    "coordinates":
                        [coords]
                }
            }
        ]
    }

    return json.dumps(
        data,
        indent=4
    )


# ============================================================
# DXF
# ============================================================

def jana_dxf(
    df,
    col_e,
    col_n,
    col_stn,
    df_hasil,
    no_lot,
    luas_m2
):

    lines = [
        "0",
        "SECTION",
        "2",
        "ENTITIES"
    ]

    # --------------------------------------------------------
    # POLYGON
    # --------------------------------------------------------

    lines.extend([
        "0",
        "LWPOLYLINE",
        "8",
        "SEMPADAN_LOT",
        "90",
        str(len(df)),
        "70",
        "1"
    ])

    for _, row in df.iterrows():

        lines.extend([
            "10",
            str(row[col_e]),
            "20",
            str(row[col_n])
        ])

    # --------------------------------------------------------
    # STATION
    # --------------------------------------------------------

    for _, row in df.iterrows():

        lines.extend([
            "0",
            "TEXT",
            "8",
            "STESEN",
            "10",
            str(row[col_e]),
            "20",
            str(row[col_n]),
            "40",
            "1.5",
            "1",
            f"STN {row[col_stn]}"
        ])

    # --------------------------------------------------------
    # BEARING + JARAK
    # --------------------------------------------------------

    for _, row in df_hasil.iterrows():

        bearing = str(
            row['Bearing (° \' ")']
        )

        jarak = float(
            row["Jarak (m)"]
        )

        lines.extend([
            "0",
            "TEXT",
            "8",
            "BEARING_JARAK",
            "10",
            str(row["Mid_E"]),
            "20",
            str(row["Mid_N"]),
            "40",
            "1.0",
            "1",
            f"{bearing}    {jarak:.3f}m"
        ])

    # --------------------------------------------------------
    # LOT
    # --------------------------------------------------------

    center_e = (
        df[col_e]
        .astype(float)
        .mean()
    )

    center_n = (
        df[col_n]
        .astype(float)
        .mean()
    )

    lines.extend([
        "0",
        "TEXT",
        "8",
        "LABEL_LOT",
        "10",
        str(center_e),
        "20",
        str(center_n),
        "40",
        "2.0",
        "1",
        f"{no_lot} ({luas_m2:,.2f} m2)"
    ])

    lines.extend([
        "0",
        "ENDSEC",
        "0",
        "EOF"
    ])

    return "\n".join(lines)


# ============================================================
# KIRA SUDUT TEKS
# ============================================================

def kira_sudut_teks(
    lon1,
    lat1,
    lon2,
    lat2
):

    mean_lat = (
        lat1 + lat2
    ) / 2

    dx = (
        lon2 - lon1
    ) * math.cos(
        math.radians(
            mean_lat
        )
    )

    dy = (
        lat2 - lat1
    )

    if (
        abs(dx) < 1e-12
        and
        abs(dy) < 1e-12
    ):
        return 0

    angle = math.degrees(
        math.atan2(
            -dy,
            dx
        )
    )

    # Elak tulisan terbalik
    if angle > 90:
        angle -= 180

    if angle < -90:
        angle += 180

    return angle


# ============================================================
# BEARING LUAR + JARAK DALAM
# ============================================================

def tambah_label_bearing_jarak(
    m,
    lons,
    lats,
    df_hasil,
    saiz_bearing=7,
    saiz_jarak=7
):

    # --------------------------------------------------------
    # CENTER POLYGON
    # --------------------------------------------------------

    center_lon = float(
        np.mean(lons)
    )

    center_lat = float(
        np.mean(lats)
    )

    # --------------------------------------------------------
    # OFFSET
    #
    # Bearing = luar garisan
    # Jarak   = dalam garisan
    # --------------------------------------------------------

    bearing_offset_m = 2.5
    jarak_offset_m = 2.5

    # --------------------------------------------------------
    # LOOP SETIAP GARISAN
    # --------------------------------------------------------

    for i, row in df_hasil.iterrows():

        # ====================================================
        # TITIK MULA
        # ====================================================

        lon1 = float(
            lons[i]
        )

        lat1 = float(
            lats[i]
        )

        # ====================================================
        # TITIK AKHIR
        # ====================================================

        next_i = (
            (i + 1)
            % len(lons)
        )

        lon2 = float(
            lons[next_i]
        )

        lat2 = float(
            lats[next_i]
        )

        # ====================================================
        # TITIK TENGAH
        # ====================================================

        mid_lon = (
            lon1 + lon2
        ) / 2

        mid_lat = (
            lat1 + lat2
        ) / 2

        # ====================================================
        # SUDUT GARISAN
        # ====================================================

        mean_lat = (
            lat1 + lat2
        ) / 2

        dx = (
            lon2 - lon1
        ) * math.cos(
            math.radians(
                mean_lat
            )
        )

        dy = (
            lat2 - lat1
        )

        panjang = math.sqrt(
            dx ** 2 +
            dy ** 2
        )

        if panjang == 0:
            continue

        angle = kira_sudut_teks(
            lon1,
            lat1,
            lon2,
            lat2
        )

        # ====================================================
        # NORMAL KE SISI KIRI GARISAN
        # ====================================================

        nx = -dy / panjang
        ny = dx / panjang

        # ====================================================
        # TENTUKAN NORMAL YANG MENUJU KE DALAM LOT
        # ====================================================

        vector_center_x = (
            (
                center_lon -
                mid_lon
            )
            * math.cos(
                math.radians(
                    mid_lat
                )
            )
        )

        vector_center_y = (
            center_lat -
            mid_lat
        )

        dot = (
            nx *
            vector_center_x
            +
            ny *
            vector_center_y
        )

        if dot > 0:

            # normal = DALAM
            inside_nx = nx
            inside_ny = ny

        else:

            # songsangkan normal
            inside_nx = -nx
            inside_ny = -ny

        # ====================================================
        # CONVERSION METER -> DEGREE
        # ====================================================

        meter_per_degree_lat = 111320

        meter_per_degree_lon = (
            111320 *
            math.cos(
                math.radians(
                    mid_lat
                )
            )
        )

        if abs(
            meter_per_degree_lon
        ) < 1e-12:

            meter_per_degree_lon = 111320

        # ====================================================
        # BEARING POSITION
        # LUAR GARISAN
        # ====================================================

        bearing_lon = (
            mid_lon
            -
            (
                inside_nx *
                bearing_offset_m /
                meter_per_degree_lon
            )
        )

        bearing_lat = (
            mid_lat
            -
            (
                inside_ny *
                bearing_offset_m /
                meter_per_degree_lat
            )
        )

        # ====================================================
        # JARAK POSITION
        # DALAM GARISAN
        # ====================================================

        jarak_lon = (
            mid_lon
            +
            (
                inside_nx *
                jarak_offset_m /
                meter_per_degree_lon
            )
        )

        jarak_lat = (
            mid_lat
            +
            (
                inside_ny *
                jarak_offset_m /
                meter_per_degree_lat
            )
        )

        # ====================================================
        # NILAI BEARING
        # ====================================================

        bearing_value = str(
            row['Bearing (° \' ")']
        )

        # ====================================================
        # NILAI JARAK
        # ====================================================

        jarak_value = float(
            row["Jarak (m)"]
        )

        # ====================================================
        # LABEL BEARING
        # LUAR GARISAN
        # ====================================================

        bearing_html = f"""
        <div style="
            transform:
                translate(-50%, -50%)
                rotate({angle:.2f}deg);

            transform-origin:
                center center;

            white-space:
                nowrap;

            font-family:
                Arial, sans-serif;

            font-size:
                {saiz_bearing}px;

            font-weight:
                normal;

            line-height:
                1;

            color:
                yellow;

            text-shadow:
                -1px -1px 0 black,
                 1px -1px 0 black,
                -1px  1px 0 black,
                 1px  1px 0 black;

            pointer-events:
                none;
        ">
            {html.escape(
                bearing_value
            )}
        </div>
        """

        folium.Marker(

            location=[
                bearing_lat,
                bearing_lon
            ],

            icon=folium.DivIcon(

                html=bearing_html,

                icon_size=(
                    1,
                    1
                ),

                icon_anchor=(
                    0,
                    0
                )
            ),

            tooltip=(
                f"Bearing: "
                f"{bearing_value}"
            )

        ).add_to(m)

        # ====================================================
        # LABEL JARAK
        # DALAM GARISAN
        # ====================================================

        jarak_html = f"""
        <div style="
            transform:
                translate(-50%, -50%)
                rotate({angle:.2f}deg);

            transform-origin:
                center center;

            white-space:
                nowrap;

            font-family:
                Arial, sans-serif;

            font-size:
                {saiz_jarak}px;

            font-weight:
                normal;

            line-height:
                1;

            color:
                yellow;

            text-shadow:
                -1px -1px 0 black,
                 1px -1px 0 black,
                -1px  1px 0 black,
                 1px  1px 0 black;

            pointer-events:
                none;
        ">
            {jarak_value:.3f}m
        </div>
        """

        folium.Marker(

            location=[
                jarak_lat,
                jarak_lon
            ],

            icon=folium.DivIcon(

                html=jarak_html,

                icon_size=(
                    1,
                    1
                ),

                icon_anchor=(
                    0,
                    0
                )
            ),

            tooltip=(
                f"Jarak: "
                f"{jarak_value:.3f} m"
            )

        ).add_to(m)


# ============================================================
# LOGIN
# ============================================================

if not st.session_state.logged_in:

    st.write(
        "<br><br>",
        unsafe_allow_html=True
    )

    if os.path.exists(
        LALUAN_LOGO
    ):

        st.image(
            LALUAN_LOGO,
            width=250
        )

    st.subheader(
        "🔒 Log Masuk Pengguna"
    )

    username = st.text_input(
        "Nama Pengguna",
        value="harraz"
    )

    password = st.text_input(
        "Kata Laluan",
        type="password"
    )

    if st.button(
        "Log Masuk"
    ):

        if (
            username != ""
            and
            password == "12345"
        ):

            st.session_state.logged_in = True
            st.session_state.username = username

            st.rerun()

        else:

            st.error(
                "Nama pengguna atau kata laluan salah."
            )


# ============================================================
# SISTEM UTAMA
# ============================================================

else:

    # ========================================================
    # SIDEBAR
    # ========================================================

    with st.sidebar:

        if os.path.exists(
            LALUAN_LOGO
        ):

            st.image(
                LALUAN_LOGO,
                use_container_width=True
            )

        else:

            st.title(
                "POLITEKNIK"
            )

        st.markdown(
            f"""
            <div class="user-badge">
                👤 {st.session_state.username}
            </div>
            """,
            unsafe_allow_html=True
        )

        # ----------------------------------------------------
        # NO LOT
        # ----------------------------------------------------

        st.caption(
            "No. Lot"
        )

        no_lot = st.text_input(
            "No. Lot Label",
            value="Lot 308",
            label_visibility="collapsed"
        )

        # ----------------------------------------------------
        # PEMILIK
        # ----------------------------------------------------

        st.caption(
            "Nama Pemilik"
        )

        nama_pemilik = st.text_input(
            "Nama Pemilik Label",
            value="Ali Bin Abu",
            label_visibility="collapsed"
        )

        # ----------------------------------------------------
        # SAIZ STN / LOT
        # ----------------------------------------------------

        saiz_tulisan = st.slider(
            "Saiz Tulisan STN / Lot",
            min_value=7,
            max_value=16,
            value=9
        )

        # ----------------------------------------------------
        # SATELLITE
        # ----------------------------------------------------

        st.markdown(
            "<b>🛰️ Kawalan Layer Satelit:</b>",
            unsafe_allow_html=True
        )

        papar_satelit = st.checkbox(
            "📷 Satellite Image",
            value=True
        )

        # ----------------------------------------------------
        # PAPARAN
        # ----------------------------------------------------

        st.markdown(
            "<br><b>👁️ Kawalan Paparan:</b>",
            unsafe_allow_html=True
        )

        papar_bearing_jarak = st.checkbox(
            "Bearing & Jarak",
            value=True
        )

        papar_lot_luas = st.checkbox(
            "No. Lot & Luas",
            value=True
        )

        papar_sempadan = st.checkbox(
            "Sempadan",
            value=True
        )

        papar_batu_sempadan = st.checkbox(
            "Batu Sempadan",
            value=True
        )

        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

        st.markdown(
            "---"
        )

        uploaded_file = st.file_uploader(
            "📂 Upload CSV",
            type=["csv"]
        )

        st.markdown(
            "---"
        )

        # ----------------------------------------------------
        # LOGOUT
        # ----------------------------------------------------

        if st.button(
            "🚪 Log Keluar",
            use_container_width=True
        ):

            st.session_state.logged_in = False

            st.rerun()


    # ========================================================
    # TAJUK
    # ========================================================

    st.subheader(
        "🌐 Sistem Maklumat Geomatik & Kadaster"
    )


    # ========================================================
    # CSV BELUM UPLOAD
    # ========================================================

    if uploaded_file is None:

        st.info(
            "Sila muat naik fail CSV "
            "di sidebar."
        )


    # ========================================================
    # CSV SUDAH UPLOAD
    # ========================================================

    else:

        try:

            # ==================================================
            # BACA CSV
            # ==================================================

            df = pd.read_csv(
                uploaded_file
            )

            senarai_kolom = list(
                df.columns
            )


            # ==================================================
            # TETAPAN KOORDINAT
            # ==================================================

            st.markdown(
                "---"
            )

            st.markdown(
                "## Tetapan Koordinat & Peta"
            )

            col_x, col_y, col_stn = (
                st.columns(3)
            )


            # --------------------------------------------------
            # EASTING
            # --------------------------------------------------

            with col_x:

                idx_e = (
                    senarai_kolom.index("E")
                    if "E" in senarai_kolom
                    else 0
                )

                sel_e = st.selectbox(
                    "Easting",
                    senarai_kolom,
                    index=idx_e
                )


            # --------------------------------------------------
            # NORTHING
            # --------------------------------------------------

            with col_y:

                idx_n = (
                    senarai_kolom.index("N")
                    if "N" in senarai_kolom
                    else (
                        1
                        if len(
                            senarai_kolom
                        ) > 1
                        else 0
                    )
                )

                sel_n = st.selectbox(
                    "Northing",
                    senarai_kolom,
                    index=idx_n
                )


            # --------------------------------------------------
            # STATION
            # --------------------------------------------------

            with col_stn:

                idx_stn = (
                    senarai_kolom.index("STN")
                    if "STN" in senarai_kolom
                    else 0
                )

                sel_stn = st.selectbox(
                    "ID Stesen",
                    senarai_kolom,
                    index=idx_stn
                )


            # ==================================================
            # LOT / CRS / BASEMAP
            # ==================================================

            col_lot, col_crs, col_map = (
                st.columns(3)
            )


            with col_lot:

                lot_name_input = st.text_input(
                    "No. Lot",
                    value="308"
                )


            with col_crs:

                crs_type = st.selectbox(
                    "CRS",
                    [
                        "Cassini-Soldner (EPSG:4390)",
                        "WGS 84 (EPSG:4326)",
                        "Custom EPSG"
                    ],
                    index=0
                )


            with col_map:

                pilihan_basemap = st.selectbox(
                    "Basemap",
                    [
                        "🗺️ OpenStreetMap",
                        "🌙 CartoDB Dark",
                        "⚪ White Background"
                    ]
                )


            # ==================================================
            # EPSG
            # ==================================================

            if "WGS 84" in crs_type:

                epsg_val = 4326

            elif "Cassini-Soldner" in crs_type:

                epsg_val = 4390

            else:

                epsg_val = st.number_input(
                    "EPSG Code",
                    value=4390,
                    step=1
                )


            # ==================================================
            # KIRAAN
            # ==================================================

            (
                df_hasil,
                luas_m2,
                luas_hektar,
                luas_ekar
            ) = kira_kira_geomatik(
                df,
                sel_e,
                sel_n,
                sel_stn
            )


            # ==================================================
            # HASIL LUAS
            # ==================================================

            st.markdown(
                "---"
            )

            st.write(
                "### 📐 Hasil Analisis Luas"
            )

            c1, c2, c3 = (
                st.columns(3)
            )

            c1.metric(
                "Luas",
                f"{luas_m2:,.3f} m²"
            )

            c2.metric(
                "Hektar",
                f"{luas_hektar:,.4f} ha"
            )

            c3.metric(
                "Ekar",
                f"{luas_ekar:,.4f}"
            )


            # ==================================================
            # JADUAL
            # ==================================================

            st.markdown(
                "---"
            )

            c_left, c_right = (
                st.columns(2)
            )

            with c_left:

                st.write(
                    "### 📋 Koordinat"
                )

                st.dataframe(
                    df,
                    use_container_width=True
                )

            with c_right:

                st.write(
                    "### 📏 Bearing & Jarak"
                )

                st.dataframe(
                    df_hasil[
                        [
                            "Dari STN",
                            "Ke STN",
                            "Jarak (m)",
                            'Bearing (° \' ")'
                        ]
                    ],
                    use_container_width=True
                )


            # ==================================================
            # EXPORT
            # ==================================================

            st.markdown(
                "---"
            )

            geojson_str = jana_geojson(
                df,
                sel_e,
                sel_n,
                lot_name_input,
                nama_pemilik
            )

            dxf_str = jana_dxf(
                df,
                sel_e,
                sel_n,
                sel_stn,
                df_hasil,
                lot_name_input,
                luas_m2
            )

            col_exp1, col_exp2 = (
                st.columns(2)
            )

            with col_exp1:

                st.download_button(
                    "📄 Export GeoJSON",
                    data=geojson_str,
                    file_name=(
                        f"{lot_name_input}.geojson"
                    ),
                    mime="application/json",
                    use_container_width=True
                )

            with col_exp2:

                st.download_button(
                    "📐 Export DXF",
                    data=dxf_str,
                    file_name=(
                        f"{lot_name_input}.dxf"
                    ),
                    mime="application/dxf",
                    use_container_width=True
                )


            # ==================================================
            # KOORDINAT
            # ==================================================

            e_vals = (
                df[sel_e]
                .astype(float)
                .values
            )

            n_vals = (
                df[sel_n]
                .astype(float)
                .values
            )


            # ==================================================
            # CONVERT CRS
            # ==================================================

            if (
                HAS_PYPROJ
                and
                epsg_val != 4326
            ):

                try:

                    transformer = (
                        Transformer.from_crs(
                            f"EPSG:{epsg_val}",
                            "EPSG:4326",
                            always_xy=True
                        )
                    )

                    lons, lats = (
                        transformer.transform(
                            e_vals,
                            n_vals
                        )
                    )

                except Exception:

                    lons = e_vals
                    lats = n_vals

            else:

                lons = e_vals
                lats = n_vals


            # ==================================================
            # CENTER
            # ==================================================

            center_lat = float(
                np.mean(lats)
            )

            center_lon = float(
                np.mean(lons)
            )


            # ==================================================
            # TABS
            # ==================================================

            tab_peta, tab_data = (
                st.tabs([
                    "🗺️ Peta Utama",
                    "✏️ Lukisan Interaktif"
                ])
            )


            # ==================================================
            # PETA UTAMA
            # ==================================================

            with tab_peta:

                m = folium.Map(

                    location=[
                        center_lat,
                        center_lon
                    ],

                    zoom_start=18,

                    control_scale=True
                )


                # =================================================
                # BASEMAP
                # =================================================

                if "OpenStreetMap" in (
                    pilihan_basemap
                ):

                    folium.TileLayer(
                        "OpenStreetMap",
                        name="OpenStreetMap"
                    ).add_to(m)

                elif "CartoDB Dark" in (
                    pilihan_basemap
                ):

                    folium.TileLayer(
                        "CartoDB dark_matter",
                        name="CartoDB Dark"
                    ).add_to(m)


                # =================================================
                # SATELLITE
                # =================================================

                if papar_satelit:

                    folium.TileLayer(

                        tiles=(
                            "https://server.arcgisonline.com/"
                            "ArcGIS/rest/services/"
                            "World_Imagery/"
                            "MapServer/tile/{z}/{y}/{x}"
                        ),

                        attr=(
                            "Esri World Imagery"
                        ),

                        name="Satellite",

                        overlay=True,

                        control=True

                    ).add_to(m)


                # =================================================
                # POLYGON
                # =================================================

                points = [

                    [
                        float(lats[i]),
                        float(lons[i])
                    ]

                    for i in range(
                        len(lons)
                    )
                ]

                if points:
                    points.append(
                        points[0]
                    )


                if papar_sempadan:

                    folium.Polygon(

                        locations=points,

                        color="yellow",

                        weight=4,

                        fill=True,

                        fill_color="red",

                        fill_opacity=0.35,

                        popup=(
                            f"Lot "
                            f"{lot_name_input}"
                        )

                    ).add_to(m)


                # =================================================
                # STATION / BATU SEMPADAN
                # =================================================

                if papar_batu_sempadan:

                    for i in range(
                        len(lons)
                    ):

                        # -----------------------------------------
                        # BULATAN STATION
                        # -----------------------------------------

                        folium.CircleMarker(

                            location=[
                                float(lats[i]),
                                float(lons[i])
                            ],

                            radius=6,

                            color="red",

                            fill=True,

                            fill_color="red",

                            fill_opacity=1,

                            tooltip=(
                                f"STN "
                                f"{df.iloc[i][sel_stn]}"
                            )

                        ).add_to(m)


                        # -----------------------------------------
                        # LABEL STN
                        # -----------------------------------------

                        folium.Marker(

                            location=[
                                float(lats[i]),
                                float(lons[i])
                            ],

                            icon=folium.DivIcon(

                                html=f"""
                                <div style="
                                    transform:
                                    translate(-50%, -160%);

                                    color:white;

                                    font-size:
                                    {saiz_tulisan}px;

                                    font-weight:bold;

                                    white-space:
                                    nowrap;

                                    text-shadow:
                                    -1px -1px 0 #000,
                                     1px -1px 0 #000,
                                    -1px  1px 0 #000,
                                     1px  1px 0 #000;
                                ">
                                    STN {html.escape(
                                        str(
                                            df.iloc[i][sel_stn]
                                        )
                                    )}
                                </div>
                                """

                            )

                        ).add_to(m)


                # =================================================
                # BEARING + JARAK
                #
                # BEARING:
                #   - LUAR GARISAN
                #   - TENGAH GARISAN
                #   - SELARI DENGAN GARISAN
                #
                # JARAK:
                #   - DALAM GARISAN
                #   - TENGAH GARISAN
                #   - SELARI DENGAN GARISAN
                # =================================================

                if papar_bearing_jarak:

                    tambah_label_bearing_jarak(

                        m,

                        lons,

                        lats,

                        df_hasil,

                        saiz_bearing=7,

                        saiz_jarak=7
                    )


                # =================================================
                # LOT + LUAS
                # =================================================

                if papar_lot_luas:

                    lot_text = (
                        f"<b>Lot "
                        f"{html.escape(
                            str(
                                lot_name_input
                            )
                        )}</b>"
                        f"<br>"
                        f"{html.escape(
                            str(
                                nama_pemilik
                            )
                        )}"
                        f"<br>"
                        f"<b>"
                        f"{luas_m2:,.2f} m²"
                        f"</b>"
                    )

                    folium.Marker(

                        location=[
                            center_lat,
                            center_lon
                        ],

                        icon=folium.DivIcon(

                            html=f"""
                            <div style="
                                transform:
                                translate(-50%, -50%);

                                color:#00FFFF;

                                font-size:
                                {saiz_tulisan + 2}px;

                                font-weight:bold;

                                text-align:center;

                                white-space:nowrap;

                                text-shadow:
                                -1px -1px 0 #000,
                                 1px -1px 0 #000,
                                -1px  1px 0 #000,
                                 1px  1px 0 #000;
                            ">
                                {lot_text}
                            </div>
                            """

                        )

                    ).add_to(m)


                # =================================================
                # LAYER CONTROL
                # =================================================

                folium.LayerControl(
                    position="topright"
                ).add_to(m)


                # =================================================
                # PAPAR PETA
                # =================================================

                st_folium(

                    m,

                    width="100%",

                    height=720,

                    returned_objects=[]
                )


            # ==================================================
            # LUKISAN INTERAKTIF
            # ==================================================

            with tab_data:

                st.write(
                    "### ✏️ Lukisan Interaktif"
                )

                st.caption(
                    "Gunakan alat di sebelah kiri "
                    "peta untuk melukis poligon, "
                    "garisan atau marker."
                )


                m2 = folium.Map(

                    location=[
                        center_lat,
                        center_lon
                    ],

                    zoom_start=18
                )


                # ------------------------------------------------
                # SATELLITE
                # ------------------------------------------------

                if papar_satelit:

                    folium.TileLayer(

                        tiles=(
                            "https://server.arcgisonline.com/"
                            "ArcGIS/rest/services/"
                            "World_Imagery/"
                            "MapServer/tile/{z}/{y}/{x}"
                        ),

                        attr="Esri",

                        name="Satellite",

                        overlay=False,

                        control=True

                    ).add_to(m2)


                # ------------------------------------------------
                # POLYGON
                # ------------------------------------------------

                if points:

                    folium.Polygon(

                        locations=points,

                        color="yellow",

                        weight=4,

                        fill=True,

                        fill_color="red",

                        fill_opacity=0.35

                    ).add_to(m2)


                # ------------------------------------------------
                # DRAW TOOL
                # ------------------------------------------------

                draw = Draw(

                    export=True,

                    filename=(
                        "lukisan_geomatik.geojson"
                    ),

                    position="topleft",

                    draw_options={

                        "polyline": True,

                        "polygon": True,

                        "rectangle": True,

                        "circle": False,

                        "marker": True,

                        "circlemarker": False
                    },

                    edit_options={

                        "poly": {

                            "allowIntersection":
                                False
                        }
                    }
                )

                draw.add_to(
                    m2
                )


                # ------------------------------------------------
                # PAPAR
                # ------------------------------------------------

                output_lukisan = st_folium(

                    m2,

                    width="100%",

                    height=650,

                    key="folium_draw_map"
                )


                # ------------------------------------------------
                # GEOJSON
                # ------------------------------------------------

                if (
                    output_lukisan
                    and
                    output_lukisan.get(
                        "all_drawings"
                    )
                ):

                    st.write(
                        "### 📌 GeoJSON"
                    )

                    st.json(
                        output_lukisan[
                            "all_drawings"
                        ]
                    )


        except Exception as e:

            st.error(
                f"Ralat semasa membaca/"
                f"memproses fail: {e}"
            )

