---
title: Firebird 5 Migration: Der Praxis-Leitfaden für einen Umstieg ohne böse Überraschungen
date: 2026-10-06
author: Vladislav Sloboder
summary: Firebird 5 Migration in 5 Schritten: ODS prüfen, Stolpersteine finden, parallel sichern und wiederherstellen. Praxis-Checkliste vom Datenbankarchitekten.
---
Deine Firebird-Datenbank läuft seit Jahren stabil. Niemand fasst sie an, und genau das ist das Problem: Backups dauern über Nacht, ein Sweep legt zur Mittagszeit den Server lahm, und das Wort „Upgrade“ löst im Team Schweißausbrüche aus.

Dabei ist der Umstieg auf **Firebird 5** besser planbar, als die meisten denken. In diesem Leitfaden zeige ich dir den Fahrplan, den ich in Datenbankprojekten verwende, und die Stolpersteine, über die ich immer wieder stolpere.

## Warum sich der Umstieg lohnt

Firebird 5.0 ändert nichts an der Architektur, bringt aber Werkzeuge, die den Alltag spürbar verbessern:

- **Parallele Wartung:** Backup, Restore, Sweep und Indexaufbau laufen auf mehreren Threads. Je nach Hardware und Datenbank halbiert oder drittelt das die Restore-Zeit.
- **Besserer Optimizer:** Abfragen bekommen vielfach bessere Ausführungspläne, ohne dass du eine Zeile SQL anfasst.
- **Neue SQL-Features:** Partielle Indizes, `SKIP LOCKED` für Queue-artige Zugriffe, ein Profiler für SQL und PSQL und mehrzeiliges `RETURNING`.
- **Minor-Upgrade ohne Backup/Restore:** Von Firebird 4.0 auf 5.0 genügt oft ein einziger Befehl.

## Schritt 1: Wo stehst du? Die ODS-Version entscheidet

Jede Firebird-Version hat eine On-Disk-Structure (ODS). Sie bestimmt, wie viel Aufwand der Umstieg bedeutet:

| Deine Version | ODS | Weg zu Firebird 5.0 |
|---|---|---|
| Firebird 2.5 | 11.2 | Backup und Restore, plus Kompatibilitätsprüfung |
| Firebird 3.0 | 12.0 | Backup und Restore |
| Firebird 4.0 | 13.0 | `gfix -upgrade` oder Backup/Restore |
| Firebird 5.0 | 13.1 | bereits am Ziel |

Datenbanken im Format 13.0 kann ein Firebird-5.0-Server weiter öffnen, mit einigen noch nicht nutzbaren neuen Funktionen. Alle älteren Datenbanken müssen per `gbak` in das neue Format überführt werden.

## Schritt 2: Stolpersteine finden, bevor sie dich finden

Mein wichtigster Rat: **Fang nicht mit dem Backup an, sondern mit der Prüfung.** Diese Punkte kosten in der Praxis die meiste Zeit:

- **Authentifizierung:** Ab Firebird 3 ist ein neues Verfahren Standard. Alte Treiber und Clients, die damit nicht zurechtkommen, melden sich nicht mehr an.
- **Benutzerverwaltung:** Die Sicherheitsdatenbank wandert nicht automatisch mit. Von 4.0 auf 5.0 sicherst du `security4.fdb` mit dem alten `gbak` und stellst sie mit dem neuen als `security5.fdb` wieder her.
- **UDFs:** Alte externe Funktionen funktionieren in neueren Versionen nicht mehr. Meist ersetzen eingebaute Funktionen oder UDRs sie.
- **Client-Bibliotheken:** Anwendungen, die eine feste `fbclient`-Version mitbringen, brauchen ein Update.
- **Zeichensätze und reservierte Wörter:** Prüf sie mit einer Testumgebung, nicht erst in Produktion.

## Schritt 3: Der Testlauf auf einer Kopie

Mach eine vollständige Probe auf einem separaten Server, mit einer echten Kopie deiner Daten:

```bash
# Backup auf der bisherigen Version
gbak -b -g -v -user SYSDBA -password <passwort> \
  -se server/3050:service_mgr meine_db backup.fbk

# Restore mit Firebird 5.0, parallel mit 4 Threads
gbak -c -par 4 -v -user SYSDBA -password <passwort> \
  backup.fbk neue_db.fdb
```

Die Option `-g` spart beim Backup die Garbage Collection. Damit `-par` greift, muss in der `firebird.conf` die Einstellung `MaxParallelWorkers` gesetzt sein. In der Standardkonfiguration läuft nichts parallel.

Vergleiche anschließend Laufzeiten, Abfragepläne und die Ergebnisse deiner wichtigsten Reports. Wenn eine Abfrage plötzlich langsamer ist, willst du das jetzt wissen und nicht am Montagmorgen.

## Schritt 4: Der Sonderweg von 4.0 auf 5.0

Wenn du bereits auf 4.0 bist, geht es kürzer:

```bash
gfix -upgrade neue_db.fdb -user SYSDBA -password <passwort>
```

Das hebt die Datenbank innerhalb der gleichen Hauptversion auf 13.1 an, ohne Backup und Restore. Mach trotzdem vorher ein Backup. Ein Rückweg ist schnell vergessen und teuer, wenn er fehlt.

## Schritt 5: Umschalten mit Rückfallplan

- Lege ein **Wartungsfenster** fest und teile es allen Beteiligten mit.
- Sichere den alten Server komplett, bevor du ihn abschaltest.
- Teste nach dem Umschalten die Anmeldungen, die Reports und die Schnittstellen.
- Plane einen **klaren Rückweg**, solange der alte Stand noch nicht überschrieben ist.

## Nach dem Umstieg: Nutz die neuen Möglichkeiten

Starte den Sweep parallel, zum Beispiel mit `gfix -sweep -parallel 4`. Probier partielle Indizes für Abfragen, die nur einen kleinen Teil der Zeilen betreffen. Und nutz den neuen Profiler, bevor du langsame Abfragen im Blindflug optimierst.

## Wann Unterstützung sinnvoll ist

Eine einzelne Datenbank bekommst du mit diesem Plan in einem Wochenende hin. Schwieriger wird es bei vielen Datenbanken, älteren Anwendungen oder engen Zeitfenstern. Dann hilft ein erfahrener Blick auf die Risiken, bevor etwas schiefgeht.

Ich begleite solche Migrationen als unabhängiger Datenbankarchitekt, von der Analyse bis zum Betrieb. Als Partner für **HQbird und IBSurgeon in Deutschland** unterstütze ich außerdem bei Monitoring, Backup-Konzepten und der Wiederherstellung beschädigter Firebird-Datenbanken.

Du planst einen Umstieg oder willst wissen, wo deine Datenbank steht? [Schreib mir kurz](/#kontakt), dann schauen wir gemeinsam darauf.
