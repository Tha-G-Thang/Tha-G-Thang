ADDON_ID = "script.playlistcreator"
CONFIG_FILE = "sets.json"
VIDEO_EXTS = ['.mp4', '.mkv', '.avi', '.mov'] # Bevestigd
# Zorg ervoor dat dit pad correct is ingesteld
PLAYLIST_DIR = "special://profile/playlists/video/" 
STREAM_SETS_FILE = "stream_sets.json" 
PLAYLIST_SETS_FILE = "playlist_sets.json" 

# Lijst van setting_ids die opgeslagen en geladen moeten worden met elke set
FOLDER_SET_SETTINGS = [
    "file_sort_order",
    "folder_sort_order",
    "custom_folder_order",
    "max_files_per_folder",
    "max_files_total",
    "new_to_top",
    "new_to_top_count",
    "exclude_pattern",
    "recursive_scan",
    "file_extensions",
    "min_file_size_mb",
    "scan_timeout_seconds",
    "folder_depth_limit",
    "ignore_empty_folders",
    "show_folder_names", # Oude setting, zal later hernoemd worden
    "show_metadata",
    "metadata_display_mode",
    "metadata_template",
    "use_color_tags", # Oude setting, zal later hernoemd worden
    "color_tag_pos", # Oude setting, zal later hernoemd worden
    "download_path",
    "download_path_adult",
    "enable_auto_clean",
    "show_context_menu_items",
    "enable_ai",
    "ai_title_cleaning",  # Toegevoegd voor AI
    "ai_metadata_enhance", # Toegevoegd voor AI
    "ai_content_grouping", # Toegevoegd voor AI
    "ai_auto_tagging", # Toegevoegd voor AI
    # NIEUWE SETTINGS voor afspeellijst weergave
    "show_folder_names_in_playlist", # Nieuw
    "playlist_folder_name_color", # Nieuw
    "playlist_folder_name_position", # Nieuw
]

# Map om de type van de instellingen te bepalen
# Gebruikt voor het correct parsen van instellingen
SETTING_TYPE_MAP = {
    "file_extensions": "str",
    "recursive_scan": "bool",
    "exclude_pattern": "str",
    "max_files_per_folder": "int",
    "max_files_total": "int",
    "folder_sort_order": "int",
    "custom_folder_order": "str",
    "file_sort_order": "int",
    "new_to_top": "bool",
    "new_to_top_count": "int",
    "min_file_size_mb": "int",
    "scan_timeout_seconds": "int",
    "folder_depth_limit": "int",
    "ignore_empty_folders": "bool",
    "content_filter_mode": "int",
    "adult_content_keywords": "str",
    "show_folder_names": "bool", # Oude setting
    "show_metadata": "bool",
    "metadata_display_mode": "int",
    "metadata_template": "str",
    "use_color_tags": "bool", # Oude setting
    "folder_name_color": "str", # Oude setting, zal later hernoemd worden
    "folder_name_position": "int", # Oude setting, zal later hernoemd worden
    "color_tag_pos": "int", # Oude setting, zal later hernoemd worden
    "download_path": "str",
    "create_streams_subfolder_playlist": "bool",
    "download_path_adult": "str",
    "enable_auto_clean": "bool",
    "show_context_menu_items": "bool",
    "progress_dialog_mode": "int",
    "debug_logging": "bool",
    "log_level": "int",
    "enable_ai": "bool", # AI master schakelaar
    "ai_title_cleaning": "bool",
    "ai_content_grouping": "bool",
    "ai_auto_tagging": "bool",
    "ai_metadata_enhance": "bool",
    "nltk_data_downloaded": "bool", # Om de status van de NLTK download bij te houden
    # NIEUWE SETTINGS voor afspeellijst weergave
    "show_folder_names_in_playlist": "bool",
    "playlist_folder_name_color": "str",
    "playlist_folder_name_position": "int",
}

# Default waardes voor instellingen die niet direct in settings.xml staan, maar wel in SETTING_TYPE_MAP
# Dit zorgt ervoor dat get_setting altijd een fallback heeft.
DEFAULT_SETTINGS = {
    "nltk_data_downloaded": False, # Standaard is NLTK data niet gedownload
    # NIEUWE DEFAULTS
    "show_folder_names_in_playlist": True,
    "playlist_folder_name_color": "green",
    "playlist_folder_name_position": 0, # 0 = Voor, 1 = Achter
}

# Voeg eventuele ontbrekende defaults uit settings.xml toe aan DEFAULT_SETTINGS indien nodig
# Dit wordt afgehandeld door de get_setting functie zelf door zijn 'default' parameter.