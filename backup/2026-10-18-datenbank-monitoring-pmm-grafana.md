---
title: Datenbank-Monitoring mit PMM und Grafana: 80 Datenbanken, 30 Minuten
date: 2026-10-18
author: Vladislav Sloboder
summary: Datenbank-Monitoring für 80 Produktiv-Datenbanken: PMM, Grafana und Oracle EMCC mit Docker aufgebaut. Mit Compose-Dateien, Befehlen und Praxis-Tipps.
---
Wer **80 produktive Datenbanken** betreibt, Oracle, MariaDB, MySQL und PostgreSQL gemischt, braucht ein zentrales **Datenbank-Monitoring**. Im Notfall erst zu überlegen, in welchem Tool man nachschauen muss, kostet wertvolle Zeit.

Mein Ziel war ein **einziger Blick auf alles**. Das Ergebnis läuft produktiv, und die Plattform stand nach etwa **30 Minuten**: mit **Percona Monitoring and Management (PMM)**, **Grafana** und **Docker**, zwei Compose-Dateien und Open-Source-Werkzeugen. In diesem Beitrag zeige ich dir den Aufbau, die Konfiguration und die Stellen, an denen du aufpassen solltest.

## Architektur: PMM, Oracle EMCC und Grafana im Überblick

![Architektur des Datenbank-Monitorings mit PMM Server, Oracle EMCC und zentralem Grafana](blog/images/pmm-grafana-architektur.png)

Das Prinzip ist einfach, weil jede Technologie den Weg nimmt, den sie am besten beherrscht:

- **Oracle** liefert seine Daten über die vorhandenen Agenten an **Oracle Enterprise Manager Cloud Control (EMCC)**.
- **MariaDB, MySQL und PostgreSQL** werden über **Exporter** vom **Percona Monitoring and Management (PMM) Server** eingesammelt.
- Ein **zentrales Grafana** greift auf beide Quellen zu: auf EMCC über ein Plugin und auf PMM über die Prometheus-kompatible Schnittstelle.

Du brauchst dafür keine neue Monitoring-Welt, sondern nur eine gemeinsame Oberfläche über das, was ohnehin Daten liefert.

## Schritt 1: Docker-Netzwerk für das Monitoring anlegen

Beide Dienste laufen auf demselben Host und sollen sich über Namen erreichen können. Dafür genügt ein externes Netzwerk:

```bash
docker network create monitoring
docker volume create pmm-data
```

## Schritt 2: PMM Server mit Docker Compose starten

Datei `docker-compose.yml` im Verzeichnis für PMM:

```yaml
services:
  pmm-server:
    image: percona/pmm-server:3
    container_name: pmm-server
    restart: always
    ports:
      - "443:8443"
    volumes:
      - pmm-data:/srv
    networks:
      - monitoring

volumes:
  pmm-data:
    external: true

networks:
  monitoring:
    external: true
```

Dann `docker compose up -d`. Die Oberfläche erreichst du danach über `https://<host>`. Ändere das Standard-Passwort sofort.

## Schritt 3: Grafana mit Oracle-EMCC-Plugin einrichten

Das Plugin liegt als ZIP-Datei im Ordner `./plugins` und wird beim Start installiert. Die Zugangsdaten gehören nicht in die Compose-Datei, sondern in eine `.env`-Datei neben ihr.

```yaml
services:
  grafana:
    image: grafana/grafana:latest   # in Produktion: feste Version eintragen
    container_name: grafana_oem_app
    volumes:
      - grafana-data:/var/lib/grafana
      - ./plugins:/var/lib/grafana/plugins
    user: "0"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_PLUGINS_PREINSTALL=/var/lib/grafana/plugins/oracle-emcc-app-5.0.0.zip;oracle-emcc-app
      - GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=oracle-emcc-app,oracle-emcc-datasource
    restart: unless-stopped
    ports:
      - "3000:3000"
    networks:
      - monitoring

volumes:
  grafana-data:
    name: grafana-data

networks:
  monitoring:
    external: true
```

Zwei Hinweise dazu:

- **Unsigniertes Plugin:** Das EMCC-Plugin ist nicht von Grafana signiert, deshalb musst du es ausdrücklich erlauben. Erlaube nur Plugins, deren Herkunft du kennst.
- **Root-Benutzer:** Der Container läuft hier als `root`, damit das Plugin aus dem lokalen ZIP vorinstalliert werden kann. Prüf nach der Einrichtung, ob sich die Rechte eingrenzen lassen.

## Schritt 4: MySQL, MariaDB, PostgreSQL und Oracle anbinden

**Oracle:** Hier ändert sich nichts an deinen Agenten. Du richtest in Grafana die EMCC-Datenquelle mit einem Benutzer ein, der nur lesen darf.

**MariaDB, MySQL, PostgreSQL:** Auf jedem Datenbankserver installierst du den PMM-Client, registrierst den Server und fügst die Datenbank hinzu. Für die Anmeldung am PMM Server nutzt du ein Service-Account-Token, nicht das Admin-Passwort:

```bash
pmm-admin config --server-insecure-tls \
  --server-url=https://service_token:<TOKEN>@<pmm-host>:443

# MySQL oder MariaDB
pmm-admin add mysql --username=pmm --password='<passwort>' \
  --query-source=perfschema --service-name=<name> --host=127.0.0.1 --port=3306

# PostgreSQL
pmm-admin add postgresql --username=pmm --password='<passwort>' \
  --query-source=pgstatements --service-name=<name> --host=127.0.0.1 --port=5432
```

Lege für PMM in jeder Datenbank einen eigenen Benutzer mit den Mindestrechten an. Bei 80 Instanzen lohnt sich ein kleines Skript oder eine Ansible-Rolle. Dann kostet jede neue Instanz nur noch wenige Minuten.

## Schritt 5: PMM als Prometheus-Datenquelle in Grafana

In Grafana legst du eine **Prometheus-Datenquelle** an:

- **URL:** `https://pmm-server:8443/prometheus`. Der Name funktioniert, weil beide Container im Netz `monitoring` hängen.
- **Anmeldung:** per Service-Account-Token im Header `Authorization: Bearer <TOKEN>`.
- **TLS:** Bei einem selbst signierten Zertifikat die Prüfung anpassen. Besser ist ein eigenes Zertifikat.

Details findest du in der [Dokumentation von Percona](https://docs.percona.com/percona-monitoring-and-management/3/). Je nach PMM-Version unterscheidet sich der Pfad (`/prometheus` oder `/victoriametrics`). Teste die Erreichbarkeit zuerst mit `curl` aus dem Grafana-Container.

## Praxis-Tipps für das Datenbank-Monitoring

- **Benennung ist alles:** Ein einheitliches Schema für Service-Namen und Labels (Umgebung, Kunde, Technologie) macht aus 80 Datenbanken eine durchsuchbare Landschaft.
- **Backups nicht vergessen:** Sichere die Volumes `pmm-data` und `grafana-data` und die Dashboards. Auch Monitoring fällt irgendwann aus.
- **Aufbewahrung planen:** Lege fest, wie lange Metriken bleiben sollen. Das bestimmt den Speicherbedarf.
- **Netz begrenzen:** Die Ports 443 und 3000 gehören hinter eine Firewall oder einen Reverse Proxy mit gültigem Zertifikat.
- **Versionen festlegen:** Ersetze `latest` durch eine feste Version und plane Updates bewusst.
- **Lizenzen klären:** PMM und Grafana sind Open Source. Für Oracle EMCC und seine Management Packs gelten Oracles Lizenzregeln. Prüf sie vorab, bevor du Daten daraus nutzt.

## Fazit

Gutes Monitoring braucht keine teure Neuanschaffung. Es reicht, die richtigen Datenquellen sauber zu verbinden und in einer Oberfläche zusammenzuführen. Die Plattform steht in einer halben Stunde, den Rest macht die konsequente Anbindung der Datenbanken.

Plant ihr auch einen Wechsel der Plattform, etwa von [SQL Server nach PostgreSQL oder Firebird](/blog/sql-server-migration-postgresql-firebird/)? Dann lohnt es sich, das Monitoring gleich mitzudenken.

Du betreibst viele Datenbanken und willst sie zentral im Blick haben? Ich plane und baue solche Umgebungen als unabhängiger Datenbankarchitekt, von der Architektur bis zum Betrieb. [Schreib mir kurz](/#kontakt), dann schauen wir gemeinsam, was bei dir sinnvoll ist.
