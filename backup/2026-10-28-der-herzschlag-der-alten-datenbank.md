---
title: Der Herzschlag der alten Datenbank
date: 2026-10-28
author: Vladislav Sloboder
summary: 
---
*Wie ich Firebird 2.5 zum Sprechen brachte – und was mich eine Monitoring-Plattform dabei lehrte*

Von Vladislav Sloboder · ArchiDB

Es gibt Datenbanken, die niemand mehr anfasst, weil sie funktionieren. Firebird 2.5 ist eine davon. In Warenwirtschaften, Abrechnungssystemen und Lagerverwaltungen läuft sie seit mehr als einem Jahrzehnt, leise wie ein Maschinenraum tief im Bauch eines Schiffes. Das Tückische an leisen Maschinen: Man hört sie erst, wenn sie verstummen.

Mich ließ das nicht los. Wer ein Vierteljahrhundert lang Datenbanken betreut, lernt, dass ein Ausfall selten mit einem Knall beginnt. Er beginnt mit einer Zahl, die langsam in die falsche Richtung wandert, Tag für Tag, unbemerkt, weil niemand sie anschaut. Also stellte ich mir eine einfache Frage: Was würde ich sehen wollen, wenn ich das Ohr an dieses Schiff legen könnte?

## Die Instrumente im Maschinenraum

Firebird besitzt seit Version 2.1 eine Reihe versteckter Instrumente, die MON$-Tabellen. Sie verraten, wer verbunden ist, was gerade läuft und wie es um die Transaktionen steht – und die sind der eigentliche Herzschlag. Jede Transaktion trägt eine fortlaufende Nummer. Daneben führt die Datenbank Buch über die älteste Transaktion, die noch Spuren hinterlässt (OIT), und die älteste, die noch offen ist (OAT).

Der Abstand zwischen der nächsten Nummer und der ältesten offenen ist wie ein Seil zwischen Schiff und Anker. Bleibt er kurz, ist alles gut. Wird er länger und länger, hält irgendwo jemand eine Transaktion fest, die längst hätte enden sollen. Dann kann die Garbage Collection nicht aufräumen, alte Datensatzversionen stapeln sich, und das Schiff wird träge, ohne dass ein einziger Alarm erklingt.

Ich wollte dieses Seil sichtbar machen. So entstand ein kleiner Exporter in Python, der die Instrumente ausliest und im Format von Prometheus anbietet, damit Percona PMM und Grafana daraus Kurven zeichnen können.

## Der Zeiger, der log

Die erste Version war schnell geschrieben, die Metriken direkt im Code. Sie lief, sie lieferte Zahlen, und ich war zufrieden. Bis ich im Protokoll eine Zeile las, die dort schon lange stand:

*Table unknown – MON$LOCKS.*

Ich hatte eine Tabelle abgefragt, die es in Firebird 2.5 nie gegeben hat. Der Fehler war nicht laut, er stand nur im Log, und die Anzeige im Dashboard zeigte unbeirrt eine freundliche Null. Schlimmer noch: Der Fehler riss alle nachfolgenden Abfragen mit sich. Ein Messgerät, das im Zweifel Null anzeigt, ist gefährlicher als eines, das gar nichts anzeigt. Die Null sieht nach Ruhe aus.

Das war der Moment, in dem ich den Exporter neu dachte. Heute stehen alle Metriken in einer Datei, `metrics.json`, jede mit ihrer eigenen Abfrage und jede für sich abgesichert: Scheitert eine, läuft der Rest weiter, und der Fehler wird sichtbar gezählt. Bei jedem Abruf fragt der Exporter die Datenbank neu, und eine eigene Metrik, `firebird_up`, sagt ehrlich, ob die Verbindung überhaupt steht. Keine alten Werte mehr, die Normalität vortäuschen.

## Das Labyrinth hinter der freundlichen Tür

Der Exporter war bereit. Nun brauchte er ein Zuhause: einen PMM-Server, einen Agenten, ein paar Container in Docker Compose. Was folgte, war weniger Handwerk als Detektivarbeit.

**Der Agent, der nie erwachte.** Ich hatte den Startbefehl des PMM-Clients durch ein eigenes Skript ersetzt. Der Container lief, schwieg aber – kein Agent, keine Anmeldung, nur ein geduldiges `tail`, das ins Leere lauschte.

**Die freundliche Tür.** Der Server antwortete auf jede Anfrage mit demselben Satz: *500 Internal Server Error*. Es war der Pförtner, nginx, der höflich meldete, dass etwas nicht stimmte, ohne zu sagen, was. Dahinter fand ich ein leeres Haus: Die Datenbank des Servers fand ihr Verzeichnis nicht, ein anderer Dienst startete im Sekundentakt neu und fiel wieder um. Die Ursache war so schlicht wie unsichtbar. Das Image, das ich verwendete, war für Intel-Prozessoren gebaut, mein Mac aber trägt Apple Silicon und versuchte es in einer Emulation. Erst mit PMM 3, das auch für ARM erscheint, kam Leben ins Haus.

**Eine Datei, die niemand nennt.** Der Client der neuen Version verlangte eine Konfigurationsdatei, ohne es freundlich zu sagen, und brach mit einer Meldung ab, die erst beim dritten Lesen Sinn ergab.

**Ein Schlüssel, der nicht passte.** Mein Agent wurde mit *Invalid username or password* abgewiesen, bis ich statt eines Passworts ein Service-Token einsetzte, das genau dafür gedacht ist.

Und dann, in einem der vielen Fenster, das, wofür sich alles gelohnt hatte:

```
firebird_up 1.0
firebird_transaction_oit 2590
firebird_transaction_oat 2591
firebird_transaction_gap 1
```

Eine Datenbank, ruhig atmend. Das Seil zwischen Schiff und Anker: ein einziges Glied lang. Es ist erstaunlich, wie sehr einen eine Eins berühren kann, wenn man Stunden damit verbracht hat, sie zu finden.

## Was heute gemessen wird

Aus dem kleinen Experiment wurde ein Werkzeug, das viel mehr hört als nur den Herzschlag:

- den Transaktionszähler, OIT, OAT und OST sowie die Lücke dazwischen,
- Verbindungen insgesamt, aktive und nach Benutzer,
- die älteste offene Transaktion und das am längsten laufende Statement in Sekunden,
- Cache-Trefferquote und Seiten-I/O,
- Einfügungen, Änderungen, Löschungen, sequentielle gegen indexierte Lesezugriffe und Garbage Collection,
- Speicher, Datenbankgröße und freien Plattenplatz,
- und jede eigene SQL-Abfrage, die Sie in `metrics.json` ergänzen.

Dazu gehört ein Dashboard, das aus den Zahlen Kurven und aus den Kurven Gewissheit macht.

## Für alle Umgebungen: ein Container

Am Ende war mir wichtig, dass niemand all das noch einmal erleben muss. Deshalb steckt der Exporter in einem Docker-Image, das Python, alle Bibliotheken in festen Versionen und den Firebird-Client mitbringt. Auf dem Server genügt:

```
docker compose up -d --build
curl -s http://localhost:9103/metrics | grep firebird_up
```

Der PMM-Agent bekommt den Exporter mit einem einzigen Befehl vorgestellt:

```
pmm-admin add external --service-name=firebird-exporter --group=firebird --listen-port=9103 --metrics-path=/metrics
```

Und bei mehreren Umgebungen? Dort dasselbe Image, dieselben Versionen, dieselbe Handhabung. Das ist der ganze Zauber.

## Epilog

Ich glaube, dass gutes Monitoring weniger mit Technik zu tun hat als mit Vertrauen. Dem Vertrauen, dass die Stille im Maschinenraum echte Stille ist und kein Messfehler. Dass eine Null eine Null bedeutet und kein Fehler im Verborgenen sitzt. Dass man nachts ruhig schlafen kann, weil jemand die Instrumente ablesen würde, wenn es nötig wäre.

Der Exporter ist Open Source und steht unter der MIT-Lizenz. Sie finden ihn, das Dockerfile und alles, was dazugehört, hier:

**[github.com/vladislavsloboder/firebird-exporter](https://github.com/vladislavsloboder/firebird-exporter)**

Wenn Sie ihn in Ihrer Umgebung einrichten möchten oder sich fragen, was Ihre Firebird-Datenbank Ihnen gerade nicht erzählt, sprechen Sie mich gern an. Index gut, alles gut.
