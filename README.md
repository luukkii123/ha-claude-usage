# Claude Usage

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

**Zeigt die rollierenden Nutzungslimits eines claude.ai-Abos als Sensoren in
Home Assistant.**

## Wofür das gut ist

Ein claude.ai-Abo hat zwei gleitende Fenster: eines über 5 Stunden, eines über
7 Tage. Wie voll die gerade sind, sieht man sonst erst, wenn man auf die Grenze
läuft. Diese Integration fragt den Stand regelmäßig ab und legt ihn als Sensoren
ab — damit lässt sich ein Dashboard bauen oder eine Benachrichtigung auslösen,
bevor das Fenster voll ist.

## Vorher lesen

- **Es braucht ein claude.ai-OAuth-Token, keinen API-Schlüssel.** Ein
  `sk-ant-api…`-Schlüssel funktioniert hier nicht sinnvoll: er misst die
  **API-Tier-Limits** (Anfragen und Token pro Minute), nicht die Abo-Limits, um
  die es hier geht.
- **Die ausgelesenen Header sind undokumentiert.** `anthropic-ratelimit-unified-*`
  steht in keiner öffentlichen Dokumentation von Anthropic. Sie können sich
  jederzeit ändern oder verschwinden. Die Integration liest deshalb defensiv:
  ein fehlender oder unlesbarer Header lässt den zugehörigen Sensor auf
  `unknown`, statt abzustürzen.
- **Noch nicht gegen ein laufendes Konto getestet.** Der Code ist geschrieben und
  geprüft, aber es lief noch keine Abfrage gegen ein echtes claude.ai-Abo. Was
  die Sensoren im Betrieb wirklich anzeigen, ist damit unbestätigt.
- Nicht mit Anthropic verbunden.

## Installation über HACS

1. HACS → ⋮ → **Custom repositories**
2. Repository: `https://github.com/luukkii123/ha-claude-usage`,
   Kategorie: **Integration**
3. **Claude Usage** herunterladen, Home Assistant neu starten
4. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „Claude Usage"

Manuell geht auch: den Ordner `custom_components/claude_usage` nach
`<config>/custom_components/claude_usage` kopieren und neu starten.

Voraussetzungen: Home Assistant **2024.11.0** oder neuer. Zusätzliche Pakete
braucht die Integration nicht — der HTTP-Client kommt von Home Assistant selbst.

Jedes Feld des Dialogs trägt seinen eigenen Hilfetext (deutsch und englisch, je
nach Spracheinstellung von Home Assistant); die Tabelle unter „Einrichtung"
wiederholt ihn in Kurzform.

*English:* add this repository to HACS as a **custom repository** of category
**Integration**, download *Claude Usage*, restart Home Assistant, then go to
Settings → Devices & Services → **Add integration** → *Claude Usage*. Every
field in the dialog carries its own helper text, so nothing has to be guessed.

## Token beschaffen

Das Token entsteht beim Login in claude.ai bzw. Claude Code:

- **Linux / Windows:** `~/.claude/.credentials.json` → `claudeAiOauth.accessToken`
- **macOS:** Schlüsselbund-Eintrag `Claude Code-credentials`

Das Token wird im Config-Entry von Home Assistant abgelegt — **nie** in diesem
Repository und in keiner Datei, die man teilt.

## Einrichtung

| Feld | Standard | Bedeutung |
| --- | --- | --- |
| OAuth-Token | — | das Token von oben; Pflichtfeld, wird verdeckt eingegeben und einmal ausprobiert, bevor der Eintrag entsteht |
| Abfrageintervall | 300 s | Sekunden zwischen zwei Testabfragen an die Anthropic-API; erlaubt 60 bis 3600 |

Beim Speichern macht die Integration sofort eine Probeabfrage. Wird das Token
mit 401/403 abgelehnt, kommt „Token abgelehnt"; ist die API nicht erreichbar,
„nicht erreichbar". Erst danach wird der Eintrag angelegt.

Über **Konfigurieren** lassen sich Intervall und Token später ändern:

| Option | Standard | Wirkung |
| --- | --- | --- |
| Neues OAuth-Token | leer | ersetzt das gespeicherte Token ab sofort; leer lassen behält das bisherige |
| Abfrageintervall | 300 s | Sekunden zwischen zwei Testabfragen an die Anthropic-API; erlaubt 60 bis 3600 |

**Es ist nur ein Eintrag möglich.**

### Wenn das Token abläuft

Ein claude.ai-OAuth-Token ist kurzlebig. Antwortet die API mit 401 oder 403,
startet die Integration die **erneute Anmeldung**: Home Assistant zeigt bei
*Claude Usage* die Meldung „Erneut anmelden" mit einem Knopf, der ein einziges
Feld öffnet — das neue Token. Es wird geprüft, bevor es das alte ersetzt, und
zugleich aus den Optionen entfernt, damit kein altes Token aus einem früheren
„Konfigurieren" gewinnt. Die Sensoren laufen danach weiter, ohne dass der
Eintrag neu angelegt werden muss.

Ein automatischer Refresh-Token ist bewusst **nicht** gebaut (siehe „Grenzen");
die erneute Anmeldung ist der von Home Assistant vorgesehene Weg, das
sichtbar zu machen, statt die Sensoren still `unavailable` werden zu lassen.

## Entitäten

Es entsteht ein Dienstgerät „Claude Usage" mit sieben Sensoren. Die Entitäts-IDs
lauten üblicherweise `sensor.claude_usage_<schlüssel>`.

| Sensor | Einheit / Klasse | Inhalt |
| --- | --- | --- |
| Five-hour utilization | `%`, Messwert | Auslastung des 5-Stunden-Fensters |
| Seven-day utilization | `%`, Messwert | Auslastung des 7-Tage-Fensters |
| Five-hour reset | Zeitstempel | wann das 5-Stunden-Fenster zurückgesetzt wird |
| Seven-day reset | Zeitstempel | wann das 7-Tage-Fenster zurückgesetzt wird |
| Five-hour status | Text | Statustext zum 5-Stunden-Fenster |
| Seven-day status | Text | Statustext zum 7-Tage-Fenster |
| Overall status | Text | Statustext insgesamt |

Die Auslastung liefert der Header als Bruch (0–1); die Integration rechnet auf
Prozent um und rundet auf zwei Stellen. Die Reset-Zeiten kommen als
Unix-Epoch und werden zu UTC-Zeitstempeln, die Home Assistant in der lokalen
Zeitzone anzeigt.

Die drei Statuswerte werden **unverändert durchgereicht** — die Integration
wertet sie nicht aus und kennt keine feste Liste möglicher Werte. Welche Texte
dort auftauchen, ist ebenso undokumentiert wie die Header selbst.

Fehlt ein Header, bleibt der zugehörige Sensor `unknown`. Die anderen Sensoren
sind davon nicht betroffen.

## Wie die Daten entstehen

Jedes Intervall schickt die Integration einen `POST` an
`https://api.anthropic.com/v1/messages` mit `model=claude-haiku-4-5`,
`max_tokens=1` und einem einzelnen Zeichen als Prompt, authentifiziert mit
`Authorization: Bearer <Token>` und `anthropic-beta: oauth-2025-04-20`.

**Gelesen wird nur die Kopfzeile der Antwort, nie der Text.** Der Aufruf ist
lediglich der Anlass, überhaupt eine Antwort zu bekommen; die Zahlen stehen in
den `anthropic-ratelimit-unified-*`-Headern.

## Grenzen

- **Kein automatischer Token-Refresh.** Ein claude.ai-OAuth-Token ist kurzlebig.
  Läuft es ab, antwortet die API mit 401 — seit 09.09.2026 wird daraus die
  erneute Anmeldung (siehe „Wenn das Token abläuft"), nicht mehr ein stilles
  `unavailable`. Ein neues Token einzutragen bleibt trotzdem Handarbeit; das ist
  der häufigste Zustand im Alltag und der größte offene Punkt dieser
  Integration.
- **Die Abfrage zählt mit.** `max_tokens=1` auf Haiku ist praktisch nichts, aber
  eben nicht null: jede Abfrage ist eine Anfrage. Bei 300 s sind das rund 288
  am Tag. Ein kürzeres Intervall erhöht die Zahl entsprechend.
- **Zu häufiges Abfragen führt zu 429.** Die Integration meldet das als Fehler
  samt `retry-after` und schlägt ein größeres Intervall vor; sie drosselt sich
  nicht selbst.
- **Undokumentierte Header** — siehe oben. Ändert Anthropic etwas, hört diese
  Integration ohne Vorwarnung auf, Zahlen zu liefern.
- **Ungetestet gegen ein echtes Konto** — siehe oben.

## Entfernen

1. Einstellungen → Geräte & Dienste → **Claude Usage** → ⋮ → **Löschen**. Damit
   endet die Abfrage sofort, und die Sensoren verschwinden aus Home Assistant.
   Das gespeicherte OAuth-Token wird mit dem Eintrag gelöscht.
2. In HACS **Claude Usage** → ⋮ → **Entfernen**, danach Home Assistant neu
   starten. Das löscht `custom_components/claude_usage`.

**Was zurückbleibt:** nichts von der Integration selbst — kein Gerät, keine
Entität, keine Datei außerhalb des Config-Entrys. Was im Verlauf (Recorder)
und in den Langzeitstatistiken der Sensoren steht, bleibt bis zum nächsten
Aufräumen des Recorders erhalten; wer es sofort los sein will, löscht es unter
*Entwicklerwerkzeuge → Statistiken*. Das Token bei claude.ai selbst wird
dadurch **nicht** widerrufen — dafür meldet man sich dort ab.

*English:* delete the entry under Settings → Devices & Services (this removes
the stored token and all sensors), then remove *Claude Usage* in HACS and
restart. Nothing is left behind except recorder history and long-term
statistics of the deleted sensors; the claude.ai token itself is not revoked.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
