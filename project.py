"""SpotifyTools desktop application.

Browse the current user's playlists and permanently randomize a playlist's
track order through the Spotify Web API.
"""

from __future__ import annotations

import base64
import os
import random
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Iterable

from cachetools import LRUCache
from PIL import Image, ImageTk
from spotipy import Spotify, SpotifyException
from spotipy.oauth2 import SpotifyOAuth


APP_NAME = "SpotifyTools"
APP_DIR = Path(__file__).resolve().parent
SCOPES = "playlist-read-private playlist-modify-private playlist-modify-public"


def print_app_name() -> str:
    """Return the welcome message (kept as a small, testable public helper)."""
    return f"Welcome to {APP_NAME}!"


def get_base64_encoded_credentials(client_id: str, client_secret: str) -> str:
    """Encode an OAuth client ID and secret using HTTP Basic auth format."""
    credentials = f"{client_id}:{client_secret}"
    return base64.b64encode(credentials.encode("utf-8")).decode("ascii")


def shuffled_copy(items: Iterable[str], rng: random.Random | None = None) -> list[str]:
    """Return a randomized copy without mutating the caller's collection."""
    result = list(items)
    (rng or random).shuffle(result)
    return result


def chunked(items: list[str], size: int = 100) -> list[list[str]]:
    """Split items into Spotify API-sized batches."""
    if size < 1:
        raise ValueError("size must be at least 1")
    return [items[index : index + size] for index in range(0, len(items), size)]


def fetch_all_pages(client: Spotify, first_page: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect items from a paginated Spotify response."""
    items = list(first_page.get("items", []))
    page = first_page
    while page.get("next"):
        page = client.next(page)
        items.extend(page.get("items", []))
    return items


class SpotifyToolsApp:
    """Tkinter UI for browsing and shuffling Spotify playlists."""

    def __init__(self, window: tk.Tk) -> None:
        self.window = window
        self.window.title(APP_NAME)
        self.window.geometry("620x520")
        self.window.minsize(520, 420)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.client_id = os.getenv("SPOTIPY_CLIENT_ID", "")
        self.client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
        self.oauth: SpotifyOAuth | None = None
        self.spotify: Spotify | None = None
        self.user: dict[str, Any] | None = None
        self.playlists: list[dict[str, Any]] = []
        self.selected_playlist: dict[str, Any] | None = None
        self.track_cache: LRUCache[str, list[dict[str, Any]]] = LRUCache(maxsize=100)
        self._images: list[ImageTk.PhotoImage] = []

        self.container = ttk.Frame(window, padding=24)
        self.container.pack(fill="both", expand=True)
        self.show_login()

    def clear(self) -> None:
        for widget in self.container.winfo_children():
            widget.destroy()

    def run_task(
        self,
        label: str,
        task: Callable[[], Any],
        on_success: Callable[[Any], None],
    ) -> None:
        """Run network work off the UI thread and marshal results back safely."""
        dialog = tk.Toplevel(self.window)
        dialog.title(label)
        dialog.transient(self.window)
        dialog.grab_set()
        ttk.Label(dialog, text=label).pack(padx=30, pady=(20, 8))
        bar = ttk.Progressbar(dialog, mode="indeterminate", length=240)
        bar.pack(padx=30, pady=(0, 20))
        bar.start(12)

        def worker() -> None:
            try:
                result = task()
            except Exception as exc:  # display errors on the Tk thread
                self.window.after(0, finish_error, exc)
            else:
                self.window.after(0, finish_success, result)

        def finish_success(result: Any) -> None:
            dialog.destroy()
            on_success(result)

        def finish_error(exc: Exception) -> None:
            dialog.destroy()
            messagebox.showerror("SpotifyTools", f"{label} failed:\n{exc}")

        threading.Thread(target=worker, daemon=True).start()

    def show_login(self) -> None:
        self.clear()
        logo_path = APP_DIR / "spotify_logo.png"
        if logo_path.exists():
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((340, 120), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(logo)
            self._images = [photo]
            ttk.Label(self.container, image=photo).pack(pady=(45, 20))
        ttk.Label(self.container, text=print_app_name(), font=("Segoe UI", 22, "bold")).pack(pady=10)
        ttk.Label(
            self.container,
            text="Browse your playlists and give every track a genuinely random position.",
            wraplength=460,
            justify="center",
        ).pack(pady=(0, 24))
        ttk.Button(self.container, text="Log in with Spotify", command=self.login).pack()

    def login(self) -> None:
        if not self.client_id or not self.client_secret:
            messagebox.showerror(
                "Configuration required",
                "Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET before starting the app. "
                "See README.md for setup instructions.",
            )
            return

        def authenticate() -> tuple[SpotifyOAuth, Spotify, dict[str, Any]]:
            oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=SCOPES,
                open_browser=True,
                show_dialog=True,
            )
            oauth.get_access_token(as_dict=False)
            client = Spotify(auth_manager=oauth, requests_timeout=15, retries=3)
            return oauth, client, client.current_user()

        def logged_in(result: tuple[SpotifyOAuth, Spotify, dict[str, Any]]) -> None:
            self.oauth, self.spotify, self.user = result
            self.show_home()

        self.run_task("Signing in to Spotify", authenticate, logged_in)

    def show_home(self) -> None:
        self.clear()
        display_name = (self.user or {}).get("display_name") or "Spotify user"
        ttk.Label(self.container, text=f"Hello, {display_name}", font=("Segoe UI", 22, "bold")).pack(pady=(50, 12))
        ttk.Label(self.container, text="Choose a playlist to inspect or shuffle its saved order.").pack(pady=(0, 24))
        ttk.Button(self.container, text="View playlists", command=self.load_playlists).pack(pady=6)
        ttk.Button(self.container, text="Log out", command=self.logout).pack(pady=6)

    def load_playlists(self) -> None:
        assert self.spotify is not None

        def fetch() -> list[dict[str, Any]]:
            return fetch_all_pages(self.spotify, self.spotify.current_user_playlists(limit=50))

        def loaded(playlists: list[dict[str, Any]]) -> None:
            self.playlists = playlists
            self.show_playlists()

        self.run_task("Loading playlists", fetch, loaded)

    def show_playlists(self) -> None:
        self.clear()
        ttk.Label(self.container, text="Your playlists", font=("Segoe UI", 20, "bold")).pack(pady=(5, 14))
        list_frame = ttk.Frame(self.container)
        list_frame.pack(fill="both", expand=True)
        playlist_list = tk.Listbox(list_frame, activestyle="none", font=("Segoe UI", 11))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=playlist_list.yview)
        playlist_list.configure(yscrollcommand=scrollbar.set)
        playlist_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for playlist in self.playlists:
            playlist_list.insert("end", playlist.get("name", "Untitled playlist"))

        def open_selected(_event: tk.Event | None = None) -> None:
            selection = playlist_list.curselection()
            if selection:
                self.load_playlist(self.playlists[selection[0]])

        playlist_list.bind("<Double-Button-1>", open_selected)
        ttk.Button(self.container, text="Open selected", command=open_selected).pack(pady=(14, 5))
        ttk.Button(self.container, text="Home", command=self.show_home).pack(pady=5)

    def load_playlist(self, playlist: dict[str, Any]) -> None:
        assert self.spotify is not None
        self.selected_playlist = playlist
        uri = playlist["uri"]

        def fetch() -> list[dict[str, Any]]:
            if uri not in self.track_cache:
                self.track_cache[uri] = fetch_all_pages(
                    self.spotify, self.spotify.playlist_items(uri, limit=100)
                )
            return self.track_cache[uri]

        self.run_task("Loading tracks", fetch, self.show_playlist)

    def show_playlist(self, items: list[dict[str, Any]]) -> None:
        self.clear()
        playlist = self.selected_playlist or {}
        ttk.Label(
            self.container,
            text=playlist.get("name", "Playlist"),
            font=("Segoe UI", 20, "bold"),
            wraplength=500,
        ).pack(pady=(5, 4))
        valid_tracks = [item.get("track") for item in items if item.get("track")]
        ttk.Label(self.container, text=f"{len(valid_tracks)} tracks").pack(pady=(0, 12))
        track_list = tk.Listbox(self.container, activestyle="none", font=("Segoe UI", 10))
        track_list.pack(fill="both", expand=True)
        for track in valid_tracks:
            artists = ", ".join(artist["name"] for artist in track.get("artists", []))
            track_list.insert("end", f"{track.get('name', 'Unknown track')} — {artists}")
        ttk.Button(self.container, text="Shuffle playlist order", command=lambda: self.confirm_shuffle(valid_tracks)).pack(pady=(14, 5))
        ttk.Button(self.container, text="Back to playlists", command=self.show_playlists).pack(pady=5)

    def confirm_shuffle(self, tracks: list[dict[str, Any]]) -> None:
        uris = [track["uri"] for track in tracks if track.get("uri")]
        if not uris:
            messagebox.showinfo(APP_NAME, "This playlist has no reorderable tracks.")
            return
        if not messagebox.askyesno(
            "Shuffle playlist order",
            "This permanently changes the playlist's saved track order. Continue?",
        ):
            return
        self.shuffle_playlist(uris)

    def shuffle_playlist(self, uris: list[str]) -> None:
        assert self.spotify is not None and self.selected_playlist is not None
        playlist_uri = self.selected_playlist["uri"]

        def update() -> None:
            batches = chunked(shuffled_copy(uris))
            self.spotify.playlist_replace_items(playlist_uri, batches[0])
            for batch in batches[1:]:
                self.spotify.playlist_add_items(playlist_uri, batch)

        def complete(_result: None) -> None:
            self.track_cache.pop(playlist_uri, None)
            messagebox.showinfo(APP_NAME, "Playlist order shuffled successfully.")
            self.load_playlist(self.selected_playlist or {})

        self.run_task("Shuffling playlist", update, complete)

    def logout(self) -> None:
        if self.oauth:
            try:
                self.oauth.cache_handler.delete_cached_token()
            except (AttributeError, OSError):
                pass
        self.spotify = None
        self.oauth = None
        self.user = None
        self.playlists = []
        self.track_cache.clear()
        self.show_login()

    def close(self) -> None:
        self.window.destroy()


def main() -> None:
    root = tk.Tk()
    SpotifyToolsApp(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SpotifyException):
        print("SpotifyTools stopped.")
