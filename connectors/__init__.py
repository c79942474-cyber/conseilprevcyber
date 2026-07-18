"""Connecteurs d'ingestion pour le cockpit CONSEILPREV Cyber.

Chaque source (CSV, syslog, plateforme OT) normalise ses données vers le modèle
commun {asset, zone, type, event, severity, ts} et les pousse sur POST /api/ingest.

Voir connectors/README.md pour l'utilisation, et docs/integration-donnees-reelles.md
pour l'architecture d'ensemble.
"""
