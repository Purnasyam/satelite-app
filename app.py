"""Satellite Imagery Web Application — main Streamlit entry point."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure src/ is on Python path for imports
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
from streamlit_folium import st_folium

from satellite_app.downloads.export import ExportService
from satellite_app.map.drawing_tools import (
    calculate_geometry_stats,
    export_geometry_geojson,
    parse_draw_output,
)
from satellite_app.map.folium_map import MapManager
from satellite_app.services.ee_auth import verify_ee_connection
from satellite_app.services.ee_imagery import ImageryService
from satellite_app.services.geocoding import GeocodingService
from satellite_app.ui.components import (
    render_auth_panel,
    render_download_buttons,
    render_imagery_controls,
    render_search_panel,
    render_statistics_panel,
)
from satellite_app.ui.theme import apply_custom_css, init_session_state
from satellite_app.utils.logging_config import setup_logging

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Satellite Imagery Explorer",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

setup_logging()
init_session_state()


def _load_streamlit_secrets() -> None:
    """Load Earth Engine credentials from Streamlit secrets (cloud deployment)."""
    import os

    try:
        if hasattr(st, "secrets") and st.secrets:
            for key in (
                "EE_PROJECT",
                "EE_SERVICE_ACCOUNT",
                "EE_PRIVATE_KEY_PATH",
                "EE_PRIVATE_KEY_DATA",
                "GOOGLE_CLOUD_PROJECT",
            ):
                if key in st.secrets:
                    os.environ[key] = str(st.secrets[key])
            from satellite_app.config.settings import get_settings

            get_settings.cache_clear()
    except Exception:
        pass


_load_streamlit_secrets()


def main() -> None:
    """Run the Satellite Imagery Web Application."""
    dark_mode = st.sidebar.toggle("Dark mode", value=st.session_state.dark_mode)
    st.session_state.dark_mode = dark_mode
    apply_custom_css(dark_mode)

    st.markdown(
        """
        <div class="app-header">
            <h1 style="margin:0;">🛰️ Satellite Imagery Explorer</h1>
            <p style="margin:0.5rem 0 0 0; opacity:0.8;">
                Explore Sentinel-2 & Landsat imagery powered by Google Earth Engine
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.title("Controls")
        connected = render_auth_panel()

        if not connected:
            st.stop()

        geocoder = GeocodingService()
        render_search_panel(geocoder)

        st.divider()
        imagery_params = render_imagery_controls()

        basemap = st.selectbox(
            "Basemap",
            ["Satellite", "Terrain", "OpenStreetMap"],
            index=["Satellite", "Terrain", "OpenStreetMap"].index(
                st.session_state.basemap
            ),
        )
        st.session_state.basemap = basemap

        load_imagery = st.button(
            "Load Imagery",
            type="primary",
            use_container_width=True,
        )

        st.divider()
        st.subheader("Time Series")

        compare_mode = st.checkbox("Compare two dates", value=False)
        before_date = st.date_input(
            "Before date",
            value=date.today() - timedelta(days=180),
            disabled=not compare_mode,
        )
        after_date = st.date_input(
            "After date",
            value=date.today() - timedelta(days=30),
            disabled=not compare_mode,
        )

        timelapse = st.checkbox("Enable time-lapse", value=False)
        max_frames = st.slider("Max frames", 3, 20, 8, disabled=not timelapse)

    # Services
    imagery_service = ImageryService()
    export_service = ExportService()

    center = tuple(st.session_state.map_center)
    zoom = st.session_state.map_zoom
    map_manager = MapManager(center=center, zoom=zoom, basemap=basemap)

    # Load imagery onto map
    current_image = None
    vis_params = None
    region = None
    stats: dict = {}

    if load_imagery:
        with st.spinner("Loading satellite imagery from Earth Engine..."):
            try:
                bounds_region = _get_map_region(center, zoom)
                mosaic = imagery_service.get_mosaic(
                    source=imagery_params["source"],
                    start_date=imagery_params["start_date"],
                    end_date=imagery_params["end_date"],
                    cloud_cover=imagery_params["cloud_cover"],
                    region=bounds_region,
                )
                display_image, vis_params = imagery_service.prepare_visualization(
                    mosaic,
                    imagery_params["source"],
                    imagery_params["viz_mode"],
                )
                map_manager.add_ee_layer(
                    display_image,
                    vis_params,
                    name=f"{imagery_params['source']} - {imagery_params['viz_mode']}",
                )
                st.session_state.current_image = display_image
                st.session_state.vis_params = vis_params
                st.session_state.imagery_source = imagery_params["source"]
                st.success("Imagery loaded successfully!")
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Failed to load imagery: {exc}")

    # Before/after comparison slider
    if compare_mode and st.session_state.get("ee_connected"):
        _render_before_after(
            imagery_service,
            map_manager,
            imagery_params,
            before_date,
            after_date,
        )

    # Main map layout
    map_col, stats_col = st.columns([3, 1])

    with map_col:
        st.subheader("Interactive Map")
        map_data = st_folium(
            map_manager.get_map(),
            width=None,
            height=600,
            returned_objects=["last_active_drawing", "all_drawings", "bounds", "zoom"],
            key="main_map",
        )

        if map_data:
            if map_data.get("bounds"):
                b = map_data["bounds"]
                st.session_state.last_bounds = b
            if map_data.get("zoom"):
                st.session_state.map_zoom = map_data["zoom"]

        # Process drawn geometry
        drawn = None
        if map_data and map_data.get("last_active_drawing"):
            drawn = parse_draw_output(map_data["last_active_drawing"])
        elif map_data and map_data.get("all_drawings"):
            drawings = map_data["all_drawings"]
            if drawings:
                drawn = parse_draw_output(drawings[-1])

        if drawn:
            st.session_state.drawn_geometry = drawn["geometry"]
            geom_stats = calculate_geometry_stats(drawn["geometry"])
            st.info(f"Selected area: **{geom_stats['area_formatted']}**")

            geojson_str = export_geometry_geojson(drawn["geometry"])
            st.download_button(
                "Export Geometry (GeoJSON)",
                data=geojson_str,
                file_name="selected_geometry.geojson",
                mime="application/geo+json",
            )

            if st.session_state.get("current_image"):
                try:
                    import ee

                    region = ee.Geometry(drawn["geometry"])
                    stats = imagery_service.compute_statistics(
                        st.session_state.current_image,
                        region,
                        st.session_state.get("imagery_source", "Sentinel-2"),
                    )
                except Exception as exc:
                    st.warning(f"Could not compute statistics: {exc}")

    with stats_col:
        render_statistics_panel(stats)
        if st.session_state.get("current_image") and st.session_state.get("drawn_geometry"):
            import ee

            region = ee.Geometry(st.session_state.drawn_geometry)
            render_download_buttons(
                export_service,
                st.session_state.current_image,
                st.session_state.vis_params,
                region,
                st.session_state.get("imagery_source", "Sentinel-2"),
                imagery_params["viz_mode"],
            )

    # Time-lapse
    if timelapse:
        _render_timelapse(
            imagery_service,
            export_service,
            imagery_params,
            center,
            zoom,
            max_frames,
        )

    # Image preview
    if st.session_state.get("current_image") and st.session_state.get("vis_params"):
        _render_preview(
            export_service,
            st.session_state.current_image,
            st.session_state.vis_params,
            center,
            zoom,
        )


def _get_map_region(center: tuple[float, float], zoom: int):
    """Approximate map bounds as EE geometry from center and zoom."""
    import ee

    lat, lon = center
    # Rough degrees per zoom level
    delta = 360 / (2 ** (zoom + 1))
    return ee.Geometry.Rectangle([
        lon - delta,
        lat - delta,
        lon + delta,
        lat + delta,
    ])


def _render_before_after(
    imagery_service: ImageryService,
    map_manager: MapManager,
    params: dict,
    before: date,
    after: date,
) -> None:
    """Render before/after comparison with slider."""
    import ee

    st.subheader("Before / After Comparison")
    slider_val = st.slider("Swipe between Before (0) and After (100)", 0, 100, 50)

    try:
        with st.spinner("Loading comparison images..."):
            region = _get_map_region(
                tuple(st.session_state.map_center),
                st.session_state.map_zoom,
            )
            before_img = imagery_service.get_image_for_date(
                params["source"], before, params["cloud_cover"], region
            )
            after_img = imagery_service.get_image_for_date(
                params["source"], after, params["cloud_cover"], region
            )
            before_vis = imagery_service.prepare_visualization(
                before_img, params["source"], params["viz_mode"]
            )[1]
            after_vis = imagery_service.prepare_visualization(
                after_img, params["source"], params["viz_mode"]
            )[1]

        col_before, col_after = st.columns(2)
        export_svc = ExportService()

        if slider_val <= 50:
            with col_before:
                st.caption(f"Before: {before}")
                url = export_svc.get_thumbnail_url(before_img, before_vis, region, 512)
                st.image(url, use_container_width=True)
            with col_after:
                st.caption(f"After: {after} (preview)")
                url = export_svc.get_thumbnail_url(after_img, after_vis, region, 512)
                st.image(url, use_container_width=True, opacity=slider_val / 100)
        else:
            with col_before:
                st.caption(f"Before: {before} (preview)")
                url = export_svc.get_thumbnail_url(before_img, before_vis, region, 512)
                st.image(url, use_container_width=True, opacity=(100 - slider_val) / 100)
            with col_after:
                st.caption(f"After: {after}")
                url = export_svc.get_thumbnail_url(after_img, after_vis, region, 512)
                st.image(url, use_container_width=True)

    except Exception as exc:
        st.error(f"Comparison failed: {exc}")


def _render_timelapse(
    imagery_service: ImageryService,
    export_service: ExportService,
    params: dict,
    center: tuple[float, float],
    zoom: int,
    max_frames: int,
) -> None:
    """Generate and display time-lapse animation."""
    st.subheader("Time-Lapse Animation")

    if st.button("Generate Time-Lapse", use_container_width=True):
        with st.spinner("Building time-lapse frames..."):
            try:
                import ee

                region = _get_map_region(center, zoom)
                dates = imagery_service.get_time_series_dates(
                    params["source"],
                    params["start_date"],
                    params["end_date"],
                    params["cloud_cover"],
                    region,
                    max_frames,
                )
                if len(dates) < 2:
                    st.warning("Not enough images for time-lapse. Expand date range.")
                    return

                urls = []
                for d in dates:
                    img = imagery_service.get_image_for_date(
                        params["source"],
                        date.fromisoformat(d),
                        params["cloud_cover"],
                        region,
                    )
                    _, vis = imagery_service.prepare_visualization(
                        img, params["source"], params["viz_mode"]
                    )
                    urls.append(export_service.get_thumbnail_url(img, vis, region, 512))

                gif_data = export_service.create_timelapse_gif(urls)
                st.image(gif_data, caption=f"Time-lapse: {len(dates)} frames")
                st.download_button(
                    "Download GIF",
                    data=gif_data,
                    file_name="timelapse.gif",
                    mime="image/gif",
                )
            except Exception as exc:
                st.error(f"Time-lapse failed: {exc}")


def _render_preview(
    export_service: ExportService,
    image,
    vis_params: dict,
    center: tuple[float, float],
    zoom: int,
) -> None:
    """Show image preview thumbnail."""
    st.subheader("Image Preview")
    try:
        region = _get_map_region(center, zoom)
        url = export_service.get_thumbnail_url(image, vis_params, region, 768)
        st.image(url, caption="Current visualization preview", use_container_width=True)
    except Exception as exc:
        st.warning(f"Preview unavailable: {exc}")


if __name__ == "__main__":
    main()
