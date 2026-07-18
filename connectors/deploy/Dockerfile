# Connecteur OT -> cockpit, en conteneur. Le connecteur n'a AUCUNE dépendance
# (Python standard) : l'image reste minimale.
#
# Build (depuis la racine du dépôt) :
#   docker build -f connectors/deploy/Dockerfile -t conseilprev-connector .
#
# Run (interrogation d'une plateforme OT) :
#   docker run --rm --env-file /etc/conseilprev/connector.env conseilprev-connector \
#     otplatform --url "$OT_API_URL" --header "Authorization: Bearer $OT_API_TOKEN" --interval 10
#
# Run (réception syslog UDP — exposer le port) :
#   docker run --rm -p 5514:5514/udp --env-file /etc/conseilprev/connector.env \
#     conseilprev-connector syslog --listen 0.0.0.0:5514
FROM python:3.11-slim

WORKDIR /opt/conseilprev
COPY connectors/ ./connectors/

# Utilisateur non-root.
RUN useradd --system --no-create-home connector
USER connector

# COCKPIT_URL et INGEST_TOKEN sont fournis via --env-file / -e au démarrage.
ENTRYPOINT ["python", "-m", "connectors.connector"]
CMD ["demo", "--dry-run"]
