<div align="center">
  <img src="spotify_logo.png" alt="SpotifyTools" width="360">
  <h1>SpotifyTools</h1>
  <p>A lightweight desktop app for browsing Spotify playlists and giving every track a genuinely random position.</p>

  [![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Spotify Web API](https://img.shields.io/badge/Spotify-Web_API-1DB954?logo=spotify&logoColor=white)](https://developer.spotify.com/documentation/web-api)
</div>

> [!IMPORTANT]
> SpotifyTools changes the saved order of tracks when you use **Shuffle playlist order**. It does not merely change playback order. The app always asks for confirmation first.

## What it does

- Signs in through Spotify OAuth—credentials are read from environment variables and are never stored in source code.
- Loads all of your playlists, including paginated results.
- Displays every available track and artist in the selected playlist.
- Randomizes the complete playlist instead of shuffling isolated groups of 100 tracks.
- Updates playlists of any size using Spotify's 100-item request limit.
- Caches fetched tracks during the session and performs network calls outside the UI thread.

## Requirements

- Python 3.10 or newer
- A Spotify account
- A Spotify developer application with a client ID and client secret

## Setup

1. Clone the repository and enter its directory:

   ```bash
   git clone https://github.com/laxmanmudigonda/Spotify.git
   cd Spotify
   ```

2. Create and activate a virtual environment:

   **Windows PowerShell**

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS / Linux**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard). Add this redirect URI to the app settings exactly as shown:

   ```text
   http://127.0.0.1:8888/callback
   ```

5. Set your credentials for the current terminal session:

   **Windows PowerShell**

   ```powershell
   $env:SPOTIPY_CLIENT_ID = "your-client-id"
   $env:SPOTIPY_CLIENT_SECRET = "your-client-secret"
   $env:SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
   ```

   **macOS / Linux**

   ```bash
   export SPOTIPY_CLIENT_ID="your-client-id"
   export SPOTIPY_CLIENT_SECRET="your-client-secret"
   export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8888/callback"
   ```

6. Start the app:

   ```bash
   python project.py
   ```

## How to use it

1. Select **Log in with Spotify** and approve the requested playlist permissions in your browser.
2. Open **View playlists** and double-click a playlist (or select it and use **Open selected**).
3. Review its tracks, then select **Shuffle playlist order**.
4. Confirm the change. The new order is written back to Spotify.

Only playlist read and playlist modification scopes are requested. OAuth tokens are cached locally by Spotipy in `.cache`, which is excluded from Git. Logging out deletes the cached token from the machine.

## Development

Run the automated tests without opening the GUI:

```bash
pytest -q
```

The test suite covers credential encoding, deterministic shuffle behavior, Spotify-sized batching, and API pagination.

## Project structure

```text
Spotify/
├── project.py          # Tkinter application and Spotify integration
├── test_project.py     # Unit tests for core behavior
├── requirements.txt    # Runtime and test dependencies
├── spotify_logo.png    # Login and README artwork
└── logout_icon.png     # Legacy artwork retained from the original UI
```

## Roadmap

- Optional sorting and filtering without modifying a playlist
- Playlist snapshots or undo support before a shuffle
- Improved accessibility and keyboard navigation
- Packaging as a standalone desktop executable

## Disclaimer

This is an independent educational project and is not affiliated with, endorsed by, or sponsored by Spotify. Spotify and its marks belong to their respective owners.
