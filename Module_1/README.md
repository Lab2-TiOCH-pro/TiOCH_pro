#  Interfejs użytkownika – Moduł 1 (React)

Ten moduł zawiera kod frontendowy odpowiedzialny za część wizualną aplikacji, stworzoną w technologii **React**. Interfejs umożliwia użytkownikom przesyłanie dokumentów do analizy oraz przeglądanie wyników.


## Struktura projektu

```

TiOCH\_pro/
└── Module\_1/
└── interfejs/
├── public/
└── src/
├── components/      # Komponenty React odpowiadające za poszczególne ekrany
├── img/             # Pliki graficzne (np. logo, ikony)
├── App.js           # Główna konfiguracja routingu
└── index.js         # Punkt wejścia do aplikacji

```

## Uruchomienie aplikacji

Aby uruchomić interfejs, należy przejść do katalogu `interfejs` :

```bash
cd TiOCH_pro/Module_1/interfejs
```
A następnie z poziomu terminala wykonać poniższe polecenia:

```bash
npm install   # tylko przy pierwszym uruchomieniu
npm start
```

## Dostępne widoki

* **`HomePage`** – Strona główna z przyciskiem do przejścia dalej.
* **`SprawdzPage`** – Formularz przesyłania plików i opcjonalnie adresu e-mail.
* **`WynikiPage`** – Prezentacja wyników i możliwość ich pobrania.


## Wymagania systemowe

* Node.js `>= 14`
* npm `>= 6`