# Define a dictionary for 'Normal' profile settings
NORMAL_PROFILE_SETTINGS = {
    # File Selection
    'enable_max_size': 'false',
    'scan_depth': '0', # Unlimited
    'enable_date_filter': 'false',

    # Playlist Ordering
    'custom_folder_order': '', # No custom order
    'newest_files_per_folder_to_top_count': '0',

    # Context Menu Integration
    'context_menu_adult': 'false',

    # Advanced Settings (all false/default for Normal)
    'enable_backups': 'false',
    'show_scan_progress': 'true',
    'debug_logging': 'false',

    # Download Settings
    'download_regex_enable': 'false',
    'download_cleanup_adult_toggle': 'false',
    'download_regex_enable_adult': 'false',
    # Ensure other non-regex download settings are set to their normal defaults if they were modified by 'pro' defaults.
}

# Define a dictionary for 'Pro' profile settings
PRO_PROFILE_SETTINGS = {
    # File Selection
    'enable_max_size': 'false', # Default to false, but visible
    'scan_depth': '0', # Default to unlimited, but visible
    'enable_date_filter': 'false', # Default to false, but visible

    # Playlist Ordering
    'custom_folder_order': '', # Default to empty, but visible
    'newest_files_per_folder_to_top_count': '0', # Default to 0, but visible

    # Context Menu Integration
    'context_menu_adult': 'false', # Default to false, but visible

    # Advanced Settings (all false/default for Pro, but visible)
    'enable_backups': 'false',
    'show_scan_progress': 'true',
    'debug_logging': 'false',

    # Download Settings
    'download_regex_enable': 'false', # Default to false, but visible
    'download_cleanup_adult_toggle': 'false', # Default to false, but visible
    'download_regex_enable_adult': 'false', # Default to false, but visible
    # Ensure other non-regex download settings are set to their pro defaults if any.
}