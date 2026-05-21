# 🎧 EPUB → MP3 Converter

Zaawansowana, nowoczesna aplikacja webowa napisana w języku Python przy użyciu frameworka **Streamlit**, która konwertuje książki elektroniczne w formacie **EPUB** na wysokiej jakości pliki **MP3** (audiobooki).

Aplikacja oferuje pełne wsparcie dla lokalnej syntezy mowy **Supertonic TTS** oraz chmurowej, bezpłatnej usługi **Microsoft Edge TTS** z szerokim wachlarzem personalizacji głosu, prędkości oraz tonu.

---

## 🌟 Główne Funkcje

*   **📖 Inteligentny podział rozdziałów**:
    Aplikacja automatycznie dzieli długie teksty na mniejsze segmenty (do 100 000 znaków) na granicach zdań, co zapobiega ucinaniu słów w środku wypowiedzi i ułatwia przetwarzanie przez silniki TTS.
*   **🌍 Dwa silniki syntezy mowy (TTS)**:
    *   **Supertonic TTS**: W pełni lokalny, zaawansowany silnik TTS wspierający 31 języków (w tym model `supertonic-3`). Oferuje zestaw dopracowanych profili głosowych (męskich M1–M5 oraz damskich F1–F5).
    *   **Microsoft Edge TTS**: Chmurowy silnik (nie wymaga żadnego klucza API ani systemu Windows!), oferujący dziesiątki naturalnie brzmiących głosów neuronowych, automatycznie filtrowanych pod kątem wybranego języka książki.
*   **🎛️ Pełna kontrola parametrów mowy (Edge TTS)**:
    *   Regulacja prędkości odtwarzania (**Speech Rate**): `-50%` do `+100%`
    *   Regulacja głośności mowy (**Speech Volume**): `-50%` do `+50%`
    *   Regulacja wysokości/tonu głosu (**Speech Pitch**): `-50Hz` do `+50Hz`
*   **🧹 Zaawansowane oczyszczanie tekstu (Normalizacja)**:
    Automatyczne usuwanie i oczyszczanie niestandardowych cudzysłowów, pauz, myślników, miękkich łączników, znaków kontrolnych oraz podwójnych spacji w celu zapewnienia idealnej intonacji lektora.
*   **🚀 Wygodne sterowanie konwersją**:
    *   Konwersja pojedynczego, wybranego rozdziału.
    *   Konwersja całej książki naraz.
    *   Możliwość wznowienia konwersji od konkretnego numeru rozdziału.
*   **🎧 Elastyczny format wyjściowy (MP3)**:
    Możliwość wyboru przepływności (bitrate): `64k`, `96k`, `128k` (domyślnie), `192k`, `256k`, `320k`. Pliki są automatycznie nazywane w usystematyzowany sposób (np. `001_Nazwa_Rozdzialu.mp3`).

---

## 🛠️ Wymagania systemowe

Aby aplikacja mogła poprawnie kodować pliki audio do formatu MP3, w Twoim systemie operacyjnym musi być zainstalowany program **FFmpeg**.

### Instalacja FFmpeg:
*   **Linux (Ubuntu/Debian)**:
    ```bash
    sudo apt update
    sudo apt install ffmpeg
    ```
*   **macOS (Homebrew)**:
    ```bash
    brew install ffmpeg
    ```
*   **Windows**:
    Pobierz oficjalną wersję instalacyjną ze strony [ffmpeg.org](https://ffmpeg.org/) i dodaj ścieżkę binariów do zmiennej środowiskowej systemowej `PATH`.

---

## 🚀 Instalacja i Uruchomienie

1.  **Sklonuj repozytorium**:
    ```bash
    git clone <url-twojego-repozytorium>
    cd Supertonic2
    ```

2.  **Stwórz i aktywuj środowisko wirtualne**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Na Windows: venv\Scripts\activate
    ```

3.  **Zainstaluj wymagane zależności**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Uruchom aplikację Streamlit**:
    ```bash
    streamlit run app.py
    ```

Po uruchomieniu aplikacja otworzy się automatycznie w Twojej domyślnej przeglądarce pod adresem: `http://localhost:8501`.

---

## 📂 Struktura Projektu

*   `app.py` — Główny plik aplikacji zawierający architekturę Streamlit, silniki syntezy mowy oraz logikę przetwarzania tekstu.
*   `requirements.txt` — Lista zależności bibliotecznych (Streamlit, Supertonic, Edge-TTS, BeautifulSoup4, Soundfile, lxml).

---

## 📄 Licencja

Projekt dystrybuowany na licencji MIT. Zobacz plik `LICENSE` w celu uzyskania szczegółowych informacji.

---
*Stworzone przy użyciu technologii [Supertonic](https://github.com/supertone-inc/supertonic) oraz [Edge-TTS](https://github.com/rany2/edge-tts).*
